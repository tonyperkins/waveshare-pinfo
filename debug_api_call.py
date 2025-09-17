import json
import os
import requests

TOKEN_FILE = 'token.json'

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def main():
    """A simple, direct API call to debug Google Photos authentication."""
    print_header("Direct Google Photos API Debug Test")

    # 1. Check if token.json exists
    if not os.path.exists(TOKEN_FILE):
        print(f"ERROR: '{TOKEN_FILE}' not found.")
        print("Please run 'python setup_google_photos.py test' to authenticate first.")
        return

    # 2. Load the token and extract the access token
    try:
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        
        access_token = token_data.get('token')
        if not access_token:
            print("ERROR: Could not find 'token' in token.json.")
            return
        print("Successfully loaded access token from token.json.")
    except Exception as e:
        print(f"ERROR: Failed to read or parse token.json: {e}")
        return

    # 3. Make the direct API call
    api_url = 'https://photoslibrary.googleapis.com/v1/mediaItems?pageSize=1'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    print(f"\nMaking a direct GET request to: {api_url}")
    try:
        response = requests.get(api_url, headers=headers, timeout=20)

        # 4. Print the results
        print_header("API Response Details")
        print(f"Status Code: {response.status_code}")
        print("\n--- Response Headers ---")
        for key, value in response.headers.items():
            print(f"{key}: {value}")
        
        print("\n--- Response Body ---")
        try:
            # Try to print pretty JSON
            print(json.dumps(response.json(), indent=2))
            print("\nSUCCESS: The API call worked directly!")
            print("This means the issue is likely with the 'google-api-python-client' library.")
        except json.JSONDecodeError:
            # If not JSON, print as text
            print(response.text)
            print("\nERROR: The API call failed.")
            print("This confirms the problem is on the Google Cloud project configuration side.")

    except requests.exceptions.RequestException as e:
        print(f"\nFATAL ERROR: The web request itself failed: {e}")

if __name__ == "__main__":
    main()
