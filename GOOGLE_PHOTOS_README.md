# Google Photos E-ink Display Integration

This service displays photos from your Google Photos library on a Waveshare e-ink display, automatically rotating through images at configurable intervals.

## Features

- **Automatic Photo Rotation**: Cycles through photos from your Google Photos library
- **Album Support**: Display photos from specific albums or recent photos
- **E-ink Optimized**: Images are processed for optimal display on e-ink screens
- **Metadata Display**: Shows photo filename, date, and last update time
- **Caching**: Intelligent caching to minimize API calls
- **Error Handling**: Graceful error handling with informative display messages
- **Systemd Integration**: Can run as a system service

## Prerequisites

1. **Hardware**: Waveshare 4.01" e-ink display
2. **Google Cloud Project**: With Photos Library API enabled
3. **OAuth 2.0 Credentials**: Desktop application credentials from Google Cloud Console

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Photos Library API**:
   - Go to APIs & Services > Library
   - Search for "Photos Library API"
   - Click on it and press "Enable"
4. Create OAuth 2.0 credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Give it a name (e.g., "E-ink Photo Display")
   - Click "Create"
5. Download the credentials JSON file and save it as `credentials.json` in this directory

### 3. Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure your settings:
   ```bash
   # Optional: Specific album ID (leave empty to use recent photos)
   GOOGLE_PHOTOS_ALBUM_ID=your_album_id_here
   
   # Photo rotation interval in minutes
   PHOTO_ROTATION_INTERVAL_MINUTES=30
   
   # Credentials files (usually don't need to change)
   GOOGLE_PHOTOS_CREDENTIALS_FILE=credentials.json
   GOOGLE_PHOTOS_TOKEN_FILE=token.json
   ```

### 4. Initial Setup and Testing

Use the setup script to configure and test your integration:

```bash
# Show detailed setup instructions
python setup_google_photos.py instructions

# Test authentication and photo fetching
python setup_google_photos.py test

# List available albums and select one
python setup_google_photos.py albums
```

### 5. First Run

Run the photo display service:

```bash
python photo_display_service.py
```

On first run, it will:
1. Open a web browser for Google authentication
2. Ask you to sign in and grant permissions
3. Save authentication tokens for future use
4. Start displaying photos

## Usage

### Running the Service

```bash
# Run interactively
python photo_display_service.py

# List available albums
python photo_display_service.py list-albums

# Test authentication only
python photo_display_service.py test-auth
```

### Installing as System Service

1. Copy the service file:
   ```bash
   sudo cp photo-display.service /etc/systemd/system/
   ```

2. Update the service file paths if needed:
   ```bash
   sudo nano /etc/systemd/system/photo-display.service
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable photo-display.service
   sudo systemctl start photo-display.service
   ```

4. Check service status:
   ```bash
   sudo systemctl status photo-display.service
   ```

5. View logs:
   ```bash
   sudo journalctl -u photo-display.service -f
   ```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_PHOTOS_ALBUM_ID` | Specific album ID to display photos from | None (uses recent photos) |
| `PHOTO_ROTATION_INTERVAL_MINUTES` | Minutes between photo changes | 30 |
| `GOOGLE_PHOTOS_CREDENTIALS_FILE` | Path to OAuth credentials JSON | credentials.json |
| `GOOGLE_PHOTOS_TOKEN_FILE` | Path to store auth tokens | token.json |

### Photo Selection

- **No Album ID**: Displays recent photos from your entire library (up to 500 most recent)
- **With Album ID**: Displays photos from the specified album only
- **Randomization**: Photos are shuffled for variety

### Display Behavior

- **Photo Processing**: Images are automatically resized and optimized for e-ink display
- **Metadata**: Shows filename, creation date, and last update time
- **Error Handling**: Displays informative error messages if photos can't be loaded
- **Caching**: Photo list is cached for 1 hour to reduce API calls

## Troubleshooting

### Authentication Issues

1. **"Credentials file not found"**:
   - Ensure `credentials.json` is in the correct location
   - Check the `GOOGLE_PHOTOS_CREDENTIALS_FILE` environment variable

2. **"Authentication failed"**:
   - Delete `token.json` and re-authenticate
   - Check that Photos Library API is enabled in Google Cloud Console
   - Verify OAuth 2.0 credentials are for "Desktop application"

3. **"Access denied"**:
   - Make sure you granted all requested permissions during authentication
   - Check that your Google account has access to Google Photos

### Photo Loading Issues

1. **"No photos available"**:
   - Check that your Google Photos library has photos
   - If using an album ID, verify the album exists and has photos
   - Run `python setup_google_photos.py albums` to list available albums

2. **"Failed to download photo"**:
   - Check internet connection
   - Photos may be too large or in unsupported format
   - Check logs for specific error messages

3. **"Failed to process photo"**:
   - Image processing error, usually due to corrupted or unsupported image format
   - Check logs for specific PIL/image processing errors

### Display Issues

1. **Display not updating**:
   - Check e-ink display connections
   - Verify display initialization in logs
   - Check GPIO permissions (may need to run as root or add user to gpio group)

2. **Poor image quality**:
   - E-ink displays have limited color depth and resolution
   - Images are automatically processed for optimal e-ink display
   - Try different photos or adjust processing parameters

### Service Issues

1. **Service won't start**:
   - Check service file paths are correct
   - Verify all dependencies are installed
   - Check logs: `sudo journalctl -u photo-display.service`

2. **Service stops unexpectedly**:
   - Check for authentication token expiration
   - Review error logs for specific issues
   - Ensure stable internet connection

## API Limits and Considerations

- **Google Photos API**: Has daily quotas and rate limits
- **Caching**: The service caches photo lists to minimize API calls
- **Token Refresh**: Authentication tokens are automatically refreshed
- **Offline Mode**: Service will show error messages if API is unavailable

## File Structure

```
waveshare-pinfo/
├── google_photos_service.py      # Google Photos API integration
├── photo_display_service.py      # Main photo display service
├── setup_google_photos.py        # Setup and configuration script
├── photo-display.service         # Systemd service file
├── credentials.json              # OAuth 2.0 credentials (you provide)
├── token.json                    # Authentication tokens (auto-generated)
├── .env                          # Environment configuration
└── GOOGLE_PHOTOS_README.md       # This file
```

## Security Notes

- **Credentials**: Keep `credentials.json` and `token.json` secure
- **Permissions**: The service only requests read-only access to your photos
- **Local Storage**: No photos are permanently stored locally
- **Network**: All communication uses HTTPS

## Support

For issues specific to this integration:
1. Check the troubleshooting section above
2. Review service logs for error messages
3. Test authentication and photo fetching with the setup script
4. Ensure all prerequisites are met

For Google Photos API issues:
- [Google Photos Library API Documentation](https://developers.google.com/photos/library/guides/overview)
- [Google Cloud Console](https://console.cloud.google.com/)

## License

This integration follows the same license as the main project.
