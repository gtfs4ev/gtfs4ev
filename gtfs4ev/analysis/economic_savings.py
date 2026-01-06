# coding: utf-8

"""
Economic Savings from Transition to Electric Vehicles (EVs)
-----------------------------------------------------------

This script calculates the potential economic savings resulting from replacing
diesel vehicles with electric vehicles, based on the results of the mobility 
simulation and basic cost assumptions.

INPUT:
    - The CSV file containing the fleet operation as a result of the
      mobility simulation (i.e., the file containing the columns: vehicle_id,
      travel_sequences, trip_repetitions, total_distance_km, ...)
    - Some basic parameters (see the "Input Parameters" section)

OUTPUT:
    - A CSV file with estimated economic savings per vehicle-trip (in USD)

HOW TO USE:
    1. Modify the file paths and parameters in the "Input Parameters" section.
    2. Run the script using any Python environment with pandas installed.
"""

import pandas as pd

#########################################################
########### Input Parameters (TO BE MODIFIED) ###########
#########################################################

# Path to the file containing the mobility simulation
input_file = "C:/Users/dumoulin/Documents/_CODES/gtfs4ev/examples/output/Mobility_fleet_operation.csv"
output_file = 'economic_savings_results.csv'

# Number of days
active_working_days = 260

# Electric energy use 
ev_consumption = 0.39 # EV consumption (kWh/km) - Value should not affect the output
charging_efficiency = 0.9 # Loss during charging process
electricity_price = 0.3 # Electricity price (US$/kWh)

# Diesel vehicle
diesel_consumption = 0.1 # Diesel consumption (L/km)
diesel_price = 1.385 # Diesel price (US$/L)

#########################################################
###################### Processing #######################
#########################################################

data = pd.read_csv(input_file)

total_km = data['total_distance_km'] * active_working_days
savings_per_km = (diesel_consumption * diesel_price) - (ev_consumption / charging_efficiency * electricity_price)

# Compute emissions and savings
data['economic_savings_USD'] = total_km * savings_per_km

# Create final dataframe
result_df = data[['vehicle_id', 'trip_id', 'economic_savings_USD']]

# Save to file
result_df.to_csv(output_file, index=False)

# Print summary stats
avg_savings = result_df['economic_savings_USD'].mean()
total_savings = result_df['economic_savings_USD'].sum()

print(f"Average economic savings per vehicle: {avg_savings:.2f} USD")
print(f"Total savings: {total_savings:.2f} USD")
