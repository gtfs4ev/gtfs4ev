# coding: utf-8

"""
CO2Savings
------------------

A class to estimate CO2 emission reductions and diesel fuel savings from
transitioning diesel vehicles to electric vehicles, based on fleet operation data.

Usage:
    1. Instantiate the class with input CSV file path and parameters.
    2. Call `compute_savings()` to run the calculations.
    3. Use `save_results(output_file)` to save the results.
    4. Call `print_summary()` to display summary statistics.

Example:
    calculator = CO2EmissionSavings(
        input_file="path/to/mobility_fleet_operation.csv",
        active_working_days=260,
        ev_consumption=0.39,
        charging_efficiency=0.9,
        electricity_co2_intensity=0.1,
        diesel_consumption=0.1,
        diesel_co2_intensity=2.7,
    )
    calculator.compute_savings()
    calculator.save_results("output/co2_savings_results.csv")
    calculator.print_summary()
"""

import pandas as pd

class CO2Savings:
    def __init__(
        self,
        input_file: str,
        active_working_days: int = 260,
        ev_consumption: float = 0.39,
        charging_efficiency: float = 0.9,
        electricity_co2_intensity: float = 0.1,
        diesel_consumption: float = 0.1,
        diesel_co2_intensity: float = 2.7,
    ):
        """
        Initialize the CO2EmissionSavings calculator.

        Args:
            input_file (str): Path to the CSV file with fleet operation data.
            active_working_days (int): Number of active working days per year.
            ev_consumption (float): EV energy consumption in kWh/km.
            charging_efficiency (float): Charging efficiency (fraction).
            electricity_co2_intensity (float): CO2 intensity of electricity (kgCO2/kWh).
            diesel_consumption (float): Diesel consumption in L/km.
            diesel_co2_intensity (float): CO2 intensity of diesel fuel (kgCO2/L).
        """
        self.input_file = input_file
        self.active_working_days = active_working_days
        self.ev_consumption = ev_consumption
        self.charging_efficiency = charging_efficiency
        self.electricity_co2_intensity = electricity_co2_intensity
        self.diesel_consumption = diesel_consumption
        self.diesel_co2_intensity = diesel_co2_intensity

        self.data = None
        self.results = None

    def compute_savings(self):
        """Load data and compute CO2 emission reductions and diesel savings."""
        self.data = pd.read_csv(self.input_file)

        diesel_emissions_per_km = self.diesel_consumption * self.diesel_co2_intensity
        ev_emissions_per_km = (
            self.ev_consumption / self.charging_efficiency * self.electricity_co2_intensity
        )

        # Calculate total kilometers driven over the active working days
        total_km = self.data["total_distance_km"] * self.active_working_days

        # Compute emission reductions in tonnes CO2 and diesel savings in liters
        self.data["emission_reduction_tco2"] = (total_km * (diesel_emissions_per_km - ev_emissions_per_km)) / 1000
        self.data["diesel_savings_L"] = total_km * self.diesel_consumption

        # Select relevant columns for output
        self.results = self.data[["vehicle_id", "trip_id", "emission_reduction_tco2", "diesel_savings_L"]]

    def save_results(self, output_file: str):
        """
        Save the results to a CSV file.

        Args:
            output_file (str): Path to the output CSV file.
        """
        if self.results is None:
            raise RuntimeError("No results to save. Run compute_savings() first.")

        self.results.to_csv(output_file, index=False)

    def print_summary(self):
        """Print summary statistics of emission reductions and diesel savings."""
        if self.results is None:
            raise RuntimeError("No results to summarize. Run compute_savings() first.")

        avg_emission_reduction = self.results["emission_reduction_tco2"].mean()
        total_emission_reduction = self.results["emission_reduction_tco2"].sum()
        avg_diesel_savings = self.results["diesel_savings_L"].mean()
        total_diesel_savings = self.results["diesel_savings_L"].sum()

        print(f"Average emission reduction per vehicle: {avg_emission_reduction:.2f} tCO2")
        print(f"Total emission reduction: {total_emission_reduction:.2f} tCO2")
        print(f"Average diesel savings per vehicle: {avg_diesel_savings:.2f} L")
        print(f"Total diesel savings: {total_diesel_savings:.2f} L")