# Raspberry Pi E-Ink Display with Home Assistant

This project turns your Raspberry Pi 4 with a Waveshare 4.01" color e-ink display into an information dashboard that integrates with Home Assistant and other data sources.

## Features

- Displays time, date, and weather information
- Integrates with Home Assistant for smart home data
- Auto-updates at configurable intervals
- Low-power e-ink display for always-on visibility
- Modular design for easy customization

## Hardware Requirements

- Raspberry Pi 4 (recommended) or Pi 3B+
- Waveshare 4.01" Color E-Ink Display (model: 4.01inch e-Paper HAT)
- MicroSD card (16GB or larger recommended)
- Power supply for Raspberry Pi

## Setup Instructions

1. **Install Raspberry Pi OS**
   - Download and flash Raspberry Pi OS Lite (32-bit) to your microSD card
   - Enable SSH by creating an empty file named `ssh` in the boot partition
   - Configure WiFi by creating a `wpa_supplicant.conf` file in the boot partition

2. **Install Dependencies**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-pil python3-numpy python3-spidev python3-rpi.gpio
   ```

3. **Clone the Repository**
   ```bash
   git clone <repository-url>
      cd waveshare-pinfo
   ```

4. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   nano .env
   ```
   Update the values with your Home Assistant URL and access token.

6. **Install Required Fonts**
   ```bash
   sudo apt-get install -y fonts-dejavu
   ```

7. **Install Waveshare Library**
   ```bash
   wget https://www.waveshare.com/w/upload/2/2f/Waveshare_e-Paper_code.7z
   sudo apt-get install -y p7zip
   7z x Waveshare_e-Paper_code.7z
   cp -r Waveshare_e-Paper_code/RaspberryPi_JetsonNano/python/lib/waveshare_epd /usr/local/lib/python3.7/dist-packages/
   ```

## Configuration

Edit the `.env` file to customize:
- Home Assistant connection details
- Update intervals
- Display preferences

## Deployment

This project includes a simple deployment script (`deploy.sh`) to pull the latest code from your Git repository and restart the application.

### Workflow

1.  **Develop Locally**: Write and test code on your main computer.
2.  **Commit to Git**: Push your changes to the `main` branch of your repository.
3.  **Deploy on Raspberry Pi**: SSH into your Pi and run the script:
    ```bash
    ./deploy.sh
    ```

### One-Time Setup on the Pi

1.  **Make the script executable**:
    ```bash
    chmod +x deploy.sh
    ```
2.  **(Recommended) Set up SSH keys with your Git provider** to avoid entering your password every time you deploy.

## Running the Application

To start the display:
```bash
python3 eink_display.py
```

To run as a service (recommended for production):
```bash
sudo cp eink-display.service /etc/systemd/system/
sudo systemctl enable eink-display
sudo systemctl start eink-display
```

## Customization

### Adding New Data Sources
1. Create a new method in the `EInkDisplay` class to fetch your data
2. Update the `update_display` method to show the new data
3. Add any required environment variables to `.env.example` and `.env`

### Changing the Layout
Modify the `update_display` method to change what information is shown and how it's arranged on the screen.

## Troubleshooting

- **Display not working**: Check the SPI interface is enabled in `raspi-config`
- **Home Assistant connection issues**: Verify your URL and access token in `.env`
- **Missing fonts**: Ensure the DejaVu fonts are installed

## License

This project is open source and available under the MIT License.
