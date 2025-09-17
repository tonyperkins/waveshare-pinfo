#!/usr/bin/env python3
"""
Setup script for Google Photos integration with e-ink display.
This script helps configure Google Photos API credentials and test the connection.
"""

import os
import sys
import json
from google_photos_service import GooglePhotosService
from dotenv import load_dotenv

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_step(step_num, description):
    """Print a formatted step"""
    print(f"\nStep {step_num}: {description}")
    print("-" * 40)

def check_credentials_file():
    """Check if credentials.json exists"""
    creds_file = os.getenv('GOOGLE_PHOTOS_CREDENTIALS_FILE', 'credentials.json')
    
    if os.path.exists(creds_file):
        print(f"✓ Found credentials file: {creds_file}")
        return True
    else:
        print(f"✗ Credentials file not found: {creds_file}")
        return False

def setup_instructions():
    """Print setup instructions"""
    print_header("Google Photos API Setup Instructions")
    
    print("""
To use Google Photos with your e-ink display, you need to:

1. Go to the Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Photos Library API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials JSON file
6. Place it in this directory as 'credentials.json'

Detailed steps:
""")
    
    print_step(1, "Create/Select Google Cloud Project")
    print("- Go to https://console.cloud.google.com/")
    print("- Create a new project or select existing one")
    
    print_step(2, "Enable Photos Library API")
    print("- Go to APIs & Services > Library")
    print("- Search for 'Photos Library API'")
    print("- Click on it and press 'Enable'")
    
    print_step(3, "Create OAuth 2.0 Credentials")
    print("- Go to APIs & Services > Credentials")
    print("- Click 'Create Credentials' > 'OAuth 2.0 Client IDs'")
    print("- Choose 'Desktop application'")
    print("- Give it a name (e.g., 'E-ink Photo Display')")
    print("- Click 'Create'")
    
    print_step(4, "Download Credentials")
    print("- Click the download button for your new credentials")
    print("- Save the file as 'credentials.json' in this directory")
    print(f"- Full path should be: {os.path.abspath('credentials.json')}")
    
    print_step(5, "Configure Environment")
    print("- Copy .env.example to .env")
    print("- Edit .env and set your album ID (optional)")
    print("- If no album ID is set, recent photos will be used")

def test_authentication():
    """Test Google Photos authentication"""
    print_header("Testing Google Photos Authentication")
    
    service = GooglePhotosService()
    
    print("Attempting to authenticate with Google Photos...")
    print("Note: If you're in a headless environment (no GUI), you'll need to:")
    print("1. Copy the authentication URL to a browser on another device")
    print("2. Complete the authentication process")
    print("3. Copy the authorization code back to this terminal")
    print()
    
    if service.authenticate():
        print("✓ Authentication successful!")
        return service
    else:
        print("✗ Authentication failed!")
        print("\nTroubleshooting tips:")
        print("- Make sure credentials.json is valid")
        print("- Check that Photos Library API is enabled")
        print("- Verify your Google account has access to Google Photos")
        return None

def list_albums(service):
    """List available albums"""
    print_header("Available Google Photos Albums")
    
    albums = service.list_albums()
    
    if not albums:
        print("No albums found or unable to fetch albums.")
        return
    
    print(f"Found {len(albums)} albums:\n")
    
    for i, album in enumerate(albums, 1):
        print(f"{i:2d}. {album['title']}")
        print(f"    ID: {album['id']}")
        print(f"    Photos: {album['mediaItemsCount']}")
        print()
    
    # Ask user if they want to set an album ID
    try:
        choice = input("Enter album number to use (or press Enter to use recent photos): ").strip()
        
        if choice and choice.isdigit():
            album_num = int(choice) - 1
            if 0 <= album_num < len(albums):
                selected_album = albums[album_num]
                print(f"\nSelected album: {selected_album['title']}")
                print(f"Album ID: {selected_album['id']}")
                
                # Update .env file
                update_env_file(selected_album['id'])
            else:
                print("Invalid album number.")
        else:
            print("No album selected. Will use recent photos.")
            
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
    except Exception as e:
        print(f"Error: {e}")

def update_env_file(album_id):
    """Update .env file with album ID"""
    env_file = '.env'
    
    # Read existing .env or create from example
    if not os.path.exists(env_file):
        if os.path.exists('.env.example'):
            with open('.env.example', 'r') as f:
                content = f.read()
        else:
            content = ""
    else:
        with open(env_file, 'r') as f:
            content = f.read()
    
    # Update or add album ID
    lines = content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith('GOOGLE_PHOTOS_ALBUM_ID='):
            lines[i] = f'GOOGLE_PHOTOS_ALBUM_ID={album_id}'
            updated = True
            break
    
    if not updated:
        lines.append(f'GOOGLE_PHOTOS_ALBUM_ID={album_id}')
    
    # Write back to .env
    with open(env_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"✓ Updated {env_file} with album ID")

def test_photo_fetch(service):
    """Test fetching a photo"""
    print_header("Testing Photo Fetch")
    
    print("Fetching a test photo...")
    photo = service.get_next_photo()
    
    if photo:
        print("✓ Successfully fetched photo:")
        print(f"  Filename: {photo.get('filename', 'Unknown')}")
        print(f"  ID: {photo.get('id', 'Unknown')}")
        print(f"  Creation time: {photo.get('creationTime', 'Unknown')}")
        
        # Test download
        print("\nTesting photo download...")
        image = service.download_photo(photo, 400, 300)
        
        if image:
            print(f"✓ Successfully downloaded photo: {image.size}")
            
            # Test processing
            print("Testing image processing for e-ink...")
            processed = service.process_image_for_eink(image, 640, 400)
            
            if processed:
                print(f"✓ Successfully processed image: {processed.size}")
            else:
                print("✗ Failed to process image")
        else:
            print("✗ Failed to download photo")
    else:
        print("✗ Failed to fetch photo")

def main():
    """Main setup function"""
    load_dotenv()
    
    print_header("Google Photos E-ink Display Setup")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "instructions":
            setup_instructions()
            return
        elif command == "test":
            if not check_credentials_file():
                print("\nPlease run 'python setup_google_photos.py instructions' first.")
                return
            
            service = test_authentication()
            if service:
                test_photo_fetch(service)
            return
        elif command == "albums":
            if not check_credentials_file():
                print("\nPlease run 'python setup_google_photos.py instructions' first.")
                return
            
            service = test_authentication()
            if service:
                list_albums(service)
            return
    
    # Interactive setup
    print("Welcome to the Google Photos e-ink display setup!")
    print("\nThis script will help you configure Google Photos integration.")
    
    # Check if credentials exist
    if not check_credentials_file():
        print("\n" + "!"*60)
        print("SETUP REQUIRED: Google Photos API credentials not found!")
        print("!"*60)
        setup_instructions()
        return
    
    # Test authentication
    service = test_authentication()
    if not service:
        print("\nAuthentication failed. Please check your credentials.")
        return
    
    # List albums and let user choose
    list_albums(service)
    
    # Test photo fetch
    test_photo_fetch(service)
    
    print_header("Setup Complete!")
    print("Your Google Photos integration is ready!")
    print("\nTo start the photo display service:")
    print("  python photo_display_service.py")
    print("\nTo install as a system service:")
    print("  sudo cp photo-display.service /etc/systemd/system/")
    print("  sudo systemctl enable photo-display.service")
    print("  sudo systemctl start photo-display.service")

if __name__ == "__main__":
    main()
