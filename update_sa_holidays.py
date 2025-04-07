import re
import requests
import os
from datetime import datetime

ICS_URL = "https://www.officeholidays.com/ics-all/australia/south-australia"  
OUTPUT_FILE = "SA-Public-Holidays.ics"
URL = ICS_URL  # Used in notifications

def clean_event_name(summary: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", summary).strip()

def send_failure_notification(error_excerpt: str):
    # Get Pushover credentials from environment variables
    token = os.environ.get("PUSHOVER_APP_TOKEN")
    user = os.environ.get("PUSHOVER_USER_KEY")
    
    # Skip notification if credentials are missing
    if not token or not user or token == "YOUR_PUSHOVER_APP_TOKEN" or user == "YOUR_PUSHOVER_USER_KEY":
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
    token = os.environ.get("PUSHOVER_APP_TOKEN")
    user = os.environ.get("PUSHOVER_USER_KEY")
    
    # Skip notification if credentials are missing
    if not token or not user or token == "YOUR_PUSHOVER_APP_TOKEN" or user == "YOUR_PUSHOVER_USER_KEY":
        print("⚠️ Pushover credentials not configured. Skipping success notification.")
        return
        
    import httpx
    formatted_date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).strftime("%A %d %B %Y")

    message = (
        "✅ SA Public Holidays Updated ✅\n\n"
        "SA Public Holiday calendar was successfully updated via GitHub!\n\n"
        f"🕒 Next auto-update:\n{formatted_date}\n\n"
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
        print(f"❌ Error updating calendar: {str(e)}")
        send_failure_notification(str(e))

if __name__ == "__main__":
    main()
