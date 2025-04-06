#!/usr/bin/env python3
import re
from datetime import datetime, timedelta

def rebuild_calendar():
    """Rebuild the calendar file with proper categories"""
    print("Rebuilding the calendar file with proper categories...")
    
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
        
        # Determine the appropriate category
        category = "Unknown"
        if any(holiday in summary.lower() for holiday in ["day", "cup", "easter", "anzac", "christmas", "proclamation"]):
            category = "Public Holiday"
        elif "term" in summary.lower() and ("begins" in summary.lower() or "ends" in summary.lower()):
            category = "School Term"
        elif "holiday" in summary.lower():
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
    print("Categories have been standardized to: Public Holiday, School Term, School Holiday")

if __name__ == "__main__":
    rebuild_calendar() 