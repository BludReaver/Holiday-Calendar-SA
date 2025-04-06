#!/usr/bin/env python3
"""
Comprehensive Verification Script for South Australia Public Holiday Calendar
This script verifies all aspects of the calendar:
- iCalendar format validity
- Event categories and counts
- Public holidays verification
- School terms and holidays verification
- Event formatting (all-day events, no brackets)
"""

import re
import os
from datetime import datetime

# Expected counts
EXPECTED_TOTAL_EVENTS = 90
EXPECTED_PUBLIC_HOLIDAYS = 42
EXPECTED_SCHOOL_TERMS = 24
EXPECTED_SCHOOL_HOLIDAYS = 24

# Key holidays to verify for each year
KEY_HOLIDAYS = {
    2025: {
        "New Year's Day": "2025-01-01",
        "Australia Day": "2025-01-27",
        "Adelaide Cup Day": "2025-03-10",
        "Good Friday": "2025-04-18",
        "Easter Monday": "2025-04-21",
        "Anzac Day": "2025-04-25",
        "King's Birthday": "2025-06-09",
        "Labour Day": "2025-10-06",
        "Christmas Day": "2025-12-25"
    },
    2026: {
        "New Year's Day": "2026-01-01",
        "Australia Day": "2026-01-26",
        "Adelaide Cup Day": "2026-03-09",
        "Good Friday": "2026-04-03",
        "Easter Monday": "2026-04-06",
        "Anzac Day": "2026-04-25",
        "King's Birthday": "2026-06-08",
        "Labour Day": "2026-10-05",
        "Christmas Day": "2026-12-25"
    },
    2027: {
        "New Year's Day": "2027-01-01",
        "Australia Day": "2027-01-26",
        "Adelaide Cup Day": "2027-03-08",
        "Good Friday": "2027-03-26",
        "Easter Monday": "2027-03-29",
        "Anzac Day": "2027-04-25",
        "King's Birthday": "2027-06-14",
        "Labour Day": "2027-10-04",
        "Christmas Day": "2027-12-25"
    }
}

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def verify_icalendar_format():
    """Verify that the calendar file follows the iCalendar format"""
    print_section("VERIFYING ICALENDAR FORMAT")
    
    with open('Public-Holiday-Calendar-SA.ics', 'r') as f:
        content = f.read()
    
    # Check for required iCalendar components
    has_begin_vcalendar = "BEGIN:VCALENDAR" in content
    has_end_vcalendar = "END:VCALENDAR" in content
    has_version = re.search(r'VERSION:\d+\.\d+', content) is not None
    has_prodid = re.search(r'PRODID:.*', content) is not None
    
    # Check for events
    events = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL)
    has_events = len(events) > 0
    
    # Check for required event properties in at least one event
    has_required_properties = False
    if has_events:
        event = events[0]
        has_dtstart = re.search(r'DTSTART.*:', event) is not None
        has_dtend = re.search(r'DTEND.*:', event) is not None
        has_summary = re.search(r'SUMMARY:', event) is not None
        has_uid = re.search(r'UID:', event) is not None
        has_required_properties = has_dtstart and has_dtend and has_summary and has_uid
    
    # Check for unique UIDs
    uids = re.findall(r'UID:(.*?)(?:\r\n|\r|\n)', content)
    unique_uids = len(set(uids)) == len(uids)
    
    print(f"Calendar begins with BEGIN:VCALENDAR: {'✓' if has_begin_vcalendar else '✗'}")
    print(f"Calendar ends with END:VCALENDAR: {'✓' if has_end_vcalendar else '✗'}")
    print(f"Calendar has VERSION property: {'✓' if has_version else '✗'}")
    print(f"Calendar has PRODID property: {'✓' if has_prodid else '✗'}")
    print(f"Calendar contains {len(events)} events: {'✓' if has_events else '✗'}")
    print(f"Events have required properties: {'✓' if has_required_properties else '✗'}")
    print(f"All UIDs are unique: {'✓' if unique_uids else '✗'}")
    
    is_valid = (has_begin_vcalendar and has_end_vcalendar and has_version and 
                has_prodid and has_events and has_required_properties and unique_uids)
    
    print(f"\nOverall iCalendar format is {'valid ✓' if is_valid else 'invalid ✗'}")
    return is_valid, events

