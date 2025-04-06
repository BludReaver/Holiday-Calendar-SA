#!/usr/bin/env python3
import re
from collections import defaultdict
from datetime import datetime

def find_duplicate_holidays():
    """Find any duplicate holiday entries in the calendar"""
    print("Checking for duplicate holidays in the calendar...")
    
    # Read the calendar file
    with open('Public-Holiday-Calendar-SA.ics', 'r') as f:
        content = f.read()
    
    # Extract events
    events = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL)
    print(f"Found {len(events)} events in the calendar")
    
    # Track holidays by date and name
    holidays_by_date = defaultdict(list)
    
    # Process each event
    for event in events:
        # Get date, summary, and category
        date_match = re.search(r'DTSTART;VALUE=DATE:(\d{8})', event)
        summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
        category_match = re.search(r'CATEGORIES:(.*?)(?:\r\n|\r|\n)', event)
        
        if date_match and summary_match and category_match:
            date_str = date_match.group(1)
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            date_formatted = f"{year}-{month:02d}-{day:02d}"
            summary = summary_match.group(1).strip()
            category = category_match.group(1).strip()
            
            # Store in the holidays dictionary
            if category == "School Holiday":
                holidays_by_date[date_formatted].append(summary)
    
    # Check for duplicates
    print("\nChecking for duplicate school holidays...")
    found_duplicates = False
    
    for date, summaries in sorted(holidays_by_date.items()):
        if len(summaries) > 1:
            print(f"\n✗ Duplicate on {date}:")
            for summary in summaries:
                print(f"  - {summary}")
            found_duplicates = True
    
    # Also, count holidays by year to help diagnose issues
    holidays_by_year = defaultdict(int)
    for date in holidays_by_date.keys():
        year = int(date.split('-')[0])
        holidays_by_year[year] += len(holidays_by_date[date])
    
    print("\nSchool holidays by year:")
    for year in sorted(holidays_by_year.keys()):
        print(f"  {year}: {holidays_by_year[year]} holidays")
    
    if not found_duplicates:
        print("\n✓ No duplicate school holidays found")
        print("\nThe issue might be due to overlapping holiday periods or an extra holiday entry.")
        print("Check for any holidays that shouldn't be in the calendar.")
    
    return found_duplicates

if __name__ == "__main__":
    find_duplicate_holidays() 