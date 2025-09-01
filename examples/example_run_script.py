# coding: utf-8

"""
A Python script illustrating the basic usage of the GTFS4EV model for simulating and analyzing vehicle fleet operations.

This script demonstrates how to:
1. Load, clean, and filter GTFS data.
2. Simulate the operation of a vehicle fleet for a set of trips.
3. Optionally, visualize and store results of the fleet simulation.

Ensure the following structure for the input data:
- GTFS data folder (e.g., "input/GTFS_Nairobi")
- Output directories for results (e.g., "output/")
"""

import sys
import os
import time
import json
import pandas as pd
from shapely.ops import substring

# Adding the parent directory to the Python path for access to the GTFS4EV module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

# Import relevant classes from the GTFS4EV package
from gtfs4ev.gtfsmanager import GTFSManager
from gtfs4ev.tripsimulator import TripSimulator
from gtfs4ev.fleetsimulator import FleetSimulator
from gtfs4ev.chargingsimulator import ChargingSimulator
from gtfs4ev.pvsimulator import PVSimulator
from gtfs4ev.evpvsynergies import EVPVSynergies

if __name__ == "__main__":
    #################################################################################
    ########### STEP 1: Load, clean, and filter (optional) the GTFS data ############
    #################################################################################

    # 1.1) Load GTFS data from the specified folder
    gtfs = GTFSManager(gtfs_datafolder="input/GTFS_Nairobi")

    # 1.2) Check the consistency of the GTFS data, and clean it if necessary
    # This step ensures that the data is valid for simulation
    if not gtfs.check_all():
        print("INFO \t Data is inconsistent, cleaning data...")
        gtfs.clean_all()

    # 1.3) OPTIONAL - Data filtering and manipulation (uncomment to enable)
    # Example 1: Filter for services that run daily (e.g., remove weekend-only services)
    # gtfs.filter_services(service_id="DAILY") # Keep only trips operating under the specified service schedule.
    
    # Example 2: Filter out agencies that are not part of the bus fleet (e.g., exclude ferries)
    # gtfs.filter_agency(agency_id="UON") # Removes all data related to the specified agency.
    
    # Example 3: Add additional idle time at trip terminals (optional based on specific fleet simulation needs)
    gtfs.add_idle_time_terminals(mean_idle_time_s = 60, std_idle_time_s = 10)  # Adds idle time at trip terminals
    #gtfs.add_idle_time_stops(mean_idle_time_s = 20, std_idle_time_s = 5)  # Adds idle time at intermediate stops

    # Example 4: Trim tripshapes to make sure their start and end points correspond to the projection of the start (RECOMMENDED)
    # and stop stops locations once projected on the tripshape (needed later to calculate distance between stops)
    gtfs.trim_tripshapes_to_terminal_locations()

    # 1.4) OPTIONAL - Show information and export 
    # Show general information about the GTFS feed (e.g., number of trips, agencies, etc.)
    gtfs.show_general_info()
    gtfs.generate_summary_report("output/GTFS_summary.txt")

    # Export cleaned/filtered GTFS data to GTFS file (usefull to avoid pre-processing everytime)
    #gtfs.export_to_csv("input/GTFS_Nairobi_cleaned")

    # Export a map of a trip or the entire GTFS data (e.g., stops, routes, and trips) as an HTML file 
    # gtfs.generate_network_map("output/GTFS_map_alldata.html")

    # trip_id = "1011F110"
    # gtfs.generate_single_trip_map(trip_id = trip_id, filepath = f"output/GTFS_map_{trip_id}.html", projected = True)

    ###############################################################################
    ############# STEP 2: Simulate the operation of the vehicle fleet ############# 
    ###############################################################################

    # 2.1) Initialize the FleetSimulator with the GTFS data and a list of trip IDs to simulate
    # If no trip IDs are specified, all trips in the GTFS feed will be simulated
    fleet_sim = FleetSimulator(gtfs_manager=gtfs, trip_ids=["1011F110", "1107D110", "10114111"])
    # If you want to simulate all trips, uncomment the line below:
    #fleet_sim = FleetSimulator(gtfs_manager=gtfs)

    # 2.2) Compute the fleet operation for the selected trips
    # Use multiprocessing to speed up the simulation (set to False if you want a single-threaded computation)
    fleet_sim.compute_fleet_operation(use_multiprocessing=False)  # Set use_multiprocessing=True for parallel processing
    fleet_sim.fleet_operation.to_csv(f"output/Mobility_fleet_operation.csv", index=False)
    fleet_sim.trip_travel_sequences.to_csv(f"output/Mobility_trip_travel_sequences.csv", index=False)

    # # 2.3) OPTIONAL - Map the spatio-temporal movement of vehicles 
    # # Warning : this might take a very long time and a lot of disk space if many trips are simulated
    # df = fleet_sim.get_fleet_trajectory(time_step=120)
    # df.to_csv(f"output/Mobility_fleet_trajectory.csv", index=True)
    # fleet_sim.generate_fleet_trajectory_map(fleet_trajectory=df, filepath=f"output/Mobility_fleet_trajectory_map.html")

    ###############################################################################
    ########################## STEP 3: Charging Scenario ########################## 
    ###############################################################################

    # 3.1) Initialize the ChargingSimulator object with basic parameters 
    # Available charging powers at each charging location must be specified as a list of [power, share] values

    cs = ChargingSimulator(
        fleet_sim = fleet_sim,
        energy_consumption_kWh_per_km = 0.39,
        battery_capacity_kWh = 50,
        security_driving_distance_km = 0,
        charging_powers_kW = {
            "depot": [[11,1.0], [22,0.0]],
            "terminal": [[1000,1.0]],
            "stop": [[200, 1.0]]
        }
    )

    # 3.2) Compute the charging schedule by applying a sequence of charging strategies.
    # The strategies are applied in the order provided until each vehicle is fully charged or no further strategy is available.
    # Note: Some strategies require additional parameters, which must be specified accordingly.

    cs.compute_charging_schedule(["terminal_random", "depot_night"], 
        charge_probability_terminal=0.5,
        charge_probability_stop=0.1,
        depot_travel_time_min=[30,15])

    # 3.3) Export the charging sequence (per vehicle and per stop) and map the charging needs
    cs.charging_schedule_pervehicle.to_csv(f"output/Charging_schedule_pervehicle.csv", index=False)
    cs.charging_schedule_perstop.to_csv(f"output/Charging_schedule_perstop.csv", index=False)
    cs.generate_charging_map(stop_charging_schedule = cs.charging_schedule_perstop, filepath=f"output/Charging_stop_map.html")

    # 3.4) Generate and export the aggregated load curve
    load_curve = cs.compute_charging_load_curve(time_step_s = 5)
    load_curve.to_csv(f"output/Charging_load_curve.csv", index=False)

    ###############################################################################
    ############################ STEP 4: PV Simulation ############################ 
    ###############################################################################

    pv = PVSimulator(
        environment={
            'latitude': 0.17094549,  
            'longitude': 37.9039685,  
            'year': 2020  
        }, 
        pv_module={
            'efficiency': 0.22,
            'temperature_coefficient': -0.004  
        }, 
        installation={
            'type': 'rooftop',  # Options: 'rooftop' or 'groundmounted_fixed'
            'system_losses': 0.14
        }
    )

    pv.compute_pv_production() # Calculate PV production based on the defined parameters
    pv.results.to_csv("output/PV_production.csv") # Save PV production data

    ###############################################################################
    ######################## STEP 5: EV-PV Complementarity ######################## 
    ###############################################################################

    evpv = EVPVSynergies(pv=pv, load_curve=load_curve, pv_capacity_MW=10)

    # Calculate daily synergy metrics for the first week of January, adjusting recompute_probability as needed
    synergy_metrics = evpv.daily_metrics("01-01", "01-03")
    synergy_metrics.to_csv("output/EVPVSynergies.csv") # Save synergy metrics data
    


