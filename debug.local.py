from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

# Define the scopes (adjust as needed)
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

# Path to your client secrets file (downloaded from Google Cloud Console)
CLIENT_SECRETS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'  # Where the token will be stored

# Load or create credentials
creds = None
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)  # Or use flow.run_console() for console auth
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

# Build the Photos service

service = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)
# Now try listing albums
results = service.albums().list(pageSize=50).execute()
print(results)