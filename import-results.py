#!/usr/bin/env python3

import os
import re
import time
import requests
from datetime import datetime
import subprocess
from pathlib import Path

# Create output directory
output_dir = Path("indycar_results")
output_dir.mkdir(exist_ok=True)

# Document ID ranges by year - with correct starting points
DOCUMENT_RANGES = {
    2019: [5463, 5471, 5480, 5490, 5500, 5510, 5520, 5530, 5540, 5550, 5560, 5570, 5580, 5590, 5600],
    2020: [5733, 5740, 5750, 5760, 5770, 5780, 5790],  # Starting at 5733
    2021: [5797, 5810, 5820, 5830, 5840, 5850, 5860, 5870, 5880],  # Starting at 5797
    2022: [5905, 5920, 5930, 5940, 5950, 5960, 5970, 5980, 5990],  # Starting at 5905
    2023: [6125, 6140, 6150, 6160, 6170, 6180, 6190, 6200, 6210],  # Starting at 6125
    2024: [6298, 6310, 6320, 6330, 6340, 6350, 6360, 6370, 6380],  # Starting at 6298
    2025: [6472, 6480, 6490, 6500, 6510, 6520, 6530, 6540, 6550],  # Starting at 6472
}

# Track locations for known dates
TRACK_MAPPING = {
    "2025-04-13": "long-beach",
    "2025-05-04": "birmingham",
    "2025-06-01": "detroit",
    "2019-04-07": "long-beach",
}

# All race dates by year - fixed typos in the comma placement that existed in original data
RACE_DATES = {
    2019: [
        "2019-03-10", "2019-03-24", "2019-04-07", "2019-04-14", "2019-05-11", "2019-05-26",
        "2019-06-01", "2019-06-08", "2019-06-23", "2019-07-14", "2019-07-20", "2019-07-21", "2019-07-28",
        "2019-08-18", "2019-08-24", "2019-09-01", "2019-09-22"
    ],
    2020: [
        "2020-06-06", "2020-07-04", "2020-07-11", "2020-07-12", "2020-07-17",
        "2020-08-23", "2020-08-29", "2020-08-30", "2020-09-12", "2020-09-13",
        "2020-10-02", "2020-10-03", "2020-10-25"
    ],
    2021: [
        "2021-04-18", "2021-04-25", "2021-05-01", "2021-05-02", "2021-05-15",
        "2021-05-30", "2021-06-12", "2021-06-13", "2021-06-20", "2021-07-04",
        "2021-07-11", "2021-08-08", "2021-08-14", "2021-08-21", "2021-09-12",
        "2021-09-19", "2021-09-26"
    ],
    2022: [
        "2022-02-27", "2022-03-20", "2022-04-10", "2022-05-01", "2022-05-14",
        "2022-05-29", "2022-06-05", "2022-06-12", "2022-07-03", "2022-07-17",
        "2022-07-24", "2022-07-30", "2022-08-07", "2022-08-20",
        "2022-09-04", "2022-09-11"
    ],
    2023: [
        "2023-03-05", "2023-04-02", "2023-04-16", "2023-04-30", "2023-05-13",
        "2023-05-28", "2023-06-04", "2023-06-18", "2023-07-02", "2023-07-16",
        "2023-07-22", "2023-07-23", "2023-08-06", "2023-08-12", "2023-08-27",
        "2023-09-03", "2023-09-10"
    ],
    2024: [
        "2024-03-10", "2024-03-24", "2024-04-21", "2024-04-28", "2024-05-11",
        "2024-05-26", "2024-06-02", "2024-06-09", "2024-06-23", "2024-07-07",
        "2024-07-13", "2024-07-14", "2024-07-21", "2024-08-17", "2024-08-25",
        "2024-08-31", "2024-09-01", "2024-09-15"
    ],
    2025: [
        "2025-03-02", "2025-03-23", "2025-04-13", "2025-05-04", "2025-05-10",
        "2025-05-25", "2025-06-01", "2025-06-15", "2025-06-22", "2025-07-06",
        "2025-07-12", "2025-07-13", "2025-07-20", "2025-07-27", "2025-08-10",
        "2025-08-24", "2025-08-31"
    ]
}

