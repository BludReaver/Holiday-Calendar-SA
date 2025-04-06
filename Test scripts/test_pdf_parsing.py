import os
import pdfplumber
import re
from datetime import datetime

# Configuration
PDF_FOLDER = "Public Holidays PDF Data"
LOG_FILE = "pdf_parsing_test.txt"

# Verify PDF folder exists
os.makedirs(PDF_FOLDER, exist_ok=True)

# Find any PDF files in the folder
pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith('.pdf')]

# Log file for results
with open(LOG_FILE, "w") as log:
    if not pdf_files:
        log.write("No PDF files found in the folder.\n")
        print("No PDF files found.")
    else:
        pdf_name = os.path.join(PDF_FOLDER, pdf_files[0])
        log.write(f"Found PDF: {pdf_name}\n")
        print(f"Found PDF: {pdf_name}")
        
        # Parse holidays from PDF
        holidays = []
        try:
            log.write(f"Parsing PDF: {pdf_name}\n")
            with pdfplumber.open(pdf_name) as pdf:
                log.write(f"PDF has {len(pdf.pages)} pages\n")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    log.write(f"Processing page {page_num}...\n")
                    tables = page.extract_tables()
                    log.write(f"Found {len(tables)} tables on page {page_num}\n")
                    
                    for table_num, table in enumerate(tables, 1):
                        log.write(f"Processing table {table_num} on page {page_num}...\n")
                        if not table or len(table) <= 1:
                            log.write(f"Table {table_num} on page {page_num} is empty or has only headers\n")
                            continue
                            
                        headers = table[0] if table else []
                        log.write(f"Headers: {headers}\n")
                        
                        for row_num, row in enumerate(table[1:], 1):
                            if not row or not row[0]:
                                continue
                            
                            # Original holiday name
                            original_name = row[0].strip()
                            
                            # Clean name (remove brackets)
                            name = re.sub(r'\([^)]*\)', '', original_name)
                            name = re.sub(r'\[[^\]]*\]', '', name)
                            name = re.sub(r'\{[^}]*\}', '', name)
                            name = re.sub(r'<[^>]*>', '', name)
                            name = name.strip()
                            
                            # If it's a part-day holiday, treat as full day
                            if "Part-day" in name or "part-day" in name:
                                name = re.sub(r'Part-day public holiday|part-day public holiday', 'Public Holiday', name)
                            
                            for i in range(1, len(headers)):
                                year = headers[i].strip() if i < len(headers) else ""
                                cell = row[i].strip() if i < len(row) and row[i] else ""
                                
                                if not cell or not year:
                                    continue
                                
                                # Try different date formats
                                date_obj = None
                                
                                # Format: "Weekday Day Month"
                                date_match = re.search(r'(\w+)\s+(\d{1,2})\s+(\w+)', cell)
                                if date_match:
                                    weekday, day, month = date_match.groups()
                                    try:
                                        date_obj = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                                    except ValueError:
                                        try:
                                            date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                                        except ValueError:
                                            pass
                                
                                # Format: "Day Month"
                                if not date_obj:
                                    date_match = re.search(r'(\d{1,2})\s+(\w+)', cell)
                                    if date_match:
                                        day, month = date_match.groups()
                                        try:
                                            date_obj = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                                        except ValueError:
                                            try:
                                                date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                                            except ValueError:
                                                pass
                                
                                if date_obj:
                                    holidays.append((date_obj, name))
            
            # Write results
            log.write(f"\nFound {len(holidays)} holidays in the PDF.\n")
            log.write("\nHolidays by year:\n")
            
            years = {}
            for date_obj, name in holidays:
                year = date_obj.year
                if year not in years:
                    years[year] = []
                years[year].append((date_obj, name))
            
            for year in sorted(years.keys()):
                log.write(f"\n{year} Holidays ({len(years[year])}):\n")
                for date_obj, name in sorted(years[year]):
                    log.write(f"  {date_obj.strftime('%Y-%m-%d')} - {name}\n")
            
            print(f"PDF parsing completed. Found {len(holidays)} holidays. Details in {LOG_FILE}")
            
        except Exception as e:
            log.write(f"Error parsing PDF: {str(e)}\n")
            print(f"Error parsing PDF: {str(e)}")

print(f"PDF parsing test completed. Results in {LOG_FILE}") 