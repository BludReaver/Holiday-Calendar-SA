#!/usr/bin/env python3
import icalendar
from collections import Counter, defaultdict

def check_categories():
    """Check event categories and ensure they are consistent"""
    print("Checking event categories in calendar file...")
    
    # Read the calendar file
    with open('Public-Holiday-Calendar-SA.ics', 'rb') as f:
        cal = icalendar.Calendar.from_ical(f.read())
    
    # Track categories
    categories_counter = Counter()
    events_by_category = defaultdict(list)
    categorized_events = 0
    uncategorized_events = 0
    
    # Expected categories
    expected_categories = {"Public Holiday", "School Term", "School Holiday"}
    
    # Process each event
    for component in cal.walk():
        if component.name == 'VEVENT':
            summary = str(component.get('SUMMARY', ''))
            
            # Extract category
            category = None
            if 'CATEGORIES' in component:
                try:
                    # Try to extract as a string
                    category_data = component.get('CATEGORIES')
                    if isinstance(category_data, icalendar.prop.vCategory):
                        category = str(category_data).replace('CATEGORIES:', '').strip()
                    else:
                        category = category_data.decode('utf-8') if hasattr(category_data, 'decode') else str(category_data)
                except Exception as e:
                    print(f"Error extracting category from {summary}: {e}")
            
            if category:
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
        print(f"\n{category} (showing 3 of {len(events)}):")
        for event in events[:3]:
            print(f"  - {event}")
    
    print("\nCategory check completed.")

if __name__ == "__main__":
    check_categories() 