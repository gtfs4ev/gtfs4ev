# coding: utf-8

import pvlib
from pvlib import location, pvsystem, modelchain
import pandas as pd
from timezonefinder import TimezoneFinder
import pytz
from datetime import datetime

class PVSimulator:
    def __init__(self, environment: dict, pv_module: dict, installation: dict):
        """
        Initializes the PVSimulator with validated environmental data, PV module parameters, and installation settings.

        Args:
            environment (dict): A dictionary containing environmental parameters with the following keys:
                - latitude (float): Latitude of the location (must be between -90 and 90).
                - longitude (float): Longitude of the location (must be between -180 and 180).
                - year (int): Year for the simulation.
            pv_module (dict): A dictionary containing PV module parameters with the following keys:
                - efficiency (float): Efficiency of the PV module (must be a positive decimal less than or equal to 1).
                - temperature_coefficient (float): Temperature coefficient of the module.
            installation (dict): A dictionary containing installation parameters with the following keys:
                - type (str): Type of installation (e.g., 'groundmounted_fixed').
                - system_losses (float): System losses as a decimal (must be between 0 and 1).
        """
        print("=========================================")
        print(f"INFO \t Creation of a PVSimulator object.")
        print("=========================================")

        # Initialize and validate environment attributes
        self.environment = environment
        self.installation = installation
        self.pv_module = pv_module

        print(f"INFO \t Successful initialization of input parameters.")

        # Modeling results
        self._results = pd.DataFrame()

        # Create location, weather data and PV system objects
        self.location = self._create_location()
        self.weather_data = self._fetch_weather_data()
        self.pv_system = self._create_pv_system()

    # Properties and Setters with validation

    @property
    def environment(self) -> dict:
        return self._environment

    @environment.setter
    def environment(self, value: dict) -> None:
        if not isinstance(value, dict):
            raise ValueError("Environment must be a dictionary")

        latitude = value.get('latitude')
        longitude = value.get('longitude')
        year = value.get('year')

        if not (-90 <= latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        if not (-180 <= longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if not isinstance(year, int):
            raise ValueError("Year must be an integer")

        self._environment = value

    @property
    def installation(self) -> dict:
        return self._installation

    @installation.setter
    def installation(self, value: dict) -> None:
        if not isinstance(value, dict):
            raise ValueError("Installation must be a dictionary")

        install_type = value.get('type')
        system_losses = value.get('system_losses')

        if install_type not in [
            'groundmounted_fixed', 'rooftop', 'groundmounted_dualaxis',
            'groundmounted_singleaxis_horizontal', 'groundmounted_singleaxis_vertical']:
            raise ValueError("Invalid installation type specified")
        if not (0 <= system_losses <= 1):
            raise ValueError("System losses must be between 0 and 1")

        self._installation = value

    @property
    def pv_module(self) -> dict:
        return self._pv_module

    @pv_module.setter
    def pv_module(self, value: dict) -> None:
        if not isinstance(value, dict):
            raise ValueError("PV module must be a dictionary")

        efficiency = value.get('efficiency')
        temperature_coefficient = value.get('temperature_coefficient')

        if not (0 < efficiency <= 1):
            raise ValueError("Efficiency must be a positive decimal not exceeding 1")
        if not isinstance(temperature_coefficient, float):
            raise ValueError("Temperature coefficient must be a float")

        self._pv_module = value

    # Results
    @property
    def results(self) -> pd.DataFrame:
        return self._results

    @results.setter
    def results(self, results_df: pd.DataFrame):
        self._results = results_df

    # Location, Weather, PV System 

    def _create_location(self) -> location.Location:
        """Creates a location object based on the environment settings.

        Returns:
            location.Location: A location object containing latitude, longitude, and timezone information.
        """
        print(f"INFO \t Creating location object...")

        timezone = self.get_timezone(self.environment.get('latitude'), self.environment.get('longitude'))

        print(f"\t > Lat.: {self.environment['latitude']} - Lon.: {self.environment['longitude']}")
        print(f"\t > Timezone: {timezone}")        

        return location.Location(
            latitude=self.environment['latitude'],
            longitude=self.environment['longitude'],
            tz=timezone
        )

    def _fetch_weather_data(self) -> pd.DataFrame:
        """Fetches hourly weather data with POA irradiance from PVGIS for the specified year.

        Returns:
            pd.DataFrame: A DataFrame containing the weather data with POA irradiance.
        """
        print(f"INFO \t Fetching hourly weather data with POA irradiance from PV GIS for the year {self.environment['year']} (Installation type: {self.installation['type']})...")

        # Initialize tilt and azimuth
        tilt = 0  # Default value
        azimuth = 180  # Default value 
        optimize_tilt = optimize_azimuth = True

        # Set the tracking and tilt/azimuth options
        if self.installation['type'] == 'groundmounted_fixed':
            trackingtype = 0
            # Correct a bug of PVGIS optimizer for low latitudes
            if abs(self.location.latitude) < 2:
                optimize_tilt = False
                optimize_azimuth = False
                tilt = 0
                azimuth = 180
        elif self.installation['type'] == 'groundmounted_singleaxis_horizontal':
            trackingtype = 1
        elif self.installation['type'] == 'groundmounted_singleaxis_vertical':
            trackingtype = 3
        elif self.installation['type'] == 'groundmounted_dualaxis':
            trackingtype = 2
        elif self.installation['type'] == 'rooftop':
            trackingtype = 0
            optimize_tilt = optimize_azimuth = False                 
            azimuth = 180
            tilt = 0
        else:
            raise ValueError(f"ERROR \t PV installation type is unknown.")

        # Get data from PVGIS
        weather_data_poa, meta, inputs = pvlib.iotools.get_pvgis_hourly(
            self.location.latitude,
            self.location.longitude,
            start=self.environment['year'],
            end=self.environment['year'],
            raddatabase='PVGIS-SARAH3',
            components=True,
            surface_tilt=tilt,
            surface_azimuth=azimuth,
            outputformat='json',
            usehorizon=True,
            userhorizon=None,
            pvcalculation=False,
            peakpower=None,
            pvtechchoice='crystSi',
            mountingplace='free',
            loss=0,
            trackingtype=trackingtype,
            optimal_surface_tilt=optimize_tilt,
            optimalangles=optimize_azimuth,
            url='https://re.jrc.ec.europa.eu/api/v5_3/',
            map_variables=True,
            timeout=30
        )

        # Get Diffuse and Global Irradiance in POA
        weather_data_poa['poa_diffuse'] = weather_data_poa['poa_sky_diffuse'] + weather_data_poa['poa_ground_diffuse']
        weather_data_poa['poa_global'] = weather_data_poa['poa_direct'] + weather_data_poa['poa_diffuse']

        # Convert the index to datetime
        weather_data_poa.index = pd.to_datetime(weather_data_poa.index)
        weather_data_poa.index = pd.to_datetime(weather_data_poa.index)

        # Convert the to local timezone
        weather_data_poa = weather_data_poa.tz_convert(self.location.tz)

        # Because of the converting of the time zone, the last rows could be those of the next year
        # Here, we detect how many rows we have and shift them to the beginning of the data
        tz = pytz.timezone(self.location.tz) 
        n = int(tz.localize(datetime.utcnow()).utcoffset().total_seconds() / 3600)  # Get the number of hours from UTC

        last_n_rows = weather_data_poa.tail(n)
        remaining_rows = weather_data_poa.head(len(weather_data_poa) - n)
        weather_data_poa = pd.concat([last_n_rows, remaining_rows])

        # Reattach the year information to the DataFrame
        weather_data_poa.index = pd.date_range(start=f'{self.environment["year"]}-01-01', periods=len(weather_data_poa), freq='h')

        # Print some information
        print(f"\t > Elevation: {meta['location']['elevation']} m ")
        print(f"\t > Mounting: {meta['mounting_system']}")
        print(f"\t > Global POA irradiance: {(weather_data_poa['poa_global'] * 1).sum() / 1000 } kWh/m2/yr ")
        print(f"\t > Diffuse POA irradiance: {(weather_data_poa['poa_diffuse'] * 1).sum() / 1000 } kWh/m2/yr ")

        # Update the angles (useful only for fixed mounting to calculate AOI losses)
        if self.installation['type'] == 'groundmounted_fixed':
            self._installation['tilt'] = meta['mounting_system']['fixed']['slope']['value']
            self._installation['azimuth'] = meta['mounting_system']['fixed']['azimuth']['value']
        else:
            self._installation['tilt'] = tilt
            self._installation['azimuth'] = azimuth

        return weather_data_poa

    def _create_pv_system(self) -> pvsystem.PVSystem:
        """Create a PV System with parameters compatible with the PVWatts model.

        Returns:
            pvsystem.PVSystem: A PVSystem object configured with module and inverter parameters.
        """
        print(f"INFO \t Creating a pvlib PVSystem object...")

        # Set mounting conditions for the thermal model
        mounting = 'freestanding'

        if self.installation['type'] == 'rooftop':
            mounting = 'insulated'

        system = pvsystem.PVSystem(
            module_parameters={
                'pdc0': self.pv_module['efficiency'] * 1000,  # Nominal DC power of 1 m2 of PV panel
                'gamma_pdc': self.pv_module['temperature_coefficient']  # Temperature coefficient (negative value)
            },
            inverter_parameters={
                'pdc0': self.pv_module['efficiency'] * 1000,  # Nominal DC power
                'eta_inv_nom': 1.0,  # Inverter efficiency of 100% (system losses are computed ex-post)
                'ac_0': self.pv_module['efficiency'] * 1000  # AC power rating assumed equal to DC power rating
            },
            temperature_model_parameters=pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['pvsyst'][mounting],  # PVSyst temperature model    
            surface_tilt=self.installation['tilt'],  # Used for AOI losses
            surface_azimuth=self.installation['azimuth']  # Used for AOI losses       
        )

        return system

    # Compute PV Production 

    def compute_pv_production(self) -> pd.DataFrame:
        """Compute the PV production and main KPIs using POA weather data.

        Returns:
            pd.DataFrame: A DataFrame containing PV production, performance ratio, capacity factor, 
                          operating temperature, and POA irradiance.
        """
        print(f"INFO \t Computing the hourly PV production...")

        # Initialize the model chain and run from POA
        mc = modelchain.ModelChain(self.pv_system, self.location, aoi_model="no_loss", spectral_model="no_loss")
        mc.run_model_from_poa(self.weather_data)

        # Correct to account for angle of incidence loss (problem when using the run_model_from_poa here)
        if self.installation['type'] == 'groundmounted_fixed' or self.installation['type'] == 'rooftop':
            pv_production = mc.results.dc * (1 - self.calculate_angular_losses(self.environment['latitude'] - self.installation['tilt'])/100)
        else:
            pv_production = mc.results.dc

        # Correct the DC power for system losses to get AC production
        pv_production = pv_production * (1 - self.installation['system_losses'])

        # Compute KPIs
        performance_ratio = pv_production / (self.pv_module['efficiency'] * self.weather_data['poa_global'])
        capacity_factor = pv_production / (self.pv_module['efficiency'] * 1000)
        operating_temperature = mc.results.cell_temperature

        # Create a DataFrame with the results
        results_df = pd.DataFrame({
            'PV Production (W/m2)': pv_production,
            'Performance Ratio': performance_ratio,
            'Capacity Factor': capacity_factor,
            'Temperature (C)': operating_temperature,
            'POA Irradiance (W/m2)': self.weather_data['poa_global']
        })

        print(f"\t > Energy yield: {(pv_production * 1).sum() / 1000} kWh/m2/yr")
        print(f"\t > Specific yield: {(pv_production * 1).sum() / (self.pv_module['efficiency'] * 1000)} kWh/kWp/yr")
        print(f"\t > Performance ratio: {(pv_production * 1).sum() / (self.pv_module['efficiency'] * self.weather_data['poa_global']).sum() }")
        print(f"\t > Average capacity factor: {capacity_factor.mean()} ")

        self._results = results_df

    # Helpers

    def get_timezone(self, lat: float, lon: float) -> str:
        """Get timezone string based on latitude and longitude.

        Args:
            lat (float): Latitude of the location.
            lon (float): Longitude of the location.

        Returns:
            str: The timezone string if found, otherwise None.
        """
        tf = TimezoneFinder()  # Initialize TimezoneFinder

        if lat is not None and lon is not None:
            tz_string = tf.timezone_at(lat=lat, lng=lon)
            if tz_string:
                return tz_string

        return None

    def calculate_angular_losses(self, lat_tilt_diff: float) -> float:
        """
        Calculate the angular losses for a standard m-Si module based on the difference
        between latitude and tilt angle.

        Martin, J.M. Ruiz,
        Calculation of the PV modules angular losses under field conditions by means of an analytical model,
        Solar Energy Materials and Solar Cells,
        Volume 70, Issue 1,
        2001,
        Pages 25-38,
        ISSN 0927-0248,
        https://doi.org/10.1016/S0927-0248(00)00408-6.

        Parameters:
        - lat_tilt_diff (float): The difference between latitude and tilt angle in degrees.

        Returns:
        - float: Angular losses as a percentage.
        """
        # Coefficients for the weighted quadratic fit model
        a = 11.3e-4
        b = -11.9e-3
        c = 2.87

        # Calculate angular losses
        angular_losses = a * lat_tilt_diff**2 + b * lat_tilt_diff + c
        return angular_losses   