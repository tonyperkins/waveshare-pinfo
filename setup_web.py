from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# This will store the shareToken once the user provides it
shared_data = {'share_token': None}

@app.route('/')
def index():
    """Serves the main setup page."""
    # We pass the Client ID to the template for the Google Picker API
    client_id = get_client_id()
    if not client_id:
        return "Error: Could not find Google Client ID in credentials.json. Please run the standard setup first.", 500
    return render_template('setup.html', google_client_id=client_id)

@app.route('/token', methods=['POST'])
def receive_token():
    """Receives the shareToken from the frontend and stores it."""
    data = request.json
    token = data.get('shareToken')
    if token:
        shared_data['share_token'] = token
        print(f"\n\n" + "="*60)
        print("  SUCCESS! Received Share Token from the browser.")
        print(f"  Your Album Share Token is: {token}")
        print("  Please copy this token and add it to your .env file as:")
        print(f"  GOOGLE_PHOTOS_SHARE_TOKEN={token}")
        print("  You can now close this setup script (Ctrl+C).")
        print("="*60 + "\n")
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'No token provided'}), 400

def get_client_id():
    """Reads the client ID from the credentials file."""
    import json
    credentials_file = os.getenv('GOOGLE_PHOTOS_CREDENTIALS_FILE', 'credentials.json')
    if os.path.exists(credentials_file):
        with open(credentials_file, 'r') as f:
            data = json.load(f)
            return data.get('installed', {}).get('client_id')
    return None

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  Google Photos Picker Setup Server")
    print("="*60)
    print("1. Open a web browser on your desktop computer (not the Pi).")
    print("2. Navigate to: http://<your_pi_ip_address>:5000")
    print("3. Follow the on-screen instructions to select your album.")
    print("4. The required 'shareToken' will be printed here.")
    print("\nWaiting for you to complete the process in your browser...")
    app.run(host='0.0.0.0', port=5000)
