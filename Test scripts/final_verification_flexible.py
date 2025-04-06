#!/usr/bin/env python3
"""
Comprehensive verification script for the South Australia Public Holiday Calendar.
This flexible version accepts events from any year as long as they're properly formatted.
"""

import os
import re
import sys
from datetime import datetime
from icalendar import Calendar

# Configuration
ICS_FILE = "Public-Holiday-Calendar-SA.ics"

def verify_icalendar_format(cal):
    """Verify that the calendar follows the iCalendar format."""
    print("================================================================================")
    print(" VERIFYING ICALENDAR FORMAT")
    print("================================================================================")

    # Check if the file starts with BEGIN:VCALENDAR
    with open(ICS_FILE, 'r') as f:
        first_line = f.readline().strip()
        print(f"Calendar begins with BEGIN:VCALENDAR: {'✓' if first_line == 'BEGIN:VCALENDAR' else '✗'}")

    # Check if the file ends with END:VCALENDAR
    with open(ICS_FILE, 'r') as f:
        lines = f.readlines()
        last_line = lines[-1].strip()
        print(f"Calendar ends with END:VCALENDAR: {'✓' if last_line == 'END:VCALENDAR' else '✗'}")

    # Check for required properties
    has_version = 'VERSION' in cal
    print(f"Calendar has VERSION property: {'✓' if has_version else '✗'}")

    has_prodid = 'PRODID' in cal
    print(f"Calendar has PRODID property: {'✓' if has_prodid else '✗'}")

    # Count events
    events = [component for component in cal.walk() if component.name == 'VEVENT']
    print(f"Calendar contains {len(events)} events: {'✓' if len(events) > 0 else '✗'}")

    # Check all events for required properties
    all_events_have_required_props = True
    for event in events:
        if not all(prop in event for prop in ['UID', 'SUMMARY', 'DTSTART']):
            all_events_have_required_props = False
            break
    print(f"Events have required properties: {'✓' if all_events_have_required_props else '✗'}")

    # Check for unique UIDs
    uids = [event['UID'] for event in events]
    unique_uids = len(uids) == len(set(uids))
    print(f"All UIDs are unique: {'✓' if unique_uids else '✗'}")

    # Check Google Calendar sync requirements
    missing_props = {
        'DTEND': 0,
        'DTSTAMP': 0,
        'TRANSP': 0,
    }
    
    for event in events:
        for prop in missing_props.keys():
            if prop not in event:
                missing_props[prop] += 1

    gc_sync_ready = all(count == 0 for count in missing_props.values())
    if gc_sync_ready:
        print(f"Calendar meets Google Calendar syncing requirements: ✓")
    else:
        print(f"Calendar has issues with Google Calendar syncing: ✗")
        for prop, count in missing_props.items():
            if count > 0:
                print(f"  - {count} events missing {prop}")

    # Overall format validation result
    is_valid = (first_line == 'BEGIN:VCALENDAR' and 
                last_line == 'END:VCALENDAR' and 
                has_version and 
                has_prodid and 
                len(events) > 0 and 
                all_events_have_required_props and 
                unique_uids and
                gc_sync_ready)

    print("\nOverall iCalendar format is valid", "✓" if is_valid else "✗")
    print()
    return is_valid

