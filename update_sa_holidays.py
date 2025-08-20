#!/usr/bin/env python3
import io
import sys
import os
import re
import uuid
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

import requests
import httpx
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
TERMS_YEAR = 2025  # ← bump yearly
NEXT_YEAR  = TERMS_YEAR + 1

# Public holidays source (unchanged)
ICS_URL = "https://www.officeholidays.com/ics-all/australia/south-australia"

# Official SA school terms ICS (may 403/404 from CI)
SCHOOL_TERMS_URL = "https://www.education.sa.gov.au/docs/sper/communications/term-calendar/ical-School-term-dates-calendar-2025.ics"

# Human reference page (for ICS metadata/URL fields)
EDU_TERMS_PAGE = "https://www.education.sa.gov.au/parents-and-families/term-dates-south-australian-state-schools"

# Primary fallback site to scrape
HWK_URL = "https://holidayswithkids.com.au/sa-school-holidays/"

# Additional public mirrors used as secondary fallbacks
def FALLBACK_YEAR_URLS(year: int):
    return [
        (f"https://www.schoolholidayssa.com.au/sa-school-holiday-dates-{year}/", "schoolholidayssa.com.au"),
        (f"https://saschoolholidays.com.au/sa-school-holidays-{year}/", "saschoolholidays.com.au"),
        (f"https://www.calendar-australia.com/school-calendars/south-australia/{year}/1/1/1/1/", "calendar-australia.com"),
    ]

# Output filenames
OUTPUT_FILE         = "SA-Public-Holidays.ics"
SCHOOL_OUTPUT_FILE  = "SA-School-Terms-Holidays.ics"

# Source link for notifications
PUBLIC_HOLIDAYS_SOURCE_URL = "https://www.officeholidays.com/subscribe/australia/south-australia"

# Mild browser headers (safe & generic)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
    "Accept": "text/calendar, text/html;q=0.9, */*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
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

    for term in sorted(terms, key=lambda t: (t["start"], t["summary"])):
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

        # Term end (special case for 2026 kept as requested)
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

# ─── FETCHING (with tiny retry/backoff) ─────────────────────────────────────────
def fetch_text(url: str, *, tries: int = 3, sleep: float = 0.6) -> Optional[str]:
    last_err = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_err = e
            time.sleep(sleep)
    print(f"{EMOJI_WARNING} Fetch failed from {url}: {last_err}")
    return None

# ─── ROBUST DATE TOKEN PARSING ──────────────────────────────────────────────────
_MONTH_MAP = {
    'jan':1,'january':1,'feb':2,'february':2,'mar':3,'march':3,'apr':4,'april':4,
    'may':5,'jun':6,'june':6,'jul':7,'july':7,'aug':8,'august':8,'sep':9,'sept':9,'september':9,
    'oct':10,'october':10,'nov':11,'november':11,'dec':12,'december':12
}
WEEKDAY_OPT = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?\s*,?\s*"
MONTHS_RX   = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DMY_RX      = rf"(?:{WEEKDAY_OPT})?(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS_RX})(?:\s*,?\s*(\d{{4}}))?"
MDY_RX      = rf"(?:{WEEKDAY_OPT})?({MONTHS_RX})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{{4}}))?"
DATE_TOKEN_RX = rf"(?:{DMY_RX})|(?:{MDY_RX})"
SEP_RX = r"(?:\bto\b|\buntil\b|–|—|-)"

def _parse_date_loose(token: str, default_year: int) -> Optional[datetime]:
    s = " ".join(token.replace("—","-").replace("–","-").split())
    m = re.fullmatch(DMY_RX, s, flags=re.I)
    if m:
        day  = int(m.group(1)); mon = _MONTH_MAP[m.group(2).lower()]
        year = int(m.group(3)) if m.group(3) else default_year
        return datetime(year, mon, day)
    m = re.fullmatch(MDY_RX, s, flags=re.I)
    if m:
        mon = _MONTH_MAP[m.group(1).lower()]; day = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else default_year
        return datetime(year, mon, day)
    return None

