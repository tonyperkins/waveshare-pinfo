import os
import time
import logging
import schedule
import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
from dotenv import load_dotenv
from google_photos_service import GooglePhotosService

# Configure logging
logging.basicConfig(level=logging.INFO)

# E-ink display setup
try:
    from waveshare_epd import epd7in5_V2
    epd = epd7in5_V2.EPD()
except ImportError:
    logging.warning("E-ink display library not found. Using mock display.")
    from unittest.mock import Mock
    epd = Mock()

# Font setup
try:
    FONT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fonts')
    FONT_REGULAR = ImageFont.truetype(os.path.join(FONT_DIR, 'OpenSans-Regular.ttf'), 18)
    FONT_BOLD = ImageFont.truetype(os.path.join(FONT_DIR, 'OpenSans-Bold.ttf'), 24)
except IOError:
    logging.warning("Fonts not found. Using default fonts.")
    FONT_REGULAR = ImageFont.load_default()
    FONT_BOLD = ImageFont.load_default()

def display_image(image_data, photo_info):
    """Display the given image on the e-ink screen with metadata."""
    try:
        logging.info("Initializing and clearing display...")
        epd.init()
        epd.Clear()

        image = Image.open(io.BytesIO(image_data))
        image = image.convert('L') # Convert to grayscale
        image = ImageOps.autocontrast(image)

        screen_image = Image.new('L', (epd.width, epd.height), 255) # 255 for white

        x_offset = (epd.width - image.width) // 2
        y_offset = (epd.height - image.height) // 2
        screen_image.paste(image, (x_offset, y_offset))

        draw = ImageDraw.Draw(screen_image)
        filename = photo_info.get('filename', 'Unknown')
        creation_time_str = photo_info.get('mediaMetadata', {}).get('creationTime', '')
        try:
            parsed_date = datetime.fromisoformat(creation_time_str.replace('Z', '+00:00'))
            creation_time = parsed_date.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            creation_time = "Unknown date"

        text = f"{filename} - {creation_time}"
        text_bbox = draw.textbbox((0, 0), text, font=FONT_REGULAR)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        draw.text((10, epd.height - text_height - 10), text, font=FONT_REGULAR, fill=0)

        epd.display(epd.getbuffer(screen_image))
        logging.info("Image displayed. Putting display to sleep.")
        epd.sleep()
    except Exception as e:
        logging.error(f"Error displaying image: {e}")

def display_message(message):
    """Display a text message on the e-ink screen."""
    try:
        logging.info(f"Displaying message: {message}")
        epd.init()
        epd.Clear()
        screen_image = Image.new('L', (epd.width, epd.height), 255)
        draw = ImageDraw.Draw(screen_image)
        lines = message.split('\n')
        y_text = 20
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=FONT_BOLD)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text(((epd.width - text_width) / 2, y_text), line, font=FONT_BOLD, fill=0)
            y_text += text_height + 10
        epd.display(epd.getbuffer(screen_image))
        epd.sleep()
    except Exception as e:
        logging.error(f"Error displaying message: {e}")

def main(reload_check=lambda: False):
    """Main loop for the e-ink photo display service."""
    display_message("Starting up Photo Frame...")
    
    load_dotenv(override=True)
    
    photos_service = GooglePhotosService()
    if not photos_service.authenticate():
        logging.error("Authentication failed. Stopping display loop.")
        display_message("Authentication Failed.\nCheck .env and token files.")
        while not reload_check():
            time.sleep(5)
        return

    def update_photo_job():
        logging.info("Scheduled job: Updating photo...")
        image_data, photo_info = photos_service.get_photo()
        if image_data and photo_info:
            display_image(image_data, photo_info)
        else:
            logging.warning("Could not get a new photo for scheduled update.")
            display_message("Could not fetch a new photo.\nCheck logs for details.")

    update_photo_job()

    update_interval = int(os.getenv('UPDATE_INTERVAL_MINUTES', 30))
    schedule.every(update_interval).minutes.do(update_photo_job)
    logging.info(f"Scheduled to update photo every {update_interval} minutes.")

    while not reload_check():
        schedule.run_pending()
        time.sleep(1)
    
    logging.info("Reload signal received. Exiting display loop.")
