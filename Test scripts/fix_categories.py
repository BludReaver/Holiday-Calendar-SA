#!/usr/bin/env python3
import re

def fix_categories():
    """Fix the category format in the iCalendar file"""
    print("Fixing categories in the iCalendar file...")
    
    # Read the current file
    with open('Public-Holiday-Calendar-SA.ics', 'r') as f:
        content = f.read()
    
    # Replace complex category format with simple text
    # Pattern: Find the categories line followed by any non-newline characters
    content = re.sub(r'CATEGORIES:.*?(?=\n)', 
                    lambda m: fix_category_line(m.group(0)), 
                    content)
    
    # Write the updated content
    with open('Public-Holiday-Calendar-SA.ics', 'w') as f:
        f.write(content)
    
    print("Categories fixed successfully!")

def fix_category_line(line):
    """Map a complex category line to a simple text category"""
    if "public holiday" in line.lower():
        return "CATEGORIES:Public Holiday"
    elif "school term" in line.lower() or "term begins" in line.lower() or "term ends" in line.lower():
        return "CATEGORIES:School Term"
    elif "school holiday" in line.lower():
        return "CATEGORIES:School Holiday"
    else:
        print(f"Warning: Unknown category line: {line}")
        return line

if __name__ == "__main__":
    fix_categories() 