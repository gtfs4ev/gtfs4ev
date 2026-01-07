# coding: utf-8

"""
A minimal commented Python API example demonstrating the analysis of
photovoltaic (PV) production and EV-PV synergies using aggregated charging load data.

This script performs the following steps:
1. Load the aggregated EV charging load curve (output from a fleet charging simulation).
2. Define and compute PV production for a given location and PV system configuration.
3. Analyze complementarity and synergy metrics between PV production and EV charging demand.
4. Export the results for further analysis or visualization.

Expected input/output structure:
- Input: aggregated charging load curve CSV file (e.g., from a previous simulation)
- Output: PV production and EV-PV synergy metrics CSV files in the specified output directory
"""

import os
import pandas as pd

from gtfs4ev.analysis.pvsimulator import PVSimulator
from gtfs4ev.analysis.evpvsynergies import EVPVSynergies

# Configuration
# ------------------------------------------------------------------------------

LOAD_CURVE_FILE = "results/api_basic_simulation/charging_load_curve.csv"
OUTPUT_FOLDER = "results/api_ex_post_pv"

# Create the output folder if it does not exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Load aggregated EV charging load curve 
# ------------------------------------------------------------------------------

load_curve = pd.read_csv(LOAD_CURVE_FILE)

# ------------------------------------------------------------------------------
# 2. Define PV system and compute PV production
# ------------------------------------------------------------------------------

pv = PVSimulator(
    environment={
        "latitude": 0.17094549,
        "longitude": 37.9039685,
        "year": 2020,
    },
    pv_module={
        "efficiency": 0.22,
        "temperature_coefficient": -0.004,
    },
    installation={
        "type": "rooftop",  # Options: 'rooftop' or 'groundmounted_fixed'
        "system_losses": 0.14,
    }
)

pv.compute_pv_production()

# Save PV production results
pv_output_file = os.path.join(OUTPUT_FOLDER, "PV_production.csv")
pv.results.to_csv(pv_output_file, index=True)

# ------------------------------------------------------------------------------
# 3. Analyze EV-PV synergies using the load curve and PV production
# ------------------------------------------------------------------------------

# Specify PV system capacity in MW for scaling
pv_capacity_MW = 10

evpv = EVPVSynergies(pv=pv, load_curve=load_curve, pv_capacity_MW=pv_capacity_MW)

# Calculate daily synergy metrics for a selected period (e.g., first 3 days of January)
synergy_metrics = evpv.daily_metrics(start_date="01-01", end_date="01-03")

# Save synergy metrics results
synergy_output_file = os.path.join(OUTPUT_FOLDER, "EVPVSynergies.csv")
synergy_metrics.to_csv(synergy_output_file, index=True)