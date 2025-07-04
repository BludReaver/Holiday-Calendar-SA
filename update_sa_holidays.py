import io
import sys

# Set UTF-8 encoding for stdout to properly handle emoji characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import re
import requests
import os
from datetime import datetime, timedelta
import uuid
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# Use text-based symbols as fallbacks for emoji in case of console encoding issues
EMOJI_CHECK = "✅"       # Success
EMOJI_WARNING = "⚠️"    # Warning
EMOJI_ERROR = "❌"       # Error
EMOJI_CALENDAR = "📅"    # Calendar
EMOJI_SAVE = "💾"        # Save
EMOJI_SEARCH = "🔍"      # Search
EMOJI_CRYSTAL_BALL = "🔮"  # Future prediction
EMOJI_SUN = "🌞"         # Sun
EMOJI_PLUS = "➕"        # Plus
EMOJI_PENCIL = "📝"      # Pencil

# Configuration settings
TEST_MODE = False  # Set to True to test error notifications
ERROR_SIMULATION = None  # e.g. "public_holidays", "school_terms", "future_term", etc.
ICS_URL = "https://www.officeholidays.com/ics-all/australia/south-australia"
SCHOOL_TERMS_URL = "https://www.education.sa.gov.au/docs/sper/communications/term-calendar/ical-School-term-dates-calendar-2025.ics"
FUTURE_TERMS_URL = "https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools"
OUTPUT_FILE = "SA-Public-Holidays.ics"
SCHOOL_OUTPUT_FILE = "SA-School-Terms-Holidays.ics"

# Notification source URLs
PUBLIC_HOLIDAYS_SOURCE_URL = "https://www.officeholidays.com/subscribe/australia/south-australia"
SCHOOL_TERMS_SOURCE_URL = "https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools"

def clean_event_name(summary: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", summary).strip()

def get_next_update_date() -> str:
    """
    Returns the next monthly update date in the format 'Monday 1st August 2025'.
    Always rolls to the first of the next calendar month.
    """
    today = datetime.now()
    # Compute first day of next month
    if today.month == 12:
        next_date = datetime(today.year + 1, 1, 1)
    else:
        next_date = datetime(today.year, today.month + 1, 1)

    day = next_date.day  # always 1
    # Ordinal suffix logic
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    return next_date.strftime(f"%A {day}{suffix} %B %Y")

def send_failure_notification(error_excerpt: str, failed_calendar=None):
    token = os.environ.get("PUSHOVER_API_TOKEN")
    user = os.environ.get("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover credentials not configured. Skipping failure notification.")
        print(f"Error: {error_excerpt}")
        return

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
        calendar_source = (
            f"🔗 Calendar Sources:\n"
            f"- Public Holidays: {PUBLIC_HOLIDAYS_SOURCE_URL}\n"
            f"- School Terms: {SCHOOL_TERMS_SOURCE_URL}\n"
            f"- Future Terms: {FUTURE_TERMS_URL}\n\n"
        )

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
    resp = httpx.post("https://api.pushover.net/1/messages.json", data={
        "token": token, "user": user, "message": message
    })
    print(f"{EMOJI_CHECK} Failure notification sent" if resp.status_code == 200 else f"{EMOJI_ERROR} Failed to send notification: {resp.text}")

def send_success_notification(future_term_fetched: bool = True):
    token = os.environ.get("PUSHOVER_API_TOKEN")
    user = os.environ.get("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover credentials not configured. Skipping success notification.")
        return

    import httpx
    next_update = get_next_update_date()
    future_note = ""
    if not future_term_fetched:
        future_note = f"{EMOJI_WARNING} Note: Future Term 1 dates could not be fetched.\n\n"

    message = (
        f"{EMOJI_CHECK} SA Calendars Updated {EMOJI_CHECK}\n\n"
        "Your calendars were successfully updated via GitHub!\n\n"
        f"{EMOJI_CALENDAR} Updated calendars:\n"
        "- SA Public Holidays\n"
        "- SA School Terms & Holidays\n\n"
        f"{future_note}"
        f"🕒 Next update: {next_update}\n\n"
        f"{EMOJI_SUN} Have a nice day! {EMOJI_SUN}"
    )
    resp = httpx.post("https://api.pushover.net/1/messages.json", data={
        "token": token, "user": user, "message": message
    })
    print(f"{EMOJI_CHECK} Success notification sent" if resp.status_code == 200 else f"{EMOJI_ERROR} Failed to send notification: {resp.text}")

def parse_ics_date(date_str: str) -> datetime:
    return datetime(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))

