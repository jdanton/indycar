import re
from PyPDF2 import PdfReader
import csv
import os

# Path to the PDF file - use expanduser to handle the tilde
pdf_path = os.path.expanduser("~/demos/indycar/indycar-sectionresults-race.pdf")

# Check if the PDF exists
if not os.path.exists(pdf_path):
    print(f"Error: PDF file not found at {pdf_path}")
    exit(1)

reader = PdfReader(pdf_path)
print(f"PDF loaded successfully with {len(reader.pages)} pages")

def extract_driver_lap_times(reader, car_number, driver_name):
    """
    Extract lap times for a specific driver from an IndyCar timing sheet PDF.
    
    Args:
        reader: PdfReader object
        car_number: String with the car number
        driver_name: String with the driver's name
        
    Returns:
        List of tuples (car_number, driver_name, lap_number, lap_time)
    """
    lap_data = {}  # Use dictionary to handle duplicate lap numbers
    capture = False
    section_count = 0
    current_section = None
    debug_mode = True  # Set to True for verbose logging

    possible_identifiers = [
        f"Section Data for Car {car_number} - {driver_name}",
        f"Car {car_number} - {driver_name}",
        f"{car_number} - {driver_name}"
    ]

    print(f"Looking for data for Car {car_number} - {driver_name}")

    # Process every page in the PDF
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
            
        # Check if this page contains data for our driver
        if any(pid in text for pid in possible_identifiers):
            if debug_mode:
                print(f"Found identifier on page {page_num+1}")
            capture = True
            section_count += 1
        
        # If we're capturing data for this driver
        if capture:
            lines = text.split('\n')
            lap_found_on_page = False
            
            for line in lines:
                line = line.strip()
                
                # Check if we should stop capturing
                # Careful check for section headers for other cars
                if line.startswith("Section Data for Car "):
                    if not any(pid in line for pid in possible_identifiers):
                        if debug_mode:
                            print(f"Found new section header: {line}")
                        capture = False
                        break
                
                # Match lines that start with a number followed by T (lap number identifier)
                lap_match = re.match(r'^(\d+)T\s+(.*)', line)
                if lap_match:
                    lap = int(lap_match.group(1))
                    lap_data_text = lap_match.group(2)
                    
                    # Extract all floating point numbers from the line
                    numbers = re.findall(r'\d+\.\d+', lap_data_text)
                    
                    if numbers:
                        lap_found_on_page = True
                        # Debug the full line and all numbers found
                        if debug_mode:
                            print(f"Raw data for lap {lap}: {numbers}")
                        
                        # Typical IndyCar format: S1, S2, LAP_TIME, [PI_TO_PO]
                        # We need to identify which number is the actual lap time
                        
                        # First, identify valid lap time candidates (between 65-150 seconds)
                        valid_lap_times = [float(n) for n in numbers if 65.0 <= float(n) <= 150.0]
                        
                        # If we found valid lap times
                        if valid_lap_times:
                            lap_time = min(valid_lap_times)  # Use the fastest valid time
                            
                            # Store in our lap data dictionary
                            if lap not in lap_data or lap_time < lap_data[lap][3]:
                                lap_data[lap] = (car_number, driver_name, lap, lap_time)
                                if debug_mode:
                                    print(f"Added lap {lap}: {lap_time:.4f} seconds (valid lap time)")
                        # If no valid lap times found, try a more lenient approach
                        elif any(40.0 <= float(n) <= 65.0 for n in numbers):
                            # These are suspicious times - might be bad data or PI_TO_PO
                            # For now, let's flag them but don't include them
                            if debug_mode:
                                print(f"Suspicious lap time for lap {lap}: likely PI_TO_PO or other data")
                        else:
                            # No valid data found for this lap
                            if debug_mode:
                                print(f"No valid lap time found for lap {lap}")
            
            # If we didn't find any lap times on a page where we expected to find the driver,
            # we should reset the capture flag
            if capture and not lap_found_on_page:
                if debug_mode:
                    print(f"No lap times found on page {page_num+1} despite driver identifier")
                capture = False

    print(f"Found {len(lap_data)} unique lap times for {driver_name} across {section_count} sections")
    return list(lap_data.values())

# Extract lap times for all three drivers
oward_lap_times = extract_driver_lap_times(reader, "5", "O'Ward, Pato")
rossi_lap_times = extract_driver_lap_times(reader, "7", "Rossi, Alexander")
palou_lap_times = extract_driver_lap_times(reader, "10", "Palou, Alex")

# Combine all lap times
all_lap_times = oward_lap_times + rossi_lap_times + palou_lap_times

# Save to CSV
csv_path_full = os.path.expanduser("~/demos/indycar/indycar-lap-times.csv")
if all_lap_times:
    with open(csv_path_full, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Car", "Driver", "Lap", "T (Time)"])
        writer.writerows(all_lap_times)

    print(f"✅ Saved {len(all_lap_times)} lap times to {csv_path_full}")
    print(f"O'Ward: {len(oward_lap_times)} laps, Rossi: {len(rossi_lap_times)} laps, Palou: {len(palou_lap_times)} laps")
else:
    print("⚠️ No lap times found. Check the PDF format and ensure the driver names match exactly.")