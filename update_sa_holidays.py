#!/usr/bin/env python3
import io
import sys
import os
import re
import uuid
import requests
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# ensure stdout is utf-8 so emojis render
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# emoji fallbacks
EMOJI_CHECK        = "✅"
EMOJI_WARNING      = "⚠️"
EMOJI_ERROR        = "❌"
EMOJI_CALENDAR     = "📅"
EMOJI_SAVE         = "💾"
EMOJI_SEARCH       = "🔍"
EMOJI_CRYSTAL_BALL = "🔮"
EMOJI_SUN          = "🌞"
EMOJI_PLUS         = "➕"
EMOJI_PENCIL       = "📝"

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
TEST_MODE            = False
ERROR_SIMULATION     = None   # e.g. "public_holidays", "school_terms", "future_term", "connection", "404", etc.
ICS_URL             = "https://www.officeholidays.com/ics-all/australia/south-australia"
SCHOOL_TERMS_URL    = "https://www.education.sa.gov.au/docs/sper/communications/term-calendar/ical-School-term-dates-calendar-2025.ics"
FUTURE_TERMS_URL    = "https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools"
OUTPUT_FILE         = "SA-Public-Holidays.ics"
SCHOOL_OUTPUT_FILE  = "SA-School-Terms-Holidays.ics"

PUBLIC_HOLIDAYS_SOURCE_URL = "https://www.officeholidays.com/subscribe/australia/south-australia"
SCHOOL_TERMS_SOURCE_URL    = "https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools"

# ─── UTILITIES ────────────────────────────────────────────────────────────────────
def clean_event_name(summary: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", summary).strip()

def get_next_update_date() -> str:
    """
    Returns the first of next calendar month, e.g.
    'Friday 1st August 2025'
    """
    today = datetime.now()
    if today.month == 12:
        next_month = datetime(today.year + 1, 1, 1)
    else:
        next_month = datetime(today.year, today.month + 1, 1)

    day = next_month.day  # always 1
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = {1:"st",2:"nd",3:"rd"}.get(day % 10, "th")

    fmt = f"%A {day}{suffix} %B %Y"
    return next_month.strftime(fmt)

def send_failure_notification(error_excerpt: str, failed_calendar: Optional[str]=None):
    token = os.getenv("PUSHOVER_API_TOKEN")
    user  = os.getenv("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover creds missing—skipping failure notification.")
        print("Error:", error_excerpt)
        return

    if failed_calendar == "public_holidays":
        cal_info   = f"{EMOJI_CALENDAR} Public Holidays update failed\n\n"
        cal_source = f"🔗 Source: {PUBLIC_HOLIDAYS_SOURCE_URL}\n\n"
    elif failed_calendar == "school_terms":
        cal_info   = f"{EMOJI_CALENDAR} School Terms update failed\n\n"
        cal_source = f"🔗 Source: {SCHOOL_TERMS_SOURCE_URL}\n\n"
    elif failed_calendar == "future_term":
        cal_info   = f"{EMOJI_CALENDAR} Future Term-1 fetch failed\n\n"
        cal_source = f"🔗 Source: {FUTURE_TERMS_URL}\n\n"
    else:
        cal_info   = f"{EMOJI_CALENDAR} Calendar update failed\n\n"
        cal_source = (
            f"🔗 Sources:\n"
            f"- Public Holidays: {PUBLIC_HOLIDAYS_SOURCE_URL}\n"
            f"- School Terms:    {SCHOOL_TERMS_SOURCE_URL}\n"
            f"- Future Terms:    {FUTURE_TERMS_URL}\n\n"
        )

    message = (
        "‼️ SA Calendar Update Failed ‼️\n\n"
        f"{cal_info}"
        "Check GitHub Actions logs:\n"
        "1. Navigate to your repo\n"
        "2. Click **Actions**\n"
        "3. Open the failed run\n\n"
        f"{cal_source}"
        f"📝 Error Log:\n{error_excerpt}"
    )

    resp = httpx.post(
        "https://api.pushover.net/1/messages.json",
        data={"token":token, "user":user, "message":message}
    )
    if resp.status_code == 200:
        print(f"{EMOJI_CHECK} Failure notification sent")
    else:
        print(f"{EMOJI_ERROR} Notification failed:", resp.text)

def send_success_notification(future_term_fetched: bool = True):
    token = os.getenv("PUSHOVER_API_TOKEN")
    user  = os.getenv("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover creds missing—skipping success notification.")
        return

    next_up = get_next_update_date()
    note = ""
    if not future_term_fetched:
        note = f"{EMOJI_WARNING} Could not fetch future Term-1 dates.\n\n"

    message = (
        f"{EMOJI_CHECK} SA Calendars Updated! {EMOJI_CHECK}\n\n"
        "✓ Public Holidays\n"
        "✓ School Terms & Holidays\n\n"
        f"{note}"
        f"🕒 Next update: {next_up}\n\n"
        f"{EMOJI_SUN} Have a great day! {EMOJI_SUN}"
    )

    resp = httpx.post(
        "https://api.pushover.net/1/messages.json",
        data={"token":token, "user":user, "message":message}
    )
    if resp.status_code == 200:
        print(f"{EMOJI_CHECK} Success notification sent")
    else:
        print(f"{EMOJI_ERROR} Notification failed:", resp.text)

def parse_ics_date(s: str) -> datetime:
    return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]))

