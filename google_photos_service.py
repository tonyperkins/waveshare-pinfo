import os
import json
import logging
import requests
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GooglePhotosService:
    """Service for fetching and managing Google Photos for e-ink display using the Picker API flow."""
    
    # The only scope needed is for sharing, used by the Picker setup to get a shareable album.
    SCOPES = ['https://www.googleapis.com/auth/photoslibrary.sharing']

    def __init__(self):
        self.credentials = None
        self.share_token = os.getenv('GOOGLE_PHOTOS_SHARE_TOKEN')
        self.token_file = os.getenv('GOOGLE_PHOTOS_TOKEN_FILE', 'token.json')
        self.photo_cache = []
        self.current_photo_index = -1 # Start at -1 to get the first photo on the first call
        self.last_fetch_time = None
        self.cache_duration = timedelta(hours=1)

    def authenticate(self):
        """Loads API credentials from token.json. Does not handle interactive login."""
        if not self.share_token:
            logger.error("FATAL: Missing GOOGLE_PHOTOS_SHARE_TOKEN in your .env file.")
            logger.error("Please run 'python setup_web.py' to select an album and get your token.")
            return False

        if not os.path.exists(self.token_file):
            logger.error(f"FATAL: Token file '{self.token_file}' not found.")
            logger.error("Please run 'python setup_web.py' to authenticate and create the token file.")
            return False
        
        try:
            self.credentials = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
            if self.credentials.expired and self.credentials.refresh_token:
                logger.info("Refreshing expired token...")
                self.credentials.refresh(Request())
            logger.info("Authentication successful.")
            return True
        except Exception as e:
            logger.error(f"Failed to load or refresh token: {e}")
            return False

    def refresh_photo_cache(self):
        """Refreshes the photo cache from the shared album using the shareToken."""
        if not self.credentials or not self.credentials.token:
            logger.error("Not authenticated. Cannot refresh photo cache.")
            return

        logger.info("Refreshing photo cache from shared album...")
        try:
            headers = {'Authorization': f'Bearer {self.credentials.token}'}
            url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
            body = {
                "pageSize": 100,
                "shareToken": self.share_token
            }
            
            response = requests.post(url, headers=headers, json=body, timeout=30)

            if response.status_code == 200:
                photos = response.json().get('mediaItems', [])
                self.photo_cache = [p for p in photos if 'image' in p.get('mediaMetadata', {})]
                logger.info(f"Found {len(self.photo_cache)} photos in the shared album.")
            else:
                logger.error(f"API request failed: {response.status_code} {response.reason}")
                logger.error(f"Response: {response.text}")
                if response.status_code in [401, 403]:
                    logger.error("Your authentication token may be invalid. Please delete 'token.json' and run 'python setup_web.py' again.")

        except requests.exceptions.RequestException as e:
            logger.error(f"An unexpected error occurred during photo refresh: {e}")

    def get_photo(self):
        """Gets the next photo from the cache, refreshing if necessary."""
        now = datetime.now()
        if not self.photo_cache or (self.last_fetch_time and now - self.last_fetch_time > self.cache_duration):
            self.refresh_photo_cache()
            self.last_fetch_time = now

        if not self.photo_cache:
            logger.warning("Photo cache is empty. No photos to display.")
            return None, None

        # Rotate through the photos
        self.current_photo_index = (self.current_photo_index + 1) % len(self.photo_cache)
        photo_info = self.photo_cache[self.current_photo_index]
        
        # E-ink display dimensions (800x480 for 7.5 inch display)
        base_url = photo_info['baseUrl']
        image_url = f"{base_url}=w800-h480"

        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return response.content, photo_info
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image: {e}")
            return None, None

    def list_albums(self):
        """List available albums"""
        if not self.service and not self.credentials:
            if not self.authenticate():
                return []
        
        try:
            albums = []
            page_token = None
            
            while True:
                if self.service:
                    request = self.service.albums().list(pageSize=50)
                    if page_token:
                        request = self.service.albums().list(pageSize=50, pageToken=page_token)
                    response = request.execute()
                else:
                    # Use direct API call
                    url = 'https://photoslibrary.googleapis.com/v1/albums'
                    params = {'pageSize': 50}
                    if page_token:
                        params['pageToken'] = page_token
                    response = self._make_api_request(f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}")
                    if not response:
                        break
                
                if 'albums' in response:
                    for album in response['albums']:
                        albums.append({
                            'id': album['id'],
                            'title': album.get('title', 'Untitled'),
                            'mediaItemsCount': album.get('mediaItemsCount', 0),
                            'coverPhotoBaseUrl': album.get('coverPhotoBaseUrl')
                        })
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Found {len(albums)} albums")
            for album in albums:
                logger.info(f"Album: {album['title']} (ID: {album['id']}, Photos: {album['mediaItemsCount']})")
            
            return albums
            
        except HttpError as e:
            logger.error(f"Google Photos API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching albums: {e}")
            return []
    
    def refresh_photo_cache(self):
        """Refresh the photo cache if needed"""
        now = datetime.now()
        
        if (not self.last_fetch_time or 
            now - self.last_fetch_time > self.cache_duration or 
            not self.photo_cache):
            
            logger.info("Refreshing photo cache...")
            self.photo_cache = self.get_album_photos()
            self.last_fetch_time = now
            
            if self.photo_cache:
                # Shuffle photos for variety
                import random
                random.shuffle(self.photo_cache)
                logger.info(f"Photo cache refreshed with {len(self.photo_cache)} photos")
            else:
                logger.warning("No photos found in cache refresh")
    
    def get_next_photo(self):
        """Get the next photo in rotation"""
        self.refresh_photo_cache()
        
        if not self.photo_cache:
            logger.warning("No photos available")
            return None
        
        photo = self.photo_cache[self.current_photo_index]
        self.current_photo_index = (self.current_photo_index + 1) % len(self.photo_cache)
        
        return photo
    
    def download_photo(self, photo_info, max_width=640, max_height=400):
        """Download and process photo for e-ink display"""
        try:
            # Construct download URL with size parameters
            download_url = f"{photo_info['baseUrl']}=w{max_width}-h{max_height}"
            
            logger.info(f"Downloading photo: {photo_info['filename']}")
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            # Open image from bytes
            image = Image.open(io.BytesIO(response.content))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            logger.info(f"Downloaded photo: {image.size}")
            return image
            
        except Exception as e:
            logger.error(f"Error downloading photo {photo_info['filename']}: {e}")
            return None
    
    def process_image_for_eink(self, image, target_width=640, target_height=400):
        """Process image for optimal e-ink display"""
        try:
            # Calculate aspect ratios
            img_ratio = image.width / image.height
            target_ratio = target_width / target_height
            
            # Resize image to fit within target dimensions while maintaining aspect ratio
            if img_ratio > target_ratio:
                # Image is wider than target
                new_width = target_width
                new_height = int(target_width / img_ratio)
            else:
                # Image is taller than target
                new_height = target_height
                new_width = int(target_height * img_ratio)
            
            # Resize image
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create new image with white background
            final_image = Image.new('RGB', (target_width, target_height), 'white')
            
            # Center the resized image
            x_offset = (target_width - new_width) // 2
            y_offset = (target_height - new_height) // 2
            final_image.paste(resized_image, (x_offset, y_offset))
            
            # Convert to grayscale for better e-ink display
            final_image = final_image.convert('L')
            
            # Enhance contrast for e-ink
            final_image = ImageOps.autocontrast(final_image, cutoff=2)
            
            # Convert back to RGB for compatibility
            final_image = final_image.convert('RGB')
            
            logger.info(f"Processed image for e-ink: {final_image.size}")
            return final_image
            
        except Exception as e:
            logger.error(f"Error processing image for e-ink: {e}")
            return None
