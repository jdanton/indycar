import re
from PyPDF2 import PdfReader
import csv
import os
import sys
import glob

# Create the output directory if it doesn't exist
output_dir = os.path.expanduser("~/demos/indycar/parsed-results")
os.makedirs(output_dir, exist_ok=True)

def extract_event_info(reader):
    """
    Extract event name and date from the PDF header information.
    Returns a tuple: (event_name, event_date)
    """
    event_name = "unknown-event"
    event_date = "unknown-date"
    
    # Check first few pages for header information
    for page_num in range(min(5, len(reader.pages))):
        text = reader.pages[page_num].extract_text()
        if not text:
            continue
            
        # Look for event name pattern
        event_match = re.search(r"Event:\s*([^\n]+)", text)
        if event_match:
            event_name = event_match.group(1).strip()
        
        # Look for date pattern - check for month name followed by day and year
        date_match = re.search(r"(\w+ \d+, \d{4})", text)
        if date_match:
            event_date = date_match.group(1).strip()
        
        # Also check for specific format in IndyCar PDFs
        race_match = re.search(r"([^:\n]+Grand Prix|[^:\n]+Race|[^:\n]+375|[^:\n]+500)", text, re.IGNORECASE)
        if race_match and event_name == "unknown-event":
            event_name = race_match.group(1).strip()
            
        # If we found both, no need to check more pages
        if event_name != "unknown-event" and event_date != "unknown-date":
            break
    
    # Extract date from filename if not found in content
    if event_date == "unknown-date":
        # Try to extract date from the PDF filename (format: YYYY-MM-DD)
        filename = os.path.basename(reader.stream.name)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            event_date = date_match.group(1)
    
    # Clean up the event name for filename use (replace spaces, special chars)
    event_name = re.sub(r'[^\w\s-]', '', event_name).strip().lower()
    event_name = re.sub(r'[\s]+', '-', event_name)
    
    return event_name, event_date

def find_all_drivers(reader):
    """
    Find all drivers and their car numbers in the PDF.
    Returns a list of tuples: [(car_number, driver_name), ...]
    """
    drivers = []
    driver_dict = {}  # To avoid duplicates
    
    # Common patterns for driver information in IndyCar result PDFs
    car_driver_pattern = re.compile(r'(\d{1,2})\s+([A-Z][a-z]+\s+[A-Z][a-zA-Z\'-]+)')
    alt_pattern = re.compile(r'(?:^|\s)(\d{1,2})\s+([A-Z][a-zA-Z\'-]+),\s+([A-Z][a-zA-Z\'-]+)')
    
    # Scan all pages for driver information
    for page_num in range(len(reader.pages)):
        text = reader.pages[page_num].extract_text()
        if not text:
            continue
        
        # Process each line in the page
        for line in text.split('\n'):
            # Try first pattern
            matches = car_driver_pattern.findall(line)
            for match in matches:
                car_number, driver_name = match
                if car_number not in driver_dict:
                    driver_dict[car_number] = driver_name
            
            # Try alternate pattern
            alt_matches = alt_pattern.findall(line)
            for match in alt_matches:
                car_number, last_name, first_name = match
                driver_name = f"{first_name} {last_name}"
                if car_number not in driver_dict:
                    driver_dict[car_number] = driver_name
    
    # Convert dictionary to list of tuples
    for car_number, driver_name in driver_dict.items():
        drivers.append((car_number, driver_name))
    
    # If no drivers found, try a more aggressive approach
    if not drivers:
        print("No drivers found with standard pattern, trying alternative method...")
        
        # Simplified pattern that might catch more formats
        simple_pattern = re.compile(r'(\d{1,2})[\s\.\-]+([A-Za-z]+)')
        
        for page_num in range(len(reader.pages)):
            text = reader.pages[page_num].extract_text()
            if not text:
                continue
            
            matches = simple_pattern.findall(text)
            for match in matches:
                car_number, name_part = match
                # Only add if car number seems reasonable for IndyCar
                if 1 <= int(car_number) <= 99 and len(name_part) > 2:
                    if car_number not in driver_dict:
                        driver_dict[car_number] = name_part
        
        # Convert dictionary to list of tuples again
        drivers = [(car_number, driver_name) for car_number, driver_name in driver_dict.items()]
    
    return drivers

