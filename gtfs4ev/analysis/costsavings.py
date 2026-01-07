# coding: utf-8

"""
CostSavings
---------------

A class to estimate economic savings from transitioning diesel vehicles
to electric vehicles, based on fleet operation data and energy cost assumptions.

Usage:
    1. Instantiate the class with input CSV file path and parameters.
    2. Call `compute_savings()` to run the calculations.
    3. Use `save_results(output_file)` to save the results.
    4. Call `print_summary()` to display summary statistics.

Example:
    calculator = CostSavings(
        input_file="path/to/Mobility_fleet_operation.csv",
        active_working_days=260,
        ev_consumption=0.39,
        charging_efficiency=0.9,
        electricity_price=0.3,
        diesel_consumption=0.1,
        diesel_price=1.385,
    )
    calculator.compute_savings()
    calculator.save_results("output/economic_savings_results.csv")
    calculator.print_summary()
"""

import pandas as pd


class CostSavings:
    def __init__(
        self,
        input_file: str,
        active_working_days: int = 260,
        ev_consumption: float = 0.39,
        charging_efficiency: float = 0.9,
        electricity_price: float = 0.3,
        diesel_consumption: float = 0.1,
        diesel_price: float = 1.385,
    ):
        """
        Initialize the CostSavings calculator.

        Args:
            input_file (str): Path to the CSV file with fleet operation data.
            active_working_days (int): Number of active working days per year.
            ev_consumption (float): EV energy consumption in kWh/km.
            charging_efficiency (float): Charging efficiency (fraction).
            electricity_price (float): Electricity price in USD/kWh.
            diesel_consumption (float): Diesel consumption in L/km.
            diesel_price (float): Diesel price in USD/L.
        """
        self.input_file = input_file
        self.active_working_days = active_working_days
        self.ev_consumption = ev_consumption
        self.charging_efficiency = charging_efficiency
        self.electricity_price = electricity_price
        self.diesel_consumption = diesel_consumption
        self.diesel_price = diesel_price

        self.data = None
        self.results = None

    def compute_savings(self):
        """Load data and compute economic savings from EV transition."""
        self.data = pd.read_csv(self.input_file)

        # Total annual distance
        total_km = self.data["total_distance_km"] * self.active_working_days

        # Cost per km
        diesel_cost_per_km = self.diesel_consumption * self.diesel_price
        ev_cost_per_km = (
            self.ev_consumption / self.charging_efficiency * self.electricity_price
        )

        savings_per_km = diesel_cost_per_km - ev_cost_per_km

        # Compute economic savings
        self.data["economic_savings_USD"] = total_km * savings_per_km

        # Select relevant output columns
        self.results = self.data[
            ["vehicle_id", "trip_id", "economic_savings_USD"]
        ]

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
        """Print summary statistics of economic savings."""
        if self.results is None:
            raise RuntimeError("No results to summarize. Run compute_savings() first.")

        avg_savings = self.results["economic_savings_USD"].mean()
        total_savings = self.results["economic_savings_USD"].sum()

        print(f"Average economic savings per vehicle: {avg_savings:.2f} USD")
        print(f"Total economic savings: {total_savings:.2f} USD")