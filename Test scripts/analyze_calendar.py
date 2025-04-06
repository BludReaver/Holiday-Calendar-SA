import icalendar
from datetime import datetime

# Open and read the calendar file
with open('Public-Holiday-Calendar-SA.ics', 'rb') as f:
    cal = icalendar.Calendar.from_ical(f.read())

# Open a file for writing the results
with open('calendar_analysis.txt', 'w') as output_file:
    # Initialize counters
    public_holidays = 0
    school_terms = 0
    school_holidays = 0
    total_events = 0

    # Yearly counters
    events_by_year = {
        "2025": {"public": 0, "school_term": 0, "school_holiday": 0},
        "2026": {"public": 0, "school_term": 0, "school_holiday": 0},
        "2027": {"public": 0, "school_term": 0, "school_holiday": 0},
        "other": {"public": 0, "school_term": 0, "school_holiday": 0}
    }

    # Extract and count events by category and year
    output_file.write("PUBLIC HOLIDAYS BY YEAR:\n")
    for component in cal.walk():
        if component.name == 'VEVENT':
            total_events += 1
            
            # Get the start date
            start_date = None
            if 'DTSTART' in component:
                dt_value = component['DTSTART'].dt
                if isinstance(dt_value, datetime):
                    start_date = dt_value.strftime("%Y%m%d")
                else:  # date
                    start_date = dt_value.strftime("%Y%m%d")
            
            # Determine year
            year = "other"
            if start_date:
                if start_date.startswith("2025"):
                    year = "2025"
                elif start_date.startswith("2026"):
                    year = "2026"
                elif start_date.startswith("2027"):
                    year = "2027"
            
            # Get the category value
            if 'CATEGORIES' in component:
                category_obj = component['CATEGORIES']
                category_value = category_obj.to_ical().decode('utf-8') if hasattr(category_obj, 'to_ical') else str(category_obj)
                
                if 'Public Holiday' in category_value:
                    public_holidays += 1
                    events_by_year[year]["public"] += 1
                    
                    # Print details of public holidays
                    summary = component.get('SUMMARY', 'No summary')
                    output_file.write(f"{year} - Public Holiday: {summary} ({start_date})\n")
                    
                elif 'School Term' in category_value:
                    school_terms += 1
                    events_by_year[year]["school_term"] += 1
                elif 'School Holiday' in category_value:
                    school_holidays += 1
                    events_by_year[year]["school_holiday"] += 1

    # Print results
    output_file.write(f"\nSUMMARY:\n")
    output_file.write(f"Total events: {total_events}\n")
    output_file.write(f"Public Holidays: {public_holidays}\n")
    output_file.write(f"School Terms: {school_terms}\n")
    output_file.write(f"School Holidays: {school_holidays}\n")

    # Print events by year
    output_file.write("\nEVENTS BY YEAR:\n")
    for year, counts in events_by_year.items():
        total_year = sum(counts.values())
        if total_year > 0:
            output_file.write(f"  {year}:\n")
            output_file.write(f"    Public Holidays: {counts['public']}\n")
            output_file.write(f"    School Terms: {counts['school_term']}\n")
            output_file.write(f"    School Holidays: {counts['school_holiday']}\n")
            output_file.write(f"    Total: {total_year}\n")

print("Analysis complete. Results written to calendar_analysis.txt") 