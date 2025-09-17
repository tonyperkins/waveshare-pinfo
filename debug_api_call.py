import json
import os
import requests

TOKEN_FILE = 'token.json'

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def main():
    """A simple, direct API call to fetch photos, bypassing the Google client library."""
    print_header("Direct Google Photos API Fetch Test")

    if not os.path.exists(TOKEN_FILE):
        print(f"ERROR: '{TOKEN_FILE}' not found. Please authenticate first.")
        return

    try:
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        
        access_token = token_data.get('token')
        if not access_token:
            print("ERROR: Could not find 'token' in token.json.")
            return
        print("Successfully loaded access token.")
    except Exception as e:
        print(f"ERROR: Failed to read token.json: {e}")
        return

    api_url = 'https://photoslibrary.googleapis.com/v1/mediaItems?pageSize=10'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    print(f"\nMaking a direct GET request to fetch photos...")
    try:
        response = requests.get(api_url, headers=headers, timeout=30)

        print_header("API Response")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("\nSUCCESS! The API call worked and fetched photos.")
            photos = response.json().get('mediaItems', [])
            print(f"Found {len(photos)} photos.")
            for i, photo in enumerate(photos):
                print(f"  {i+1}. {photo.get('filename')} ({photo.get('id')})")
        else:
            print("\nERROR: The direct API call failed.")
            print("Response Body:")
            try:
                print(json.dumps(response.json(), indent=2))
            except json.JSONDecodeError:
                print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"\nFATAL ERROR: The web request itself failed: {e}")

if __name__ == "__main__":
    main()
