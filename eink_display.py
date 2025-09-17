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
            self.font_large_details = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)  # 80% of xlarge
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            self.font_humidity = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)  # 70% of xlarge
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
            self.font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except OSError:
            # Fallback to default fonts if system fonts not available
            self.font_xlarge = ImageFont.load_default()
            self.font_large_details = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.font_humidity = ImageFont.load_default()
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
        self.last_partial_update_time = 0  # Track last partial update for 180s minimum interval
        
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
        """Time update every 10 minutes - respects 180-second minimum interval"""
        try:
            now = datetime.now()
            current_minute = now.strftime("%I:%M %p")
            current_time = time.time()
            
            # Only check for updates every 10 minutes (when minute ends in 0)
            if now.minute % 10 != 0:
                return
                
            # Only update if the time has actually changed to a 10-minute mark
            if self.last_minute == current_minute:
                return
            
            # Check 180-second minimum interval (Waveshare requirement)
            time_since_last_update = current_time - self.last_partial_update_time
            if time_since_last_update < 180:
                logger.info(f"Skipping time update - only {time_since_last_update:.1f}s since last update (need 180s minimum)")
                return
            
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%A, %B %d")
            
            # Since partial updates aren't supported, do a full display update every 10 minutes
            logger.info(f"Time update triggered (every 10 minutes): {time_str}")
            
            # Update tracking variables
            self.last_minute = current_minute
            self.last_partial_update_time = current_time
            
            # Trigger a full display update
            self.update_display()
            
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
            header_height = 50  # Reduced from 70
            main_section_y = header_height + 20
            
            # Get current time
            now = datetime.now()
            time_str = now.strftime("%I:%M %p")  # 12-hour format with AM/PM
            date_str = now.strftime("%A, %B %d")
            update_time = now.strftime("%I:%M %p")
            
            # === HEADER SECTION ===
            # Draw main border around entire display
            self.draw_section_box(draw, 5, 5, self.width - 10, self.height - 10, 0, 3)
            
            # Draw "Updated" with time and date
            self.draw_left_aligned_text(draw, 20, 15, "Updated", self.font_tiny, 0)
            self.draw_left_aligned_text(draw, 20, 35, f"{time_str} {date_str}", self.font_medium, 0)
            
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
            temp_section_height = 80  # Reduced since no icon
            
            # Draw temperature section box
            self.draw_section_box(draw, margin, temp_section_y, self.width - 2*margin, temp_section_height, 0, 2)
            
            # Draw temperature and feels-like side by side (no humidity here)
            temp_line = f"{temp}{temp_unit}"
            feels_line = f"{feels_like}{temp_unit}" if feels_like != 'N/A' else f"{temp}{temp_unit}"
            
            # Calculate positions for two-column layout
            quarter_width = self.width // 4
            temp_x = quarter_width
            feels_x = 3 * quarter_width
            
            # Only show feels-like if it's different and available
            if feels_like != 'N/A' and feels_like != temp:
                # Draw temperature on left side (adjusted for no icon)
                temp_width = draw.textlength(temp_line, font=self.font_xlarge)
                temp_start_x = temp_x - temp_width // 2
                self.draw_left_aligned_text(draw, temp_start_x, temp_section_y + 45, temp_line, self.font_xlarge, 0)
                
                # Draw feels-like on right side (adjusted for no icon)
                feels_width = draw.textlength(feels_line, font=self.font_xlarge)
                feels_start_x = feels_x - feels_width // 2
                self.draw_left_aligned_text(draw, feels_start_x, temp_section_y + 45, feels_line, self.font_xlarge, 0)
                
                # Add labels (adjusted spacing)
                temp_label_width = draw.textlength("ACTUAL", font=self.font_tiny)
                temp_label_x = temp_x - temp_label_width // 2
                self.draw_left_aligned_text(draw, temp_label_x, temp_section_y + 15, "ACTUAL", self.font_tiny, 0)
                
                feels_label_width = draw.textlength("FEELS LIKE", font=self.font_tiny)
                feels_label_x = feels_x - feels_label_width // 2
                self.draw_left_aligned_text(draw, feels_label_x, temp_section_y + 15, "FEELS LIKE", self.font_tiny, 0)
            else:
                # Just show the single temperature centered (adjusted for no icon)
                self.draw_centered_text(draw, temp_section_y + 45, temp_line, self.font_xlarge, 0)
            
            # === WIND SECTION ===
            wind_section_y = temp_section_y + temp_section_height + 15
            wind_section_height = 80  # Increased for better spacing
            
            # Draw wind section box
            self.draw_section_box(draw, margin, wind_section_y, self.width - 2*margin, wind_section_height, 0, 2)
            
            # Format wind display as x.x / y.y mph
            if wind_gust != 'N/A' and wind_gust != wind_speed:
                # Two column layout for wind and gust
                wind_x = self.width // 4
                gust_x = 3 * self.width // 4
                
                # Draw wind speed
                wind_value = f"{wind_speed} {wind_unit}"
                wind_width = draw.textlength(wind_value, font=self.font_large_details)
                wind_start_x = wind_x - wind_width // 2
                self.draw_left_aligned_text(draw, wind_start_x, wind_section_y + 45, wind_value, self.font_large_details, 0)
                
                # Draw gust speed
                gust_value = f"{wind_gust} {wind_unit}"
                gust_width = draw.textlength(gust_value, font=self.font_large_details)
                gust_start_x = gust_x - gust_width // 2
                self.draw_left_aligned_text(draw, gust_start_x, wind_section_y + 45, gust_value, self.font_large_details, 0)
                
                # Add labels
                wind_label_width = draw.textlength("WIND", font=self.font_tiny)
                wind_label_x = wind_x - wind_label_width // 2
                self.draw_left_aligned_text(draw, wind_label_x, wind_section_y + 15, "WIND", self.font_tiny, 0)
                
                gust_label_width = draw.textlength("GUST", font=self.font_tiny)
                gust_label_x = gust_x - gust_label_width // 2
                self.draw_left_aligned_text(draw, gust_label_x, wind_section_y + 15, "GUST", self.font_tiny, 0)
            else:
                # Single wind value centered
                wind_value = f"{wind_speed} {wind_unit}"
                self.draw_centered_text(draw, wind_section_y + 45, wind_value, self.font_large_details, 0)
                
                # Add label
                self.draw_centered_text(draw, wind_section_y + 15, "WIND", self.font_tiny, 0)
            
            # === RAIN AND HUMIDITY SECTION ===
            rain_section_y = wind_section_y + wind_section_height + 15
            rain_section_height = 80  # Increased for better spacing
            
            # Draw rain/humidity section box
            self.draw_section_box(draw, margin, rain_section_y, self.width - 2*margin, rain_section_height, 0, 2)
            
            # Two column layout for rain and humidity
            rain_x = self.width // 4
            humidity_x = 3 * self.width // 4
            
            # Draw rain value
            rain_value = f"{daily_rain} {rain_unit}"
            rain_width = draw.textlength(rain_value, font=self.font_large_details)
            rain_start_x = rain_x - rain_width // 2
            self.draw_left_aligned_text(draw, rain_start_x, rain_section_y + 45, rain_value, self.font_large_details, 0)
            
            # Draw humidity value
            humidity_value = f"{humidity}%"
            humidity_width = draw.textlength(humidity_value, font=self.font_large_details)
            humidity_start_x = humidity_x - humidity_width // 2
            self.draw_left_aligned_text(draw, humidity_start_x, rain_section_y + 45, humidity_value, self.font_large_details, 0)
            
            # Add labels
            rain_label_width = draw.textlength("RAIN", font=self.font_tiny)
            rain_label_x = rain_x - rain_label_width // 2
            self.draw_left_aligned_text(draw, rain_label_x, rain_section_y + 15, "RAIN", self.font_tiny, 0)
            
            humidity_label_width = draw.textlength("HUMIDITY", font=self.font_tiny)
            humidity_label_x = humidity_x - humidity_label_width // 2
            self.draw_left_aligned_text(draw, humidity_label_x, rain_section_y + 15, "HUMIDITY", self.font_tiny, 0)
            
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
