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

# Ensure stdout is UTF-8 so emojis render in logs
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Emojis (used in logs)
EMOJI_CHECK        = "✅"
EMOJI_WARNING      = "⚠️"
EMOJI_ERROR        = "❌"
EMOJI_CALENDAR     = "📅"
EMOJI_SAVE         = "💾"
EMOJI_SEARCH       = "🔍"
EMOJI_CRYSTAL_BALL = "🔮"
EMOJI_SUN          = "🌞"
EMOJI_PLUS         = "➕"

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
# Which year's terms to publish from official or fallback sources
TERMS_YEAR = 2025

# Public holidays source (unchanged)
ICS_URL = "https://www.officeholidays.com/ics-all/australia/south-australia"

# Official SA school terms ICS (may 403/404 from CI)
SCHOOL_TERMS_URL = "https://www.education.sa.gov.au/docs/sper/communications/term-calendar/ical-School-term-dates-calendar-2025.ics"

# Human page (usually gated from CI) — kept only for display links in generated ICS
EDU_TERMS_PAGE = "https://www.education.sa.gov.au/parents-and-families/term-dates-south-australian-state-schools"

# Fallback site we can reliably scrape (you asked for this)
HWK_URL = "https://holidayswithkids.com.au/sa-school-holidays/"

# Output filenames
OUTPUT_FILE         = "SA-Public-Holidays.ics"
SCHOOL_OUTPUT_FILE  = "SA-School-Terms-Holidays.ics"

# Source links for notifications
PUBLIC_HOLIDAYS_SOURCE_URL = "https://www.officeholidays.com/subscribe/australia/south-australia"

# Mild browser headers (safe & generic)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
    "Accept": "text/calendar, text/html;q=0.9, */*;q=0.8",
    "Connection": "keep-alive",
}

# ─── UTILITIES ───────────────────────────────────────────────────────────────────
def clean_event_name(summary: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", summary).strip()

def get_next_update_date() -> str:
    today = datetime.now()
    next_month = datetime(today.year + (1 if today.month == 12 else 0),
                          1 if today.month == 12 else today.month + 1, 1)
    day = next_month.day  # 1
    suffix = "th" if 4 <= day <= 20 or 24 <= day <= 30 else {1:"st",2:"nd",3:"rd"}.get(day % 10,"th")
    return next_month.strftime(f"%A {day}{suffix} %B %Y")

def send_failure_notification(error_excerpt: str, failed_calendar: Optional[str]=None):
    token = os.getenv("PUSHOVER_API_TOKEN")
    user  = os.getenv("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover creds missing—skipping failure notification.")
        print("Error:", error_excerpt)
        return

    if failed_calendar == "public_holidays":
        cal_info = f"{EMOJI_CALENDAR} Public Holidays update failed\n\n"
        cal_src  = f"🔗 Source: {PUBLIC_HOLIDAYS_SOURCE_URL}\n\n"
    elif failed_calendar == "school_terms":
        cal_info = f"{EMOJI_CALENDAR} School Terms update failed\n\n"
        cal_src  = f"🔗 Sources: official ICS and {HWK_URL}\n\n"
    elif failed_calendar == "future_term":
        cal_info = f"{EMOJI_CALENDAR} Future Term-1 fetch failed\n\n"
        cal_src  = f"🔗 Source: {HWK_URL}\n\n"
    else:
        cal_info = f"{EMOJI_CALENDAR} Calendar update failed\n\n"
        cal_src  = (
            "🔗 Sources:\n"
            f"- Public Holidays: {PUBLIC_HOLIDAYS_SOURCE_URL}\n"
            f"- School Terms (ICS): {SCHOOL_TERMS_URL}\n"
            f"- Fallback: {HWK_URL}\n\n"
        )

    message = (
        "‼️ SA Calendar Update Failed ‼️\n\n"
        f"{cal_info}"
        "Check GitHub Actions logs:\n"
        "1. Navigate to your repo\n"
        "2. Click **Actions**\n"
        "3. Open the failed run\n\n"
        f"{cal_src}"
        f"📝 Error Log:\n{error_excerpt}"
    )

    try:
        resp = httpx.post("https://api.pushover.net/1/messages.json",
                          data={"token":token, "user":user, "message":message})
        if resp.status_code == 200:
            print(f"{EMOJI_CHECK} Failure notification sent")
        else:
            print(f"{EMOJI_ERROR} Notification failed:", resp.text)
    except Exception as e:
        print(f"{EMOJI_ERROR} Notification error:", e)

def send_success_notification(future_term_fetched: bool = True):
    token = os.getenv("PUSHOVER_API_TOKEN")
    user  = os.getenv("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover creds missing—skipping success notification.")
        return

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
        resp = httpx.post("https://api.pushover.net/1/messages.json",
                          data={"token":token, "user":user, "message":message})
        if resp.status_code == 200:
            print(f"{EMOJI_CHECK} Success notification sent")
        else:
            print(f"{EMOJI_ERROR} Notification failed:", resp.text)
    except Exception as e:
        print(f"{EMOJI_ERROR} Notification error:", e)

def parse_ics_date(s: str) -> datetime:
    return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]))