def extract_term_dates(cal_text: str) -> List[Dict[str, datetime]]:
    lines = cal_text.splitlines()
    terms, current = [], {}
    in_ev = False

    for L in lines:
        if L == "BEGIN:VEVENT":
            in_ev = True
            current = {}
        elif L == "END:VEVENT" and in_ev:
            if {"start","end","summary"} <= set(current):
                terms.append(current)
            in_ev = False
        elif in_ev:
            if L.startswith("DTSTART;VALUE=DATE:"):
                current["start"] = parse_ics_date(L.split(":",1)[1])
            elif L.startswith("DTEND;VALUE=DATE:"):
                dt = parse_ics_date(L.split(":",1)[1])
                current["end"] = dt - timedelta(days=1)
            elif L.startswith("SUMMARY"):
                current["summary"] = L.split(":",1)[1]
    return terms

def generate_holiday_periods(terms: List[Dict[str, datetime]]) -> List[Dict[str, datetime]]:
    if not terms:
        return []
    t_sorted = sorted(terms, key=lambda t: t["start"])
    hols = []
    for a, b in zip(t_sorted, t_sorted[1:]):
        if b["start"] > a["end"] + timedelta(days=1):
            num = a["summary"].split()[-1]
            hols.append({
                "start": a["end"] + timedelta(days=1),
                "end":   b["start"] - timedelta(days=1),
                "summary": f"School Holidays (After Term {num})"
            })
    return hols

def format_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")

