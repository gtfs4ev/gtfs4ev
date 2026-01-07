# ------------------------------------------
# CONFIGURATION FILE: GTFS4EV MODEL
# ------------------------------------------

# ========================================== #
# ============= BASIC PARAMETERS =========== #
# ========================================== #

# --- General ---
output_folder = "output"  # Output folder path (stores the output files)

# --- GTFS Data ---
gtfs_datafolder = "input/GTFS_Nairobi" # Path to the GTFS data folder (needs to be unziped!)

# --- Fleet Operation Simulation ---
trips_to_simulate = ["1011F110", "1107D110", "10114111"]  
# List of specific trip IDs to simulate. Useful for testing or focusing on a small subset.
# Write 'trips_to_simulate = None' to simulate all trips.

# --- Charging Scenario ---
energy_consumption_kWh_per_km = 0.39  # Vehicle energy consumption per kilometer (in kWh)

charging_powers_kW = {
    "depot": [[11, 0.5], [22, 0.5]],       # List of [power_kW, probability] for depot chargers
    "terminal": [[100, 1.0]],              # Charging powers at terminals
    "stop": [[200, 1.0]]                   # Charging powers regular bus stops
}

# Sequence of charging strategies to apply in order.
# The first strategy is attempted first. If charging needs are unmet, the next is tried.
charging_strategy_sequence = ["terminal_random", "stop_random", "depot_night"]

# Available strategies:
# - "terminal_random"       → Random charging at terminal with given probability
# - "stop_random"           → Random charging at regular stops with given probability
# - "depot_night"           → Recharge at depot during off-hours at the end of the day
# - "depot_day"             → Recharge at depot during the day when not in operation

# Parameters for specific strategies
charge_probability_terminal = 0.1  # Probability of charging at terminal
charge_probability_stop = 0.1      # Probability of charging at stop
depot_travel_time_min = [30, 15]   # [mean, std_deviation] of travel time (in minutes) to/from depot

# --- PV Production ---
latitude = 0.17094549   # Latitude of the PV system location
longitude = 37.9039685  # Longitude of the PV system location
year = 2020             # Year for PV simulation (affects solar data)

installation_type = "groundmounted_fixed"  
# PV installation type. Options include:
# 'rooftop', 'groundmounted_fixed', 'groundmounted_singleaxis_horizontal', 
# 'groundmounted_singleaxis_vertical', 'groundmounted_dualaxis'

# --- EV-PV Complementarity ---
pv_capacity_MW = 10  # Installed PV capacity in megawatts
start_date = "01-01"  # Simulation start date (format: MM-DD)
end_date = "01-07"    # Simulation end date (format: MM-DD)


# ========================================== #
# =========== ADVANCED PARAMETERS ========== #
# ========================================== #

# --- GTFS Data Preprocessing ---
clean_gtfs_data = True  # Whether to clean and check consistency GTFS data before simulation
trim_tripshapes_to_terminal_locations = True  # Trim trip shapes so that the exactly start and end at terminal locations
filter_out_services = []  # List of GTFS service IDs to exclude, e.g. ["id1", "id2", id3]
filter_out_agencies = []  # List of GTFS agency IDs to exclude
add_idle_time_terminals_s = [0, 0]  # Additionnal idle time (in seconds) added at terminals [average, standard_deviation]
add_idle_time_stops_s = [0, 0]      # Additionnal idle time (in seconds) added at stops [average, standard_deviation]

# --- GTFS Outputs ---
export_cleaned_gtfs = False  # If True, export cleaned/filtered GTFS data to a new folder to be easily reused
generate_network_map = True  # If True, generate a visual map of the transport network
generate_map_specific_trips = []  # Trips to map in a dedicated HTML file for inspection 

# --- Fleet Operation Simulation ---
use_multiprocessing = False  # Enable parallel processing for faster simulation
generate_map_fleet_movement = False # Generates an animation/map of bus movements (only works if less than 5 trips are simulated)

# --- Charging Scenario ---
security_driving_distance_km = 0  # Extra buffer distance added to each vehicle (in km)
load_curve_timestep_s = 60        # Time step (in seconds) for generating load curves

# --- PV Production ---
module_efficiency = 0.22             # Nominal efficiency of the PV modules (decimal)
temperature_coefficient = -0.004     # Power loss per °C 
system_losses = 0.14                 # Additionnal system losses (wiring, inverter, etc.)