def extract_driver_lap_times(reader, car_number, driver_name):
    """
    Extract lap times for a specific driver.
    Returns a list of tuples: [(car_number, driver_name, lap_number, lap_time), ...]
    """
    lap_times = []
    
    # Pattern to match lap time data
    lap_pattern = re.compile(rf'{car_number}\s+{re.escape(driver_name)}.*?(\d+)\s+(\d+:\d+\.\d+|\d+\.\d+)')
    alt_pattern = re.compile(rf'(Lap|LAP)\s+(\d+).*?{car_number}.*?(\d+:\d+\.\d+|\d+\.\d+)')
    
    # Scan all pages for lap times
    for page_num in range(len(reader.pages)):
        text = reader.pages[page_num].extract_text()
        if not text:
            continue
        
        # Process each line for the main pattern
        for line in text.split('\n'):
            matches = lap_pattern.findall(line)
            for match in matches:
                lap_number, lap_time = match
                lap_times.append((car_number, driver_name, lap_number, lap_time))
        
        # Try alternate pattern if needed
        if not lap_times:
            for line in text.split('\n'):
                matches = alt_pattern.findall(line)
                for match in matches:
                    _, lap_number, lap_time = match
                    lap_times.append((car_number, driver_name, lap_number, lap_time))
    
    # If still no lap times, try a more general approach
    if not lap_times:
        # Just look for numbers that might be lap times near the car number
        time_pattern = re.compile(r'(\d{1,2}:\d{2}\.\d{4}|\d{1,2}\.\d{4})')
        
        for page_num in range(len(reader.pages)):
            text = reader.pages[page_num].extract_text()
            if not text:
                continue
            
            for line in text.split('\n'):
                if car_number in line:
                    times = time_pattern.findall(line)
                    for i, time in enumerate(times):
                        # Use index+1 as a pseudo lap number since we don't know the actual lap
                        lap_times.append((car_number, driver_name, str(i+1), time))
    
    return lap_times

# Function to process a single PDF file
def process_pdf(pdf_path):
    print(f"\nProcessing: {os.path.basename(pdf_path)}")
    
    # Check if the PDF exists
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return False
    
    try:
        reader = PdfReader(pdf_path)
        print(f"PDF loaded successfully with {len(reader.pages)} pages")
        
        # Find all drivers in the PDF
        print("Scanning PDF for all drivers...")
        all_drivers = find_all_drivers(reader)
        print(f"Found {len(all_drivers)} drivers in the PDF:")
        for car, driver in all_drivers:
            print(f"  Car #{car}: {driver}")
        
        # Extract lap times for all drivers
        driver_lap_times = {}
        all_lap_times = []
        
        for car_number, driver_name in all_drivers:
            # Extract lap times for this driver
            laps = extract_driver_lap_times(reader, car_number, driver_name)
            driver_lap_times[driver_name] = laps
            all_lap_times.extend(laps)
        
        # Extract event information from the PDF
        event_name, event_date = extract_event_info(reader)
        print(f"Event: {event_name}, Date: {event_date}")
        
        # Generate dynamic filename
        csv_filename = f"indycar-{event_name}-{event_date}-laptimes.csv"
        
        # Save to the parsed-results folder
        csv_path_full = os.path.join(output_dir, csv_filename)
        
        if all_lap_times:
            with open(csv_path_full, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Car", "Driver", "Lap", "T (Time)"])
                writer.writerows(all_lap_times)
            
            print(f"✅ Saved {len(all_lap_times)} lap times to {csv_path_full}")
            return True
        else:
            print("No lap times found to save.")
            return False
    
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        return False

# Main execution code
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If a specific PDF path is provided as argument, process just that one
        pdf_path = sys.argv[1]
        process_pdf(pdf_path)
    else:
        # Process all PDFs in the indycar_results folder
        results_dir = os.path.expanduser("~/demos/indycar/indycar_results")
        if not os.path.exists(results_dir):
            print(f"Warning: Results directory not found at {results_dir}")
            # Try relative path as fallback
            results_dir = "indycar_results"
            if not os.path.exists(results_dir):
                print(f"Error: Could not find results directory")
                exit(1)
        
        # Get all PDF files in the results directory
        pdf_files = glob.glob(os.path.join(results_dir, "*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {results_dir}")
            exit(1)
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each PDF
        successful = 0
        for pdf_path in pdf_files:
            if process_pdf(pdf_path):
                successful += 1
        
        print(f"\nProcessing complete. Successfully processed {successful} of {len(pdf_files)} files.")