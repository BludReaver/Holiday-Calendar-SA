#!/usr/bin/env python3
import io
import sys
import os
import re
import uuid
import requests
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
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

# Public holidays
ICS_URL              = "https://www.officeholidays.com/ics-all/australia/south-australia"

# School terms ICS (works in browsers; may 403/404 on CI IPs)
SCHOOL_TERMS_URL     = "https://www.education.sa.gov.au/docs/sper/communications/term-calendar/ical-School-term-dates-calendar-2025.ics"

# Main page for term dates (HTML fallback + future terms)
FUTURE_TERMS_URL     = "https://www.education.sa.gov.au/parents-and-families/term-dates-south-australian-state-schools"

OUTPUT_FILE          = "SA-Public-Holidays.ics"
SCHOOL_OUTPUT_FILE   = "SA-School-Terms-Holidays.ics"

PUBLIC_HOLIDAYS_SOURCE_URL = "https://www.officeholidays.com/subscribe/australia/south-australia"
SCHOOL_TERMS_SOURCE_URL    = FUTURE_TERMS_URL

# Browser-like headers to prevent simple gating on Education SA endpoints
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
    "Accept": "text/calendar, text/html;q=0.9, */*;q=0.8",
    "Referer": SCHOOL_TERMS_SOURCE_URL,
    "Accept-Language": "en-AU,en;q=0.9",
    "Connection": "keep-alive",
}

# ─── UTILITIES ────────────────────────────────────────────────────────────────────
def clean_event_name(summary: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", summary).strip()

def get_next_update_date() -> str:
    today = datetime.now()
    if today.month == 12:
        next_month = datetime(today.year + 1, 1, 1)
    else:
        next_month = datetime(today.year, today.month + 1, 1)
    day = next_month.day  # always 1
    suffix = "th" if 4 <= day <= 20 or 24 <= day <= 30 else {1:"st",2:"nd",3:"rd"}.get(day % 10, "th")
    return next_month.strftime(f"%A {day}{suffix} %B %Y")

def send_failure_notification(error_excerpt: str, failed_calendar: Optional[str]=None):
    token = os.getenv("PUSHOVER_API_TOKEN"); user = os.getenv("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover creds missing—skipping failure notification.")
        print("Error:", error_excerpt); return

    if failed_calendar == "public_holidays":
        cal_info, cal_source = f"{EMOJI_CALENDAR} Public Holidays update failed\n\n", f"🔗 Source: {PUBLIC_HOLIDAYS_SOURCE_URL}\n\n"
    elif failed_calendar == "school_terms":
        cal_info, cal_source = f"{EMOJI_CALENDAR} School Terms update failed\n\n", f"🔗 Source: {SCHOOL_TERMS_SOURCE_URL}\n\n"
    elif failed_calendar == "future_term":
        cal_info, cal_source = f"{EMOJI_CALENDAR} Future Term-1 fetch failed\n\n", f"🔗 Source: {FUTURE_TERMS_URL}\n\n"
    else:
        cal_info = f"{EMOJI_CALENDAR} Calendar update failed\n\n"
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
    try:
        resp = httpx.post("https://api.pushover.net/1/messages.json", data={"token":token, "user":user, "message":message})
        print(f"{EMOJI_CHECK} Failure notification sent" if resp.status_code == 200 else f"{EMOJI_ERROR} Notification failed: {resp.text}")
    except Exception as e:
        print(f"{EMOJI_ERROR} Notification exception: {e}")

def send_success_notification(future_term_fetched: bool = True):
    token = os.getenv("PUSHOVER_API_TOKEN"); user = os.getenv("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover creds missing—skipping success notification."); return
    note = f"{EMOJI_WARNING} Could not fetch future Term-1 dates.\n\n" if not future_term_fetched else ""
    message = (
        f"{EMOJI_CHECK} SA Calendars Updated! {EMOJI_CHECK}\n\n"
        "✓ Public Holidays\n"
        "✓ School Terms & Holidays\n\n"
        f"{note}"
        f"🕒 Next update: {get_next_update_date()}\n\n"
        f"{EMOJI_SUN} Have a great day! {EMOJI_SUN}"
    )
    try:
        resp = httpx.post("https://api.pushover.net/1/messages.json", data={"token":token, "user":user, "message":message})
        print(f"{EMOJI_CHECK} Success notification sent" if resp.status_code == 200 else f"{EMOJI_ERROR} Notification failed: {resp.text}")
    except Exception as e:
        print(f"{EMOJI_ERROR} Notification exception: {e}")

# ─── ICS PARSING ────────────────────────────────────────────────────────────────
def parse_ics_date(s: str) -> datetime:
    return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]))

def extract_term_dates(cal_text: str) -> List[Dict[str, datetime]]:
    lines = cal_text.splitlines()
    terms, current, in_ev = [], {}, False
    for L in lines:
        if L == "BEGIN:VEVENT":
            in_ev = True; current = {}
        elif L == "END:VEVENT" and in_ev:
            if {"start","end","summary"} <= set(current):
                terms.append(current)
            in_ev = False
        elif in_ev:
            if L.startswith("DTSTART;VALUE=DATE:"):
                current["start"] = parse_ics_date(L.split(":",1)[1])
            elif L.startswith("DTEND;VALUE=DATE:"):
                current["end"] = parse_ics_date(L.split(":",1)[1]) - timedelta(days=1)
            elif L.startswith("SUMMARY"):
                current["summary"] = L.split(":",1)[1]
    return terms

