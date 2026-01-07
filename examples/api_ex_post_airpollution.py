# coding: utf-8

"""
A minimal commented Python API example demonstrating how to calculate
population exposure to traffic-related air pollution (TRAP) based on
fleet operation simulation results.

This script performs the following steps:
1. Load fleet operation data, travel sequences, and population raster.
2. Instantiate and configure the AirPollutionExposure calculator.
3. Compute local emissions, distance-weighted exposure, and population exposure.
4. Export raster outputs.

Expected input/output structure:
- Input:
    - Fleet operation CSV
    - Travel sequences CSV
    - Population raster (.tif)
- Output:
    - Raster files stored in the specified output folder:
        * Local emission index:
          A rasterized proxy for traffic emissions, proportional to the
          vehicle-kilometers traveled (VKM) on road segments intersecting
          each pixel.

        * Distance-weighted exposure index:
          A spatially smoothed version of the local emission index that
          accounts for pollutant dispersion using an exponential decay
          with distance from emission sources.

        * Population-weighted exposure index (normalized):
          The distance-weighted exposure multiplied by population density,
          representing relative population exposure to traffic-related
          air pollution across space.
"""

import os

from gtfs4ev.analysis.airpollution import AirPollutionExposure

# Configuration
# ------------------------------------------------------------------------------

INPUT_FLEET_OPERATION = "results/api_basic_simulation/fleet_operation.csv"
INPUT_TRAVEL_SEQUENCES = "results/api_basic_simulation/trip_travel_sequences.csv"
POPULATION_RASTER = "data/population.tif"

OUTPUT_FOLDER = "results/api_ex_post_airpollution"

# Create output folder if it does not exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Instantiate the AirPollutionExposure calculator with parameters
# ------------------------------------------------------------------------------

calculator = AirPollutionExposure(
    input_fleet_operation=INPUT_FLEET_OPERATION,
    input_travel_sequences=INPUT_TRAVEL_SEQUENCES,
    population_raster=POPULATION_RASTER,
    buffer_distance=300,     # Maximum influence distance (m)
    decay_rate=0.0064        # Exponential decay rate (per meter)
)

# ------------------------------------------------------------------------------
# 2. Compute air pollution exposure
# ------------------------------------------------------------------------------

calculator.compute_exposure(
    output_local_emission_index=os.path.join(
        OUTPUT_FOLDER, "air_pollution_local_emission_index.tif"
    ),
    output_distance_weighted_index=os.path.join(
        OUTPUT_FOLDER, "air_pollution_distance_weighted_index.tif"
    ),
    output_population_exposure=os.path.join(
        OUTPUT_FOLDER, "air_pollution_population_exposure.tif"
    )
)