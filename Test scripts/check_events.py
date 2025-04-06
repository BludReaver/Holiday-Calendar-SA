from icalendar import Calendar
import sys

def check_events():
    try:
        with open('Public-Holiday-Calendar-SA.ics', 'rb') as f:
            cal = Calendar.from_ical(f.read())
    except Exception as e:
        print(f"Error opening calendar file: {e}")
        sys.exit(1)

    events = list(cal.walk('VEVENT'))
    print(f"Total events: {len(events)}\n")
    
    # Count events by year
    years = {}
    for event in events:
        dtstart = event.get('dtstart')
        if dtstart:
            year = dtstart.dt.year
            if year not in years:
                years[year] = {"total": 0, "categories": {}}
            
            years[year]["total"] += 1
            
            # Count by category
            summary = str(event.get('summary', ''))
            categories_field = event.get('categories')
            
            if categories_field:
                cat_str = str(categories_field)
                if 'Public Holiday' in cat_str:
                    cat = 'Public Holiday'
                elif 'School Term' in cat_str:
                    cat = 'School Term'
                elif 'School Holiday' in cat_str:
                    cat = 'School Holiday'
                else:
                    # Determine category from summary
                    if "Term" in summary and ("Begin" in summary or "End" in summary):
                        cat = 'School Term'
                    elif "Holiday" in summary and "School" in summary:
                        cat = 'School Holiday'
                    else:
                        cat = 'Public Holiday'  # Default for holidays
            else:
                # No category field, determine from summary
                if "Term" in summary and ("Begin" in summary or "End" in summary):
                    cat = 'School Term'
                elif "Holiday" in summary and "School" in summary:
                    cat = 'School Holiday'
                else:
                    cat = 'Public Holiday'  # Default for holidays
                
            if cat not in years[year]["categories"]:
                years[year]["categories"][cat] = 0
            years[year]["categories"][cat] += 1
    
    # Print events by year
    print("Events by year:")
    for year in sorted(years.keys()):
        print(f"\n{year}: {years[year]['total']} events")
        for cat, count in years[year]["categories"].items():
            print(f"  - {cat}: {count}")
    
    # Check for specific important holidays
    important_holidays = {
        "New Year's Day": False,
        "Australia Day": False,
        "Adelaide Cup Day": False,
        "Good Friday": False,
        "Easter Saturday": False,
        "Easter Sunday": False,
        "Easter Monday": False,
        "Anzac Day": False,
        "King's Birthday": False,
        "Labour Day": False,
        "Christmas Eve": False,
        "Christmas Day": False,
        "Proclamation Day": False,
        "New Year's Eve": False
    }
    
    for event in events:
        summary = str(event.get('summary', ''))
        for holiday in important_holidays:
            if holiday in summary or holiday.replace("'s", "") in summary or holiday.replace("'", "") in summary:
                important_holidays[holiday] = True
    
    print("\nVerifying important holidays:")
    all_present = True
    for holiday, present in important_holidays.items():
        status = "✓" if present else "✗"
        print(f"  {status} {holiday}")
        if not present:
            all_present = False
    
    if all_present:
        print("\n✅ All important holidays are present")
    else:
        print("\n❌ Some important holidays are missing")
        
    # Check the first 10 events
    print("\nFirst 10 events:")
    for i, event in enumerate(events[:10]):
        summary = event.get('summary', 'No summary')
        dtstart = event.get('dtstart', 'No start date')
        
        # Extract category more reliably
        cat_str = str(event.get('categories', 'No category'))
        
        # Determine category from both fields and name
        if 'Public Holiday' in cat_str:
            category = 'Public Holiday'
        elif 'School Term' in cat_str:
            category = 'School Term'
        elif 'School Holiday' in cat_str:
            category = 'School Holiday'
        else:
            # Determine category from summary
            if "Term" in summary and ("Begin" in summary or "End" in summary):
                category = 'School Term'
            elif "Holiday" in summary and "School" in summary:
                category = 'School Holiday'
            else:
                category = 'Public Holiday'  # Default for holidays
            
        print(f"{i+1}. {summary} - Start: {dtstart.dt if hasattr(dtstart, 'dt') else 'Unknown'}, Category: {category}")

if __name__ == "__main__":
    check_events() 