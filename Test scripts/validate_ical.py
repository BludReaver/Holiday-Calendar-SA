#!/usr/bin/env python3
import sys
import icalendar
from datetime import datetime, timedelta

def validate_ical(filename):
    """
    Validate an iCalendar file by checking:
    1. If it can be successfully parsed
    2. If all required fields are present
    3. If event dates make sense
    4. If there are any duplicate UIDs
    """
    try:
        # Try parsing the file
        print(f"Validating {filename}...")
        with open(filename, 'rb') as f:
            cal = icalendar.Calendar.from_ical(f.read())
        
        print("✓ File successfully parsed as iCalendar")
        
        # Check required calendar properties
        required_calendar_props = ['VERSION', 'PRODID']
        for prop in required_calendar_props:
            if prop not in cal:
                print(f"✗ Calendar missing required property: {prop}")
                return False
        print("✓ Calendar has all required properties")
        
        # Track event UIDs to check for duplicates
        uids = set()
        dates = {}
        categories = {}
        
        # Check events
        for component in cal.walk():
            if component.name == 'VEVENT':
                # Check required event properties
                required_event_props = ['SUMMARY', 'DTSTART', 'UID']
                for prop in required_event_props:
                    if prop not in component:
                        print(f"✗ Event missing required property: {prop}")
                        return False
                
                # Check for duplicate UIDs
                uid = str(component.get('UID'))
                if uid in uids:
                    print(f"✗ Duplicate UID found: {uid}")
                    return False
                uids.add(uid)
                
                # Check dates
                start = component.get('DTSTART').dt
                if 'DTEND' in component:
                    end = component.get('DTEND').dt
                    if end <= start:
                        print(f"✗ End date <= Start date for: {component.get('SUMMARY')}")
                        return False
                
                # Track dates and categories for statistics
                year = start.year
                if year not in dates:
                    dates[year] = []
                dates[year].append(start)
                
                if 'CATEGORIES' in component:
                    category = str(component.get('CATEGORIES'))
                    if year not in categories:
                        categories[year] = {}
                    if category not in categories[year]:
                        categories[year][category] = 0
                    categories[year][category] += 1
        
        print("✓ All events have unique UIDs")
        print("✓ All events have valid date ranges")
        
        # Print statistics
        print("\nCalendar Statistics:")
        print(f"Total events: {len(uids)}")
        
        print("\nEvents by year:")
        for year in sorted(dates.keys()):
            print(f"  {year}: {len(dates[year])} events")
            if year in categories:
                for category, count in categories[year].items():
                    print(f"    - {category}: {count}")
        
        print("\niCalendar validation successful!")
        return True
    
    except Exception as e:
        print(f"✗ Error validating iCalendar file: {e}")
        return False

if __name__ == "__main__":
    filename = "Public-Holiday-Calendar-SA.ics"
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    
    is_valid = validate_ical(filename)
    if not is_valid:
        print("\nValidation failed! The iCalendar file has issues.")
        sys.exit(1)
    else:
        print("\nValidation successful! The iCalendar file is well-formed.")
        sys.exit(0) 