def verify_event_categories(events):
    """Verify event categories and counts"""
    print_section("VERIFYING EVENT CATEGORIES")
    
    categories = {"Public Holiday": 0, "School Term": 0, "School Holiday": 0, "Unknown": []}
    
    for event in events:
        category_match = re.search(r'CATEGORIES:(.*?)(?:\r\n|\r|\n)', event)
        summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
        
        if category_match:
            category = category_match.group(1).strip()
            if category in categories:
                categories[category] += 1
            else:
                summary = summary_match.group(1).strip() if summary_match else "Unknown"
                categories["Unknown"].append(f"{summary} (Category: {category})")
    
    print(f"Public Holidays: {categories['Public Holiday']} (Expected: {EXPECTED_PUBLIC_HOLIDAYS})")
    print(f"School Terms: {categories['School Term']} (Expected: {EXPECTED_SCHOOL_TERMS})")
    print(f"School Holidays: {categories['School Holiday']} (Expected: {EXPECTED_SCHOOL_HOLIDAYS})")
    
    if categories["Unknown"]:
        print("\nUnknown categories:")
        for item in categories["Unknown"]:
            print(f"  - {item}")
    else:
        print("\nNo unknown categories found ✓")
    
    categories_valid = (
        categories["Public Holiday"] == EXPECTED_PUBLIC_HOLIDAYS and
        categories["School Term"] == EXPECTED_SCHOOL_TERMS and
        categories["School Holiday"] == EXPECTED_SCHOOL_HOLIDAYS and
        not categories["Unknown"]
    )
    
    print(f"\nEvent categories are {'valid ✓' if categories_valid else 'invalid ✗'}")
    return categories_valid

def verify_event_formatting(events):
    """Verify event formatting (all-day events, no brackets)"""
    print_section("VERIFYING EVENT FORMATTING")
    
    all_valid = True
    issues = []
    
    for event in events:
        # Check for all-day event format
        dtstart_match = re.search(r'DTSTART;VALUE=DATE:', event)
        dtend_match = re.search(r'DTEND;VALUE=DATE:', event)
        is_all_day = dtstart_match is not None and dtend_match is not None
        
        # Check for brackets in summary
        summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
        if summary_match:
            summary = summary_match.group(1).strip()
            has_brackets = '(' in summary or ')' in summary
        else:
            summary = "Unknown"
            has_brackets = False
        
        if not is_all_day or has_brackets:
            all_valid = False
            issues.append(f"{summary}: {'Not all-day event' if not is_all_day else ''} {'Has brackets' if has_brackets else ''}")
    
    print(f"All events are all-day events: {'✓' if all_valid else '✗'}")
    print(f"No events have brackets in their titles: {'✓' if all_valid else '✗'}")
    
    if issues:
        print("\nIssues found:")
        for issue in issues[:10]:  # Show at most 10 issues
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more issues")
    else:
        print("\nNo formatting issues found ✓")
    
    print(f"\nEvent formatting is {'valid ✓' if all_valid else 'invalid ✗'}")
    return all_valid

