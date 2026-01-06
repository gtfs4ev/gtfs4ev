# coding: utf-8

import numpy as np
import pandas as pd
import warnings
from scipy.interpolate import interp1d
import scipy.integrate as integrate
from scipy.stats import spearmanr
from scipy.integrate import IntegrationWarning
import os
import contextlib

from gtfs4ev.pvsimulator import PVSimulator

# Suppress repeated IntegrationWarning
warnings.filterwarnings("ignore", category=IntegrationWarning)

class EVPVSynergies:
    """
    A class to analyze energy synergies between electric vehicle (EV) charging demand and photovoltaic (PV) production. 
    The main metrics calculated include energy coverage, self-sufficiency, self-consumption, and excess PV ratios, 
    as well as the Spearman correlation between EV and PV profiles over specific days.

    This class requires:

    - A PVSimulator object, which holds the capacity factor time series data for PV production.
    - A ChargingSimulator object, which stores EV charging demand profiles.
    - The installed PV capacity (in megawatts, MW) as a float value.
    """

    def __init__(self, pv: PVSimulator, load_curve: pd.DataFrame, pv_capacity_MW: float):
        """
        Initialize the EVPVSynergies object.
        
        Args:
            pv: Object containing PV production calculations.
            ev: Object containing EV charging demand calculations.
            pv_capacity_MW: PV capacity in megawatts (MW).
        """
        print("=========================================")
        print(f"INFO \t Creation of a EVPVSynergies object.")
        print("=========================================")
        
        self.pv_capacity_MW = pv_capacity_MW
        self.pv_capacity_factor = pv       

        self.ev_charging_demand_MW = load_curve # Store only the interpolate charging demand

        print(f"INFO \t Successful initialization of input parameters.")

    @property
    def ev_charging_demand_MW(self) -> interp1d:
        """interp1d: Interpolation function for EV charging demand."""
        return self._ev_charging_demand_MW

    @ev_charging_demand_MW.setter
    def ev_charging_demand_MW(self, load_curve: pd.DataFrame):

        # Extract the 'Time' and 'Total profile (MW)' columns
        time = load_curve['time_h']

        profile = (load_curve['depot'] + load_curve['stop'] + load_curve['terminal']) / 1000.0

        self._ev_charging_demand_MW = interp1d(time, profile, kind='linear', fill_value='extrapolate') 

    @property
    def pv_capacity_factor(self) -> dict:
        """ dict: Dictionary of interpolation functions for PV capacity factors by day."""
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
        """ float: PV capacity in megawatts (MW)."""
        return self._pv_capacity_MW

    @pv_capacity_MW.setter
    def pv_capacity_MW(self, pv_capacity_MW: float):
        self._pv_capacity_MW = pv_capacity_MW
        
    # PV Production

    def pv_power_MW(self, day: str = '01-01') -> callable:
        """Return the PV power in megawatts for a given day as a function of time.

        Args:
            day (str): The day in 'MM-DD' format to calculate PV power for. Defaults to '01-01'.

        Returns:
            callable: A lambda function that calculates PV power (MW) at any given time.
        """
        return lambda x: self.pv_capacity_factor[day](x) * self.pv_capacity_MW

    def pv_production(self, day: str = '01-01') -> float:
        """Calculate the total PV production for a given day by integrating over 24 hours.

        Args:
            day (str): The day in 'MM-DD' format to calculate PV production for. Defaults to '01-01'.

        Returns:
            float: Total PV production (MWh) for the specified day.
        """
        result, error = integrate.quad(self.pv_power_MW(day), 0, 24)
        return result

    # EV Charging demand

    def ev_demand(self) -> float:
        """Calculate the total EV charging demand by integrating over 24 hours.

        Returns:
            float: Total EV charging demand (MWh) for the day.
        """
        result, error = integrate.quad(self.ev_charging_demand_MW, 0, 24)
        return result

    # EV-PV Synergies 

    def energy_coverage_ratio(self, day: str = '01-01') -> float:
        """Calculate the ratio of PV production to EV charging demand for a given day.

        Args:
            day (str): The day in 'MM-DD' format to calculate the energy coverage ratio for. Defaults to '01-01'.

        Returns:
            float: Energy coverage ratio for the specified day.
        """
        return self.pv_production(day) / self.ev_demand()

    def self_sufficiency_ratio(self, day: str = '01-01', coincident_power: float = None) -> float:
        """Calculate the self-sufficiency ratio for a given day.

        The self-sufficiency ratio is the ratio of coincident power (minimum of PV and EV demand) 
        to EV demand.

        Args:
            day (str): The day in 'MM-DD' format to calculate the self-sufficiency ratio for. Defaults to '01-01'.
            coincident_power (float): The coincident power if already calculated. Default is None.

        Returns:
            float: Self-sufficiency ratio for the specified day.
        """
        if coincident_power is None:
            coincident_power = lambda x: min(self.pv_power_MW(day)(x), self.ev_charging_demand_MW(x))
            result, error = integrate.quad(coincident_power, 0, 24)
            coincident_power = result

        return coincident_power / self.ev_demand()

    def self_consumption_ratio(self, day: str = '01-01', coincident_power: float = None) -> float:
        """Calculate the self-consumption ratio for a given day.

        The self-consumption ratio is the ratio of coincident power to total PV production.

        Args:
            day (str): The day in 'MM-DD' format to calculate the self-consumption ratio for. Defaults to '01-01'.
            coincident_power (float): The coincident power if already calculated. Default is None.

        Returns:
            float: Self-consumption ratio for the specified day.
        """
        if coincident_power is None:
            coincident_power = lambda x: min(self.pv_power_MW(day)(x), self.ev_charging_demand_MW(x))
            result, error = integrate.quad(coincident_power, 0, 24)
            coincident_power = result

        return coincident_power / self.pv_production(day)

    def excess_pv_ratio(self, day: str = '01-01', coincident_power: float = None) -> float:
        """Calculate the excess PV ratio for a given day.

        The excess PV ratio is the fraction of PV production that exceeds the EV demand.

        Args:
            day (str): The day in 'MM-DD' format to calculate the excess PV ratio for. Defaults to '01-01'.
            coincident_power (float): The coincident power if already calculated. Default is None.

        Returns:
            float: Excess PV ratio for the specified day.
        """
        if coincident_power is None:
            coincident_power = lambda x: min(self.pv_power_MW(day)(x), self.ev_charging_demand_MW(x))
            result, error = integrate.quad(coincident_power, 0, 24)
            coincident_power = result

        pv_prod = self.pv_production(day)

        return (pv_prod - coincident_power) / pv_prod

    def spearman_correlation(self, day: str = '01-01', n_points: int = 100) -> tuple:
        """Calculate the Spearman correlation between PV production and EV charging demand.

        Args:
            day (str): The day in 'MM-DD' format to calculate the Spearman correlation for. Defaults to '01-01'.
            n_points (int): The number of points to sample across the 24-hour period. Defaults to 100.

        Returns:
            tuple: Spearman correlation coefficient and p-value.
        """
        # Define the range and resolution
        t_values = np.linspace(0, 24, n_points) 

        pv_values = self.pv_power_MW(day)(t_values)
        ev_values = self.ev_charging_demand_MW(t_values)

        # Compute the Spearman rank correlation coefficient
        spearman_coef, p_value = spearmanr(pv_values, ev_values)

        return spearman_coef, p_value

    def daily_metrics(self, start_date: str, end_date: str, n_points: int = 100) -> pd.DataFrame:
        """Compute all energy and synergy metrics over a given period.

        Args:
            start_date (str): Start date in 'MM-DD' format.
            end_date (str): End date in 'MM-DD' format.
            n_points (int): The number of points to sample for each day. Defaults to 100.
            recompute_probability (float): Probability (between 0 and 1) of recomputing EV demand for each day.

        Returns:
            pd.DataFrame: DataFrame containing all metrics for each day within the specified range.
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