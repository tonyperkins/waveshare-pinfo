import time
from dotenv import load_dotenv
from photo_display import main as run_photo_display

if __name__ == '__main__':
    print("Starting Photo Frame Display...")
    load_dotenv()
    # We run the main loop from photo_display directly
    # It will handle its own scheduling and looping.
    run_photo_display()
    print("Display loop exited. Shutting down.")
