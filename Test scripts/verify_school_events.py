#!/usr/bin/env python3
import re
from datetime import datetime

def verify_school_events():
    """
    Verify that school terms and holidays are correctly defined
    and follow the expected pattern (terms begin/end, holidays between terms)
    """
    print("Verifying school terms and holidays for 2025-2027...")
    
    # Read the calendar file
    with open('Public-Holiday-Calendar-SA.ics', 'r') as f:
        content = f.read()
    
    # Extract events
    events = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL)
    print(f"Found {len(events)} events in the calendar")
    
    # Create structures to store terms and holidays by year
    school_terms = {2025: [], 2026: [], 2027: []}
    school_holidays = {2025: [], 2026: [], 2027: []}
    
    # Process each event
    for event in events:
        # Get date, summary, and category
        date_match = re.search(r'DTSTART;VALUE=DATE:(\d{8})', event)
        summary_match = re.search(r'SUMMARY:(.*?)(?:\r\n|\r|\n)', event)
        category_match = re.search(r'CATEGORIES:(.*?)(?:\r\n|\r|\n)', event)
        
        if date_match and summary_match and category_match:
            date_str = date_match.group(1)
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            summary = summary_match.group(1).strip()
            category = category_match.group(1).strip()
            
            # Store event info based on category
            event_info = {
                "date": f"{year}-{month:02d}-{day:02d}",
                "summary": summary
            }
            
            if category == "School Term":
                if year in school_terms:
                    school_terms[year].append(event_info)
            elif category == "School Holiday":
                if year in school_holidays:
                    school_holidays[year].append(event_info)
    
    # Sort events by date
    for year in school_terms:
        school_terms[year].sort(key=lambda x: x["date"])
        school_holidays[year].sort(key=lambda x: x["date"])
    
    # Verify patterns for each year
    print("\nVerifying school event patterns:")
    
    all_valid = True
    
    for year in sorted(school_terms.keys()):
        terms = school_terms[year]
        holidays = school_holidays[year]
        
        print(f"\n{year}:")
        
        # Check number of terms
        if len(terms) == 8:  # 4 begins and 4 ends
            print(f"  ✓ Found 8 term events (4 terms)")
            
            # Check term pattern (begins followed by ends)
            begins = [t for t in terms if "Begins" in t["summary"]]
            ends = [t for t in terms if "Ends" in t["summary"]]
            
            if len(begins) == 4 and len(ends) == 4:
                print(f"  ✓ Found 4 term begins and 4 term ends")
                
                # Check alternating pattern
                alternating = True
                i = 0
                while i < len(terms) - 1:
                    if ("Begins" in terms[i]["summary"] and "Ends" not in terms[i+1]["summary"]) or \
                       ("Ends" in terms[i]["summary"] and "Begins" not in terms[i+1]["summary"]):
                        alternating = False
                        break
                    i += 2
                
                if alternating:
                    print(f"  ✓ Terms follow the correct Begin->End pattern")
                else:
                    print(f"  ✗ Terms do not follow the correct Begin->End pattern")
                    all_valid = False
            else:
                print(f"  ✗ Imbalance in term begins ({len(begins)}) and ends ({len(ends)})")
                all_valid = False
        else:
            print(f"  ✗ Expected 8 term events, found {len(terms)}")
            all_valid = False
            
        # Check number of holidays
        if len(holidays) == 8:  # 2 per term (start and end of holiday)
            print(f"  ✓ Found 8 holiday events (4 holiday periods)")
        else:
            print(f"  ✗ Expected 8 holiday events, found {len(holidays)}")
            all_valid = False
            
        # Check that holidays occur after term ends and before term begins
        # Display the pattern of terms and holidays
        print(f"\n  School events sequence:")
        all_events = []
        for t in terms:
            all_events.append((t["date"], t["summary"], "Term"))
        for h in holidays:
            all_events.append((h["date"], h["summary"], "Holiday"))
        
        all_events.sort(key=lambda x: x[0])
        
        for date, summary, event_type in all_events:
            print(f"    {date}: {summary} ({event_type})")
    
    # Print final result
    print("\nSummary:")
    if all_valid:
        print("All school terms and holidays follow the expected patterns! ✓")
    else:
        print("Some issues found with school terms and holidays ✗")

if __name__ == "__main__":
    verify_school_events() 