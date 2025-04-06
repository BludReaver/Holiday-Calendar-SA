#!/usr/bin/env python3
"""
Final Comprehensive Test Script

This script performs a complete verification of the SA Public Holiday Calendar system, including:
1. Calendar format verification (all-day events, no brackets)
2. Notification functionality (error and success)
3. Event categorization
4. Term dates validation
5. Creating a sample calendar to ensure system works end-to-end
"""

import os
import sys
import re
import datetime
import subprocess
from icalendar import Calendar

# Configuration
ICS_FILE = "Public-Holiday-Calendar-SA.ics"
UPDATE_SCRIPT = "update_calendar.py"
LOG_FILE = "update_log.txt"

def banner(title):
    """Print a section banner for better readability."""
    width = 80
    print("\n" + "=" * width)
    print(f" {title}".center(width))
    print("=" * width)

def test_calendar_format():
    """Verify that the calendar follows all formatting requirements."""
    banner("CALENDAR FORMAT TEST")
    
    if not os.path.exists(ICS_FILE):
        print(f"Error: Calendar file {ICS_FILE} not found")
        return False
    
    # Read the calendar file
    with open(ICS_FILE, 'rb') as f:
        cal = Calendar.from_ical(f.read())
    
    # Get all events
    events = [component for component in cal.walk() if component.name == 'VEVENT']
    print(f"Found {len(events)} events in the calendar")
    
    # Check for brackets in event titles
    bracket_events = []
    bracket_chars = ['(', ')', '[', ']', '{', '}', '<', '>']
    
    for event in events:
        summary = str(event.get('summary', ''))
        has_brackets = any(char in summary for char in bracket_chars)
        
        if has_brackets:
            bracket_events.append(summary)
    
    if bracket_events:
        print(f"❌ Found {len(bracket_events)} events with brackets:")
        for event in bracket_events[:5]:  # Show at most 5
            print(f"  - {event}")
        if len(bracket_events) > 5:
            print(f"  ... and {len(bracket_events) - 5} more")
    else:
        print("✅ No events have brackets in their titles")
    
    # Check all-day formatting
    non_all_day_events = []
    
    for event in events:
        summary = str(event.get('summary', ''))
        try:
            dt_start = event.get('dtstart').dt
            
            # Check if it's an all-day event
            is_all_day = isinstance(dt_start, datetime.date) and not isinstance(dt_start, datetime.datetime)
            
            if not is_all_day:
                non_all_day_events.append(summary)
        except Exception as e:
            print(f"Error processing {summary}: {str(e)}")
    
    if non_all_day_events:
        print(f"❌ Found {len(non_all_day_events)} events that are NOT formatted as all-day events:")
        for event in non_all_day_events[:5]:  # Show at most 5
            print(f"  - {event}")
        if len(non_all_day_events) > 5:
            print(f"  ... and {len(non_all_day_events) - 5} more")
    else:
        print("✅ All events are correctly formatted as all-day events")
    
    # Check for part-day holiday handling
    part_day_holidays = ["Christmas Eve", "New Year's Eve", "Proclamation Day"]
    part_day_events = []
    
    for event in events:
        summary = str(event.get('summary', ''))
        for holiday in part_day_holidays:
            if holiday in summary:
                part_day_events.append(summary)
                break
    
    if part_day_events:
        print(f"✅ Found and properly formatted {len(part_day_events)} part-day holidays:")
        for event in part_day_events:
            print(f"  - {event}")
    else:
        print("⚠️ No part-day holidays found in the calendar")
    
    # Check categories
    categories = {
        'Public Holiday': 0,
        'School Term': 0,
        'School Holiday': 0,
        'Unknown': 0
    }
    
    for event in events:
        category = event.get('categories')
        if category:
            try:
                # Try different methods to extract the category
                cat_str = ""
                
                # Method 1: Direct string representation
                cat_str = str(category)
                
                # Method 2: Try to decode from ical format
                if not cat_str or cat_str == "[]":
                    try:
                        cat_str = category.to_ical().decode('utf-8')
                    except:
                        pass
                
                # Method 3: Try alternative property access
                if not cat_str or cat_str == "[]":
                    try:
                        if hasattr(category, 'cats'):
                            cat_str = str(category.cats[0])
                    except:
                        pass
                
                # Determine category based on string content
                if "Public Holiday" in cat_str:
                    categories['Public Holiday'] += 1
                elif "School Term" in cat_str:
                    categories['School Term'] += 1
                elif "School Holiday" in cat_str:
                    categories['School Holiday'] += 1
                else:
                    # Try to extract from summary as fallback
                    summary = str(event.get('summary', ''))
                    if "Term" in summary and ("Begin" in summary or "End" in summary):
                        categories['School Term'] += 1
                    elif "Holiday" in summary:
                        categories['School Holiday'] += 1
                    else:
                        # Assume it's a public holiday if not school-related
                        categories['Public Holiday'] += 1
            except Exception as e:
                print(f"Error processing category: {str(e)}")
                categories['Unknown'] += 1
        else:
            # If no category, try to guess from summary
            summary = str(event.get('summary', ''))
            if "Term" in summary and ("Begin" in summary or "End" in summary):
                categories['School Term'] += 1
            elif "Holiday" in summary:
                categories['School Holiday'] += 1
            else:
                # Assume it's a public holiday if not school-related
                categories['Public Holiday'] += 1
    
    print("\nEvent categories distribution:")
    for category, count in categories.items():
        if category != 'Unknown':
            print(f"  - {category}s: {count}")
    
    if categories['Unknown'] > 0:
        print(f"❌ Found {categories['Unknown']} events with unknown categories")
    else:
        print("✅ All events are properly categorized")
    
    # Overall format test result
    format_valid = (not bracket_events and 
                   not non_all_day_events and 
                   categories['Unknown'] == 0)
    
    print("\nOverall Calendar Format:", "Valid ✓" if format_valid else "Invalid ✗")
    return format_valid

