import pytest
import shutil
import numpy as np
import pandas as pd
import datetime
from shapely.geometry import LineString, Point

from gtfs4ev.core.gtfsmanager import GTFSManager
from gtfs4ev.core.fleetsimulator import FleetSimulator
from gtfs4ev.core.chargingsimulator import ChargingSimulator
from gtfs4ev.utils import helpers as hlp

# -------------------------------------------------------------------------------
# GTFSManager Tests
# -------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def manager():
    """Load example GTFS feed once for all tests."""
    return GTFSManager("examples/data/sample_GTFS")

# Construction & basic validation

def test_required_tables_exist(manager):
    """Required GTFS tables must be present."""
    assert isinstance(manager.stops, pd.DataFrame)
    assert isinstance(manager.trips, pd.DataFrame)
    assert isinstance(manager.stop_times, pd.DataFrame)

def test_tables_not_empty(manager):
    """GTFS tables should not be empty."""
    assert len(manager.stops) > 0
    assert len(manager.trips) > 0
    assert len(manager.stop_times) > 0

def test_invalid_path_raises():
    """Invalid GTFS path should raise an error."""
    with pytest.raises(Exception):
        GTFSManager("examples/data/non_existent_gtfs")

# GTFS consistency & integrity

def test_stop_sequence_non_negative(manager):
    """stop_sequence must be non-negative."""
    assert (manager.stop_times["stop_sequence"] >= 0).all()


def test_stop_sequence_sorted_within_trip(manager):
    """stop_sequence must be ordered within each trip."""
    for trip_id, group in manager.stop_times.groupby("trip_id"):
        seq = group["stop_sequence"].values
        assert np.all(seq == np.sort(seq))


def test_trip_stop_references_exist(manager):
    """All stop_times must reference existing stops."""
    stop_ids = set(manager.stops["stop_id"])
    assert set(manager.stop_times["stop_id"]).issubset(stop_ids)


def test_trip_route_references_exist(manager):
    """Trips must reference valid routes if routes table exists."""
    if hasattr(manager, "routes"):
        route_ids = set(manager.routes["route_id"])
        assert set(manager.trips["route_id"]).issubset(route_ids)

# GTFS service time loading

def test_gtfsmanager_load_extended_frequency_times(tmp_path):
    """Extended GTFS frequency times must be preserved as strings."""
    (tmp_path / "frequencies.txt").write_text(
        "trip_id,start_time,end_time,headway_secs\n"
        "T1,23:00:00,27:00:00,600\n"
    )

    manager = GTFSManager.__new__(GTFSManager)
    manager.gtfs_datafolder = tmp_path

    df = manager._load_csv(
        "frequencies.txt",
        gtfs_time_columns=['start_time', 'end_time']
    )

    assert df["start_time"].iloc[0] == "23:00:00"
    assert df["end_time"].iloc[0] == "27:00:00"


def test_gtfsmanager_load_extended_stop_times(tmp_path):
    """Extended GTFS stop times must be preserved as strings."""
    (tmp_path / "stop_times.txt").write_text(
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "T1,23:30:00,23:35:00,S1,1\n"
        "T1,27:00:00,27:05:00,S2,2\n"
    )

    manager = GTFSManager.__new__(GTFSManager)
    manager.gtfs_datafolder = tmp_path

    df = manager._load_csv(
        "stop_times.txt",
        gtfs_time_columns=['arrival_time', 'departure_time']
    )

    assert df["arrival_time"].iloc[1] == "27:00:00"
    assert df["departure_time"].iloc[1] == "27:05:00"


def test_gtfsmanager_reject_invalid_time(tmp_path):
    """GTFSManager must reject malformed GTFS time values."""
    (tmp_path / "frequencies.txt").write_text(
        "trip_id,start_time,end_time,headway_secs\n"
        "T1,23:00:00,-01:00:00,600\n"
    )

    manager = GTFSManager.__new__(GTFSManager)
    manager.gtfs_datafolder = tmp_path

    with pytest.raises(ValueError):
        manager._load_csv(
            "frequencies.txt",
            gtfs_time_columns=['start_time', 'end_time']
        )

