# coding: utf-8

"""
A minimal commented Python API example demonstrating a complete GTFS4EV workflow
for electric bus fleet simulation and charging analysis.

This script performs the following steps:
1. Load, validate, and clean a GTFS feed if needed.
2. Simulate vehicle fleet operations for all scheduled trips.
3. Simulate electric vehicle charging under predefined depot and terminal charging strategies.
4. Export some basic results and visualisation (Optional advanced outputs commented at the end)

Expected input/output structure:
- A GTFS data directory (e.g., "data/sample_GTFS/")
- An output directory for simulation results and visualizations (e.g., "results/")
"""

import os

from gtfs4ev.core.gtfsmanager import GTFSManager
from gtfs4ev.core.fleetsimulator import FleetSimulator
from gtfs4ev.core.chargingsimulator import ChargingSimulator

# Configuration
# ------------------------------------------------------------------------------

GTFS_DATA_FOLDER = "data/sample_GTFS"
OUTPUT_FOLDER = "results/api_basic_simulation"

# Create the output folder if it does not exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 1. Load and prepare GTFS data
# ------------------------------------------------------------------------------

# Initialize GTFS manager
gtfs = GTFSManager(gtfs_datafolder=GTFS_DATA_FOLDER)

# Validate GTFS feed and clean it if issues are detected
if not gtfs.check_all():
    gtfs.clean_all()

# 2. Fleet operation simulation
# ------------------------------------------------------------------------------

# Initialize the fleet simulator 
fleet_sim = FleetSimulator(gtfs_manager=gtfs)

# Optional: restrict the simulation to a subset of trips (useful for testing of large GTFS datasets)
# fleet_sim = FleetSimulator(gtfs_manager=gtfs, trip_ids=["1107D110", "1107D111"])

# Run the fleet operation simulation for all selected trips
# Multiprocessing is disabled by default
fleet_sim.compute_fleet_operation(use_multiprocessing=False)

# ------------------------------------------------------------------------------
# 3. Charging simulation
# ------------------------------------------------------------------------------

# Define vehicle energy parameters and available charging infrastructure
charging = ChargingSimulator(
    fleet_sim=fleet_sim,                     # Fleet operation results used as input
    energy_consumption_kWh_per_km=0.39,      # Average vehicle energy consumption per kilometer
    security_driving_distance_km=0,          # Extra distance reserve to keep in the battery
    battery_capacity_kWh=50,                 # Usable battery capacity of each vehicle
    charging_powers_kW={
        # Charging power levels (kW) and their relative availability/probability
        "depot": [[11, 0.5], [22, 0.5]],     # Depot chargers: 50% at 11 kW, 50% at 22 kW
        "terminal": [[150, 1.0]]             # Terminal chargers: 100% at 150 kW
    }
)

# Compute charging schedules based on the selected charging strategies
charging.compute_charging_schedule(
    charging_strategies=["terminal_random", "depot_night"],  # Opportunity charging at terminals during service + overnight charging at the depot
    charge_probability_terminal=0.5,                         # Probability of initiating a charge upon arrival at a terminal
    depot_travel_time_min=[30, 15]                           # [mean, std] travel time (minutes) from end of service to the depot
)

# ------------------------------------------------------------------------------
# 4. Results export and visualization
# ------------------------------------------------------------------------------

# --- Basic outputs (recommended) ---

# Export the charging schedule per vehicle
charging.charging_schedule_pervehicle.to_csv(f"{OUTPUT_FOLDER}/charging_schedules_per_vehicle.csv", index=False)

# Compute and export the aggregated charging load curve for all vehicles
load_curve = charging.compute_charging_load_curve(time_step_s=60)
load_curve.to_csv(f"{OUTPUT_FOLDER}/charging_load_curve.csv", index=False)

# Generate an interactive HTML map of the full GTFS network (routes, stops, trips)
gtfs.generate_network_map(f"{OUTPUT_FOLDER}/GTFS_map_alldata.html")

# --- Optional outputs and visualizations (uncomment to enable) ---

# Export detailed fleet operation results 
# fleet_sim.fleet_operation.to_csv(f"{OUTPUT_FOLDER}/fleet_operation.csv", index=False)

# Export detailed trip travel sequences (stop-by-stop vehicle movements)
# fleet_sim.trip_travel_sequences.to_csv(f"{OUTPUT_FOLDER}/trip_travel_sequences.csv", index=False)

# Export charging schedules per stop / charging location
# charging.charging_schedule_perstop.to_csv(f"{OUTPUT_FOLDER}/charging_schedules_per_stop.csv", index=False)

# Generate a map of charging activity at stops and terminals
# charging.generate_charging_map(stop_charging_schedule=charging.charging_schedule_perstop, filepath=f"{OUTPUT_FOLDER}/charging_stop_map.html")

# Generate a spatio-temporal fleet trajectory (can be large for full GTFS feeds)
# fleet_trajectory = fleet_sim.get_fleet_trajectory(time_step=120)
# fleet_trajectory.to_csv(f"{OUTPUT_FOLDER}/fleet_trajectory.csv", index=True)
# fleet_sim.generate_fleet_trajectory_map(fleet_trajectory=fleet_trajectory, filepath=f"{OUTPUT_FOLDER}/fleet_trajectory_map.html")