def extract_term_dates(cal_text: str) -> List[Dict[str, datetime]]:
    lines = cal_text.splitlines()
    terms, current, in_ev = [], {}, False
    for L in lines:
        if L == "BEGIN:VEVENT":
            in_ev, current = True, {}
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

    for term in terms:
        num   = term["summary"].split()[-1]
        start = format_dt(term["start"])
        end   = format_dt(term["end"])
        nextd = format_dt(term["start"] + timedelta(days=1))
        nextde= format_dt(term["end"] + timedelta(days=1))

        # Term start
        summ = f"Term {num} Start"
        if term["start"].year == 2026 and num == "1":
            summ = "Term 1 Start (January 27, 2026)"
        cal += [
            "BEGIN:VEVENT","CLASS:PUBLIC",
            f"UID:START-{start}-TERM{num}@sa-school-terms.education.sa.gov.au",
            f"CREATED:{ts}",
            "DESCRIPTION:First day of term for South Australian schools.",
            f"URL:{EDU_TERMS_PAGE}",
            f"DTSTART;VALUE=DATE:{start}","DTEND;VALUE=DATE:{nextd}","DTSTAMP:{ts}",
            "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{ts}","SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:{summ}",
            "TRANSP:OPAQUE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE","END:VEVENT"
        ]

        # Term end (with special-case you previously had)
        if term["end"].year == 2026 and num == "1":
            cal += [
                "BEGIN:VEVENT","CLASS:PUBLIC",
                f"UID:TERM1-2026-END-DISTINCT-{uuid.uuid4()}@sa-school-terms.education.sa.gov.au",
                f"CREATED:{ts}",
                "DESCRIPTION:Last day of Term 1, 2026 for South Australian schools.",
                f"URL:{EDU_TERMS_PAGE}",
                f"DTSTART;VALUE=DATE:{end}","DTEND;VALUE=DATE:{nextde}","DTSTAMP:"+ts.replace("Z","1Z"),
                "LOCATION:South Australia Schools","PRIORITY:5",
                f"LAST-MODIFIED:{ts.replace('Z','2Z')}","SEQUENCE:2",
                "SUMMARY;LANGUAGE=en-us:Term 1 End - April 10th, 2026",
                "TRANSP:OPAQUE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE","END:VEVENT"
            ]
        else:
            cal += [
                "BEGIN:VEVENT","CLASS:PUBLIC",
                f"UID:END-{end}-TERM{num}@sa-school-terms.education.sa.gov.au",
                f"CREATED:{ts}",
                "DESCRIPTION:Last day of term for South Australian schools.",
                f"URL:{EDU_TERMS_PAGE}",
                f"DTSTART;VALUE=DATE:{end}","DTEND;VALUE=DATE:{nextde}","DTSTAMP:{ts}",
                "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{ts}","SEQUENCE:1",
                f"SUMMARY;LANGUAGE=en-us:Term {num} End",
                "TRANSP:OPAQUE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE","END:VEVENT"
            ]

    # Holidays between terms
    for hol in holidays:
        start = format_dt(hol["start"])
        end   = format_dt(hol["end"] + timedelta(days=1))
        num   = hol["summary"].split()[-1]
        cal += [
            "BEGIN:VEVENT","CLASS:PUBLIC",
            f"UID:HOLIDAY-{start}-TERM{num}@sa-school-terms.education.sa.gov.au",
            f"CREATED:{ts}",
            "DESCRIPTION:School holiday period between terms.",
            f"URL:{EDU_TERMS_PAGE}",
            f"DTSTART;VALUE=DATE:{start}","DTEND;VALUE=DATE:{end}","DTSTAMP:{ts}",
            "LOCATION:South Australia","PRIORITY:5",f"LAST-MODIFIED:{ts}","SEQUENCE:1",
            f"SUMMARY;LANGUAGE=en-us:{hol['summary']}",
            "TRANSP:OPAQUE","X-MICROSOFT-CDO-ALLDAYEVENT:TRUE","END:VEVENT"
        ]

    cal.append("END:VCALENDAR")
    return "\n".join(cal)

# ─── HOLIDAYSWITHKIDS SCRAPERS ──────────────────────────────────────────────────
def _fetch_text(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"{EMOJI_WARNING} Fetch failed from {url}: {e}")
        return None

def _parse_au_date(s: str, year: int) -> datetime:
    s = s.strip()
    s = re.sub(r"^[A-Za-z]+,?\s+", "", s)             # remove weekday if present
    s = s.replace("–", "-")                           # normalize en-dash
    s = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s)       # remove ordinals
    return datetime.strptime(f"{s} {year}", "%d %B %Y")

