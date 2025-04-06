#!/usr/bin/env python3
import re
from collections import defaultdict, Counter

def count_events_by_type_and_year():
    with open('Public-Holiday-Calendar-SA.ics', 'r') as f:
        content = f.read()
    
    # Extract all events
    events = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL)
    
    # Initialize counters
    total_events = len(events)
    events_by_year = defaultdict(Counter)
    event_categories = Counter()
    
    for event in events:
        # Get date (DTSTART)
        date_match = re.search(r'DTSTART;VALUE=DATE:(\d{8})', event)
        if date_match:
            date_str = date_match.group(1)
            year = date_str[:4]
            
            # Get category
            category_match = re.search(r'CATEGORIES:(.*?)(?:\r\n|\r|\n)', event)
            if category_match:
                category = category_match.group(1).strip()
            else:
                category = "Unknown"
                
            # Get summary
            summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
            summary = summary_match.group(1).strip() if summary_match else "Unknown"
            
            # Count by year and category
            events_by_year[year][category] += 1
            event_categories[category] += 1
    
    # Print results
    print(f"Total events in calendar: {total_events}")
    print("\nEvents by category:")
    for category, count in event_categories.most_common():
        print(f"  {category}: {count}")
    
    print("\nEvents by year and category:")
    for year in sorted(events_by_year.keys()):
        print(f"\n{year}:")
        for category, count in events_by_year[year].most_common():
            print(f"  {category}: {count}")
    
    # Print sample events for each category
    print("\nSample events by category:")
    samples = defaultdict(list)
    for event in events[:20]:  # Limit to first 20 events for sampling
        category_match = re.search(r'CATEGORIES:(.*?)(?:\r\n|\r|\n)', event)
        if category_match:
            category = category_match.group(1).strip()
            summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
            if summary_match:
                summary = summary_match.group(1).strip()
                samples[category].append(summary)
    
    for category, summaries in samples.items():
        print(f"\n{category} samples:")
        for summary in summaries[:3]:  # Show up to 3 samples per category
            print(f"  - {summary}")

if __name__ == "__main__":
    count_events_by_type_and_year() 