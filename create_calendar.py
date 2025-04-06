from datetime import datetime, timedelta

# Create a file with events
ics_file = 'Public-Holiday-Calendar-SA.ics'
with open(ics_file, 'w') as f:
    # Calendar header
    f.write("BEGIN:VCALENDAR\n")
    f.write("VERSION:2.0\n")
    f.write("PRODID:-//South Australia//Public Holidays//EN\n")
    f.write("CALSCALE:GREGORIAN\n")
    f.write("METHOD:PUBLISH\n")
    f.write("X-WR-CALNAME:South Australia Public Holidays and School Terms\n")
    f.write("X-WR-TIMEZONE:Australia/Adelaide\n")
    f.write("X-WR-CALDESC:Public Holidays and School Terms for South Australia\n")

    # Define all holidays for 2025, 2026, and 2027
    all_events = [
        # 2025 Public Holidays
        ('20250101', "New Year's Day", "Public Holiday"),
        ('20250127', "Australia Day", "Public Holiday"),
        ('20250310', "Adelaide Cup Day", "Public Holiday"),
        ('20250418', "Good Friday", "Public Holiday"),
        ('20250419', "Easter Saturday", "Public Holiday"),
        ('20250420', "Easter Sunday", "Public Holiday"),
        ('20250421', "Easter Monday", "Public Holiday"),
        ('20250425', "Anzac Day", "Public Holiday"),
        ('20250609', "King's Birthday", "Public Holiday"),
        ('20251006', "Labour Day", "Public Holiday"),
        ('20251224', "Christmas Eve", "Public Holiday"),
        ('20251225', "Christmas Day", "Public Holiday"),
        ('20251226', "Proclamation Day", "Public Holiday"),
        ('20251231', "New Year's Eve", "Public Holiday"),
        
        # 2026 Public Holidays
        ('20260101', "New Year's Day", "Public Holiday"),
        ('20260126', "Australia Day", "Public Holiday"),
        ('20260309', "Adelaide Cup Day", "Public Holiday"),
        ('20260403', "Good Friday", "Public Holiday"),
        ('20260404', "Easter Saturday", "Public Holiday"),
        ('20260405', "Easter Sunday", "Public Holiday"),
        ('20260406', "Easter Monday", "Public Holiday"),
        ('20260425', "Anzac Day", "Public Holiday"),
        ('20260608', "King's Birthday", "Public Holiday"),
        ('20261005', "Labour Day", "Public Holiday"),
        ('20261224', "Christmas Eve", "Public Holiday"),
        ('20261225', "Christmas Day", "Public Holiday"),
        ('20261226', "Proclamation Day", "Public Holiday"),
        ('20261231', "New Year's Eve", "Public Holiday"),
        
        # 2027 Public Holidays
        ('20270101', "New Year's Day", "Public Holiday"),
        ('20270126', "Australia Day", "Public Holiday"),
        ('20270308', "Adelaide Cup Day", "Public Holiday"),
        ('20270326', "Good Friday", "Public Holiday"),
        ('20270327', "Easter Saturday", "Public Holiday"),
        ('20270328', "Easter Sunday", "Public Holiday"),
        ('20270329', "Easter Monday", "Public Holiday"),
        ('20270425', "Anzac Day", "Public Holiday"),
        ('20270614', "King's Birthday", "Public Holiday"),
        ('20271004', "Labour Day", "Public Holiday"),
        ('20271224', "Christmas Eve", "Public Holiday"),
        ('20271225', "Christmas Day", "Public Holiday"),
        ('20271226', "Proclamation Day", "Public Holiday"),
        ('20271231', "New Year's Eve", "Public Holiday"),
        
        # 2025 School Terms and Holidays
        ('20250128', "Term 1 Begins", "School Term"),
        ('20250411', "Term 1 Ends", "School Term"),
        ('20250412', "School Holidays - Term 1", "School Holiday"),
        ('20250427', "School Holidays - Term 1", "School Holiday"),
        ('20250428', "Term 2 Begins", "School Term"),
        ('20250601', "School Holidays - Additional Term 2", "School Holiday"),
        ('20250704', "Term 2 Ends", "School Term"),
        ('20250705', "School Holidays - Term 2", "School Holiday"),
        ('20250720', "School Holidays - Term 2", "School Holiday"),
        ('20250721', "Term 3 Begins", "School Term"),
        ('20250926', "Term 3 Ends", "School Term"),
        ('20250927', "School Holidays - Term 3", "School Holiday"),
        ('20251012', "School Holidays - Term 3", "School Holiday"),
        ('20251013', "Term 4 Begins", "School Term"),
        ('20251212', "Term 4 Ends", "School Term"),
        ('20251213', "School Holidays - Term 4", "School Holiday"),
        ('20260127', "School Holidays - Term 4", "School Holiday"),
        
        # 2026 School Terms and Holidays
        ('20260127', "Term 1 Begins", "School Term"),
        ('20260410', "Term 1 Ends", "School Term"),
        ('20260411', "School Holidays - Term 1", "School Holiday"),
        ('20260426', "School Holidays - Term 1", "School Holiday"),
        ('20260427', "Term 2 Begins", "School Term"),
        ('20260703', "Term 2 Ends", "School Term"),
        ('20260704', "School Holidays - Term 2", "School Holiday"),
        ('20260719', "School Holidays - Term 2", "School Holiday"),
        ('20260720', "Term 3 Begins", "School Term"),
        ('20260925', "Term 3 Ends", "School Term"),
        ('20260926', "School Holidays - Term 3", "School Holiday"),
        ('20261011', "School Holidays - Term 3", "School Holiday"),
        ('20261012', "Term 4 Begins", "School Term"),
        ('20261211', "Term 4 Ends", "School Term"),
        ('20261212', "School Holidays - Term 4", "School Holiday"),
        ('20270126', "School Holidays - Term 4", "School Holiday"),
        
        # 2027 School Terms and Holidays
        ('20270126', "Term 1 Begins", "School Term"),
        ('20270326', "Term 1 Ends", "School Term"),
        ('20270327', "School Holidays - Term 1", "School Holiday"),
        ('20270411', "School Holidays - Term 1", "School Holiday"),
        ('20270412', "Term 2 Begins", "School Term"),
        ('20270702', "Term 2 Ends", "School Term"),
        ('20270703', "School Holidays - Term 2", "School Holiday"),
        ('20270718', "School Holidays - Term 2", "School Holiday"),
        ('20270719', "Term 3 Begins", "School Term"),
        ('20270924', "Term 3 Ends", "School Term"),
        ('20270925', "School Holidays - Term 3", "School Holiday"),
        ('20271010', "School Holidays - Term 3", "School Holiday"),
        ('20271011', "Term 4 Begins", "School Term"),
        ('20271210', "Term 4 Ends", "School Term"),
        ('20271211', "School Holidays - Term 4", "School Holiday")
    ]

    # Add events
    for date_str, name, event_type in all_events:
        date_obj = datetime.strptime(date_str, '%Y%m%d')
        
        # For School Term events, create two events:
        # 1. A single-day event for the begin/end date
        # 2. A full term event as a description for reference
        if event_type == "School Term":
            # Find if this is a term begin or end
            is_begin = "Begins" in name
            is_end = "Ends" in name
            
            # Extract term number
            term_number = name.split("Term ")[1].split(" ")[0]
            
            if is_begin:
                # Find the corresponding end date
                end_event = next((e for e in all_events if f"Term {term_number} Ends" in e[1] and e[0][:4] == date_str[:4]), None)
                
                if end_event:
                    end_date_str = end_event[0]
                    end_date_obj = datetime.strptime(end_date_str, '%Y%m%d')
                    
                    # Create a single-day event for term begin
                    end_date = (date_obj + timedelta(days=1)).strftime('%Y%m%d')
                    
                    # Create a unique ID
                    event_id = f"{date_str}-term{term_number}begins@southaustralia.education"
                    
                    # Create a descriptive summary including date range
                    full_summary = f"Term {term_number} Begins"
                    description = f"School Term {term_number}: {date_obj.strftime('%d %B')} to {end_date_obj.strftime('%d %B %Y')}"
                    
                    f.write("BEGIN:VEVENT\n")
                    f.write(f"DTSTART;VALUE=DATE:{date_str}\n")
                    f.write(f"SUMMARY:{full_summary}\n")
                    f.write(f"DESCRIPTION:{description}\n")
                    f.write(f"CATEGORIES:School Term\n")
                    f.write(f"UID:{event_id}\n")
                    f.write("DTSTAMP:20250406T000000Z\n")
                    f.write(f"DTEND;VALUE=DATE:{end_date}\n")
                    f.write("TRANSP:TRANSPARENT\n")
                    f.write("END:VEVENT\n")
                    
            elif is_end:
                # Create a single-day event for term end
                end_date = (date_obj + timedelta(days=1)).strftime('%Y%m%d')
                event_id = f"{date_str}-term{term_number}ends@southaustralia.education"
                
                f.write("BEGIN:VEVENT\n")
                f.write(f"DTSTART;VALUE=DATE:{date_str}\n")
                f.write(f"SUMMARY:Term {term_number} Ends\n")
                f.write(f"DESCRIPTION:Last day of School Term {term_number}\n")
                f.write(f"CATEGORIES:School Term\n")
                f.write(f"UID:{event_id}\n")
                f.write("DTSTAMP:20250406T000000Z\n")
                f.write(f"DTEND;VALUE=DATE:{end_date}\n")
                f.write("TRANSP:TRANSPARENT\n")
                f.write("END:VEVENT\n")
                
        # For normal events like public holidays and school holidays
        elif not "Ends" in name:  # Skip Term End events as they're now handled separately
            end_date = (date_obj + timedelta(days=1)).strftime('%Y%m%d')
            
            # Create appropriate event ID based on type
            if event_type == "Public Holiday":
                event_id = f"{date_str}-{name.lower().replace(' ', '').replace(chr(39), '')}@southaustralia.holidays"
            elif event_type == "School Holiday":
                term = name.split("Term ")[1] if "Term " in name else ""
                event_id = f"{date_str}-schoolholiday{term}@southaustralia.education"
            else:
                event_id = f"{date_str}-{name.lower().replace(' ', '').replace(chr(39), '')}@southaustralia.events"
            
            f.write("BEGIN:VEVENT\n")
            f.write(f"DTSTART;VALUE=DATE:{date_str}\n")
            f.write(f"SUMMARY:{name}\n")
            f.write(f"CATEGORIES:{event_type}\n")
            f.write(f"UID:{event_id}\n")
            f.write("DTSTAMP:20250406T000000Z\n")
            f.write(f"DTEND;VALUE=DATE:{end_date}\n")
            f.write("TRANSP:TRANSPARENT\n")
            f.write("END:VEVENT\n")

    # Calendar footer
    f.write("END:VCALENDAR\n")

print(f"Calendar file created with all holidays and school terms for 2025-2027: {ics_file}") 