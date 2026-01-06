# coding: utf-8

"""
CO2 Emission Reductions and Diesel Savings from EV Transition
-------------------------------------------------------------

This script calculates the potential CO2 savings and diesel fuel savings
resulting from replacing diesel vehicles with electric vehicles, based on 
the results of the mobility simulation.

INPUT:
    - The CSV file containing the fleet operation as a result of the
    mobility simulation (ie the file containing the columns: vehicle_id,
    travel_sequences, trip_repetitions,	total_distance_km, ...)
    - Some basic parameters (see the "Input Parameters" section)

OUTPUT: A CSV file with estimated CO2 and diesel savings per vehicle.

HOW TO USE:
    1. Modify the file paths and parameters in the "Input Parameters" section.
    2. Run the script using any Python environment with panda installed.
"""
import pandas as pd

#########################################################
########### Input Parameters (TO BE MODIFIED) ###########
#########################################################

# Path to the file containing the mobility simulation
input_file = "C:/Users/dumoulin/Documents/_CODES/gtfs4ev/examples/output/Mobility_fleet_operation.csv"
output_file = 'co2_savings_results.csv'

# Number of days
active_working_days = 260

# Electric energy use 
ev_consumption = 0.39 # EV consumption (kWh/km) - Value should not affect the output
charging_efficiency = 0.9 # Loss during charging process
electricity_co2_intensity = 0.1 # CO2 intensity of the electricity mix (kgCO2/kWh)

# Diesel vehicle
diesel_consumption = 0.1 # Diesel consumption (L/km)
diesel_co2_intensity = 2.7 # Diesel CO2 intensity (kgCO2/L)

#########################################################
###################### Processing #######################
#########################################################

data = pd.read_csv(input_file)

diesel_emissions = diesel_consumption * diesel_co2_intensity
ev_emissions = ev_consumption / charging_efficiency * electricity_co2_intensity

# Total km = distance per trip × number of repetitions per day × number of working days
total_km = data['total_distance_km'] * active_working_days

# Compute emissions and savings
data['emission_reduction_tco2'] = (total_km * (diesel_emissions - ev_emissions)) / 1000  # tonnes CO2
data['diesel_savings_L'] = total_km * diesel_consumption

# Create final dataframe
result_df = data[['vehicle_id', 'trip_id', 'emission_reduction_tco2', 'diesel_savings_L']]

# Save to file
result_df.to_csv(output_file, index=False)

# Print summary stats
avg_emission_reduction = result_df['emission_reduction_tco2'].mean()
total_emission_reduction = result_df['emission_reduction_tco2'].sum()

avg_diesel_savings = result_df['diesel_savings_L'].mean()
total_diesel_savings = result_df['diesel_savings_L'].sum()

print(f"Average emission reduction per vehicle: {avg_emission_reduction:.2f} tCO2")
print(f"Total emission reduction: {total_emission_reduction:.2f} tCO2")

print(f"Average diesel savings per vehicle: {avg_diesel_savings:.2f} L")
print(f"Total diesel savings: {total_diesel_savings:.2f} L")