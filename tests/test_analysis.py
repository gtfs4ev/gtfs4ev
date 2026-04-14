import pytest
import numpy as np
import pandas as pd

from gtfs4ev.analysis.pvsimulator import PVSimulator
from gtfs4ev.analysis.evpvsynergies import EVPVSynergies
from gtfs4ev.analysis.costsavings import CostSavings
from gtfs4ev.analysis.co2savings import CO2Savings
from gtfs4ev.analysis.airpollution import AirPollutionExposure

# -------------------------------------------------------------------------------
# PVSimulator Tests
# -------------------------------------------------------------------------------

@pytest.fixture
def env():
    return {"latitude": 46.5, "longitude": 6.6, "year": 2020}


@pytest.fixture
def module():
    return {"efficiency": 0.2, "temperature_coefficient": -0.004}


@pytest.fixture
def install():
    return {"type": "flat_roof", "system_losses": 0.1}


@pytest.fixture(autouse=True)
def mock_pvgis(monkeypatch):
    """Mock PVGIS API to avoid external calls."""
    def fake_get_pvgis_hourly(*args, **kwargs):
        index = pd.date_range("2020-01-01", periods=24, freq="h", tz="UTC")

        df = pd.DataFrame({
            "poa_direct": np.ones(24) * 500,
            "poa_sky_diffuse": np.ones(24) * 100,
            "poa_ground_diffuse": np.ones(24) * 50,
        }, index=index)

        meta = {
            "location": {"elevation": 500},
            "mounting_system": {"fixed": {"slope": {"value": 30}}}
        }

        return df, meta, {}

    import pvlib.iotools
    monkeypatch.setattr(pvlib.iotools, "get_pvgis_hourly", fake_get_pvgis_hourly)


# Initialization

def test_pvsimulator_initialization(env, module, install):
    sim = PVSimulator(env, module, install)

    assert sim.environment == env
    assert isinstance(sim.weather_data, pd.DataFrame)
    assert sim.results.empty


# Validation

def test_invalid_inputs_raise(env, module):
    with pytest.raises(ValueError):
        PVSimulator(env, {"efficiency": -0.1, "temperature_coefficient": -0.004}, module)

    with pytest.raises(ValueError):
        PVSimulator(env, module, {"type": "wrong", "system_losses": 0.1})


# Weather data

def test_weather_data(env, module, install):
    sim = PVSimulator(env, module, install)

    assert len(sim.weather_data) > 0
    assert "poa_global" in sim.weather_data.columns


# PV production

def test_compute_pv_production(env, module, install):
    sim = PVSimulator(env, module, install)

    sim.compute_pv_production()

    assert isinstance(sim.results, pd.DataFrame)
    assert len(sim.results) > 0
    assert "PV Production (W/m2)" in sim.results.columns


def test_pv_production_non_negative(env, module, install):
    sim = PVSimulator(env, module, install)

    sim.compute_pv_production()

    assert (sim.results["PV Production (W/m2)"] >= 0).all()


# Helper

def test_get_timezone(env, module, install):
    sim = PVSimulator(env, module, install)

    tz = sim.get_timezone(env["latitude"], env["longitude"])

    assert isinstance(tz, str)


# -------------------------------------------------------------------------------
# EVPVSynergies Tests
# -------------------------------------------------------------------------------

@pytest.fixture
def mock_pv():
    """Minimal mock PVSimulator with results."""
    class MockPV:
        def __init__(self):
            index = pd.date_range("2020-01-01", periods=24, freq="h")
            self.results = pd.DataFrame({
                "Capacity Factor": np.linspace(0, 1, 24)
            }, index=index)

    return MockPV()


@pytest.fixture
def load_curve():
    """Simple EV load curve."""
    time = np.linspace(0, 24, 24)

    return pd.DataFrame({
        "time_h": time,
        "depot": np.ones(24) * 100,
        "stop": np.ones(24) * 50,
        "terminal": np.ones(24) * 50,
    })


@pytest.fixture
def synergy(mock_pv, load_curve):
    return EVPVSynergies(mock_pv, load_curve, pv_capacity_MW=10)


# Initialization

def test_initialization(synergy):
    assert synergy.pv_capacity_MW == 10
    assert callable(synergy.ev_charging_demand_MW)
    assert isinstance(synergy.pv_capacity_factor, dict)


# EV demand

def test_ev_demand_positive(synergy):
    demand = synergy.ev_demand()

    assert demand > 0


# PV production

def test_pv_production_positive(synergy):
    prod = synergy.pv_production("01-01")

    assert prod >= 0


# Ratios

def test_energy_coverage_ratio(synergy):
    ratio = synergy.energy_coverage_ratio("01-01")

    assert ratio >= 0


def test_self_sufficiency_ratio(synergy):
    ratio = synergy.self_sufficiency_ratio("01-01")

    assert 0 <= ratio <= 1


def test_self_consumption_ratio(synergy):
    ratio = synergy.self_consumption_ratio("01-01")

    assert 0 <= ratio <= 1


