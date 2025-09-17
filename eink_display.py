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
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%A, %B %d")
            
            # === HEADER SECTION ===
            # Draw main border around entire display
            self.draw_section_box(draw, 5, 5, self.width - 10, self.height - 10, 0, 3)
            
            # Draw time prominently in header
            self.draw_centered_text(draw, 15, time_str, self.font_xlarge, 0)
            self.draw_centered_text(draw, 65, date_str, self.font_small, 0)
            
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
            temp_section_height = 120
            
            # Draw temperature section box
            self.draw_section_box(draw, margin, temp_section_y, self.width - 2*margin, temp_section_height, 0, 2)
            
            # Get weather icon
            weather_icon = self.get_weather_icon(temp, humidity, wind_speed, daily_rain)
            
            # Draw large temperature with icon
            temp_line = f"{temp}{temp_unit}"
            temp_with_icon = f"{weather_icon} {temp_line}"
            self.draw_centered_text(draw, temp_section_y + 25, temp_with_icon, self.font_xlarge, 0)
            
            # Draw "feels like" if different
            if feels_like != 'N/A' and feels_like != temp:
                feels_line = f"Feels like {feels_like}{temp_unit}"
                self.draw_centered_text(draw, temp_section_y + 80, feels_line, self.font_tiny, 0)
            
            # === WEATHER DETAILS SECTION ===
            details_section_y = temp_section_y + temp_section_height + 15
            details_section_height = self.height - details_section_y - 20
            
            # Draw details section box
            self.draw_section_box(draw, margin, details_section_y, self.width - 2*margin, details_section_height, 0, 2)
            
            # Two-column layout for weather details
            left_col_x = margin + 20
            right_col_x = self.width // 2 + 10
            detail_y_start = details_section_y + 20
            line_height = 35
            
            # Left column - Humidity and Wind
            self.draw_left_aligned_text(draw, left_col_x, detail_y_start, "💧 HUMIDITY", self.font_tiny, 0)
            self.draw_left_aligned_text(draw, left_col_x, detail_y_start + 20, f"{humidity}{humidity_unit}", self.font_medium, 0)
            
            wind_display = f"{wind_speed} {wind_unit}"
            if wind_gust != 'N/A' and wind_gust != wind_speed:
                wind_display += f"\nGusts: {wind_gust} {wind_unit}"
            
            self.draw_left_aligned_text(draw, left_col_x, detail_y_start + line_height + 20, "💨 WIND", self.font_tiny, 0)
            wind_lines = wind_display.split('\n')
            for i, line in enumerate(wind_lines):
                self.draw_left_aligned_text(draw, left_col_x, detail_y_start + line_height + 40 + (i * 25), line, self.font_medium, 0)
            
            # Right column - Rain and additional info
            self.draw_left_aligned_text(draw, right_col_x, detail_y_start, "🌧 RAIN TODAY", self.font_tiny, 0)
            self.draw_left_aligned_text(draw, right_col_x, detail_y_start + 20, f"{daily_rain} {rain_unit}", self.font_medium, 0)
            
            # Add update time at bottom
            update_time = now.strftime("%I:%M %p")
            self.draw_centered_text(draw, self.height - 35, f"Updated: {update_time}", self.font_tiny, 0)
            
            # Create content hash to detect changes
            content_string = f"{time_str}|{date_str}|{temp_line}|{humidity}|{wind_speed}|{daily_rain}|{feels_like}"
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
