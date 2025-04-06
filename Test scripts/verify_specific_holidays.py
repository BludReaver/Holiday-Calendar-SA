#!/usr/bin/env python3
import re
from datetime import datetime

def verify_specific_holidays():
    """
    Verify that specific holidays occur on the expected dates
    for each year (2025-2027)
    """
    print("Verifying specific holidays for 2025-2027...")
    
    # Read the calendar file
    with open('Public-Holiday-Calendar-SA.ics', 'r') as f:
        content = f.read()
    
    # Extract events
    events = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL)
    print(f"Found {len(events)} events in the calendar")
    
    # Define expected dates for key holidays
    expected_holidays = {
        # 2025 key dates
        "2025-01-01": "New Year's Day",
        "2025-01-26": "Australia Day",
        "2025-03-10": "Adelaide Cup Day",
        "2025-04-18": "Good Friday",
        "2025-04-25": "Anzac Day",
        "2025-06-09": "King's Birthday",
        "2025-10-06": "Labour Day",
        "2025-12-25": "Christmas Day",
        
        # 2026 key dates
        "2026-01-01": "New Year's Day",
        "2026-01-26": "Australia Day",
        "2026-03-09": "Adelaide Cup Day",
        "2026-04-03": "Good Friday",
        "2026-04-25": "Anzac Day",
        "2026-06-08": "King's Birthday",
        "2026-10-05": "Labour Day",
        "2026-12-25": "Christmas Day",
        
        # 2027 key dates
        "2027-01-01": "New Year's Day",
        "2027-01-26": "Australia Day",
        "2027-03-08": "Adelaide Cup Day",
        "2027-03-26": "Good Friday",
        "2027-04-25": "Anzac Day",
        "2027-06-14": "King's Birthday",
        "2027-10-04": "Labour Day",
        "2027-12-25": "Christmas Day",
    }
    
    # Track found holidays
    found_holidays = {}
    
    # Process each event
    for event in events:
        # Get date and summary
        date_match = re.search(r'DTSTART;VALUE=DATE:(\d{8})', event)
        summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
        category_match = re.search(r'CATEGORIES:(.*?)(?:\r\n|\r|\n)', event)
        
        if date_match and summary_match and category_match:
            date_str = date_match.group(1)
            # Convert YYYYMMDD to YYYY-MM-DD
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            summary = summary_match.group(1).strip()
            category = category_match.group(1).strip()
            
            # Only check public holidays
            if category == "Public Holiday":
                found_holidays[formatted_date] = summary
    
    # Check which expected holidays were found
    found_count = 0
    missing_count = 0
    print("\nVerifying expected holidays:")
    
    for date, expected_name in sorted(expected_holidays.items()):
        if date in found_holidays:
            actual_name = found_holidays[date]
            if expected_name.lower() in actual_name.lower():
                status = "✓"
                found_count += 1
            else:
                status = "✗ (found with different name)"
                missing_count += 1
            print(f"  {date}: {expected_name} - {status} ({actual_name})")
        else:
            print(f"  {date}: {expected_name} - ✗ MISSING")
            missing_count += 1
    
    # Print summary
    print(f"\nFound {found_count} of {len(expected_holidays)} expected holidays")
    if missing_count == 0:
        print("All expected holidays are present with correct names! ✓")
    else:
        print(f"Warning: {missing_count} expected holidays are missing or have incorrect names")
    
    # Check if there are any unexpected holidays
    unexpected_count = 0
    print("\nChecking for unexpected holidays:")
    for date, name in sorted(found_holidays.items()):
        if date not in expected_holidays:
            unexpected_count += 1
            print(f"  {date}: {name}")
    
    if unexpected_count == 0:
        print("No unexpected holidays found (beyond those being verified) ✓")
    else:
        print(f"Found {unexpected_count} additional holidays beyond those being verified")

if __name__ == "__main__":
    verify_specific_holidays() 