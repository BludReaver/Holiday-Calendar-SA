#!/usr/bin/env python3
import re
from datetime import datetime

def fix_calendar_final():
    """Final script to fix all remaining category issues"""
    print("Performing final fixes on the calendar...")
    
    # Read the current file
    with open('Public-Holiday-Calendar-SA.ics', 'r') as f:
        content = f.read()
    
    # Parse all events
    events = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL)
    print(f"Found {len(events)} events in the calendar")
    
    # Header part of the calendar
    header = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//South Australia//Public Holidays//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:South Australia Public Holidays and School Terms
X-WR-TIMEZONE:Australia/Adelaide
X-WR-CALDESC:Public Holidays and School Terms for South Australia
"""
    
    # Footer of the calendar
    footer = "END:VCALENDAR"
    
    # Process and rewrite each event
    rebuilt_events = []
    
    for event in events:
        # Get the summary to determine category
        summary = ""
        summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
        if summary_match:
            summary = summary_match.group(1).strip()
        
        # Determine the appropriate category based on summary
        category = "Unknown"
        if "New Year's Eve" in summary or "New Year's Day" in summary or "Christmas" in summary or "Australia Day" in summary or "Cup Day" in summary or "Easter" in summary or "Anzac" in summary or "King's Birthday" in summary or "Labour Day" in summary or "Proclamation Day" in summary:
            category = "Public Holiday"
        elif "Term" in summary and ("Begins" in summary or "Ends" in summary):
            category = "School Term"
        elif "School Holiday" in summary or "Holidays" in summary:
            category = "School Holiday"
        
        # Replace or add the category
        if re.search(r'CATEGORIES:', event):
            event = re.sub(r'CATEGORIES:.*?(?:\r\n|\r|\n)', f'CATEGORIES:{category}\n', event)
        else:
            # Add category after summary if none exists
            event = re.sub(r'(SUMMARY:.*?)(?:\r\n|\r|\n)', f'\\1\nCATEGORIES:{category}\n', event)
        
        # Add the rebuilt event
        rebuilt_events.append(f"BEGIN:VEVENT{event}END:VEVENT")
    
    # Combine everything
    new_content = header + "\n".join(rebuilt_events) + "\n" + footer
    
    # Write the updated content
    with open('Public-Holiday-Calendar-SA.ics', 'w') as f:
        f.write(new_content)
    
    print(f"Calendar rebuilt with {len(rebuilt_events)} events.")
    print("Categories have been corrected for all events.")
    
    # Now count the events by category
    public_holidays = 0
    school_terms = 0
    school_holidays = 0
    unknown = 0
    
    for event in rebuilt_events:
        if "CATEGORIES:Public Holiday" in event:
            public_holidays += 1
        elif "CATEGORIES:School Term" in event:
            school_terms += 1
        elif "CATEGORIES:School Holiday" in event:
            school_holidays += 1
        else:
            unknown += 1
    
    print("\nFinal Category Counts:")
    print(f"Public Holidays: {public_holidays}")
    print(f"School Terms: {school_terms}")
    print(f"School Holidays: {school_holidays}")
    print(f"Unknown: {unknown}")
    
    print("\nCalendar update complete.")

if __name__ == "__main__":
    fix_calendar_final() 