def _find_two_dates_near(text: str, anchor_idx: int, default_year: int, window: int = 1200
                         ) -> Optional[Tuple[datetime, datetime, str]]:
    seg = text[anchor_idx: anchor_idx + window]
    matches = list(re.finditer(DATE_TOKEN_RX, seg, flags=re.I))
    if not matches:
        return None
    # adjacent pairs first (strongest signal)
    for i in range(len(matches)-1):
        a, b = matches[i], matches[i+1]
        between = seg[a.end():b.start()]
        if not re.search(SEP_RX, between, flags=re.I):
            continue
        d1 = _parse_date_loose(a.group(0), default_year)
        d2 = _parse_date_loose(b.group(0), default_year)
        if not d1 or not d2:
            continue
        # sensible SA Term 1 heuristic
        if d1.month in (1,2) and d2 >= d1 and d2.month in (3,4):
            snippet = seg[max(0, a.start()-40): min(len(seg), b.end()+40)]
            return d1, d2, snippet
    # fall back: any pair with a separator
    for i in range(len(matches)-1):
        for j in range(i+1, len(matches)):
            a, b = matches[i], matches[j]
            between = seg[a.end():b.start()]
            if not re.search(SEP_RX, between, flags=re.I):
                continue
            d1 = _parse_date_loose(a.group(0), default_year)
            d2 = _parse_date_loose(b.group(0), default_year)
            if d1 and d2 and d1 <= d2:
                snippet = seg[max(0, a.start()-40): min(len(seg), b.end()+40)]
                return d1, d2, snippet
    return None

def _slice_for_year(text: str, year: int, span: int = 6000) -> str:
    m = re.search(rf"\b{year}\b", text)
    if not m:
        return text
    start = m.start()
    return text[start:start+span]

def _extract_terms_four(text: str, year: int) -> Optional[List[Dict[str, datetime]]]:
    """Find Term 1..4 inside a year-focused slice, robust to formats."""
    segment = _slice_for_year(text, year)
    results: List[Dict[str, datetime]] = []
    for n in range(1, 5):
        found = None
        for m in re.finditer(rf"Term\s*{n}\b", segment, flags=re.I):
            hit = _find_two_dates_near(segment, m.start(), year, window=1600)
            if hit:
                d1, d2, _ = hit
                found = {"start": d1, "end": d2, "summary": f"Term {n}"}
                break
        if not found:
            return None
        results.append(found)
    return results

def _extract_term1_any(text: str, year: int) -> Optional[Dict[str, datetime]]:
    """Find Term 1 (for next year) anywhere on page."""
    # prefer the year slice (e.g., "2026") if present
    segment = _slice_for_year(text, year)
    # try 'Term 1' anchor(s)
    for m in re.finditer(r"Term\s*1\b", segment, flags=re.I):
        hit = _find_two_dates_near(segment, m.start(), year, window=1600)
        if hit:
            d1, d2, snippet = hit
            print(f"{EMOJI_CHECK} Future Term-1 {year}: {d1.date()} → {d2.date()} (from page)")
            print(f"{EMOJI_SEARCH} excerpt: …{snippet}…")
            return {"start": d1, "end": d2, "summary": "Term 1"}
    # last resort: scan whole text once
    for m in re.finditer(r"Term\s*1\b", text, flags=re.I):
        hit = _find_two_dates_near(text, m.start(), year, window=1600)
        if hit:
            d1, d2, snippet = hit
            print(f"{EMOJI_CHECK} Future Term-1 {year}: {d1.date()} → {d2.date()} (from page)")
            print(f"{EMOJI_SEARCH} excerpt: …{snippet}…")
            return {"start": d1, "end": d2, "summary": "Term 1"}
    return None

# ─── SCRAPERS ───────────────────────────────────────────────────────────────────
def parse_terms_from_hwk(year: int) -> Optional[List[Dict[str, datetime]]]:
    html = fetch_text(HWK_URL, tries=3)
    if not html:
        return None
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    terms = _extract_terms_four(text, year)
    if terms:
        print(f"{EMOJI_CHECK} Parsed SA terms {year} from holidayswithkids.com.au")
    else:
        print(f"{EMOJI_WARNING} Could not parse all 4 terms for {year} from holidayswithkids.com.au")
    return terms