# Cleaning

def test_clean_removes_or_preserves_entities(manager):
    """Cleaning should not increase entity counts."""
    stops_before_cleaning = manager.stops
    trips_before_cleaning = manager.trips
    stop_times_before_cleaning = manager.stop_times

    manager.clean_all()

    assert len(stops_before_cleaning) >= len(manager.stops)
    assert len(trips_before_cleaning) >= len(manager.trips)
    assert len(stop_times_before_cleaning) >= len(manager.stop_times)

# Adding idle times

def test_add_idle_time_stops_creates_column(manager):
    """Idle times should be added to stop_times."""
    # Store original departure times
    original_times = manager.stop_times['departure_time'].copy()
    
    manager.add_idle_time_stops(mean_idle_time_s=600, std_idle_time_s=60)

    # Check that some departure times have increased
    time_diff = (
        manager.stop_times['departure_time'].map(hlp.gtfs_time_to_seconds)
        - original_times.map(hlp.gtfs_time_to_seconds)
    )
    assert time_diff.max() > 0  # At least some stops have added idle time
    assert time_diff.mean() > 0  # On average, time has been added

# Shape trimming

def test_shape_trimming_reduces_or_preserves_shape_length(manager):
    """Trimming shapes should not increase shape point counts."""
    if not hasattr(manager, "shapes"):
        pytest.skip("No shapes in GTFS")
    
    before = manager.shapes.groupby("shape_id").size().mean()
    
    manager.trim_tripshapes_to_terminal_locations()
    
    after = manager.shapes.copy().groupby("shape_id").size().mean()
    assert after <= before

# Validation methods

def test_check_all_returns_bool(manager):
    result = manager.check_all()
    assert isinstance(result, bool)


def test_individual_checks_return_bool(manager):
    assert isinstance(manager.check_agency(), bool)
    assert isinstance(manager.check_shapes(), bool)
    assert isinstance(manager.check_stops(), bool)
    assert isinstance(manager.check_frequencies(), bool)
    assert isinstance(manager.check_calendar(), bool)
    assert isinstance(manager.check_routes(), bool)
    assert isinstance(manager.check_stop_times(), bool)
    assert isinstance(manager.check_trips(), bool)


# Trip analytics

def test_trip_length_positive(manager):
    trip_id = manager.trips["trip_id"].iloc[0]
    assert manager.trip_length_km(trip_id) > 0


def test_trip_duration_positive(manager):
    trip_id = manager.trips["trip_id"].iloc[0]
    assert manager.trip_duration_sec(trip_id) > 0


def test_number_of_stops_matches_stop_times(manager):
    trip_id = manager.trips["trip_id"].iloc[0]
    expected = len(manager.stop_times[manager.stop_times["trip_id"] == trip_id])
    assert manager.n_stops(trip_id) == expected


# Geometry & spatial logic

def test_bounding_box_valid(manager):
    bbox = manager.bounding_box()
    minx, miny, maxx, maxy = bbox.bounds

    assert minx < maxx
    assert miny < maxy


def test_simulation_area_positive(manager):
    assert manager.simulation_area_km2() > 0


# Statistics

def test_trip_statistics_keys(manager):
    stats = manager.trip_statistics()

    expected_keys = {
        'total_trips',
        'total_trip_len_km',
        'ave_trip_len_km',
        'min_trip_len_km',
        'max_trip_len_km',
        'trip_to_route_ratio'
    }

    assert expected_keys.issubset(stats.keys())


