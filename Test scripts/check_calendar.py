from icalendar import Calendar
import sys

def check_calendar():
    # Open the calendar file
    try:
        with open('Public-Holiday-Calendar-SA.ics', 'rb') as f:
            cal = Calendar.from_ical(f.read())
    except Exception as e:
        print(f"Error opening calendar file: {e}")
        sys.exit(1)

    # Get all events
    events = list(cal.walk('VEVENT'))
    print(f"Total events: {len(events)}")

    # Count categories
    categories = {
        'Public Holiday': 0,
        'School Term': 0,
        'School Holiday': 0,
        'Unknown': 0
    }

    # Check each event
    for event in events:
        summary = str(event.get('summary', ''))
        category = event.get('categories')
        
        if category:
            # Try different ways to extract the category
            cat_str = str(category)
            
            # Look for the actual category string in different formats
            if 'Public Holiday' in cat_str:
                categories['Public Holiday'] += 1
            elif 'School Term' in cat_str:
                categories['School Term'] += 1 
            elif 'School Holiday' in cat_str:
                categories['School Holiday'] += 1
            else:
                # Try to extract from the raw value
                try:
                    # Some iCalendar libraries store it differently
                    if hasattr(category, 'to_ical'):
                        raw_cat = category.to_ical().decode('utf-8')
                        if 'Public Holiday' in raw_cat:
                            categories['Public Holiday'] += 1
                            continue
                        elif 'School Term' in raw_cat:
                            categories['School Term'] += 1
                            continue
                        elif 'School Holiday' in raw_cat:
                            categories['School Holiday'] += 1
                            continue
                except Exception:
                    pass
                
                # Fallback to guessing based on event name
                if "Term" in summary and ("Begin" in summary or "End" in summary):
                    categories['School Term'] += 1
                elif "Holiday" in summary and "School" in summary:
                    categories['School Holiday'] += 1
                else:
                    # Most likely a public holiday
                    categories['Public Holiday'] += 1
                print(f"Guessed category for: {summary}")
        else:
            # No category - guess based on title
            if "Term" in summary and ("Begin" in summary or "End" in summary):
                categories['School Term'] += 1
            elif "Holiday" in summary and "School" in summary:
                categories['School Holiday'] += 1
            else:
                # Most likely a public holiday
                categories['Public Holiday'] += 1
            print(f"Missing category for event: {summary}")
    
    # Print results
    print("\nCategory distribution:")
    for cat, count in categories.items():
        print(f" - {cat}: {count}")

    # Check for events with brackets
    brackets = ['(', ')', '[', ']', '{', '}', '<', '>']
    bracket_events = []
    
    for event in events:
        summary = str(event.get('summary', ''))
        if any(b in summary for b in brackets):
            bracket_events.append(summary)
    
    if bracket_events:
        print(f"\nFound {len(bracket_events)} events with brackets:")
        for e in bracket_events[:5]:
            print(f" - {e}")
        if len(bracket_events) > 5:
            print(f" ... and {len(bracket_events) - 5} more")
    else:
        print("\nNo events with brackets found")
    
    # Check for all-day events
    non_all_day = []
    for event in events:
        summary = str(event.get('summary', ''))
        dtstart = event.get('dtstart')
        if dtstart and hasattr(dtstart, 'dt'):
            if hasattr(dtstart.dt, 'hour'):  # Datetime (not all-day)
                non_all_day.append(summary)
    
    if non_all_day:
        print(f"\nFound {len(non_all_day)} non-all-day events:")
        for e in non_all_day[:5]:
            print(f" - {e}")
        if len(non_all_day) > 5:
            print(f" ... and {len(non_all_day) - 5} more")
    else:
        print("\nAll events are all-day events")

if __name__ == "__main__":
    check_calendar() 