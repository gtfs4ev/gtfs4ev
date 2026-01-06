# coding: utf-8

import sys
import os
import importlib.util
import time
import json
import pandas as pd
from shapely.ops import substring

# Import relevant classes from the GTFS4EV package
from gtfs4ev.gtfsmanager import GTFSManager
from gtfs4ev.tripsimulator import TripSimulator
from gtfs4ev.fleetsimulator import FleetSimulator
from gtfs4ev.chargingsimulator import ChargingSimulator
from gtfs4ev.pvsimulator import PVSimulator
from gtfs4ev.evpvsynergies import EVPVSynergies

# Std redirection

class Tee:
    """A class to duplicate stdout to both a file and the terminal."""
    def __init__(self, filename):
        self.terminal = sys.stdout  # Keep reference to original stdout
        self.log = open(filename, mode="w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)  # Print to terminal
        self.log.write(message)  # Save to file

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Main

def main():
    # Welcome message
    print("------------------------------------------------")
    print("         Welcome to the GTFS4EV Model!")
    print("------------------------------------------------")
    
    print("------------------------------------------------")
    print("Make sure to configure your case study in the config file.")
    print("Let's electrify your public transport fleet!")
    print("------------------------------------------------")

    print("")

    config_path = input("Enter the path to the python configuration file: ")  # e.g., '/path/to/config.py'
    
    # Dynamically load the config
    config = load_config(config_path) 

    sys.stdout = Tee(f"{config.output_folder}/output.log")  # Capture all prints in a log file   

    # Run the simulation using the loaded config module
    run_simulation(config)

    sys.stdout = sys.__stdout__  # Reset stdout after script ends

# Run the simulation

def run_simulation(config):

    # Welcome message

    print("")
    print("------------------------------------------------")
    print(f"Starting the run of the case study")
    print(f"Results are stored in the following folder: {config.output_folder}")
    print("------------------------------------------------")
    print("")

    # Start time

    start_time = time.time()

    #################################################################################
    ########### STEP 1: Load, clean, and filter (optional) the GTFS data ############
    #################################################################################

    gtfs = GTFSManager(gtfs_datafolder=config.gtfs_datafolder)
    
    if config.clean_gtfs_data:
        if not gtfs.check_all():
            print("INFO \t Data is inconsistent, cleaning data...")
            gtfs.clean_all()

    for service_id in config.filter_out_services:
        gtfs.filter_services(service_id=service_id)

    for agency_id in config.filter_out_agencies:
        gtfs.filter_agency(agency_id=agency_id)

    if config.add_idle_time_terminals_s[0] != 0:
        gtfs.add_idle_time_terminals(mean_idle_time_s = config.add_idle_time_terminals_s[0], std_idle_time_s = config.add_idle_time_terminals_s[1])  
    
    if config.add_idle_time_stops_s[0] != 0:
        gtfs.add_idle_time_stops(mean_idle_time_s = config.add_idle_time_stops_s[0], std_idle_time_s = config.add_idle_time_stops_s[1])  

    if config.trim_tripshapes_to_terminal_locations:
        gtfs.trim_tripshapes_to_terminal_locations()

    if config.export_cleaned_gtfs:
        gtfs.export_to_csv(f"{config.output_folder}/GTFS_cleaned")

    gtfs.show_general_info()
    gtfs.generate_summary_report(f"{config.output_folder}/GTFS_summary.txt")

    if config.generate_network_map:
        gtfs.generate_network_map(f"{config.output_folder}/GTFS_map_alldata.html")

    for trip_id in config.generate_map_specific_trips:
        gtfs.generate_single_trip_map(trip_id = trip_id, filepath = f"{config.output_folder}/GTFS_map_{trip_id}.html", projected = config.trim_tripshapes_to_terminal_locations)

    ###############################################################################
    ############# STEP 2: Simulate the operation of the vehicle fleet ############# 
    ###############################################################################
    fleet_sim = FleetSimulator(gtfs_manager=gtfs, trip_ids=config.trips_to_simulate)
    fleet_sim.compute_fleet_operation(use_multiprocessing=config.use_multiprocessing)  # Set use_multiprocessing=True for parallel processing
    fleet_sim.fleet_operation.to_csv(f"{config.output_folder}/Mobility_fleet_operation.csv", index=False)
    fleet_sim.trip_travel_sequences.to_csv(f"{config.output_folder}/Mobility_trip_travel_sequences.csv", index=False)

    if config.generate_map_fleet_movement:
        if config.trips_to_simulate is not None and len(config.trips_to_simulate) < 5:    
            df = fleet_sim.get_fleet_trajectory(time_step=120)
            df.to_csv(f"{config.output_folder}/Mobility_fleet_trajectory.csv", index=True)
            fleet_sim.generate_fleet_trajectory_map(
                fleet_trajectory=df,
                filepath=f"{config.output_folder}/Mobility_fleet_trajectory_map.html"
            )
        else:
            print(f"\nALERT \t Fleet movement map can not be create. Generation requires fewer than 5 trips. Please reduce 'trips_to_simulate'. \n")

    ###############################################################################
    ########################## STEP 3: Charging Scenario ########################## 
    ###############################################################################

    cs = ChargingSimulator(
        fleet_sim = fleet_sim,
        energy_consumption_kWh_per_km = config.energy_consumption_kWh_per_km,
        security_driving_distance_km = config.security_driving_distance_km,
        charging_powers_kW = config.charging_powers_kW
    )
    cs.compute_charging_schedule(config.charging_strategy_sequence, 
        charge_probability_terminal=config.charge_probability_terminal,
        charge_probability_stop=config.charge_probability_stop,
        depot_travel_time_min=config.depot_travel_time_min)

    cs.charging_schedule_pervehicle.to_csv(f"{config.output_folder}/Charging_schedule_pervehicle.csv", index=False)
    cs.charging_schedule_perstop.to_csv(f"{config.output_folder}/Charging_schedule_perstop.csv", index=False)
    cs.generate_charging_map(stop_charging_schedule = cs.charging_schedule_perstop, filepath=f"{config.output_folder}/Charging_stop_map.html")

    load_curve = cs.compute_charging_load_curve(time_step_s = config.load_curve_timestep_s)
    load_curve.to_csv(f"{config.output_folder}/Charging_load_curve.csv", index=False)

    ###############################################################################
    ############################ STEP 4: PV Simulation ############################ 
    ###############################################################################

    pv = PVSimulator(
        environment={
            'latitude': config.latitude,  
            'longitude': config.longitude,  
            'year': config.year  
        }, 
        pv_module={
            'efficiency': config.module_efficiency,
            'temperature_coefficient': config.temperature_coefficient
        }, 
        installation={
            'type': config.installation_type,  
            'system_losses': config.system_losses
        }
    )

    pv.compute_pv_production() # Calculate PV production based on the defined parameters
    pv.results.to_csv(f"{config.output_folder}/PV_production.csv") # Save PV production data

    ###############################################################################
    ######################## STEP 5: EV-PV Complementarity ######################## 
    ###############################################################################

    evpv = EVPVSynergies(pv=pv, load_curve=load_curve, pv_capacity_MW=config.pv_capacity_MW)
    synergy_metrics = evpv.daily_metrics(config.start_date, config.end_date)
    synergy_metrics.to_csv(f"{config.output_folder}/EVPVSynergies.csv") # Save synergy metrics data

    # End time and message 

    end_time = time.time()

    # Calculate the duration
    duration = end_time - start_time
    minutes = int(duration // 60)  # Get the whole minutes
    seconds = duration % 60         # Get the remaining seconds

    print("")
    print("")
    print("------------------------------------------------")
    print(f"Simulation completed")
    print(f"Elapsed time: : {minutes} minutes and {seconds:.2f} seconds")
    print("------------------------------------------------")

# Helper functions

def load_config(config_path):
    # Ensure the provided config file exists
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Get the module name (e.g., 'config') from the file name (e.g., 'config.py')
    config_name = os.path.splitext(os.path.basename(config_path))[0]

    # Dynamically load the config module
    spec = importlib.util.spec_from_file_location(config_name, config_path)
    config_module = importlib.util.module_from_spec(spec)
    sys.modules[config_name] = config_module
    spec.loader.exec_module(config_module)

    return config_module

if __name__ == "__main__":    
    main()  # Run your main function
