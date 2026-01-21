# coding: utf-8

"""
A minimal commented Python API example demonstrating how to calculate CO2 emission reductions
and diesel fuel savings from replacing diesel vehicles with electric vehicles, based on
fleet operation simulation results.

This script performs the following steps:
1. Load fleet operation data from a CSV file (output from a mobility simulation).
2. Instantiate and configure the CO2EmissionSavings calculator with parameters.
3. Compute CO2 and diesel savings per vehicle.
4. Export the results to a CSV file.
5. Print summary statistics for emission reductions and diesel savings.

Expected input/output structure:
- Input: fleet operation CSV file with vehicle distances and repetitions.
- Output: CSV file with CO2 and diesel savings per vehicle.
"""

import os

from gtfs4ev.analysis.co2savings import CO2Savings  

# Configuration
# ------------------------------------------------------------------------------

INPUT_FILE = "results/api_basic_simulation/fleet_operation.csv"  # Adjust path to your input CSV
OUTPUT_FOLDER = "results/api_ex_post_co2savings"

# Create output folder if it does not exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Instantiate the CO2Savings calculator with relevant parameters
# ------------------------------------------------------------------------------

calculator = CO2Savings(
    input_file=INPUT_FILE,
    active_working_days=260,             # Number of active working days per year 
    ev_consumption=0.39,                 # EV consumption (kWh/km)
    charging_efficiency=0.9,             # Charging efficiency
    electricity_co2_intensity=0.1,      # CO2 intensity of electricity (kgCO2/kWh)
    diesel_consumption=0.1,              # Diesel consumption (L/km)
    diesel_co2_intensity=2.7             # CO2 intensity of diesel fuel (kgCO2/L)
)

# ------------------------------------------------------------------------------
# 2. Compute CO2 emission reductions and diesel savings
# ------------------------------------------------------------------------------

calculator.compute_savings()

# ------------------------------------------------------------------------------
# 3. Save results to CSV file
# ------------------------------------------------------------------------------

output_path = os.path.join(OUTPUT_FOLDER, "co2_diesel_savings.csv")
calculator.save_results(output_path)

# ------------------------------------------------------------------------------
# 4. Print summary statistics
# ------------------------------------------------------------------------------

calculator.print_summary()