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
        self.font_small = ImageFont.truetype('DejaVuSans-Bold.ttf', 18)
        self.font_medium = ImageFont.truetype('DejaVuSans-Bold.ttf', 24)
        self.font_large = ImageFont.truetype('DejaVuSans-Bold.ttf', 32)
        self.homeassistant_url = os.getenv('HOME_ASSISTANT_URL')
        self.homeassistant_token = os.getenv('HOME_ASSISTANT_TOKEN')
        
    def init_display(self):
        """Initialize the e-ink display"""
        logger.info("Initializing e-ink display...")
        self.epd.init()
        self.clear_display()
        
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
            
            # Example: Get weather from Home Assistant
            weather = self.get_homeassistant_entity("weather.home")
            if weather:
                temp = weather.get('attributes', {}).get('temperature', 'N/A')
                condition = weather.get('state', 'Unknown')
                weather_text = f"{temp}°C • {condition}"
                self.draw_centered_text(draw, 100, weather_text, self.font_medium, 0)
            
            # Convert to 7-color format and display
            self.epd.display(self.epd.getbuffer(image))
            logger.info("Display updated successfully")
            
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
