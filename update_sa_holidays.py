import re
import requests
import os
import sys
from datetime import datetime, timedelta
import uuid
from typing import List, Dict, Tuple, Optional

# Configuration settings
TEST_MODE = False  # Set to True to test error notifications
ERROR_SIMULATION = None  # Can be set to: "public_holidays", "school_terms", "both", "connection", "404", "permission", "no_terms", or None
ICS_URL = "https://www.officeholidays.com/ics-all/australia/south-australia"  # Public holidays URL
SCHOOL_TERMS_URL = "https://www.education.sa.gov.au/docs/sper/communications/term-calendar/ical-School-term-dates-calendar-2025.ics"  # School terms URL
OUTPUT_FILE = "SA-Public-Holidays.ics"  # Public holidays output file
SCHOOL_OUTPUT_FILE = "SA-School-Terms-Holidays.ics"  # School terms and holidays output file

# Updated notification URLs - more accurate for the error notifications
PUBLIC_HOLIDAYS_SOURCE_URL = "https://www.officeholidays.com/subscribe/australia/south-australia"
SCHOOL_TERMS_SOURCE_URL = "https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools"

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

def send_failure_notification(error_excerpt: str, failed_calendar=None):
    """
    Send a failure notification with information about which calendar failed.
    
    Parameters:
        error_excerpt: The error message to include
        failed_calendar: Optional identifier of which calendar failed (public_holidays, school_terms, or None for general failure)
    """
    # Get Pushover credentials from environment variables
    token = os.environ.get("PUSHOVER_API_TOKEN")  # Updated from APP_TOKEN to API_TOKEN
    user = os.environ.get("PUSHOVER_USER_KEY")
    
    # Skip notification if credentials are missing
    if not token or not user or token == "YOUR_PUSHOVER_API_TOKEN" or user == "YOUR_PUSHOVER_USER_KEY":
        print("⚠️ Pushover credentials not configured. Skipping failure notification.")
        print(f"Error: {error_excerpt}")
        return
    
    # Determine which calendar failed and set appropriate sources
    calendar_info = ""
    calendar_source = ""
    
    if failed_calendar == "public_holidays":
        calendar_info = "📅 Public Holidays Calendar update failed\n\n"
        calendar_source = f"🔗 Calendar Source: {PUBLIC_HOLIDAYS_SOURCE_URL}\n\n"
    elif failed_calendar == "school_terms":
        calendar_info = "📅 School Terms Calendar update failed\n\n"
        calendar_source = f"🔗 Calendar Source: {SCHOOL_TERMS_SOURCE_URL}\n\n"
    else:
        calendar_info = "📅 Calendar update failed\n\n"
        calendar_source = f"🔗 Calendar Sources:\n- Public Holidays: {PUBLIC_HOLIDAYS_SOURCE_URL}\n- School Terms: {SCHOOL_TERMS_SOURCE_URL}\n\n"
        
    import httpx
    message = (
        "‼️ SA Calendar Update Failed ‼️\n\n"
        f"{calendar_info}"
        "Check the following: 🔎\n\n"
        "1. Go to your GitHub repository.\n"
        "2. Click the Actions tab.\n"
        "3. Open the failed workflow.\n"
        "4. Check which step failed.\n\n"
        f"🌐 Actions: https://github.com/BludReaver/Public-Holiday-Calendar-SA/actions\n\n"
        f"{calendar_source}"
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
        "✅ SA Calendars Updated ✅\n\n"
        "Your calendars were successfully updated via GitHub!\n\n"
        "📅 Updated calendars:\n"
        "- SA Public Holidays\n"
        "- SA School Terms & Holidays\n\n"
        f"🕒 Next update: {next_update}\n\n"
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

def parse_ics_date(date_str: str) -> datetime:
    """Parse a date string from ICS format (YYYYMMDD) to datetime object"""
    year = int(date_str[0:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])
    return datetime(year, month, day)

def extract_term_dates(content: str) -> List[Dict[str, datetime]]:
    """Extract term start and end dates from the school terms ICS content"""
    terms = []
    current_term = {}
    
    lines = content.splitlines()
    in_event = False
    
    for i, line in enumerate(lines):
        if line == "BEGIN:VEVENT":
            in_event = True
            current_term = {}
        elif line == "END:VEVENT" and in_event:
            if "start" in current_term and "end" in current_term and "summary" in current_term:
                terms.append(current_term)
            in_event = False
        elif in_event:
            if line.startswith("DTSTART;VALUE=DATE:"):
                date_str = line.split(":", 1)[1]
                current_term["start"] = parse_ics_date(date_str)
            elif line.startswith("DTEND;VALUE=DATE:"):
                date_str = line.split(":", 1)[1]
                # In ICS, end dates are exclusive, so subtract one day
                current_term["end"] = parse_ics_date(date_str) - timedelta(days=1)
            elif line.startswith("SUMMARY"):
                summary = line.split(":", 1)[1]
                current_term["summary"] = summary
    
    return terms

def generate_holiday_periods(terms: List[Dict[str, datetime]]) -> List[Dict[str, datetime]]:
    """Generate holiday periods between terms"""
    if not terms:
        return []
    
    # Sort terms by start date
    sorted_terms = sorted(terms, key=lambda x: x["start"])
    
    holidays = []
    
    # Add holidays between terms
    for i in range(len(sorted_terms) - 1):
        current_term_end = sorted_terms[i]["end"]
        next_term_start = sorted_terms[i+1]["start"]
        
        # Only add if there's a gap
        if next_term_start > current_term_end + timedelta(days=1):
            holiday_start = current_term_end + timedelta(days=1)
            holiday_end = next_term_start - timedelta(days=1)
            
            term_number = sorted_terms[i]["summary"].strip().split(" ")[-1]
            next_term_number = sorted_terms[i+1]["summary"].strip().split(" ")[-1]
            
            holidays.append({
                "start": holiday_start,
                "end": holiday_end,
                "summary": f"School Holidays (After Term {term_number})"
            })
    
    return holidays

def format_ics_datetime(dt: datetime) -> str:
    """Format a datetime object as an ICS date (YYYYMMDD)"""
    return dt.strftime("%Y%m%d")

def generate_school_calendar(terms: List[Dict[str, datetime]], holidays: List[Dict[str, datetime]]) -> str:
    """Generate a complete ICS calendar with terms and holidays that matches the public holidays format exactly"""
    current_year = datetime.now().year
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//South Australia School Terms and Holidays//EN",
        "X-WR-CALNAME:South Australia School Terms and Holidays",
        "X-WR-CALDESC:School terms and holiday periods in South Australia",
        "REFRESH-INTERVAL;VALUE=DURATION:PT48H",
        "X-PUBLISHED-TTL:PT48H",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-MS-OLK-FORCEINSPECTOROPEN:TRUE"
    ]
    
    # Add term START dates
    for term in terms:
        term_start_date = format_ics_datetime(term['start'])
        term_end_next_day = format_ics_datetime(term['start'] + timedelta(days=1))
        uid = str(uuid.uuid4())
        term_number = term['summary'].strip().split(" ")[-1]
        
        term_lines = [
            "BEGIN:VEVENT",
            "CLASS:PUBLIC",
            f"UID:{term_start_date}-TERM{term_number}-START@sa-school-terms.education.sa.gov.au",
            f"CREATED:{timestamp}",
            f"DESCRIPTION:First day of Term {term_number} for South Australian schools.\\n\\nInformation provided by education.sa.gov.au",
            "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
            f"DTSTART;VALUE=DATE:{term_start_date}",
            f"DTEND;VALUE=DATE:{term_end_next_day}",
            f"DTSTAMP:{timestamp}",
            "LOCATION:South Australia",
            "PRIORITY:5",
            f"LAST-MODIFIED:{timestamp}",
            "SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:Term {term_number} Start",
            "TRANSP:OPAQUE",
            "X-MICROSOFT-CDO-BUSYSTATUS:BUSY",
            "X-MICROSOFT-CDO-IMPORTANCE:1",
            "X-MICROSOFT-DISALLOW-COUNTER:FALSE",
            "X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
            "X-MS-OLK-AUTOFILLLOCATION:FALSE",
            "X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
            "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE",
            "X-MS-OLK-CONFTYPE:0",
            "END:VEVENT"
        ]
        lines.extend(term_lines)
    
    # Add term END dates
    for term in terms:
        term_end_date = format_ics_datetime(term['end'])
        term_end_next_day = format_ics_datetime(term['end'] + timedelta(days=1))
        uid = str(uuid.uuid4())
        term_number = term['summary'].strip().split(" ")[-1]
        
        term_lines = [
            "BEGIN:VEVENT",
            "CLASS:PUBLIC",
            f"UID:{term_end_date}-TERM{term_number}-END@sa-school-terms.education.sa.gov.au",
            f"CREATED:{timestamp}",
            f"DESCRIPTION:Last day of Term {term_number} for South Australian schools.\\n\\nInformation provided by education.sa.gov.au",
            "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
            f"DTSTART;VALUE=DATE:{term_end_date}",
            f"DTEND;VALUE=DATE:{term_end_next_day}",
            f"DTSTAMP:{timestamp}",
            "LOCATION:South Australia",
            "PRIORITY:5",
            f"LAST-MODIFIED:{timestamp}",
            "SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:Term {term_number} End",
            "TRANSP:OPAQUE",
            "X-MICROSOFT-CDO-BUSYSTATUS:BUSY",
            "X-MICROSOFT-CDO-IMPORTANCE:1",
            "X-MICROSOFT-DISALLOW-COUNTER:FALSE",
            "X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
            "X-MS-OLK-AUTOFILLLOCATION:FALSE",
            "X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
            "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE",
            "X-MS-OLK-CONFTYPE:0",
            "END:VEVENT"
        ]
        lines.extend(term_lines)
    
    # Add holiday events
    for holiday in holidays:
        holiday_start_date = format_ics_datetime(holiday['start'])
        holiday_end_date = format_ics_datetime(holiday['end'] + timedelta(days=1))
        term_number = holiday['summary'].strip().split(" ")[-1].replace(")", "")
        
        holiday_lines = [
            "BEGIN:VEVENT",
            "CLASS:PUBLIC",
            f"UID:{holiday_start_date}-HOLIDAY-TERM{term_number}@sa-school-terms.education.sa.gov.au",
            f"CREATED:{timestamp}",
            f"DESCRIPTION:School holidays after Term {term_number} for South Australian schools.\\n\\nInformation provided by education.sa.gov.au",
            "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
            f"DTSTART;VALUE=DATE:{holiday_start_date}",
            f"DTEND;VALUE=DATE:{holiday_end_date}",
            f"DTSTAMP:{timestamp}",
            "LOCATION:South Australia",
            "PRIORITY:5",
            f"LAST-MODIFIED:{timestamp}",
            "SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:{holiday['summary']}",
            "TRANSP:OPAQUE",
            "X-MICROSOFT-CDO-BUSYSTATUS:BUSY",
            "X-MICROSOFT-CDO-IMPORTANCE:1",
            "X-MICROSOFT-DISALLOW-COUNTER:FALSE",
            "X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
            "X-MS-OLK-AUTOFILLLOCATION:FALSE",
            "X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
            "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE",
            "X-MS-OLK-CONFTYPE:0",
            "END:VEVENT"
        ]
        lines.extend(holiday_lines)
    
    lines.append("END:VCALENDAR")
    return "\n".join(lines)

