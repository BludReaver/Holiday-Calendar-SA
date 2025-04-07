#!/usr/bin/env python3
import os
import sys
import importlib.util
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Lists to track test results
errors = []
warnings = []
successes = []

def add_error(message: str) -> None:
    """Add an error message to the errors list and print it"""
    errors.append(message)
    print(f"ERROR: {message}")

def add_warning(message: str) -> None:
    """Add a warning message to the warnings list and print it"""
    warnings.append(message)
    print(f"WARNING: {message}")

def add_success(message: str) -> None:
    """Add a success message to the successes list and print it"""
    successes.append(message)
    print(f"SUCCESS: {message}")

print("COMPREHENSIVE TESTING OF SA HOLIDAY CALENDAR UPDATER")
print("="*80)

# Try to load the script
script_module = None
script_path = "update_sa_holidays.py"

def load_script() -> None:
    """Load the update_sa_holidays.py script as a module"""
    global script_module
    
    if not os.path.exists(script_path):
        add_error("Script file {script_path} not found")
        return
    
    try:
        # Load the script as a module
        spec = importlib.util.spec_from_file_location("update_sa_holidays", script_path)
        script_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script_module)
        add_success("Successfully loaded update_sa_holidays.py")
    except Exception as e:
        add_error(f"Failed to load script: {e}")

# Test required imports
def test_required_imports() -> None:
    """Test that all required modules are available"""
    required_modules = [
        "typing",
        "os",
        "sys",
        "datetime",
        "requests",
        "json",
        "uuid",
        "re",
        "bs4.BeautifulSoup"
    ]
    
    try:
        import typing
        import os
        import sys
        import datetime
        import requests
        import json
        import uuid
        import re
        import bs4
        from bs4 import BeautifulSoup
        import httpx  # For Pushover notifications
        
        for module_name in required_modules:
            if "." in module_name:
                module_parts = module_name.split(".")
                base_module = importlib.import_module(module_parts[0])
                attr = getattr(base_module, module_parts[1])
            else:
                importlib.import_module(module_name)
        add_success("All required modules are available")
    except ImportError as e:
        add_error(f"Missing required module: {e}")

# Test requirements.txt
def test_requirements() -> None:
    """Test that requirements.txt exists and contains all necessary dependencies"""
    if not os.path.exists("requirements.txt"):
        add_error("requirements.txt file not found")
        return
    
    with open("requirements.txt", "r") as f:
        requirements = f.read()
    
    # Check for required packages
    required_packages = ["requests", "httpx", "beautifulsoup4"]
    missing_packages = []
    
    for package in required_packages:
        if package not in requirements:
            missing_packages.append(package)
    
    if missing_packages:
        add_error(f"Missing dependencies in requirements.txt: {', '.join(missing_packages)}")
    else:
        add_success("All necessary dependencies found in requirements.txt")

# Test GitHub workflow
def test_github_workflow() -> None:
    """Test that the GitHub workflow is correctly configured"""
    workflow_path = ".github/workflows/update-calendar.yml"
    
    if not os.path.exists(workflow_path):
        add_error(f"GitHub workflow file {workflow_path} not found")
        return
    
    with open(workflow_path, "r") as f:
        workflow = f.read()
    
    # Check for cron schedule (quarterly)
    if "cron" in workflow and ("0 0 1 */3 *" in workflow or "quarterly" in workflow.lower()):
        add_success("GitHub workflow contains a quarterly cron schedule")
    else:
        add_warning("GitHub workflow might not be set to run quarterly")
    
    # Check for environment variables
    env_vars = [
        "PUSHOVER_API_TOKEN",
        "PUSHOVER_USER_KEY",
        "TEST_MODE",
        "ERROR_SIMULATION"
    ]
    
    missing_vars = []
    for var in env_vars:
        if var not in workflow:
            missing_vars.append(var)
    
    if missing_vars:
        add_warning(f"Missing environment variables in GitHub workflow: {', '.join(missing_vars)}")
    else:
        add_success("All necessary environment variables found in GitHub workflow")

# Test notification functions
def test_notification_functions() -> None:
    """Test that the notification functions exist and work correctly"""
    if not script_module:
        add_error("Cannot test notification functions: script not loaded")
        return
    
    # Check if the functions exist
    if not hasattr(script_module, "send_success_notification"):
        add_error("send_success_notification function not found")
    else:
        add_success("send_success_notification function exists")
    
    if not hasattr(script_module, "send_failure_notification"):
        add_error("send_failure_notification function not found")
    else:
        add_success("send_failure_notification function exists")

# Test holiday periods
def test_holiday_periods() -> None:
    """Test generating holiday periods between terms"""
    if not script_module:
        add_error("Cannot test holiday periods: script not loaded")
        return
    
    if not hasattr(script_module, "generate_holiday_periods"):
        add_error("generate_holiday_periods function not found")
        return
    
    # Create sample terms
    terms = [
        {
            "summary": "Term 1",
            "start": datetime(2023, 1, 30),
            "end": datetime(2023, 4, 14)
        },
        {
            "summary": "Term 2",
            "start": datetime(2023, 5, 1),
            "end": datetime(2023, 7, 7)
        },
        {
            "summary": "Term 3",
            "start": datetime(2023, 7, 24),
            "end": datetime(2023, 9, 29)
        },
        {
            "summary": "Term 4",
            "start": datetime(2023, 10, 16),
            "end": datetime(2023, 12, 15)
        },
        {
            "summary": "Term 1",
            "start": datetime(2024, 1, 29),
            "end": datetime(2024, 4, 12)
        }
    ]
    
    try:
        holidays = script_module.generate_holiday_periods(terms)
        
        # Check that we have the expected number of holiday periods
        if len(holidays) != 4:  # 3 mid-year holidays + 1 end-of-year holiday
            add_warning(f"Expected 4 holiday periods, but got {len(holidays)}")
        else:
            add_success("Generated the expected number of holiday periods")
    except Exception as e:
        add_error(f"Error in generate_holiday_periods: {e}")

