#!/bin/bash

# Setup script for headless Google Photos e-ink display service

echo "Setting up Google Photos E-ink Display Service for headless operation..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file to configure your settings:"
    echo "- Set GOOGLE_PHOTOS_ALBUM_ID if you want a specific album"
    echo "- Adjust PHOTO_ROTATION_INTERVAL_MINUTES as needed"
fi

# Check for required files
echo "Checking required files..."

if [ ! -f credentials.json ]; then
    echo "❌ ERROR: credentials.json not found!"
    echo "Please download OAuth 2.0 credentials from Google Cloud Console"
    echo "and save as credentials.json in this directory"
    exit 1
fi

if [ ! -f token.json ]; then
    echo "⚠️  WARNING: token.json not found!"
    echo "You need to authenticate first. Run:"
    echo "python setup_google_photos.py test"
    echo "This will create the token.json file needed for headless operation"
    exit 1
fi

echo "✅ All required files present"

# Install system service
echo "Installing systemd service..."

# Update service file with correct paths
SERVICE_FILE="photo-display.service"
CURRENT_DIR=$(pwd)
USER=$(whoami)

# Create updated service file
cat > ${SERVICE_FILE} << EOF
[Unit]
Description=Google Photos E-ink Display Service
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=${USER}
Group=${USER}
WorkingDirectory=${CURRENT_DIR}
Environment=PYTHONPATH=${CURRENT_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 ${CURRENT_DIR}/photo_display_service.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

# Ensure network is available
ExecStartPre=/bin/bash -c 'until ping -c1 google.com; do sleep 1; done'

[Install]
WantedBy=multi-user.target
EOF

# Install service
sudo cp ${SERVICE_FILE} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable photo-display.service

echo "✅ Service installed and enabled"

# Test the service
echo "Testing authentication and photo fetching..."
python setup_google_photos.py test

if [ $? -eq 0 ]; then
    echo "✅ Authentication test successful"
    
    # Start the service
    echo "Starting photo display service..."
    sudo systemctl start photo-display.service
    
    echo "✅ Service started successfully!"
    echo ""
    echo "Service Management Commands:"
    echo "- Check status: sudo systemctl status photo-display.service"
    echo "- View logs: sudo journalctl -u photo-display.service -f"
    echo "- Stop service: sudo systemctl stop photo-display.service"
    echo "- Restart service: sudo systemctl restart photo-display.service"
    echo "- Disable service: sudo systemctl disable photo-display.service"
    echo ""
    echo "The service will now start automatically on boot!"
else
    echo "❌ Authentication test failed"
    echo "Please fix authentication issues before starting the service"
    exit 1
fi
EOF