def verify_event_categories(cal):
    """Verify that all events have valid categories."""
    print("================================================================================")
    print(" VERIFYING EVENT CATEGORIES")
    print("================================================================================")

    events = [component for component in cal.walk() if component.name == 'VEVENT']
    
    # Count events by category
    categories = {
        'Public Holiday': 0,
        'School Term': 0,
        'School Holiday': 0,
        'Unknown': 0
    }
    
    events_by_year = {}
    
    for event in events:
        # Get the event year
        dt_start = event.get('dtstart').dt
        event_year = dt_start.year if hasattr(dt_start, 'year') else dt_start.date().year
        
        # Initialize the year counter if not exists
        if event_year not in events_by_year:
            events_by_year[event_year] = {
                'Public Holiday': 0,
                'School Term': 0,
                'School Holiday': 0,
                'Unknown': 0,
                'Total': 0
            }
        
        # Update total count for the year
        events_by_year[event_year]['Total'] += 1
        
        # Get category
        category = event.get('categories')
        category_str = "Unknown"
        
        if category:
            try:
                # Try to get category as string
                category_str = str(category.to_ical().decode('utf-8'))
            except:
                try:
                    # Try direct string conversion
                    category_str = str(category)
                except:
                    category_str = "Unknown"
        
        # Clean up the category string if needed
        if category_str in ["Public Holiday", "School Term", "School Holiday"]:
            # Already clean
            pass
        elif "Public Holiday" in category_str:
            category_str = "Public Holiday"
        elif "School Term" in category_str:
            category_str = "School Term" 
        elif "School Holiday" in category_str:
            category_str = "School Holiday"
        else:
            category_str = "Unknown"
        
        # Update category counts
        if category_str in categories:
            categories[category_str] += 1
            # Update category count for the year
            events_by_year[event_year][category_str] += 1
        else:
            categories['Unknown'] += 1
            events_by_year[event_year]['Unknown'] += 1
    
    # Print category counts
    for category, count in categories.items():
        if category != 'Unknown':
            print(f"{category}s: {count}")
    
    # Print events by year
    print("\nEvents by year:")
    for year in sorted(events_by_year.keys()):
        year_data = events_by_year[year]
        print(f"  {year}: Total: {year_data['Total']} (Public: {year_data['Public Holiday']}, School Terms: {year_data['School Term']}, School Holidays: {year_data['School Holiday']})")
    
    # Print unknown categories
    if categories['Unknown'] > 0:
        print(f"\nFound {categories['Unknown']} events with unknown categories")
        print("Unknown categories found ✗")
    else:
        print("\nNo unknown categories found ✓")
    
    # Overall categories validation result
    all_categorized = categories['Unknown'] == 0
    
    print("\nEvent categories are valid", "✓" if all_categorized else "✗")
    print()
    return all_categorized, events_by_year

def verify_event_formatting(cal):
    """Verify event formatting (all-day events, no brackets)"""
    print("================================================================================")
    print(" VERIFYING EVENT FORMATTING")
    print("================================================================================")

    events = [component for component in cal.walk() if component.name == 'VEVENT']
    issues = []
    
    for event in events:
        # Check if it's an all-day event
        dt_start = event.get('dtstart').dt
        is_all_day = False
        
        try:
            # If dt_start is a date (not datetime), it's an all-day event
            is_all_day = not hasattr(dt_start, 'hour')
        except:
            is_all_day = False
        
        # Check for brackets in summary
        summary = str(event.get('summary', ''))
        
        try:
            has_brackets = '(' in summary or ')' in summary
        except:
            has_brackets = False
            
        if not is_all_day or has_brackets:
            event_name = summary
            issues.append(f"{summary}: {'Not all-day event' if not is_all_day else ''} {'Has brackets' if has_brackets else ''}")
    
    all_valid = len(issues) == 0
    print(f"No events have brackets in their titles: {'✓' if all_valid else '✗'}")
    
    if not all_valid:
        print("\nEvents with formatting issues:")
        for issue in issues:
            print(f"  - {issue}")
    
    print("\nNo formatting issues found", "✓" if all_valid else "✗")
    print("\nEvent formatting is valid", "✓" if all_valid else "✗")
    print()
    return all_valid

