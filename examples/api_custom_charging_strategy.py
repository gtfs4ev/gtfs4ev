# coding: utf-8

"""
This script demonstrates the definition and use of user-defined custom 
charging strategy.

About building custom strategies
--------------------------------
GTFS4EV allows charging strategies to be provided in two ways:
1. As built-in strategies, referenced by string identifiers (e.g. "depot_night")
2. As user-defined Python callables implementing custom charging logic

When a callable charging strategy is provided, the ChargingSimulator will:
- Call the function once per vehicle
- Pass the vehicle travel sequence
- Pass the remaining energy need for the vehicle
- Pass a reference to the ChargingSimulator instance itself

A custom charging strategy must:
- Accept the following arguments:
    * travel_sequence (list of dict)
    * remaining_need_kWh (float)
    * simulator (ChargingSimulator)

  Example of a travel_sequence element:
    {
        "status": "at_terminal",
        "start_time": "16:45:00",
        "duration_h": 0.25,
        "stop_id": "STOP_123"
    }

- Return a list of charging event dictionaries.

  Example of a charging event:
    {
        "start_time": "16:45:00",
        "end_time": "17:00:00",
        "location": "terminal",
        "stop_id": "STOP_123",
        "power": 150,
        "energy_charged_kWh": 37.5
    }

This design allows users to implement arbitrary charging behaviors
(time-based, location-based, stochastic, PV-aware, etc.).
--------------------------------

This script performs the following steps:
1. Load and simulate vehicle fleet operations from a GTFS feed
2. Define a custom charging strategy as a standalone Python function
3. Run the charging simulation using both built-in and custom strategies
4. Export basic charging results and load curves

Expected input/output structure:
- A GTFS data directory (e.g., "data/sample_GTFS/")
- An output directory for simulation results (e.g., "results/")
"""

import os
from datetime import datetime, timedelta

from gtfs4ev.core.gtfsmanager import GTFSManager
from gtfs4ev.core.fleetsimulator import FleetSimulator
from gtfs4ev.core.chargingsimulator import ChargingSimulator

# Configuration
# ------------------------------------------------------------------------------

GTFS_DATA_FOLDER = "data/sample_GTFS"
OUTPUT_FOLDER = "results/api_custom_charging_strategy"

# Create the output folder if it does not exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Load data and run fleet simulation 
# ------------------------------------------------------------------------------

gtfs = GTFSManager(gtfs_datafolder=GTFS_DATA_FOLDER)

fleet_sim = FleetSimulator(gtfs_manager=gtfs)
fleet_sim.compute_fleet_operation()

# ------------------------------------------------------------------------------
# 2. Charging simulation
# ------------------------------------------------------------------------------

# --- User-defined custom charging strategy ------------------------------------

def evening_terminal_charging(
    travel_sequence,
    remaining_need_kWh,
    simulator,
    min_hour=16,
    **kwargs
):
    """
    Custom charging strategy example.

    Strategy logic:
    - Charging is only allowed at terminal stops
    - Charging is only allowed after a given hour (default: 16:00)
    - Charging continues until the vehicle energy need is satisfied
    """

    # List that will store all charging events created by this strategy
    charging_events = []

    # Local copy of remaining energy need, updated as charging occurs
    remaining = remaining_need_kWh

    # Iterate over the vehicle travel sequence in chronological order
    for event in travel_sequence:

        # Stop if the vehicle energy need has already been fully satisfied
        if remaining <= 0:
            break

        # Only consider terminal stops for this strategy
        if event["status"] != "at_terminal":
            continue

        # Convert the event start time to a datetime object
        start_dt = datetime.strptime(event["start_time"], "%H:%M:%S")

        # Skip terminal stops occurring before the allowed charging hour
        if start_dt.hour < min_hour:
            continue

        # Retrieve a charging power (kW) based on terminal charger availability
        # This uses the simulator configuration and random sampling if needed
        power = simulator._get_random_charging_power("terminal")

        # Duration of the stop in hours
        duration_h = event["duration_h"]

        # Maximum energy that could be charged during this stop
        max_energy = power * duration_h

        # Actual charged energy is limited by the remaining vehicle need
        energy = min(max_energy, remaining)

        # Compute the end time of the charging event
        end_dt = start_dt + timedelta(hours=energy / power)

        # Append the charging event to the result list
        charging_events.append({
            "start_time": start_dt.strftime("%H:%M:%S"),
            "end_time": end_dt.strftime("%H:%M:%S"),
            "location": "terminal",
            "stop_id": event["stop_id"],
            "power": power,
            "energy_charged_kWh": energy
        })

        # Update remaining energy need
        remaining -= energy

    # The simulator will aggregate the returned charging events
    # across all strategies and vehicles
    return charging_events

# --- Charging simulator configuration -----------------------------------------

charging = ChargingSimulator(
    fleet_sim=fleet_sim,
    energy_consumption_kWh_per_km=0.39,
    security_driving_distance_km=0,
    charging_powers_kW={
        "depot": [[22, 0.5], [50, 0.5]],
        "terminal": [[300, 1.0]]
    }
)

# Compute charging schedules using both built-in and custom strategies
charging.compute_charging_schedule(
    charging_strategies=[
        evening_terminal_charging,  # Custom user-defined strategy
        "depot_night"             # Built-in overnight depot charging
    ],
    depot_travel_time_min=[30, 15]
)

# ------------------------------------------------------------------------------
# 3. Results export 
# ------------------------------------------------------------------------------

# Export the charging schedule per vehicle
charging.charging_schedule_pervehicle.to_csv(f"{OUTPUT_FOLDER}/charging_schedules_per_vehicle.csv", index=False)

# Compute and export the aggregated charging load curve
load_curve = charging.compute_charging_load_curve(time_step_s=60)
load_curve.to_csv(f"{OUTPUT_FOLDER}/charging_load_curve.csv", index=False)