def verify_public_holidays(events):
    """Verify that key public holidays are present with correct dates"""
    print_section("VERIFYING PUBLIC HOLIDAYS")
    
    holidays_by_year = {2025: {}, 2026: {}, 2027: {}}
    
    for event in events:
        date_match = re.search(r'DTSTART;VALUE=DATE:(\d{8})', event)
        summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
        category_match = re.search(r'CATEGORIES:(.*?)(?:\r\n|\r|\n)', event)
        
        if date_match and summary_match and category_match:
            date_str = date_match.group(1)
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            summary = summary_match.group(1).strip()
            category = category_match.group(1).strip()
            
            if category == "Public Holiday" and year in holidays_by_year:
                holidays_by_year[year][summary] = f"{year}-{month:02d}-{day:02d}"
    
    # Verify against expected holidays
    missing_holidays = []
    incorrect_dates = []
    
    for year, expected in KEY_HOLIDAYS.items():
        for holiday_name, expected_date in expected.items():
            found = False
            
            # Check for exact match
            if holiday_name in holidays_by_year[year]:
                found = True
                actual_date = holidays_by_year[year][holiday_name]
                if actual_date != expected_date:
                    incorrect_dates.append(f"{year} {holiday_name}: Expected {expected_date}, got {actual_date}")
            
            # Check for partial match
            if not found:
                for actual_name, actual_date in holidays_by_year[year].items():
                    if holiday_name in actual_name:
                        found = True
                        if actual_date != expected_date:
                            incorrect_dates.append(f"{year} {holiday_name}: Expected {expected_date}, got {actual_date} (matched '{actual_name}')")
                        break
            
            # Report missing holiday
            if not found:
                missing_holidays.append(f"{year} {holiday_name}")
    
    print("Checking key public holidays for 2025-2027...")
    
    # Process results
    for year in sorted(holidays_by_year.keys()):
        print(f"\n{year} Public Holidays:")
        for expected_name in KEY_HOLIDAYS[year].keys():
            # Check if holiday exists (exact or partial match)
            found = False
            for actual_name in holidays_by_year[year].keys():
                if expected_name == actual_name or expected_name in actual_name:
                    date = holidays_by_year[year][actual_name]
                    expected_date = KEY_HOLIDAYS[year][expected_name]
                    status = "✓" if date == expected_date else "✗"
                    print(f"  {status} {actual_name}: {date}")
                    found = True
                    break
            if not found:
                print(f"  ✗ {expected_name}: Missing")
    
    # Print unexpected holidays
    print("\nAdditional holidays found:")
    additional_holidays = []
    for year in sorted(holidays_by_year.keys()):
        for holiday_name, date in sorted(holidays_by_year[year].items()):
            # Check if it's not in the expected key holidays
            is_unexpected = True
            for expected_name in KEY_HOLIDAYS[year].keys():
                if expected_name == holiday_name or expected_name in holiday_name:
                    is_unexpected = False
                    break
            if is_unexpected:
                additional_holidays.append(f"  - {year} {holiday_name}: {date}")
    
    if additional_holidays:
        for holiday in additional_holidays:
            print(holiday)
    else:
        print("  No additional holidays found")
    
    all_valid = not missing_holidays and not incorrect_dates
    
    if missing_holidays:
        print("\nMissing holidays:")
        for holiday in missing_holidays:
            print(f"  - {holiday}")
    
    if incorrect_dates:
        print("\nIncorrect dates:")
        for issue in incorrect_dates:
            print(f"  - {issue}")
    
    print(f"\nPublic holidays verification: {'Passed ✓' if all_valid else 'Failed ✗'}")
    return all_valid

