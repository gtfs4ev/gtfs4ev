# coding: utf-8

import pandas as pd
import sys
import multiprocessing as mp
import time
import gc

from gtfs4ev.core.gtfsmanager import GTFSManager
from gtfs4ev.core.tripsimulator import TripSimulator
from gtfs4ev.utils import helpers as hlp

class FleetSimulator:
    """
    **GTFS-based fleet simulation engine** for the entire vehicle fleet operating 
    on multiple trips.

    The `FleetSimulator` orchestrates multiple `TripSimulator` objects, acting as 
    a higher level engine for fleet-wide simulations. Results are aggregated into
    unified fleet-level outputs, including:

    - **Operational schedules** across multiple vehicles operating on different trips
    - **Aggregated travel event sequences** for all simulated vehicles
    - **Time-resolved spatial trajectories** and **map visualizations** of fleet movements

    Each trip is simulated independently using `TripSimulator` instances, and the
    results are merged into pandas DataFrames.

    Notes:
        - All trips are assumed to belong to the same GTFS feed and service day (GTFS data pre-processing is needed for a different behaviour).
        - Trip simulations are independent; no vehicle interlining is assumed.
        - Multiprocessing can be enabled to speed up large fleet simulations.
        - Time-resolved fleet trajectoriy calculation may be computationally expensive.

    Attributes:
        gtfs_manager (GTFSManager): GTFS data manager providing access to GTFS tables.
        trip_ids (list[str]): List of GTFS trip identifiers included in the simulation.
        fleet_operation (pd.DataFrame): Aggregated fleet operation schedule (result - computed after simulation).
        trip_travel_sequences (pd.DataFrame): Aggregated event-level travel sequences (result - computed after simulation).

    Examples:
        >>> simulator = FleetSimulator(manager, trip_ids=["trip_1", "trip_2"])
        >>> simulator.compute_fleet_operation()
        >>> fleet_df = simulator.fleet_operation
        >>> traj = simulator.get_fleet_trajectory(time_step=120)
    """

    ## ============================================================
    ## Constructor
    ## ============================================================
   
    def __init__(self, gtfs_manager: GTFSManager, trip_ids: str = None):
        """
        Initialize a FleetSimulator for a set of GTFS trips.

        This constructor binds the simulator to a GTFSManager and validates
        the list of trips to be simulated. If no trip IDs are provided, all
        available trips in the GTFS feed are selected.

        Args:
            gtfs_manager (GTFSManager): Instance managing the GTFS dataset.
            trip_ids (list[str], optional): List of trip IDs to simulate. If None, all trips in the GTFS feed are included.

        Raises:
            ValueError: If one or more trip IDs are not found in the GTFS dataset.
        """
        print("=========================================")
        print(f"INFO \t Creation of a FleetSimulator object.")
        print("=========================================")

        self.gtfs_manager = gtfs_manager
        self.trip_ids = trip_ids

        self._fleet_operation = None
        self._trip_travel_sequences = None

        print("INFO \t Successful initialization of the FleetSimulator. The fleet operation can now be simulated. ")
    
    ## ============================================================
    ## Attributes
    ## ============================================================

    @property
    def gtfs_manager(self) -> GTFSManager:
        """
        GTFS data manager associated with the fleet simulator.

        Returns:
            GTFSManager: The GTFS manager instance.
        """
        return self._gtfs_manager

    @gtfs_manager.setter
    def gtfs_manager(self, value):
        if not isinstance(value, object):  # Ideally, check against GTFSManager class
            raise ValueError("ERROR \t gtfs_manager must be a valid GTFSManager instance.")
        self._gtfs_manager = value
    
    @property
    def trip_ids(self) -> list:
        """
        List of GTFS trip identifiers included in the fleet simulation.

        Returns:
            list[str]: Trip IDs simulated by the fleet simulator.
        """
        return self._trip_ids
    
    @trip_ids.setter
    def trip_ids(self, value):
        """Sets the list of trip IDs, ensuring they exist in the GTFS feed."""
        available_trips = set(self.gtfs_manager.trips["trip_id"].unique())
        
        if value is None:
            self._trip_ids = list(available_trips)
        else:
            invalid_trips = [trip for trip in value if trip not in available_trips]
            if invalid_trips:
                raise ValueError(f"ERROR \t Some trip IDs do not exist in the GTFS feed: {invalid_trips}")
            self._trip_ids = value

    @property
    def fleet_operation(self) -> pd.DataFrame:
        """
        Aggregated fleet-wide operation schedule.

        Each row corresponds to a simulated vehicle-trip combination and
        includes operational metrics such as:

        - Operation start and end times
        - Number of trip repetitions
        - Travel, stop, and terminal durations
        - Total distance and active time

        Returns:
            pd.DataFrame: Fleet operation description.
        """
        return self._fleet_operation

    @property
    def trip_travel_sequences(self) -> pd.DataFrame:
        """
        Aggregated event-level travel sequences for all simulated trips.

        This DataFrame merges the `single_trip_sequence` outputs of all
        underlying TripSimulator` instances and includes:

        - Event type (`travelling`, `at_stop`, `at_terminal`)
        - Duration and distance
        - Geometry (Point or LineString)
        - Associated trip identifier

        Returns:
            pd.DataFrame: Fleet-wide travel event sequences.
        """
        return self._trip_travel_sequences

    ## ============================================================
    ## Fleet operation
    ## ============================================================
        
    def compute_fleet_operation(self, use_multiprocessing = False, transient_regime = False) -> None:
        """
        Compute the fleet-wide operation schedule for all selected trips.

        This method iterates over the configured trip IDs, runs a
        `TripSimulator` for each trip, and aggregates their
        fleet operation outputs into a single DataFrame.

        Optionally, multiprocessing can be enabled to parallelize
        per-trip simulations and reduce computation time for large fleets.

        The result is stored internally in `self.fleet_operation` and `self.trip_travel_sequences`.

        Args:
            use_multiprocessing (bool, optional): If True, run trip simulations in parallel using Python multiprocessing. Default is False.
            transient_regime (bool, optional): Whether to include transient (non-steady-state) fleet behavior in the simulation.

        Returns:
            None
        """
        num_trips = len(self.trip_ids)
        print(f"INFO \t Computing fleet operation of {num_trips} trips (multiprocessing = {use_multiprocessing})...")

        # If use_multiprocessing is True, perform the computation in parallel
        if use_multiprocessing:
            # Create a shared manager to track the progress
            with mp.Manager() as manager:
                progress_counter = manager.Value('i', 0)  # Shared counter to track progress

                # Create multiprocessing pool and apply function
                with mp.Pool(mp.cpu_count()) as pool:
                    results = pool.starmap(
                        process_trip, 
                        [(trip_id, self.gtfs_manager, progress_counter, num_trips) for trip_id in self.trip_ids]
                    )
            fleet_operations, sequences = zip(*results)
            fleet_operations = list(fleet_operations)
            sequences = list(sequences)
        else:
            # If no multiprocessing, compute trips sequentially
            fleet_operations = []
            sequences = []
            counter = 1
            for trip_id in self.trip_ids:
                tripsim = TripSimulator(gtfs_manager=self.gtfs_manager, trip_id=trip_id)
                tripsim.compute_fleet_operation(transient_regime = transient_regime)

                fleet_operation = pd.DataFrame(tripsim._fleet_operation)
                sequence = pd.DataFrame(tripsim._single_trip_sequence)

                # Add trip_id column to the sequence dataframe
                sequence['trip_id'] = trip_id
                fleet_operation['trip_id'] = trip_id                

                sys.stdout.write(f"\r \t Progress: {counter}/{num_trips} trips.")
                sys.stdout.flush()

                counter += 1

                fleet_operations.append(fleet_operation)
                sequences.append(sequence)

        # Step 3: Merge all results **at once**
        self._fleet_operation = pd.concat(fleet_operations, ignore_index=True)
        self._trip_travel_sequences = pd.concat(sequences, ignore_index=True)        

        print("\n \t Fleet operation computation completed.")

    ## ============================================================
    ## Time-resolved fleet trajectory
    ## ============================================================

    def get_fleet_trajectory(self, time_step: int, transient_regime = False) -> pd.DataFrame:
        """
        Compute time-resolved spatial trajectories for the entire fleet.

        For each simulated trip, this method recomputes the fleet operation
        and generates vehicle trajectories sampled at a fixed time step.

        !!! warning
            This method needs to be further optimized. For the moment, it recomputes trip 
            simulations internally and may be computationally heavy.

        Args:
            time_step (int): Temporal resolution in seconds at which vehicle positions are sampled.
            transient_regime (bool, optional): Whether to include transient fleet behavior.

        Returns:
            pd.DataFrame: Multi-index DataFrame indexed by
            `(trip_id, vehicle_id)` with columns representing time steps
            (`HH:MM:SS`). Each cell contains a `shapely.geometry.Point`
            representing the vehicle location or None.
        """
        print(f"INFO \t Generating vehicle fleet trajectories...")

        results = []

        counter = 1
        for trip_id in self.trip_ids:
            tripsim = TripSimulator(gtfs_manager=self.gtfs_manager, trip_id=trip_id)
            tripsim.compute_fleet_operation(transient_regime = transient_regime)

            sys.stdout.write(f"\r \t Progress: {counter}/{len(self.trip_ids)} trips.")
            sys.stdout.flush()
            counter += 1

            df = tripsim.get_fleet_trajectory(time_step=time_step)

            results.append(df)

        print(f"")

        return pd.concat(results, keys=self.trip_ids, names=["trip_id", "vehicle_id"])

    def generate_fleet_trajectory_map(self, fleet_trajectory: pd.DataFrame, filepath: str) -> None:
        """
        Generate an interactive HTML map visualizing fleet trajectories.

        This method merges per-trip folium maps generated by
        `TripSimulator` into a single interactive map with a
        time slider showing vehicle movements.

        !!! warning
            This visualization currently assumes a fixed time step of 2 minutes.

        Args:
            fleet_trajectory (pd.DataFrame): Fleet trajectory DataFrame as returned by :meth:`get_fleet_trajectory`.
            filepath (str): Path where the generated HTML map is saved.

        Returns:
            None
        """
        print(f"INFO \t Generating a HTML map with vehicle fleet trajectories. This may take some time...")

        # Initialize a base map
        merged_map = None

        counter = 1
        # Loop over all the unique trip_ids in the fleet_trajectory DataFrame
        for trip_id in fleet_trajectory.index.get_level_values("trip_id").unique():
            # Filter the fleet_trajectory DataFrame for the current trip_id
            trip_data = fleet_trajectory.xs(trip_id, level="trip_id")

            sys.stdout.write(f"\r \t Progress: {counter}/{len(fleet_trajectory.index.get_level_values("trip_id").unique())} trips.")
            sys.stdout.flush()
            counter += 1

            # Generate the map for the current DataFrame
            tripsim = TripSimulator(gtfs_manager=self.gtfs_manager, trip_id=trip_id)
            m = tripsim.get_fleet_trajectory_map(fleet_trajectory=trip_data)            
            
            # If merged_map is None, initialize it with the first map
            if merged_map is None:
                merged_map = m
            else:
                # Merge the map (You can add layers or features here depending on the method)
                for layer in m._children.values():
                    # Add each feature layer from the new map to the merged map
                    merged_map.add_child(layer)

        # Save the final merged map
        merged_map.save(filepath)

