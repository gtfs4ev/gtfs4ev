# coding: utf-8

"""
A minimal commented Python API example demonstrating how to calculate
economic fuel savings from replacing diesel vehicles with electric vehicles,
based on fleet operation simulation results.

This script performs the following steps:
1. Load fleet operation data from a CSV file (output from a mobility simulation).
2. Instantiate and configure the EconomicSavings calculator with parameters.
3. Compute economic savings per vehicle.
4. Export the results to a CSV file.
5. Print summary statistics for economic savings.

Expected input/output structure:
- Input: fleet operation CSV file with vehicle distances and repetitions.
- Output: CSV file with economic savings per vehicle (USD).
"""

import os

from gtfs4ev.analysis.costsavings import CostSavings

# Configuration
# ------------------------------------------------------------------------------

INPUT_FILE = "results/api_basic_simulation/fleet_operation.csv"  # Adjust path to your input CSV
OUTPUT_FOLDER = "results/api_ex_post_costsavings"

# Create output folder if it does not exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Instantiate the EconomicSavings calculator with relevant parameters
# ------------------------------------------------------------------------------

calculator = CostSavings(
    input_file=INPUT_FILE,
    active_working_days=260,      # Number of active working days per year
    ev_consumption=0.39,          # EV consumption (kWh/km)
    charging_efficiency=0.9,      # Charging efficiency
    electricity_price=0.30,       # Electricity price (USD/kWh)
    diesel_consumption=0.1,       # Diesel consumption (L/km)
    diesel_price=1.4              # Diesel price (USD/L)
)

# ------------------------------------------------------------------------------
# 2. Compute economic savings
# ------------------------------------------------------------------------------

calculator.compute_savings()

# ------------------------------------------------------------------------------
# 3. Save results to CSV file
# ------------------------------------------------------------------------------

output_path = os.path.join(OUTPUT_FOLDER, "economic_savings.csv")
calculator.save_results(output_path)

# ------------------------------------------------------------------------------
# 4. Print summary statistics
# ------------------------------------------------------------------------------

calculator.print_summary()