#!/usr/bin/env python3
"""
Configuration script for headless Google Photos e-ink display.
This script helps set up the service for automatic startup.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_status(message, status="INFO"):
    symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}
    print(f"{symbols.get(status, 'ℹ️')} {message}")

def check_file_exists(filepath, description):
    """Check if a required file exists"""
    if os.path.exists(filepath):
        print_status(f"{description} found: {filepath}", "SUCCESS")
        return True
    else:
        print_status(f"{description} missing: {filepath}", "ERROR")
        return False

def check_authentication():
    """Check if authentication is properly set up"""
    print_header("Checking Authentication Setup")
    
    creds_ok = check_file_exists("credentials.json", "OAuth credentials")
    token_ok = check_file_exists("token.json", "Authentication token")
    
    if not creds_ok:
        print("\nTo get credentials.json:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Enable Photos Library API")
        print("3. Create OAuth 2.0 credentials (Desktop application)")
        print("4. Download and save as credentials.json")
        return False
    
    if not token_ok:
        print("\nTo create authentication token:")
        print("Run: python setup_google_photos.py test")
        print("This will guide you through the authentication process")
        return False
    
    # Test if token is valid
    try:
        from google_photos_service import GooglePhotosService
        service = GooglePhotosService()
        if service.authenticate():
            print_status("Authentication token is valid", "SUCCESS")
            return True
        else:
            print_status("Authentication token is invalid", "ERROR")
            return False
    except Exception as e:
        print_status(f"Error testing authentication: {e}", "ERROR")
        return False

def setup_environment():
    """Set up environment configuration"""
    print_header("Setting Up Environment Configuration")
    
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            subprocess.run(["cp", ".env.example", ".env"])
            print_status("Created .env from template", "SUCCESS")
        else:
            print_status(".env.example not found", "ERROR")
            return False
    else:
        print_status(".env already exists", "INFO")
    
    print("\nEnvironment variables you can configure in .env:")
    print("- GOOGLE_PHOTOS_ALBUM_ID: Specific album to display (optional)")
    print("- PHOTO_ROTATION_INTERVAL_MINUTES: How often to change photos (default: 30)")
    print("- GOOGLE_PHOTOS_CREDENTIALS_FILE: Path to credentials.json (default: credentials.json)")
    print("- GOOGLE_PHOTOS_TOKEN_FILE: Path to token.json (default: token.json)")
    
    return True

def install_service():
    """Install systemd service"""
    print_header("Installing Systemd Service")
    
    service_file = "photo-display.service"
    if not os.path.exists(service_file):
        print_status(f"Service file {service_file} not found", "ERROR")
        return False
    
    # Update service file with current directory
    current_dir = os.getcwd()
    current_user = os.getenv("USER", "pi")
    
    # Read and update service file
    with open(service_file, 'r') as f:
        content = f.read()
    
    # Replace paths and user
    content = content.replace("/opt/waveshare-pinfo", current_dir)
    content = content.replace("User=pi", f"User={current_user}")
    content = content.replace("Group=pi", f"Group={current_user}")
    
    # Write updated service file
    updated_service = f"{service_file}.updated"
    with open(updated_service, 'w') as f:
        f.write(content)
    
    try:
        # Install service
        subprocess.run(["sudo", "cp", updated_service, f"/etc/systemd/system/{service_file}"], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", service_file], check=True)
        
        print_status("Service installed and enabled", "SUCCESS")
        
        # Clean up
        os.remove(updated_service)
        
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to install service: {e}", "ERROR")
        return False

def test_service():
    """Test the service"""
    print_header("Testing Service")
    
    try:
        # Test authentication and photo fetching
        result = subprocess.run([sys.executable, "setup_google_photos.py", "test"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print_status("Service test successful", "SUCCESS")
            return True
        else:
            print_status(f"Service test failed: {result.stderr}", "ERROR")
            return False
    except subprocess.TimeoutExpired:
        print_status("Service test timed out", "ERROR")
        return False
    except Exception as e:
        print_status(f"Error testing service: {e}", "ERROR")
        return False

def start_service():
    """Start the service"""
    print_header("Starting Service")
    
    try:
        subprocess.run(["sudo", "systemctl", "start", "photo-display.service"], check=True)
        print_status("Service started successfully", "SUCCESS")
        
        # Check status
        result = subprocess.run(["sudo", "systemctl", "is-active", "photo-display.service"], 
                              capture_output=True, text=True)
        
        if result.stdout.strip() == "active":
            print_status("Service is running", "SUCCESS")
        else:
            print_status("Service may not be running properly", "WARNING")
        
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to start service: {e}", "ERROR")
        return False

def show_management_commands():
    """Show service management commands"""
    print_header("Service Management Commands")
    
    commands = [
        ("Check status", "sudo systemctl status photo-display.service"),
        ("View logs", "sudo journalctl -u photo-display.service -f"),
        ("Stop service", "sudo systemctl stop photo-display.service"),
        ("Restart service", "sudo systemctl restart photo-display.service"),
        ("Disable service", "sudo systemctl disable photo-display.service"),
        ("View recent logs", "sudo journalctl -u photo-display.service --since '1 hour ago'"),
    ]
    
    for description, command in commands:
        print(f"• {description:15}: {command}")

def main():
    """Main configuration function"""
    print_header("Google Photos E-ink Display - Headless Setup")
    
    print("This script will configure your Pi for headless operation.")
    print("The service will start automatically on boot and display photos from Google Photos.")
    
    # Step 1: Check authentication
    if not check_authentication():
        print_status("Please fix authentication issues before continuing", "ERROR")
        return False
    
    # Step 2: Set up environment
    if not setup_environment():
        print_status("Failed to set up environment", "ERROR")
        return False
    
    # Step 3: Install service
    if not install_service():
        print_status("Failed to install service", "ERROR")
        return False
    
    # Step 4: Test service
    if not test_service():
        print_status("Service test failed - check configuration", "WARNING")
        # Continue anyway, user can debug later
    
    # Step 5: Start service
    if not start_service():
        print_status("Failed to start service", "ERROR")
        return False
    
    # Show management commands
    show_management_commands()
    
    print_header("Setup Complete!")
    print("Your Google Photos e-ink display service is now running!")
    print("It will automatically start on boot and display photos from your Google Photos library.")
    print("\nThe display will:")
    print("• Rotate photos every 30 minutes (configurable)")
    print("• Automatically handle authentication token refresh")
    print("• Restart automatically if it encounters errors")
    print("• Show error messages on the display if something goes wrong")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
