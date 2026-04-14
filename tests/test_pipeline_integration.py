# coding: utf-8

import pandas as pd

from gtfs4ev.core.gtfsmanager import GTFSManager
from gtfs4ev.core.fleetsimulator import FleetSimulator
from gtfs4ev.core.chargingsimulator import ChargingSimulator


def test_full_pipeline_minimal(tmp_path):
    """
    Minimal end-to-end GTFS4EV pipeline test following the API example structure.
    """

    # ------------------------------------------------------------------------------
    # Configuration 
    # ------------------------------------------------------------------------------

    gtfs_datafolder = "examples/data/sample_GTFS"
    output_folder = tmp_path

    # ------------------------------------------------------------------------------
    # 1. Load and prepare GTFS data
    # ------------------------------------------------------------------------------

    gtfs = GTFSManager(gtfs_datafolder=str(gtfs_datafolder))

    if not gtfs.check_all():
        gtfs.clean_all()

    assert gtfs is not None

    # ------------------------------------------------------------------------------
    # 2. Fleet operation simulation
    # ------------------------------------------------------------------------------

    fleet_sim = FleetSimulator(gtfs_manager=gtfs)

    fleet_sim.compute_fleet_operation(use_multiprocessing=False)

    assert hasattr(fleet_sim, "fleet_operation")
    assert fleet_sim.fleet_operation is not None
    assert len(fleet_sim.fleet_operation) > 0

    # ------------------------------------------------------------------------------
    # 3. Charging simulation
    # ------------------------------------------------------------------------------

    charging = ChargingSimulator(
        fleet_sim=fleet_sim,
        energy_consumption_kWh_per_km=0.39,
        security_driving_distance_km=0,
        charging_powers_kW={
            "depot": [[22, 0.5], [50, 0.5]],
            "terminal": [[150, 1.0]],
            "stop": [[150, 1.0]],
        },
    )

    charging.compute_charging_schedule(
        charging_strategies=["terminal_random", "depot_night"],
        charge_probability_terminal=0.5,
        depot_travel_time_min=[30, 15],
    )

    assert hasattr(charging, "charging_schedule_pervehicle")
    assert charging.charging_schedule_pervehicle is not None
    assert len(charging.charging_schedule_pervehicle) > 0

    # ------------------------------------------------------------------------------
    # 4. Outputs (minimal but complete)
    # ------------------------------------------------------------------------------

    fleet_file = output_folder / "fleet_operation.csv"
    charging_file = output_folder / "charging_schedules_per_vehicle.csv"
    load_curve_file = output_folder / "charging_load_curve.csv"

    fleet_sim.fleet_operation.to_csv(fleet_file, index=False)
    charging.charging_schedule_pervehicle.to_csv(charging_file, index=False)

    load_curve = charging.compute_charging_load_curve(time_step_s=60)
    load_curve.to_csv(load_curve_file, index=False)

    # ------------------------------------------------------------------------------
    # Assertions (file existence + non-empty)
    # ------------------------------------------------------------------------------

    assert fleet_file.exists()
    assert charging_file.exists()
    assert load_curve_file.exists()

    assert not pd.read_csv(fleet_file).empty
    assert not pd.read_csv(charging_file).empty
    assert not pd.read_csv(load_curve_file).empty