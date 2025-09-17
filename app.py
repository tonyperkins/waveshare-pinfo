from flask import Flask, render_template, request, jsonify
import os
import json
import threading
import time
from dotenv import load_dotenv, set_key
from photo_display import main as run_eink_display

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- Web Server for Album Selection ---

@app.route('/')
def index():
    """Serves the main setup and album picker page."""
    client_id = get_client_id()
    if not client_id:
        return "Error: 'credentials.json' not found or invalid. Please ensure it is in your project directory.", 500
    
    current_token = os.getenv('GOOGLE_PHOTOS_SHARE_TOKEN')
    return render_template('setup.html', google_client_id=client_id, current_share_token=current_token)

@app.route('/token', methods=['POST'])
def receive_token():
    """Receives the shareToken from the frontend and saves it to the .env file."""
    data = request.json
    token = data.get('shareToken')
    if token:
        try:
            dotenv_path = '.env'
            # Create .env if it doesn't exist
            if not os.path.exists(dotenv_path):
                open(dotenv_path, 'a').close()
            
            # Set the key in the .env file
            set_key(dotenv_path, 'GOOGLE_PHOTOS_SHARE_TOKEN', token)
            
            print(f"\n" + "="*60)
            print(f"  SUCCESS! Saved new Album Share Token to .env file.")
            print(f"  The e-ink display will update with the new album shortly.")
            print("="*60 + "\n")
            
            # This is a simple way to signal the main loop to reload. 
            # A more robust solution might use a formal signaling mechanism.
            global needs_reload
            needs_reload = True
            
            return jsonify({'status': 'success'}), 200
        except Exception as e:
            print(f"Error saving token to .env file: {e}")
            return jsonify({'status': 'error', 'message': 'Failed to save token.'}), 500

    return jsonify({'status': 'error', 'message': 'No token provided'}), 400

def get_client_id():
    """Reads the client ID from the credentials file."""
    credentials_file = os.getenv('GOOGLE_PHOTOS_CREDENTIALS_FILE', 'credentials.json')
    if os.path.exists(credentials_file):
        with open(credentials_file, 'r') as f:
            try:
                data = json.load(f)
                # Handles both 'installed' and 'web' credential types
                client_info = data.get('installed', data.get('web'))
                return client_info.get('client_id')
            except json.JSONDecodeError:
                return None
    return None

# --- Main Application Logic ---

needs_reload = False

def run_display_loop():
    """Wrapper to run the e-ink display and handle reloads."""
    global needs_reload
    while True:
        print("Starting e-ink display service...")
        # We run the main function from eink_display
        # It will loop internally until a reload is needed
        run_eink_display(lambda: needs_reload)
        
        # If the function returned, it means a reload is needed
        print("Reloading e-ink display service due to album change...")
        needs_reload = False
        # Reload environment variables to get the new token
        load_dotenv(override=True)
        time.sleep(5) # Give a moment before restarting

if __name__ == '__main__':
    # Start the e-ink display loop in a background thread
    display_thread = threading.Thread(target=run_display_loop, daemon=True)
    display_thread.start()

    # Run the Flask web server in the main thread
    print("\n" + "="*60)
    print("  Photo Frame Application Started")
    print("="*60)
    print("The e-ink display is running.")
    print("To change the album, open a browser and navigate to:")
    print("http://<your_pi_ip_address>:5000")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5000)
