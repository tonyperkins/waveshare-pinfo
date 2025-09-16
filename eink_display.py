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
        
        # Load fonts
        self.font_large = ImageFont.load_default()
        self.font_medium = ImageFont.load_default()
        
        # Load environment variables
        self.homeassistant_url = os.getenv('HOME_ASSISTANT_URL')
        self.homeassistant_token = os.getenv('HOME_ASSISTANT_TOKEN')
        
        # Track last content to avoid unnecessary updates
        self.last_content_hash = None
        self.update_count = 0
        
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
    
    def update_display(self):
        """Update the display with current information"""
        try:
            # Create a new image with white background
            image = Image.new('RGB', (self.width, self.height), 'white')
            draw = ImageDraw.Draw(image)
            
            # Get current time
            now = datetime.now()
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%A, %B %d")
            
            # Draw header
            self.draw_centered_text(draw, 10, time_str, self.font_large, 0)
            self.draw_centered_text(draw, 50, date_str, self.font_medium, 0)
            
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
            
            # Format weather display
            temp_line = f"{temp}{temp_unit}"
            if feels_like != 'N/A' and feels_like != temp:
                temp_line += f" (feels {feels_like}{temp_unit})"
            
            humidity_line = f"Humidity: {humidity}{humidity_unit}"
            wind_line = f"Wind: {wind_speed} {wind_unit}"
            if wind_gust != 'N/A' and wind_gust != wind_speed:
                wind_line += f" (gust {wind_gust})"
            rain_line = f"Rain today: {daily_rain} {rain_unit}"
            
            # Draw weather information
            self.draw_centered_text(draw, 90, temp_line, self.font_large, 0)
            self.draw_centered_text(draw, 130, humidity_line, self.font_medium, 0)
            self.draw_centered_text(draw, 160, wind_line, self.font_medium, 0)
            self.draw_centered_text(draw, 190, rain_line, self.font_medium, 0)
            
            # Create content hash to detect changes
            content_string = f"{time_str}|{date_str}|{temp_line}|{humidity_line}|{wind_line}|{rain_line}"
            import hashlib
            content_hash = hashlib.md5(content_string.encode()).hexdigest()
            
            # Skip update if content hasn't changed (except every 10th update for full refresh)
            if (self.last_content_hash == content_hash and 
                self.update_count % 10 != 0):
                logger.info("Content unchanged, skipping display update")
                return
            
            # Update display
            self.epd.display(self.epd.getbuffer(image))
            self.last_content_hash = content_hash
            self.update_count += 1
            
            logger.info(f"Display updated successfully (update #{self.update_count})")
            
        except Exception as e:
            logger.error(f"Error updating display: {e}")
            
    def run(self):
        """Main loop for the display"""
        logger.info("Starting e-ink display application")
        self.init_display()
        
        # Schedule updates
        schedule.every(5).minutes.do(self.update_display)
        
        # Initial update
        self.update_display()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
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
