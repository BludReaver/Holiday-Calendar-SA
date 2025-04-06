#!/usr/bin/env python3
"""
Utility script to update school term dates in both create_calendar.py and update_calendar.py
This ensures that both scripts have consistent and up-to-date term data.
"""

import re
import os
import sys
from datetime import datetime
import argparse

def parse_arguments():
    """Parse command-line arguments for updating school term dates"""
    parser = argparse.ArgumentParser(description='Update school term dates in calendar scripts')
    parser.add_argument('--year', type=int, required=True, help='Year to update (e.g., 2025)')
    parser.add_argument('--term1-begin', type=str, help='Term 1 begin date (YYYYMMDD)')
    parser.add_argument('--term1-end', type=str, help='Term 1 end date (YYYYMMDD)')
    parser.add_argument('--term2-begin', type=str, help='Term 2 begin date (YYYYMMDD)')
    parser.add_argument('--term2-end', type=str, help='Term 2 end date (YYYYMMDD)')
    parser.add_argument('--term3-begin', type=str, help='Term 3 begin date (YYYYMMDD)')
    parser.add_argument('--term3-end', type=str, help='Term 3 end date (YYYYMMDD)')
    parser.add_argument('--term4-begin', type=str, help='Term 4 begin date (YYYYMMDD)')
    parser.add_argument('--term4-end', type=str, help='Term 4 end date (YYYYMMDD)')
    parser.add_argument('--special-holiday', type=str, help='Special holiday date (YYYYMMDD)')
    
    # Parse arguments
    return parser.parse_args()

def validate_date_format(date_str):
    """Validate that a date string is in YYYYMMDD format"""
    if not date_str:
        return False
    
    try:
        # Try to parse the date
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False

def update_create_calendar_script(year, term_dates, special_holiday=None):
    """Update the create_calendar.py script with new term dates"""
    print(f"Updating create_calendar.py with {year} term dates...")
    
    # Read the current script
    with open('create_calendar.py', 'r') as f:
        content = f.read()
    
    # Find the section for the specified year
    year_pattern = f"# {year} School Terms and Holidays"
    year_section_match = re.search(f"{year_pattern}.*?# [0-9]{{4}} School Terms", content, re.DOTALL)
    
    # If not found, look for the end of the array
    if not year_section_match:
        year_section_match = re.search(f"{year_pattern}.*?]", content, re.DOTALL)
    
    if year_section_match:
        # Extract the section
        year_section = year_section_match.group(0)
        
        # Create the replacement section
        replacement = f"# {year} School Terms and Holidays\n"
        replacement += f"        ('{term_dates['term1_begin']}', \"Term 1 Begins\", \"School Term\"),\n"
        replacement += f"        ('{term_dates['term1_end']}', \"Term 1 Ends\", \"School Term\"),\n"
        replacement += f"        ('{next_day(term_dates['term1_end'])}', \"School Holidays - Term 1\", \"School Holiday\"),\n"
        replacement += f"        ('{prev_day(term_dates['term2_begin'])}', \"School Holidays - Term 1\", \"School Holiday\"),\n"
        replacement += f"        ('{term_dates['term2_begin']}', \"Term 2 Begins\", \"School Term\"),\n"
        
        # Add special holiday if provided
        if special_holiday:
            replacement += f"        ('{special_holiday}', \"School Holidays - Additional Term 2\", \"School Holiday\"),\n"
        
        replacement += f"        ('{term_dates['term2_end']}', \"Term 2 Ends\", \"School Term\"),\n"
        replacement += f"        ('{next_day(term_dates['term2_end'])}', \"School Holidays - Term 2\", \"School Holiday\"),\n"
        replacement += f"        ('{prev_day(term_dates['term3_begin'])}', \"School Holidays - Term 2\", \"School Holiday\"),\n"
        replacement += f"        ('{term_dates['term3_begin']}', \"Term 3 Begins\", \"School Term\"),\n"
        replacement += f"        ('{term_dates['term3_end']}', \"Term 3 Ends\", \"School Term\"),\n"
        replacement += f"        ('{next_day(term_dates['term3_end'])}', \"School Holidays - Term 3\", \"School Holiday\"),\n"
        replacement += f"        ('{prev_day(term_dates['term4_begin'])}', \"School Holidays - Term 3\", \"School Holiday\"),\n"
        replacement += f"        ('{term_dates['term4_begin']}', \"Term 4 Begins\", \"School Term\"),\n"
        replacement += f"        ('{term_dates['term4_end']}', \"Term 4 Ends\", \"School Term\"),\n"
        replacement += f"        ('{next_day(term_dates['term4_end'])}', \"School Holidays - Term 4\", \"School Holiday\"),\n"
        
        # Check if this is the last section in the array
        if year_section.endswith("]"):
            # This is the last section
            replacement = replacement[:-2]  # Remove the last comma and newline
            replacement += "\n    ]"
        else:
            # Find the next year section and add it
            next_year_pattern = "# [0-9]{4} School Terms"
            next_year_match = re.search(next_year_pattern, year_section)
            if next_year_match:
                next_year_section = next_year_match.group(0)
                replacement += f"        {next_year_section}"
            else:
                # Something went wrong
                print(f"Error: Could not find the next year section after {year}")
                return False
        
        # Replace the section in the content
        updated_content = content.replace(year_section, replacement)
        
        # Write the updated content
        with open('create_calendar.py', 'w') as f:
            f.write(updated_content)
        
        print(f"Successfully updated create_calendar.py with {year} term dates")
        return True
    else:
        # Year section not found, need to add a new one
        print(f"Could not find section for {year} in create_calendar.py. Please add it manually.")
        return False