def generate_school_calendar(terms: List[Dict[str, datetime]], holidays: List[Dict[str, datetime]]) -> str:
    ts = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    cal = [
        "BEGIN:VCALENDAR","VERSION:2.0",
        "PRODID:-//South Australia School Terms and Holidays//EN",
        "X-WR-CALNAME:South Australia School Terms and Holidays",
        "X-WR-CALDESC:School terms and holiday periods in South Australia",
        "REFRESH-INTERVAL;VALUE=DURATION:PT48H","X-PUBLISHED-TTL:PT48H",
        "CALSCALE:GREGORIAN","METHOD:PUBLISH","X-MS-OLK-FORCEINSPECTOROPEN:TRUE"
    ]

    # Term starts & ends
    for term in terms:
        num = term["summary"].split()[-1]
        # START
        start = format_dt(term["start"])
        nextd = format_dt(term["start"] + timedelta(days=1))
        summ = f"Term {num} Start"
        if term["start"].year == 2026 and num == "1":
            summ = "Term 1 Start (January 27, 2026)"
        cal += [
            "BEGIN:VEVENT","CLASS:PUBLIC",
            f"UID:START-{start}-TERM{num}@sa-school-terms.education.sa.gov.au",
            f"CREATED:{ts}",
            f"DESCRIPTION:First day of Term {num} for South Australian schools.\\n\\nInformation provided by education.sa.gov.au",
            "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
            f"DTSTART;VALUE=DATE:{start}","DTEND;VALUE=DATE:{nextd}","DTSTAMP:{ts}",
            "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{ts}","SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:{summ}",
            "TRANSP:OPAQUE","X-MICROSOFT-CDO-BUSYSTATUS:BUSY","X-MICROSOFT-CDO-IMPORTANCE:1",
            "X-MICROSOFT-CDO-DISALLOW-COUNTER:FALSE","X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
            "X-MS-OLK-AUTOFILLLOCATION:FALSE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
            "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE","X-MICROSOFT-CDO-CONFTYPE:0","END:VEVENT"
        ]
        # END
        end = format_dt(term["end"])
        nextde = format_dt(term["end"] + timedelta(days=1))
        summ_end = f"Term {num} End"
        if term["end"].year == 2026 and num == "1":
            # special distinct 2026 Term1-End
            cal += [
                "BEGIN:VEVENT","CLASS:PUBLIC",
                f"UID:TERM1-2026-END-DISTINCT-{uuid.uuid4()}@sa-school-terms.education.sa.gov.au",
                f"CREATED:{ts}",
                "DESCRIPTION:Last day of Term 1, 2026 for South Australian schools.\\n\\n"
                "This event marks the end of the first term on April 10, 2026.\\n\\n"
                "Information provided by education.sa.gov.au",
                "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
                f"DTSTART;VALUE=DATE:{end}","DTEND;VALUE=DATE:{nextde}",
                f"DTSTAMP:{ts.replace('Z','1Z')}",
                "LOCATION:South Australia Schools","PRIORITY:5",
                f"LAST-MODIFIED:{ts.replace('Z','2Z')}","SEQUENCE:2",
                "SUMMARY;LANGUAGE=en-us:Term 1 End - April 10th, 2026",
                "TRANSP:OPAQUE","X-MICROSOFT-CDO-BUSYSTATUS:BUSY","X-MICROSOFT-CDO-IMPORTANCE:1",
                "X-MICROSOFT-CDO-DISALLOW-COUNTER:FALSE","X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
                "X-MS-OLK-AUTOFILLLOCATION:FALSE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
                "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE","X-MICROSOFT-CDO-CONFTYPE:0","END:VEVENT"
            ]
        else:
            cal += [
                "BEGIN:VEVENT","CLASS:PUBLIC",
                f"UID:END-{end}-TERM{num}@sa-school-terms.education.sa.gov.au",
                f"CREATED:{ts}",
                f"DESCRIPTION:Last day of Term {num} for South Australian schools.\\n\\nInformation provided by education.sa.gov.au",
                "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
                f"DTSTART;VALUE=DATE:{end}","DTEND;VALUE=DATE:{nextde}","DTSTAMP:{ts}",
                "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{ts}","SEQUENCE:1",
                f"SUMMARY;LANGUAGE=en-us:{summ_end}",
                "TRANSP:OPAQUE","X-MICROSOFT-CDO-BUSYSTATUS:BUSY","X-MICROSOFT-CDO-IMPORTANCE:1",
                "X-MICROSOFT-CDO-DISALLOW-COUNTER:FALSE","X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
                "X-MS-OLK-AUTOFILLLOCATION:FALSE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
                "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE","X-MICROSOFT-CDO-CONFTYPE:0","END:VEVENT"
            ]

    # Holidays
    for hol in holidays:
        start = format_dt(hol["start"])
        end   = format_dt(hol["end"] + timedelta(days=1))
        num   = hol["summary"].split()[-1]
        cal += [
            "BEGIN:VEVENT","CLASS:PUBLIC",
            f"UID:HOLIDAY-{start}-TERM{num}@sa-school-terms.education.sa.gov.au",
            f"CREATED:{ts}",
            f"DESCRIPTION:School holidays after Term {num} for South Australian schools.\\n\\nInformation provided by education.sa.gov.au",
            "URL:https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools",
            f"DTSTART;VALUE=DATE:{start}","DTEND;VALUE=DATE:{end}","DTSTAMP:{ts}",
            "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{ts}","SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:{hol['summary']}",
            "TRANSP:OPAQUE","X-MICROSOFT-CDO-BUSYSTATUS:BUSY","X-MICROSOFT-CDO-IMPORTANCE:1",
            "X-MICROSOFT-CDO-DISALLOW-COUNTER:FALSE","X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
            "X-MS-OLK-AUTOFILLLOCATION:FALSE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
            "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE","X-MICROSOFT-CDO-CONFTYPE:0","END:VEVENT"
        ]

    cal.append("END:VCALENDAR")
    return "\n".join(cal)