def test_stop_statistics_keys(manager):
    stats = manager.stop_statistics()

    expected_keys = {
        'total_stops',
        'min_stops_per_trip',
        'max_stops_per_trip',
        'std_dev_stops_per_trip',
        'ave_stops_per_trip',
        'ave_stops_per_route',
        'stops_to_trips_ratio',
        'stops_to_routes_ratio'
    }

    assert expected_keys.issubset(stats.keys())

# Accessors

def test_get_shape_returns_linestring(manager):
    trip_id = manager.trips["trip_id"].iloc[0]
    assert isinstance(manager.get_shape(trip_id), LineString)


def test_get_stop_locations_returns_points(manager):
    trip_id = manager.trips["trip_id"].iloc[0]
    stops = manager.get_stop_locations(trip_id)

    assert isinstance(stops, list)
    assert all(isinstance(s, Point) for s in stops)


# Filtering (services)

def test_filter_services_reduces_trips(manager):
    if not hasattr(manager, "calendar"):
        pytest.skip("No calendar in GTFS")

    original = len(manager.trips)

    service_id = manager.calendar["service_id"].iloc[0]
    manager.filter_services(service_id)

    assert len(manager.trips) <= original


# Export

def test_export_to_csv(tmp_path, manager):
    output_dir = tmp_path / "gtfs_export"

    manager.export_to_csv(output_dir)

    expected_files = [
        "agency.txt",
        "routes.txt",
        "trips.txt",
        "stops.txt",
        "stop_times.txt",
        "calendar.txt",
        "frequencies.txt",
        "shapes.txt"
    ]

    for f in expected_files:
        assert (output_dir / f).exists()


# Edge cases

def test_invalid_trip_id_raises(manager):
    with pytest.raises(IndexError):
        manager.trip_length_km("INVALID_TRIP_ID")

# Missing shapes.txt

@pytest.mark.parametrize("shapes_content", [None, "", "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\n"])
def test_missing_or_empty_shapes_generate_trip_geometries(tmp_path, shapes_content):
    """Trips remain simulation-ready when shapes.txt is missing or empty."""
    source = "examples/data/sample_GTFS"
    feed = tmp_path / "gtfs"
    shutil.copytree(source, feed)

    shapes_file = feed / "shapes.txt"
    if shapes_content is None:
        shapes_file.unlink()
    else:
        shapes_file.write_text(shapes_content)

    gtfs = GTFSManager(str(feed))

    assert gtfs.check_all()
    assert len(gtfs.shapes) == len(gtfs.trips)
    for trip_id in gtfs.trips["trip_id"]:
        shape = gtfs.get_shape(trip_id)
        assert isinstance(shape, LineString)
        assert shape.length > 0
        assert gtfs.trip_length_km(trip_id) > 0


def test_missing_shape_id_column(tmp_path):
    """The shape_id column is optional when trip geometries are generated."""
    feed = tmp_path / "gtfs"
    shutil.copytree("examples/data/sample_GTFS", feed)
    (feed / "shapes.txt").unlink()

    trips = pd.read_csv(feed / "trips.txt", dtype=str)
    trips.drop(columns="shape_id", errors="ignore").to_csv(feed / "trips.txt", index=False)

    gtfs = GTFSManager(str(feed))

    assert gtfs.check_all()
    assert gtfs.trips["shape_id"].notna().all()
    assert all(isinstance(gtfs.get_shape(trip_id), LineString) for trip_id in gtfs.trips["trip_id"])


def test_existing_shapes_are_preserved():
    """Loading a valid shapes.txt file must not replace its geometries."""
    gtfs = GTFSManager("examples/data/sample_GTFS")

    assert gtfs.check_all()
    assert not gtfs.trips["shape_id"].str.startswith("generated_").any()

# -------------------------------------------------------------------------------
# FleetSimulator Tests
# -------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def all_trip_ids(manager):
    """Return all trip IDs from the GTFS feed."""
    return manager.trips["trip_id"].unique().tolist()


@pytest.fixture
def fleet_simulator(manager, all_trip_ids):
    """FleetSimulator using all available trips."""
    return FleetSimulator(manager, trip_ids=all_trip_ids)

