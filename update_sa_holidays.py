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

# Public holidays (unchanged)
ICS_URL              = "https://www.officeholidays.com/ics-all/australia/south-australia"

# Official SA school terms ICS (may 403/404 from CI)
SCHOOL_TERMS_URL     = "https://www.education.sa.gov.au/docs/sper/communications/term-calendar/ical-School-term-dates-calendar-2025.ics"

# Human page (usually also gated from CI)
FUTURE_TERMS_URL     = "https://www.education.sa.gov.au/parents-and-families/term-dates-south-australian-state-schools"

OUTPUT_FILE          = "SA-Public-Holidays.ics"
SCHOOL_OUTPUT_FILE   = "SA-School-Terms-Holidays.ics"

PUBLIC_HOLIDAYS_SOURCE_URL = "https://www.officeholidays.com/subscribe/australia/south-australia"
SCHOOL_TERMS_SOURCE_URL    = "https://www.schoolholidayssa.com.au/sa-school-holiday-dates-2025/"

# Browser-like headers (official endpoints sometimes require this)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
    "Accept": "text/calendar, text/html;q=0.9, */*;q=0.8",
    "Referer": FUTURE_TERMS_URL,
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
        cal_source = f"🔗 Source: https://www.education.sa.gov.au\n\n"
    elif failed_calendar == "future_term":
        cal_info   = f"{EMOJI_CALENDAR} Future Term-1 fetch failed\n\n"
        cal_source = f"🔗 Source: {FUTURE_TERMS_URL}\n\n"
    else:
        cal_info   = f"{EMOJI_CALENDAR} Calendar update failed\n\n"
        cal_source = (
            f"🔗 Sources:\n"
            f"- Public Holidays: {PUBLIC_HOLIDAYS_SOURCE_URL}\n"
            f"- School Terms:    https://www.education.sa.gov.au\n"
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
            "URL:https://www.education.sa.gov.au/parents-and-families/term-dates-south-australian-state-schools",
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

# ─── ALT SOURCE SCRAPING ─────────────────────────────────────────────────────────
def _fetch_text(url: str, *, headers=None, timeout=30) -> Optional[str]:
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"{EMOJI_WARNING} Fetch failed from {url}: {e}")
        return None

def _parse_au_date(s: str) -> datetime:
    s = s.strip()
    s = re.sub(r"^[A-Za-z]+,?\s+", "", s)           # remove weekday if present
    s = s.replace("–", "-")                        # normalize en-dash
    s = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s)     # remove ordinals
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date: {s}")

def _extract_terms_from_text(text: str, year: int) -> List[Dict[str, datetime]]:
    t = re.sub(r"\s+", " ", text.replace("\u2013", "-")).strip()
    terms: List[Dict[str, datetime]] = []
    for n in range(1, 5):
        patt = rf"Term\s*{n}\s*[:,\-]?\s*(?:[A-Za-z]+,?\s*)?(\d{{1,2}}\s+\w+\s+{year})\s*(?:-|to|–)\s*(?:[A-Za-z]+,?\s*)?(\d{{1,2}}\s+\w+\s+{year})"
        m = re.search(patt, t, flags=re.I)
        if not m:
            return []
        start_dt = _parse_au_date(m.group(1))
        end_dt   = _parse_au_date(m.group(2))
        terms.append({"start": start_dt, "end": end_dt, "summary": f"Term {n}"})
    return terms

def _extract_term1_from_text(text: str, year: int) -> Optional[Dict[str, datetime]]:
    t = re.sub(r"\s+", " ", text.replace("\u2013", "-")).strip()
    patt = rf"Term\s*1\s*[:,\-]?\s*(?:[A-Za-z]+,?\s*)?(\d{{1,2}}\s+\w+\s+{year})\s*(?:-|to|–)\s*(?:[A-Za-z]+,?\s*)?(\d{{1,2}}\s+\w+\s+{year})"
    m = re.search(patt, t, flags=re.I)
    if not m:
        return None
    return {"start": _parse_au_date(m.group(1)),
            "end":   _parse_au_date(m.group(2)),
            "summary": "Term 1"}

def scrape_terms_from_alt_sources(year: int = 2025) -> Optional[List[Dict[str, datetime]]]:
    alt_urls = [
        (f"https://www.schoolholidayssa.com.au/sa-school-holiday-dates-{year}/", "schoolholidayssa.com.au"),
        (f"https://saschoolholidays.com.au/sa-school-holidays-{year}/", "saschoolholidays.com.au"),
        (f"https://www.calendar-australia.com/school-calendars/south-australia/{year}/1/1/1/1/", "calendar-australia.com"),
    ]
    for url, label in alt_urls:
        print(f"{EMOJI_SEARCH} Trying fallback source: {label}")
        html = _fetch_text(url, headers=BROWSER_HEADERS)
        if not html:
            continue
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        terms = _extract_terms_from_text(text, year)
        if len(terms) == 4:
            print(f"{EMOJI_CHECK} Parsed SA terms from {label}")
            return terms
        else:
            print(f"{EMOJI_WARNING} Could not parse 4 terms from {label}")
    return None

