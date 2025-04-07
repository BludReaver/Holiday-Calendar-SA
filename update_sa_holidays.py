import re
import requests
import os
from datetime import datetime, timedelta

# Configuration settings
TEST_MODE = True  # Set to True to test error notifications
ICS_URL = "https://www.officeholidays.com/ics-all/australia/south-australia"  # Restored original URL
OUTPUT_FILE = "SA-Public-Holidays.ics"  # Updated filename to match new repository
URL = ICS_URL  # Used in notifications

def clean_event_name(summary: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", summary).strip()

def get_next_update_date():
    """Returns the next quarterly update date in the format 'Monday 1st July 2025'"""
    today = datetime.now()
    current_year = today.year
    next_year = current_year + 1 if today.month > 9 else current_year
    
    # Determine the next update date based on current date
    if today.month < 4:
        next_date = datetime(current_year, 4, 1)
    elif today.month < 7:
        next_date = datetime(current_year, 7, 1)
    elif today.month < 10:
        next_date = datetime(current_year, 10, 1)
    else:
        next_date = datetime(next_year, 1, 1)
    
    # Format the date with the ordinal suffix (1st, 2nd, 3rd, etc.)
    day = next_date.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    
    # Format the full date string
    return next_date.strftime(f"%A {day}{suffix} %B %Y")

def send_failure_notification(error_excerpt: str):
    # Get Pushover credentials from environment variables
    token = os.environ.get("PUSHOVER_API_TOKEN")  # Updated from APP_TOKEN to API_TOKEN
    user = os.environ.get("PUSHOVER_USER_KEY")
    
    # Skip notification if credentials are missing
    if not token or not user or token == "YOUR_PUSHOVER_API_TOKEN" or user == "YOUR_PUSHOVER_USER_KEY":
        print("⚠️ Pushover credentials not configured. Skipping failure notification.")
        print(f"Error: {error_excerpt}")
        return
        
    import httpx
    message = (
        "‼️ SA Calendar Update Failed ‼️\n\n"
        "Your SA Public Holiday calendar could not be updated... Check the following: 🔎\n\n"
        "1. Go to your GitHub repository.\n"
        "2. Click the Actions tab.\n"
        "3. Open the failed workflow.\n"
        "4. Check which step failed.\n\n"
        f"🌐 Main site: {URL}\n"
        f"📅 Calendar source: {URL}\n\n"
        f"📝 Error Log:\n{error_excerpt}"
    )

    response = httpx.post("https://api.pushover.net/1/messages.json", data={
        "token": token,
        "user": user,
        "message": message
    })
    
    if response.status_code == 200:
        print("✅ Failure notification sent")
    else:
        print(f"❌ Failed to send notification: {response.text}")

def send_success_notification():
    # Get Pushover credentials from environment variables
    token = os.environ.get("PUSHOVER_API_TOKEN")  # Updated from APP_TOKEN to API_TOKEN
    user = os.environ.get("PUSHOVER_USER_KEY")
    
    # Skip notification if credentials are missing
    if not token or not user or token == "YOUR_PUSHOVER_API_TOKEN" or user == "YOUR_PUSHOVER_USER_KEY":
        print("⚠️ Pushover credentials not configured. Skipping success notification.")
        return
        
    import httpx
    next_update = get_next_update_date()

    message = (
        "✅ SA Public Holidays Updated ✅\n\n"
        "SA Public Holiday calendar was successfully updated via GitHub!\n\n"
        f"🕒 Next auto-update:\n{next_update}\n\n"
        "🌞 Have a nice day! 🌞"
    )

    response = httpx.post("https://api.pushover.net/1/messages.json", data={
        "token": token,
        "user": user,
        "message": message
    })
    
    if response.status_code == 200:
        print("✅ Success notification sent")
    else:
        print(f"❌ Failed to send notification: {response.text}")

def main():
    try:
        # Test mode check
        if TEST_MODE:
            print("🧪 TEST MODE ACTIVE - Simulating an error...")
            raise Exception("Test mode is enabled. This is a simulated error to test the notification system.")
            
        print(f"📅 Downloading calendar from {ICS_URL}...")
        response = requests.get(ICS_URL)
        response.raise_for_status()
        content = response.text
        
        print("🧹 Cleaning event names...")
        cleaned_lines = []
        for line in content.splitlines():
            if line.startswith("SUMMARY"):
                # Find the position of the colon that separates the attribute from the value
                colon_pos = line.find(":")
                if colon_pos > -1:
                    # Extract everything before the colon (including the colon)
                    summary_prefix = line[:colon_pos+1]
                    # Extract everything after the colon (the summary value)
                    summary_value = line[colon_pos+1:]
                    # Clean the summary value
                    cleaned_summary = clean_event_name(summary_value)
                    # Reconstruct the line
                    clean_line = f"{summary_prefix}{cleaned_summary}"
                    cleaned_lines.append(clean_line)
                else:
                    # If no colon is found (shouldn't happen), keep the line as is
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)


        print(f"💾 Saving to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(cleaned_lines))
            
        print("✅ Calendar updated successfully!")
        send_success_notification()

    except Exception as e:
        error_message = str(e)
        
        # Create a more user-friendly error message
        if TEST_MODE:
            user_friendly_error = "TEST MODE is enabled. This is a simulated error to verify that notifications are working correctly. No actual issue with the calendar."
        elif "Connection" in error_message or "Timeout" in error_message:
            user_friendly_error = f"Could not connect to the holidays website. The site might be down or there might be internet connectivity issues. Technical details: {error_message}"
        elif "404" in error_message:
            user_friendly_error = "The calendar URL has changed or is no longer available. Please check if the website structure has been updated."
        elif "Permission" in error_message:
            user_friendly_error = "Permission denied when trying to save the calendar file. Check GitHub Actions permissions."
        else:
            user_friendly_error = f"An unexpected error occurred: {error_message}"
            
        print(f"❌ Error updating calendar: {error_message}")
        send_failure_notification(user_friendly_error)

if __name__ == "__main__":
    main()