# Construction & validation

def test_fleetsimulator_initialization(manager, all_trip_ids):
    """FleetSimulator should initialize with valid inputs."""
    sim = FleetSimulator(manager, trip_ids=all_trip_ids)

    assert sim.gtfs_manager is manager
    assert isinstance(sim.trip_ids, list)
    assert set(sim.trip_ids) == set(all_trip_ids)
    assert sim.fleet_operation is None
    assert sim.trip_travel_sequences is None


def test_fleetsimulator_with_no_trip_ids_uses_all_trips(manager):
    """If no trip_ids are provided, all trips should be selected."""
    sim = FleetSimulator(manager)

    assert set(sim.trip_ids) == set(manager.trips["trip_id"].unique())


def test_invalid_trip_ids_raise_error(manager):
    """Invalid trip IDs should raise a ValueError."""
    with pytest.raises(ValueError):
        FleetSimulator(manager, trip_ids=["non_existing_trip"])

# Fleet operation computation

def test_compute_fleet_operation_creates_outputs(fleet_simulator):
    """compute_fleet_operation should populate result attributes."""
    fleet_simulator.compute_fleet_operation()

    assert isinstance(fleet_simulator.fleet_operation, pd.DataFrame)
    assert isinstance(fleet_simulator.trip_travel_sequences, pd.DataFrame)
    assert len(fleet_simulator.fleet_operation) > 0
    assert len(fleet_simulator.trip_travel_sequences) > 0


def test_fleet_operation_contains_trip_id_column(fleet_simulator):
    """Fleet operation must contain trip_id column."""
    fleet_simulator.compute_fleet_operation()

    assert "trip_id" in fleet_simulator.fleet_operation.columns
    assert fleet_simulator.fleet_operation["trip_id"].notnull().all()


def test_trip_travel_sequences_contains_trip_id_column(fleet_simulator):
    """Trip travel sequences must contain trip_id column."""
    fleet_simulator.compute_fleet_operation()

    assert "trip_id" in fleet_simulator.trip_travel_sequences.columns
    assert fleet_simulator.trip_travel_sequences["trip_id"].notnull().all()


def test_fleet_operation_trip_ids_subset(fleet_simulator):
    """Fleet operation trip IDs should match simulator trip IDs."""
    fleet_simulator.compute_fleet_operation()

    assert set(fleet_simulator.fleet_operation["trip_id"]).issubset(
        set(fleet_simulator.trip_ids)
    )

# Determinism & consistency

def test_repeated_computation_is_consistent(fleet_simulator):
    """Repeated fleet computations should produce consistent results."""
    fleet_simulator.compute_fleet_operation()
    df1 = fleet_simulator.fleet_operation.copy()

    fleet_simulator.compute_fleet_operation()
    df2 = fleet_simulator.fleet_operation.copy()

    assert len(df1) == len(df2)
    assert set(df1.columns) == set(df2.columns)

# Fleet trajectory

def test_get_fleet_trajectory_returns_dataframe(fleet_simulator):
    """Fleet trajectory should return a pandas DataFrame."""
    traj = fleet_simulator.get_fleet_trajectory(time_step=300)

    assert isinstance(traj, pd.DataFrame)
    assert isinstance(traj.index, pd.MultiIndex)
    assert "trip_id" in traj.index.names
    assert "vehicle_id" in traj.index.names


def test_fleet_trajectory_non_empty(fleet_simulator):
    """Fleet trajectory should not be empty."""
    traj = fleet_simulator.get_fleet_trajectory(time_step=360)

    assert len(traj) > 0

# GTFS extended service times