def scrape_future_term1_from_alt_sources(year: int) -> Optional[Dict[str, datetime]]:
    alt_urls = [
        (f"https://www.schoolholidayssa.com.au/sa-school-holiday-dates-{year}/", "schoolholidayssa.com.au"),
        (f"https://saschoolholidays.com.au/sa-school-holidays-{year}/", "saschoolholidays.com.au"),
        (f"https://www.calendar-australia.com/school-calendars/south-australia/{year}/1/1/1/1/", "calendar-australia.com"),
    ]
    for url, label in alt_urls:
        print(f"{EMOJI_SEARCH} Future-term fallback: {label}")
        html = _fetch_text(url, headers=BROWSER_HEADERS)
        if not html:
            continue
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        t1 = _extract_term1_from_text(text, year)
        if t1:
            print(f"{EMOJI_CHECK} Parsed Term 1 {year} from {label}")
            return t1
        else:
            print(f"{EMOJI_warning if False else EMOJI_WARNING} Could not parse Term 1 {year} from {label}")
    return None

# ─── FUTURE TERM-1 (primary + fallback) ─────────────────────────────────────────
def get_future_term1_date() -> Optional[Dict[str, datetime]]:
    next_year = datetime.now().year + 1
    print(f"{EMOJI_CRYSTAL_BALL} Checking future Term-1 from official page (best-effort)")
    # 1) Official page
    try:
        r = requests.get(FUTURE_TERMS_URL, headers=BROWSER_HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        heading = next((h for h in soup.find_all(["h2","h3"])
                        if "future term dates" in h.get_text().lower()), None)
        if heading:
            table = heading.find_next("table")
            if table:
                for row in table.find_all("tr"):
                    th = row.find("th")
                    if th and th.get_text().strip().isdigit() and int(th.get_text()) == next_year:
                        td = row.find("td")
                        if not td:
                            break
                        text = re.sub(r"\s+", " ", td.get_text(separator=" ")).strip()
                        parts = re.split(r"\bto\b|\-", text)
                        if len(parts) == 2:
                            start = datetime.strptime(f"{parts[0].strip()} {next_year}", "%d %B %Y")
                            end   = datetime.strptime(f"{parts[1].strip()} {next_year}", "%d %B %Y")
                            print(f"{EMOJI_CHECK} Future Term-1: {start.date()} → {end.date()} (official)")
                            return {"start": start, "end": end, "summary": "Term 1"}
        print(f"{EMOJI_WARNING} Official future-term table not found or unparsable")
    except Exception as e:
        print(f"{EMOJI_WARNING} Future-term official fetch blocked: {e}")

    # 2) Fallback mirrors for next_year Term 1
    t1 = scrape_future_term1_from_alt_sources(next_year)
    if t1:
        return t1
    return None

# ─── FETCH / UPDATE LOGIC ───────────────────────────────────────────────────────
def update_school_terms() -> bool:
    print(f"{EMOJI_CALENDAR} Downloading school terms…")
    if TEST_MODE and ERROR_SIMULATION in ("school_terms","both","connection"):
        raise requests.exceptions.ConnectionError("Simulated")
    if TEST_MODE and ERROR_SIMULATION == "404":
        raise requests.exceptions.HTTPError("404 Simulated")

    terms: Optional[List[Dict[str, datetime]]] = None

    # 1) Try official ICS first
    try:
        r = requests.get(SCHOOL_TERMS_URL, headers=BROWSER_HEADERS, timeout=30)
        r.raise_for_status()
        if r.text.strip().startswith("BEGIN:VCALENDAR"):
            terms = extract_term_dates(r.text)
            if terms:
                print(f"{EMOJI_CHECK} Parsed terms from official ICS")
    except Exception as e:
        print(f"{EMOJI_WARNING} ICS fetch failed ({e}); falling back to public mirrors")

    # 2) Fallback to public mirror pages if needed
    if not terms:
        terms = scrape_terms_from_alt_sources(2025)
        if not terms:
            raise Exception("All sources blocked or unparsable for SA term dates 2025")

    # 3) Optionally augment with Future Term-1 if available
    future_ok = True
    try:
        fut = get_future_term1_date()
        if fut and not any(t["start"].year == fut["start"].year and t["summary"].endswith("1") for t in terms):
            print(f"{EMOJI_PLUS} Adding future Term-1")
            terms.append(fut)
        elif not fut:
            future_ok = False
    except Exception as e:
        print(f"{EMOJI_WARNING} Future-term step failed: {e}")
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

    r = requests.get(ICS_URL, timeout=30); r.raise_for_status()
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
