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
            print(f"Found potential data on page {page_num+1}")
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
    
    print(f"Found {len(lap_data)} unique lap times for {driver_name} across {len(found_sections)} sections")
    return list(lap_data.values())

# Extract lap times for all three drivers
oward_lap_times = extract_driver_lap_times(reader, "5", "O'Ward, Pato")
rossi_lap_times = extract_driver_lap_times(reader, "20", "Rossi, Alexander")
palou_lap_times = extract_driver_lap_times(reader, "10", "Palou, Alex")
lungaard_lap_times = extract_driver_lap_times(reader, "7", "Lundgaard, Christian")

# Combine all lap times
all_lap_times = oward_lap_times + rossi_lap_times + palou_lap_times + lungaard_lap_times

# Save to CSV
csv_path_full = os.path.expanduser("~/demos/indycar/indycar-lap-times.csv")
if all_lap_times:
    with open(csv_path_full, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Car", "Driver", "Lap", "T (Time)"])
        writer.writerows(all_lap_times)

    print(f"✅ Saved {len(all_lap_times)} lap times to {csv_path_full}")
    print(f"O'Ward: {len(oward_lap_times)} laps, Rossi: {len(rossi_lap_times)} laps, Palou: {len(palou_lap_times)} laps, Lungaard: {len(lungaard_lap_times)} laps")
else:
    print("⚠️ No lap times found. Check the PDF format and ensure the driver names match exactly.")