#!/usr/bin/env python3
"""
Test script for the update_school_terms.py utility.
This script tests that the utility correctly updates school term dates
in both create_calendar.py and update_calendar.py.
"""

import os
import sys
import re
import shutil
import subprocess
import tempfile
from datetime import datetime

# Set up temporary test environment
def setup_test_environment():
    """Create temporary copies of the calendar scripts for testing."""
    temp_dir = tempfile.mkdtemp()
    print(f"Creating temporary test environment in {temp_dir}")
    
    # Create backup copies of the scripts
    for script in ['create_calendar.py', 'update_calendar.py']:
        if os.path.exists(script):
            backup_path = os.path.join(temp_dir, script)
            shutil.copy(script, backup_path)
            print(f"Created backup of {script} at {backup_path}")
        else:
            print(f"Warning: {script} does not exist")
    
    return temp_dir

def restore_scripts(temp_dir):
    """Restore the original scripts after testing."""
    print("Restoring original scripts...")
    for script in ['create_calendar.py', 'update_calendar.py']:
        backup_path = os.path.join(temp_dir, script)
        if os.path.exists(backup_path):
            shutil.copy(backup_path, script)
            print(f"Restored {script} from backup")
    
    # Clean up temporary directory
    shutil.rmtree(temp_dir)
    print(f"Removed temporary directory {temp_dir}")

def check_term_dates_in_script(script_path, year, term_dates, special_holiday=None):
    """
    Check if the term dates were correctly updated in the script.
    
    Args:
        script_path: Path to the script to check
        year: Year to check for
        term_dates: Dictionary with term dates
        special_holiday: Optional special holiday date
    
    Returns:
        True if all dates were found, False otherwise
    """
    if not os.path.exists(script_path):
        print(f"Error: Script {script_path} does not exist")
        return False
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Check for the year entry
    year_pattern = rf"{year}\s*:\s*{{"
    if not re.search(year_pattern, content):
        print(f"Year {year} not found in {script_path}")
        return False
    
    # Check for each term date
    all_dates_found = True
    for term, date_str in term_dates.items():
        # Adjust the pattern based on the script structure
        if script_path.endswith('create_calendar.py'):
            # In create_calendar.py dates are formatted like 'term1_begin': '20280125'
            pattern = rf"[\'\"]({term})[\'\"]:\s*[\'\"]({date_str})[\'\"]"
        else:
            # In update_calendar.py dates might be formatted differently
            pattern = rf"[\'\"]({term})[\'\"]:\s*[\'\"]({date_str})[\'\"]"
        
        if not re.search(pattern, content):
            print(f"Date for {term}={date_str} not found in {script_path}")
            all_dates_found = False
    
    # Check for special holiday if provided
    if special_holiday:
        if script_path.endswith('create_calendar.py'):
            special_pattern = rf"[\'\"]special_holiday[\'\"]:\s*[\'\"]({special_holiday})[\'\"]"
        else:
            special_pattern = rf"[\'\"]special_holiday[\'\"]:\s*[\'\"]({special_holiday})[\'\"]"
        
        if not re.search(special_pattern, content):
            print(f"Special holiday {special_holiday} not found in {script_path}")
            all_dates_found = False
    
    return all_dates_found

def run_update_script(year, term_dates, special_holiday=None):
    """Run the update_school_terms.py script with the provided parameters."""
    cmd = [
        sys.executable,
        'update_school_terms.py',
        '--year', str(year),
        '--term1-begin', term_dates['term1_begin'],
        '--term1-end', term_dates['term1_end'],
        '--term2-begin', term_dates['term2_begin'],
        '--term2-end', term_dates['term2_end'],
        '--term3-begin', term_dates['term3_begin'],
        '--term3-end', term_dates['term3_end'],
        '--term4-begin', term_dates['term4_begin'],
        '--term4-end', term_dates['term4_end']
    ]
    
    if special_holiday:
        cmd.extend(['--special-holiday', special_holiday])
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Command output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print("Command output:")
        print(e.stdout)
        print("Errors:")
        print(e.stderr)
        return False

def main():
    """Main test function."""
    # Test data - using 2029 to avoid conflicts with existing data
    test_year = 2029
    test_term_dates = {
        'term1_begin': '20290129',
        'term1_end': '20290413',
        'term2_begin': '20290430',
        'term2_end': '20290706',
        'term3_begin': '20290723',
        'term3_end': '20290928',
        'term4_begin': '20291015',
        'term4_end': '20291214'
    }
    test_special_holiday = '20290607'
    
    # Setup test environment
    temp_dir = setup_test_environment()
    
    try:
        # Run the update script
        print(f"\nTesting update_school_terms.py with year {test_year}...")
        success = run_update_script(test_year, test_term_dates, test_special_holiday)
        
        if success:
            # Check if the dates were correctly updated in both scripts
            create_calendar_updated = check_term_dates_in_script(
                'create_calendar.py', test_year, test_term_dates, test_special_holiday
            )
            
            update_calendar_updated = check_term_dates_in_script(
                'update_calendar.py', test_year, test_term_dates, test_special_holiday
            )
            
            if create_calendar_updated and update_calendar_updated:
                print("\n✅ TEST PASSED: Both scripts were successfully updated with the new term dates.")
            elif create_calendar_updated:
                print("\n❌ TEST PARTIALLY PASSED: Only create_calendar.py was updated correctly.")
            elif update_calendar_updated:
                print("\n❌ TEST PARTIALLY PASSED: Only update_calendar.py was updated correctly.")
            else:
                print("\n❌ TEST FAILED: Neither script was updated correctly.")
        else:
            print("\n❌ TEST FAILED: The update_school_terms.py script returned an error.")
    
    finally:
        # Restore original scripts
        restore_scripts(temp_dir)
        print("\nTest completed. Original scripts have been restored.")

if __name__ == "__main__":
    main() 