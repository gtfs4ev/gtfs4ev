# coding: utf-8

import numpy as np
import pandas as pd
import warnings
from scipy.interpolate import interp1d
import scipy.integrate as integrate
from scipy.stats import spearmanr
from scipy.integrate import IntegrationWarning
import os

from gtfs4ev.analysis.pvsimulator import PVSimulator

# Suppress repeated IntegrationWarning
warnings.filterwarnings("ignore", category=IntegrationWarning)

class EVPVSynergies:
    """
    **Electric Vehicle – Photovoltaic (EV–PV) energy synergy analyzer**.

    The `EVPVSynergies` class quantifies the temporal and energetic interaction
    between electric vehicle (EV) charging demand and photovoltaic (PV) electricity
    production. It evaluates how effectively on-site or nearby PV generation
    can support EV charging loads. *

    The class computes daily energy and synergy indicators including:
        - Energy coverage ratio
        - Self-sufficiency ratio
        - Self-consumption ratio
        - Excess PV production ratio
        - Spearman rank correlation between PV and EV profiles

    All metrics are evaluated on a **24-hour basis** and can be aggregated
    across a user-defined date range.

    Required inputs:
        - A `PVSimulator` instance containing PV capacity factor time series
        - An EV charging demand load curve
        - Installed PV capacity (MW)

    Attributes:
        pv_capacity_MW (float): Installed photovoltaic capacity (MW).
        pv_capacity_factor (dict): Daily interpolation functions of PV capacity factors.
        ev_charging_demand_MW (callable): Interpolated EV charging demand profile (MW).

    Notes:
        - All integrations are performed over a 24-hour horizon (0–24 h)
        - Time resolution is defined by interpolation and integration settings
        - Results represent **theoretical energy synergies**, not operational dispatch
    """

    ## ============================================================
    ## Constructor
    ## ============================================================

    def __init__(self, pv: PVSimulator, load_curve: pd.DataFrame, pv_capacity_MW: float):
        """
        Initialize the EV–PV synergy analyzer.

        Args:
            pv (PVSimulator): Object containing PV capacity factor results.
            load_curve (pd.DataFrame): EV charging demand profile containing:
                - time_h
                - depot
                - stop
                - terminal
            pv_capacity_MW (float): Installed PV capacity in megawatts (MW).
        """
        print("=========================================")
        print(f"INFO \t Creation of a EVPVSynergies object.")
        print("=========================================")
        
        self.pv_capacity_MW = pv_capacity_MW
        self.pv_capacity_factor = pv       

        self.ev_charging_demand_MW = load_curve # Store only the interpolate charging demand

        print(f"INFO \t Successful initialization of input parameters.")

    ## ============================================================
    ## Attributes
    ## ============================================================

    @property
    def ev_charging_demand_MW(self) -> interp1d:
        """
        Interpolated EV charging demand profile.

        Returns:
            interp1d: Continuous EV charging demand function (MW vs time).
        """
        return self._ev_charging_demand_MW

    @ev_charging_demand_MW.setter
    def ev_charging_demand_MW(self, load_curve: pd.DataFrame):

        # Extract the 'Time' and 'Total profile (MW)' columns
        time = load_curve['time_h']

        profile = (load_curve['depot'] + load_curve['stop'] + load_curve['terminal']) / 1000.0

        self._ev_charging_demand_MW = interp1d(time, profile, kind='linear', fill_value='extrapolate') 

    @property
    def pv_capacity_factor(self) -> dict:
        """
        Daily PV capacity factor interpolation functions.

        Returns:
            dict: Dictionary mapping 'MM-DD' to interpolation functions
                  returning PV capacity factors as a function of hour.
        """
        return self._pv_capacity_factor

    @pv_capacity_factor.setter
    def pv_capacity_factor(self, pv: PVSimulator):
        """pv_capacity_factor (pd.DataFrame): DataFrame containing PV capacity factors."""
        df = pv.results['Capacity Factor'].reset_index() 

        # Rename the columns for convenience (optional, but helpful)
        df.columns = ['Timestamp', 'Capacity Factor']

        # Convert the first column to datetime format
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])

        # Extract the 'Month-Day' and 'Hour' from the timestamp
        df['Month-Day'] = df['Timestamp'].dt.strftime('%m-%d')
        df['Hour'] = df['Timestamp'].dt.hour

        # Create a dictionary to hold the interpolation functions for each day
        interpolation_functions = {}

        # Group data by 'Day'
        grouped = df.groupby('Month-Day')

        # Create an interpolation function for each day
        for day, group in grouped:
            hours = group['Hour']
            profile = group['Capacity Factor']

            # Create the interpolation function for this day
            interpolation_function = interp1d(hours, profile, kind='linear', fill_value='extrapolate')
            
            # Store the function in the dictionary with the day as the key
            interpolation_functions[day] = interpolation_function

        self._pv_capacity_factor = interpolation_functions

    @property
    def pv_capacity_MW(self) -> float:
        """
        Installed PV capacity.

        Returns:
            float: PV capacity in megawatts (MW).
        """
        return self._pv_capacity_MW

    @pv_capacity_MW.setter
    def pv_capacity_MW(self, pv_capacity_MW: float):
        self._pv_capacity_MW = pv_capacity_MW
        
    ## ============================================================
    ## PV Production
    ## ============================================================

    def pv_power_MW(self, day: str = '01-01') -> callable:
        """
        PV power output function for a given day.

        Args:
            day (str, optional): Day in 'MM-DD' format. Defaults to '01-01'.

        Returns:
            callable: Function returning PV power output (MW) at time t.
        """
        return lambda x: self.pv_capacity_factor[day](x) * self.pv_capacity_MW

    def pv_production(self, day: str = '01-01') -> float:
        """
        Total daily PV electricity production.

        Args:
            day (str, optional): Day in 'MM-DD' format. Defaults to '01-01'.

        Returns:
            float: Daily PV energy production (MWh).
        """
        result, error = integrate.quad(self.pv_power_MW(day), 0, 24)
        return result

    ## ============================================================
    ## EV Charging Demand
    ## ============================================================

    def ev_demand(self) -> float:
        """
        Total daily EV charging demand.

        Returns:
            float: Daily EV electricity demand (MWh).
        """
        result, error = integrate.quad(self.ev_charging_demand_MW, 0, 24)
        return result

    ## ============================================================
    ## EV–PV Synergy Metrics
    ## ============================================================

    def energy_coverage_ratio(self, day: str = '01-01') -> float:
        """
        Energy coverage ratio.

        Defined as:
            PV production / EV charging demand

        Args:
            day (str, optional): Day in 'MM-DD' format. Defaults to '01-01'.

        Returns:
            float: Energy coverage ratio.
        """
        return self.pv_production(day) / self.ev_demand()

    def self_sufficiency_ratio(self, day: str = '01-01', coincident_power: float = None) -> float:
        """
        Self-sufficiency ratio.

        Defined as:
            Coincident PV–EV energy / EV charging demand

        Args:
            day (str, optional): Day in 'MM-DD' format. Defaults to '01-01'.
            coincident_power (float, optional): Precomputed coincident energy (MWh).

        Returns:
            float: Self-sufficiency ratio.
        """
        if coincident_power is None:
            coincident_power = lambda x: min(self.pv_power_MW(day)(x), self.ev_charging_demand_MW(x))
            result, error = integrate.quad(coincident_power, 0, 24)
            coincident_power = result

        return coincident_power / self.ev_demand()

    def self_consumption_ratio(self, day: str = '01-01', coincident_power: float = None) -> float:
        """
        Self-consumption ratio.

        Defined as:
            Coincident PV–EV energy / PV production

        Args:
            day (str, optional): Day in 'MM-DD' format. Defaults to '01-01'.
            coincident_power (float, optional): Precomputed coincident energy (MWh).

        Returns:
            float: Self-consumption ratio.
        """
        if coincident_power is None:
            coincident_power = lambda x: min(self.pv_power_MW(day)(x), self.ev_charging_demand_MW(x))
            result, error = integrate.quad(coincident_power, 0, 24)
            coincident_power = result

        return coincident_power / self.pv_production(day)

    def excess_pv_ratio(self, day: str = '01-01', coincident_power: float = None) -> float:
        """
        Excess PV production ratio.

        Defined as:
            (PV production − coincident energy) / PV production

        Args:
            day (str, optional): Day in 'MM-DD' format. Defaults to '01-01'.
            coincident_power (float, optional): Precomputed coincident energy (MWh).

        Returns:
            float: Excess PV ratio.
        """
        if coincident_power is None:
            coincident_power = lambda x: min(self.pv_power_MW(day)(x), self.ev_charging_demand_MW(x))
            result, error = integrate.quad(coincident_power, 0, 24)
            coincident_power = result

        pv_prod = self.pv_production(day)

        return (pv_prod - coincident_power) / pv_prod

    def spearman_correlation(self, day: str = '01-01', n_points: int = 100) -> tuple:
        """
        Spearman rank correlation between PV production and EV demand profiles.

        Args:
            day (str, optional): Day in 'MM-DD' format. Defaults to '01-01'.
            n_points (int, optional): Number of temporal samples. Defaults to 100.

        Returns:
            tuple: (Spearman correlation coefficient, p-value).
        """
        # Define the range and resolution
        t_values = np.linspace(0, 24, n_points) 

        pv_values = self.pv_power_MW(day)(t_values)
        ev_values = self.ev_charging_demand_MW(t_values)

        # Compute the Spearman rank correlation coefficient - Checking first if calculation makes sense
        if (np.all(pv_values == pv_values[0]) or np.all(ev_values == ev_values[0])):
            spearman_coef, p_value = np.nan, np.nan
        else:
            spearman_coef, p_value = spearmanr(pv_values, ev_values)

        return spearman_coef, p_value

    ## ============================================================
    ## Aggregated Daily Analysis
    ## ============================================================

    def daily_metrics(self, start_date: str, end_date: str, n_points: int = 100) -> pd.DataFrame:
        """
        Compute all EV–PV synergy metrics over a date range.

        Metrics computed for each day include:
            - PV production
            - EV demand
            - Energy coverage ratio
            - Self-sufficiency ratio
            - Self-consumption ratio
            - Excess PV ratio
            - Spearman correlation coefficient and p-value

        Args:
            start_date (str): Start date in 'MM-DD' format.
            end_date (str): End date in 'MM-DD' format.
            n_points (int, optional): Temporal sampling resolution. Defaults to 100.

        Returns:
            pd.DataFrame: Daily EV–PV synergy metrics.
        """
        print(f"INFO \t Computing all metrics over a given period. This might take some time...")

        # Convert start and end dates from MM-DD to YYYY-MM-DD format
        start_date = f'1901-{start_date}'
        end_date = f'1901-{end_date}'

        # Generate a list of dates from start to end date in MM-DD format
        date_range = pd.date_range(start=start_date, end=end_date)
        filtered_days = [date.strftime('%m-%d') for date in date_range if date.strftime('%m-%d') in self.pv_capacity_factor]

        # Initialize lists to hold results
        results = []

        for day in filtered_days:
            print(f"\t > Day: {day}", end='\r')
            
            # Calculate metrics
            spearman_coef, p_value = self.spearman_correlation(day, n_points)
            pv_prod = self.pv_production(day)
            ev_dmd = self.ev_demand()
            energy_cov_ratio = self.energy_coverage_ratio(day)

            # Precomputed coincident power
            coincident_power = lambda x: min(self.pv_power_MW(day)(x), self.ev_charging_demand_MW(x))
            result, error = integrate.quad(coincident_power, 0, 24)

            self_suf_ratio = self.self_sufficiency_ratio(day, result)            
            self_cons_ratio = self.self_consumption_ratio(day, result)
            excess_pv_rat = self.excess_pv_ratio(day, result)

            results.append({
                'Day': f'1901-{day}',                
                'PV Production (MWh)': pv_prod,
                'EV Demand (MWh)': ev_dmd,
                'Spearman Coefficient': spearman_coef,
                'P-Value': p_value,
                'Energy Coverage Ratio': energy_cov_ratio,
                'Self Sufficiency Ratio': self_suf_ratio,                
                'Self Consumption Ratio': self_cons_ratio,
                'Excess PV Ratio': excess_pv_rat
            })
        print("")

        # Create a DataFrame from the results
        df = pd.DataFrame(results)

        return df