def generate_holiday_periods(terms: List[Dict[str, datetime]]) -> List[Dict[str, datetime]]:
    if not terms: return []
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
            "URL:https://www.education.sa.gov.au/parents-and-families/term-dates-south-australian-state-schools",
            f"DTSTART;VALUE=DATE:{start}","DTEND;VALUE=DATE:{nextd}","DTSTAMP:{ts}",
            "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{ts}","SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:{summ}",
            "TRANSP:OPAQUE","X-MICROSOFT-CDO-BUSYSTATUS:BUSY","X-MICROSOFT-CDO-IMPORTANCE:1",
            "X-MICROSOFT-CDO-DISALLOW-COUNTER:FALSE","X-MS-OLK-ALLOWEXTERNCHECK:TRUE",
            "X-MS-OLK-AUTOFILLLOCATION:FALSE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE",
            "X-MICROSOFT-MSNCALENDAR-ALLDAYEVENT:TRUE","X-MICROSOFT-CDO-CONFTYPE:0","END:VEVENT"
        ]
        end = format_dt(term["end"])
        nextde = format_dt(term["end"] + timedelta(days=1))
        summ_end = f"Term {num} End"
        if term["end"].year == 2026 and num == "1":
            cal += [
                "BEGIN:VEVENT","CLASS:PUBLIC",
                f"UID:TERM1-2026-END-DISTINCT-{uuid.uuid4()}@sa-school-terms.education.sa.gov.au",
                f"CREATED:{ts}",
                "DESCRIPTION:Last day of Term 1, 2026 for South Australian schools.\\n\\n"
                "This event marks the end of the first term on April 10, 2026.\\n\\n"
                "Information provided by education.sa.gov.au",
                "URL:https://www.education.sa.gov.au/parents-and-families/term-dates-south-australian-state-schools",
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
                "URL:https://www.education.sa.gov.au/parents-and-families/term-dates-south-australian-state-schools",
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
            "URL:https://www.education.sa.gov.au/parents-and-families/term-dates-south-australian-state-schools",
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

# ─── HTML SCRAPE FALLBACK ──────────────────────────────────────────────────────
TERM_ROW_RE = re.compile(r"^\s*Term\s*(\d+)\s*$", re.IGNORECASE)
DATE_RANGE_RE = re.compile(
    r"(\d{1,2}\s+[A-Za-z]+)\s*(?:–|-|to)\s*(\d{1,2}\s+[A-Za-z]+)",
    re.IGNORECASE
)

def _find_table_near_year(soup: BeautifulSoup, year: int) -> Optional[Tuple[BeautifulSoup, int]]:
    """
    Find a table that likely contains the given year's term dates.
    Strategy: look for a heading containing the year; else pick a table that mentions 'Term 1'.
    Returns (table, year_detected) if found.
    """
    # Try headings with the year
    for h in soup.find_all(["h1","h2","h3","h4"]):
        text = h.get_text(" ", strip=True)
        if str(year) in text and ("term" in text.lower() or "school" in text.lower()):
            tbl = h.find_next("table")
            if tbl: return tbl, year
    # Fallback: find a table containing 'Term 1'
    for tbl in soup.find_all("table"):
        if "term 1" in tbl.get_text(" ", strip=True).lower():
            return tbl, year
    return None

def scrape_terms_from_html() -> List[Dict[str, datetime]]:
    """
    Scrape the term dates page to extract Term 1..4 for the current year.
    """
    print(f"{EMOJI_SEARCH} Scraping term dates HTML fallback from {FUTURE_TERMS_URL}")
    r = requests.get(FUTURE_TERMS_URL, headers=BROWSER_HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    year = datetime.now().year
    found = _find_table_near_year(soup, year)
    if not found:
        # Try current year; if not, try previous/next just in case
        for y in (year, year+1, year-1):
            found = _find_table_near_year(soup, y)
            if found: year = y; break
    if not found:
        raise Exception("Could not locate a term dates table on the page")

    table, year = found
    # Expect rows where first cell mentions 'Term 1'..'Term 4', and second cell has a date range
    terms: List[Dict[str, datetime]] = []
    for row in table.find_all("tr"):
        cells = row.find_all(["td","th"])
        if len(cells) < 2: continue
        term_label = cells[0].get_text(" ", strip=True)
        m_term = TERM_ROW_RE.match(term_label)
        if not m_term: continue
        term_num = m_term.group(1)

        text = re.sub(r"\s+", " ", cells[1].get_text(" ", strip=True))
        m_range = DATE_RANGE_RE.search(text)
        if not m_range:
            # Some pages put the date range in subsequent cells; scan all cells
            for c in cells[1:]:
                t2 = re.sub(r"\s+", " ", c.get_text(" ", strip=True))
                m_range = DATE_RANGE_RE.search(t2)
                if m_range: break
        if not m_range: continue

        start_s, end_s = m_range.groups()
        # Infer months across year-boundaries (Term 1 may start in Jan/Feb; Term 4 ends in Dec)
        try:
            start = datetime.strptime(f"{start_s} {year}", "%d %B %Y")
            # If end month earlier than start (e.g., Jan to Apr but year set wrong), adjust
            end_try = datetime.strptime(f"{end_s} {year}", "%d %B %Y")
            if end_try < start:
                end_try = datetime.strptime(f"{end_s} {year+1}", "%d %B %Y")
            end = end_try
        except ValueError:
            # Try abbreviated month names
            start = datetime.strptime(f"{start_s} {year}", "%d %b %Y")
            end   = datetime.strptime(f"{end_s} {year}", "%d %b %Y")
            if end < start:
                end = datetime.strptime(f"{end_s} {year+1}", "%d %b %Y")

        terms.append({"start": start, "end": end, "summary": f"Term {term_num}"})

    if len(terms) < 4:
        print(f"{EMOJI_WARNING} Only parsed {len(terms)} terms from HTML")
    else:
        print(f"{EMOJI_CHECK} Parsed {len(terms)} terms from HTML")

    return sorted(terms, key=lambda t: t["start"])

# ─── SCHOOL TERMS UPDATE ───────────────────────────────────────────────────────
def get_future_term1_date() -> Optional[Dict[str, datetime]]:
    print(f"{EMOJI_CRYSTAL_BALL} Checking future Term-1 from {FUTURE_TERMS_URL}")
    try:
        r = requests.get(FUTURE_TERMS_URL, headers=BROWSER_HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        heading = next((h for h in soup.find_all(["h2","h3"]) if "future term dates" in h.get_text().lower()), None)
        if not heading: return None
        table = heading.find_next("table")
        if not table: return None

        year = datetime.now().year + 1
        for row in table.find_all("tr"):
            th = row.find("th")
            if th and th.get_text().strip().isdigit() and int(th.get_text()) == year:
                td = row.find("td")
                if not td: return None
                text = re.sub(r"\s+", " ", td.get_text(separator=" ")).strip()
                parts = text.split("to")
                if len(parts) != 2: return None
                start = datetime.strptime(f"{parts[0].strip()} {year}", "%d %B %Y")
                end   = datetime.strptime(f"{parts[1].strip()} {year}", "%d %B %Y")
                print(f"{EMOJI_CHECK} Future Term-1: {start.date()} → {end.date()}")
                return {"start": start, "end": end, "summary": "Term 1"}
        return None
    except Exception as e:
        print(f"{EMOJI_WARNING} Error fetching future term: {e}")
        return None

def update_school_terms() -> bool:
    print(f"{EMOJI_CALENDAR} Downloading school terms…")
    cal_text = None
    terms: List[Dict[str, datetime]] = []

    # 1) Try ICS first (may 403/404 on CI IPs)
    try:
        r = requests.get(SCHOOL_TERMS_URL, headers=BROWSER_HEADERS, timeout=30)
        r.raise_for_status()
        terms = extract_term_dates(r.text)
        if not terms:
            raise Exception("No school terms found in ICS")
        print(f"{EMOJI_CHECK} ICS fetched successfully")
    except Exception as e:
        print(f"{EMOJI_WARNING} ICS fetch failed ({e}); falling back to HTML scrape")
        # 2) Fallback: scrape HTML table to construct terms
        terms = scrape_terms_from_html()
        if not terms:
            raise Exception("HTML fallback produced no terms")

    future_ok = True
    fut = get_future_term1_date()
    if fut and not any(t["start"].year == fut["start"].year and t["summary"].endswith("1") for t in terms):
        print(f"{EMOJI_PLUS} Adding future Term-1"); terms.append(fut)
    elif not fut:
        future_ok = False

    terms.sort(key=lambda x: x["start"])
    holidays = generate_holiday_periods(terms)
    cal_text = generate_school_calendar(terms, holidays)

    with open(SCHOOL_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(cal_text)
    print(f"{EMOJI_SAVE} Wrote {SCHOOL_OUTPUT_FILE}")
    return future_ok

# ─── PUBLIC HOLIDAYS UPDATE ────────────────────────────────────────────────────
def update_public_holidays():
    print(f"{EMOJI_CALENDAR} Downloading public holidays…")
    r = requests.get(ICS_URL, timeout=30); r.raise_for_status()
    cleaned = []
    for L in r.text.splitlines():
        if L.startswith("SUMMARY"):
            p = L.find(":")
            cleaned.append(f"{L[:p+1]}{clean_event_name(L[p+1:])}" if p > -1 else L)
        else:
            cleaned.append(L)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned))
    print(f"{EMOJI_SAVE} Wrote {OUTPUT_FILE}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    try:
        ok_ph, ok_st, ok_future = False, False, True

        try:
            update_public_holidays(); ok_ph = True
        except Exception as e:
            print(f"{EMOJI_ERROR} Public holidays failed: {e}")
            send_failure_notification(str(e), "public_holidays")

        try:
            ok_future = update_school_terms(); ok_st = True
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
