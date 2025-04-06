#!/usr/bin/env python3
import re

def fix_good_friday():
    """Fix the Good Friday category"""
    print("Fixing Good Friday categories...")
    
    # Read the current file
    with open('Public-Holiday-Calendar-SA.ics', 'r') as f:
        content = f.read()
    
    # Fix Good Friday events to be Public Holiday
    fixed_content = re.sub(
        r'SUMMARY:Good Friday\nCATEGORIES:Unknown',
        'SUMMARY:Good Friday\nCATEGORIES:Public Holiday',
        content
    )
    
    # Write the updated content
    with open('Public-Holiday-Calendar-SA.ics', 'w') as f:
        f.write(fixed_content)
    
    print("Good Friday categories fixed!")
    
    # Count the events after fix
    events = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', fixed_content, re.DOTALL)
    
    # Count categories
    public_holidays = sum(1 for event in events if "CATEGORIES:Public Holiday" in event)
    school_terms = sum(1 for event in events if "CATEGORIES:School Term" in event)
    school_holidays = sum(1 for event in events if "CATEGORIES:School Holiday" in event)
    unknown = sum(1 for event in events if "CATEGORIES:Unknown" in event)
    
    print("\nFinal Category Counts:")
    print(f"Public Holidays: {public_holidays}")
    print(f"School Terms: {school_terms}")
    print(f"School Holidays: {school_holidays}")
    print(f"Unknown: {unknown}")
    print(f"Total: {len(events)}")

if __name__ == "__main__":
    fix_good_friday() 