def extract_term_dates(content: str) -> List[Dict[str, datetime]]:
    terms = []
    current = {}
    lines = content.splitlines()
    in_event = False
    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
            current = {}
        elif line == "END:VEVENT" and in_event:
            if {"start","end","summary"} <= set(current):
                terms.append(current)
            in_event = False
        elif in_event:
            if line.startswith("DTSTART;VALUE=DATE:"):
                current["start"] = parse_ics_date(line.split(":",1)[1])
            elif line.startswith("DTEND;VALUE=DATE:"):
                # exclusive ⇒ subtract one day
                current["end"] = parse_ics_date(line.split(":",1)[1]) - timedelta(days=1)
            elif line.startswith("SUMMARY"):
                current["summary"] = line.split(":",1)[1]
    return terms

def generate_holiday_periods(terms: List[Dict[str, datetime]]) -> List[Dict[str, datetime]]:
    if not terms:
        return []
    terms_sorted = sorted(terms, key=lambda x: x["start"])
    holidays = []
    for a, b in zip(terms_sorted, terms_sorted[1:]):
        if b["start"] > a["end"] + timedelta(days=1):
            holidays.append({
                "start": a["end"] + timedelta(days=1),
                "end": b["start"] - timedelta(days=1),
                "summary": f"School Holidays (After Term {a['summary'].split()[-1]})"
            })
    return holidays

