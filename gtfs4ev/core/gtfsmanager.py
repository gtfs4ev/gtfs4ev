# coding: utf-8

import os
import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
from shapely.geometry import LineString, Point, box
from shapely.ops import transform, snap
import pyproj
from pyproj import Geod
from contextlib import redirect_stdout
import folium
from folium.plugins import MarkerCluster
from folium import PolyLine
from shapely.ops import substring

from gtfs4ev import helpers as hlp

class GTFSManager:
    """A class to represent and manage a GTFS feed data.

    Holds and curates the GTFS feed. This class reads a GTFS data folder and provides methods
    to check data consistency, filter and clean data, and extract general transit indicators.

    Note: The calendar_dates.txt file is not considered, so some service exceptions are not handled.
    """

    def __init__(self, gtfs_datafolder: str):
        print("=========================================")
        print(f"INFO \t Creation of a GTFSManager object.")
        print("=========================================")

        self.gtfs_datafolder = gtfs_datafolder

        # Load the datasets using the helper method
        self._agency = self.load_csv("agency.txt", 
                                      columns=['agency_id', 'agency_name', 'agency_url', 'agency_timezone'],
                                      dtypes={col: str for col in ['agency_id', 'agency_name', 'agency_url', 'agency_timezone']})
        self._trips = self.load_csv("trips.txt",
                                     columns=['route_id', 'service_id', 'trip_id', 'shape_id'],
                                     dtypes={col: str for col in ['route_id', 'service_id', 'trip_id', 'shape_id']})
        self._routes = self.load_csv("routes.txt", 
                                      columns=['route_id', 'agency_id', 'route_short_name', 'route_long_name'],
                                      dtypes={col: str for col in ['route_id', 'agency_id', 'route_short_name', 'route_long_name']})
        self._stop_times = self.load_csv("stop_times.txt",
                                          columns=['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'],
                                          dtypes={'trip_id': str, 'arrival_time': str, 'departure_time': str, 'stop_id': str, 'stop_sequence': int},
                                          parse_dates={'arrival_time': '%H:%M:%S', 'departure_time': '%H:%M:%S'})
        self._calendar = self.load_csv("calendar.txt",
                                        dtypes={'service_id': str, 'monday': bool, 'tuesday': bool, 'wednesday': bool,
                                                'thursday': bool, 'friday': bool, 'saturday': bool, 'sunday': bool,
                                                'start_date': str, 'end_date': str},
                                        parse_dates={'start_date': '%Y%m%d', 'end_date': '%Y%m%d'})
        self._frequencies = self.load_csv("frequencies.txt",
                                           columns=['trip_id', 'start_time', 'end_time', 'headway_secs'],
                                           dtypes={'trip_id': str, 'start_time': str, 'end_time': str, 'headway_secs': int},
                                           parse_dates={'start_time': '%H:%M:%S', 'end_time': '%H:%M:%S'},
                                           replace_times={'24:00:00': '23:59:59'})
        self._stops = self.load_stops()
        self._shapes = self.load_shapes()

        print("INFO \t Successful initialization of the GTFSManager. The GTFS feed could now be analyzed, cleaned, or filtered.")

    # Properties and Setters

    @property
    def gtfs_datafolder(self) -> str:
        """str: The absolute path to the GTFS data folder as a string."""
        if self._gtfs_datafolder is None:
            raise ValueError("GTFS data folder has not been set.")
        return self._gtfs_datafolder

    @gtfs_datafolder.setter
    def gtfs_datafolder(self, abs_path):
        abs_path = Path(abs_path)  # Convert string to Path object
        required_files = ['agency.txt', 'routes.txt', 'stop_times.txt', 'calendar.txt',
                          'frequencies.txt', 'shapes.txt', 'stops.txt', 'trips.txt']
        if not abs_path.is_dir():
            raise FileNotFoundError(f"ERROR \t Unable to find folder: /{abs_folder}")
        for file_name in required_files:
            if not (abs_path / file_name).exists():
                print(f"ERROR \t Required file '{file_name}' is missing")
        for file_name in os.listdir(abs_path):
            if file_name not in required_files:
                print(f"INFO \t The data folder contains a GTFS file that is not required: '{file_name}'.")
        self._gtfs_datafolder = abs_path

    @property
    def agency(self) -> pd.DataFrame:
        """pd.DataFrame: The GTFS agency data."""
        return self._agency

    @property
    def routes(self) -> pd.DataFrame:
        """pd.DataFrame: The GTFS routes data."""
        return self._routes

    @property
    def stop_times(self) -> pd.DataFrame:
        """pd.DataFrame: The GTFS stop times data."""
        return self._stop_times

    @property
    def stops(self) -> pd.DataFrame:
        """pd.DataFrame: The GTFS stops data, including geometries."""
        return self._stops

    @property
    def trips(self) -> pd.DataFrame:
        """pd.DataFrame: The GTFS trips data."""
        return self._trips

    @property
    def calendar(self) -> pd.DataFrame:
        """pd.DataFrame: The GTFS calendar data."""
        return self._calendar

    @property
    def frequencies(self) -> pd.DataFrame:
        """pd.DataFrame: The GTFS frequencies data."""
        return self._frequencies

    @property
    def shapes(self) -> pd.DataFrame:
        """pd.DataFrame: The GTFS shapes data as a GeoDataFrame containing LineString geometries."""
        return self._shapes

    # Data validation

    def check_agency(self):
        """ Checking that each agency is associated with at least one route
        """
        problem = False
        agency_ids = self.agency['agency_id']
        
        all_present = agency_ids.isin(self.routes['agency_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some agencies are not associated with any route.")

        return problem 

    def check_shapes(self):
        """ Checking that each shape is associated with at least one trip
        """
        problem = False

        shape_ids = self.shapes['shape_id']
        
        all_present = shape_ids.isin(self.trips['shape_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some shapes are not associated with any trip.")

        return problem

    def check_stops(self):
        """ Checking that each stop is associated with at least one stop time
        """
        problem = False

        stop_ids = self.stops['stop_id']
        
        all_present = stop_ids.isin(self.stop_times['stop_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some stops are not associated with any stop time.")

        return problem

    def check_frequencies(self):
        """ Checking that each frequency is associated with at least one stop trip
        """
        problem = False

        trip_ids = self.frequencies['trip_id']
        
        all_present = trip_ids.isin(self.trips['trip_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some frequencies are not associated with any trip.")

        return problem

    def check_calendar(self):
        """ Checking that each service is associated with at least one stop trip
        """
        problem = False

        service_ids = self.calendar['service_id']
        
        all_present = service_ids.isin(self.trips['service_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some services are not associated with any trip.")

        return problem

    def check_routes(self):
        """ Checking that each route is associated with an agency and trips
        """
        problem = False

        route_ids = self.routes['route_id']
        agency_ids = self.routes['agency_id']
        
        all_present = route_ids.isin(self.trips['route_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some routes are not associated with any trip.")

        all_present = agency_ids.isin(self.agency['agency_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some routes are not associated with any agency.")

        return problem

    def check_stop_times(self):
        """ Checking that each stop time is associated with trips and stops
        """
        problem = False

        stop_ids = self.stop_times['stop_id']
        trip_ids = self.stop_times['trip_id']
        
        all_present = stop_ids.isin(self.stops['stop_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some stop times are not associated with any stop.")

        all_present = trip_ids.isin(self.trips['trip_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some stop times are not associated with any trip.")

        return problem

    def check_trips(self):
        """ Checking that each trips is associated with the needed information: routes, service, frequencies, stop_times, shapes
        """
        problem = False

        route_ids = self.trips['route_id']
        service_ids = self.trips['service_id']
        trip_ids = self.trips['trip_id']
        shape_ids = self.trips['shape_id']
        
        all_present = route_ids.isin(self.routes['route_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some trips are not associated with any route.")

        all_present = service_ids.isin(self.calendar['service_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some trips are not associated with any agency.")

        all_present = trip_ids.isin(self.frequencies['trip_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some trips are not associated with any frequencies. Could cause important issues.")

        all_present = trip_ids.isin(self.stop_times['trip_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some trips are not associated with any stop times.")  

        all_present = shape_ids.isin(self.shapes['shape_id']).all()
        if not all_present:
            problem = True
            print("ALERT \t Data consistency: some trips are not associated with any shape.")

        return problem

    def check_all(self): 
        """ Checking the consistency of all the data
        """
        print("INFO \t Checking data consistency.")

        consistent = False

        agency_status = self.check_agency()
        shapes_status = self.check_shapes()
        stops_status = self.check_stops()
        frequencies_status = self.check_frequencies()
        calendar_status = self.check_calendar()
        routes_status = self.check_routes()
        stop_times_status = self.check_stop_times()
        trips_status = self.check_trips()

        if (not agency_status and not shapes_status and not stops_status and not frequencies_status and not calendar_status and not routes_status and not stop_times_status and not trips_status):
            print("\t No problems found.")
            consistent = True

        return consistent

    # Data cleaning 

    def clean_agency(self):
        """Deletes each agency not associated with any route."""
        self._agency = self._agency[self._agency['agency_id'].isin(self._routes['agency_id'])]

    def clean_shapes(self):
        """Deletes each shape not associated with any trip."""
        self._shapes = self._shapes[self._shapes['shape_id'].isin(self._trips['shape_id'])]

    def clean_stops(self):
        """Deletes each stop not associated with any stop_time."""
        self._stops = self._stops[self._stops['stop_id'].isin(self._stop_times['stop_id'])]

    def clean_frequencies(self):
        """Deletes each frequency not associated with any trip."""
        self._frequencies = self._frequencies[self._frequencies['trip_id'].isin(self._trips['trip_id'])]

    def clean_calendar(self):
        """Deletes each service not associated with any trip."""
        self._calendar = self._calendar[self._calendar['service_id'].isin(self._trips['service_id'])]

    def clean_routes(self):
        """Deletes each route not associated with any agency or trip."""
        self._routes = self._routes[self._routes['agency_id'].isin(self._agency['agency_id'])]
        self._routes = self._routes[self._routes['route_id'].isin(self._trips['route_id'])]

    def clean_stop_times(self):
        """Deletes each stop_time not associated with any trip or stop."""
        self.drop_useless_stop_times()
        self._stop_times = self._stop_times[self._stop_times['trip_id'].isin(self._trips['trip_id'])]

    def clean_trips(self):
        """Deletes each trip not associated with any route, service, frequency, stop_time, or shape."""
        self.drop_useless_trips()
        self._trips = self._trips[self._trips['route_id'].isin(self._routes['route_id'])]
        self._trips = self._trips[self._trips['service_id'].isin(self._calendar['service_id'])]

    def drop_useless_trips(self):
        """ Delete the trips which are not useable because they are not assiocated to any frequency, stop_times, or shapes
        Warning: This ensures that all the trips could be simulated by gtfs4ev but could alter data consistency: do a cleaning to ensure th whole dataset is consistent
        """
        trips = self.trips
        frequencies = self.frequencies
        stop_times = self.stop_times
        shapes = self.shapes

        # Drop trips not associated to any frequency
        merged_df = trips.merge(frequencies, on='trip_id')        
        cleaned_trips = trips[trips['trip_id'].isin(merged_df['trip_id'])] # Only keep the useful rows

        # Drop trips not associated to any stop_times
        merged_df = cleaned_trips.merge(stop_times, on='trip_id')        
        cleaned_trips_2 = cleaned_trips[cleaned_trips['trip_id'].isin(merged_df['trip_id'])] # Only keep the useful rows

        # Drop trips not associated to any shape
        merged_df = cleaned_trips_2.merge(shapes, on='shape_id')        
        cleaned_trips_3 = cleaned_trips_2[cleaned_trips_2['shape_id'].isin(merged_df['shape_id'])] # Only keep the useful rows

        self._trips = cleaned_trips_3

    def drop_useless_stop_times(self):
        """ Delete the stop_times which are not useable because they are not assiocated to any stop
        Warning: This ensures that all the stop_times could be simulated by gtfs4ev but could alter data consistency: do a cleaning to ensure th whole dataset is consistent
        """        
        stop_times = self.stop_times
        stops = self.stops

        # Drop stop_times not associated to any frequency
        merged_df = stop_times.merge(stops, on='stop_id')        
        cleaned_stop_times = stop_times[stop_times['stop_id'].isin(merged_df['stop_id'])] # Only keep the useful rows

        self._stop_times = cleaned_stop_times

    def clean_all(self):
        """Executes all the cleaning functions to ensure a fully consistent and usable dataset."""

        # Clean everything and repeat until consistency is reached
        print("INFO \t Starting GTFS dataset cleaning to ensure a fully consistent and usable dataset...")
        print("\t - Removing unreferenced agencies, routes, trips, stops, stop_times, frequencies, and shapes.")
        print("\t - Ensuring all trips, stop_times, shapes, and frequencies are correctly linked.")

        with redirect_stdout(None): 
            while not self.check_all():
                self.clean_agency()
                self.clean_shapes()
                self.clean_stops()
                self.clean_frequencies()
                self.clean_calendar()
                self.clean_routes() 
                self.clean_stop_times()
                self.clean_trips()

        print("\t Data cleaning completed successfully. The dataset is now consistent and ready for simulation.")

    def trim_tripshapes_to_terminal_locations(self):
        """
        Efficiently trims trip shapes to start and end at the closest terminal stops
        without modifying stop locations.
        """
        print("INFO \t Trimming trip shapes using terminal location projections. This might take some time...")

        # Merge trips and shapes once
        trip_shapes = pd.merge(
            self.trips[['trip_id', 'shape_id']],
            self.shapes[['shape_id', 'geometry']],
            on='shape_id',
            how='left'
        )

        # Group stop_times and get first/last stop geometries
        stop_times_with_geom = pd.merge(
            self.stop_times,
            self.stops[['stop_id', 'geometry']],
            on='stop_id',
            how='left'
        )

        # Prepare dictionary to hold trimmed shapes by shape_id
        trimmed_shapes = {}

        for shape_id, shape_group in trip_shapes.groupby("shape_id"):
            linestring = shape_group['geometry'].iloc[0]

            # Get all trips using this shape
            for _, row in shape_group.iterrows():
                trip_id = row['trip_id']

                stops = stop_times_with_geom[stop_times_with_geom['trip_id'] == trip_id]

                if stops.empty:
                    continue

                first_geom = stops.iloc[0]['geometry']
                last_geom = stops.iloc[-1]['geometry']

                first_proj = linestring.project(hlp.find_closest_point(linestring, first_geom))
                last_proj = linestring.project(hlp.find_closest_point(linestring, last_geom))

                if first_proj > last_proj:
                    first_proj, last_proj = last_proj, first_proj

                trimmed_line = substring(linestring, first_proj, last_proj)

                # Only update if this trip is the "canonical" one for this shape
                # Or store all versions if you want trip-specific shapes (optional)
                trimmed_shapes[shape_id] = trimmed_line
                break  # Just do one trimming per shape_id (if all trips share the same shape)

        # Apply the trimmed shapes back
        for shape_id, trimmed_geom in trimmed_shapes.items():
            self._shapes.loc[self._shapes['shape_id'] == shape_id, 'geometry'] = trimmed_geom

    # Data filtering

    def filter_services(self, service_id, clean_all = True):
        """ Drop the data belonging to a specific service, for example to consider only weekdays
        """

        print(f"INFO \t Filtering out all the data from the following service: {service_id}")

        # Drop the trips associated to a specific service       
        self._trips.drop(self.trips[self.trips['service_id'] == service_id].index, inplace=True)

        # Clean all the dataset to be consistent with the trips
        if clean_all:
            with redirect_stdout(None): 
                self.clean_all()

    def filter_agency(self, agency_id, clean_all = True):
        """ Drop the data belonging to a specific agency, for example to consider only paratransit
        """

        print(f"INFO \t Filtering out all the data from the following agency: {agency_id}")

        # Drop the routes associated to a specific agency       
        self._routes.drop(self.routes[self.routes['agency_id'] == agency_id].index, inplace=True)

        # Clean all the dataset to be consistent with the routes
        if clean_all:
            with redirect_stdout(None): 
                self.clean_all()

    # Data analysis

    """ Basic aggregated indicators """

    def show_general_info(self):
        """Displays general information about the GTFS feed in a clean and readable format."""        

        print("INFO \t 🚍 GTFS Feed Summary:")

        print(f"\t {'Trips:':<15} {self.trips.shape[0]:>8}  |  {'Routes:':<15} {self.routes.shape[0]:>8}  |  {'Services:':<15} {self.calendar.shape[0]:>8}")
        print(f"\t {'Stops:':<15} {self.stops.shape[0]:>8}  |  {'Stop Times:':<15} {self.stop_times.shape[0]:>8}  |  {'Frequencies:':<15} {self.frequencies.shape[0]:>8}")
        print(f"\t {'Agencies:':<15} {self.agency.shape[0]:>8}  |  {'Shapes:':<15} {self.shapes.shape[0]:>8}")
        

        # Check if the number of trips is exactly twice the number of routes (potential round-trip pattern)
        if self.trips.shape[0] / self.routes.shape[0] == 2.0:
            print("\t🔹Note: The number of trips is twice the number of routes, suggesting that each route is associated with a round trip.")

        # Analyze frequency consistency
        group_sizes = self.frequencies.groupby('trip_id').size().reset_index(name='row_count')
        are_all_values_same = group_sizes['row_count'].nunique() == 1

        print(f"\t Simulation area: {self.simulation_area_km2()} km2")

        if are_all_values_same:
            print("\t Temporal Analysis:")
            print(f"\t  - Frequency intervals: {group_sizes['row_count'][0]}")
            print(f"\t  - Operating from {self.frequencies['start_time'].min()} to {self.frequencies['end_time'].max()}")
        else:
            print("\t🔹Note: The number of frequency intervals is inconsistent across trips.")


    """ Per trip transit indicators """

    def trip_length_km(self, trip_id, geodesic = True) -> float:
        """ Calculates the lenght in km of a trip.
        """
        # Get the shape of the corresponding trip and project it into epsg:3857 crs
        gdf = pd.merge(self.trips, self.shapes[['shape_id', 'geometry']], on='shape_id', how='left')
        linestring = gdf.loc[gdf['trip_id'] == trip_id, 'geometry'].iloc[0]

        return hlp.length_km(linestring)

    def trip_duration_sec(self, trip_id) -> float:
        """ Calculates the time in sec of a trip
        """
        trip_stop_times = self.stop_times[self.stop_times['trip_id'] == trip_id]
        duration = (trip_stop_times['arrival_time'].iloc[-1] - trip_stop_times['departure_time'].iloc[0]).total_seconds()

        return duration

    def ave_distance_between_stops(self, trip_id, correct_stop_loc = True) -> float:
        """ Calculates the average distance between stops in km along a trip
        If needed, the stop location can by clipped to the closest point along the shape of the trip
        """
        gdf = pd.merge(self.trips, self.shapes[['shape_id', 'geometry']], on='shape_id', how='left')
        linestring = gdf.loc[gdf['trip_id'] == trip_id, 'geometry'].iloc[0]

        web_mercator_projection = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform 

        linestring_web_mercator_projection = transform(web_mercator_projection, linestring)

        # 2. Create a table which contains the stop times for the trip, the stop name and geometry
        filtered_stop_times = self.stop_times[self.stop_times['trip_id'] == trip_id]        
        result_df = pd.merge(filtered_stop_times, self.stops[['stop_id', 'stop_name', 'geometry']], on='stop_id', how='left') # Merge the filtered_df with the stop_points_df on 'stop_id'

        # 3. Add the closest point on the linestring path as the point for the stop
        if correct_stop_loc:
            result_df['closest_point_on_path'] = result_df['geometry'].apply(lambda point: hlp.find_closest_point(linestring, point))
        else:
            result_df['closest_point_on_path'] = result_df['geometry']

        result_df['stop_dist_km'] = .0

        # Define the projection from WGS84 (EPSG:4326) to Web Mercator (EPSG:3857) 
        for i in range(1, len(result_df)):
            current_stop = result_df.iloc[i] 
            previous_stop = result_df.iloc[i - 1]

            start_point = transform(web_mercator_projection, previous_stop['closest_point_on_path'])
            end_point = transform(web_mercator_projection, current_stop['closest_point_on_path'])

            distance_along_line = abs(linestring_web_mercator_projection.project(start_point) - linestring_web_mercator_projection.project(end_point)) 

            result_df.loc[result_df.index == i, 'stop_dist_km'] = distance_along_line

        return result_df['stop_dist_km'].mean() / 1000.0

    def n_stops(self, trip_id) -> int:
        """ Number of stops of a trip
        """        
        stop_times = self.stop_times       
        n_stops = stop_times.groupby('trip_id').size().reset_index(name='row_count')

        return n_stops.loc[n_stops['trip_id'] == trip_id, 'row_count'].iloc[0]

    """ Per stop transit indicators """

    def stop_frequencies(self) -> int:
        """ Returns the number of times a stop is used by all trips
        """
        stop_times = self.stop_times

        stop_counts = stop_times.groupby('stop_id').size().reset_index(name='count')
        stop_counts = pd.merge(stop_counts, self.stops[['stop_id', 'geometry']], on='stop_id', how='left')
        
        return stop_counts

    """ Global transit indicators """

    def bounding_box(self) -> box:
        """ Returns the bounding box for the simulation    
        """
        gdf = self.shapes

        self.min_latitude = gdf['geometry'].apply(lambda line: line.bounds[1]).min()
        self.max_latitude = gdf['geometry'].apply(lambda line: line.bounds[3]).max()
        self.min_longitude = gdf['geometry'].apply(lambda line: line.bounds[0]).min()
        self.max_longitude = gdf['geometry'].apply(lambda line: line.bounds[2]).max()

        return box(self.min_longitude, self.min_latitude, self.max_longitude, self.max_latitude)

    def simulation_area_km2(self) -> float:
        """ Calculates the simulation area in km2
        """
        # Create a GeoDataFrame with the bounding box
        gdf_bbox = gpd.GeoDataFrame(geometry=[self.bounding_box()], crs='epsg:4326')

        # Reproject the GeoDataFrame to EPSG:3857
        gdf_bbox_web_mercator = gdf_bbox.to_crs('epsg:3857')

        # Calculate the area in square kilometers
        area_km2 = gdf_bbox_web_mercator['geometry'].area / 1e6  # Convert square meters to square kilometers

        return area_km2[0]  

    def trip_length_km_all(self) -> float:
        """ Length of all trips
        """        
        gdf = pd.merge(self.trips, self.shapes[['shape_id', 'geometry']], on='shape_id', how='left')

        gdf['trip_length_km'] = gdf['trip_id'].apply(self.trip_length_km)

        return gdf       

    def ave_distance_between_stops_all(self, correct_stop_loc = True) -> float:
        """ Average distance between stops in km of all trips
        """        
        gdf = pd.merge(self.trips, self.shapes[['shape_id', 'geometry']], on='shape_id', how='left')

        gdf['stop_dist_km'] = gdf['trip_id'].apply(lambda trip_id: self.ave_distance_between_stops(trip_id, correct_stop_loc=correct_stop_loc))
        gdf['n_stops'] = gdf['trip_id'].apply(self.n_stops)

        return gdf

    def trip_statistics(self) -> dict:
        """ Calculates some general statitistics regarding the trips
        """   
        number_of_trips = len(self.trips)
        number_of_routes = len(self.routes)
        gdf = self.trip_length_km_all()

        # Calculate the minimum, maximum, average, and standard deviation of the number of rows per trip_id
        statistics = {
            'total_trips': number_of_trips,
            'total_trip_len_km': gdf['trip_length_km'].sum(),
            'ave_trip_len_km': gdf['trip_length_km'].mean(),
            'min_trip_len_km': gdf['trip_length_km'].min(),
            'max_trip_len_km': gdf['trip_length_km'].max(), 
            'trip_to_route_ratio': number_of_trips / number_of_routes
        }
        
        return statistics

    def stop_statistics(self) -> dict:
        """ Calculates some general statistics regarding the number of stops
        """
        # Add the route information to the stop_times by merging the two DataFrames on 'trip_id'
        stop_times = pd.merge(self.stop_times, self.trips[['trip_id', 'route_id']], on='trip_id', how='left')

        number_of_stops = len(self.stops)
        number_of_trips = len(self.trips)
        number_of_routes = len(self.routes)

        # Calculate the minimum, maximum, average, and standard deviation of the number of rows per trip_id
        statistics = {
            'total_stops': number_of_stops,
            'min_stops_per_trip': stop_times.groupby('trip_id').size().min(),
            'max_stops_per_trip': stop_times.groupby('trip_id').size().max(),
            'std_dev_stops_per_trip': stop_times.groupby('trip_id').size().std(),
            'ave_stops_per_trip': stop_times.groupby('trip_id').size().mean(),
            'ave_stops_per_route': stop_times.groupby('route_id').size().mean(),
            'stops_to_trips_ratio': number_of_stops / number_of_trips,
            'stops_to_routes_ratio': number_of_stops / number_of_routes            
        }
        
        return statistics 

    # Data manipulation

    def add_idle_time_terminals(self, mean_idle_time_s, std_idle_time_s):
        """
        Adds an idle time to the terminal of each trip, drawn from a normal distribution.
        This idle time is split between the first and the last stop.

        Parameters:
            mean_idle_time_s (float): Mean idle time in seconds.
            std_idle_time_s (float): Standard deviation of idle time in seconds.
        """
        print(f"INFO \t Adding terminal idle time (mean={mean_idle_time_s}s, std={std_idle_time_s}s)")

        # Ensure stop_times is sorted
        self.stop_times.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)

        # Identify first and last stops for each trip
        first_stop_indices = self.stop_times.groupby('trip_id')['stop_sequence'].idxmin()
        last_stop_indices = self.stop_times.groupby('trip_id')['stop_sequence'].idxmax()

        # Convert time columns to datetime if needed
        time_cols = ['arrival_time', 'departure_time']
        for col in time_cols:
            self.stop_times[col] = pd.to_datetime(self.stop_times[col])

        # Loop over each trip and apply individual idle times
        for trip_id in self.stop_times['trip_id'].unique():
            idle_time = max(0, np.random.normal(mean_idle_time_s, std_idle_time_s))  # prevent negative values
            idle_delta = pd.to_timedelta(idle_time / 2, unit='s')

            first_idx = first_stop_indices[trip_id]
            last_idx = last_stop_indices[trip_id]

            self.stop_times.loc[first_idx, 'departure_time'] += idle_delta
            self.stop_times.loc[last_idx, 'departure_time'] += idle_delta

            # Shift all stops after the first by half the idle time
            mask = (self.stop_times['trip_id'] == trip_id) & (self.stop_times.index > first_idx)
            self.stop_times.loc[mask, time_cols] += idle_delta

    def add_idle_time_stops(self, mean_idle_time_s, std_idle_time_s):
        """
        Adds a random idle time to all intermediate stops (excluding the first and last) of each trip.
        The idle time is added to the departure_time only (i.e., increases dwell time).

        Parameters:
            mean_idle_time_s (float): Mean idle time in seconds.
            std_idle_time_s (float): Standard deviation of idle time in seconds.
        """
        print(f"INFO \t Adding random stop idle time (mean={mean_idle_time_s}s, std={std_idle_time_s}s)")

        self.stop_times.sort_values(by=['trip_id', 'stop_sequence'], inplace=True)

        time_cols = ['arrival_time', 'departure_time']
        for col in time_cols:
            self.stop_times[col] = pd.to_datetime(self.stop_times[col])

        for trip_id, trip_df in self.stop_times.groupby('trip_id'):
            stop_indices = trip_df.index.tolist()
            if len(stop_indices) <= 2:
                continue  # no intermediate stops

            for idx in stop_indices[1:-1]:  # intermediate stops only
                idle_time = max(0, np.random.normal(mean_idle_time_s, std_idle_time_s))
                idle_delta = pd.to_timedelta(idle_time, unit='s')

                # Extend dwell time at this stop
                self.stop_times.loc[idx, 'departure_time'] += idle_delta

                # Shift all following stops (both arrival and departure)
                following_mask = (self.stop_times['trip_id'] == trip_id) & (self.stop_times.index > idx)
                self.stop_times.loc[following_mask, time_cols] += idle_delta

    # Helper methods

    def load_csv(self, filename, columns=None, dtypes=None, parse_dates=None, replace_times=None):
        """
        Generic helper method to load a CSV file with optional column selection,
        data type conversion, and date parsing.
        """
        file_path = self.gtfs_datafolder / filename
        try:
            df = pd.read_csv(file_path, usecols=columns, dtype=dtypes)
            if replace_times:
                for col in ['start_time', 'end_time']:
                    if col in df.columns:
                        df[col] = df[col].str.replace('24:00:00', replace_times.get('24:00:00', '23:59:59'))
            if parse_dates:
                for col, fmt in parse_dates.items():
                    df[col] = pd.to_datetime(df[col], format=fmt)
        except Exception as e:
            raise ValueError(f"ERROR \t Problem loading {filename}.") from e
        return df

    def load_stops(self):
        """Loads and returns the stops GeoDataFrame."""
        file_path = self.gtfs_datafolder / "stops.txt"
        try:
            df = pd.read_csv(file_path, usecols=['stop_id', 'stop_name', 'stop_lat', 'stop_lon'],
                             dtype={'stop_id': str, 'stop_name': str, 'stop_lat': float, 'stop_lon': float})
            geometry = [Point(lon, lat) for lon, lat in zip(df['stop_lon'], df['stop_lat'])]
            df.drop(['stop_lon', 'stop_lat'], axis=1, inplace=True)
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
        except Exception as e:
            raise ValueError("ERROR \t Problem creating GeoDataFrame from stops.txt.") from e
        return gdf

    def load_shapes(self):
        """Loads and returns the shapes GeoDataFrame as LineStrings."""
        file_path = self.gtfs_datafolder / "shapes.txt"
        try:
            df = pd.read_csv(file_path, usecols=['shape_id', 'shape_pt_lat', 'shape_pt_lon'],
                             dtype={'shape_id': str, 'shape_pt_lat': float, 'shape_pt_lon': float})
            grouped = df.groupby('shape_id').apply(lambda x: LineString(zip(x['shape_pt_lon'], x['shape_pt_lat'])))
            gdf = gpd.GeoDataFrame(geometry=grouped, crs="EPSG:4326").reset_index()
        except Exception as e:
            raise ValueError("ERROR \t Problem creating GeoDataFrame from shapes.txt.") from e
        return gdf

    def get_shape(self, trip_id):
        """ Get the shape of a trip_id as a LineString Object
        """
        gdf = pd.merge(self.trips, self.shapes[['shape_id', 'geometry']], on='shape_id', how='left')
        linestring = gdf.loc[gdf['trip_id'] == trip_id, 'geometry'].iloc[0]

        return linestring

    def get_stop_locations(self, trip_id):
        """ Get a list of the coordinates of all the stops belonging to a trip 
        """
        gdf = pd.merge(self.stop_times, self.stops[['stop_id', 'geometry']], on='stop_id', how='left')       
        coordinates = gdf.loc[gdf['trip_id'] == trip_id, 'geometry']

        return coordinates.tolist()

    # Export and visualisation

    def export_to_csv(self, output_folder: str):
        """
        Export the loaded GTFS data back into CSV files.
        
        Args:
            output_folder (str): Path to the folder where CSVs will be saved.
        """
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        print("INFO \t Exporting GTFS data to CSV...")

        export_map = {
            "agency.txt": self.agency,
            "routes.txt": self.routes,
            "stop_times.txt": self.stop_times,
            "calendar.txt": self.calendar,
            "frequencies.txt": self.frequencies,
            "stops.txt": self.stops,  
            "trips.txt": self.trips,
            "shapes.txt": self.shapes  # will handle below
        }

        # Export everything except shapes.txt first
        for filename, df in export_map.items():
            if filename != "shapes.txt":
                try:
                    # Create a temporary copy of the dataframe
                    temp_df = df.copy()

                    # Reformat time columns to strings during export (without modifying the class attributes)
                    time_cols = ['arrival_time', 'departure_time', 'start_time', 'end_time']
                    for col in time_cols:
                        if col in temp_df.columns and pd.api.types.is_datetime64_any_dtype(temp_df[col]):
                            temp_df[col] = temp_df[col].dt.strftime('%H:%M:%S')  # Convert datetime to string

                    # Handle the calendar.txt export
                    if filename == "calendar.txt":
                        # Replace True with 1 and False with 0
                        bool_cols = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                        for col in bool_cols:
                            if col in temp_df.columns:
                                temp_df[col] = temp_df[col].astype(int)  # Convert booleans to 1/0

                        # Format start and end date in the format YYYYMMDD
                        if 'start_date' in temp_df.columns:
                            temp_df['start_date'] = temp_df['start_date'].dt.strftime('%Y%m%d')
                        if 'end_date' in temp_df.columns:
                            temp_df['end_date'] = temp_df['end_date'].dt.strftime('%Y%m%d')

                    # Handle stops.txt export (add lat/lon columns)
                    if filename == "stops.txt":
                        # Add lat/lon columns based on geometry
                        if 'geometry' in temp_df.columns:
                            temp_df['stop_lat'] = temp_df['geometry'].apply(lambda geom: geom.y if geom else None)
                            temp_df['stop_lon'] = temp_df['geometry'].apply(lambda geom: geom.x if geom else None)
                            temp_df = temp_df.drop(columns='geometry', errors='ignore')
                        
                    # Export the modified dataframe to CSV
                    temp_df.to_csv(output_path / filename, index=False)
                    print(f"\t - Exported: {filename}")
                except Exception as e:
                    print(f"\t - Failed to export {filename}: {e}")

        # Special handling for shapes.txt (rebuild the lat/lon structure)
        try:
            if isinstance(self.shapes, gpd.GeoDataFrame):
                shapes_df = self.shapes.copy()
                shapes_rows = []

                for _, row in shapes_df.iterrows():
                    shape_id = row['shape_id']
                    geometry = row['geometry']
                    if isinstance(geometry, LineString):
                        for i, (lon, lat) in enumerate(geometry.coords):
                            shapes_rows.append({
                                'shape_id': shape_id,
                                'shape_pt_lat': lat,
                                'shape_pt_lon': lon,
                                'shape_pt_sequence': i
                            })

                shapes_out = pd.DataFrame(shapes_rows)
                shapes_out.to_csv(output_path / "shapes.txt", index=False)
                print(f"\t - Exported: shapes.txt")
        except Exception as e:
            print(f"\t - Failed to export shapes.txt: {e}")

    def generate_network_map(self, filepath: str) -> None:
        print("INFO \t Generating a HTML map for the visualization of the GTFS network. This may take some time...")
        
        # Get the bounding box center
        bbox = self.bounding_box()
        center_lat = (bbox.bounds[1] + bbox.bounds[3]) / 2
        center_lon = (bbox.bounds[0] + bbox.bounds[2]) / 2
        
        # Initialize map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

        features = []

        for _, row in self.shapes.iterrows():
            # Get trip details for popup
            related_trips = self.trips[self.trips['shape_id'] == row['shape_id']]
            trip_info = "".join(
                f"<b>Trip ID:</b> {trip['trip_id']}<br>"
                f"<b>Length:</b> {self.trip_length_km(trip['trip_id']):.2f} km<br>"
                f"<b>Stops:</b> {self.n_stops(trip['trip_id'])}<br>"
                for _, trip in related_trips.iterrows()
            )
            popup_content = f"<b>Shape ID:</b> {row['shape_id']}<br>{trip_info if trip_info else 'No trip information'}"

            # Create GeoJSON feature
            feature = {
                "type": "Feature",
                "properties": {
                    "shape_id": row["shape_id"],
                    "popup": popup_content
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [(lon, lat) for lon, lat in row["geometry"].coords]
                }
            }
            features.append(feature)

        geojson_data = {"type": "FeatureCollection", "features": features}

        # Add route polylines using GeoJson
        route_layer = folium.GeoJson(
            geojson_data,
            name="Routes",
            style_function=lambda feature: {
                "color": "blue",
                "weight": 3,
                "opacity": 0.7,
            },
            highlight_function=lambda feature: {
                "color": "red",
                "weight": 5,
            },
            tooltip=folium.GeoJsonTooltip(fields=["popup"], aliases=["Info"], parse_html=True),
        ).add_to(m)

        # Add stop markers
        marker_cluster = MarkerCluster().add_to(m)
        for _, row in self.stops.iterrows():
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                popup=f"Stop: {row['stop_name']} ({row['stop_id']})",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(marker_cluster)

        # Save the map
        m.save(filepath)
        print(f"INFO \t Map successfully generated and saved to {filepath}")

    def generate_single_trip_map(self, trip_id: str, filepath: str = "trip_map.html", projected: bool = True):
        """
        Plots a specific trip and its stops on a Folium map.

        Parameters:
        - trip_id: ID of the trip to visualize.
        - filepath: Where to save the map HTML file.
        - projected: If True, project stops onto the trip shape.
        """
        print(f"INFO \t Creating a HTML map for trip {trip_id} (projecting stops to trip shapes={projected})...")

        # Get trip shape
        trip_row = self.trips[self.trips['trip_id'] == trip_id].iloc[0]
        shape_id = trip_row['shape_id']
        linestring = self.shapes[self.shapes['shape_id'] == shape_id]['geometry'].iloc[0]

        # Get and sort stops
        stop_times_trip = self.stop_times[self.stop_times['trip_id'] == trip_id].sort_values("stop_sequence")
        stops_with_geom = pd.merge(
            stop_times_trip,
            self.stops[['stop_id', 'stop_name', 'geometry']],
            on='stop_id',
            how='left'
        )

        # Project stops if requested
        if projected:
            stops_with_geom['proj_geom'] = stops_with_geom['geometry'].apply(
                lambda pt: hlp.find_closest_point(linestring, pt)
            )
            stop_points = stops_with_geom['proj_geom'].tolist()
        else:
            stop_points = stops_with_geom['geometry'].tolist()

        # Map center
        center_lat = stop_points[0].y
        center_lon = stop_points[0].x
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

        # Add trip shape
        folium.GeoJson(
            data=linestring.__geo_interface__,
            name="Trip Shape",
            style_function=lambda _: {
                "color": "blue",
                "weight": 4,
                "opacity": 0.8
            }
        ).add_to(m)

        # Add stop markers
        marker_cluster = MarkerCluster().add_to(m)
        for i, pt in enumerate(stop_points):
            stop_info = stops_with_geom.iloc[i]
            stop_name = stop_info['stop_name']
            stop_id = stop_info['stop_id']
            stop_seq = stop_info['stop_sequence']

            folium.Marker(
                location=[pt.y, pt.x],
                popup=f"<b>{stop_seq}. {stop_name}</b><br>ID: {stop_id}",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(marker_cluster)

        # Save map
        m.save(filepath)
        print(f"INFO \t Map saved to {filepath}")

    def generate_summary_report(self, filepath: str) -> None:
        """
        Exports key GTFS statistics and results to a text file.
        
        Parameters:
        filepath (str): The path where the statistics will be saved.
        """
        print("INFO \t Generating GTFS statistics and exporting the report to a text file...")
        
        trip_stats = self.trip_statistics()
        stop_stats = self.stop_statistics()
        area_km2 = self.simulation_area_km2()
        
        with open(filepath, 'w') as f:
            f.write("GTFS Feed Summary:\n")
            f.write("===========================================\n\n")
            f.write(f"Trips: {trip_stats['total_trips']}  |  Routes: {len(self.routes)}  |  Services: {len(self.calendar)}\n")
            f.write(f"Stops: {stop_stats['total_stops']}  |  Stop Times: {len(self.stop_times)}  |  Frequencies: {len(self.frequencies)}\n")
            f.write(f"Agencies: {len(self.agency)}  |  Shapes: {len(self.shapes)}\n\n")
            
            if trip_stats['trip_to_route_ratio'] == 2.0:
                f.write("Note: The number of trips is twice the number of routes, suggesting that each route is associated with a round trip.\n\n")
            
            f.write(f"Simulation area: {area_km2:.2f} km²\n\n")

            f.write("===========================================\n\n")
            
            f.write("Temporal Analysis:\n")
            f.write("=================\n\n")
            
            # Analyze frequency consistency
            group_sizes = self.frequencies.groupby('trip_id').size().reset_index(name='row_count')
            are_all_values_same = group_sizes['row_count'].nunique() == 1

            if are_all_values_same:
                f.write(f"Frequency intervals: {group_sizes['row_count'][0]} \n")
                f.write(f"Operating from {self.frequencies['start_time'].min()} to {self.frequencies['end_time'].max()}")
            else:
                f.write("\t Note: The number of frequency intervals is inconsistent across trips.")
            
            f.write("\n\nTrip Statistics:\n")
            f.write("=================\n\n")
            f.write(f"Total Trip Length (km): {trip_stats['total_trip_len_km']:.2f}\n")
            f.write(f"Average Trip Length (km): {trip_stats['ave_trip_len_km']:.2f}\n")
            f.write(f"Min Trip Length (km): {trip_stats['min_trip_len_km']:.2f}\n")
            f.write(f"Max Trip Length (km): {trip_stats['max_trip_len_km']:.2f}\n\n")
            
            f.write("Stop Statistics:\n")
            f.write("=================\n\n")
            f.write(f"Min Stops per Trip: {stop_stats['min_stops_per_trip']}\n")
            f.write(f"Max Stops per Trip: {stop_stats['max_stops_per_trip']}\n")
            f.write(f"Avg Stops per Trip: {stop_stats['ave_stops_per_trip']:.2f}\n")
            f.write(f"Avg Stops per Route: {stop_stats['ave_stops_per_route']:.2f}\n\n")
            
        print(f"INFO \t Statistics successfully exported to {filepath}")