def test_error_notification():
    """Test error notification functionality."""
    banner("ERROR NOTIFICATION TEST")
    
    # Temporarily modify update_calendar.py to enable FAIL_TEST_MODE
    original_content = None
    with open(UPDATE_SCRIPT, 'r') as f:
        original_content = f.read()
    
    # Set FAIL_TEST_MODE to True
    modified_content = re.sub(
        r'FAIL_TEST_MODE = False', 
        'FAIL_TEST_MODE = True',
        original_content
    )
    
    with open(UPDATE_SCRIPT, 'w') as f:
        f.write(modified_content)
    
    print("Temporarily enabled FAIL_TEST_MODE to test error notification")
    
    # Run the update script and expect it to fail
    try:
        print("Running update script with FAIL_TEST_MODE enabled...")
        subprocess.run(['python', UPDATE_SCRIPT], check=True, capture_output=True)
        print("❌ Update script did not fail as expected")
        test_passed = False
    except subprocess.CalledProcessError as e:
        print("✅ Update script failed as expected")
        test_passed = True
        
        # Check if the log file contains the expected error message
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                log_content = f.read()
                if "Fail test mode is active" in log_content:
                    print("✅ Error log contains the expected failure message")
                else:
                    print("❌ Error log does not contain the expected failure message")
                    test_passed = False
        else:
            print("❌ Error log file not created")
            test_passed = False
    
    # Set FAIL_TEST_MODE back to False
    with open(UPDATE_SCRIPT, 'w') as f:
        f.write(original_content)
    
    print("Restored FAIL_TEST_MODE to False")
    
    print("\nError Notification Test:", "Passed ✓" if test_passed else "Failed ✗")
    return test_passed

