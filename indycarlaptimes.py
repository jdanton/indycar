import re
from PyPDF2 import PdfReader
import csv
import os

# Path to the PDF file - use expanduser to handle the tilde
pdf_path = os.path.expanduser("~/demos/indycar/indycar-sectionresults-race-birmingham-2025.pdf")

# Check if the PDF exists
if not os.path.exists(pdf_path):
    print(f"Error: PDF file not found at {pdf_path}")
    exit(1)

reader = PdfReader(pdf_path)
print(f"PDF loaded successfully with {len(reader.pages)} pages")

def find_all_drivers(reader):
    """
    Scan through the PDF to find all drivers and their car numbers
    Returns a list of tuples: (car_number, driver_name)
    """
    drivers = {}  # Using dict to eliminate duplicates
    
    # Look for section headers like "Section Data for Car X - Driver Name"
    section_header_pattern = r"Section Data for Car (\d+) - ([^,]+),\s*([^,]+)"
    
    for page_num in range(len(reader.pages)):
        text = reader.pages[page_num].extract_text()
        if not text:
            continue
            
        # Check if this page has driver information
        matches = re.findall(section_header_pattern, text)
        for match in matches:
            car_number = match[0]
            last_name = match[1].strip()
            first_name = match[2].strip()
            driver_name = f"{last_name}, {first_name}"
            
            # Add to our drivers dictionary
            drivers[car_number] = driver_name
    
    # Convert dict to list of tuples
    driver_list = [(car, name) for car, name in drivers.items()]
    
    # Sort by car number
    driver_list.sort(key=lambda x: int(x[0]))
    
    return driver_list

def extract_driver_lap_times(reader, car_number, driver_name):
    """
    Extract lap times for a specific driver based on the observed pattern:
    - Lap number on one line
    - "T" on next line
    - Several sector times
    - Full lap time right before a line with just "S"
    """
    lap_data = {}
    found_sections = []
    
    print(f"Looking for data for driver {driver_name} (Car {car_number})")
    
    # Process every page
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
            
        # Check if this page contains data for our driver
        if driver_name in text or f"Car {car_number}" in text:
            found_sections.append(page_num)
            
            lines = text.split('\n')
            
            # Look for the pattern: lap number, sector times, lap time, "S"
            current_lap = None
            
            for i in range(len(lines)-1):
                # Check if current line is just "S" - the full lap time would be right before
                if lines[i].strip() == "S" and i > 0:
                    # Try to get lap time from previous line
                    lap_time_match = re.match(r'^(\d+\.\d+)$', lines[i-1].strip())
                    if lap_time_match and current_lap is not None:
                        lap_time = float(lap_time_match.group(1))
                        
                        # Validate the lap time (seems to be around 70 seconds for this track)
                        if 65.0 <= lap_time <= 80.0:
                            lap_data[current_lap] = (car_number, driver_name, current_lap, lap_time)
                            # Reduce verbosity - only print every 10th lap
                            if current_lap % 10 == 0:
                                print(f"Added lap {current_lap}: {lap_time} seconds")
                            
                            # Reset current lap
                            current_lap = None
                
                # Check if this line is a lap number
                if re.match(r'^\d+$', lines[i].strip()) and i+1 < len(lines):
                    # Check if next line is "T"
                    if lines[i+1].strip() == "T":
                        # This is likely a lap number
                        try:
                            current_lap = int(lines[i].strip())
                        except ValueError:
                            current_lap = None
    
    print(f"Found {len(lap_data)} unique lap times for {driver_name} (Car {car_number}) across {len(found_sections)} sections")
    return list(lap_data.values())

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

# Save to CSV
csv_path_full = os.path.expanduser("~/demos/indycar/indycar-lap-times.csv")
if all_lap_times:
    with open(csv_path_full, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Car", "Driver", "Lap", "T (Time)"])
        writer.writerows(all_lap_times)

    print(f"\n✅ Saved {len(all_lap_times)} lap times to {csv_path_full}")
    
    # Print summary of lap times by driver
    print("\nLap counts by driver:")
    for driver, laps in driver_lap_times.items():
        print(f"  {driver}: {len(laps)} laps")
else:
    print("⚠️ No lap times found. Check the PDF format and ensure the driver names match exactly.")