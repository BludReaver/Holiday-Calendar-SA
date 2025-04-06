#!/usr/bin/env python3
"""
Test script to verify that the calendar meets Google Calendar syncing requirements.
"""

import os
from icalendar import Calendar

def test_google_sync(ics_file="Public-Holiday-Calendar-SA.ics"):
    """Test the calendar for Google Calendar syncing compatibility."""
    if not os.path.exists(ics_file):
        print(f"Error: Calendar file {ics_file} not found")
        return False
    
    print(f"\n=== Google Calendar Sync Test: {ics_file} ===\n")
    
    # Read the calendar file
    with open(ics_file, 'rb') as f:
        cal = Calendar.from_ical(f.read())
    
    # Check calendar level requirements
    required_props = ['VERSION', 'PRODID', 'CALSCALE', 'METHOD']
    print("Checking calendar properties:")
    
    for prop in required_props:
        if prop in cal:
            print(f"✅ Has {prop}: {cal[prop]}")
        else:
            print(f"❌ Missing {prop}")
    
    # Check all events for required properties
    events = [component for component in cal.walk() if component.name == 'VEVENT']
    print(f"\nFound {len(events)} events in the calendar")
    
    # Google calendar requirements:
    # - Must have UID (unique identifier)
    # - Must have SUMMARY (event title)
    # - Must have DTSTART (start time)
    # - Should have DTEND or DURATION (end time or duration)
    # - Should have DTSTAMP (creation timestamp)
    
    missing_props = {
        'UID': 0,
        'SUMMARY': 0,
        'DTSTART': 0,
        'DTEND': 0,
        'DTSTAMP': 0,
    }
    
    print("\nChecking event properties:")
    
    for event in events:
        for prop in missing_props.keys():
            if prop not in event:
                missing_props[prop] += 1
    
    all_valid = True
    for prop, count in missing_props.items():
        if count > 0:
            print(f"❌ {count} events missing {prop}")
            all_valid = False
        else:
            print(f"✅ All events have {prop}")
    
    # Check for TRANSP property (indicates time blocking)
    transparent_events = sum(1 for event in events if event.get('TRANSP', '') == 'TRANSPARENT')
    print(f"\n✅ {transparent_events} events set as TRANSPARENT (non-blocking)")
    
    # Check for CATEGORIES property
    categorized_events = sum(1 for event in events if 'CATEGORIES' in event)
    print(f"✅ {categorized_events} events have CATEGORIES property")
    
    # Check for X-PUBLISHED-TTL (recommended for subscribed calendars)
    has_ttl = 'X-PUBLISHED-TTL' in cal
    if has_ttl:
        print(f"✅ Calendar has X-PUBLISHED-TTL: {cal['X-PUBLISHED-TTL']}")
    else:
        print("ℹ️ Calendar does not have X-PUBLISHED-TTL (recommended but not required)")
    
    # Check X-WR-CALNAME (calendar name)
    has_name = 'X-WR-CALNAME' in cal
    if has_name:
        print(f"✅ Calendar has X-WR-CALNAME: {cal['X-WR-CALNAME']}")
    else:
        print("ℹ️ Calendar does not have X-WR-CALNAME (recommended but not required)")
    
    # Final assessment
    print("\n=== Google Calendar Sync Test Results ===")
    
    if all_valid:
        print("🎉 SUCCESS: Calendar is ready for Google Calendar sync!")
        print("All required properties are present.")
    else:
        print("⚠️ WARNING: Some required properties are missing.")
        print("The calendar may not sync correctly with Google Calendar.")
    
    return all_valid

if __name__ == "__main__":
    test_google_sync() 