def verify_school_terms_and_holidays(events):
    """Verify school terms and holidays patterns"""
    print_section("VERIFYING SCHOOL TERMS AND HOLIDAYS")
    
    # Create structures to store terms and holidays by year
    school_terms = {2025: [], 2026: [], 2027: []}
    school_holidays = {2025: [], 2026: [], 2027: []}
    
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
            summary = summary_match.group(1).strip()
            category = category_match.group(1).strip()
            
            # Store event info based on category
            event_info = {
                "date": f"{year}-{month:02d}-{day:02d}",
                "summary": summary
            }
            
            if category == "School Term":
                if year in school_terms:
                    school_terms[year].append(event_info)
            elif category == "School Holiday":
                if year in school_holidays:
                    school_holidays[year].append(event_info)
    
    # Sort events by date
    for year in school_terms:
        school_terms[year].sort(key=lambda x: x["date"])
        school_holidays[year].sort(key=lambda x: x["date"])
    
    # Verify patterns for each year
    all_valid = True
    years_status = {}
    
    for year in sorted(school_terms.keys()):
        terms = school_terms[year]
        holidays = school_holidays[year]
        
        year_valid = True
        year_report = []
        
        # Check number of terms
        if len(terms) == 8:  # 4 begins and 4 ends
            year_report.append(f"  ✓ Found 8 term events (4 terms)")
            
            # Check term pattern (begins followed by ends)
            begins = [t for t in terms if "Begins" in t["summary"]]
            ends = [t for t in terms if "Ends" in t["summary"]]
            
            if len(begins) == 4 and len(ends) == 4:
                year_report.append(f"  ✓ Found 4 term begins and 4 term ends")
                
                # Check alternating pattern
                alternating = True
                i = 0
                while i < len(terms) - 1:
                    if ("Begins" in terms[i]["summary"] and "Ends" not in terms[i+1]["summary"]) or \
                       ("Ends" in terms[i]["summary"] and "Begins" not in terms[i+1]["summary"]):
                        alternating = False
                        break
                    i += 2
                
                if alternating:
                    year_report.append(f"  ✓ Terms follow the correct Begin->End pattern")
                else:
                    year_report.append(f"  ✗ Terms do not follow the correct Begin->End pattern")
                    year_valid = False
            else:
                year_report.append(f"  ✗ Imbalance in term begins ({len(begins)}) and ends ({len(ends)})")
                year_valid = False
        else:
            year_report.append(f"  ✗ Expected 8 term events, found {len(terms)}")
            year_valid = False
            
        # Check number of holidays
        if len(holidays) == 8:  # 2 per term (start and end of holiday)
            year_report.append(f"  ✓ Found 8 holiday events (4 holiday periods)")
        else:
            year_report.append(f"  ✗ Expected 8 holiday events, found {len(holidays)}")
            year_valid = False
        
        all_valid = all_valid and year_valid
        years_status[year] = {"valid": year_valid, "report": year_report}
    
    # Print results
    for year in sorted(years_status.keys()):
        status = years_status[year]
        print(f"\n{year} School Calendar: {'✓' if status['valid'] else '✗'}")
        for line in status["report"]:
            print(line)
    
    print(f"\nSchool terms and holidays verification: {'Passed ✓' if all_valid else 'Failed ✗'}")
    return all_valid

def main():
    """Main function to run all verifications"""
    print("SOUTH AUSTRALIA PUBLIC HOLIDAY CALENDAR - FINAL VERIFICATION")
    print(f"Date of verification: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Calendar file: Public-Holiday-Calendar-SA.ics")
    
    # Verify calendar exists
    if not os.path.exists('Public-Holiday-Calendar-SA.ics'):
        print("\nERROR: Calendar file 'Public-Holiday-Calendar-SA.ics' not found!")
        return False
    
    # Run all verifications
    is_valid_format, events = verify_icalendar_format()
    categories_valid = verify_event_categories(events)
    formatting_valid = verify_event_formatting(events)
    holidays_valid = verify_public_holidays(events)
    school_valid = verify_school_terms_and_holidays(events)
    
    # Final result
    all_valid = is_valid_format and categories_valid and formatting_valid and holidays_valid and school_valid
    
    print_section("FINAL VERIFICATION RESULT")
    print(f"Total events in calendar: {len(events)}")
    print(f"iCalendar format: {'✓' if is_valid_format else '✗'}")
    print(f"Event categories: {'✓' if categories_valid else '✗'}")
    print(f"Event formatting: {'✓' if formatting_valid else '✗'}")
    print(f"Public holidays: {'✓' if holidays_valid else '✗'}")
    print(f"School terms and holidays: {'✓' if school_valid else '✗'}")
    
    print("\nOVERALL RESULT:")
    if all_valid:
        print("✅ CALENDAR VERIFICATION PASSED - All checks successful! ✅")
    else:
        print("❌ CALENDAR VERIFICATION FAILED - Please check the issues above. ❌")
    
    return all_valid

if __name__ == "__main__":
    main() 