def test_excess_pv_ratio(synergy):
    ratio = synergy.excess_pv_ratio("01-01")

    assert 0 <= ratio <= 1


# Correlation

def test_spearman_correlation(synergy):
    coef, pval = synergy.spearman_correlation("01-01")

    assert isinstance(coef, float)
    assert isinstance(pval, float)


# Daily metrics

def test_daily_metrics_returns_dataframe(synergy):
    df = synergy.daily_metrics("01-01", "01-03")

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "PV Production (MWh)" in df.columns


# -------------------------------------------------------------------------------
# CostSavings Tests
# -------------------------------------------------------------------------------

@pytest.fixture
def sample_csv(tmp_path):
    df = pd.DataFrame({
        "vehicle_id": [1, 2],
        "trip_id": [101, 201],
        "total_distance_km": [10, 20],
    })

    file_path = tmp_path / "fleet.csv"
    df.to_csv(file_path, index=False)

    return file_path


@pytest.fixture
def calculator(sample_csv):
    return CostSavings(input_file=sample_csv)


# Compute savings

def test_compute_savings(calculator):
    calculator.compute_savings()

    assert isinstance(calculator.results, pd.DataFrame)
    assert "economic_savings_USD" in calculator.results.columns


# Save results

def test_save_results(calculator, tmp_path):
    calculator.compute_savings()

    output_file = tmp_path / "results.csv"
    calculator.save_results(output_file)

    assert output_file.exists()


# Error handling

def test_save_without_compute_raises(calculator, tmp_path):
    with pytest.raises(RuntimeError):
        calculator.save_results(tmp_path / "results.csv")


# -------------------------------------------------------------------------------
# CO2Savings Tests
# -------------------------------------------------------------------------------

@pytest.fixture
def sample_csv(tmp_path):
    df = pd.DataFrame({
        "vehicle_id": [1, 2],
        "trip_id": [101, 201],
        "total_distance_km": [10, 20],
    })

    file_path = tmp_path / "fleet.csv"
    df.to_csv(file_path, index=False)

    return file_path


@pytest.fixture
def calculator(sample_csv):
    return CO2Savings(input_file=sample_csv)


# Compute savings

def test_compute_savings(calculator):
    calculator.compute_savings()

    assert isinstance(calculator.results, pd.DataFrame)
    assert "emission_reduction_tco2" in calculator.results.columns
    assert "diesel_savings_L" in calculator.results.columns


# Save results

def test_save_results(calculator, tmp_path):
    calculator.compute_savings()

    output_file = tmp_path / "results.csv"
    calculator.save_results(output_file)

    assert output_file.exists()


# Error handling

def test_save_without_compute_raises(calculator, tmp_path):
    with pytest.raises(RuntimeError):
        calculator.save_results(tmp_path / "results.csv")

# -------------------------------------------------------------------------------
# AirPollutionExposure Tests
# -------------------------------------------------------------------------------

@pytest.fixture
def fake_csvs(tmp_path):
    """Create minimal CSV inputs."""

    fleet = pd.DataFrame({
        "trip_id": [1, 2],
        "total_distance_km": [10, 20],
    })

    seq = pd.DataFrame({
        "trip_id": [1, 1, 2, 2],
        "status": ["travelling"] * 4,
        "location": [
            "LINESTRING (0 0, 1 1)",
            "LINESTRING (1 1, 2 2)",
            "LINESTRING (0 0, 1 0)",
            "LINESTRING (1 0, 2 0)",
        ]
    })

    fleet_file = tmp_path / "fleet.csv"
    seq_file = tmp_path / "seq.csv"

    fleet.to_csv(fleet_file, index=False)
    seq.to_csv(seq_file, index=False)

    return fleet_file, seq_file


@pytest.fixture
def model(fake_csvs, tmp_path):
    fleet_file, seq_file = fake_csvs

    return AirPollutionExposure(
        input_fleet_operation=fleet_file,
        input_travel_sequences=seq_file,
        population_raster=str(tmp_path / "fake.tif"),  # not used in these tests
        buffer_distance=100,
        decay_rate=0.01,
    )


# Initialization

def test_initialization(model):
    assert model.buffer_distance == 100
    assert model.decay_rate == 0.01
    assert model.output_local_emission_index is None


# Data preparation (light test only)

def test_prepare_vkm_and_geometry(model):
    vkm, lines = model._prepare_vkm_and_geometry()

    assert isinstance(vkm, list)
    assert len(vkm) == 2
    assert len(lines) == 2
    assert vkm[0] == 10


# Kernel helper (IMPORTANT pure function test)

def test_exponential_decay_kernel():
    kernel = AirPollutionExposure._exponential_decay_kernel(3, 1.0)

    assert kernel.shape == (3, 3)
    assert np.all(kernel >= 0)


# Mask helper

def test_mask_within_radius():
    mask = AirPollutionExposure._mask_within_radius(5, 2)

    assert mask.shape == (5, 5)
    assert mask.sum() > 0
