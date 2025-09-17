import os
import time
import json
import logging
import schedule
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import requests
from dotenv import load_dotenv
import numpy as np
from waveshare_epd import epd4in01f, epdconfig

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EInkDisplay:
    def __init__(self):
        self.epd = epd4in01f.EPD()
        self.width = self.epd.width
        self.height = self.epd.height
        
        # Load fonts with improved sizes for better space utilization
        try:
            self.font_xlarge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
            self.font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except OSError:
            # Fallback to default fonts if system fonts not available
            self.font_xlarge = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()
        
        # Load environment variables
        self.homeassistant_url = os.getenv('HOME_ASSISTANT_URL')
        self.homeassistant_token = os.getenv('HOME_ASSISTANT_TOKEN')
        
        # Track last content to avoid unnecessary updates
        self.last_content_hash = None
        self.update_count = 0
        self.last_minute = None
        self.last_weather_hash = None
        
    def init_display(self):
        """Initialize the e-ink display"""
        logger.info("Initializing e-ink display...")
        self.epd.init()
        # Only clear on startup, not on every update
        logger.info("Clearing display for initial setup...")
        self.epd.Clear()
        
    def clear_display(self):
        logger.info("Clearing display...")
        self.epd.Clear()
        
    def get_homeassistant_entity(self, entity_id):
        """Fetch entity state from Home Assistant"""
        if not all([self.homeassistant_url, self.homeassistant_token]):
            logger.warning("Home Assistant credentials not configured")
            return None
            
        headers = {
            "Authorization": f"Bearer {self.homeassistant_token}",
            "content-type": "application/json",
        }
        
        try:
            response = requests.get(
                f"{self.homeassistant_url}/api/states/{entity_id}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching from Home Assistant: {e}")
            return None
    
    def draw_centered_text(self, draw, y, text, font, color=0):
        """Draw centered text on the image"""
        text_width = draw.textlength(text, font=font)
        x = (self.width - text_width) // 2
        draw.text((x, y), text, font=font, fill=color)
        
    def draw_left_aligned_text(self, draw, x, y, text, font, color=0):
        """Draw left-aligned text on the image"""
        draw.text((x, y), text, font=font, fill=color)
        
    def draw_right_aligned_text(self, draw, x, y, text, font, color=0):
        """Draw right-aligned text on the image"""
        text_width = draw.textlength(text, font=font)
        draw.text((x - text_width, y), text, font=font, fill=color)
        
    def draw_horizontal_line(self, draw, y, color=0, thickness=2):
        """Draw a horizontal line across the width"""
        for i in range(thickness):
            draw.line([(10, y + i), (self.width - 10, y + i)], fill=color)
            
    def draw_section_box(self, draw, x, y, width, height, color=0, thickness=2):
        """Draw a rectangular border"""
        for i in range(thickness):
            draw.rectangle([x + i, y + i, x + width - i, y + height - i], outline=color, fill=None)
            
    def get_weather_icon(self, temp, humidity, wind_speed, rain):
        """Get a simple text-based weather icon"""
        try:
            temp_val = float(temp) if temp != 'N/A' else 0
            humidity_val = float(humidity) if humidity != 'N/A' else 0
            wind_val = float(wind_speed) if wind_speed != 'N/A' else 0
            rain_val = float(rain) if rain != 'N/A' else 0
            
            if rain_val > 0.1:
                return "🌧"
            elif wind_val > 15:
                return "💨"
            elif humidity_val > 80:
                return "🌫"
            elif temp_val > 80:
                return "☀"
            elif temp_val < 40:
                return "❄"
            else:
                return "⛅"
        except:
            return "⛅"
    
    def update_time_only(self):
        """Fast partial update for just the time display"""
        try:
            now = datetime.now()
            current_minute = now.strftime("%I:%M %p")
            
            # Only update if the minute has changed
            if self.last_minute == current_minute:
                return
            
            # Check if the display supports partial updates
            if hasattr(self.epd, 'displayPartial') or hasattr(self.epd, 'displayPartBaseImage'):
                # Create a small image for just the time areas
                time_image = Image.new('RGB', (self.width, self.height), 'white')
                time_draw = ImageDraw.Draw(time_image)
                
                # Draw main border (to maintain visual consistency)
                self.draw_section_box(time_draw, 5, 5, self.width - 10, self.height - 10, 0, 3)
                
                # Draw time/date in upper left
                time_str = now.strftime("%I:%M %p")
                date_str = now.strftime("%A, %B %d")
                self.draw_left_aligned_text(time_draw, 20, 15, time_str, self.font_large, 0)
                self.draw_left_aligned_text(time_draw, 20, 50, date_str, self.font_tiny, 0)
                
                # Draw last updated in upper right
                self.draw_right_aligned_text(time_draw, self.width - 20, 15, "Updated:", self.font_tiny, 0)
                self.draw_right_aligned_text(time_draw, self.width - 20, 35, current_minute, self.font_medium, 0)
                
                # Try partial update
                try:
                    if hasattr(self.epd, 'displayPartial'):
                        self.epd.displayPartial(self.epd.getbuffer(time_image))
                    elif hasattr(self.epd, 'displayPartBaseImage'):
                        self.epd.displayPartBaseImage(self.epd.getbuffer(time_image))
                    
                    self.last_minute = current_minute
                    logger.info(f"Time updated via partial refresh: {time_str}")
                    return
                except Exception as partial_error:
                    logger.warning(f"Partial update failed: {partial_error}, falling back to smart update")
            
            # Fallback: Only do full update if it's been more than 5 minutes since last weather update
            # This prevents too frequent full updates while keeping time reasonably current
            logger.info("Partial update not available, skipping time-only update")
            self.last_minute = current_minute
            
        except Exception as e:
            logger.error(f"Error in time update: {e}")
    
    def update_display(self):
        """Update the display with current information"""
        try:
            # Create a new image with white background
            image = Image.new('RGB', (self.width, self.height), 'white')
            draw = ImageDraw.Draw(image)
            
            # Define layout margins and sections
            margin = 15
            header_height = 80
            main_section_y = header_height + 20
            
            # Get current time
            now = datetime.now()
            time_str = now.strftime("%I:%M %p")  # 12-hour format with AM/PM
            date_str = now.strftime("%A, %B %d")
            update_time = now.strftime("%I:%M %p")
            
            # === HEADER SECTION ===
            # Draw main border around entire display
            self.draw_section_box(draw, 5, 5, self.width - 10, self.height - 10, 0, 3)
            
            # Draw time/date in upper left
            self.draw_left_aligned_text(draw, 20, 15, time_str, self.font_large, 0)
            self.draw_left_aligned_text(draw, 20, 50, date_str, self.font_tiny, 0)
            
            # Draw last updated in upper right (slightly smaller than main time)
            self.draw_right_aligned_text(draw, self.width - 20, 15, "Updated:", self.font_tiny, 0)
            self.draw_right_aligned_text(draw, self.width - 20, 35, update_time, self.font_medium, 0)
            
            # Draw horizontal line under header
            self.draw_horizontal_line(draw, header_height + 10, 0, 2)
            
            # Get Ecowitt weather data
            temp_data = self.get_homeassistant_entity("sensor.gw1200b_outdoor_temperature")
            humidity_data = self.get_homeassistant_entity("sensor.gw1200b_humidity")
            wind_speed_data = self.get_homeassistant_entity("sensor.gw1200b_wind_speed")
            wind_gust_data = self.get_homeassistant_entity("sensor.gw1200b_wind_gust")
            daily_rain_data = self.get_homeassistant_entity("sensor.gw1200b_daily_rain_piezo")
            feels_like_data = self.get_homeassistant_entity("sensor.gw1200b_feels_like_temperature")
            
            # Extract values with fallbacks
            temp = temp_data.get('state', 'N/A') if temp_data else 'N/A'
            temp_unit = temp_data.get('attributes', {}).get('unit_of_measurement', '°C') if temp_data else '°C'
            
            humidity = humidity_data.get('state', 'N/A') if humidity_data else 'N/A'
            humidity_unit = humidity_data.get('attributes', {}).get('unit_of_measurement', '%') if humidity_data else '%'
            
            wind_speed = wind_speed_data.get('state', 'N/A') if wind_speed_data else 'N/A'
            wind_gust = wind_gust_data.get('state', 'N/A') if wind_gust_data else 'N/A'
            wind_unit = wind_speed_data.get('attributes', {}).get('unit_of_measurement', 'mph') if wind_speed_data else 'mph'
            
            daily_rain = daily_rain_data.get('state', 'N/A') if daily_rain_data else 'N/A'
            rain_unit = daily_rain_data.get('attributes', {}).get('unit_of_measurement', 'in') if daily_rain_data else 'in'
            
            feels_like = feels_like_data.get('state', 'N/A') if feels_like_data else 'N/A'
            
            # === MAIN TEMPERATURE SECTION ===
            temp_section_y = main_section_y
            temp_section_height = 100
            
            # Draw temperature section box
            self.draw_section_box(draw, margin, temp_section_y, self.width - 2*margin, temp_section_height, 0, 2)
            
            # Get weather icon
            weather_icon = self.get_weather_icon(temp, humidity, wind_speed, daily_rain)
            
            # Draw weather icon centered at top
            self.draw_centered_text(draw, temp_section_y + 15, weather_icon, self.font_large, 0)
            
            # Draw temperature and feels-like side by side with equal prominence
            temp_line = f"{temp}{temp_unit}"
            feels_line = f"{feels_like}{temp_unit}" if feels_like != 'N/A' else f"{temp}{temp_unit}"
            
            # Calculate positions for side-by-side display
            quarter_width = self.width // 4
            temp_x = quarter_width
            feels_x = 3 * quarter_width
            
            # Only show feels-like if it's different and available
            if feels_like != 'N/A' and feels_like != temp:
                # Draw temperature on left side
                temp_width = draw.textlength(temp_line, font=self.font_xlarge)
                temp_start_x = temp_x - temp_width // 2
                self.draw_left_aligned_text(draw, temp_start_x, temp_section_y + 55, temp_line, self.font_xlarge, 0)
                
                # Draw feels-like on right side
                feels_width = draw.textlength(feels_line, font=self.font_xlarge)
                feels_start_x = feels_x - feels_width // 2
                self.draw_left_aligned_text(draw, feels_start_x, temp_section_y + 55, feels_line, self.font_xlarge, 0)
                
                # Add labels
                temp_label_width = draw.textlength("ACTUAL", font=self.font_tiny)
                temp_label_x = temp_x - temp_label_width // 2
                self.draw_left_aligned_text(draw, temp_label_x, temp_section_y + 35, "ACTUAL", self.font_tiny, 0)
                
                feels_label_width = draw.textlength("FEELS LIKE", font=self.font_tiny)
                feels_label_x = feels_x - feels_label_width // 2
                self.draw_left_aligned_text(draw, feels_label_x, temp_section_y + 35, "FEELS LIKE", self.font_tiny, 0)
            else:
                # Just show the single temperature centered
                self.draw_centered_text(draw, temp_section_y + 55, temp_line, self.font_xlarge, 0)
            
            # === WEATHER DETAILS SECTION ===
            details_section_y = temp_section_y + temp_section_height + 15
            details_section_height = 100  # Even larger section for xlarge font
            
            # Draw details section box
            self.draw_section_box(draw, margin, details_section_y, self.width - 2*margin, details_section_height, 0, 2)
            
            # Create single line with all weather details in same font as temperature
            detail_y = details_section_y + 35
            
            # Format wind display
            wind_display = f"{wind_speed} {wind_unit}"
            if wind_gust != 'N/A' and wind_gust != wind_speed:
                wind_display += f" (gusts {wind_gust})"
            
            # Create the details line
            details_line = f"💧 {humidity}{humidity_unit}  •  💨 {wind_display}  •  🌧 {daily_rain} {rain_unit}"
            
            # Draw the details line centered with same font as temperature (xlarge)
            self.draw_centered_text(draw, detail_y, details_line, self.font_xlarge, 0)
            
            # Create content hash for weather data only (excluding time)
            weather_string = f"{temp_line}|{humidity}|{wind_speed}|{daily_rain}|{feels_like}"
            import hashlib
            weather_hash = hashlib.md5(weather_string.encode()).hexdigest()
            
            # Check if weather data has changed
            weather_changed = self.last_weather_hash != weather_hash
            
            # Force full update every 20th update for display refresh
            force_full_update = self.update_count % 20 == 0
            
            if weather_changed or force_full_update:
                # Full update needed
                self.epd.display(self.epd.getbuffer(image))
                self.last_weather_hash = weather_hash
                self.last_minute = now.strftime("%I:%M %p")  # Update time tracking
                self.update_count += 1
                logger.info(f"Full display update (update #{self.update_count})")
            else:
                logger.info("Weather unchanged, skipping full display update")
            
            # Always update the content hash for comparison
            content_string = f"{time_str}|{date_str}|{temp_line}|{humidity}|{wind_speed}|{daily_rain}|{feels_like}"
            self.last_content_hash = hashlib.md5(content_string.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error updating display: {e}")
            
    def run(self):
        """Main loop for the display"""
        logger.info("Starting e-ink display application")
        self.init_display()
        
        # Schedule updates
        schedule.every(5).minutes.do(self.update_display)  # Full weather update every 5 minutes
        
        # Initial update
        self.update_display()
        
        last_minute_check = None
        
        try:
            while True:
                # Check for scheduled weather updates
                schedule.run_pending()
                
                # Manual minute checking for more reliable time updates
                now = datetime.now()
                current_minute = now.strftime("%I:%M %p")
                
                if last_minute_check != current_minute:
                    self.update_time_only()
                    last_minute_check = current_minute
                
                time.sleep(10)  # Check every 10 seconds instead of every second
                
        except KeyboardInterrupt:
            logger.info("Shutting down due to KeyboardInterrupt...")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
        finally:
            logger.info("Cleaning up GPIO and putting display to sleep...")
            epdconfig.module_exit()

if __name__ == "__main__":
    display = EInkDisplay()
    display.run()