def update_public_holidays():
    """Update the public holidays calendar"""
    print(f"📅 Downloading public holidays from {ICS_URL}...")
    
    # Simulate errors if in test mode
    if TEST_MODE and ERROR_SIMULATION:
        if ERROR_SIMULATION in ["public_holidays", "both", "connection"]:
            raise requests.exceptions.ConnectionError("Simulated connection error for public holidays")
        elif ERROR_SIMULATION == "404":
            raise requests.exceptions.HTTPError("404 Client Error: Not Found for url: " + ICS_URL)
        elif ERROR_SIMULATION == "permission":
            raise PermissionError("Simulated permission error for public holidays")
    
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

    print(f"💾 Saving public holidays to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_lines))
    
    print("✅ Public holidays calendar updated successfully!")

def update_school_terms():
    """Update the school terms and holidays calendar"""
    print(f"📅 Downloading school terms from {SCHOOL_TERMS_URL}...")
    
    # Simulate errors if in test mode
    if TEST_MODE and ERROR_SIMULATION:
        if ERROR_SIMULATION in ["school_terms", "both", "connection"]:
            raise requests.exceptions.ConnectionError("Simulated connection error for school terms")
        elif ERROR_SIMULATION == "404":
            raise requests.exceptions.HTTPError("404 Client Error: Not Found for url: " + SCHOOL_TERMS_URL)
        elif ERROR_SIMULATION == "permission":
            raise PermissionError("Simulated permission error for school terms")
        elif ERROR_SIMULATION == "no_terms":
            # Return empty content that will lead to "No school terms found"
            response = requests.Response()
            response.status_code = 200
            response._content = b"BEGIN:VCALENDAR\nEND:VCALENDAR"
            response.raise_for_status()
            content = response._content.decode('utf-8')
            
            # Process the rest normally, which will lead to the "No school terms found" error
            print("🔍 Extracting term dates...")
            terms = extract_term_dates(content)
            
            if not terms:
                raise Exception("No school terms found in the calendar")
            
            return
    
    response = requests.get(SCHOOL_TERMS_URL)
    response.raise_for_status()
    content = response.text
    
    print("🔍 Extracting term dates...")
    terms = extract_term_dates(content)
    
    if not terms:
        raise Exception("No school terms found in the calendar")
    
    print(f"Found {len(terms)} school terms")
    
    print("🌞 Generating school holiday periods...")
    holidays = generate_holiday_periods(terms)
    
    print(f"Generated {len(holidays)} holiday periods")
    
    print("📝 Creating new calendar with terms and holidays...")
    calendar_content = generate_school_calendar(terms, holidays)
    
    print(f"💾 Saving school terms and holidays to {SCHOOL_OUTPUT_FILE}...")
    with open(SCHOOL_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(calendar_content)
    
    print("✅ School terms and holidays calendar updated successfully!")

def main():
    try:
        # Test mode check
        if TEST_MODE and not ERROR_SIMULATION:
            print("🧪 TEST MODE ACTIVE - Simulating a general error...")
            raise Exception("Test mode is enabled. This is a simulated error to test the notification system.")
            
        # Track which parts succeeded
        public_holidays_success = False
        school_terms_success = False
        
        try:
            # Update public holidays calendar
            update_public_holidays()
            public_holidays_success = True
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)
            print(f"❌ Connection error updating public holidays calendar: {error_message}")
            user_friendly_error = "Couldn't download the public holidays. The website might be down or the internet connection might be having problems."
            send_failure_notification(user_friendly_error, "public_holidays")
        except requests.exceptions.HTTPError as e:
            error_message = str(e)
            print(f"❌ HTTP error updating public holidays calendar: {error_message}")
            if "404" in error_message:
                user_friendly_error = "The calendar file couldn't be found. The website might have moved or renamed their calendar files."
            else:
                user_friendly_error = f"Received an error from the public holidays website: {error_message}"
            send_failure_notification(user_friendly_error, "public_holidays")
        except PermissionError as e:
            error_message = str(e)
            print(f"❌ Permission error updating public holidays calendar: {error_message}")
            user_friendly_error = "The script doesn't have permission to save the calendar files. GitHub Actions might need updated permissions."
            send_failure_notification(user_friendly_error, "public_holidays")
        except Exception as e:
            error_message = str(e)
            print(f"❌ Error updating public holidays calendar: {error_message}")
            user_friendly_error = f"An error occurred updating the public holidays calendar: {error_message}"
            send_failure_notification(user_friendly_error, "public_holidays")
            
        try:
            # Update school terms and holidays calendar
            update_school_terms()
            school_terms_success = True
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)
            print(f"❌ Connection error updating school terms calendar: {error_message}")
            user_friendly_error = "Couldn't download the school terms calendar. The website might be down or the internet connection might be having problems."
            send_failure_notification(user_friendly_error, "school_terms")
        except requests.exceptions.HTTPError as e:
            error_message = str(e)
            print(f"❌ HTTP error updating school terms calendar: {error_message}")
            if "404" in error_message:
                user_friendly_error = "The school terms calendar file couldn't be found. The website might have moved or renamed their calendar files."
            else:
                user_friendly_error = f"Received an error from the school terms website: {error_message}"
            send_failure_notification(user_friendly_error, "school_terms")
        except PermissionError as e:
            error_message = str(e)
            print(f"❌ Permission error updating school terms calendar: {error_message}")
            user_friendly_error = "The script doesn't have permission to save the calendar files. GitHub Actions might need updated permissions."
            send_failure_notification(user_friendly_error, "school_terms")
        except Exception as e:
            error_message = str(e)
            print(f"❌ Error updating school terms calendar: {error_message}")
            if "No school terms found" in error_message:
                user_friendly_error = "No school terms were found in the calendar. The website might have changed how they organize their data."
            else:
                user_friendly_error = f"An error occurred updating the school terms calendar: {error_message}"
            send_failure_notification(user_friendly_error, "school_terms")
        
        # Only send success notification if both calendars updated successfully
        if public_holidays_success and school_terms_success:
            send_success_notification()
        else:
            print("⚠️ One or more calendars failed to update, skipping success notification")
            
        # If either calendar failed, exit with error code
        if not (public_holidays_success and school_terms_success):
            sys.exit(1)

    except Exception as e:
        # This is for errors that happen outside of the specific calendar updates
        error_message = str(e)
        
        # Create a more user-friendly error message
        if TEST_MODE and not ERROR_SIMULATION:
            user_friendly_error = "This is just a test. Test Mode is turned on. Nothing is actually wrong with the calendars."
        elif "Connection" in error_message or "Timeout" in error_message:
            user_friendly_error = "Couldn't connect to the calendar websites. The sites might be down or the internet connection might be having problems."
        elif "404" in error_message:
            user_friendly_error = "The calendar files couldn't be found. The websites might have moved or renamed their files."
        elif "Permission" in error_message:
            user_friendly_error = "The script doesn't have permission to save the calendar files. GitHub Actions might need updated permissions."
        else:
            user_friendly_error = f"An unexpected error occurred: {error_message}"
            
        print(f"❌ Error updating calendars: {error_message}")
        send_failure_notification(user_friendly_error)
        
        # Exit with non-zero status code to make the GitHub Actions workflow fail
        sys.exit(1)

if __name__ == "__main__":
    main()






