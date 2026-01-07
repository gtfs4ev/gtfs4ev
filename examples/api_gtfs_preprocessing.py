# coding: utf-8

"""
A minimal commented Python API example demonstrating the main features of the
GTFSManager class.

This script performs the following steps:
1. Load a GTFS feed and check its data consistency.
2. Clean the dataset automatically if inconsistencies are found.
3. Filter services and agencies, then export the cleaned GTFS feed.
4. Trim trip shapes to terminal stop locations.
5. Add idle times at terminals and intermediate stops.
6. Display general indicators and trip statistics

Expected input/output structure:
- A GTFS data directory (e.g., "data/sample_GTFS/")
- An output directory for processed GTFS data, reports, and maps (e.g., "results/")
"""

import os

from gtfs4ev.core.gtfsmanager import GTFSManager

# Configuration
# ------------------------------------------------------------------------------

GTFS_DATA_FOLDER = "data/sample_GTFS"
OUTPUT_FOLDER = "results/api_gtfs_preprocessing"

# Create the output folder if it does not exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 1. Load and check GTFS data
# ------------------------------------------------------------------------------

# Instantiate the GTFS manager
gtfs = GTFSManager(GTFS_DATA_FOLDER)

# Check GTFS data consistency
is_consistent = gtfs.check_all()

# 2. Clean GTFS data if needed
# ------------------------------------------------------------------------------

if not is_consistent:
    gtfs.clean_all()

# 3. Filter services and agencies
# ------------------------------------------------------------------------------

# Example: remove a specific service (e.g. weekend service)
gtfs.filter_services(service_id="WEEKEND", clean_all=True)

# Example: remove a specific agency (only one agency in the sample data)
#gtfs.filter_agency(agency_id="UON", clean_all=True)

# 4. Trim trip shapes to terminal stop locations
# ------------------------------------------------------------------------------

# Ensure that trip shapes start and end at the terminal stops
gtfs.trim_tripshapes_to_terminal_locations()

# 5. Add idle times to trips
# ------------------------------------------------------------------------------

# Add idle time at trip terminals (split between first and last stop)
gtfs.add_idle_time_terminals(mean_idle_time_s=300,std_idle_time_s=60)

# Add dwell time at intermediate stops
gtfs.add_idle_time_stops(mean_idle_time_s=30,std_idle_time_s=10)

# Export the resulting filtered GTFS feed for later use withour pre-processing again
gtfs.export_to_csv(os.path.join(OUTPUT_FOLDER, "gtfs_modified"))

# 6. Display indicators and compute statistics
# ------------------------------------------------------------------------------

# Print general GTFS indicators to the console
gtfs.show_general_info()

# Compute trip-level statistics
trip_stats = gtfs.trip_statistics()

print("\nINFO \t Trip statistics:")
for key, value in trip_stats.items():
    print(f"\t - {key}: {value}")

# Export a summary report
gtfs.generate_summary_report(filepath=os.path.join(OUTPUT_FOLDER, "gtfs_summary_report.txt"))