def get_future_term1_date() -> Optional[Dict[str, datetime]]:
    print(f"{EMOJI_CRYSTAL_BALL} Checking future Term-1 from {FUTURE_TERMS_URL}")
    try:
        r = requests.get(FUTURE_TERMS_URL); r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        heading = next((h for h in soup.find_all(["h2","h3"])
                        if "future term dates" in h.get_text().lower()), None)
        if not heading:
            print(f"{EMOJI_WARNING} No 'Future term dates' heading found")
            return None
        table = heading.find_next("table")
        if not table:
            print(f"{EMOJI_WARNING} No table after heading")
            return None

        year = datetime.now().year + 1
        for row in table.find_all("tr"):
            th = row.find("th")
            if th and th.get_text().strip().isdigit() and int(th.get_text()) == year:
                td = row.find("td")
                if not td:
                    return None
                text = re.sub(r"\s+", " ", td.get_text(separator=" ")).strip()
                parts = text.split("to")
                if len(parts) != 2:
                    print(f"{EMOJI_WARNING} Unexpected format: {text}")
                    return None
                start = datetime.strptime(f"{parts[0].strip()} {year}", "%d %B %Y")
                end   = datetime.strptime(f"{parts[1].strip()} {year}", "%d %B %Y")
                print(f"{EMOJI_CHECK} Future Term-1: {start.date()} → {end.date()}")
                return {"start": start, "end": end, "summary": "Term 1"}
        print(f"{EMOJI_WARNING} No row for year {year}")
        return None

    except Exception as e:
        print(f"{EMOJI_WARNING} Error fetching future term: {e}")
        return None

def update_school_terms() -> bool:
    print(f"{EMOJI_CALENDAR} Downloading school terms…")
    if TEST_MODE and ERROR_SIMULATION in ("school_terms","both","connection"):
        raise requests.exceptions.ConnectionError("Simulated")
    if TEST_MODE and ERROR_SIMULATION == "404":
        raise requests.exceptions.HTTPError("404 Simulated")

    r = requests.get(SCHOOL_TERMS_URL); r.raise_for_status()
    terms = extract_term_dates(r.text)
    if not terms:
        raise Exception("No school terms found")

    future_ok = True
    if not (TEST_MODE and ERROR_SIMULATION == "future_term"):
        fut = get_future_term1_date()
        if fut and not any(t["start"].year == fut["start"].year and t["summary"].endswith("1") for t in terms):
            print(f"{EMOJI_PLUS} Adding future Term-1")
            terms.append(fut)
        elif not fut:
            future_ok = False

    terms.sort(key=lambda x: x["start"])
    holidays = generate_holiday_periods(terms)
    cal_text = generate_school_calendar(terms, holidays)

    with open(SCHOOL_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(cal_text)
    print(f"{EMOJI_SAVE} Wrote {SCHOOL_OUTPUT_FILE}")

    return future_ok

def update_public_holidays():
    print(f"{EMOJI_CALENDAR} Downloading public holidays…")
    if TEST_MODE and ERROR_SIMULATION in ("public_holidays","both","connection"):
        raise requests.exceptions.ConnectionError("Simulated")
    if TEST_MODE and ERROR_SIMULATION == "404":
        raise requests.exceptions.HTTPError("404 Simulated")

    r = requests.get(ICS_URL); r.raise_for_status()
    cleaned = []
    for L in r.text.splitlines():
        if L.startswith("SUMMARY"):
            p = L.find(":")
            if p > -1:
                cleaned.append(f"{L[:p+1]}{clean_event_name(L[p+1:])}")
            else:
                cleaned.append(L)
        else:
            cleaned.append(L)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned))
    print(f"{EMOJI_SAVE} Wrote {OUTPUT_FILE}")

def main():
    try:
        if TEST_MODE and not ERROR_SIMULATION:
            raise Exception("Simulated general error")

        ok_ph     = False
        ok_st     = False
        ok_future = True

        try:
            update_public_holidays()
            ok_ph = True
        except Exception as e:
            print(f"{EMOJI_ERROR} Public holidays failed: {e}")
            send_failure_notification(str(e), "public_holidays")

        try:
            ok_future = update_school_terms()
            ok_st     = True
        except Exception as e:
            print(f"{EMOJI_ERROR} School terms failed: {e}")
            send_failure_notification(str(e), "school_terms")

        if ok_ph and ok_st:
            send_success_notification(ok_future)
        else:
            print(f"{EMOJI_WARNING} Skipping success notification; one or more failed.")
            sys.exit(1)

    except Exception as e:
        print(f"{EMOJI_ERROR} Fatal error: {e}")
        send_failure_notification(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
