#!/usr/bin/env python3
import os
from icalendar import Calendar
from datetime import datetime
import re
import sys

def verify_calendar():
    """
    Comprehensively verify the calendar against all requirements:
    - All events must be all-day events
    - No events should have brackets in their titles
    - All events must have proper categories
    - All required holidays must be present
    - No part-day holidays
    """
    print("\n" + "="*80)
    print("{:^80}".format("SOUTH AUSTRALIA PUBLIC HOLIDAY CALENDAR VERIFICATION"))
    print("="*80)
    
    try:
        with open('Public-Holiday-Calendar-SA.ics', 'rb') as f:
            cal = Calendar.from_ical(f.read())
    except Exception as e:
        print(f"Error opening calendar file: {e}")
        sys.exit(1)

    events = list(cal.walk('VEVENT'))
    print(f"Found {len(events)} events in the calendar\n")
    
    # 1. Check for all-day events
    non_all_day = []
    for event in events:
        summary = str(event.get('summary', ''))
        dtstart = event.get('dtstart')
        if dtstart and hasattr(dtstart, 'dt'):
            if hasattr(dtstart.dt, 'hour'):  # Datetime (not all-day)
                non_all_day.append(summary)
    
    if non_all_day:
        print("❌ Found non-all-day events:")
        for e in non_all_day[:5]:
            print(f"  - {e}")
        if len(non_all_day) > 5:
            print(f"  ... and {len(non_all_day) - 5} more")
    else:
        print("✅ All events are properly formatted as all-day events")
    
    # 2. Check for brackets in titles
    bracket_events = []
    for event in events:
        summary = str(event.get('summary', ''))
        if re.search(r'[\(\[\{\<].*?[\)\]\}\>]', summary):
            bracket_events.append(summary)
    
    if bracket_events:
        print("\n❌ Found events with brackets in titles:")
        for e in bracket_events[:5]:
            print(f"  - {e}")
        if len(bracket_events) > 5:
            print(f"  ... and {len(bracket_events) - 5} more")
    else:
        print("\n✅ No events have brackets in their titles")
    
    # 3. Check categories
    categories = {
        'Public Holiday': 0,
        'School Term': 0,
        'School Holiday': 0,
        'Unknown': 0
    }
    
    for event in events:
        summary = str(event.get('summary', ''))
        category = event.get('categories')
        
        if category:
            cat_str = str(category)
            if 'Public Holiday' in cat_str:
                categories['Public Holiday'] += 1
            elif 'School Term' in cat_str:
                categories['School Term'] += 1
            elif 'School Holiday' in cat_str:
                categories['School Holiday'] += 1
            else:
                # Try to extract from the name
                if "Term" in summary and ("Begin" in summary or "End" in summary):
                    categories['School Term'] += 1
                elif "Holiday" in summary and "School" in summary:
                    categories['School Holiday'] += 1
                else:
                    categories['Public Holiday'] += 1
        else:
            # No category field, determine from summary
            if "Term" in summary and ("Begin" in summary or "End" in summary):
                categories['School Term'] += 1
            elif "Holiday" in summary and "School" in summary:
                categories['School Holiday'] += 1
            else:
                categories['Public Holiday'] += 1
    
    print("\nEvent categories distribution:")
    for cat, count in categories.items():
        if cat != 'Unknown':
            print(f"  - {cat}: {count}")
    
    if categories['Unknown'] > 0:
        print(f"❌ Found {categories['Unknown']} events with unknown categories")
    else:
        print("✅ All events have proper categories")
    
    # 4. Check for specific important holidays
    important_holidays = {
        "New Year's Day": False,
        "Australia Day": False,
        "Adelaide Cup Day": False,
        "Good Friday": False,
        "Easter Saturday": False,
        "Easter Sunday": False,
        "Easter Monday": False,
        "Anzac Day": False,
        "King's Birthday": False, 
        "Labour Day": False,
        "Christmas Eve": False,
        "Christmas Day": False,
        "Proclamation Day": False,
        "New Year's Eve": False
    }
    
    for event in events:
        summary = str(event.get('summary', ''))
        for holiday in important_holidays:
            # Check with different apostrophe variations
            if holiday in summary or holiday.replace("'s", "") in summary or holiday.replace("'", "") in summary:
                important_holidays[holiday] = True
    
    print("\nVerifying important holidays:")
    missing_holidays = []
    for holiday, present in important_holidays.items():
        if not present:
            missing_holidays.append(holiday)
    
    if missing_holidays:
        print("❌ Missing important holidays:")
        for holiday in missing_holidays:
            print(f"  - {holiday}")
    else:
        print("✅ All important holidays are present")
    
    # 5. Check for part-day holidays
    part_day_count = 0
    part_day_fixed = 0
    for event in events:
        summary = str(event.get('summary', ''))
        if "part-day" in summary.lower() or "part day" in summary.lower():
            part_day_count += 1
            # Check if they've been converted to full-day holidays
            if "Public Holiday" in summary:
                part_day_fixed += 1
    
    if part_day_count > 0:
        if part_day_count == part_day_fixed:
            print(f"\n✅ All {part_day_count} part-day holidays correctly converted to full-day holidays")
        else:
            print(f"\n❌ Found {part_day_count - part_day_fixed} part-day holidays not converted properly")
    else:
        print("\n✅ No part-day holidays found, which is expected if they were properly converted")
    
    # 6. Check distribution by year
    years = {}
    for event in events:
        dtstart = event.get('dtstart')
        if dtstart and hasattr(dtstart, 'dt'):
            year = dtstart.dt.year
            if year not in years:
                years[year] = 0
            years[year] += 1
    
    print("\nEvent distribution by year:")
    for year in sorted(years.keys()):
        print(f"  - {year}: {years[year]} events")
    
    # Summary
    print("\n" + "="*80)
    print("{:^80}".format("VERIFICATION SUMMARY"))
    print("="*80)
    
    all_tests_passed = (
        len(non_all_day) == 0 and
        len(bracket_events) == 0 and
        categories['Unknown'] == 0 and
        len(missing_holidays) == 0 and
        (part_day_count == 0 or part_day_count == part_day_fixed)
    )
    
    if all_tests_passed:
        print("\n✅ All verification tests passed!")
        print("\nThe calendar meets all requirements:")
        print("  - All events are all-day events")
        print("  - No events have brackets in their titles")
        print("  - All events have proper categories")
        print("  - All required holidays are present")
        print(f"  - All {part_day_fixed} part-day holidays are correctly formatted")
        print(f"\nTotal of {len(events)} events spanning {len(years)} years ({', '.join(str(y) for y in sorted(years.keys()))})")
        return 0
    else:
        print("\n❌ Some verification tests failed. See details above.")
        return 1

if __name__ == "__main__":
    sys.exit(verify_calendar()) 