def test_fleetsimulator_extended_service_times(manager):
    """Fleet operation must preserve GTFS times beyond midnight."""
    trip_id = manager.frequencies["trip_id"].iloc[0]

    # Create an overnight frequency interval without modifying the shared manager
    overnight_manager = GTFSManager("examples/data/sample_GTFS")
    overnight_manager._frequencies = overnight_manager.frequencies[
        overnight_manager.frequencies["trip_id"] == trip_id
    ].iloc[[0]].copy()

    overnight_manager._frequencies.loc[:, "start_time"] = "23:00:00"
    overnight_manager._frequencies.loc[:, "end_time"] = "27:00:00"
    overnight_manager._frequencies.loc[:, "headway_secs"] = 3600

    sim = FleetSimulator(overnight_manager, trip_ids=[trip_id])
    sim.compute_fleet_operation(transient_regime=True)

    # Check that fleet operation extends beyond midnight
    operating_sequences = [
        seq
        for sequences in sim.fleet_operation["travel_sequences"]
        for seq in sequences
        if seq["operating"]
    ]

    assert len(operating_sequences) > 0
    assert any(
        hlp.gtfs_time_to_seconds(seq["end_time"]) > 86400
        for seq in operating_sequences
    )

# Edge cases

def test_single_trip_simulation(manager):
    """FleetSimulator should work with a single trip."""
    single_trip_id = manager.trips["trip_id"].iloc[0]
    sim = FleetSimulator(manager, trip_ids=[single_trip_id])

    sim.compute_fleet_operation()

    assert len(sim.fleet_operation) > 0
    assert sim.fleet_operation["trip_id"].nunique() == 1

# -------------------------------------------------------------------------------
# ChargingSimulator Tests
# -------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fleet_sim(manager):
    """FleetSimulator with computed fleet operation."""
    sim = FleetSimulator(manager)
    sim.compute_fleet_operation()
    return sim

@pytest.fixture
def charging_powers():
    """Example charging power configuration."""
    return {
        "depot": [[22, 1.0]],
        "terminal": [[50, 1.0]],
        "stop": [[50, 1.0]]
    }


@pytest.fixture
def charging_simulator(fleet_sim, charging_powers):
    """ChargingSimulator ready for charging computation."""
    return ChargingSimulator(
        fleet_sim=fleet_sim,
        energy_consumption_kWh_per_km=1.2,
        security_driving_distance_km=10.0,
        charging_powers_kW=charging_powers
    )

# Construction & validation

def test_chargingsimulator_initialization(charging_simulator):
    """ChargingSimulator should initialize correctly."""
    assert charging_simulator.fleet_sim is not None
    assert charging_simulator.energy_consumption_kWh_per_km > 0
    assert charging_simulator.security_driving_distance_km >= 0
    assert isinstance(charging_simulator.charging_powers_kW, dict)
    assert charging_simulator.charging_schedule_pervehicle is None
    assert charging_simulator.charging_schedule_perstop is None

def test_invalid_energy_consumption_raises(fleet_sim):
    """Invalid energy consumption should raise."""
    with pytest.raises(ValueError):
        ChargingSimulator(fleet_sim, -1.0, 5.0)


def test_invalid_security_distance_raises(fleet_sim):
    """Invalid security driving distance should raise."""
    with pytest.raises(ValueError):
        ChargingSimulator(fleet_sim, 1.0, -5.0)


def test_invalid_charging_powers_raises(fleet_sim):
    """Invalid charging_powers_kW should raise."""
    with pytest.raises(ValueError):
        ChargingSimulator(
            fleet_sim,
            1.0,
            5.0,
            charging_powers_kW={"depot": "not_a_list"}
        )

# Charging schedule computation

def test_compute_charging_schedule_creates_outputs(charging_simulator):
    """Charging schedule computation should populate result DataFrames."""
    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night", "terminal_random"]
    )

    assert isinstance(charging_simulator.charging_schedule_pervehicle, pd.DataFrame)
    assert isinstance(charging_simulator.charging_schedule_perstop, pd.DataFrame)
    assert len(charging_simulator.charging_schedule_pervehicle) > 0