def format_ics_datetime(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")

def generate_school_calendar(terms, holidays) -> str:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR","VERSION:2.0",
        "PRODID:-//South Australia School Terms and Holidays//EN",
        "X-WR-CALNAME:South Australia School Terms and Holidays",
        "X-WR-CALDESC:School terms and holiday periods in South Australia",
        "REFRESH-INTERVAL;VALUE=DURATION:PT48H",
        "X-PUBLISHED-TTL:PT48H","CALSCALE:GREGORIAN","METHOD:PUBLISH",
        "X-MS-OLK-FORCEINSPECTOROPEN:TRUE"
    ]
    # Term starts & ends...
    for term in terms:
        num = term["summary"].split()[-1]
        # START
        start = format_ics_datetime(term["start"])
        next_day = format_ics_datetime(term["start"] + timedelta(days=1))
        summary_start = f"Term {num} Start"
        if term["start"].year == 2026 and num=="1":
            summary_start = "Term 1 Start (January 27, 2026)"
        lines += [
            "BEGIN:VEVENT","CLASS:PUBLIC",
            f"UID:START-{start}-TERM{num}@sa-school-terms.education.sa.gov.au",
            f"CREATED:{timestamp}",
            f"DESCRIPTION:First day of Term {num} for South Australian schools.\\n\\nInformation provided by education.sa.gov.au",
            "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
            f"DTSTART;VALUE=DATE:{start}",
            f"DTEND;VALUE=DATE:{next_day}",
            f"DTSTAMP:{timestamp}",
            "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{timestamp}","SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:{summary_start}",
            "TRANSP:OPAQUE","X-MICROSOFT-CDO-BUSYSTATUS:BUSY","X-MICROSOFT-CDO-IMPORTANCE:1",
            "X-MICROSOFT-CDO-DISALLOW-COUNTER:FALSE","X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
            "X-MS-OLK-AUTOFILLLOCATION:FALSE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
            "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE","X-MS-OLK-CONFTYPE:0","END:VEVENT"
        ]
        # END (with special 2026 Term 1 handling)
        end = format_ics_datetime(term["end"])
        next_day_end = format_ics_datetime(term["end"] + timedelta(days=1))
        summary_end = f"Term {num} End"
        if term["end"].year == 2026 and num=="1":
            lines += [
                "BEGIN:VEVENT","CLASS:PUBLIC",
                f"UID:TERM1-2026-END-DISTINCT-{uuid.uuid4()}@sa-school-terms.education.sa.gov.au",
                f"CREATED:{timestamp}",
                "DESCRIPTION:Last day of Term 1, 2026 for South Australian schools.\\n\\n"
                "This event marks the end of the first term on April 10, 2026.\\n\\n"
                "Information provided by education.sa.gov.au",
                "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
                f"DTSTART;VALUE=DATE:{end}",
                f"DTEND;VALUE=DATE:{next_day_end}",
                f"DTSTAMP:{timestamp.replace('Z','1Z')}",
                "LOCATION:South Australia Schools","PRIORITY:5",
                f"LAST-MODIFIED:{timestamp.replace('Z','2Z')}","SEQUENCE:2",
                "SUMMARY;LANGUAGE=en-us:Term 1 End - April 10th, 2026",
                "TRANSP:OPAQUE","X-MICROSOFT-CDO-BUSYSTATUS:BUSY","X-MICROSOFT-CDO-IMPORTANCE:1",
                "X-MICROSOFT-CDO-DISALLOW-COUNTER:FALSE","X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
                "X-MS-OLK-AUTOFILLLOCATION:FALSE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
                "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE","X-MS-OLK-CONFTYPE:0","END:VEVENT"
            ]
        else:
            lines += [
                "BEGIN:VEVENT","CLASS:PUBLIC",
                f"UID:END-{end}-TERM{num}@sa-school-terms.education.sa.gov.au",
                f"CREATED:{timestamp}",
                f"DESCRIPTION:Last day of Term {num} for South Australian schools.\\n\\n"
                "Information provided by education.sa.gov.au",
                "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
                f"DTSTART;VALUE=DATE:{end}",
                f"DTEND;VALUE=DATE:{next_day_end}",
                f"DTSTAMP:{timestamp}",
                "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{timestamp}","SEQUENCE:1",
                f"SUMMARY;LANGUAGE=en-us:{summary_end}",
                "TRANSP:OPAQUE","X-MICROSOFT-CDO-BUSYSTATUS:BUSY","X-MICROSOFT-CDO-IMPORTANCE:1",
                "X-MICROSOFT-CDO-DISALLOW-COUNTER:FALSE","X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
                "X-MS-OLK-AUTOFILLLOCATION:FALSE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
                "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE","X-MS-OLK-CONFTYPE:0","END:VEVENT"
            ]

    # Add holiday periods
    for holiday in generate_holiday_periods(terms):
        start = format_ics_datetime(holiday["start"])
        end = format_ics_datetime(holiday["end"] + timedelta(days=1))
        num = holiday["summary"].split()[-1]
        lines += [
            "BEGIN:VEVENT","CLASS:PUBLIC",
            f"UID:HOLIDAY-{start}-TERM{num}@sa-school-terms.education.sa.gov.au",
            f"CREATED:{timestamp}",
            f"DESCRIPTION:School holidays after Term {num} for South Australian schools.\\n\\n"
            "Information provided by education.sa.gov.au",
            "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
            f"DTSTART;VALUE=DATE:{start}",
            f"DTEND;VALUE=DATE:{end}",
            f"DTSTAMP:{timestamp}",
            "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{timestamp}","SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:{holiday['summary']}",
            "TRANSP:OPAQUE","X-MICROSOFT-CDO-BUSYSTATUS:BUSY","X-MICROSOFT-CDO-IMPORTANCE:1",
            "X-MICROSOFT-CDO-DISALLOW-COUNTER:FALSE","X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
            "X-MS-OLK-AUTOFILLLOCATION:FALSE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
            "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE","X-MS-OLK-CONFTYPE:0","END:VEVENT"
        ]

    lines.append("END:VCALENDAR")
    return "\n".join(lines)

