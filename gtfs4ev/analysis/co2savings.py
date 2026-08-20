# coding: utf-8

import pandas as pd

class CO2Savings:
    """
    **Fleet electrification CO₂ emissions and diesel fuel savings calculator**.

    The `CO2Savings` class estimates **annual CO₂ emission reductions** and
    **diesel fuel savings** resulting from the replacement of diesel vehicles
    with electric vehicles (EVs), based on fleet operation data.

    The calculation is performed at the trip and vehicle level and assumes
    a full substitution of diesel operation by electric driving over a
    defined number of active working days per year.

    Workflow:
        1. Load fleet operation data containing trip distances.
        2. Annualize traveled distance using active working days.
        3. Compute diesel baseline emissions.
        4. Compute EV-related emissions from electricity consumption.
        5. Estimate CO₂ emission reductions and diesel fuel savings.
        6. Export results and summary statistics.

    Notes:
        - Emission factors are assumed constant over time.
        - EV electricity consumption is corrected for charging efficiency.
        - No vehicle-specific efficiency differences are modeled.
        - Results represent **potential annual savings**, not measured values.
        - Upstream vehicle manufacturing emissions are not included.

    Attributes:
        input_file (str): Path to CSV file containing fleet operation data.
        active_working_days (int): Number of operational days per year.
        ev_consumption (float): EV electricity consumption (kWh/km).
        charging_efficiency (float): Charging efficiency (0–1).
        electricity_co2_intensity (float): Electricity CO₂ intensity (kgCO₂/kWh).
        diesel_consumption (float): Diesel fuel consumption (L/km).
        diesel_co2_intensity (float): Diesel CO₂ intensity (kgCO₂/L).
        data (pd.DataFrame): Raw input fleet data.
        results (pd.DataFrame): Computed emission reductions and fuel savings.

    Examples:
        >>> calculator = CO2Savings(
        ...     input_file="mobility_fleet_operation.csv",
        ...     active_working_days=260,
        ...     ev_consumption=0.39,
        ...     charging_efficiency=0.9,
        ...     electricity_co2_intensity=0.1,
        ...     diesel_consumption=0.1,
        ...     diesel_co2_intensity=2.7,
        ... )
        >>> calculator.compute_savings()
        >>> calculator.save_results("co2_savings_results.csv")
        >>> calculator.print_summary()
    """

    ## ============================================================
    ## Constructor
    ## ============================================================

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
        Initialize the CO₂ emissions and diesel savings calculator.

        This constructor registers all input parameters but does not perform
        any computation. Calculations are triggered by calling
        `compute_savings()`.

        Args:
            input_file (str): Path to CSV file containing fleet operation data.
                The file must include at least:
                - vehicle_id
                - trip_id
                - total_distance_km
            active_working_days (int, optional): Number of active operating
                days per year. Defaults to 260.
            ev_consumption (float, optional): EV electricity consumption in
                kWh per km. Defaults to 0.39.
            charging_efficiency (float, optional): Charging efficiency as a
                fraction (0–1). Defaults to 0.9.
            electricity_co2_intensity (float, optional): CO₂ intensity of
                electricity in kgCO₂/kWh. Defaults to 0.1.
            diesel_consumption (float, optional): Diesel fuel consumption in
                liters per km. Defaults to 0.1.
            diesel_co2_intensity (float, optional): CO₂ intensity of diesel
                fuel in kgCO₂ per liter. Defaults to 2.7.
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

    ## ============================================================
    ## Computation and results
    ## ============================================================

    def compute_savings(self) -> None:
        """
        Compute annual CO₂ emissions and emission reductions.

        Results are stored internally and made available via the
        `results` attribute.
        """
        self.data = pd.read_csv(self.input_file)

        # Emissions per km
        diesel_emissions_per_km = (self.diesel_consumption * self.diesel_co2_intensity)

        ev_emissions_per_km = (
            self.ev_consumption
            / self.charging_efficiency
            * self.electricity_co2_intensity
        )

        # Calculate total kilometers driven over the active working days
        total_km = self.data["total_distance_km"] * self.active_working_days

        # Diesel baseline emissions
        self.data["diesel_emissions_tco2"] = (
            total_km * diesel_emissions_per_km
        ) / 1000

        # EV electricity emissions
        self.data["ev_emissions_tco2"] = (
            total_km * ev_emissions_per_km
        ) / 1000

        # Emission reduction
        self.data["emission_reduction_tco2"] = (
            self.data["diesel_emissions_tco2"]
            - self.data["ev_emissions_tco2"]
        )

        # Diesel fuel savings
        self.data["diesel_savings_L"] = (
            total_km * self.diesel_consumption
        )

        # Select relevant columns for output
        self.results = self.data[
            [
                "vehicle_id",
                "trip_id",
                "diesel_emissions_tco2",
                "ev_emissions_tco2",
                "emission_reduction_tco2",
                "diesel_savings_L",
            ]
        ]

    def save_results(self, output_file: str) -> None:
        """
        Save computed results to a CSV file.

        Args:
            output_file (str): Path to the output CSV file.

        Raises:
            RuntimeError: If `compute_savings()` has not been called.
        """
        if self.results is None:
            raise RuntimeError("No results to save. Run compute_savings() first.")

        self.results.to_csv(output_file, index=False)

    def print_summary(self) -> None:
        """
        Print summary statistics of emission reductions and diesel savings.

        The summary includes:
        - Average CO₂ emission reduction per vehicle
        - Total CO₂ emission reduction
        - Average diesel fuel savings per vehicle
        - Total diesel fuel savings

        Raises:
            RuntimeError: If `compute_savings()` has not been called.
        """
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