def test_charging_schedule_pervehicle_schema(charging_simulator):
    """Vehicle-level charging schedule must contain core fields."""
    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night"]
    )

    df = charging_simulator.charging_schedule_pervehicle

    required_columns = {
        "vehicle_id",
        "charging_sequence",
        "success",
        "charging_need_kWh",
        "remaining_need_kWh",
        "min_capacity_kWh",
        "start_soc_with_min_capacity_kWh"
    }

    assert required_columns.issubset(df.columns)


def test_charging_sequence_is_list(charging_simulator):
    """Each vehicle charging sequence should be a list."""
    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night"]
    )

    seq = charging_simulator.charging_schedule_pervehicle["charging_sequence"]
    assert seq.apply(lambda x: isinstance(x, list)).all()


def test_success_column_is_boolean(charging_simulator):
    """Success column must be boolean."""
    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night"]
    )

    assert charging_simulator.charging_schedule_pervehicle["success"].dtype == bool

# Charging load curve

def test_compute_charging_load_curve_returns_dataframe(charging_simulator):
    """Charging load curve should return a DataFrame."""
    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night"]
    )

    df = charging_simulator.compute_charging_load_curve(time_step_s=900)

    assert isinstance(df, pd.DataFrame)
    assert "time_h" in df.columns
    assert {"depot", "stop", "terminal"}.issubset(df.columns)


def test_charging_load_curve_time_index(charging_simulator):
    """Charging load curve index should represent time of day."""
    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night"]
    )

    df = charging_simulator.compute_charging_load_curve(time_step_s=1800)

    assert df.index.name == "time"
    assert df.index.is_monotonic_increasing


def test_charging_load_curve_non_negative(charging_simulator):
    """Charging load values must be non-negative."""
    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night"]
    )

    df = charging_simulator.compute_charging_load_curve(time_step_s=900)

    assert (df.drop(columns=["time_h"]) >= 0).all().all()


# Robustness & determinism

def test_repeated_charging_computation_consistency(charging_simulator):
    """Repeated charging computation should not break output schema."""
    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night"]
    )
    df1 = charging_simulator.charging_schedule_pervehicle.copy()

    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night"]
    )
    df2 = charging_simulator.charging_schedule_pervehicle.copy()

    assert set(df1.columns) == set(df2.columns)
    assert len(df1) == len(df2)

# Charging load curve: midnight sessions must preserve energy and end before following charges

def simulator(events):
    obj = ChargingSimulator.__new__(ChargingSimulator)
    obj._charging_schedule_pervehicle = pd.DataFrame(
        [{"charging_sequence": events}]
    )
    return obj

@pytest.mark.parametrize("time_step_s", [60, 900, 1800])
@pytest.mark.parametrize("location", ["depot", "stop", "terminal"])
def test_midnight_split_conserves_energy(time_step_s, location):
    obj = simulator([
        {"start_time": "23:00:00", "end_time": "25:00:00",
         "location": location, "power": 60}
    ])
    curve = obj.compute_charging_load_curve(time_step_s)
    assert curve[location].sum() * time_step_s / 3600 == pytest.approx(120)
    expected = ((curve["time_h"] < 1) | (curve["time_h"] >= 23)).astype(float) * 60
    np.testing.assert_array_equal(curve[location], expected)


@pytest.mark.parametrize("time_step_s", [60, 900, 1800])
def test_midnight_split_does_not_create_overlap(time_step_s):
    obj = simulator([
        {"start_time": "23:00:00", "end_time": "25:00:00",
         "location": "depot", "power": 60},
        {"start_time": "01:00:00", "end_time": "02:00:00",
         "location": "depot", "power": 60},
    ])
    curve = obj.compute_charging_load_curve(time_step_s)
    assert curve["depot"].max() == 60
    assert curve["depot"].sum() * time_step_s / 3600 == pytest.approx(180)