## ============================================================
## Helper function (outside the class) to process trips using multiprocessing
## ============================================================

def process_trip(trip_id, gtfs_manager, progress_counter, num_trips, transient_regime):
    """
    Process a single GTFS trip for fleet simulation.

    This helper function is designed to be executed in parallel when
    multiprocessing is enabled. It runs a `TripSimulator` for
    a single trip and returns its fleet operation and travel sequence.

    Args:
        trip_id (str): GTFS trip identifier to simulate.
        gtfs_manager (GTFSManager): GTFS data manager instance.
        progress_counter (multiprocessing.Value or None): Shared counter used to track simulation progress.
        num_trips (int): Total number of trips being simulated.
        transient_regime (bool): Whether to include transient behavior.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]:
            - Fleet operation DataFrame for the trip
            - Travel sequence DataFrame for the trip
    """
    tripsim = TripSimulator(gtfs_manager=gtfs_manager, trip_id=trip_id)
    tripsim.compute_fleet_operation(transient_regime = transient_regime)

    fleet_operation = pd.DataFrame(tripsim._fleet_operation)
    sequence = pd.DataFrame(tripsim._single_trip_sequence)

    fleet_operation['trip_id'] = trip_id
    sequence['trip_id'] = trip_id

    if progress_counter is not None:
        progress_counter.value += 1
        sys.stdout.write(f"\r \t Progress: {progress_counter.value}/{num_trips} trips.")
        sys.stdout.flush()

    return fleet_operation, sequence