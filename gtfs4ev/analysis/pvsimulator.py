# coding: utf-8

import pvlib
from pvlib import location, pvsystem, modelchain
import pandas as pd
from timezonefinder import TimezoneFinder
import pytz
from datetime import datetime, timezone

class PVSimulator:
    """
    **PV production simulator** based on `pvlib` for a single location
    and a full reference year.

    The `PVSimulator` provides an end-to-end workflow to simulate **hourly
    photovoltaic electricity production** over a year, using PVGIS
    irradiance data and `pvlib`'s physical models.

    The simulator encapsulates:

    - **Geographical and temporal context** (location, timezone, reference year)
    - **PV module characteristics** (efficiency, temperature coefficient)
    - **Installation configuration** (mounting type, system losses)
    - **Weather data acquisition** with plane-of-array (POA) irradiance
    - **PV system modeling** via `pvlib.modelchain.ModelChain`
    - **Post-processing and KPI computation**

    Results are returned as a pandas DataFrame with hourly resolution and
    include both energy production and other key performance indicators.

    Notes:
        - The simulation is normalized per square meter of PV module area.
        - Weather data are sourced from PVGIS (SARAH3 database).
        - No degradation, curtailment, or grid constraints are modeled.
        - Inverter behavior is assumed ideal; system losses are applied ex-post.
        - The simulator is designed for **annual simulations** (single year).

    Attributes:
        environment (dict): Environmental configuration including latitude, longitude, and simulation year.
        installation (dict): Installation parameters such as mounting type, tilt/azimuth (derived), and system losses.
        pv_module (dict): PV module parameters including efficiency and temperature coefficient.
        location (pvlib.location.Location): pvlib Location object with timezone.
        weather_data (pd.DataFrame): Hourly POA weather data used for simulation.
        pv_system (pvlib.pvsystem.PVSystem): Configured PV system model.
        results (pd.DataFrame): Hourly simulation outputs and KPIs (computed after calling `compute_pv_production`).

    Presets:
        The simulator supports two predefined installation presets, which
        control mounting assumptions and irradiance processing:

        1. **freestanding_opt_tilt**: Ground-mounted or freestanding PV system. Surface tilt is optimized by PVGIS for maximum annual yield. Temperature model: freestanding (well-ventilated).

        2. **flat_roof**: Fixed horizontal installation (tilt = 0°, azimuth = 180°). No tilt optimization is applied. Temperature model: insulated (reduced ventilation).

    Examples:
        >>> env = {"latitude": 48.85, "longitude": 2.35, "year": 2023}
        >>> module = {"efficiency": 0.20, "temperature_coefficient": -0.004}
        >>> install = {"type": "freestanding_opt_tilt", "system_losses": 0.14}
        >>> sim = PVSimulator(env, module, install)
        >>> sim.compute_pv_production()
        >>> df = sim.results
    """

    ## ============================================================
    ## Constructor
    ## ============================================================

    def __init__(self, environment: dict, pv_module: dict, installation: dict):
        """
        Initialize a PVSimulator with environmental context, PV module
        characteristics, and installation settings.

        This constructor:
        - Validates all input dictionaries
        - Determines the local timezone from coordinates
        - Fetches hourly POA irradiance data from PVGIS
        - Instantiates a `pvlib.PVSystem` object ready for simulation

        Args:
            environment (dict): Environmental parameters with keys:
                - latitude (float): Site latitude in degrees.
                - longitude (float): Site longitude in degrees.
                - year (int): Reference year for the simulation.
            pv_module (dict): PV module parameters with keys:
                - efficiency (float): Module efficiency (0 < η ≤ 1).
                - temperature_coefficient (float): Power temperature coefficient (1/°C).
            installation (dict): Installation parameters with keys:
                - type (str): Installation type (`"freestanding_opt_tilt"` or `"flat_roof"`).
                - system_losses (float): Aggregate system losses (0–1).

        Raises:
            ValueError: If any input dictionary is invalid or contains out-of-range values.
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

    ## ============================================================
    ## Attributes 
    ## ============================================================

    @property
    def environment(self) -> dict:
        """
        Environmental configuration for the simulation.

        Contains geographical coordinates and the reference year.
        Validation ensures physically meaningful ranges.

        Returns:
            dict: Environment dictionary.
        """
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
        """
        PV installation configuration.

        Includes mounting type, system losses, and derived geometric
        parameters (tilt and azimuth).

        Returns:
            dict: Installation dictionary.
        """
        return self._installation

    @installation.setter
    def installation(self, value: dict) -> None:
        if not isinstance(value, dict):
            raise ValueError("Installation must be a dictionary")

        install_type = value.get('type')
        system_losses = value.get('system_losses')

        if install_type not in ['freestanding_opt_tilt', 'flat_roof']:
            raise ValueError("Invalid installation type specified")
        if not (0 <= system_losses <= 1):
            raise ValueError("System losses must be between 0 and 1")

        self._installation = value

    @property
    def pv_module(self) -> dict:
        """
        Photovoltaic module parameters.

        Defines conversion efficiency and temperature sensitivity
        used in PVWatts-style power modeling.

        Returns:
            dict: PV module dictionary.
        """
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
        """
        Simulation results and KPIs.

        Available after calling `compute_pv_production`.

        Returns:
            pd.DataFrame: Hourly PV production and performance indicators.
        """
        return self._results

    @results.setter
    def results(self, results_df: pd.DataFrame):
        self._results = results_df

    ## ============================================================
    ## Internal Model Construction
    ## ============================================================

    def _create_location(self) -> location.Location:
        """
        Create a `pvlib.Location` object from environmental parameters.

        The timezone is automatically inferred from latitude and longitude.

        Returns:
            pvlib.location.Location: Configured location object.
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
        """
        Retrieve hourly plane-of-array (POA) irradiance data from PVGIS.

        The method:
        - Requests SARAH3 satellite data from PVGIS
        - Applies optimal tilt when requested
        - Converts timestamps to local timezone
        - Reorders data to match the reference year exactly

        Returns:
            pd.DataFrame: Hourly POA weather data indexed by local datetime.
        """
        print(f"INFO \t Fetching hourly weather data with POA irradiance from PV GIS for the year {self.environment['year']} (Installation type: {self.installation['type']})...")


        # Default tilt/azimuth and optimization flags fixed horizontal panels
        tilt = 0
        azimuth = 180
        optimize_tilt = False
        optimize_azimuth = False

        # Determine tilt/azimuth optimization based on installation type
        if self.installation['type'] == 'freestanding_opt_tilt':
            optimize_tilt = True
            # Edge case: very low latitudes (PVGIS may return zero direct POA)
            if abs(self.location.latitude) < 1:
                optimize_tilt = False

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
            trackingtype=0,
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

        # Convert the to local timezone
        weather_data_poa = weather_data_poa.tz_convert(self.location.tz)

        # Because of the converting of the time zone, the last rows could be those of the next year
        # Here, we detect how many rows we have and shift them to the beginning of the data
        tz = pytz.timezone(self.location.tz)
        n = int(datetime.now(timezone.utc).astimezone(tz).utcoffset().total_seconds() / 3600)

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
        if self.installation['type'] == 'freestanding_opt_tilt':
            self._installation['tilt'] = meta['mounting_system']['fixed']['slope']['value']
        else:
            self._installation['tilt'] = tilt
        self._installation['azimuth'] = azimuth

        return weather_data_poa

    def _create_pv_system(self) -> pvsystem.PVSystem:
        """
        Create a `pvlib.PVSystem` instance.

        The system is configured for:
        - Per-m² normalized power output
        - Martin–Ruiz IAM model
        - PVSyst temperature model
        - Ideal inverter (losses applied separately)

        Returns:
            pvlib.pvsystem.PVSystem: Configured PV system.
        """

        print("INFO \t Creating a pvlib PVSystem object...")

        # Mounting choice for temperature model
        mounting = 'freestanding'
        if self.installation['type'] == 'flat_roof':
            mounting = 'insulated'

        system = pvsystem.PVSystem(
            surface_tilt=self.installation['tilt'],
            surface_azimuth=self.installation['azimuth'],

            module_parameters={
                # PVWatts-style per-m² normalization
                'pdc0': self.pv_module['efficiency'] * 1000,  # W/m²
                'gamma_pdc': self.pv_module['temperature_coefficient'],

                # Martin–Ruiz IAM parameters (typical for c-Si)
                'a_r': 0.16
            },

            inverter_parameters={
                # Ideal inverter, losses applied ex-post
                'pdc0': self.pv_module['efficiency'] * 1000,
                'eta_inv_nom': 1.0
            },

            temperature_model_parameters=
                pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['pvsyst'][mounting]
        )

        return system

    ## ============================================================
    ## Simulation Execution
    ## ============================================================

    def compute_pv_production(self) -> pd.DataFrame:
        """
        Compute hourly PV electricity production and key performance indicators.

        The simulation uses `pvlib.modelchain.ModelChain` driven by
        plane-of-array irradiance. System losses are applied after
        physical modeling.

        Computed outputs include:
        - AC PV production (W/m²)
        - Performance ratio
        - Capacity factor
        - Module operating temperature
        - POA irradiance

        Returns:
            pd.DataFrame: Hourly PV production and KPI time series.
        """
        print(f"INFO \t Computing the hourly PV production...")

        mc = modelchain.ModelChain(
            self.pv_system,
            self.location,
            aoi_model="martin_ruiz",
            spectral_model="no_loss"
        )

        mc.run_model_from_poa(self.weather_data)

        # AC power (W/m²), after AOI, temperature, with ideal inverter
        pv_ac = mc.results.ac

        # Correct the DC power for system losses to get AC production
        pv_production = pv_ac * (1 - self.installation['system_losses'])

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

    ## ============================================================
    ## Helpers
    ## ============================================================

    def get_timezone(self, lat: float, lon: float) -> str:
        """
        Get the timezone string from geographic coordinates.

        Args:
            lat (float): Latitude in degrees.
            lon (float): Longitude in degrees.

        Returns:
            str: Timezone identifier (e.g., "Europe/Paris"), or None if not found.
        """
        tf = TimezoneFinder()  # Initialize TimezoneFinder

        if lat is not None and lon is not None:
            tz_string = tf.timezone_at(lat=lat, lng=lon)
            if tz_string:
                return tz_string

        return None

