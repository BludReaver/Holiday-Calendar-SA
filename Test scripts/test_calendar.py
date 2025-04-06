import icalendar
import re
from datetime import datetime, timedelta
import os

def validate_calendar(calendar_file):
    print(f"Validating calendar file: {calendar_file}")
    results = []
    
    try:
        with open(calendar_file, 'rb') as f:
            cal = icalendar.Calendar.from_ical(f.read())
            
        # Check basic calendar properties
        results.append(("Calendar Version", cal.get('version', 'Missing')))
        results.append(("Calendar Name", cal.get('X-WR-CALNAME', 'Missing')))
        results.append(("Calendar Description", cal.get('X-WR-CALDESC', 'Missing')))
        results.append(("Calendar Timezone", cal.get('X-WR-TIMEZONE', 'Missing')))
        
        # Count events
        events = [e for e in cal.walk() if e.name == 'VEVENT']
        results.append(("Total Events", len(events)))
        
        # Check event types
        public_holidays = 0
        school_terms = 0
        school_holidays = 0
        other_events = 0
        
        # Check for formatting issues
        formatting_issues = []
        bracket_issues = []
        full_day_issues = []
        
        # Count events by year
        events_by_year = {
            "2025": {"public": 0, "school_term": 0, "school_holiday": 0, "other": 0},
            "2026": {"public": 0, "school_term": 0, "school_holiday": 0, "other": 0},
            "2027": {"public": 0, "school_term": 0, "school_holiday": 0, "other": 0},
            "other": {"public": 0, "school_term": 0, "school_holiday": 0, "other": 0}
        }
        
        for event in events:
            # Get event summary
            summary = str(event.get('SUMMARY', 'No summary'))
            
            # Get event date
            if 'DTSTART' in event:
                dt_value = event['DTSTART'].dt
                start_date = dt_value.strftime("%Y%m%d") if hasattr(dt_value, 'strftime') else "Unknown"
                year = start_date[:4] if start_date != "Unknown" else "other"
                if year not in events_by_year:
                    year = "other"
            else:
                start_date = "Unknown"
                year = "other"
            
            # Categorize event based on CATEGORIES property
            event_type = "other"
            if 'CATEGORIES' in event:
                category_value = str(event['CATEGORIES'])
                
                # Convert binary value if needed
                if hasattr(event['CATEGORIES'], 'to_ical'):
                    try:
                        category_value = event['CATEGORIES'].to_ical().decode('utf-8')
                    except:
                        pass
                
                if 'Public Holiday' in category_value:
                    event_type = "public"
                    public_holidays += 1
                    events_by_year[year]["public"] += 1
                elif 'School Term' in category_value:
                    event_type = "school_term"
                    school_terms += 1
                    events_by_year[year]["school_term"] += 1
                elif 'School Holiday' in category_value:
                    event_type = "school_holiday"
                    school_holidays += 1
                    events_by_year[year]["school_holiday"] += 1
                else:
                    other_events += 1
                    events_by_year[year]["other"] += 1
            else:
                other_events += 1
                events_by_year[year]["other"] += 1
            
            # Check summary for brackets
            brackets = re.findall(r'[\(\[\{\<].*?[\)\]\}\>]', summary)
            if brackets:
                bracket_issues.append(f"Event '{summary}' contains brackets: {brackets}")
            
            # Verify all-day event formatting
            dtstart = event.get('DTSTART')
            dtend = event.get('DTEND')
            transp = event.get('TRANSP')
            
            if not dtstart:
                formatting_issues.append(f"Event '{summary}' missing DTSTART")
            
            if not dtend:
                formatting_issues.append(f"Event '{summary}' missing DTEND")
                
            if not transp or str(transp) != 'TRANSPARENT':
                full_day_issues.append(f"Event '{summary}' not marked as transparent (blocking time in calendar)")
                
            # Check if it's properly formatted as an all-day event
            if dtstart and dtend:
                dtstart_dt = dtstart.dt
                dtend_dt = dtend.dt
                
                # Check if using DATE value type (all-day) instead of DATE-TIME
                if hasattr(dtstart, 'params') and 'VALUE' in dtstart.params and dtstart.params['VALUE'] == 'DATE':
                    # This is correct for all-day events
                    pass
                else:
                    full_day_issues.append(f"Event '{summary}' not using VALUE=DATE for all-day format")
                
                # For all-day events in iCalendar, end date should be start date + 1 day
                if hasattr(dtstart_dt, 'day') and hasattr(dtend_dt, 'day'):
                    # Calculate difference between dates
                    delta = (dtend_dt - dtstart_dt).days
                    if delta != 1:
                        full_day_issues.append(f"Event '{summary}' has incorrect duration: {delta} days instead of 1")
        
        results.append(("Public Holidays", public_holidays))
        results.append(("School Terms", school_terms))
        results.append(("School Holidays", school_holidays))
        results.append(("Other Events", other_events))
        
        # Report events by year
        for year in ["2025", "2026", "2027"]:
            year_counts = events_by_year[year]
            total_year = sum(year_counts.values())
            results.append((f"Events in {year}", 
                           f"Total: {total_year} (Public: {year_counts['public']}, "
                           f"School Terms: {year_counts['school_term']}, "
                           f"School Holidays: {year_counts['school_holiday']})"))
        
        # Google Calendar compatibility checks
        gc_issues = []
        
        # Check calendar file size
        file_size = os.path.getsize(calendar_file) / 1024  # in KB
        if file_size > 1024:  # > 1MB
            gc_issues.append(f"Calendar file size ({file_size:.2f} KB) may be too large for some calendar apps")
            
        # Check for UID uniqueness (required by Google Calendar)
        uid_map = {}
        for event in events:
            if 'UID' in event:
                uid = str(event['UID'])
                if uid in uid_map:
                    gc_issues.append(f"Duplicate UID found: {uid} - Events will not sync properly to Google Calendar")
                uid_map[uid] = True
            else:
                gc_issues.append(f"Event missing UID: {event.get('SUMMARY', 'Unknown')} - Required for Google Calendar")
                
        # Check for valid DTSTAMP (required by Google Calendar)
        for event in events:
            if 'DTSTAMP' not in event:
                gc_issues.append(f"Event missing DTSTAMP: {event.get('SUMMARY', 'Unknown')} - Required for Google Calendar")
        
        # Report Google Calendar compatibility issues
        if gc_issues:
            results.append(("Google Calendar Compatibility Issues", len(gc_issues)))
            for issue in gc_issues:
                results.append(("  Warning", issue))
        else:
            results.append(("Google Calendar Compatibility", "No issues detected"))
            
        # Report formatting issues
        if formatting_issues:
            results.append(("Formatting Issues", len(formatting_issues)))
            for issue in formatting_issues:
                results.append(("  Warning", issue))
                
        # Report bracket issues
        if bracket_issues:
            results.append(("Events with Brackets", len(bracket_issues)))
            for issue in bracket_issues:
                results.append(("  Warning", issue))
                
        # Report full-day formatting issues
        if full_day_issues:
            results.append(("Full-Day Event Issues", len(full_day_issues)))
            for issue in full_day_issues:
                results.append(("  Warning", issue))
                
        # Add final validation status
        has_issues = len(formatting_issues) + len(bracket_issues) + len(full_day_issues) + len(gc_issues)
        if has_issues == 0:
            results.append(("Validation Status", "Calendar is valid and compatible with Google Calendar"))
        else:
            results.append(("Validation Status", f"Calendar has {has_issues} issues that may affect compatibility"))
        
    except Exception as e:
        results.append(("Error", str(e)))
        results.append(("Validation Status", "Failed to validate calendar"))
        
    return results

if __name__ == "__main__":
    calendar_file = "Public-Holiday-Calendar-SA.ics"
    results = validate_calendar(calendar_file)
    
    # Write validation results to file, using utf-8 encoding
    with open("calendar_validation_results.txt", "w", encoding="utf-8") as f:
        f.write("SOUTH AUSTRALIA PUBLIC HOLIDAY CALENDAR VALIDATION\n")
        f.write("=" * 50 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Calendar file: {calendar_file}\n")
        f.write("-" * 50 + "\n\n")
        
        for label, value in results:
            # Skip any special characters that might cause encoding issues
            f.write(f"{label}: {value}\n")
            
    # Print summary to console
    print("\n")
    print("=" * 50)
    print("Calendar Validation Results:")
    print("-" * 50)
    for label, value in results:
        print(f"{label}: {value}")
    print("=" * 50)
    print(f"Details written to: calendar_validation_results.txt") 