def update_update_calendar_script(year, term_dates, special_holiday=None):
    """Update the update_calendar.py script with new term dates"""
    print(f"Updating update_calendar.py with {year} term dates...")
    
    # Read the current script
    with open('update_calendar.py', 'r') as f:
        content = f.read()
    
    # Find the school_term_dates dictionary
    dict_pattern = r"school_term_dates\s*=\s*\{.*?\}"
    dict_match = re.search(dict_pattern, content, re.DOTALL)
    
    if dict_match:
        dict_content = dict_match.group(0)
        
        # Check if the year is already in the dictionary
        year_pattern = rf"{year}:\s*\[.*?\]"
        year_match = re.search(year_pattern, dict_content, re.DOTALL)
        
        if year_match:
            # Year exists, replace it
            year_content = year_match.group(0)
            replacement = f"{year}: [\n"
            replacement += f"                    (\"{term_dates['term1_begin']}\", \"{term_dates['term1_end']}\", 1),  # Term 1 {year}\n"
            replacement += f"                    (\"{term_dates['term2_begin']}\", \"{term_dates['term2_end']}\", 2),  # Term 2 {year}\n"
            replacement += f"                    (\"{term_dates['term3_begin']}\", \"{term_dates['term3_end']}\", 3),  # Term 3 {year}\n"
            replacement += f"                    (\"{term_dates['term4_begin']}\", \"{term_dates['term4_end']}\", 4),  # Term 4 {year}\n"
            replacement += "                ]"
            
            # Replace the year section
            updated_dict_content = dict_content.replace(year_content, replacement)
        else:
            # Year doesn't exist, add it to the dictionary
            # Find the closing brace of the dictionary
            close_brace_pos = dict_content.rfind("}")
            
            if close_brace_pos != -1:
                replacement = f"{year}: [\n"
                replacement += f"                    (\"{term_dates['term1_begin']}\", \"{term_dates['term1_end']}\", 1),  # Term 1 {year}\n"
                replacement += f"                    (\"{term_dates['term2_begin']}\", \"{term_dates['term2_end']}\", 2),  # Term 2 {year}\n"
                replacement += f"                    (\"{term_dates['term3_begin']}\", \"{term_dates['term3_end']}\", 3),  # Term 3 {year}\n"
                replacement += f"                    (\"{term_dates['term4_begin']}\", \"{term_dates['term4_end']}\", 4),  # Term 4 {year}\n"
                replacement += "                ],\n"
                
                # Insert the new year before the closing brace
                updated_dict_content = dict_content[:close_brace_pos] + replacement + dict_content[close_brace_pos:]
            else:
                print("Error: Could not find the closing brace of the dictionary")
                return False
        
        # Replace the dictionary in the content
        updated_content = content.replace(dict_content, updated_dict_content)
        
        # Check for special case for 2025
        if year == 2025 and special_holiday:
            # Find the special case section for 2025
            special_case_pattern = r"# Special case: Add June long weekend holiday for 2025.*?log\.write\(f\"Added Additional Term 2.*?\n"
            special_case_match = re.search(special_case_pattern, content, re.DOTALL)
            
            if special_case_match:
                special_case_content = special_case_match.group(0)
                
                # Create the replacement with the new date
                replacement = f"# Special case: Add June long weekend holiday for 2025\n"
                replacement += f"                if year == 2025:\n"
                replacement += f"                    june_holiday_date = datetime.strptime(\"{special_holiday}\", '%Y%m%d').date()\n"
                replacement += "                    june_holiday_event = Event()\n"
                replacement += "                    june_holiday_event.name = \"School Holidays - Additional Term 2\"\n"
                replacement += "                    june_holiday_event.begin = pytz.timezone(TIMEZONE).localize(datetime.combine(june_holiday_date, datetime.min.time()))\n"
                replacement += "                    june_holiday_event.make_all_day()\n"
                replacement += "                    june_holiday_event.end = pytz.timezone(TIMEZONE).localize(datetime.combine(june_holiday_date + timedelta(days=1), datetime.min.time()))\n"
                replacement += "                    june_holiday_event.transparent = True\n"
                replacement += "                    june_holiday_event.categories = [\"School Holiday\"]\n"
                replacement += f"                    june_holiday_event.uid = f\"{special_holiday}-schoolholidayAdditional2@southaustralia.education\"\n"
                replacement += "                    cal.events.add(june_holiday_event)\n"
                replacement += "                    log.write(f\"Added Additional Term 2 Holiday event: {june_holiday_date}\\n\")\n"
                
                # Replace the special case section
                updated_content = updated_content.replace(special_case_content, replacement)
        
        # Write the updated content
        with open('update_calendar.py', 'w') as f:
            f.write(updated_content)
        
        print(f"Successfully updated update_calendar.py with {year} term dates")
        return True
    else:
        print("Error: Could not find school_term_dates dictionary in update_calendar.py")
        return False

