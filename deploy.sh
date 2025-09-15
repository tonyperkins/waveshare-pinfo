#!/bin/bash

# Navigate to the project directory
cd /home/pi/waveshare-pinfo || exit

# Fetch the latest changes from the main branch
# The -f flag will discard any local changes. Use with caution.
git fetch origin main
git reset --hard origin/main

# Install/update Python dependencies if requirements.txt has changed
# This is optional but good practice
pip install -r requirements.txt

# Restart the e-ink display service
sudo systemctl restart eink-display.service

echo "Deployment complete. E-ink display service restarted."
