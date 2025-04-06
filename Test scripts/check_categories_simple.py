#!/usr/bin/env python3
import re
from collections import Counter, defaultdict

def check_categories_simple():
    """Check event categories using regex directly"""
    print("Checking event categories in calendar file...")
    
    # Read the calendar file
    with open('Public-Holiday-Calendar-SA.ics', 'r') as f:
        content = f.read()
    
    # Extract all events
    events = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL)
    
    # Initialize counters
    categories_counter = Counter()
    events_by_category = defaultdict(list)
    categorized_events = 0
    uncategorized_events = 0
    
    # Expected categories
    expected_categories = {"Public Holiday", "School Term", "School Holiday"}
    
    # Process each event
    for event in events:
        # Get the summary
        summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
        summary = summary_match.group(1).strip() if summary_match else "Unknown"
        
        # Get the category
        category_match = re.search(r'CATEGORIES:(.*?)(?:\r\n|\r|\n)', event)
        if category_match:
            category = category_match.group(1).strip()
            categorized_events += 1
            categories_counter[category] += 1
            events_by_category[category].append(summary)
        else:
            uncategorized_events += 1
            print(f"Warning: Event without category: {summary}")
    
    # Print category statistics
    print("\nCategory Statistics:")
    print(f"Total events: {categorized_events + uncategorized_events}")
    print(f"Categorized events: {categorized_events}")
    print(f"Uncategorized events: {uncategorized_events}")
    
    print("\nCategories found:")
    for category, count in categories_counter.most_common():
        print(f"  {category}: {count} events")
        
    # Check if all expected categories are present
    missing_categories = expected_categories - set(categories_counter.keys())
    if missing_categories:
        print(f"\nWarning: Missing expected categories: {', '.join(missing_categories)}")
    else:
        print("\nAll expected categories are present ✓")
    
    # Check for unexpected categories
    unexpected_categories = set(categories_counter.keys()) - expected_categories
    if unexpected_categories:
        print(f"\nWarning: Unexpected categories found: {', '.join(unexpected_categories)}")
    else:
        print("No unexpected categories found ✓")
    
    # Print sample events for each category
    print("\nSample events by category:")
    for category, events in events_by_category.items():
        print(f"\n{category} (showing up to 3 of {len(events)}):")
        for event in events[:3]:
            print(f"  - {event}")
    
    print("\nCategory check completed.")

if __name__ == "__main__":
    check_categories_simple() 