def next_day(date_str):
    """Get the next day in YYYYMMDD format"""
    date = datetime.strptime(date_str, '%Y%m%d')
    next_day = date.replace(day=date.day + 1)
    return next_day.strftime('%Y%m%d')

def prev_day(date_str):
    """Get the previous day in YYYYMMDD format"""
    date = datetime.strptime(date_str, '%Y%m%d')
    prev_day = date.replace(day=date.day - 1)
    return prev_day.strftime('%Y%m%d')

def main():
    """Main function to update school term dates"""
    args = parse_arguments()
    
    # Validate year
    year = args.year
    if year < 2024 or year > 2100:
        print(f"Error: Year {year} is out of range (2024-2100)")
        return False
    
    # Validate term dates
    term_dates = {
        'term1_begin': args.term1_begin,
        'term1_end': args.term1_end,
        'term2_begin': args.term2_begin,
        'term2_end': args.term2_end,
        'term3_begin': args.term3_begin,
        'term3_end': args.term3_end,
        'term4_begin': args.term4_begin,
        'term4_end': args.term4_end
    }
    
    # Check if all term dates are provided
    missing_dates = [name for name, value in term_dates.items() if not value]
    if missing_dates:
        print(f"Error: Missing term dates: {', '.join(missing_dates)}")
        return False
    
    # Validate date formats
    invalid_dates = [name for name, value in term_dates.items() if not validate_date_format(value)]
    if invalid_dates:
        print(f"Error: Invalid date format for: {', '.join(invalid_dates)}")
        print("Dates must be in YYYYMMDD format (e.g., 20250128)")
        return False
    
    # Validate special holiday date if provided
    special_holiday = args.special_holiday
    if special_holiday and not validate_date_format(special_holiday):
        print(f"Error: Invalid date format for special holiday: {special_holiday}")
        print("Date must be in YYYYMMDD format (e.g., 20250601)")
        return False
    
    # Update the scripts
    success1 = update_create_calendar_script(year, term_dates, special_holiday)
    success2 = update_update_calendar_script(year, term_dates, special_holiday)
    
    if success1 and success2:
        print(f"Successfully updated both scripts with {year} term dates")
        return True
    else:
        print(f"Error: Failed to update one or both scripts with {year} term dates")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 