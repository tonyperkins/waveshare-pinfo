import os
import time
import logging
import schedule
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from waveshare_epd import epd4in01f, epdconfig
from google_photos_service import GooglePhotosService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PhotoDisplayService:
    """Service for displaying Google Photos on e-ink display"""
    
    def __init__(self):
        self.epd = epd4in01f.EPD()
        self.width = self.epd.width
        self.height = self.epd.height
        
        # Load fonts
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except OSError:
            # Fallback to default fonts
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
        
        # Initialize Google Photos service
        self.photos_service = GooglePhotosService()
        
        # Configuration
        self.rotation_interval = int(os.getenv('PHOTO_ROTATION_INTERVAL_MINUTES', 30))
        self.last_photo_update = None
        self.current_photo_info = None
        
        # Display state
        self.last_display_update = None
        self.update_count = 0
        
    def init_display(self):
        """Initialize the e-ink display"""
        logger.info("Initializing e-ink display for photo service...")
        self.epd.init()
        logger.info("Clearing display for initial setup...")
        self.epd.Clear()
    
    def draw_centered_text(self, draw, y, text, font, color=0):
        """Draw centered text on the image"""
        text_width = draw.textlength(text, font=font)
        x = (self.width - text_width) // 2
        draw.text((x, y), text, font=font, fill=color)
    
    def draw_photo_with_info(self, photo_image, photo_info):
        """Create display image with photo and metadata"""
        try:
            # Create base image
            display_image = Image.new('RGB', (self.width, self.height), 'white')
            draw = ImageDraw.Draw(display_image)
            
            # Calculate photo placement (leave space for metadata)
            info_height = 80  # Space for photo info at bottom
            photo_area_height = self.height - info_height
            
            # Resize photo to fit in available space
            photo_display = self.resize_photo_for_display(photo_image, self.width, photo_area_height)
            
            # Center photo in available space
            photo_x = (self.width - photo_display.width) // 2
            photo_y = (photo_area_height - photo_display.height) // 2
            
            # Paste photo onto display image
            display_image.paste(photo_display, (photo_x, photo_y))
            
            # Draw border around photo
            border_thickness = 2
            for i in range(border_thickness):
                draw.rectangle([
                    photo_x - i - 1, 
                    photo_y - i - 1, 
                    photo_x + photo_display.width + i, 
                    photo_y + photo_display.height + i
                ], outline=0, fill=None)
            
            # Draw separator line
            separator_y = photo_area_height + 10
            draw.line([(10, separator_y), (self.width - 10, separator_y)], fill=0, width=2)
            
            # Draw photo information
            info_y = separator_y + 15
            
            # Photo filename (truncate if too long)
            filename = photo_info.get('filename', 'Unknown')
            if len(filename) > 30:
                filename = filename[:27] + "..."
            
            self.draw_centered_text(draw, info_y, filename, self.font_medium, 0)
            
            # Photo date and time
            creation_time = photo_info.get('creationTime')
            if creation_time:
                try:
                    # Parse ISO format timestamp
                    dt = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                    date_str = dt.strftime("%B %d, %Y")
                    self.draw_centered_text(draw, info_y + 25, date_str, self.font_small, 0)
                except:
                    pass
            
            # Current time and update info
            now = datetime.now()
            update_str = f"Updated: {now.strftime('%I:%M %p')}"
            self.draw_centered_text(draw, info_y + 45, update_str, self.font_small, 0)
            
            return display_image
            
        except Exception as e:
            logger.error(f"Error creating photo display: {e}")
            return self.create_error_display("Error displaying photo")
    
    def resize_photo_for_display(self, photo, max_width, max_height):
        """Resize photo to fit display area while maintaining aspect ratio"""
        try:
            # Calculate scaling factor
            width_ratio = max_width / photo.width
            height_ratio = max_height / photo.height
            scale_factor = min(width_ratio, height_ratio)
            
            # Calculate new dimensions
            new_width = int(photo.width * scale_factor)
            new_height = int(photo.height * scale_factor)
            
            # Resize photo
            resized_photo = photo.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return resized_photo
            
        except Exception as e:
            logger.error(f"Error resizing photo: {e}")
            return photo
    
    def create_error_display(self, error_message):
        """Create error display image"""
        image = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Draw border
        draw.rectangle([5, 5, self.width - 5, self.height - 5], outline=0, width=3)
        
        # Draw error message
        self.draw_centered_text(draw, self.height // 2 - 50, "Photo Service Error", self.font_large, 0)
        self.draw_centered_text(draw, self.height // 2, error_message, self.font_medium, 0)
        
        # Draw timestamp
        now = datetime.now()
        time_str = now.strftime("%I:%M %p on %B %d, %Y")
        self.draw_centered_text(draw, self.height // 2 + 50, time_str, self.font_small, 0)
        
        return image
    
    def create_loading_display(self):
        """Create loading display image"""
        image = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Draw border
        draw.rectangle([5, 5, self.width - 5, self.height - 5], outline=0, width=3)
        
        # Draw loading message
        self.draw_centered_text(draw, self.height // 2 - 30, "Loading Photos...", self.font_large, 0)
        self.draw_centered_text(draw, self.height // 2 + 10, "Connecting to Google Photos", self.font_medium, 0)
        
        # Draw timestamp
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        self.draw_centered_text(draw, self.height // 2 + 50, time_str, self.font_small, 0)
        
        return image
    
    def should_update_photo(self):
        """Check if it's time to update to next photo"""
        if not self.last_photo_update:
            return True
        
        time_since_update = datetime.now() - self.last_photo_update
        return time_since_update >= timedelta(minutes=self.rotation_interval)
    
    def update_display(self):
        """Update display with current or next photo"""
        try:
            logger.info("Starting photo display update...")
            
            # Check if we need to get a new photo
            if self.should_update_photo() or not self.current_photo_info:
                logger.info("Getting next photo...")
                
                # Show loading screen first
                loading_image = self.create_loading_display()
                self.epd.display(self.epd.getbuffer(loading_image))
                
                # Get next photo
                photo_info = self.photos_service.get_next_photo()
                
                if not photo_info:
                    logger.error("No photo available")
                    error_image = self.create_error_display("No photos available")
                    self.epd.display(self.epd.getbuffer(error_image))
                    return
                
                # Download and process photo
                photo_image = self.photos_service.download_photo(photo_info, self.width, self.height - 100)
                
                if not photo_image:
                    logger.error("Failed to download photo")
                    error_image = self.create_error_display("Failed to download photo")
                    self.epd.display(self.epd.getbuffer(error_image))
                    return
                
                # Process for e-ink display
                processed_photo = self.photos_service.process_image_for_eink(
                    photo_image, self.width, self.height - 100
                )
                
                if not processed_photo:
                    logger.error("Failed to process photo")
                    error_image = self.create_error_display("Failed to process photo")
                    self.epd.display(self.epd.getbuffer(error_image))
                    return
                
                self.current_photo_info = photo_info
                self.current_photo_image = processed_photo
                self.last_photo_update = datetime.now()
                
                logger.info(f"Updated to new photo: {photo_info.get('filename', 'Unknown')}")
            
            # Create display with current photo
            if hasattr(self, 'current_photo_image') and self.current_photo_image:
                display_image = self.draw_photo_with_info(self.current_photo_image, self.current_photo_info)
                
                # Update e-ink display
                self.epd.display(self.epd.getbuffer(display_image))
                self.update_count += 1
                self.last_display_update = datetime.now()
                
                logger.info(f"Display updated successfully (update #{self.update_count})")
            else:
                logger.error("No current photo to display")
                error_image = self.create_error_display("No photo loaded")
                self.epd.display(self.epd.getbuffer(error_image))
                
        except Exception as e:
            logger.error(f"Error updating photo display: {e}")
            try:
                error_image = self.create_error_display(f"Update error: {str(e)[:30]}")
                self.epd.display(self.epd.getbuffer(error_image))
            except:
                logger.error("Failed to display error message")
    
    def list_available_albums(self):
        """List available Google Photos albums"""
        logger.info("Listing available Google Photos albums...")
        albums = self.photos_service.list_albums()
        
        if albums:
            print("\nAvailable Google Photos Albums:")
            print("-" * 50)
            for album in albums:
                print(f"Title: {album['title']}")
                print(f"ID: {album['id']}")
                print(f"Photos: {album['mediaItemsCount']}")
                print("-" * 50)
        else:
            print("No albums found or authentication failed.")
        
        return albums
    
    def run(self):
        """Main loop for the photo display service"""
        logger.info("Starting Google Photos display service")
        
        # Initialize display
        self.init_display()
        
        # Authenticate with Google Photos
        if not self.photos_service.authenticate():
            logger.error("Failed to authenticate with Google Photos")
            error_image = self.create_error_display("Authentication failed")
            self.epd.display(self.epd.getbuffer(error_image))
            return
        
        # Schedule photo rotation
        schedule.every(self.rotation_interval).minutes.do(self.update_display)
        
        # Initial display update
        self.update_display()
        
        try:
            while True:
                # Check for scheduled updates
                schedule.run_pending()
                
                # Sleep for a minute between checks
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("Shutting down photo display service...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            logger.info("Cleaning up GPIO and putting display to sleep...")
            epdconfig.module_exit()

def main():
    """Main entry point"""
    import sys
    
    service = PhotoDisplayService()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "list-albums":
            service.list_available_albums()
            return
        elif sys.argv[1] == "test-auth":
            if service.photos_service.authenticate():
                print("Authentication successful!")
                albums = service.photos_service.list_albums()
                print(f"Found {len(albums)} albums")
            else:
                print("Authentication failed!")
            return
    
    # Run the service
    service.run()

if __name__ == "__main__":
    main()