def _extract_terms_from_hwk_year_section(h: BeautifulSoup, year: int) -> Optional[List[Dict[str, datetime]]]:
    """
    On HWK the main year sections list 'Term 1: 29 Jan to 13 Apr' etc.
    We find the heading that contains the year and read the subsequent table or list.
    """
    # Find a heading that contains the year, then scan the next table/list text
    target = None
    for tag in h.find_all(["h2","h3","h4"]):
        if str(year) in tag.get_text(" ", strip=True):
            target = tag
            break
    if not target:
        return None

    # Grab a reasonable chunk of text after the heading
    chunk = []
    for sib in target.next_siblings:
        if getattr(sib, "name", None) in {"h2","h3","h4"}:
            break
        chunk.append(getattr(sib, "get_text", lambda *a, **k: str(sib))(" ", strip=True))
    text = " ".join(chunk)

    terms: List[Dict[str, datetime]] = []
    for n in range(1, 5):
        m = re.search(
            rf"Term\s*{n}\s*[:\-]?\s*(\d{{1,2}}\s+\w+)\s*(?:to|–|-)\s*(\d{{1,2}}\s+\w+)",
            text, flags=re.I
        )
        if not m:
            return None
        start = _parse_au_date(m.group(1), year)
        end   = _parse_au_date(m.group(2), year)
        terms.append({"start": start, "end": end, "summary": f"Term {n}"})
    return terms

def _extract_future_term1_from_hwk(h: BeautifulSoup, year: int) -> Optional[Dict[str, datetime]]:
    # Find “Future term dates” then table row for the year, Term 1 cell
    heading = next((x for x in h.find_all(["h2","h3"]) if "future term dates" in x.get_text(" ", strip=True).lower()), None)
    if not heading:
        print(f"{EMOJI_WARNING} HWK: 'Future term dates' heading not found")
        return None
    table = heading.find_next("table")
    if not table:
        print(f"{EMOJI_WARNING} HWK: table not found after heading")
        return None

    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td","th"])]
        if not cells:
            continue
        try:
            row_year = int(re.sub(r"\D", "", cells[0]))
        except Exception:
            continue
        if row_year != year:
            continue
        if len(cells) < 2:
            print(f"{EMOJI_WARNING} HWK: row has no Term 1 cell")
            return None
        term1 = cells[1]  # e.g., "27 January to 10 April"
        parts = re.split(r"\bto\b|–|-", term1)
        if len(parts) != 2:
            print(f"{EMOJI_WARNING} HWK: unexpected Term 1 format: {term1}")
            return None
        start = _parse_au_date(parts[0].strip(), year)
        end   = _parse_au_date(parts[1].strip(), year)
        print(f"{EMOJI_CHECK} Parsed Term 1 {year} from holidayswithkids.com.au: {start.date()} → {end.date()}")
        return {"start": start, "end": end, "summary": "Term 1"}

    print(f"{EMOJI_WARNING} HWK: no row for year {year}")
    return None

# ─── FETCH / UPDATE LOGIC ───────────────────────────────────────────────────────
def update_school_terms() -> bool:
    print(f"{EMOJI_CALENDAR} Downloading school terms…")

    terms: Optional[List[Dict[str, datetime]]] = None

    # 1) Try official ICS first
    try:
        r = requests.get(SCHOOL_TERMS_URL, headers=BROWSER_HEADERS, timeout=30)
        r.raise_for_status()
        if r.text.strip().startswith("BEGIN:VCALENDAR"):
            parsed = extract_term_dates(r.text)
            # Filter to only the configured year (if ICS contains multiple)
            terms = [t for t in parsed if t["start"].year == TERMS_YEAR]
            if terms:
                print(f"{EMOJI_CHECK} Parsed terms from official ICS")
    except Exception as e:
        print(f"{EMOJI_WARNING} ICS fetch failed ({e}); falling back to holidayswithkids.com.au")

    # 2) Fallback to Holidays With Kids (for TERMS_YEAR)
    if not terms:
        html = _fetch_text(HWK_URL)
        if not html:
            raise Exception("All sources blocked for SA term dates")
        soup = BeautifulSoup(html, "html.parser")
        terms = _extract_terms_from_hwk_year_section(soup, TERMS_YEAR)
        if not terms:
            raise Exception("Could not parse SA term dates from holidayswithkids.com.au")
        print(f"{EMOJI_CHECK} Parsed SA terms {TERMS_YEAR} from holidayswithkids.com.au")

    # 3) Add Future Term-1 (next year) from Holidays With Kids table
    future_ok = True
    try:
        html = _fetch_text(HWK_URL)
        if not html:
            future_ok = False
        else:
            soup = BeautifulSoup(html, "html.parser")
            next_year = TERMS_YEAR + 1
            fut = _extract_future_term1_from_hwk(soup, next_year)
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

def main():
    try:
        ok_ph = ok_st = False
        ok_future = True

        try:
            update_public_holidays()
            ok_ph = True
        except Exception as e:
            print(f"{EMOJI_ERROR} Public holidays failed: {e}")
            send_failure_notification(str(e), "public_holidays")

        try:
            ok_future = update_school_terms()
            ok_st = True
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
