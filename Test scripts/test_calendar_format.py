#!/usr/bin/env python3
"""
Test script to verify that the calendar meets all formatting requirements.
Specifically checks:
1. All events are formatted as all-day events
2. No events have brackets in their titles
3. Part-day holidays (like Christmas Eve) are treated as full-day events
4. All events have the proper categorization
5. The calendar is properly formatted for syncing with Google Calendar
"""

import os
import datetime
from icalendar import Calendar

def test_calendar_format(ics_file="Public-Holiday-Calendar-SA.ics"):
    """Test the calendar format to ensure it meets all requirements."""
    if not os.path.exists(ics_file):
        print(f"Error: Calendar file {ics_file} not found")
        return False
    
    print(f"\n=== Testing Calendar Format: {ics_file} ===\n")
    
    # Read the calendar file
    with open(ics_file, 'rb') as f:
        cal = Calendar.from_ical(f.read())
    
    # Check for Google Calendar compatibility
    required_properties = ['VERSION', 'PRODID', 'CALSCALE', 'METHOD']
    for prop in required_properties:
        if prop not in cal:
            print(f"❌ Missing required property: {prop}")
        else:
            print(f"✅ Has required property: {prop}")
    
    # Check all events
    events = [component for component in cal.walk() if component.name == 'VEVENT']
    print(f"\nFound {len(events)} events in the calendar")
    
    # Check categories
    categories = {}
    for event in events:
        category = event.get('categories')
        if category:
            # Handle categories properly
            try:
                # Try to convert to string and handle as a list
                cat_value = category.to_ical().decode('utf-8')
                categories[cat_value] = categories.get(cat_value, 0) + 1
            except (AttributeError, IndexError):
                # Fallback: try as a direct string
                try:
                    cat_name = str(category)
                    categories[cat_name] = categories.get(cat_name, 0) + 1
                except:
                    categories["Unknown Category"] = categories.get("Unknown Category", 0) + 1
        else:
            categories["Uncategorized"] = categories.get("Uncategorized", 0) + 1
    
    print("\n=== Category Distribution ===")
    for category, count in categories.items():
        print(f"- {category}: {count} events")
    
    # Check part-day holidays
    part_day_holidays = [
        "Christmas Eve",
        "New Year's Eve",
        "Proclamation Day"
    ]
    
    print("\n=== Part-Day Holiday Check ===")
    part_day_events = []
    for event in events:
        summary = str(event.get('summary', ''))
        
        for holiday in part_day_holidays:
            if holiday in summary:
                try:
                    dt_start = event.get('dtstart').dt if event.get('dtstart') else None
                    if dt_start is None:
                        print(f"⚠️ {summary} is missing dtstart property")
                        continue
                        
                    # Check if it's an all-day event
                    # For all-day events, dt_start is a date, not a datetime
                    is_all_day = isinstance(dt_start, datetime.date) and not isinstance(dt_start, datetime.datetime)
                    
                    part_day_events.append((summary, is_all_day))
                    
                    if is_all_day:
                        print(f"✅ {summary} is correctly formatted as an all-day event")
                    else:
                        print(f"❌ {summary} is NOT an all-day event")
                except Exception as e:
                    print(f"⚠️ Error processing {summary}: {str(e)}")
    
    if not part_day_events:
        print("No part-day holidays found in the calendar")
    
    # Check for brackets in event summaries
    print("\n=== Bracket Check ===")
    bracket_events = []
    bracket_chars = ['(', ')', '[', ']', '{', '}', '<', '>']
    
    for event in events:
        summary = str(event.get('summary', ''))
        has_brackets = any(char in summary for char in bracket_chars)
        
        if has_brackets:
            bracket_events.append(summary)
    
    if bracket_events:
        print(f"❌ Found {len(bracket_events)} events with brackets:")
        for event in bracket_events:
            print(f"  - {event}")
    else:
        print("✅ No events have brackets in their titles")
    
    # Check all-day formatting
    print("\n=== All-Day Event Check ===")
    non_all_day_events = []
    
    for event in events:
        summary = str(event.get('summary', ''))
        try:
            dt_start = event.get('dtstart').dt if event.get('dtstart') else None
            if dt_start is None:
                print(f"⚠️ {summary} is missing dtstart property")
                continue
               
            # Check if it's an all-day event 
            is_all_day = isinstance(dt_start, datetime.date) and not isinstance(dt_start, datetime.datetime)
            
            if not is_all_day:
                non_all_day_events.append(summary)
        except Exception as e:
            print(f"⚠️ Error processing {summary}: {str(e)}")
    
    if non_all_day_events:
        print(f"❌ Found {len(non_all_day_events)} events that are NOT formatted as all-day events:")
        for event in non_all_day_events:
            print(f"  - {event}")
    else:
        print("✅ All events are correctly formatted as all-day events")
    
    # Check for Google Calendar syncing requirements
    print("\n=== Google Calendar Sync Requirements ===")
    sync_issues = []
    
    for event in events:
        event_summary = str(event.get('summary', ''))
        
        # Check for UID
        if 'UID' not in event:
            sync_issues.append((event_summary, "Missing UID"))
        
        # Check for DTSTAMP
        if 'DTSTAMP' not in event:
            sync_issues.append((event_summary, "Missing DTSTAMP"))
        
        # Check for DTSTART
        if 'DTSTART' not in event:
            sync_issues.append((event_summary, "Missing DTSTART"))
        
        # Check for SUMMARY
        if 'SUMMARY' not in event:
            sync_issues.append((event_summary, "Missing SUMMARY"))
    
    if sync_issues:
        print(f"❌ Found {len(sync_issues)} events with Google Calendar sync issues:")
        for event, issue in sync_issues:
            print(f"  - {event}: {issue}")
    else:
        print("✅ All events meet Google Calendar sync requirements")
    
    # Final summary
    print("\n=== Calendar Format Test Summary ===")
    all_tests_passed = not bracket_events and not non_all_day_events and not sync_issues
    
    if all_tests_passed:
        print("🎉 SUCCESS: All format tests passed!")
        print("The calendar is ready for use with Google Calendar and other platforms.")
    else:
        print("⚠️ WARNING: Some format tests failed. See details above.")
    
    return all_tests_passed

if __name__ == "__main__":
    test_calendar_format() 