def verify_school_terms(events_by_year):
    """Verify that school terms and holidays are present for each expected year."""
    print("================================================================================")
    print(" VERIFYING SCHOOL TERMS AND HOLIDAYS")
    print("================================================================================")

    # Get the years from the events_by_year dictionary
    years = sorted([year for year in events_by_year.keys() 
                    if events_by_year[year]['School Term'] > 0 or 
                       events_by_year[year]['School Holiday'] > 0])
    
    print(f"Found school term and holiday data for years: {', '.join(map(str, years))}")
    
    all_years_valid = True
    
    for year in years:
        # For each year, check if we have at least 4 school terms and holidays
        school_terms = events_by_year[year]['School Term']
        school_holidays = events_by_year[year]['School Holiday']
        
        term_pairs = min(school_terms // 2, 4)  # Each term has a beginning and end
        
        print(f"  ✓ Found {term_pairs} term pairs" if term_pairs >= 4 else f"  ✗ Found only {term_pairs} term pairs (expected 4)")
        print(f"  ✓ Found {school_holidays} holiday events" if school_holidays >= term_pairs else f"  ✗ Found only {school_holidays} holiday events (expected at least {term_pairs})")
        
        if term_pairs < 4 or school_holidays < term_pairs:
            all_years_valid = False
    
    print("\nSchool terms and holidays verification:", "Passed ✓" if all_years_valid else "Failed ✗")
    return all_years_valid

def verify_google_calendar_sync(cal):
    """Verify that the calendar meets Google Calendar sync requirements."""
    print("================================================================================")
    print(" VERIFYING GOOGLE CALENDAR SYNC REQUIREMENTS")
    print("================================================================================")
    
    # Required calendar properties
    required_props = ['VERSION', 'PRODID', 'CALSCALE', 'METHOD']
    missing_cal_props = [prop for prop in required_props if prop not in cal]
    
    if missing_cal_props:
        print(f"❌ Missing required calendar properties: {', '.join(missing_cal_props)}")
    else:
        print("✅ Calendar has all required properties")
    
    # Get all events
    events = [component for component in cal.walk() if component.name == 'VEVENT']
    
    # Check event properties
    required_event_props = ['UID', 'SUMMARY', 'DTSTART', 'DTEND', 'DTSTAMP']
    missing_props = {prop: 0 for prop in required_event_props}
    
    for event in events:
        for prop in required_event_props:
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
    
    has_name = 'X-WR-CALNAME' in cal
    if has_name:
        print(f"✅ Calendar has X-WR-CALNAME: {cal['X-WR-CALNAME']}")
    else:
        print("ℹ️ Calendar does not have X-WR-CALNAME (recommended)")
    
    print("\nGoogle Calendar sync requirements:", "Met ✓" if all_valid else "Not Met ✗")
    return all_valid

def main():
    """Main verification function."""
    if not os.path.exists(ICS_FILE):
        print(f"Error: Calendar file {ICS_FILE} not found")
        return False
    
    # Print header
    print("SOUTH AUSTRALIA PUBLIC HOLIDAY CALENDAR - FLEXIBLE VERIFICATION")
    print(f"Date of verification: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Calendar file: {ICS_FILE}")
    print("Note: This verification accepts events from all years")
    print()
    
    # Read the calendar file
    with open(ICS_FILE, 'rb') as f:
        cal = Calendar.from_ical(f.read())
    
    # Run verification checks
    icalendar_valid = verify_icalendar_format(cal)
    categories_valid, events_by_year = verify_event_categories(cal)
    formatting_valid = verify_event_formatting(cal)
    terms_valid = verify_school_terms(events_by_year)
    google_sync_valid = verify_google_calendar_sync(cal)
    
    # Overall verification result
    all_valid = icalendar_valid and categories_valid and formatting_valid and terms_valid and google_sync_valid
    
    print("================================================================================")
    print("OVERALL RESULT:")
    print("================================================================================")
    print("iCalendar Format:", "Valid ✓" if icalendar_valid else "Invalid ✗")
    print("Event Categories:", "Valid ✓" if categories_valid else "Invalid ✗")
    print("Event Formatting:", "Valid ✓" if formatting_valid else "Invalid ✗")
    print("School Terms and Holidays:", "Valid ✓" if terms_valid else "Invalid ✗")
    print("Google Calendar Sync:", "Valid ✓" if google_sync_valid else "Invalid ✗")
    print()
    print("CALENDAR VERIFICATION:", "PASSED ✓" if all_valid else "FAILED ✗")
    print("================================================================================")
    
    return all_valid

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1) 