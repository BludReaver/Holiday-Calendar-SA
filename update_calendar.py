import os
import sys
import requests
import pdfplumber
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz
import subprocess
import re

# Toggle this to True to force a failure for testing notifications
FAIL_TEST_MODE = False

PDF_FOLDER = "Public Holidays PDF Data"
ICS_FILE = "Public-Holiday-Calendar-SA.ics"
LOG_FILE = "update_log.txt"
URL = "https://www.safework.sa.gov.au/resources/public-holidays"

# Use GitHub Actions secrets
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
TIMEZONE = "Australia/Adelaide"

def send_failure_notification(error_excerpt: str):
    """Send a notification about update failure using Pushover API."""
    msg = (
        "!! SA Calendar Update Failed !!\n\n"
        "Your SA Public Holiday calendar could not be updated. Check the following:\n\n"
        "1. Go to your GitHub repository.\n"
        "2. Click the Actions tab.\n"
        "3. Open the failed workflow.\n"
        "4. Check which step failed.\n\n"
        f"Main site: {URL}\n"
        f"Calendar source: {URL}\n\n"
        f"Error Log:\n{error_excerpt}"
    )
    
    print(f"Sending failure notification...")
    
    # Check if Pushover credentials are available
    if not PUSHOVER_USER_KEY or not PUSHOVER_API_TOKEN:
        print("::warning::Pushover API keys not found. Notification not sent.")
        return
    
    try:
        response = requests.post(
            "https://api.pushover.net/1/messages.json", 
            data={
                "token": PUSHOVER_API_TOKEN,
                "user": PUSHOVER_USER_KEY,
                "message": msg
            },
            timeout=10  # Add timeout to prevent hanging
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Notification sent successfully!")
        else:
            print(f"::warning::Failed to send notification. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"::warning::Exception while sending notification: {str(e)}")

def get_day_suffix(day):
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

# Trigger failure early if test mode is on
if FAIL_TEST_MODE:
    fail_reason = "Fail test mode is active. Simulated failure triggered."
    print(f"::error::{fail_reason}")

    with open(LOG_FILE, "w") as log:
        log.write("Exception occurred:\n" + fail_reason + "\n")

    send_failure_notification(fail_reason)
    sys.exit(1)

os.makedirs(PDF_FOLDER, exist_ok=True)

try:
    with open(LOG_FILE, "w") as log:
        log.write("Starting calendar update process...\n")
        log.write(f"Fetching data from {URL}...\n")
        response = requests.get(URL)
        response.raise_for_status()
        soup_url_match = re.search(r'href="(.*?)"[^>]*>[^<]*public holiday dates', response.text, re.IGNORECASE)

        if soup_url_match:
            pdf_url = soup_url_match.group(1)
            if not pdf_url.lower().startswith("http"):
                pdf_url = f"https://www.safework.sa.gov.au{pdf_url}"
            log.write(f"Found PDF URL: {pdf_url}\n")
            pdf_resp = requests.get(pdf_url)
            pdf_resp.raise_for_status()
            pdf_name = os.path.join(PDF_FOLDER, os.path.basename(pdf_url))
            with open(pdf_name, "wb") as f:
                f.write(pdf_resp.content)
            log.write(f"Downloaded PDF to: {pdf_name}\n")
        else:
            log.write("No PDF link found on the page. Using existing PDF if available.\n")
            # Try to find any existing PDF in the folder
            pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
            if pdf_files:
                pdf_name = os.path.join(PDF_FOLDER, pdf_files[0])
                log.write(f"Using existing PDF: {pdf_name}\n")
            else:
                raise Exception("No PDF link found on the page and no existing PDFs available.")

        # Parse holidays from PDF
        holidays = []
        log.write(f"Parsing PDF: {pdf_name}\n")
        with pdfplumber.open(pdf_name) as pdf:
            log.write(f"PDF has {len(pdf.pages)} pages\n")
            for page_num, page in enumerate(pdf.pages, 1):
                log.write(f"Processing page {page_num}...\n")
                tables = page.extract_tables()
                log.write(f"Found {len(tables)} tables on page {page_num}\n")
                
                for table_num, table in enumerate(tables, 1):
                    log.write(f"Processing table {table_num} on page {page_num}...\n")
                    if not table or len(table) <= 1:
                        log.write(f"Table {table_num} on page {page_num} is empty or has only headers\n")
                        continue
                        
                    headers = table[0] if table else []
                    log.write(f"Headers: {headers}\n")
                    
                    for row_num, row in enumerate(table[1:], 1):
                        log.write(f"Processing row {row_num}: {row}\n")
                        if not row or not row[0]:
                            log.write(f"Row {row_num} is empty or missing holiday name\n")
                            continue
                        
                        # Original holiday name
                        original_name = row[0].strip()
                        log.write(f"Original holiday name: {original_name}\n")
                        
                        # Remove ALL brackets and their contents, not just parentheses
                        name = re.sub(r'\([^)]*\)', '', original_name) # Remove (parentheses)
                        name = re.sub(r'\[[^\]]*\]', '', name)         # Remove [square brackets]
                        name = re.sub(r'\{[^}]*\}', '', name)          # Remove {curly braces}
                        name = re.sub(r'<[^>]*>', '', name)            # Remove <angle brackets>
                        name = name.strip()
                        log.write(f"Cleaned holiday name: {name}\n")
                        
                        # If it's a part-day holiday, treat as full day
                        if "Part-day" in name or "part-day" in name or "half-day" in name or "Half-day" in name:
                            # Replace the part-day designation but keep the holiday name
                            name = re.sub(r'Part-day public holiday|part-day public holiday|half-day public holiday|Half-day public holiday', 'Public Holiday', name)
                            log.write(f"Adjusted part-day holiday to full day: {name}\n")
                        
                        for i in range(1, len(headers)):
                            year = headers[i].strip() if i < len(headers) else ""
                            cell = row[i].strip() if i < len(row) and row[i] else ""
                            log.write(f"Processing date cell for {year}: '{cell}'\n")
                            
                            if not cell or not year:
                                log.write(f"Empty date cell or year column for {year}, skipping\n")
                                continue
                            
                            # Try different date formats
                            date_obj = None
                            
                            # Format: "Weekday Day Month"
                            date_match = re.search(r'(\w+)\s+(\d{1,2})\s+(\w+)', cell)
                            if date_match:
                                weekday, day, month = date_match.groups()
                                log.write(f"Matched format 'Weekday Day Month': {weekday} {day} {month} {year}\n")
                                try:
                                    date_obj = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                                    log.write(f"Successfully parsed date: {date_obj}\n")
                                except ValueError as e:
                                    log.write(f"Failed to parse with full month name: {e}\n")
                                    try:
                                        # Try abbreviated month names
                                        date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                                        log.write(f"Successfully parsed date with abbreviated month: {date_obj}\n")
                                    except ValueError as e:
                                        log.write(f"Failed to parse with abbreviated month name: {e}\n")
                            else:
                                log.write(f"No match for format 'Weekday Day Month'\n")
                            
                            # Format: "Day Month"
                            if not date_obj:
                                date_match = re.search(r'(\d{1,2})\s+(\w+)', cell)
                                if date_match:
                                    day, month = date_match.groups()
                                    log.write(f"Matched format 'Day Month': {day} {month} {year}\n")
                                    try:
                                        date_obj = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                                        log.write(f"Successfully parsed date: {date_obj}\n")
                                    except ValueError as e:
                                        log.write(f"Failed to parse with full month name: {e}\n")
                                        try:
                                            # Try abbreviated month names
                                            date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                                            log.write(f"Successfully parsed date with abbreviated month: {date_obj}\n")
                                        except ValueError as e:
                                            log.write(f"Failed to parse with abbreviated month name: {e}\n")
                                else:
                                    log.write(f"No match for format 'Day Month'\n")
                            
                            # Format: Special handling for 2025 dates when only weekday is provided
                            if not date_obj and year == "2025" and original_name:
                                # Extract the date from the holiday name if possible
                                date_in_name = None
                                day_match = re.search(r'(\d{1,2})\s+(\w+)', original_name)
                                
                                if day_match:
                                    day, month = day_match.groups()
                                    try:
                                        # Attempt to create date from the name
                                        date_in_name = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                                        log.write(f"Extracted date from name: {date_in_name}\n")
                                    except ValueError:
                                        try:
                                            # Try abbreviated month names
                                            date_in_name = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                                            log.write(f"Extracted date from name with abbreviated month: {date_in_name}\n")
                                        except ValueError:
                                            date_in_name = None
                                            
                                # Use known holidays for 2025
                                known_dates_2025 = {
                                    "New Year's Day": "20250101",
                                    "Australia Day": "20250127",  # Observed on Monday
                                    "Adelaide Cup Day": "20250310",  # Second Monday in March
                                    "Good Friday": "20250418",
                                    "Easter Saturday": "20250419",
                                    "Easter Sunday": "20250420",
                                    "Easter Monday": "20250421",
                                    "Anzac Day": "20250425",
                                    "King's Birthday": "20250609",  # Second Monday in June
                                    "Labour Day": "20251006",  # First Monday in October
                                    "Christmas Eve": "20251224",
                                    "Christmas Day": "20251225",
                                    "Proclamation Day": "20251226",
                                    "New Year's Eve": "20251231"
                                }
                                
                                for holiday, date_str in known_dates_2025.items():
                                    if holiday in name:
                                        date_obj = datetime.strptime(date_str, "%Y%m%d")
                                        log.write(f"Using known 2025 date for {name}: {date_obj}\n")
                                        break
                                        
                                # If we still don't have a date but have a weekday, try to calculate it
                                if not date_obj and date_in_name and cell in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                                    # Find the nearest occurrence of this weekday to the date in the name
                                    weekday_num = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 
                                                'Friday': 4, 'Saturday': 5, 'Sunday': 6}
                                    target_weekday = weekday_num.get(cell)
                                    
                                    if target_weekday is not None:
                                        # Start with the date from the name
                                        current_date = date_in_name
                                        # Calculate days to add to reach target weekday
                                        days_to_add = (target_weekday - current_date.weekday()) % 7
                                        date_obj = current_date + timedelta(days=days_to_add)
                                        log.write(f"Calculated 2025 date for {name} based on weekday {cell}: {date_obj}\n")
                            
                            if date_obj:
                                holidays.append((date_obj, name))
                                log.write(f"Added holiday: {date_obj.date()} - {name}\n")
                            else:
                                log.write(f"Failed to parse date from: '{cell}', skipping\n")

        log.write(f"Found {len(holidays)} holidays to add to calendar\n")
        
        cal = Calendar()
        # Loop through holidays and create all-day events
        for idx, (date_obj, name) in enumerate(holidays, 1):
            log.write(f"Creating event {idx}: {date_obj.date()} - {name}\n")
            event = Event()
            # Set event name with all brackets removed
            
            # Fix King's Birthday spelling
            if "king" in name.lower() and "birthday" in name.lower():
                name = "King's Birthday"
            
            event.name = name
            
            # Set start date (beginning of day)
            start_date = date_obj.date()
            event.begin = pytz.timezone(TIMEZONE).localize(datetime.combine(start_date, datetime.min.time()))
            
            # Make it an all-day event
            event.make_all_day()
            
            # Add end date (the following day for all-day events)
            end_date = start_date + timedelta(days=1)
            event.end = pytz.timezone(TIMEZONE).localize(datetime.combine(end_date, datetime.min.time()))
            
            # Set transparency (doesn't block time in calendar)
            event.transparent = True
            
            # Set the category to Public Holiday
            event.categories = ['Public Holiday']  # Use list format
            
            # Generate a unique ID based on date and holiday name
            event_id = f"{start_date.strftime('%Y%m%d')}-{name.lower().replace(' ', '').replace(chr(39), '')}@southaustralia.holidays"
            event.uid = event_id
            
            cal.events.add(event)
            log.write(f"Added event {idx}: {date_obj.date()} - {name} - All day - Category: Public Holiday\n")
            
        # Process school holidays from the PDF data to add corresponding school terms
        school_holiday_start_end = {}
        school_holiday_events = []
        
        # Extract school holiday dates
        for event in holidays:
            date_obj, name = event
            if "School Holidays" in name:
                # Extract term number
                term_match = re.search(r'Term\s+(\d+)', name)
                if term_match:
                    term_num = term_match.group(1)
                    year = date_obj.year
                    
                    # Store the end date for this holiday period
                    if (year, term_num) not in school_holiday_start_end:
                        school_holiday_start_end[(year, term_num)] = {"end": date_obj}
                    else:
                        school_holiday_start_end[(year, term_num)]["end"] = date_obj
                        
                    # Store the holiday event for later use
                    school_holiday_events.append(event)
        
        log.write(f"Found {len(school_holiday_events)} school holiday events in PDF\n")
        
        # Now add school term events based on the holidays
        for (year, term_num), dates in school_holiday_start_end.items():
            # If we have an end date, assume term starts the next day
            if "end" in dates:
                end_date = dates["end"]
                # Term begins the day after holiday ends
                term_begin_date = end_date + timedelta(days=1)
                
                # Create term begin event
                begin_event = Event()
                begin_event.name = f"Term {term_num} Begins"
                begin_event.begin = pytz.timezone(TIMEZONE).localize(datetime.combine(term_begin_date, datetime.min.time()))
                begin_event.make_all_day()
                begin_event.end = pytz.timezone(TIMEZONE).localize(datetime.combine(term_begin_date + timedelta(days=1), datetime.min.time()))
                begin_event.transparent = True
                begin_event.categories = ['School Term']
                begin_event.uid = f"{term_begin_date.strftime('%Y%m%d')}-term{term_num}begins@southaustralia.education"
                cal.events.add(begin_event)
                log.write(f"Added Term {term_num} Begin event for {year}: {term_begin_date}\n")
                
                # Look for the next term's holiday to find when this term ends
                next_term = str(int(term_num) + 1)
                if int(term_num) == 4:
                    next_term = "1"
                    next_year = year + 1
                else:
                    next_year = year
                    
                # Check if we have the next term's holiday
                if (next_year, next_term) in school_holiday_start_end:
                    next_holiday = school_holiday_start_end[(next_year, next_term)]
                    if "end" in next_holiday:
                        # Term ends the day before holiday begins
                        term_end_date = next_holiday["end"] - timedelta(days=14)  # Approximate 2 weeks holiday
                        
                        # Create term end event
                        end_event = Event()
                        end_event.name = f"Term {term_num} Ends"
                        end_event.begin = pytz.timezone(TIMEZONE).localize(datetime.combine(term_end_date, datetime.min.time()))
                        end_event.make_all_day()
                        end_event.end = pytz.timezone(TIMEZONE).localize(datetime.combine(term_end_date + timedelta(days=1), datetime.min.time()))
                        end_event.transparent = True
                        end_event.categories = ['School Term']
                        end_event.uid = f"{term_end_date.strftime('%Y%m%d')}-term{term_num}ends@southaustralia.education"
                        cal.events.add(end_event)
                        log.write(f"Added Term {term_num} End event for {year}: {term_end_date}\n")
        
        # Create additional School Holiday events to fill gaps
        for (year, term_num), dates in school_holiday_start_end.items():
            if "end" in dates:
                # Create second event for School Holiday (middle of period)
                mid_date = dates["end"] - timedelta(days=7)  # Approx middle of holiday period
                
                mid_event = Event()
                mid_event.name = f"School Holidays - Term {term_num}"
                mid_event.begin = pytz.timezone(TIMEZONE).localize(datetime.combine(mid_date, datetime.min.time()))
                mid_event.make_all_day()
                mid_event.end = pytz.timezone(TIMEZONE).localize(datetime.combine(mid_date + timedelta(days=1), datetime.min.time()))
                mid_event.transparent = True
                mid_event.categories = ['School Holiday']
                mid_event.uid = f"{mid_date.strftime('%Y%m%d')}-schoolholiday{term_num}middle@southaustralia.education"
                cal.events.add(mid_event)
                log.write(f"Added Holiday Middle event for Term {term_num} {year}: {mid_date}\n")

        log.write(f"Total events in calendar: {len(cal.events)}\n")
        
        # Create iCalendar output with custom headers
        log.write("Creating iCalendar file...\n")
        ical_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//South Australia//Public Holidays//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:South Australia Public Holidays and School Terms",
            f"X-WR-TIMEZONE:{TIMEZONE}",
            "X-WR-CALDESC:Public Holidays and School Terms for South Australia"
        ]
        
        # Add all events from the calendar
        for event in cal.events:
            event_lines = event.serialize().split('\r\n')
            ical_lines.append("BEGIN:VEVENT")  # Always start with BEGIN:VEVENT
            
            # Process each line in the event
            for line in event_lines:
                # Skip calendar wrapper lines and empty lines
                if line in ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//South Australia//Public Holidays//EN", 
                           "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "END:VCALENDAR", ""]:
                    continue
                    
                # Skip BEGIN/END:VEVENT as we're adding them manually
                if line in ["BEGIN:VEVENT", "END:VEVENT"]:
                    continue
                    
                # Process SUMMARY line to remove brackets
                if line.startswith("SUMMARY:"):
                    summary = line[8:]  # Get text after "SUMMARY:"
                    # Remove all types of brackets and their contents
                    summary = re.sub(r'\([^)]*\)', '', summary)  # Remove (parentheses)
                    summary = re.sub(r'\[[^\]]*\]', '', summary)  # Remove [square brackets]
                    summary = re.sub(r'\{[^}]*\}', '', summary)  # Remove {curly braces}
                    summary = re.sub(r'<[^>]*>', '', summary)    # Remove <angle brackets>
                    summary = summary.strip()
                    ical_lines.append(f"SUMMARY:{summary}")
                    
                # Process DTSTART line to ensure VALUE=DATE for all-day events  
                elif line.startswith("DTSTART"):
                    if "VALUE=DATE" not in line:
                        match = re.search(r'(\d{8})', line)
                        if match:
                            date_str = match.group(1)
                            ical_lines.append(f"DTSTART;VALUE=DATE:{date_str}")
                        else:
                            ical_lines.append(line)
                    else:
                        ical_lines.append(line)
                
                # Process DTEND line to ensure VALUE=DATE for all-day events
                elif line.startswith("DTEND"):
                    if "VALUE=DATE" not in line:
                        match = re.search(r'(\d{8})', line)
                        if match:
                            date_str = match.group(1)
                            ical_lines.append(f"DTEND;VALUE=DATE:{date_str}")
                        else:
                            ical_lines.append(line)
                    else:
                        ical_lines.append(line)
                
                # Process CATEGORIES line to handle list format from Python
                elif line.startswith("CATEGORIES:"):
                    categories = line[11:].strip()
                    # Handle list format from Python - remove brackets and quotes
                    if categories.startswith("[") and categories.endswith("]"):
                        # Extract contents between brackets
                        categories = categories[1:-1].strip("'\"")
                    # Handle vCategory object representation
                    elif "vCategory" in categories:
                        # Try to extract category name
                        if "Public Holiday" in categories:
                            categories = "Public Holiday"
                        elif "School Term" in categories:
                            categories = "School Term" 
                        elif "School Holiday" in categories:
                            categories = "School Holiday"
                        else:
                            # Default to Public Holiday
                            categories = "Public Holiday"
                    ical_lines.append(f"CATEGORIES:{categories}")
                    
                # Default: add line as is
                else:
                    ical_lines.append(line)
            
            # Add required properties if missing
            properties = [line.split(':', 1)[0] for line in ical_lines[-20:]]  # Check last few lines
            
            if "TRANSP" not in properties:
                ical_lines.append("TRANSP:TRANSPARENT")
                
            if "CATEGORIES" not in properties:
                # Try to guess category based on name
                for i in range(len(ical_lines) - 1, 0, -1):
                    if ical_lines[i].startswith("SUMMARY:"):
                        summary = ical_lines[i][8:]
                        if "Term" in summary and ("Begin" in summary or "End" in summary):
                            ical_lines.append("CATEGORIES:School Term")
                        elif "Holiday" in summary and "School" in summary:
                            ical_lines.append("CATEGORIES:School Holiday") 
                        else:
                            ical_lines.append("CATEGORIES:Public Holiday")
                        break
            
            ical_lines.append("END:VEVENT")  # End every event
            
        ical_lines.append("END:VCALENDAR")
        ical_content = "\n".join(ical_lines)  # Use standard newlines instead of \r\n
        
        # Write to root directory only
        log.write(f"Writing calendar to {ICS_FILE}...\n")
        with open(ICS_FILE, "w") as f:
            f.write(ical_content)
        log.write(f"Successfully wrote calendar to {ICS_FILE}\n")

        # Git operations
        log.write("Configuring Git...\n")
        subprocess.run(['git', 'config', 'user.name', 'GitHub Actions'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'actions@github.com'], check=True)
        
        log.write("Adding files to Git...\n")
        subprocess.run(['git', 'add', '.'], check=True)

        log.write("Committing changes...\n")
        result = subprocess.run(
            ['git', 'commit', '-m', 'Update SA Public Holiday Calendar'],
            capture_output=True, text=True
        )

        commit_output = (result.stdout + result.stderr).lower()
        log.write(f"Git commit output: {commit_output}\n")
        
        if "nothing to commit" not in commit_output:
            log.write("Pushing changes to GitHub...\n")
            push_result = subprocess.run(['git', 'push'], capture_output=True, text=True)
            log.write(f"Git push output: {push_result.stdout + push_result.stderr}\n")
        else:
            log.write("No changes to commit, skipping push\n")

        log.write("Calculating next update time...\n")
        next_run = datetime.now(pytz.timezone(TIMEZONE))
        month = ((next_run.month - 1) // 3 + 1) * 3 + 1
        year = next_run.year + (month > 12)
        month = month if month <= 12 else 1
        next_run = next_run.replace(year=year, month=month, day=1, hour=10, minute=30, second=0, microsecond=0)

        try:
            # Format the day for output
            day = next_run.day
            suffix = get_day_suffix(day)
            formatted_date = f"{day}{suffix} {next_run.strftime('%B %Y at %I:%M%p')}"
            log.write(f"Next scheduled update: {formatted_date}\n")
        except Exception as e:
            formatted_date = "Error formatting date"
            log.write(f"Error formatting next update date: {str(e)}\n")
            print(f"::error::{str(e)}")

        # Prepare success notification
        log.write("Sending success notification via Pushover...\n")
        notification_message = (
            "Success! SA Public Holidays Updated\n\n"
            "SA Public Holiday calendar was successfully updated via GitHub!\n\n"
            f"Next auto-update:\n{formatted_date}\n\n"
            "Have a nice day!"
        )
        log.write(f"Notification message: {notification_message}\n")
        
        # Send notification if API keys are available
        if PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN:
            try:
                response = requests.post(
                    "https://api.pushover.net/1/messages.json", 
                    data={
                        "token": PUSHOVER_API_TOKEN,
                        "user": PUSHOVER_USER_KEY,
                        "message": notification_message
                    },
                    timeout=10  # Add timeout to prevent hanging
                )
                log.write(f"Pushover response: {response.status_code} - {response.text}\n")
                
                # Print the result to the GitHub Actions log as well
                if response.status_code == 200:
                    print("Success notification sent successfully!")
                else:
                    print(f"::warning::Failed to send success notification. Status code: {response.status_code}")
            except Exception as e:
                log.write(f"Error sending Pushover notification: {str(e)}\n")
                print(f"::warning::Exception while sending success notification: {str(e)}")
        else:
            log.write("Pushover API keys not found, skipping notification\n")
            print("::warning::Pushover API keys not found. Success notification not sent.")
            
        log.write("Calendar update completed successfully!\n")

except Exception as e:
    error_msg = str(e).strip()
    print(f"::error::{error_msg}")

    with open(LOG_FILE, "a") as log:
        log.write("\n\nEXCEPTION OCCURRED:\n")
        log.write(f"Error: {error_msg}\n")
        import traceback
        log.write(f"Traceback:\n{traceback.format_exc()}\n")
        log.write("Calendar update failed!\n")

    # Send error notification if API keys are available
    if PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN:
        try:
            send_failure_notification(error_msg)
            with open(LOG_FILE, "a") as log:
                log.write("Error notification sent via Pushover\n")
        except Exception as notification_error:
            with open(LOG_FILE, "a") as log:
                log.write(f"Failed to send error notification: {str(notification_error)}\n")
    else:
        with open(LOG_FILE, "a") as log:
            log.write("Pushover API keys not found, skipping error notification\n")
            
    sys.exit(1)
