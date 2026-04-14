import pytest
import types
from unittest.mock import patch, MagicMock

from gtfs4ev.cli.gtfs4ev_cli import main, load_config, run_simulation


# -------------------------------------------------------------------------------
# CLI Tests
# -------------------------------------------------------------------------------

# -------------------------------------------------------------------------------
# load_config
# -------------------------------------------------------------------------------

def test_load_config(tmp_path):
    config_file = tmp_path / "config.py"

    config_file.write_text("""
output_folder = "test_output"
gtfs_datafolder = "data"
clean_gtfs_data = False
filter_out_services = []
filter_out_agencies = []
add_idle_time_terminals_s = (0, 0)
add_idle_time_stops_s = (0, 0)
trim_tripshapes_to_terminal_locations = False
export_cleaned_gtfs = False
generate_network_map = False
generate_map_specific_trips = []
trips_to_simulate = None
use_multiprocessing = False
generate_map_fleet_movement = False
energy_consumption_kWh_per_km = 1
security_driving_distance_km = 1
charging_powers_kW = [50]
charging_strategy_sequence = []
charge_probability_terminal = 0
charge_probability_stop = 0
depot_travel_time_min = 0
load_curve_timestep_s = 60
""")

    config = load_config(str(config_file))

    assert hasattr(config, "output_folder")
    assert config.output_folder == "test_output"


# -------------------------------------------------------------------------------
# main (mock everything)
# -------------------------------------------------------------------------------

@patch("gtfs4ev.cli.gtfs4ev_cli.run_simulation")
@patch("gtfs4ev.cli.gtfs4ev_cli.load_config")
@patch("builtins.input", return_value="fake_config.py")
def test_main(mock_input, mock_load_config, mock_run_simulation, tmp_path):

    fake_config = types.SimpleNamespace(output_folder=str(tmp_path))
    mock_load_config.return_value = fake_config

    main()

    mock_load_config.assert_called_once()
    mock_run_simulation.assert_called_once()


# -------------------------------------------------------------------------------
# run_simulation (fully mocked core classes)
# -------------------------------------------------------------------------------

@patch("gtfs4ev.cli.gtfs4ev_cli.ChargingSimulator")
@patch("gtfs4ev.cli.gtfs4ev_cli.FleetSimulator")
@patch("gtfs4ev.cli.gtfs4ev_cli.GTFSManager")
def test_run_simulation(mock_gtfs, mock_fleet, mock_charging):

    config = types.SimpleNamespace(
        output_folder="test",
        gtfs_datafolder="data",
        clean_gtfs_data=False,
        filter_out_services=[],
        filter_out_agencies=[],
        add_idle_time_terminals_s=(0, 0),
        add_idle_time_stops_s=(0, 0),
        trim_tripshapes_to_terminal_locations=False,
        export_cleaned_gtfs=False,
        generate_network_map=False,
        generate_map_specific_trips=[],
        trips_to_simulate=None,
        use_multiprocessing=False,
        generate_map_fleet_movement=False,
        energy_consumption_kWh_per_km=1,
        security_driving_distance_km=1,
        charging_powers_kW=[50],
        charging_strategy_sequence=[],
        charge_probability_terminal=0,
        charge_probability_stop=0,
        depot_travel_time_min=0,
        load_curve_timestep_s=60
    )

    # Mock GTFS behavior
    mock_gtfs.return_value.check_all.return_value = True

    # Mock FleetSimulator
    mock_fleet_instance = MagicMock()
    mock_fleet.return_value = mock_fleet_instance
    mock_fleet_instance.fleet_operation.to_csv = MagicMock()
    mock_fleet_instance.trip_travel_sequences.to_csv = MagicMock()

    # Mock ChargingSimulator
    mock_charging_instance = MagicMock()
    mock_charging.return_value = mock_charging_instance
    mock_charging_instance.charging_schedule_pervehicle.to_csv = MagicMock()
    mock_charging_instance.charging_schedule_perstop.to_csv = MagicMock()
    mock_charging_instance.compute_charging_load_curve.return_value.to_csv = MagicMock()

    # Run
    run_simulation(config)

    # Assertions
    mock_gtfs.assert_called_once()
    mock_fleet.assert_called_once()
    mock_charging.assert_called_once()