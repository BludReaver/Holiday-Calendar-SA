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

# Public holidays source (UNCHANGED AND WORKING)
ICS_URL = "https://www.officeholidays.com/ics-all/australia/south-australia"

# OFFICIAL LIVE SA TERM PAGE (THE ONE YOU WANT)
EDU_TERMS_PAGE = "https://www.education.sa.gov.au/students/term-dates-south-australian-state-schools"

# Output filenames (UNCHANGED)
OUTPUT_FILE         = "SA-Public-Holidays.ics"
SCHOOL_OUTPUT_FILE  = "SA-School-Terms-Holidays.ics"

# Source link for notifications (UNCHANGED)
PUBLIC_HOLIDAYS_SOURCE_URL = "https://www.officeholidays.com/subscribe/australia/south-australia"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html, */*",
}

# ─── UTILITIES (UNCHANGED) ──────────────────────────────────────────────────────
def clean_event_name(summary: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", summary).strip()

def get_next_update_date() -> str:
    today = datetime.now()
    next_month = datetime(today.year + (1 if today.month == 12 else 0),
                          1 if today.month == 12 else today.month + 1, 1)
    return next_month.strftime("%A %dst %B %Y".replace("1stst","1st"))

def send_failure_notification(error_excerpt: str, failed_calendar: Optional[str]=None):
    token = os.getenv("PUSHOVER_API_TOKEN")
    user  = os.getenv("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover creds missing.")
        return
    message = f"‼️ SA Calendar Update Failed ‼️\n\n{error_excerpt}"
    httpx.post("https://api.pushover.net/1/messages.json",
               data={"token":token, "user":user, "message":message})

def send_success_notification(future_term_fetched: bool = True):
    token = os.getenv("PUSHOVER_API_TOKEN")
    user  = os.getenv("PUSHOVER_USER_KEY")
    if not token or not user:
        print(f"{EMOJI_WARNING} Pushover creds missing.")
        return
    message = f"{EMOJI_CHECK} SA Calendars Updated!\nNext update: {get_next_update_date()}"
    httpx.post("https://api.pushover.net/1/messages.json",
               data={"token":token, "user":user, "message":message})

def parse_ics_date(s: str) -> datetime:
    return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]))

def extract_term_dates(cal_text: str):
    terms = []
    cur = {}
    inside = False
    for line in cal_text.splitlines():
        if line == "BEGIN:VEVENT":
            cur = {}
            inside = True
        elif line == "END:VEVENT" and inside:
            if {"start","end","summary"} <= set(cur):
                terms.append(cur)
            inside = False
        elif inside:
            if line.startswith("DTSTART;VALUE=DATE:"):
                cur["start"] = parse_ics_date(line.split(":",1)[1])
            elif line.startswith("DTEND;VALUE=DATE:"):
                dt = parse_ics_date(line.split(":",1)[1])
                cur["end"] = dt - timedelta(days=1)
            elif line.startswith("SUMMARY"):
                cur["summary"] = line.split(":",1)[1]
    return terms

def generate_holiday_periods(terms):
    terms_sorted = sorted(terms, key=lambda t: t["start"])
    hols=[]
    for a,b in zip(terms_sorted, terms_sorted[1:]):
        if b["start"] > a["end"] + timedelta(days=1):
            tnum = a["summary"].split()[-1]
            hols.append({
                "start": a["end"] + timedelta(days=1),
                "end":   b["start"] - timedelta(days=1),
                "summary": f"School Holidays (After Term {tnum})"
            })
    return hols

def format_dt(dt):
    return dt.strftime("%Y%m%d")

def generate_school_calendar(terms, holidays):
    ts = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    out=[
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//South Australia School Terms and Holidays//EN",
        "X-WR-CALNAME:South Australia School Terms and Holidays",
        "X-WR-CALDESC:School terms and holiday periods in South Australia",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for t in terms:
        num=t["summary"].split()[-1]
        s=format_dt(t["start"])
        e=format_dt(t["end"])
        e2=format_dt(t["end"]+timedelta(days=1))
        s2=format_dt(t["start"]+timedelta(days=1))

        out+=["BEGIN:VEVENT",
              f"UID:START-{s}-TERM{num}",
              f"SUMMARY:Term {num} Start",
              f"DTSTART;VALUE=DATE:{s}",
              f"DTEND;VALUE=DATE:{s2}",
              "END:VEVENT"]

        out+=["BEGIN:VEVENT",
              f"UID:END-{e}-TERM{num}",
              f"SUMMARY:Term {num} End",
              f"DTSTART;VALUE=DATE:{e}",
              f"DTEND;VALUE=DATE:{e2}",
              "END:VEVENT"]

    for h in holidays:
        s=format_dt(h["start"])
        e=format_dt(h["end"]+timedelta(days=1))
        out+=["BEGIN:VEVENT",
              f"UID:HOLIDAY-{s}",
              f"SUMMARY:{h['summary']}",
              f"DTSTART;VALUE=DATE:{s}",
              f"DTEND;VALUE=DATE:{e}",
              "END:VEVENT"]

    out.append("END:VCALENDAR")
    return "\n".join(out)

# ────────────────────────────────────────────────────────────────────────────────
# >>>>>>>>>>>>> NEW EDUCATION-SA SCRAPER (REPLACES HWK + FALLBACKS) <<<<<<<<<<<<<
# ────────────────────────────────────────────────────────────────────────────────

def fetch_sa_terms_from_education_page(year: int) -> Optional[List[Dict]]:
    """Parse 'Term dates for <year>' bullet list directly from official SA page."""
    print(f"{EMOJI_SEARCH} Scraping official Education SA page for {year}")
    r = requests.get(EDU_TERMS_PAGE, headers=BROWSER_HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    header = soup.find(lambda tag: tag.name in ("h2","h3") and f"Term dates for {year}" in tag.text)
    if not header:
        print(f"{EMOJI_WARNING} Year {year} section missing")
        return None

    ul = header.find_next("ul")
    if not ul:
        print(f"{EMOJI_WARNING} No bullet list for {year}")
        return None

    terms=[]
    for li in ul.find_all("li"):
        txt=li.get_text(" ",strip=True)
        m=re.match(r"Term\s+(\d)\s*[-–—]\s*(.+?)\s+to\s+(.+)",txt)
        if not m:
            continue

        tnum=int(m.group(1))
        def parse(datestr):
            parts=datestr.strip().split()
            day=int(parts[-2] if parts[-2].isdigit() else parts[-1])
            month=parts[-1]
            month_no=datetime.strptime(month,"%B").month
            return datetime(year, month_no, day)

        start=parse(m.group(2))
        end=parse(m.group(3))
        terms.append({"summary":f"Term {tnum}","start":start,"end":end})

    if len(terms)==4:
        print(f"{EMOJI_CHECK} Official {year} term dates scraped successfully")
        return terms
    else:
        print(f"{EMOJI_WARNING} Could not parse 4 terms for {year}")
        return None

# ────────────────────────────────────────────────────────────────────────────────
# END NEW SCRAPER
# ────────────────────────────────────────────────────────────────────────────────

def update_school_terms():
    print(f"{EMOJI_CALENDAR} Downloading school terms…")

    # 1) Use official Education SA page for both years
    terms = fetch_sa_terms_from_education_page(TERMS_YEAR)
    if not terms:
        raise Exception("Failed to fetch official term dates.")

    future = fetch_sa_terms_from_education_page(NEXT_YEAR)
    if future:
        terms.extend(future)
        future_ok = True
    else:
        print(f"{EMOJI_WARNING} Future year missing")
        future_ok = False

    terms_sorted = sorted(terms, key=lambda x: x["start"])
    holidays = generate_holiday_periods(terms_sorted)
    txt = generate_school_calendar(terms_sorted, holidays)

    with open(SCHOOL_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"{EMOJI_SAVE} Wrote {SCHOOL_OUTPUT_FILE}")

    return future_ok

# ─── PUBLIC HOLIDAYS — UNCHANGED ───────────────────────────────────────────────
def update_public_holidays():
    print(f"{EMOJI_CALENDAR} Downloading public holidays…")
    r=requests.get(ICS_URL,headers=BROWSER_HEADERS,timeout=30)
    r.raise_for_status()
    cleaned=[]
    for line in r.text.splitlines():
        if line.startswith("SUMMARY"):
            p=line.find(":")
            cleaned.append(f"{line[:p+1]}{clean_event_name(line[p+1:])}")
        else:
            cleaned.append(line)
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write("\n".join(cleaned))
    print(f"{EMOJI_SAVE} Wrote {OUTPUT_FILE}")

# ─── MAIN LOOP — UNCHANGED ─────────────────────────────────────────────────────
def main():
    ok_ph=ok_st=False
    ok_future=True
    try:
        try:
            update_public_holidays()
            ok_ph=True
        except Exception as e:
            print("Public holiday error:",e)
            send_failure_notification(str(e),"public_holidays")

        try:
            ok_future=update_school_terms()
            ok_st=True
        except Exception as e:
            print("School terms error:",e)
            send_failure_notification(str(e),"school_terms")

        if ok_ph and ok_st:
            send_success_notification(ok_future)
        else:
            sys.exit(1)
    except Exception as e:
        send_failure_notification(str(e))
        sys.exit(1)

if __name__=="__main__":
    main()