@pytest.mark.parametrize("time_step_s", [60, 900, 1800])
def test_non_wrapping_charge_keeps_its_profile(time_step_s):
    obj = simulator([
        {"start_time": "02:00:00", "end_time": "04:00:00",
         "location": "depot", "power": 60},
    ])
    curve = obj.compute_charging_load_curve(time_step_s)
    expected = ((curve["time_h"] >= 2) & (curve["time_h"] < 4)).astype(float) * 60
    np.testing.assert_array_equal(curve["depot"], expected)
    assert curve["depot"].sum() * time_step_s / 3600 == pytest.approx(120)

# GTFS extended charging times

def test_charging_load_curve_extended_times():
    """Charging across midnight must preserve energy and daily time bins."""
    simulator = ChargingSimulator.__new__(ChargingSimulator)

    simulator._charging_schedule_pervehicle = pd.DataFrame([{
        'charging_sequence': [{
            'start_time': '23:00:00',
            'end_time': '25:00:00',
            'location': 'depot',
            'power': 60
        }]
    }])

    load = simulator.compute_charging_load_curve(time_step_s=3600)

    assert load.loc[datetime.time(23, 0), 'depot'] == 60
    assert load.loc[datetime.time(0, 0), 'depot'] == 60
    assert load.loc[datetime.time(1, 0), 'depot'] == 0
    assert load['depot'].sum() == 120

# Built-in charging strategies starting from a fresh GTFS4EV state

@pytest.fixture
def charging_simulator(charging_powers):
    """ChargingSimulator built from a fresh GTFS state."""
    manager = GTFSManager("examples/data/sample_GTFS")

    fleet_sim = FleetSimulator(manager)
    fleet_sim.compute_fleet_operation()

    return ChargingSimulator(
        fleet_sim=fleet_sim,
        energy_consumption_kWh_per_km=1.2,
        security_driving_distance_km=10.0,
        charging_powers_kW={
            "depot": [[22, 1.0]],     
            "terminal": [[50, 1.0]],            
            "stop": [[50, 1.0]]
        }
    )

def test_depot_night(charging_simulator):
    """Depot-night charging load curve should match the expected output."""

    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_night"],
        depot_travel_time_min=[0, 0]
    )

    actual = charging_simulator.compute_charging_load_curve(time_step_s=60).reset_index(drop=True)

    expected = pd.read_csv("tests/expected/charging_load_curve_depot_night.csv")

    pd.testing.assert_frame_equal(
        actual,
        expected,
        rtol=1e-12,
        atol=1e-12,
        check_dtype=False
    )

def test_depot_day(charging_simulator):
    """Depot-day charging load curve should match the expected output."""

    charging_simulator.compute_charging_schedule(
        charging_strategies=["depot_day"],
        depot_travel_time_min=[0, 0]
    )

    actual = charging_simulator.compute_charging_load_curve(time_step_s=60).reset_index(drop=True)

    expected = pd.read_csv("tests/expected/charging_load_curve_depot_day.csv")

    pd.testing.assert_frame_equal(
        actual,
        expected,
        rtol=1e-12,
        atol=1e-12,
        check_dtype=False
    )

def test_terminal_random(charging_simulator):
    """Terminal random charging load curve should match the expected output."""

    charging_simulator.compute_charging_schedule(
        charging_strategies=["terminal_random"],
        charge_probability_terminal=1.0
    )

    actual = charging_simulator.compute_charging_load_curve(time_step_s=60).reset_index(drop=True)

    expected = pd.read_csv("tests/expected/charging_load_curve_terminal_random.csv")

    pd.testing.assert_frame_equal(
        actual,
        expected,
        rtol=1e-12,
        atol=1e-12,
        check_dtype=False
    )