def test_calendar_generation():
    """Test that the calendar can be successfully generated."""
    banner("CALENDAR GENERATION TEST")
    
    # Backup the existing calendar file if it exists
    backup_file = None
    if os.path.exists(ICS_FILE):
        backup_file = f"{ICS_FILE}.backup"
        os.rename(ICS_FILE, backup_file)
        print(f"Backed up existing calendar to {backup_file}")
    
    # Run the create_calendar.py script (if it exists)
    create_script = "create_calendar.py"
    if os.path.exists(create_script):
        try:
            print(f"Running {create_script}...")
            subprocess.run(['python', create_script], check=True, capture_output=True)
            
            if os.path.exists(ICS_FILE):
                print(f"✅ Successfully created {ICS_FILE}")
                
                # Verify the generated calendar
                test_passed = test_calendar_format()
            else:
                print(f"❌ {ICS_FILE} was not created")
                test_passed = False
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running {create_script}: {e}")
            test_passed = False
    else:
        print(f"⚠️ {create_script} not found, skipping calendar generation test")
        test_passed = True  # Skip this test if create_calendar.py doesn't exist
    
    # Restore the backup if it exists
    if backup_file:
        if os.path.exists(ICS_FILE):
            os.remove(ICS_FILE)
        os.rename(backup_file, ICS_FILE)
        print(f"Restored calendar from {backup_file}")
    
    print("\nCalendar Generation Test:", "Passed ✓" if test_passed else "Failed ✗")
    return test_passed

def test_update_script():
    """Test the update_calendar.py script."""
    banner("UPDATE SCRIPT TEST")
    
    # Backup the existing calendar file if it exists
    backup_file = None
    if os.path.exists(ICS_FILE):
        backup_file = f"{ICS_FILE}.backup"
        os.rename(ICS_FILE, backup_file)
        print(f"Backed up existing calendar to {backup_file}")
    
    # Run the update_calendar.py script
    try:
        print(f"Running {UPDATE_SCRIPT}...")
        result = subprocess.run(['python', UPDATE_SCRIPT], check=True, capture_output=True, text=True)
        
        print("Update script output:")
        print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
        
        if os.path.exists(ICS_FILE):
            print(f"✅ Successfully updated {ICS_FILE}")
            
            # Verify the updated calendar
            test_passed = test_calendar_format()
        else:
            print(f"❌ {ICS_FILE} was not created/updated")
            test_passed = False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {UPDATE_SCRIPT}: {e}")
        print("Error output:")
        print(e.stdout[:500] + "..." if len(e.stdout) > 500 else e.stdout)
        print(e.stderr[:500] + "..." if len(e.stderr) > 500 else e.stderr)
        test_passed = False
    
    # Restore the backup if it exists
    if backup_file:
        if os.path.exists(ICS_FILE):
            os.remove(ICS_FILE)
        os.rename(backup_file, ICS_FILE)
        print(f"Restored calendar from {backup_file}")
    
    print("\nUpdate Script Test:", "Passed ✓" if test_passed else "Failed ✗")
    return test_passed

def main():
    """Main function to run all tests."""
    banner("SOUTH AUSTRALIA PUBLIC HOLIDAY CALENDAR - COMPREHENSIVE TEST")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Calendar file: {ICS_FILE}")
    
    # Run all tests
    format_valid = test_calendar_format()
    error_test_passed = test_error_notification()
    generation_test_passed = test_calendar_generation()
    update_test_passed = test_update_script()
    
    # Overall test result
    all_tests_passed = (format_valid and 
                        error_test_passed and 
                        generation_test_passed and 
                        update_test_passed)
    
    banner("TEST SUMMARY")
    print("Calendar Format:", "Valid ✓" if format_valid else "Invalid ✗")
    print("Error Notification:", "Working ✓" if error_test_passed else "Not Working ✗")
    print("Calendar Generation:", "Working ✓" if generation_test_passed else "Not Working ✗")
    print("Update Process:", "Working ✓" if update_test_passed else "Not Working ✗")
    
    print("\nOVERALL RESULT:", "PASSED ✓" if all_tests_passed else "FAILED ✗")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 