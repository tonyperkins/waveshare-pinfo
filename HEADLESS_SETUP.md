# Headless Google Photos E-ink Display Setup

This guide will help you set up your Raspberry Pi to automatically display Google Photos on the e-ink display when it boots up, without any user interaction.

## Prerequisites

1. **Raspberry Pi** with Raspbian/Raspberry Pi OS
2. **Waveshare e-ink display** properly connected
3. **Internet connection** for the Pi
4. **Google Cloud Project** with Photos Library API enabled
5. **OAuth 2.0 credentials** downloaded as `credentials.json`

## Step-by-Step Setup

### 1. Initial Authentication (One-Time Setup)

Since OAuth requires interactive authentication the first time, you need to do this once:

```bash
# Navigate to your project directory
cd /opt/waveshare-pinfo

# Activate virtual environment
source .venv/bin/activate

# Run authentication setup
python setup_google_photos.py test
```

This will:
- Give you a URL to open in any browser (phone, computer, etc.)
- Ask you to sign in to Google and authorize the app
- Save authentication tokens to `token.json`

### 2. Configure for Headless Operation

Run the headless configuration script:

```bash
python configure_headless.py
```

This script will:
- ✅ Check that all required files exist
- ✅ Verify authentication is working
- ✅ Set up environment configuration
- ✅ Install the systemd service
- ✅ Test the service
- ✅ Start the service

### 3. Alternative Manual Setup

If you prefer to set up manually:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit configuration (optional)
nano .env

# 3. Install service
sudo cp photo-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable photo-display.service

# 4. Start service
sudo systemctl start photo-display.service
```

## Configuration Options

Edit `.env` file to customize behavior:

```bash
# Specific album to display (optional - leave empty for recent photos)
GOOGLE_PHOTOS_ALBUM_ID=your_album_id_here

# How often to change photos (in minutes)
PHOTO_ROTATION_INTERVAL_MINUTES=30

# Credential files (usually don't need to change)
GOOGLE_PHOTOS_CREDENTIALS_FILE=credentials.json
GOOGLE_PHOTOS_TOKEN_FILE=token.json
```

### Finding Album IDs

To display photos from a specific album:

```bash
python setup_google_photos.py albums
```

This will list all your albums with their IDs. Copy the ID of the album you want to use.

## Service Management

Once set up, use these commands to manage the service:

```bash
# Check if service is running
sudo systemctl status photo-display.service

# View live logs
sudo journalctl -u photo-display.service -f

# Stop the service
sudo systemctl stop photo-display.service

# Start the service
sudo systemctl start photo-display.service

# Restart the service
sudo systemctl restart photo-display.service

# Disable auto-start on boot
sudo systemctl disable photo-display.service

# Re-enable auto-start on boot
sudo systemctl enable photo-display.service
```

## Troubleshooting

### Service Won't Start

1. **Check logs**:
   ```bash
   sudo journalctl -u photo-display.service --since "1 hour ago"
   ```

2. **Test authentication**:
   ```bash
   python setup_google_photos.py test
   ```

3. **Check file permissions**:
   ```bash
   ls -la credentials.json token.json
   # Should be readable by the pi user
   ```

### Authentication Issues

1. **Token expired**: Delete `token.json` and re-authenticate:
   ```bash
   rm token.json
   python setup_google_photos.py test
   ```

2. **Credentials invalid**: Re-download `credentials.json` from Google Cloud Console

3. **API not enabled**: Ensure Photos Library API is enabled in Google Cloud Console

### Display Issues

1. **Check display connection**: Ensure e-ink display is properly connected
2. **GPIO permissions**: User may need to be in `gpio` group:
   ```bash
   sudo usermod -a -G gpio pi
   ```

3. **Run as root**: If GPIO issues persist, modify service to run as root:
   ```bash
   sudo nano /etc/systemd/system/photo-display.service
   # Change User=pi to User=root
   sudo systemctl daemon-reload
   sudo systemctl restart photo-display.service
   ```

### Network Issues

1. **Check internet connection**:
   ```bash
   ping google.com
   ```

2. **DNS issues**: Add to `/etc/systemd/resolved.conf`:
   ```
   DNS=8.8.8.8 8.8.4.4
   ```

3. **Firewall**: Ensure outbound HTTPS (port 443) is allowed

## Boot Behavior

Once properly configured:

1. **Pi boots up** → Network connects
2. **Service starts automatically** → Authenticates with saved tokens
3. **Fetches photos** → Downloads and displays first photo
4. **Rotates photos** → Changes photo every 30 minutes (or configured interval)
5. **Handles errors gracefully** → Shows error messages on display if needed
6. **Auto-restarts** → Service restarts if it crashes

## Security Notes

- **Token storage**: `token.json` contains sensitive authentication data
- **File permissions**: Ensure only the pi user can read credential files
- **Network security**: All communication uses HTTPS
- **Read-only access**: Service only has read access to your photos

## Advanced Configuration

### Custom Photo Processing

Edit `google_photos_service.py` to customize:
- Image processing (contrast, brightness)
- Photo selection criteria
- Display layout

### Multiple Albums

To rotate between multiple albums, modify the service to:
1. Store multiple album IDs
2. Switch between albums periodically
3. Mix photos from different albums

### Scheduling

Use cron or systemd timers for advanced scheduling:
- Different albums at different times
- Pause during certain hours
- Seasonal photo selection

## File Structure

```
/opt/waveshare-pinfo/
├── credentials.json          # OAuth credentials (you provide)
├── token.json               # Authentication tokens (auto-generated)
├── .env                     # Environment configuration
├── google_photos_service.py # Google Photos API integration
├── photo_display_service.py # Main service
├── photo-display.service    # Systemd service file
├── configure_headless.py    # Setup script
└── setup_google_photos.py   # Authentication helper
```

## Support

If you encounter issues:

1. **Check logs** first: `sudo journalctl -u photo-display.service -f`
2. **Test components** individually: `python setup_google_photos.py test`
3. **Verify hardware**: Test e-ink display with simple scripts
4. **Check network**: Ensure stable internet connection

The service is designed to be robust and handle most issues automatically, including:
- Network disconnections
- Token expiration
- API rate limits
- Display initialization errors

Your Pi should now automatically display your Google Photos whenever it's powered on!
