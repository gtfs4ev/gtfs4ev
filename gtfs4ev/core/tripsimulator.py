# coding: utf-8

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from shapely.ops import substring
from shapely.geometry import LineString, Point
import folium
from folium.plugins import TimestampedGeoJson

from gtfs4ev.core.gtfsmanager import GTFSManager
from gtfs4ev.utils import helpers as hlp

class TripSimulator:
    """
    **Internal GTFS-based simulation engine** for a single trip.

    !!! warning "Internal API"
        This class is **not intended for direct use by end users**. 
        It is an internal building block used by the `FleetSimulator` class. 

    This class simulates the temporal and spatial operation of vehicles
    assigned to a single GTFS trip. Using stop times, shapes, and frequency
    definitions, it reconstructs:

    - The **event-level sequence** of a single vehicle along the trip
      (stops, terminals, and travelling segments)
    - The **fleet operation schedule**, accounting for headways, looping
      behavior, and potential transient regimes
    - The **time-resolved spatial trajectory** of each vehicle
    - An **interactive map visualization** of fleet movements

    The simulator relies on a pre-loaded `GTFSManager` instance.

    Notes:
        - Only GTFS trips with valid `frequencies.txt` entries are supported.
        - All times are assumed to refer to a single service day (00:00–23:59).
        - Shapes are assumed to be spatially consistent with stop locations.

    Attributes:
        gtfs_manager (GTFSManager): GTFS data manager providing access to GTFS tables.
        trip_id (str): Identifier of the GTFS trip being simulated.
        single_trip_sequence (pd.DataFrame or list): Event-level description of a single vehicle run (result - computed after simulation).
        fleet_operation (pd.DataFrame or list): Fleet-wide operational schedule (result - computed after simulation).

    Examples:
        >>> simulator = TripSimulator(manager, "trip_42")
        >>> simulator.compute_single_trip_sequence()
        >>> simulator.compute_fleet_operation()
        >>> traj = simulator.get_fleet_trajectory(time_step=120)
    """

    ## ============================================================
    ## Constructor
    ## ============================================================

    def __init__(self, gtfs_manager: GTFSManager, trip_id: str):
        """
        Initialize a TripSimulator for a given GTFS trip.

        This constructor binds the simulator to a GTFS dataset and validates
        that the requested trip exists.

        Args:
            gtfs_manager (GTFSManager): Instance managing the GTFS dataset.
            trip_id (str): Identifier of the trip to simulate.

        Raises:
            ValueError: If the trip ID is not found in the GTFS dataset.
        """
        self.gtfs_manager = gtfs_manager
        self.trip_id = trip_id

        self._single_trip_sequence = None
        self._fleet_operation = None                

    ## ============================================================
    ## Attributes
    ## ============================================================

    @property
    def gtfs_manager(self) -> GTFSManager:
        """
        GTFS data manager associated with the simulator.

        Returns:
            GTFSManager: The GTFS manager instance.
        """        
        return self._gtfs_manager

    @gtfs_manager.setter
    def gtfs_manager(self, value):
        if not isinstance(value, object):  # Ideally, check against GTFSManager class
            raise ValueError("gtfs_manager must be a valid GTFSManager instance.")
        self._gtfs_manager = value

    @property
    def trip_id(self) -> str:
        """
        Identifier of the simulated GTFS trip.

        Returns:
            str: Trip identifier.
        """
        return self._trip_id

    @trip_id.setter
    def trip_id(self, value):
        if self.gtfs_manager is None:
            raise ValueError("gtfs_manager must be set before setting trip_id.")
        if value not in self.gtfs_manager.trips['trip_id'].values:
            raise ValueError(f"Trip ID {value} not found in GTFS data.")
        self._trip_id = value

    @property
    def single_trip_sequence(self) -> pd.DataFrame:
        """
        Event-level sequence of a single vehicle performing the trip.

        The sequence is ordered in time and contains alternating events such as:
        - `at_terminal`
        - `at_stop`
        - `travelling`

        Each event includes duration, distance, cumulative metrics, and geometry.

        Returns:
            pd.DataFrame or list[dict]: Structured representation of the trip events.
        """
        return self._single_trip_sequence

    @property
    def fleet_operation(self) -> pd.DataFrame:
        """
        Fleet-wide operation schedule for the simulated trip.

        Each entry corresponds to a vehicle and includes:
        - Time intervals of operation and non-operation
        - Number of trip repetitions (possibly fractional)
        - Aggregated travel, stop, and terminal times
        - Total distance and operation duration

        Returns:
            pd.DataFrame or list[dict]: Fleet operation description.
        """
        return self._fleet_operation

    ## ============================================================
    ## Fleet operation simulation
    ## ============================================================

    def compute_single_trip_sequence(self) -> None:
        """
        Compute the detailed event sequence for a single vehicle trip.

        This method reconstructs the full temporal and spatial evolution
        of one vehicle running the trip by:

        - Ordering stops using GTFS stop times
        - Projecting stops onto the trip shape
        - Computing inter-stop travel distances and durations
        - Generating a sequence of discrete events (stops, terminals, travel)

        The result is stored internally in `self.single_trip_sequence`.

        Returns:
            None
        """
        self._single_trip_sequence = []

        # --- Step 1: Filter and sort stop times for the trip ---
        # Use query to filter and copy the dataframe
        stop_times = self.gtfs_manager.stop_times.query("trip_id == @self.trip_id").copy()
        stop_times.sort_values("arrival_time", inplace=True)
        first_arrival = stop_times.iloc[0]["arrival_time"]
        stop_times["arrival_offset"] = (stop_times["arrival_time"] - first_arrival).dt.total_seconds()
        stop_times["departure_offset"] = (stop_times["departure_time"] - first_arrival).dt.total_seconds()

        # --- Step 2: Get stop geometries from a pre-cached dictionary ---
        # If not already cached on the gtfs_manager, do it once and store it.
        if not hasattr(self.gtfs_manager, "_stop_geometry_dict"):
            # Convert stop_id to string for consistent lookups
            stops = self.gtfs_manager.stops.copy()
            stops["stop_id"] = stops["stop_id"].astype(str)
            self.gtfs_manager._stop_geometry_dict = stops.set_index("stop_id")["geometry"].to_dict()
        stop_geometry_dict = self.gtfs_manager._stop_geometry_dict

        # Ensure the stop_times stop IDs are strings
        stop_times["stop_id"] = stop_times["stop_id"].astype(str)
        # Build the dictionary only for stops in this trip
        stop_ids_trip = stop_times["stop_id"].unique()
        stop_geometries = {stop_id:  # We assume the stored geometry is already a Shapely geometry;
                             # If needed, you can wrap it with Point(geom.x, geom.y) – but that may be redundant.
                             stop_geometry_dict[stop_id]
                             for stop_id in stop_ids_trip
                             if stop_id in stop_geometry_dict}

        # --- Step 3: Retrieve the trip shape and compute distances ---
        trip_shape = self.gtfs_manager.get_shape(self.trip_id)

        # Build an array of stop IDs (in order)
        stop_ids = stop_times["stop_id"].to_numpy()
        
        # Compute distances along the trip for each stop.
        # (This uses the find_closest_point function.)
        stop_distances = np.array([
            trip_shape.project(hlp.find_closest_point(trip_shape, stop_geometries[stop_id]))
            for stop_id in stop_ids
        ])

        # --- Validate stop order along shape ---
        # In case stop sequence for trip_id {self.trip_id} does not follow the order of the shape geometry.
        # Reverse shape if strictly decreasing
        if np.all(np.diff(stop_distances) <= 0):
            trip_shape = LineString(list(trip_shape.coords)[::-1])
            stop_distances = np.array([
                trip_shape.project(hlp.find_closest_point(trip_shape, stop_geometries[stop_id]))
                for stop_id in stop_ids
            ])

        arrival_times = stop_times["arrival_offset"].to_numpy()
        departure_times = stop_times["departure_offset"].to_numpy()
        # Compute travel durations vectorized
        travel_durations = np.maximum(0, arrival_times[1:] - departure_times[:-1])

        # --- Step 4: Build travel sequence event-by-event ---
        sequence = []
        cumulative_distance = 0
        cumulative_duration = 0

        # Add first event (at_terminal)
        sequence.append({
            "status": "at_terminal",
            "distance": 0,
            "duration": departure_times[0] - arrival_times[0],
            "distance_from_start": cumulative_distance,
            "duration_from_start": cumulative_duration,
            "location": stop_geometries[stop_ids[0]],
            "stop_id": stop_ids[0]
        })
        cumulative_duration += departure_times[0] - arrival_times[0]

        # Optionally, add a local cache for substring calls if many segments are identical:
        sub_linestring_cache = {}

        for i in range(len(stop_ids) - 1):
            sid_current = stop_ids[i]
            sid_next = stop_ids[i + 1]
            start_distance = stop_distances[i]
            end_distance = stop_distances[i + 1]

            # Define a helper to get a substring with caching
            def get_substring(s, e):
                key = (s, e)
                if key not in sub_linestring_cache:
                    sub_linestring_cache[key] = substring(trip_shape, s, e)
                return sub_linestring_cache[key]

            # Handle potential wrap-around of the trip shape:
            if start_distance > end_distance:
                sub_linestring1 = get_substring(start_distance, trip_shape.length)
                sub_linestring2 = get_substring(0, end_distance)
                # Create a combined LineString from the two segments
                sub_linestring = LineString(list(sub_linestring1.coords) + list(sub_linestring2.coords))
                travel_distance_km = hlp.length_km(sub_linestring1) + hlp.length_km(sub_linestring2)
            elif start_distance != end_distance:
                sub_linestring = get_substring(start_distance, end_distance)
                travel_distance_km = hlp.length_km(sub_linestring)
            else:
                sub_linestring = None
                travel_distance_km = 0

            # Travelling event:

            cumulative_distance += travel_distance_km
            cumulative_duration += travel_durations[i]
            
            sequence.append({
                "status": "travelling",
                "distance": travel_distance_km,
                "duration": travel_durations[i],
                "distance_from_start": cumulative_distance,
                "duration_from_start": cumulative_duration,
                "location": sub_linestring,  # LineString geometry
                "stop_id": None
            })            

            # Stop event:
            sequence.append({
                "status": "at_terminal" if i + 1 == len(stop_ids) - 1 else "at_stop",
                "distance": 0,
                "duration": departure_times[i + 1] - arrival_times[i + 1],
                "distance_from_start": cumulative_distance,
                "duration_from_start": cumulative_duration,
                "location": stop_geometries[sid_next],
                "stop_id": sid_next
            })
            cumulative_duration += departure_times[i + 1] - arrival_times[i + 1]

        self._single_trip_sequence = sequence

    def compute_fleet_operation(self, transient_regime: bool = False) -> None:
        """
        Compute the fleet operation required to serve the trip frequencies.

        This method expands the single-trip sequence into a fleet-level
        operational plan based on GTFS frequency definitions. It supports:

        - Looping operation (vehicles already in circulation)
        - Transient regimes (vehicles progressively entering service)
        - Partial trip repetitions at service boundaries
        - Aggregation of distance and time metrics per vehicle

        The result is stored internally in `self.fleet_operation`.

        Args:
            transient_regime (bool, optional): If True, vehicles start operation progressively after the service start time. If False, routes are assumed to be already populated with vehicles at the beginning of service. Defaults to False.

        Raises:
            ValueError: If no frequency data is available or if trip duration is zero.

        Returns:
            None
        """
        self._fleet_operation = []

        self.compute_single_trip_sequence()
        base_seq = self._single_trip_sequence
        trip_duration = sum(event['duration'] for event in base_seq)
        if trip_duration <= 0:
            raise ValueError("Trip duration must be positive.")

        # Total distance of one full trip
        full_trip_distance = sum(
            event["distance"] for event in base_seq if event["status"] == "travelling"
        )

        # Retrieve trip frequencies
        trip_freq = self.gtfs_manager.frequencies[self.gtfs_manager.frequencies['trip_id'] == self.trip_id]
        if trip_freq.empty:
            raise ValueError(f"No frequency data available for trip ID {self.trip_id}.")

        num_vehicles = self.max_vehicles_in_operation()
        durations = np.array([event['duration'] for event in base_seq])
        cum_times = np.concatenate(([0], np.cumsum(durations)))  # cumulative time from trip start

        # Store results per vehicle
        vehicle_records = {}

        for _, freq in trip_freq.iterrows():
            headway = freq['headway_secs']
            freq_start_sec = (freq['start_time'].hour * 3600 + freq['start_time'].minute * 60 + freq['start_time'].second)
            freq_end_sec = (freq['end_time'].hour * 3600 + freq['end_time'].minute * 60 + freq['end_time'].second)

            vehicles_in_operation = min(num_vehicles, max(1, round(trip_duration / headway)))
            vehicle_indices = np.arange(vehicles_in_operation)

            for veh in vehicle_indices:
                vehicle_id = f"{self.trip_id}_{veh}"

                if transient_regime:
                    # Vehicles are injected after the start time, spaced by headway
                    trip_start_time = freq_start_sec + veh * headway
                else:
                    # Vehicles are in looped operation (may begin before freq_start)
                    trip_start_time = freq_start_sec - veh * headway

                if vehicle_id not in vehicle_records:
                    vehicle_records[vehicle_id] = {
                        "vehicle_id": vehicle_id,
                        "travel_sequences": [],
                        "trip_repetitions": 0.0,
                        "total_distance_km": 0.0,
                        "total_operation_time_s": 0.0,  # Initialize total duration to 0
                        "terminal_time_s": 0.0,
                        "stop_time_s": 0.0,
                        "travel_time_s": 0.0
                    }

                repetition_start = trip_start_time
                while repetition_start < freq_end_sec + trip_duration:

                    if repetition_start >= freq_end_sec:
                        break  # Don't start new trips after end of service

                    start_abs = repetition_start
                    end_abs = repetition_start + trip_duration

                    # Apply clipping logic based on the transient_regime flag
                    clipped_start = max(start_abs, freq_start_sec)
                    if transient_regime:
                        clipped_end = end_abs
                    else:
                        clipped_end = min(end_abs, freq_end_sec)

                    if clipped_end <= clipped_start:
                        break  # nothing to store

                    # Compute the fraction of trip done
                    clipped_duration = clipped_end - clipped_start
                    repetition_fraction = clipped_duration / trip_duration

                    # Convert start/end to HH:MM:SS
                    start_str = pd.to_datetime(clipped_start, unit="s").strftime("%H:%M:%S")
                    end_str = pd.to_datetime(clipped_end, unit="s").strftime("%H:%M:%S")

                    # Iterate over the sequence of events for this trip
                    for event in base_seq:
                        event_status = event["status"]
                        event_duration = event["duration"]
                        event_distance = event["distance"]

                        # Accumulate the times based on the event status
                        if event_status == "at_terminal":
                            vehicle_records[vehicle_id]["terminal_time_s"] += event_duration * repetition_fraction
                        elif event_status == "at_stop":
                            vehicle_records[vehicle_id]["stop_time_s"] += event_duration * repetition_fraction
                        elif event_status == "travelling":
                            vehicle_records[vehicle_id]["travel_time_s"] += event_duration * repetition_fraction

                    # Store the travel sequence information
                    vehicle_records[vehicle_id]["travel_sequences"].append({
                        "start_time": start_str,
                        "end_time": end_str,
                        "offset_from_start": int(clipped_start - start_abs),  # how far from original start
                    })

                    # Update total travel distance and duration for the vehicle
                    vehicle_records[vehicle_id]["trip_repetitions"] += repetition_fraction
                    vehicle_records[vehicle_id]["total_distance_km"] += full_trip_distance * repetition_fraction
                    vehicle_records[vehicle_id]["total_operation_time_s"] += trip_duration * repetition_fraction

                    repetition_start += trip_duration

        # Fill the gaps with a vehicle that is not operation

        fleet_result = []

        for record in vehicle_records.values():
            filled_sequences = []
            prev_end = 0  # seconds since midnight

            for seq in record["travel_sequences"]:
                start_dt = datetime.strptime(seq["start_time"], "%H:%M:%S")
                end_dt = datetime.strptime(seq["end_time"], "%H:%M:%S")

                start_sec = start_dt.hour * 3600 + start_dt.minute * 60 + start_dt.second
                end_sec = end_dt.hour * 3600 + end_dt.minute * 60 + end_dt.second

                if start_sec > prev_end:
                    start_str = f"{prev_end // 3600:02}:{(prev_end % 3600) // 60:02}:{prev_end % 60:02}"
                    end_str = f"{start_sec // 3600:02}:{(start_sec % 3600) // 60:02}:{start_sec % 60:02}"
                    filled_sequences.append({
                        "start_time": start_str,
                        "end_time": end_str,
                        "offset_from_start": 0,
                        "operating": False
                    })

                seq["operating"] = True
                filled_sequences.append(seq)
                prev_end = end_sec

            if prev_end < 86399:
                start_str = f"{prev_end // 3600:02}:{(prev_end % 3600) // 60:02}:{prev_end % 60:02}"
                end_str = "23:59:59"  # explicitly clamp to end of day
                filled_sequences.append({
                    "start_time": start_str,
                    "end_time": end_str,
                    "offset_from_start": 0,
                    "operating": False
                })

            record["travel_sequences"] = filled_sequences
            fleet_result.append(record)

        # Make sur the latest not operating session starts at the same hour for every vehicle (end of operating hours)

        # Step 1: Find the latest start time among the last non-operating sessions
        last_start_seconds = []

        latest_end_time = self.gtfs_manager.frequencies['end_time'].max()
        latest_end_sec = latest_end_time.hour * 3600 + latest_end_time.minute * 60 + latest_end_time.second
        latest_start_str = f"{latest_end_sec // 3600:02}:{(latest_end_sec % 3600) // 60:02}:{latest_end_sec % 60:02}"

        for record in vehicle_records.values():
            sequences = record["travel_sequences"]
            if not sequences:
                continue

            last_seq = sequences[-1]
            if not last_seq.get("operating", True):
                dt = datetime.strptime(last_seq["start_time"], "%H:%M:%S")
                this_start_sec = dt.hour * 3600 + dt.minute * 60 + dt.second

                if this_start_sec < latest_end_sec:
                    # (1) Modify last session to end at latest start
                    last_seq["end_time"] = latest_start_str

                    # (2) Append new non-operating session to fill the rest of the day
                    sequences.append({
                        "start_time": latest_start_str,
                        "end_time": "23:59:59",
                        "offset_from_start": 0,
                        "operating": False
                    })

        # Compute the latest start time
        if last_start_seconds:
            latest_start_sec = max(last_start_seconds)
            latest_start_str = f"{latest_start_sec // 3600:02}:{(latest_start_sec % 3600) // 60:02}:{latest_start_sec % 60:02}"

            # Step 2: Adjust sequences for all vehicles
            for record in vehicle_records.values():
                sequences = record["travel_sequences"]
                if not sequences:
                    continue

                last_seq = sequences[-1]
                if not last_seq.get("operating", True):
                    dt = datetime.strptime(last_seq["start_time"], "%H:%M:%S")
                    this_start_sec = dt.hour * 3600 + dt.minute * 60 + dt.second

                    if this_start_sec < latest_start_sec:
                        # (1) Modify last session to end at latest start
                        last_seq["end_time"] = latest_start_str

                        # (2) Append new non-operating session to fill the rest of the day
                        sequences.append({
                            "start_time": latest_start_str,
                            "end_time": "23:59:59",
                            "offset_from_start": 0,
                            "operating": False
                        })
                else:
                    print(last_seq)


        self._fleet_operation = fleet_result

    ## ============================================================
    ## Helpers
    ## ============================================================

    def trip_duration_sec(self) -> int:
        """
        Compute the total duration of the trip.

        The duration is defined as the time difference between the first
        arrival and the last departure in the GTFS stop times.

        Returns:
            int: Trip duration in seconds.
        """
        trip_stop_times = self.gtfs_manager.stop_times[self.gtfs_manager.stop_times['trip_id'] == self.trip_id]
        duration = (trip_stop_times['departure_time'].iloc[-1] - trip_stop_times['arrival_time'].iloc[0]).total_seconds()

        return duration

    def max_vehicles_in_operation(self) -> int:
        """
        Estimate the maximum number of vehicles required to operate the trip.

        The estimate is based on:
        - Trip duration
        - Minimum headway across all frequency definitions

        Returns:
            int: Estimated maximum number of vehicles.

        Raises:
            ValueError: If no frequency data is available for the trip.
        """
        # Get the frequencies for this trip
        trip_frequencies = self.gtfs_manager.frequencies[self.gtfs_manager.frequencies['trip_id'] == self.trip_id]

        if trip_frequencies.empty:
            raise ValueError(f"No frequency data available for trip ID {self.trip_id}.")

        # Find the highest frequency (lowest headway)
        min_headway = trip_frequencies['headway_secs'].min()

        # Compute the number of vehicles needed
        max_num_vehicles = self.trip_duration_sec() / min_headway

        return max(1, round(max_num_vehicles))

    ## ============================================================
    ## Trajectory reconstruction and visualization
    ## ============================================================

    def get_fleet_trajectory(self, time_step: int) -> pd.DataFrame:
        """
        Compute time-resolved spatial trajectories for the entire fleet.

        Using the precomputed fleet operation and single-trip sequence,
        this method reconstructs vehicle locations at a fixed temporal
        resolution throughout the day.

        Each vehicle is represented by a row, and each column corresponds
        to a time step. Cells contain Shapely `Point` geometries or `None`
        when the vehicle is not operating.

        Args:
            time_step (int): Temporal resolution in seconds.

        Returns:
            pd.DataFrame: Fleet trajectory matrix indexed by vehicle ID
            and time (HH:MM:SS).
        """   
        # Ensure that fleet operation data exists; if not, compute it.
        if not hasattr(self, '_fleet_operation') or self._fleet_operation is None:
            self.compute_fleet_operation()
        
        # Ensure that we have the base trip sequence.
        if not hasattr(self, '_single_trip_sequence') or self._single_trip_sequence is None:
            self.compute_single_trip_sequence()
        base_seq = self._single_trip_sequence

        # Compute overall trip duration and extract event data from base_seq.
        trip_duration = sum(event['duration'] for event in base_seq)
        event_durations = np.array([event["duration"] for event in base_seq])
        event_statuses = np.array([event["status"] for event in base_seq])
        event_locations = np.array([event["location"] for event in base_seq])
        event_cumulative_durations = np.concatenate(([0], np.cumsum(event_durations)))

        # Create a daily time range with the given time_step.
        time_range = pd.date_range("00:00:00", "23:59:59", freq=f"{time_step}s")
        times = time_range.time
        times_sec = np.array([t.hour * 3600 + t.minute * 60 + t.second for t in times])
        
        # Prepare an empty array to store computed Point objects.
        num_vehicles = len(self._fleet_operation)
        fleet_location = np.empty((num_vehicles, len(times)), dtype=object)
        fleet_location.fill(None)

        # For each vehicle operation record, loop over its travel sequences.
        for veh_idx, vehicle_record in enumerate(self._fleet_operation):
            # Loop on every travel segment for this vehicle.
            for seq in vehicle_record["travel_sequences"]:
                # Skip the intervals where the vehicles are not in operation
                if not seq["operating"]: 
                    continue
                # Convert travel sequence start/end times (HH:MM:SS) into seconds-from-midnight.
                seq_start = pd.to_datetime(seq["start_time"], format="%H:%M:%S").time()
                seq_end = pd.to_datetime(seq["end_time"], format="%H:%M:%S").time()
                seq_start_sec = seq_start.hour * 3600 + seq_start.minute * 60 + seq_start.second
                seq_end_sec = seq_end.hour * 3600 + seq_end.minute * 60 + seq_end.second

                # Identify the time indices in the overall time range that fall within this travel sequence.
                indices = np.where((times_sec >= seq_start_sec) & (times_sec < seq_end_sec))[0]
                if len(indices) == 0:
                    continue

                # Retrieve the offset from start for this sequence.
                offset = seq.get("offset_from_start", 0)
                # For the found time indices, compute the elapsed time since the beginning of the sequence.
                time_indices_secs = times_sec[indices]
                # Adjust the elapsed time for the vehicle's initial offset and use modulo for wrap-around.
                durations = ((time_indices_secs - seq_start_sec + offset) % trip_duration)
                
                # Determine which event each duration falls into.
                status_indices = np.maximum(0, np.searchsorted(event_cumulative_durations, durations, side="left") - 1)
                
                # Now, for each time step in the sequence, compute the Point location.
                locations = []
                for i, dur in enumerate(durations):
                    idx = status_indices[i]
                    status = event_statuses[idx]
                    if status in ["at_stop", "at_terminal"]:
                        # For stop or terminal events, use the event location directly.
                        locations.append(event_locations[idx])
                    else:
                        # Determine the fraction of travel completed between stops.
                        prev_stop_time = event_cumulative_durations[idx]
                        next_stop_time = event_cumulative_durations[idx + 1]
                        time_in_travel = dur - prev_stop_time
                        total_travel_time = next_stop_time - prev_stop_time
                        travel_fraction = time_in_travel / total_travel_time if total_travel_time > 0 else 0

                        # For the 'travelling' status, compute the correct position along the travel linestring.
                        travel_linestring = event_locations[idx]
                        if isinstance(travel_linestring, LineString) and travel_linestring.length > 0:
                            travel_distance = travel_linestring.length * travel_fraction
                            travel_point = substring(travel_linestring, 0, travel_distance).interpolate(1.0, normalized=True)
                            locations.append(travel_point)
                        else:
                            locations.append(None)
                
                # Store the computed locations at the appropriate time indices.
                fleet_location[veh_idx, indices] = locations                
    
        # Create the final DataFrame with vehicle IDs as the index.
        vehicle_ids = [record.get("vehicle_id", f"veh_{i}") for i, record in enumerate(self._fleet_operation)]

        return pd.DataFrame(fleet_location, index=vehicle_ids, columns=times)

    def get_fleet_trajectory_map(self, fleet_trajectory: pd.DataFrame) -> folium.Map:
        """
        Generate an interactive time-slider map of fleet trajectories.

        This method visualizes the simulated fleet operation using a Folium
        map with a temporal slider. Vehicle positions are animated over time,
        and the trip shape is displayed as a reference.

        Notes:
            - This visualization currently only supports a **2-minute time step**.
            - Vehicles at identical locations are slightly jittered for clarity.

        Args:
            fleet_trajectory (pd.DataFrame): Output of `get_fleet_trajectory`.

        Returns:
            folium.Map: Interactive map with animated vehicle movements.

        Raises:
            ValueError: If no valid trajectory data is available or if the time step is incompatible.
        """    
        # Transform the fleet operation DataFrame into a long-format DataFrame
        data = []
        for vehicle_id in fleet_trajectory.index:
            for time_key, record in fleet_trajectory.loc[vehicle_id].items():
                if record is None or not isinstance(record, Point):
                    continue  # Skip invalid data

                # Extract lat/lon from the Point geometry
                longitude, latitude = record.x, record.y

                # Convert time_key to a datetime object
                if isinstance(time_key, str):
                    time_obj = datetime.strptime(time_key, "%H:%M:%S").time()
                else:
                    time_obj = time_key

                timestamp = datetime.combine(date.today(), time_obj)
                data.append({
                    "vehicle_id": vehicle_id,
                    "time": timestamp,
                    "latitude": latitude,
                    "longitude": longitude
                })

        # Convert to DataFrame and check validity
        df = pd.DataFrame(data)
        if df.empty:
            raise ValueError("No valid location data to plot.")

        # Sort and clean data
        df.sort_values(by=["time", "vehicle_id"], inplace=True)
        df.drop_duplicates(subset=["time", "vehicle_id"], inplace=True)

        # Calculate time step in minutes
        unique_times = df["time"].drop_duplicates().sort_values().reset_index(drop=True)
        if len(unique_times) < 2:
            raise ValueError("Not enough timestamps to determine time step.")

        min_step = int(unique_times.diff().dropna().min().total_seconds() // 60)  # in minutes
        if min_step != 2:
            raise ValueError("Invalid time step. This function only works with a 2-minute time step.")

        # Create base map centered at the first valid position
        first_position = df.iloc[0]
        m = folium.Map(location=[first_position['latitude'], first_position['longitude']], zoom_start=12)

        # Add trip shape (polyline) to the map if available
        trip_linestring = self.gtfs_manager.get_shape(self.trip_id)
        if trip_linestring and not trip_linestring.is_empty:
            if hasattr(trip_linestring, "coords"):
                shape_coords = [(lat, lon) for lon, lat in trip_linestring.coords]  # Folium expects (lat, lon)
                folium.PolyLine(
                    shape_coords,
                    color="black",
                    weight=4,
                    opacity=0.7,
                    tooltip="Trip Shape"
                ).add_to(m)

        # Organize data into time-based FeatureCollections
        time_grouped = df.groupby("time")
        features = []

        for timestamp, group in time_grouped:
            vehicle_points = []
            grouped_locations = group.groupby(["latitude", "longitude"])
            for (lat, lon), sub_group in grouped_locations:
                num_vehicles = len(sub_group)
                if num_vehicles > 1:
                    jitter_offsets = np.linspace(-0.0005, 0.0005, num_vehicles)  # Small lat/lon shifts
                    for (offset, row) in zip(jitter_offsets, sub_group.itertuples()):
                        vehicle_points.append({
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [lon + offset, lat + offset]  # Apply small shift
                            },
                            "properties": {
                                "time": timestamp.isoformat(),
                                "popup": f"Vehicle {row.vehicle_id}\nTime: {timestamp.strftime('%H:%M:%S')}"
                            }
                        })
                else:
                    row = sub_group.iloc[0]
                    vehicle_points.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        },
                        "properties": {
                            "time": timestamp.isoformat(),
                            "popup": f"Vehicle {row.vehicle_id}\nTime: {timestamp.strftime('%H:%M:%S')}"
                        }
                    })
            features.append({
                "type": "FeatureCollection",
                "features": vehicle_points
            })

        # Add dynamic time slider
        TimestampedGeoJson({
            "type": "FeatureCollection",
            "features": features
        },
        period="PT2M",
        duration="PT1M",
        add_last_point=False,
        auto_play=False,
        loop=True,
        max_speed=1,
        loop_button=True,
        date_options='YYYY-MM-DD HH:mm:ss',
        time_slider_drag_update=True).add_to(m)

        return m


