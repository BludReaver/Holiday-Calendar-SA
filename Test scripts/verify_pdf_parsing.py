import os
import pdfplumber
import re
from datetime import datetime, timedelta
import pytz

# Configuration
PDF_FOLDER = "Public Holidays PDF Data"
TIMEZONE = "Australia/Adelaide"

def verify_pdf_parsing():
    """Check that PDF parsing works correctly and extract holidays."""
    # Ensure the PDF folder exists
    os.makedirs(PDF_FOLDER, exist_ok=True)
    
    # Find PDF files
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {PDF_FOLDER}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s): {', '.join(pdf_files)}")
    
    # Process the first PDF file
    pdf_path = os.path.join(PDF_FOLDER, pdf_files[0])
    print(f"Processing {pdf_path}...")
    
    holidays = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF has {len(pdf.pages)} pages")
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"Processing page {page_num}...")
            
            # Extract tables from the page
            tables = page.extract_tables()
            print(f"Found {len(tables)} tables on page {page_num}")
            
            for table_num, table in enumerate(tables, 1):
                print(f"Processing table {table_num} on page {page_num}...")
                
                if not table or len(table) <= 1:
                    print(f"Table {table_num} on page {page_num} is empty or has only headers")
                    continue
                    
                headers = table[0] if table else []
                print(f"Headers: {headers}")
                
                for row_num, row in enumerate(table[1:], 1):
                    print(f"Processing row {row_num}: {row}")
                    
                    if not row or not row[0]:
                        print(f"Row {row_num} is empty or missing holiday name")
                        continue
                    
                    # Original holiday name
                    original_name = row[0].strip()
                    print(f"Original holiday name: {original_name}")
                    
                    # Remove ALL brackets and their contents
                    name = re.sub(r'\([^)]*\)', '', original_name) # Remove (parentheses)
                    name = re.sub(r'\[[^\]]*\]', '', name)         # Remove [square brackets]
                    name = re.sub(r'\{[^}]*\}', '', name)          # Remove {curly braces}
                    name = re.sub(r'<[^>]*>', '', name)            # Remove <angle brackets>
                    name = name.strip()
                    print(f"Cleaned holiday name: {name}")
                    
                    # If it's a part-day holiday, treat as full day
                    if "Part-day" in name or "part-day" in name or "half-day" in name or "Half-day" in name:
                        # Replace the part-day designation but keep the holiday name
                        name = re.sub(r'Part-day public holiday|part-day public holiday|half-day public holiday|Half-day public holiday', 'Public Holiday', name)
                        print(f"Adjusted part-day holiday to full day: {name}")
                    
                    for i in range(1, len(headers)):
                        year = headers[i].strip() if i < len(headers) else ""
                        cell = row[i].strip() if i < len(row) and row[i] else ""
                        print(f"Processing date cell for {year}: '{cell}'")
                        
                        if not cell or not year:
                            print(f"Empty date cell or year column for {year}, skipping")
                            continue
                        
                        # Try different date formats
                        date_obj = None
                        
                        # Format: "Weekday Day Month"
                        date_match = re.search(r'(\w+)\s+(\d{1,2})\s+(\w+)', cell)
                        if date_match:
                            weekday, day, month = date_match.groups()
                            print(f"Matched format 'Weekday Day Month': {weekday} {day} {month} {year}")
                            try:
                                date_obj = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                                print(f"Successfully parsed date: {date_obj}")
                            except ValueError as e:
                                print(f"Failed to parse with full month name: {e}")
                                try:
                                    # Try abbreviated month names
                                    date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                                    print(f"Successfully parsed date with abbreviated month: {date_obj}")
                                except ValueError as e:
                                    print(f"Failed to parse with abbreviated month name: {e}")
                        else:
                            print(f"No match for format 'Weekday Day Month'")
                        
                        # Format: "Day Month"
                        if not date_obj:
                            date_match = re.search(r'(\d{1,2})\s+(\w+)', cell)
                            if date_match:
                                day, month = date_match.groups()
                                print(f"Matched format 'Day Month': {day} {month} {year}")
                                try:
                                    date_obj = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                                    print(f"Successfully parsed date: {date_obj}")
                                except ValueError as e:
                                    print(f"Failed to parse with full month name: {e}")
                                    try:
                                        # Try abbreviated month names
                                        date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                                        print(f"Successfully parsed date with abbreviated month: {date_obj}")
                                    except ValueError as e:
                                        print(f"Failed to parse with abbreviated month name: {e}")
                            else:
                                print(f"No match for format 'Day Month'")
                        
                        if date_obj:
                            holidays.append((date_obj, name))
                            print(f"Added holiday: {date_obj.date()} - {name}")
                        else:
                            print(f"Failed to parse date from: '{cell}', skipping")
    
    # Print results
    print(f"\nExtracted {len(holidays)} holidays from PDF:")
    for date, name in sorted(holidays, key=lambda x: x[0]):
        print(f"{date.date()} - {name}")
    
    # Count by year
    years = {}
    for date, name in holidays:
        year = date.year
        if year not in years:
            years[year] = []
        years[year].append((date, name))
    
    print("\nHolidays by year:")
    for year, events in sorted(years.items()):
        print(f"{year}: {len(events)} holidays")
        for date, name in sorted(events, key=lambda x: x[0]):
            print(f"  {date.date()} - {name}")

if __name__ == "__main__":
    verify_pdf_parsing() 