def test_stop_random(charging_simulator):
    """Stop random charging load curve should match the expected output."""

    charging_simulator.compute_charging_schedule(
        charging_strategies=["stop_random"],
        charge_probability_stop=1.0
    )

    actual = charging_simulator.compute_charging_load_curve(time_step_s=60).reset_index(drop=True)

    expected = pd.read_csv("tests/expected/charging_load_curve_stop_random.csv")

    pd.testing.assert_frame_equal(
        actual,
        expected,
        rtol=1e-12,
        atol=1e-12,
        check_dtype=False
    )

def test_terminal_specific_random(charging_simulator):
    """Terminal specific random charging load curve should match the expected output."""

    charging_simulator.compute_charging_schedule(
        charging_strategies=["terminal_specific_random"],
        charge_probability_terminal=1.0,
        specific_terminal_ids=["0113LMD"]
    )

    actual = charging_simulator.compute_charging_load_curve(time_step_s=60).reset_index(drop=True)

    expected = pd.read_csv("tests/expected/charging_load_curve_terminal_specific_random.csv")

    pd.testing.assert_frame_equal(
        actual,
        expected,
        rtol=1e-12,
        atol=1e-12,
        check_dtype=False
    )

# Trip-specific energy consumption

def test_trip_energy_consumption_override(fleet_sim, charging_powers):
    """Trip-specific consumption affects charging demand and battery sizing."""
    trip_id = fleet_sim.fleet_operation["trip_id"].iloc[0]

    sim = ChargingSimulator(
        fleet_sim=fleet_sim,
        energy_consumption_kWh_per_km=1.2,
        security_driving_distance_km=0,
        charging_powers_kW=charging_powers,
        trip_energy_consumption_kWh_per_km={trip_id: 1.8}
    )
    sim.compute_charging_schedule(["depot_night"])

    row = sim.charging_schedule_pervehicle.merge(
        fleet_sim.fleet_operation[["vehicle_id", "trip_id"]],
        on="vehicle_id"
    )
    selected = row[row["trip_id"] == trip_id]

    assert not selected.empty
    for _, vehicle in selected.iterrows():
        assert vehicle["charging_need_kWh"] > 0
        assert vehicle["min_capacity_kWh"] >= 0

    default_sim = ChargingSimulator(
        fleet_sim=fleet_sim,
        energy_consumption_kWh_per_km=1.2,
        security_driving_distance_km=0,
        charging_powers_kW=charging_powers
    )
    default_sim.compute_charging_schedule(["depot_night"])

    baseline = default_sim.charging_schedule_pervehicle.set_index("vehicle_id")
    modified = sim.charging_schedule_pervehicle.set_index("vehicle_id")

    for vehicle_id in selected["vehicle_id"]:
        assert modified.loc[vehicle_id, "charging_need_kWh"] == pytest.approx(
            baseline.loc[vehicle_id, "charging_need_kWh"] * 1.5
        )


def test_trip_energy_consumption_fallback(fleet_sim, charging_powers):
    """Unspecified trips use the default consumption factor."""
    trip_id = fleet_sim.fleet_operation["trip_id"].iloc[0]

    sim = ChargingSimulator(
        fleet_sim=fleet_sim,
        energy_consumption_kWh_per_km=1.2,
        security_driving_distance_km=0,
        charging_powers_kW=charging_powers,
        trip_energy_consumption_kWh_per_km={trip_id: 1.8}
    )

    assert sim.trip_energy_consumption_kWh_per_km.get(
        "unknown_trip", sim.energy_consumption_kWh_per_km
    ) == 1.2


@pytest.mark.parametrize("invalid_value", [
    0, -1, "invalid", None, float("nan"), float("inf")
])
def test_invalid_trip_energy_consumption(
    fleet_sim, invalid_value
):
    """Invalid trip-specific consumption factors are rejected."""
    with pytest.raises(ValueError):
        ChargingSimulator(
            fleet_sim=fleet_sim,
            energy_consumption_kWh_per_km=1.2,
            security_driving_distance_km=10,
            trip_energy_consumption_kWh_per_km={
                "trip_1": invalid_value
            }
        )
