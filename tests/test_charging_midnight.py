"""Midnight sessions must preserve energy and end before following charges."""
import numpy as np
import pandas as pd
import pytest
from gtfs4ev.core.chargingsimulator import ChargingSimulator


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
        {"start_time": "23:00:00", "end_time": "01:00:00",
         "location": location, "power": 60}
    ])
    curve = obj.compute_charging_load_curve(time_step_s)
    assert curve[location].sum() * time_step_s / 3600 == pytest.approx(120)
    expected = ((curve["time_h"] < 1) | (curve["time_h"] >= 23)).astype(float) * 60
    np.testing.assert_array_equal(curve[location], expected)


@pytest.mark.parametrize("time_step_s", [60, 900, 1800])
def test_midnight_split_does_not_create_overlap(time_step_s):
    obj = simulator([
        {"start_time": "23:00:00", "end_time": "01:00:00",
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