# Test calendar generation
def test_calendar_generation() -> None:
    """Test generating the ICS calendar files"""
    if not script_module:
        add_error("Cannot test calendar generation: script not loaded")
        return
    
    if not hasattr(script_module, "generate_school_calendar"):
        add_error("generate_school_calendar function not found")
        return
    
    # Create sample terms and holidays
    terms = [
        {
            "summary": "Term 1",
            "start": datetime(2023, 1, 30),
            "end": datetime(2023, 4, 14)
        },
        {
            "summary": "Term 2",
            "start": datetime(2023, 5, 1),
            "end": datetime(2023, 7, 7)
        }
    ]
    
    holidays = [
        {
            "summary": "School Holidays (Term 1-2)",
            "start": datetime(2023, 4, 15),
            "end": datetime(2023, 4, 30)
        }
    ]
    
    try:
        calendar = script_module.generate_school_calendar(terms, holidays)
        
        # Check that the calendar is not empty
        if not calendar:
            add_error("Generated calendar is empty")
        
        # Check that the calendar contains the expected events
        if "Term 1" not in calendar or "Term 2" not in calendar or "School Holidays" not in calendar:
            add_error("Generated calendar is missing expected events")
        else:
            add_success("Calendar generation successful")
    except Exception as e:
        add_error(f"Error in generate_school_calendar: {e}")

# Test extract term dates
def test_extract_term_dates() -> None:
    """Test extracting term dates from ICS content"""
    if not script_module:
        add_error("Cannot test term date extraction: script not loaded")
        return
    
    if not hasattr(script_module, "extract_term_dates"):
        add_error("extract_term_dates function not found")
        return
    
    # Create a sample ICS content
    ics_content = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//SA DFE//Term Calendar//EN
BEGIN:VEVENT
SUMMARY:Term 1
DTSTART;VALUE=DATE:20230130
DTEND;VALUE=DATE:20230415
END:VEVENT
BEGIN:VEVENT
SUMMARY:Term 2
DTSTART;VALUE=DATE:20230501
DTEND;VALUE=DATE:20230708
END:VEVENT
END:VCALENDAR
"""
    
    try:
        terms = script_module.extract_term_dates(ics_content)
        
        # Check that we have the expected number of terms
        if len(terms) != 2:
            add_error(f"Expected 2 terms, but got {len(terms)}")
        else:
            add_success("Term date extraction successful")
    except Exception as e:
        add_error(f"Error in extract_term_dates: {e}")

# Test the main function
def test_main() -> None:
    """Test that the main function exists"""
    if not script_module:
        add_error("Cannot test main function: script not loaded")
        return
    
    if not hasattr(script_module, "main"):
        add_error("main function not found")
        return
    
    add_success("main function exists")

# Test emoji constants defined for encoding safety
def test_emoji_constants() -> None:
    """Test that emoji constants are defined for encoding safety"""
    if not script_module:
        add_error("Cannot test emoji constants: script not loaded")
        return
    
    emoji_constants = [
        "EMOJI_CHECK",
        "EMOJI_ERROR", 
        "EMOJI_WARNING",
        "EMOJI_CALENDAR",
        "EMOJI_SEARCH",
        "EMOJI_CRYSTAL_BALL",
        "EMOJI_SUN",
        "EMOJI_PLUS",
        "EMOJI_PENCIL",
        "EMOJI_SAVE"
    ]
    
    missing_constants = []
    for const in emoji_constants:
        if not hasattr(script_module, const):
            missing_constants.append(const)
    
    if missing_constants:
        add_error(f"Missing emoji constants: {', '.join(missing_constants)}")
    else:
        add_success("All emoji constants are defined")

# Print results and exit with appropriate code
def print_results() -> None:
    """Print the results of the tests"""
    print("\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    
    print(f"\nSUCCESS: {len(successes)}")
    for i, success in enumerate(successes, 1):
        print(f"  {i}. {success}")
    
    print(f"\nWARNINGS: {len(warnings)}")
    for i, warning in enumerate(warnings, 1):
        print(f"  {i}. {warning}")
    
    print(f"\nERRORS: {len(errors)}")
    for i, error in enumerate(errors, 1):
        print(f"  {i}. {error}")
    
    print("\n" + "="*50)
    print(f"TOTAL RESULTS: {len(successes)} successes, {len(warnings)} warnings, {len(errors)} errors")
    print("="*50)
    
    # Exit with appropriate code
    if errors:
        sys.exit(1)
    else:
        sys.exit(0)

# Run the tests
if __name__ == "__main__":
    # Load the script
    load_script()
    
    # Run the tests
    test_required_imports()
    test_requirements()
    test_github_workflow()
    test_notification_functions()
    test_holiday_periods()
    test_calendar_generation()
    test_extract_term_dates()
    test_main()
    test_emoji_constants()
    
    # Print results and exit
    print_results() 