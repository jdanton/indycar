import re
from PyPDF2 import PdfReader
import csv
import os

# Path to the PDF file
pdf_path = "~/Desktop/indycar-sectionresults-race.pdf"

# Check if the PDF exists
if not os.path.exists(pdf_path):
    print(f"Error: PDF file not found at {pdf_path}")
    exit(1)

reader = PdfReader(pdf_path)
print(f"PDF loaded successfully with {len(reader.pages)} pages")

# Function to extract lap times for a given driver (with better boundaries)
def extract_driver_lap_times(reader, car_number, driver_name):
    lap_data = {}  # Use dictionary to handle duplicate lap numbers
    capture = False
    section_count = 0
    current_section = None

    possible_identifiers = [
        f"Section Data for Car {car_number} - {driver_name}",
        f"Car {car_number} - {driver_name}",
        f"{car_number} - {driver_name}"
    ]

    print(f"Looking for data for Car {car_number} - {driver_name}")

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue

        # Check for a new section starting
        if any(pid in text for pid in possible_identifiers):
            # If we find a new section identifier, check if it's a different section
            for line in text.split('\n'):
                if any(pid in line for pid in possible_identifiers):
                    # Found the section header line
                    if line != current_section:
                        # This is a new section, start fresh
                        if capture:
                            print(f"Found new section for {driver_name}, ending previous section")
                            section_count += 1
                        current_section = line
                        print(f"Found {driver_name} section on page {page_num + 1}: {current_section}")
                        capture = True
                        break

        if capture:
            lines = text.split('\n')

            for line in lines:
                line = line.strip()

                # Match lines like "22T 5.1425 ... 81.2100"
                match = re.match(r'^(\d+)T\s+(.*)$', line)
                if match:
                    lap = int(match.group(1))
                    numbers = match.group(2).strip().split()
                    try:
                        time = float(numbers[-1])  # Last number is total lap time
                        
                        # Filter out obviously invalid times (< 20 or > 150 seconds)
                        if 20.0 <= time <= 150.0:
                            # Only keep the first occurrence of each lap number
                            if lap not in lap_data:
                                lap_data[lap] = (car_number, driver_name, lap, time)
                        else:
                            print(f"Skipping suspicious lap time: Lap {lap}, Time {time}")
                    except (IndexError, ValueError):
                        continue

        # Stop capturing if a section for a different driver starts
        for other_car in range(1, 34):  # IndyCar typically has car numbers 1-33
            if other_car != int(car_number):
                # Make the pattern more specific with word boundaries
                other_car_pattern = f"Section Data for Car {other_car} - "
                # Check if it's truly a different car section and not part of our car number
                if other_car_pattern in text and f"Section Data for Car {car_number} -" not in text:
                    print(f"Found data for Car {other_car}, ending capture for {driver_name}")
                    capture = False
                    break

    print(f"Found {len(lap_data)} unique lap times for {driver_name} across {section_count} sections")
    return list(lap_data.values())

# Extract lap times for all three drivers
oward_lap_times = extract_driver_lap_times(reader, "5", "O'Ward, Pato")
rossi_lap_times = extract_driver_lap_times(reader, "7", "Rossi, Alexander")
palou_lap_times = extract_driver_lap_times(reader, "10", "Palou, Alex")

# Combine all lap times
all_lap_times = oward_lap_times + rossi_lap_times + palou_lap_times

# Save to CSV
csv_path_full = "~/Desktop/indycar-lap-times.csv"
if all_lap_times:
    with open(csv_path_full, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Car", "Driver", "Lap", "T (Time)"])
        writer.writerows(all_lap_times)

    print(f"✅ Saved {len(all_lap_times)} lap times to {csv_path_full}")
    print(f"O'Ward: {len(oward_lap_times)} laps, Rossi: {len(rossi_lap_times)} laps, Palou: {len(palou_lap_times)} laps")
else:
    print("⚠️ No lap times found. Check the PDF format and ensure the driver names match exactly.")