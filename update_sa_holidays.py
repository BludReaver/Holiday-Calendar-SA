import io
import sys

# Set UTF-8 encoding for stdout to properly handle emoji characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import re
import requests
import os
from datetime import datetime, timedelta
import uuid
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup

# Use text-based symbols as fallbacks for emoji in case of console encoding issues
EMOJI_CHECK = "✅"  # Success
EMOJI_WARNING = "⚠️"  # Warning
EMOJI_ERROR = "❌"  # Error
EMOJI_CALENDAR = "📅"  # Calendar
EMOJI_SAVE = "💾"  # Save
EMOJI_SEARCH = "🔍"  # Search
EMOJI_CRYSTAL_BALL = "🔮"  # Future prediction
EMOJI_SUN = "🌞"  # Sun
EMOJI_PLUS = "➕"  # Plus
EMOJI_PENCIL = "📝"  # Pencil

# Configuration settings
TEST_MODE = False  # Set to True to test error notifications
ERROR_SIMULATION = None  # Can be set to: "public_holidays", "school_terms", "future_term", "both", "connection", "404", "permission", "no_terms", or None
ICS_URL = "https://www.officeholidays.com/ics-all/australia/south-australia"  # Public holidays URL
SCHOOL_TERMS_URL = "https://www.education.sa.gov.au/docs/sper/communications/term-calendar/ical-School-term-dates-calendar-2025.ics"  # School terms URL
FUTURE_TERMS_URL = "https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools"  # Future term dates URL
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
        failed_calendar: Optional identifier of which calendar failed (public_holidays, school_terms, future_term, or None for general failure)
    """
    # Get Pushover credentials from environment variables
    token = os.environ.get("PUSHOVER_API_TOKEN")  # Updated from APP_TOKEN to API_TOKEN
    user = os.environ.get("PUSHOVER_USER_KEY")
    
    # Skip notification if credentials are missing
    if not token or not user or token == "YOUR_PUSHOVER_API_TOKEN" or user == "YOUR_PUSHOVER_USER_KEY":
        print(f"{EMOJI_WARNING} Pushover credentials not configured. Skipping failure notification.")
        print(f"Error: {error_excerpt}")
        return
    
    # Determine which calendar failed and set appropriate sources
    calendar_info = ""
    calendar_source = ""
    
    if failed_calendar == "public_holidays":
        calendar_info = f"{EMOJI_CALENDAR} Public Holidays Calendar update failed\n\n"
        calendar_source = f"🔗 Calendar Source: {PUBLIC_HOLIDAYS_SOURCE_URL}\n\n"
    elif failed_calendar == "school_terms":
        calendar_info = f"{EMOJI_CALENDAR} School Terms Calendar update failed\n\n"
        calendar_source = f"🔗 Calendar Source: {SCHOOL_TERMS_SOURCE_URL}\n\n"
    elif failed_calendar == "future_term":
        calendar_info = f"{EMOJI_CALENDAR} Future Term 1 Start Date update failed\n\n"
        calendar_source = f"🔗 Calendar Source: {FUTURE_TERMS_URL}\n\n"
    else:
        calendar_info = f"{EMOJI_CALENDAR} Calendar update failed\n\n"
        calendar_source = f"🔗 Calendar Sources:\n- Public Holidays: {PUBLIC_HOLIDAYS_SOURCE_URL}\n- School Terms: {SCHOOL_TERMS_SOURCE_URL}\n- Future Terms: {FUTURE_TERMS_URL}\n\n"
        
    import httpx
    message = (
        "‼️ SA Calendar Update Failed ‼️\n\n"
        f"{calendar_info}"
        "Check the following: 🔎\n\n"
        "1. Go to your GitHub repository.\n"
        "2. Click the Actions tab.\n"
        "3. Open the failed workflow.\n"
        "4. Check which step failed.\n\n"
        f"🌐 Actions: https://github.com/BludReaver/Holiday-Calendar-SA/actions\n\n"
        f"{calendar_source}"
        f"📝 Error Log:\n{error_excerpt}"
    )

    response = httpx.post("https://api.pushover.net/1/messages.json", data={
        "token": token,
        "user": user,
        "message": message
    })
    
    if response.status_code == 200:
        print(f"{EMOJI_CHECK} Failure notification sent")
    else:
        print(f"{EMOJI_ERROR} Failed to send notification: {response.text}")

def send_success_notification(future_term_fetched=True):
    """
    Send a success notification with information about the update
    
    Parameters:
        future_term_fetched: Boolean indicating if future term dates were successfully fetched
    """
    # Get Pushover credentials from environment variables
    token = os.environ.get("PUSHOVER_API_TOKEN")  # Updated from APP_TOKEN to API_TOKEN
    user = os.environ.get("PUSHOVER_USER_KEY")
    
    # Skip notification if credentials are missing
    if not token or not user or token == "YOUR_PUSHOVER_API_TOKEN" or user == "YOUR_PUSHOVER_USER_KEY":
        print(f"{EMOJI_WARNING} Pushover credentials not configured. Skipping success notification.")
        return
        
    import httpx
    next_update = get_next_update_date()
    
    future_term_message = ""
    if not future_term_fetched:
        future_term_message = f"{EMOJI_WARNING} Note: Future Term 1 dates could not be fetched but the current term dates are available.\n\n"

    message = (
        f"{EMOJI_CHECK} SA Calendars Updated {EMOJI_CHECK}\n\n"
        "Your calendars were successfully updated via GitHub!\n\n"
        f"{EMOJI_CALENDAR} Updated calendars:\n"
        "- SA Public Holidays\n"
        "- SA School Terms & Holidays\n\n"
        f"{future_term_message}"
        f"🕒 Next update: {next_update}\n\n"
        f"{EMOJI_SUN} Have a nice day! {EMOJI_SUN}"
    )

    response = httpx.post("https://api.pushover.net/1/messages.json", data={
        "token": token,
        "user": user,
        "message": message
    })
    
    if response.status_code == 200:
        print(f"{EMOJI_CHECK} Success notification sent")
    else:
        print(f"{EMOJI_ERROR} Failed to send notification: {response.text}")

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
        term_number = term['summary'].strip().split(" ")[-1]
        
        # For Term 1 2026, make the summary more distinct to avoid Google Calendar display issues
        summary = f"Term {term_number} Start"
        if term['start'].year == 2026 and term_number == "1":
            summary = f"Term {term_number} Start (January 27, 2026)"
        
        term_lines = [
            "BEGIN:VEVENT",
            "CLASS:PUBLIC",
            f"UID:START-{term_start_date}-TERM{term_number}@sa-school-terms.education.sa.gov.au",
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
            f"SUMMARY;LANGUAGE=en-us:{summary}",
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
        term_number = term['summary'].strip().split(" ")[-1]
        
        # For Term 1 2026, make the summary more distinct to avoid Google Calendar display issues
        summary = f"Term {term_number} End"
        
        # If this is the 2026 Term 1 End, create a special enhanced event to avoid display issues
        if term['end'].year == 2026 and term_number == "1":
            # Create a special event for the 2026 Term 1 End that's properly distinct
            term_lines = [
                "BEGIN:VEVENT",
                "CLASS:PUBLIC",
                # Add a completely different UID structure
                f"UID:TERM1-2026-END-DISTINCT-{uuid.uuid4()}@sa-school-terms.education.sa.gov.au",
                f"CREATED:{timestamp}",
                # Enhanced description
                f"DESCRIPTION:Last day of Term 1, 2026 for South Australian schools.\\n\\nThis event marks the end of the first term on April 10, 2026.\\n\\nInformation provided by education.sa.gov.au",
                "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
                f"DTSTART;VALUE=DATE:{term_end_date}",
                f"DTEND;VALUE=DATE:{term_end_next_day}",
                # Different timestamp - add 1 second
                f"DTSTAMP:{timestamp.replace('Z', '1Z')}",
                "LOCATION:South Australia Schools",
                "PRIORITY:5",
                # Different last-modified timestamp
                f"LAST-MODIFIED:{timestamp.replace('Z', '2Z')}",
                "SEQUENCE:2",  # Different sequence number
                # Very distinct summary
                f"SUMMARY;LANGUAGE=en-us:Term 1 End - April 10th, 2026",
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
        else:
            # Regular term end event for all other terms
            term_lines = [
                "BEGIN:VEVENT",
                "CLASS:PUBLIC",
                f"UID:END-{term_end_date}-TERM{term_number}@sa-school-terms.education.sa.gov.au",
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
                f"SUMMARY;LANGUAGE=en-us:{summary}",
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
            f"UID:HOLIDAY-{holiday_start_date}-TERM{term_number}@sa-school-terms.education.sa.gov.au",
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

def get_future_term1_date() -> Optional[Dict[str, datetime]]:
    """
    Fetches the future Term 1 start date from the education website.
    Returns a dictionary with start date and summary if found, None otherwise.
    """
    print(f"{EMOJI_CRYSTAL_BALL} Checking for future Term 1 start date from {FUTURE_TERMS_URL}...")
    
    # We've moved the simulation check to the update_school_terms function
    
    try:
        response = requests.get(FUTURE_TERMS_URL)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the future term dates heading
        future_term_heading = None
        for heading in soup.find_all(['h2', 'h3']):
            if 'future term dates' in heading.get_text().lower():
                future_term_heading = heading
                break
        
        if not future_term_heading:
            print(f"{EMOJI_WARNING} Future term dates heading not found on the page")
            return None
        
        # Find the table that follows this heading
        future_table = future_term_heading.find_next('table')
        
        if not future_table:
            print(f"{EMOJI_WARNING} Future term dates table not found on the page")
            return None
        
        # Get the current year
        current_year = datetime.now().year
        next_year = current_year + 1
        
        # Find the row for the next year in the table
        target_year = None
        term1_text = None
        
        rows = future_table.find_all('tr')
        
        for row in rows:
            # First column should be the year
            year_cell = row.find('th')
            if not year_cell or not year_cell.get_text().strip().isdigit():
                continue
                
            year = int(year_cell.get_text().strip())
            if year == next_year:
                target_year = year
                # Term 1 dates are in the first td cell (second column)
                term1_cell = row.find('td')
                if term1_cell:
                    # Replace <br/> tags with spaces
                    for br in term1_cell.find_all('br'):
                        br.replace_with(' ')
                    term1_text = term1_cell.get_text().strip()
                break
        
        if not target_year or not term1_text:
            print(f"{EMOJI_WARNING} Could not find term dates for year {next_year}")
            return None
        
        # Parse the term 1 date range, which is in format like "27 January to 10 April"
        # Sometimes the format might have odd spacing due to <br/> tags
        term1_text = re.sub(r'\s+', ' ', term1_text)  # Normalize whitespace
        term1_parts = term1_text.split('to')
        
        if len(term1_parts) != 2:
            print(f"{EMOJI_WARNING} Unexpected format for Term 1 date: {term1_text}")
            return None
        
        start_date_str = term1_parts[0].strip()
        end_date_str = term1_parts[1].strip()
        
        # Parse the start and end dates
        try:
            # Format is like "27 January" and "10 April"
            start_date = datetime.strptime(f"{start_date_str} {target_year}", "%d %B %Y")
            end_date = datetime.strptime(f"{end_date_str} {target_year}", "%d %B %Y")
            
            print(f"{EMOJI_CHECK} Found future Term 1 date: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}")
            
            return {
                "start": start_date,
                "end": end_date,
                "summary": f"Term 1"
            }
        except ValueError as e:
            print(f"{EMOJI_WARNING} Error parsing future Term 1 date: {e}")
            return None
            
    except Exception as e:
        print(f"{EMOJI_WARNING} Error fetching future term dates: {e}")
        return None

def update_school_terms():
    """Update the school terms and holidays calendar"""
    print(f"{EMOJI_CALENDAR} Downloading school terms from {SCHOOL_TERMS_URL}...")
    
    # Track if future term dates were successfully fetched
    future_term_success = True
    
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
            print(f"{EMOJI_SEARCH} Extracting term dates...")
            terms = extract_term_dates(content)
            
            if not terms:
                raise Exception("No school terms found in the calendar")
            
            return future_term_success
    
    response = requests.get(SCHOOL_TERMS_URL)
    response.raise_for_status()
    content = response.text
    
    print(f"{EMOJI_SEARCH} Extracting term dates...")
    terms = extract_term_dates(content)
    
    if not terms:
        raise Exception("No school terms found in the calendar")
    
    print(f"Found {len(terms)} school terms")
    
    # Check for test mode error simulation for future term dates before trying to fetch them
    if TEST_MODE and ERROR_SIMULATION == "future_term":
        print(f"{EMOJI_WARNING} Simulating failure to fetch future term dates")
        future_term_success = False
        print(f"{EMOJI_WARNING} Continuing with existing term dates only")
    else:
        # Try to get the future Term 1 start date
        try:
            future_term1 = get_future_term1_date()
            
            # If we found a future Term 1 date, add to terms if it's not already there
            if future_term1:
                # Check if this term already exists in our list
                future_term_exists = any(
                    term["start"].year == future_term1["start"].year and 
                    term["summary"].strip().endswith("1")
                    for term in terms
                )
                
                if not future_term_exists:
                    print(f"{EMOJI_PLUS} Adding future Term 1 (starting {future_term1['start'].strftime('%B %d, %Y')}) to the calendar")
                    terms.append(future_term1)
            else:
                future_term_success = False
                print(f"{EMOJI_WARNING} No future Term 1 date could be found. Continuing with existing term dates only.")
        except Exception as e:
            future_term_success = False
            print(f"{EMOJI_WARNING} Failed to add future Term 1 date: {e}")
            print(f"{EMOJI_WARNING} Continuing with existing term dates only")
    
    # Sort terms by start date to ensure proper order
    terms = sorted(terms, key=lambda x: x["start"])
    
    print(f"{EMOJI_SUN} Generating school holiday periods...")
    holidays = generate_holiday_periods(terms)
    
    # Check if we need to add a year-end holiday period
    # Find the latest Term 4 and the next year's Term 1 (if available)
    terms_by_year = {}
    for term in terms:
        year = term["start"].year
        term_num = term["summary"].strip().split(" ")[-1]
        
        if year not in terms_by_year:
            terms_by_year[year] = {}
        
        terms_by_year[year][term_num] = term
    
    # Look for pairs of years where we have Term 4 of current year and Term 1 of next year
    for year in sorted(terms_by_year.keys()):
        next_year = year + 1
        
        if "4" in terms_by_year.get(year, {}) and next_year in terms_by_year and "1" in terms_by_year[next_year]:
            term4 = terms_by_year[year]["4"]
            term1_next = terms_by_year[next_year]["1"]
            
            # Check if there's already a holiday covering this period
            holiday_exists = any(
                holiday["start"] > term4["end"] and holiday["end"] < term1_next["start"]
                for holiday in holidays
            )
            
            if not holiday_exists:
                print(f"{EMOJI_PLUS} Adding year-end holiday between Term 4 {year} and Term 1 {next_year}")
                holidays.append({
                    "start": term4["end"] + timedelta(days=1),
                    "end": term1_next["start"] - timedelta(days=1),
                    "summary": f"School Holidays (After Term 4)"
                })
    
    # Re-sort holidays by start date
    holidays = sorted(holidays, key=lambda x: x["start"])
    
    print(f"Generated {len(holidays)} holiday periods")
    
    print(f"{EMOJI_PENCIL} Creating new calendar with terms and holidays...")
    calendar_content = generate_school_calendar(terms, holidays)
    
    print(f"{EMOJI_SAVE} Saving school terms and holidays to {SCHOOL_OUTPUT_FILE}...")
    with open(SCHOOL_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(calendar_content)
    
    print(f"{EMOJI_CHECK} School terms and holidays calendar updated successfully!")
    
    return future_term_success

def update_public_holidays():
    """Update the public holidays calendar"""
    print(f"{EMOJI_CALENDAR} Downloading public holidays from {ICS_URL}...")
    
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
    
    print(f"{EMOJI_WARNING} Cleaning event names...")
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

    print(f"{EMOJI_SAVE} Saving public holidays to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_lines))
    
    print(f"{EMOJI_CHECK} Public holidays calendar updated successfully!")

def main():
    try:
        # Test mode check
        if TEST_MODE and not ERROR_SIMULATION:
            print("🧪 TEST MODE ACTIVE - Simulating a general error...")
            raise Exception("Test mode is enabled. This is a simulated error to test the notification system.")
            
        # Track which parts succeeded
        public_holidays_success = False
        school_terms_success = False
        future_term_success = True  # Assume true initially, set to false on specific failure
        
        try:
            # Update public holidays calendar
            update_public_holidays()
            public_holidays_success = True
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)
            print(f"{EMOJI_ERROR} Connection error updating public holidays calendar: {error_message}")
            user_friendly_error = "Couldn't download the public holidays. The website might be down or the internet connection might be having problems."
            send_failure_notification(user_friendly_error, "public_holidays")
        except requests.exceptions.HTTPError as e:
            error_message = str(e)
            print(f"{EMOJI_ERROR} HTTP error updating public holidays calendar: {error_message}")
            if "404" in error_message:
                user_friendly_error = "The calendar file couldn't be found. The website might have moved or renamed their calendar files."
            else:
                user_friendly_error = f"Received an error from the public holidays website: {error_message}"
            send_failure_notification(user_friendly_error, "public_holidays")
        except PermissionError as e:
            error_message = str(e)
            print(f"{EMOJI_ERROR} Permission error updating public holidays calendar: {error_message}")
            user_friendly_error = "The script doesn't have permission to save the calendar files. GitHub Actions might need updated permissions."
            send_failure_notification(user_friendly_error, "public_holidays")
        except Exception as e:
            error_message = str(e)
            print(f"{EMOJI_ERROR} Error updating public holidays calendar: {error_message}")
            user_friendly_error = f"An error occurred updating the public holidays calendar: {error_message}"
            send_failure_notification(user_friendly_error, "public_holidays")
            
        try:
            # Update school terms and holidays calendar
            future_term_success = update_school_terms()
            school_terms_success = True
            
            # Log a warning if future term dates couldn't be fetched
            if not future_term_success and TEST_MODE and ERROR_SIMULATION == "future_term":
                print(f"{EMOJI_WARNING} Future term dates couldn't be fetched, but the calendar was updated with available term dates")
                # This is just a warning, not a fatal error
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)
            print(f"{EMOJI_ERROR} Connection error updating school terms calendar: {error_message}")
            user_friendly_error = "Couldn't download the school terms calendar. The website might be down or the internet connection might be having problems."
            send_failure_notification(user_friendly_error, "school_terms")
        except requests.exceptions.HTTPError as e:
            error_message = str(e)
            print(f"{EMOJI_ERROR} HTTP error updating school terms calendar: {error_message}")
            if "404" in error_message:
                user_friendly_error = "The school terms calendar file couldn't be found. The website might have moved or renamed their calendar files."
            else:
                user_friendly_error = f"Received an error from the school terms website: {error_message}"
            send_failure_notification(user_friendly_error, "school_terms")
        except PermissionError as e:
            error_message = str(e)
            print(f"{EMOJI_ERROR} Permission error updating school terms calendar: {error_message}")
            user_friendly_error = "The script doesn't have permission to save the calendar files. GitHub Actions might need updated permissions."
            send_failure_notification(user_friendly_error, "school_terms")
        except Exception as e:
            error_message = str(e)
            print(f"{EMOJI_ERROR} Error updating school terms calendar: {error_message}")
            if "No school terms found" in error_message:
                user_friendly_error = "No school terms were found in the calendar. The website might have changed how they organize their data."
                send_failure_notification(user_friendly_error, "school_terms")
            else:
                user_friendly_error = f"An error occurred updating the school terms calendar: {error_message}"
                send_failure_notification(user_friendly_error, "school_terms")
        
        # Only send success notification if both calendars updated successfully
        if public_holidays_success and school_terms_success:
            send_success_notification(future_term_success)
            if not future_term_success:
                print(f"{EMOJI_WARNING} Note: Future term dates couldn't be fetched, but the calendar was updated with available term dates")
        else:
            print(f"{EMOJI_WARNING} One or more calendars failed to update, skipping success notification")
            
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
            
        print(f"{EMOJI_ERROR} Error updating calendars: {error_message}")
        send_failure_notification(user_friendly_error)
        
        # Exit with non-zero status code to make the GitHub Actions workflow fail
        sys.exit(1)

if __name__ == "__main__":
    main()