def is_future_date(date_str):
    """Check if a date is in the future."""
    try:
        race_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        return race_date > today
    except ValueError:
        # If there's an error parsing the date, assume it's not in the future
        return False

def find_and_download_pdf(date):
    """Try to find and download a PDF for a specific race date."""
    # Validate date format
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        print(f"Invalid date format: {date} - skipping")
        return False
    
    # Skip future dates
    if is_future_date(date):
        print(f"Skipping future race date: {date}")
        return False
    
    year = date[:4]
    
    # Get track name if available
    track = TRACK_MAPPING.get(date, "")
    track_suffix = f"-{track}" if track else ""
    
    # Define filename for saving
    output_file = f"indycar-sectionresults-race{track_suffix}-{date}.pdf"
    output_path = output_dir / output_file
    
    # Check if file already exists
    if output_path.exists():
        print(f"File already exists: {output_file}. Skipping.")
        return True
    
    # Get document range for this year
    doc_range = DOCUMENT_RANGES.get(int(year), [6000])
    
    # Special case for known URLs
    if date == "2019-06-08":
        url = f"http://www.imscdn.com/INDYCAR/Documents/5471/2019-06-08/indycar-sectionresults-race.pdf"
        if download_pdf(url, output_path, date):
            return True
    
    # Try different document IDs
    for doc_id in doc_range:
        # Try a range around the estimated document ID
        for id in range(doc_id - 10, doc_id + 11):
            url = f"http://www.imscdn.com/INDYCAR/Documents/{id}/{date}/indycar-sectionresults-race.pdf"
            
            print(f"Trying: {url}")
            
            if download_pdf(url, output_path, date):
                return True
    
    print(f"❌ Could not find valid URL for race date: {date}")
    return False

def download_pdf(url, output_path, date):
    """Download a PDF if it exists."""
    try:
        # Check if the URL exists (HEAD request)
        head_response = requests.head(url, timeout=5)
        if head_response.status_code != 200:
            return False
        
        # Download the file
        print(f"Downloading results for {date} from {url}")
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200 and len(response.content) > 0:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # Verify download was successful
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"✅ Download successful: {output_path.name}")
                return True
            else:
                print(f"⚠️ Download failed or empty file: {url}")
                if output_path.exists():
                    output_path.unlink()  # Remove empty/corrupt file
                return False
        else:
            return False
    
    except requests.exceptions.RequestException:
        return False
    
    # Small delay to avoid hammering the server
    time.sleep(1)
    return False

def process_pdf(pdf_path):
    """Process a PDF with the lap time extraction script."""
    try:
        print(f"Processing {pdf_path} with lap time extraction script...")
        subprocess.run(['python3', 'indycarlaptimes.py', str(pdf_path)], check=True)
        return True
    except subprocess.SubprocessError as e:
        print(f"Error processing PDF: {e}")
        return False

def main():
    """Main function to download IndyCar race results."""
    # Years to process
    years = range(2019, 2026)  # 2019 to 2025
    
    # Collect all race dates (excluding future dates)
    all_race_dates = []
    current_date = datetime.now().date()
    
    for year in years:
        year_dates = RACE_DATES.get(year, [])
        # Filter out future dates
        year_dates = [date for date in year_dates if not is_future_date(date)]
        
        print(f"Using {len(year_dates)} race dates for {year}")
        all_race_dates.extend(year_dates)
    
    print(f"Starting IndyCar results download...")
    print(f"Attempting to download files for {len(all_race_dates)} potential race dates")
    
    # Try to download PDFs for each date
    successful_downloads = 0
    
    for date in all_race_dates:
        if find_and_download_pdf(date):
            successful_downloads += 1
    
    print(f"Download process complete.")
    print(f"Successfully downloaded {successful_downloads} race result PDFs.")
    
    # Process each downloaded PDF
    process_count = 0
    for pdf_file in output_dir.glob('*.pdf'):
        if process_pdf(pdf_file):
            process_count += 1
    
    print(f"Successfully processed {process_count} PDFs.")
    print("All operations completed.")

if __name__ == "__main__":
    main()