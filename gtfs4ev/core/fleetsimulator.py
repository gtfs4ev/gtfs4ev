# coding: utf-8

import pandas as pd
import sys
import multiprocessing as mp
import time
import gc

from gtfs4ev.gtfsmanager import GTFSManager
from gtfs4ev.tripsimulator import TripSimulator
from gtfs4ev import helpers as hlp

class FleetSimulator:
    """
    A class to simulate a fleet of vehicles based on GTFS data.
    
    Attributes:
        gtfs_manager (GTFSManager): The GTFS manager handling transit data.
        trip_ids (list[str]): List of trip IDs to simulate.
    """
    
    def __init__(self, gtfs_manager: GTFSManager, trip_ids: str = None):
        """
        Initializes the FleetSimulator instance.

        Args:
            gtfs_manager (GTFSManager): The GTFS manager handling transit data.
            trip_ids (list[str], optional): The list of trip IDs to simulate. Defaults to all trips.
        """
        print("=========================================")
        print(f"INFO \t Creation of a FleetSimulator object.")
        print("=========================================")

        self.gtfs_manager = gtfs_manager
        self.trip_ids = trip_ids

        self._fleet_operation = None
        self._trip_travel_sequences = None

        print("INFO \t Successful initialization of the FleetSimulator. The fleet operation can now be simulated. ")
    
    # Properties and Setters

    @property
    def gtfs_manager(self) -> GTFSManager:
        return self._gtfs_manager

    @gtfs_manager.setter
    def gtfs_manager(self, value):
        if not isinstance(value, object):  # Ideally, check against GTFSManager class
            raise ValueError("ERROR \t gtfs_manager must be a valid GTFSManager instance.")
        self._gtfs_manager = value
    
    @property
    def trip_ids(self):
        """Gets the list of trip IDs."""
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
    def fleet_operation(self):
        """Gets the pd dataframe with fleet operation."""
        return self._fleet_operation

    @property
    def trip_travel_sequences(self):
        """Gets the pd dataframe with fleet travel sequences."""
        return self._trip_travel_sequences

    # Fleet Operation
        
    def compute_fleet_operation(self, use_multiprocessing = False, transient_regime = False):
        """
        Runs the simulation for the selected trips and accumulates the results in a big dataframe.
        Uses parallel processing to speed up computation if 'use_multiprocessing' is True.
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

    # Fleet trajectory

    def get_fleet_trajectory(self, time_step: int, transient_regime = False) -> pd.DataFrame:
        """
        Simulation of fleet operation. 
        Warning: Not optimize (recalculation of the fleet operation) 
        
        Args:
            time_step (int): Time step in seconds.
        
        Returns:
            pd.DataFrame: DataFrame with a row per vehicle (indexed by vehicle ID)
                          and columns for each time step (HH:MM:SS). Each cell contains 
                          a Point object (or None) representing the vehicle location.
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

    # Fleet trajectory

    def generate_fleet_trajectory_map(self, fleet_trajectory: pd.DataFrame, filepath: str):
        """
        Generates an interactive folium map with a time slider using the simulated fleet operation data.

        This function only works if the time step is exactly 2 minutes.

        Args:
            fleet_trajectory (pd.DataFrame): DataFrame containing vehicle trajectory data.

        Returns:
            folium.Map: A folium map with a time slider visualization of vehicle movements.
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

# Helper function (outside the class) to process trips using multiprocessing

def process_trip(trip_id, gtfs_manager, progress_counter, num_trips, transient_regime):
    """
    Function to process a single trip. This runs in parallel or sequentially.
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