def parse_future_term1_from_hwk(year: int) -> Optional[Dict[str, datetime]]:
    html = fetch_text(HWK_URL, tries=3)
    if not html:
        return None
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return _extract_term1_any(text, year)

def parse_terms_from_fallbacks(year: int) -> Optional[List[Dict[str, datetime]]]:
    for url, label in FALLBACK_YEAR_URLS(year):
        print(f"{EMOJI_SEARCH} Trying fallback source: {label}")
        html = fetch_text(url, tries=3)
        if not html:
            continue
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        terms = _extract_terms_four(text, year)
        if terms:
            print(f"{EMOJI_CHECK} Parsed SA terms {year} from {label}")
            return terms
        else:
            print(f"{EMOJI_WARNING} Could not parse 4 terms from {label}")
    return None

def parse_future_term1_from_fallbacks(year: int) -> Optional[Dict[str, datetime]]:
    for url, label in FALLBACK_YEAR_URLS(year):
        print(f"{EMOJI_SEARCH} Future-term fallback: {label}")
        html = fetch_text(url, tries=3)
        if not html:
            continue
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        t1 = _extract_term1_any(text, year)
        if t1:
            print(f"{EMOJI_CHECK} Parsed Term 1 {year} from {label}")
            return t1
        else:
            print(f"{EMOJI_WARNING} Could not parse Term 1 {year} from {label}")
    return None

# ─── FETCH / UPDATE LOGIC ───────────────────────────────────────────────────────
def update_school_terms() -> bool:
    print(f"{EMOJI_CALENDAR} Downloading school terms…")

    terms: Optional[List[Dict[str, datetime]]] = None

    # 1) Try official ICS first (tolerate 403/404)
    try:
        r = requests.get(SCHOOL_TERMS_URL, headers=BROWSER_HEADERS, timeout=30)
        r.raise_for_status()
        if r.text.strip().startswith("BEGIN:VCALENDAR"):
            parsed = extract_term_dates(r.text)
            terms = [t for t in parsed if t["start"].year == TERMS_YEAR]
            if terms:
                print(f"{EMOJI_CHECK} Parsed terms from official ICS")
    except Exception as e:
        print(f"{EMOJI_WARNING} ICS fetch failed ({e}); will use public mirrors")

    # 2) Holidays With Kids, else other mirrors
    if not terms:
        terms = parse_terms_from_hwk(TERMS_YEAR) or parse_terms_from_fallbacks(TERMS_YEAR)
        if not terms:
            raise Exception(f"All sources blocked or unparsable for SA term dates {TERMS_YEAR}")

    # 3) Future Term-1 from HWK, else mirrors
    future_ok = True
    try:
        fut = parse_future_term1_from_hwk(NEXT_YEAR) or parse_future_term1_from_fallbacks(NEXT_YEAR)
        if fut and not any(t["start"].year == fut["start"].year and t["summary"].endswith("1") for t in terms):
            print(f"{EMOJI_PLUS} Adding future Term-1")
            terms.append(fut)
        elif not fut:
            future_ok = False
    except Exception as e:
        print(f"{EMOJI_WARNING} Future-term step failed: {e}")
        future_ok = False

    terms.sort(key=lambda x: (x["start"], x["summary"]))
    holidays = generate_holiday_periods(terms)
    cal_text = generate_school_calendar(terms, holidays)

    with open(SCHOOL_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(cal_text)
    print(f"{EMOJI_SAVE} Wrote {SCHOOL_OUTPUT_FILE}")

    return future_ok

def update_public_holidays():
    print(f"{EMOJI_CALENDAR} Downloading public holidays…")
    r = requests.get(ICS_URL, headers=BROWSER_HEADERS, timeout=30)
    r.raise_for_status()
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
