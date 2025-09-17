import os
import json
import logging
import requests
import time
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GooglePhotosService:
    """Service for fetching and managing Google Photos for e-ink display"""
    
    # Google Photos API scopes
    # photoslibrary.readonly is not enough for some operations like listing
    # Use the more general scope
    SCOPES = ['https://www.googleapis.com/auth/photoslibrary']
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.album_id = os.getenv('GOOGLE_PHOTOS_ALBUM_ID')
        self.credentials_file = os.getenv('GOOGLE_PHOTOS_CREDENTIALS_FILE', 'credentials.json')
        self.token_file = os.getenv('GOOGLE_PHOTOS_TOKEN_FILE', 'token.json')
        self.photo_cache = []
        self.current_photo_index = 0
        self.last_fetch_time = None
        self.cache_duration = timedelta(hours=1)  # Refresh photo list every hour
        
    def authenticate(self):
        """Authenticate with Google Photos API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    logger.error("Please download your OAuth 2.0 credentials from Google Cloud Console")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                
                # Check if we're in a headless environment
                headless = not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY')
                
                if headless:
                    logger.info("Headless environment detected, using manual authentication")
                    print("\n" + "="*60)
                    print(" GOOGLE PHOTOS AUTHENTICATION REQUIRED")
                    print("="*60)
                    print("Please complete authentication in your web browser:")
                    print("1. Copy the URL that appears below")
                    print("2. Open it in a web browser on any device")
                    print("3. Sign in and authorize the application")
                    print("4. Copy the authorization code and paste it back here")
                    print("="*60 + "\n")
                    
                    try:
                        # Set redirect URI for installed app
                        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                        
                        # Get the authorization URL
                        auth_url, _ = flow.authorization_url(prompt='consent')
                        print(f"Please visit this URL to authorize the application:")
                        print(f"{auth_url}\n")
                        
                        # Get the authorization code from user
                        auth_code = input("Enter the authorization code: ").strip()
                        
                        if not auth_code:
                            logger.error("No authorization code provided")
                            return False
                        
                        print("Exchanging authorization code for credentials...")
                        logger.info("Attempting to exchange authorization code for credentials")
                        
                        # Exchange the code for credentials with timeout
                        import socket
                        original_timeout = socket.getdefaulttimeout()
                        socket.setdefaulttimeout(30)  # 30 second timeout
                        
                        try:
                            # Try to fetch token with detailed error handling
                            flow.fetch_token(code=auth_code)
                            creds = flow.credentials
                            
                            # Verify credentials work
                            if creds and creds.valid:
                                logger.info("Authentication successful with manual mode")
                                print("✓ Authentication successful!")
                            else:
                                logger.error("Credentials are invalid after token exchange")
                                return False
                                
                        except Exception as token_error:
                            logger.error(f"Token exchange failed: {token_error}")
                            print(f"✗ Token exchange failed: {token_error}")
                            
                            # Check if it's a common error
                            if "invalid_grant" in str(token_error):
                                print("The authorization code may have expired or been used already.")
                                print("Please try the authentication process again with a fresh code.")
                            elif "invalid_request" in str(token_error):
                                print("The authorization code format is invalid.")
                                print("Make sure you copied the entire code correctly.")
                            
                            return False
                        finally:
                            socket.setdefaulttimeout(original_timeout)
                    except Exception as e:
                        logger.error(f"Manual authentication failed: {e}")
                        return False
                else:
                    # Try local server with browser
                    try:
                        creds = flow.run_local_server(port=0)
                        logger.info("Authentication successful with browser mode")
                    except Exception as e:
                        logger.warning(f"Browser authentication failed: {e}")
                        logger.info("Falling back to manual authentication...")
                        
                        try:
                            # Set redirect URI for installed app
                            flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                            
                            # Get the authorization URL
                            auth_url, _ = flow.authorization_url(prompt='consent')
                            print(f"\nPlease visit this URL to authorize the application:")
                            print(f"{auth_url}\n")
                            
                            # Get the authorization code from user
                            auth_code = input("Enter the authorization code: ").strip()
                            
                            if not auth_code:
                                logger.error("No authorization code provided")
                                return False
                            
                            print("Exchanging authorization code for credentials...")
                            logger.info("Attempting to exchange authorization code for credentials")
                            
                            # Exchange the code for credentials with timeout
                            import socket
                            original_timeout = socket.getdefaulttimeout()
                            socket.setdefaulttimeout(30)  # 30 second timeout
                            
                            try:
                                flow.fetch_token(code=auth_code)
                                creds = flow.credentials
                                logger.info("Authentication successful with manual fallback mode")
                                print("✓ Authentication successful!")
                            finally:
                                socket.setdefaulttimeout(original_timeout)
                        except Exception as e2:
                            logger.error(f"All authentication methods failed: {e2}")
                            return False
            
            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.credentials = creds
        
        # Build the service with discovery document URL
        try:
            # Try with explicit discovery service URL
            discovery_url = 'https://photoslibrary.googleapis.com/$discovery/rest?version=v1'
            self.service = build('photoslibrary', 'v1', credentials=creds, 
                               discoveryServiceUrl=discovery_url, cache_discovery=False)
            logger.info("Successfully authenticated with Google Photos API")
        except Exception as e:
            logger.warning(f"Failed to build service with discovery URL: {e}")
            # Fallback to direct API calls without discovery
            self.service = None
            logger.info("Will use direct API calls instead of discovery service")
        
        return True
    
    def check_token_info(self):
        """Check token information and scopes"""
        if not self.credentials:
            logger.error("No credentials available")
            return False
        
        try:
            # Check token info
            token_info_url = f"https://oauth2.googleapis.com/tokeninfo?access_token={self.credentials.token}"
            response = requests.get(token_info_url, timeout=10)
            
            if response.status_code == 200:
                token_info = response.json()
                logger.info(f"Token info: {token_info}")
                logger.info(f"Scopes: {token_info.get('scope', 'No scopes found')}")
                return True
            else:
                logger.error(f"Token info request failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error checking token info: {e}")
            return False
    
    def _make_api_request(self, url, method='GET', data=None):
        """Make direct API request when discovery service fails"""
        # Refresh token if needed
        if self.credentials.expired:
            try:
                self.credentials.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}")
                return None
        
        headers = {
            'Authorization': f'Bearer {self.credentials.token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error in API request: {e}")
            if e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response headers: {dict(e.response.headers)}")
                try:
                    error_content = e.response.json()
                    logger.error(f"Response JSON: {error_content}")
                except:
                    logger.error(f"Response text: {e.response.text}")
            else:
                logger.error("No response object available")
            return None
        except Exception as e:
            logger.error(f"Direct API request failed: {e}")
            return None
    
    def get_album_photos(self, album_id=None):
        """Fetch photos from a specific album or all photos if no album specified"""
        if not self.service and not self.credentials:
            if not self.authenticate():
                return []
        
        try:
            photos = []
            page_token = None
            
            if album_id or self.album_id:
                # Get photos from specific album
                target_album_id = album_id or self.album_id
                logger.info(f"Fetching photos from album: {target_album_id}")
                
                while True:
                    request_body = {
                        'albumId': target_album_id,
                        'pageSize': 100
                    }
                    if page_token:
                        request_body['pageToken'] = page_token
                    
                    if self.service:
                        response = self.service.mediaItems().search(body=request_body).execute()
                    else:
                        # Use direct API call
                        url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
                        response = self._make_api_request(url, 'POST', request_body)
                        if not response:
                            break
                    
                    if 'mediaItems' in response:
                        for item in response['mediaItems']:
                            if item.get('mimeType', '').startswith('image/'):
                                photos.append({
                                    'id': item['id'],
                                    'filename': item.get('filename', 'Unknown'),
                                    'baseUrl': item['baseUrl'],
                                    'creationTime': item.get('mediaMetadata', {}).get('creationTime'),
                                    'width': item.get('mediaMetadata', {}).get('width'),
                                    'height': item.get('mediaMetadata', {}).get('height')
                                })
                    
                    page_token = response.get('nextPageToken')
                    if not page_token:
                        break
            else:
                # Get recent photos from library - use mediaItems.list instead of search for recent photos
                logger.info("Fetching recent photos from library")
                
                while True:
                    if self.service:
                        request = self.service.mediaItems().list(pageSize=100)
                        if page_token:
                            request = self.service.mediaItems().list(pageSize=100, pageToken=page_token)
                        response = request.execute()
                    else:
                        # Use direct API call for listing recent photos
                        url = 'https://photoslibrary.googleapis.com/v1/mediaItems'
                        params = {'pageSize': 100}
                        if page_token:
                            params['pageToken'] = page_token
                        
                        # Build URL with parameters
                        param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
                        full_url = f"{url}?{param_string}"
                        response = self._make_api_request(full_url, 'GET')
                        if not response:
                            break
                    
                    if 'mediaItems' in response:
                        for item in response['mediaItems']:
                            photos.append({
                                'id': item['id'],
                                'filename': item.get('filename', 'Unknown'),
                                'baseUrl': item['baseUrl'],
                                'creationTime': item.get('mediaMetadata', {}).get('creationTime'),
                                'width': item.get('mediaMetadata', {}).get('width'),
                                'height': item.get('mediaMetadata', {}).get('height')
                            })
                    
                    page_token = response.get('nextPageToken')
                    if not page_token or len(photos) >= 500:  # Limit to 500 recent photos
                        break
            
            logger.info(f"Found {len(photos)} photos")
            return photos
            
        except HttpError as e:
            logger.error(f"Google Photos API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching photos: {e}")
            return []
    
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
