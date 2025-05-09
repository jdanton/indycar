# IndyCar Python Project

## Description
A Python-based data analysis tool for IndyCar racing statistics and performance metrics. Indycar releases race timing data in PDF format, that can be challenging to parse. This code parses it. This example is from the 2023 GMR Grand Prix, but it should work for any race.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/indycar.git

# Navigate to the project directory
cd indycar

# Set up a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt

# Run the main analysis script
python main.py

# Or import the modules in your own scripts
import indycar