# Quickstart Guide

This guide will help you run a **minimal working example** of GTFS4EV using some of the files provided on [Github](https://github.com/gtfs4ev/gtfs4ev/tree/main/examples) repository's `examples/` folder. We cover both:

- Running via the **command-line interface (CLI)** (`cli_basic.py`)  
- Running as a **Python library** (`api_basic_simulation.py`)  

---

## Prerequisite - Download the examples

To run the minimal examples, download the `data/` folder and the relevant scripts from the available examples:

- [Examples folder on GitHub](https://github.com/gtfs4ev/gtfs4ev/tree/main/examples)
- Folder/Files to download:
    - `data/` folder
    - `cli_basic.py`: for the command-line interface (CLI) example  
    - `api_basic_simulation.py`: for the Python API example  

> Alternatively, you can [download the full GTFS4EV repository as a ZIP](https://github.com/gtfs4ev/gtfs4ev/tree/main/zipball/master/), extract it, and copy the `examples/` folder. This way, you get all scripts and data at once.

Place all files and the `data/` folder in the same directory. After downloading, this directory should at least contain this:

```
data/                        # Sample GTFS feed(s)
api_basic_simulation.py       # Minimal Python API example
cli_basic.py                  # Minimal CLI example
```

---


## Minimal example using the CLI 

1. Open a terminal and activate your virtual environment (if any).
2. Navigate to the folder containing `cli_basic.py`.
3. Run the CLI:
```bash
gtfs4ev
```
4. You’ll be prompted to enter the path to your config file:
```bash
$ Enter the path to the python configuration file: cli_basic.py
```
> ⚠ You can use a relative path when the terminal is in the same directory as the configuration file. Otherwise, use the absolute path.

### Inputs

All parameters are documented direclty in the `cli_basic.py` configuration file. The key inputs for this minimal example are summarized below:

| Input parameter                 | Description                                                                                    |
| ------------------------------- | ---------------------------------------------------------------------------------------------- |
| `gtfs_datafolder`               | Path to the folder containing the GTFS feed (example: Nairobi, Kenya). Must be unzipped.       |
| `output_folder`                 | Path to store all output files (default: `results`).                                           |
| `trips_to_simulate`             | List of trip IDs from the GTFS file to simulate. If set to `None`, simulate all trips.         |
| `energy_consumption_kWh_per_km` | Energy consumption per kilometer for each vehicle (in kWh/km).                                 |
| `charging_powers_kW`            | Dictionary defining available charging powers and their share at depots, terminals, and stops. |
| `charging_strategy_sequence`    | Sequence of charging strategies applied in order (e.g., `terminal_random`, `depot_night`).     |
| `charge_probability_terminal`   | Probability of charging when arriving at a terminal (for the `terminal_random` strategy).      |
| `charge_probability_stop`       | Probability of charging when arriving at a terminal (for the `stop_random` strategy).          |
| `depot_travel_time_min`         | Travel time to/from depot after/before service hours in minutes ([mean, standard deviation]).  |

Other advanced parameters can be specified related to GTFS preprocessing, fleet simulation options, and additional outputs.

GTFS4EV includes several built-in charging strategies:

* **terminal_random** → Random charging at terminals with the given probability
* **stop_random** → Random charging at regular stops with the given probability
* **depot_night** → Recharge at depot during off-hours at the end of the day
* **depot_day** → Recharge at depot during the day when not in operation

In the current minimal example, the configuration uses `terminal_random` followed by `depot_night`. This means vehicles will first attempt to charge randomly at terminals, and if their energy needs are not met, they will charge at the depot during off-hours at the end of the day:

```python
charging_strategy_sequence = ["terminal_random", "depot_night"]
```

Other example configurations:

```python
# Vehicles first try to charge at terminals, then may also charge at stops according to `charge_probability_stop`, and finally recharge at the depot if needed.
charging_strategy_sequence = ["terminal_random", "stop_random", "depot_night"]

# Depot-only charging during the day
charging_strategy_sequence = ["depot_day"]
```
> For custom charging strategies, you can either: (1) Submit a feature request or issue on GitHub to request for a new strategy to be implemented and made available from the CLI ; (2) Use the Python API to develop and integrate your own charging strategy logic.

### Outputs

By default, the minimal example produces the following output files in the `output_folder`:

| Output file                          | Description                                                 |
| ------------------------------------ | ----------------------------------------------------------- |
| `Charging_schedule_pervehicle.csv`   | Per-vehicle charging events. Aso includes success/failure (feasability of the charging strategy), charging needs, remaining needs at theend of the day, minimum required battery capacity, state of charge at the beginning of the day |
| `Charging_schedule_perstop.csv`      | Charging events aggregated per stop.                        |
| `Charging_load_curve.csv`            | Aggregated charging load over time.                         |
| `GTFS_map_alldata.html`              | Visual map of the transport network.                        |
| `Mobility_fleet_operation.csv`       | Fleet operation results. 									 |
| `Mobility_trip_travel_sequences.csv` | Detailed trip travel sequences for each vehicle.            |
| `GTFS_summary.txt`                   | Summary of the GTFS feed and statistics.                    |
| `Charging_stop_map.html`             | Visual map of charging needs at terminals/stops.            |
| `output.log`                         | Log of the simulation run.                                  |

Additional outputs can be enabled via configuration options, such as specific vehicle movement visualizations or cleaned GTFS export.


---


## Minimal example using the Python API 

This example is close to the CLI minimal example but uses the Python API. To run it, execute:

```bash
python api_basic_simulation.py
```

### Key Inputs

All inputs are defined and commented in the Python file (`api_basic_simulation.py`). The main inputs are:

* GTFS data folder (e.g., `data/sample_GTFS/`)
* Output folder (e.g., `results/api_basic_simulation`)
* Vehicle energy consumption
* Charging powers and charging strategy sequence
* Probabilities for terminal/stop charging and depot travel times

Advanced options for GTFS preprocessing, fleet simulation, and optional outputs are also documented in the file.

### Outputs

By default, the minimal API example produces :

* `fleet_operation.csv`: fleet operation results
* `charging_schedules_per_vehicle.csv`: per-vehicle charging events and battery info
* `charging_load_curve.csv`: aggregated charging load over time
* `GTFS_map_alldata.html`: visual map of the full GTFS network

Other outputs (detailed trip sequences, per-stop charging, charging maps, fleet trajectory maps, etc) can be enabled by uncommenting lines in the script.

## Next steps

1. Inspect CSV outputs to understand charging schedules and load curves.
2. Modify parameters in `config_basic.py` or the Python script to explore different scenarios.
3. Explore other example scripts (`api_ex_post_*`) for ex-post analyses like CO₂ savings, air pollution, or PV integration.
4. Review the **Methodology** section for details on fleet simulation and charging computations.
5. Refer to the **API Reference** for integration into your own Python scripts.