def get_future_term1_date() -> Optional[Dict[str, datetime]]:
    print(f"{EMOJI_CRYSTAL_BALL} Checking for future Term 1 start date from {FUTURE_TERMS_URL}...")
    try:
        resp = requests.get(FUTURE_TERMS_URL)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        heading = next((h for h in soup.find_all(["h2","h3"]) if "future term dates" in h.get_text().lower()), None)
        if not heading:
            print(f"{EMOJI_WARNING} Future term dates heading not found")
            return None
        table = heading.find_next("table")
        if not table:
            print(f"{EMOJI_WARNING} Future term dates table not found")
            return None

        year = datetime.now().year + 1
        row = next((r for r in table.find_all("tr")
                    if r.find("th") and r.find("th").get_text().strip().isdigit()
                    and int(r.find("th").get_text().strip()) == year), None)
        if not row:
            print(f"{EMOJI_WARNING} No row for year {year}")
            return None

        cell = row.find("td")
        if not cell:
            return None
        # normalize
        text = re.sub(r"\s+", " ", cell.get_text(separator=" ")).strip()
        parts = text.split("to")
        if len(parts) != 2:
            print(f"{EMOJI_WARNING} Unexpected format: {text}")
            return None
        start = datetime.strptime(f"{parts[0].strip()} {year}", "%d %B %Y")
        end   = datetime.strptime(f"{parts[1].strip()} {year}", "%d %B %Y")
        print(f"{EMOJI_CHECK} Found future Term 1: {start.date()}–{end.date()}")
        return {"start": start, "end": end, "summary": "Term 1"}

    except Exception as e:
        print(f"{EMOJI_WARNING} Error fetching future dates: {e}")
        return None

def update_school_terms() -> bool:
    print(f"{EMOJI_CALENDAR} Downloading school terms from {SCHOOL_TERMS_URL}...")
    if TEST_MODE and ERROR_SIMULATION in ("school_terms","both","connection"):
        raise requests.exceptions.ConnectionError("Simulated")
    if TEST_MODE and ERROR_SIMULATION=="404":
        raise requests.exceptions.HTTPError("404 Simulated")
    resp = requests.get(SCHOOL_TERMS_URL)
    resp.raise_for_status()
    terms = extract_term_dates(resp.text)
    if not terms:
        raise Exception("No school terms found")
    success_future = True
    if not (TEST_MODE and ERROR_SIMULATION=="future_term"):
        fut = get_future_term1_date()
        if fut and not any(t["start"].year==fut["start"].year and t["summary"].endswith("1") for t in terms):
            print(f"{EMOJI_PLUS} Adding future Term 1")
            terms.append(fut)
        elif not fut:
            success_future = False
    terms.sort(key=lambda x: x["start"])
    holidays = generate_holiday_periods(terms)
    content = generate_school_calendar(terms, holidays)
    with open(SCHOOL_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"{EMOJI_CHECK} School terms & holidays written to {SCHOOL_OUTPUT_FILE}")
    return success_future

def update_public_holidays():
    print(f"{EMOJI_CALENDAR} Downloading public holidays from {ICS_URL}...")
    if TEST_MODE and ERROR_SIMULATION in ("public_holidays","both","connection"):
        raise requests.exceptions.ConnectionError("Simulated")
    if TEST_MODE and ERROR_SIMULATION=="404":
        raise requests.exceptions.HTTPError("404 Simulated")
    resp = requests.get(ICS_URL)
    resp.raise_for_status()
    cleaned = []
    for line in resp.text.splitlines():
        if line.startswith("SUMMARY"):
            p = line.find(":")
            if p>-1:
                prefix, val = line[:p+1], line[p+1:]
                cleaned.append(f"{prefix}{clean_event_name(val)}")
            else:
                cleaned.append(line)
        else:
            cleaned.append(line)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned))
    print(f"{EMOJI_CHECK} Public holidays written to {OUTPUT_FILE}")

def main():
    try:
        if TEST_MODE and not ERROR_SIMULATION:
            raise Exception("Simulated general error")
        ok_ph = ok_st = False
        ok_future = True
        try:
            update_public_holidays()
            ok_ph = True
        except Exception as e:
            send_failure_notification(str(e), "public_holidays")
        try:
            ok_future = update_school_terms()
            ok_st = True
        except Exception as e:
            send_failure_notification(str(e), "school_terms")
        if ok_ph and ok_st:
            send_success_notification(ok_future)
        else:
            print(f"{EMOJI_WARNING} One or more updates failed, skipping success.")
            sys.exit(1)
    except Exception as e:
        send_failure_notification(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
