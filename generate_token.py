import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# These scopes are required to allow the Picker to list albums (readonly)
# and to allow our app to create a shareable link (sharing).
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly', 'https://www.googleapis.com/auth/photoslibrary.sharing']

TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

def main():
    """Runs the command-line flow to generate a token.json file."""
    print("\n" + "="*60)
    print("  Google Photos Token Generator")
    print("="*60)

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\nERROR: '{CREDENTIALS_FILE}' not found.")
        print("Please download your OAuth 2.0 credentials for a 'Desktop app' and save it here.")
        return

    print("\nAttempting to authenticate with Google Photos...")
    print("The script will now start a local server and print an authentication URL.")
    print("1. Copy the URL and paste it into a browser on any device.")
    print("2. Approve the permissions (you may see a new consent screen).")
    print("3. The script will automatically complete the authentication.")
    print("="*60 + "\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        # Use a fixed port (8080) to enable SSH port forwarding from a remote machine.
        creds = flow.run_local_server(port=8080, open_browser=False)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        
        print("\n" + "-"*60)
        print(f"SUCCESS: A valid '{TOKEN_FILE}' has been created.")
        print("You can now run the main photo frame application.")
        print("-"*60 + "\n")

    except Exception as e:
        print(f"\nERROR: Authentication failed: {e}")

if __name__ == '__main__':
    main()
