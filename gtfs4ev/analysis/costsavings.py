# coding: utf-8

import pandas as pd

class CostSavings:
    """
    **Fleet electrification economic savings calculator**.

    The `CostSavings` class estimates **annual operating cost savings**
    resulting from the transition of diesel vehicles to electric vehicles (EVs),
    based on fleet operation data and energy price assumptions.

    The analysis compares:
    - Diesel fuel costs under conventional operation
    - Electricity costs under full electrification

    Savings are computed at the trip and vehicle level and aggregated
    to annual values using a specified number of active working days.

    Workflow:
        1. Load fleet operation data containing trip distances.
        2. Annualize traveled distance using active working days.
        3. Compute diesel cost baseline.
        4. Compute EV electricity costs (corrected for charging efficiency).
        5. Estimate economic savings.
        6. Export results and summary statistics.

    Notes:
        - Energy prices are assumed constant over the analysis period.
        - No maintenance, depreciation, or capital expenditure is included.
        - EV and diesel vehicles are assumed operationally equivalent.
        - Results represent **potential operational savings** only.

    Attributes:
        input_file (str): Path to CSV file containing fleet operation data.
        active_working_days (int): Number of operational days per year.
        ev_consumption (float): EV electricity consumption (kWh/km).
        charging_efficiency (float): Charging efficiency (0–1).
        electricity_price (float): Electricity price (currency/kWh).
        diesel_consumption (float): Diesel fuel consumption (L/km).
        diesel_price (float): Diesel fuel price (currency/L).
        data (pd.DataFrame): Raw input fleet operation data.
        results (pd.DataFrame): Computed economic savings per trip and vehicle.

    Examples:
        >>> calculator = CostSavings(
        ...     input_file="Mobility_fleet_operation.csv",
        ...     active_working_days=260,
        ...     ev_consumption=0.39,
        ...     charging_efficiency=0.9,
        ...     electricity_price=0.3,
        ...     diesel_consumption=0.1,
        ...     diesel_price=1.385,
        ... )
        >>> calculator.compute_savings()
        >>> calculator.save_results("economic_savings_results.csv")
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
        electricity_price: float = 0.3,
        diesel_consumption: float = 0.1,
        diesel_price: float = 1.385,
        self_sufficiency: float = 0.0,
        self_consumption: float = 1.0,
        pv_lcoe: float = 0.0,
    ):
        """
        Initialize the economic savings calculator.

        This constructor registers all required input parameters but does
        not perform any computation. Calculations are triggered by calling
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
            electricity_price (float, optional): Electricity price in
                currency per kWh. Defaults to 0.3.
            diesel_consumption (float, optional): Diesel fuel consumption
                in liters per km. Defaults to 0.1.
            diesel_price (float, optional): Diesel fuel price in
                currency per liter. Defaults to 1.385.
        """
        self.input_file = input_file
        self.active_working_days = active_working_days
        self.ev_consumption = ev_consumption
        self.charging_efficiency = charging_efficiency
        self.electricity_price = electricity_price
        self.diesel_consumption = diesel_consumption
        self.diesel_price = diesel_price
        self.self_sufficiency = self_sufficiency
        self.self_consumption = self_consumption
        self.pv_lcoe = pv_lcoe

        self.data = None
        self.results = None

    ## ============================================================
    ## Computation and results
    ## ============================================================

    def compute_savings(self) -> None:
        """
        Compute annual economic savings from fleet electrification.

        This method:
        - Loads fleet operation data from the input CSV file
        - Annualizes traveled distance using active working days
        - Computes diesel fuel costs
        - Computes EV electricity costs corrected for charging efficiency
        - Calculates net operating cost savings

        Results are stored internally and made available via the
        `results` attribute.
        """

        self.data = pd.read_csv(self.input_file)

        # Total annual distance
        total_km = self.data["total_distance_km"] * self.active_working_days

        # Diesel scenario
        # ============================================================

        diesel_cost_per_km = (
            self.diesel_consumption 
            * self.diesel_price
        )

        diesel_cost = total_km * diesel_cost_per_km

        # Electric scenario
        # ============================================================

        effective_electricity_price = (
            (1 - self.self_sufficiency) * self.electricity_price
            + (self.self_sufficiency / self.self_consumption) * self.pv_lcoe
        )

        ev_cost_per_km = (
            self.ev_consumption 
            / self.charging_efficiency
            * effective_electricity_price
        )

        electricity_cost = total_km * ev_cost_per_km

        # Savings
        # ============================================================

        savings = diesel_cost - electricity_cost


        # Store results
        self.data["diesel_cost_USD"] = diesel_cost
        self.data["electricity_cost_USD"] = electricity_cost
        self.data["economic_savings_USD"] = savings


        # Select relevant output columns
        self.results = self.data[
            [
                "vehicle_id",
                "trip_id",
                "diesel_cost_USD",
                "electricity_cost_USD",
                "economic_savings_USD",
            ]
        ]

    def save_results(self, output_file: str) -> None:
        """
        Save computed economic savings to a CSV file.

        Args:
            output_file (str): Path to the output CSV file.

        Raises:
            RuntimeError: If `compute_savings()` has not been called.
        """
        if self.results is None:
            raise RuntimeError("No results to save. Run compute_savings() first.")

        self.results.to_csv(output_file, index=False)

    def print_summary(self) -> None:

        if self.results is None:
            raise RuntimeError(
                "No results to summarize. Run compute_savings() first."
            )

        total_diesel = self.results["diesel_cost_USD"].sum()
        total_electricity = self.results["electricity_cost_USD"].sum()
        total_savings = self.results["economic_savings_USD"].sum()

        print(f"Total diesel cost: {total_diesel:.2f} USD")
        print(f"Total electricity cost: {total_electricity:.2f} USD")
        print(f"Total economic savings: {total_savings:.2f} USD")

    ## ============================================================
    ## Static helper method to calculate the LCOE
    ## ============================================================

    @staticmethod
    def calculate_pv_lcoe(
        investment_cost: float,
        om_cost: float,
        annual_yield: float,
        lifetime: int,
        discount_rate: float,
        degradation_rate: float = 0.005,
    ) -> float:
        """
        Calculate PV levelized cost of electricity (LCOE)
        including annual PV degradation.

        Args:
            investment_cost:
                Initial PV investment cost (USD/kWp).

            om_cost:
                Annual O&M cost (USD/kWp/year).

            annual_yield:
                First-year PV electricity production (kWh/kWp/year).

            lifetime:
                PV project lifetime (years).

            discount_rate:
                Discount rate as a fraction (e.g. 0.05).

            degradation_rate:
                Annual PV degradation rate as a fraction
                (e.g. 0.005 = 0.5%/year).

        Returns:
            PV LCOE (USD/kWh).
        """

        discounted_costs = investment_cost
        discounted_energy = 0

        for year in range(1, lifetime + 1):

            discount_factor = (1 + discount_rate) ** year

            # Degraded PV production
            energy_year = annual_yield * (
                (1 - degradation_rate) ** (year - 1)
            )

            discounted_costs += om_cost / discount_factor

            discounted_energy += energy_year / discount_factor

        return discounted_costs / discounted_energy