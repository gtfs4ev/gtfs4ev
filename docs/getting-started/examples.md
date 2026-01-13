This page provides an overview of the examples included in the GitHub repository. 
Each example demonstrates some functionality of GTFS4EV, either via the command-line interface (CLI) or the Python API.

> ⚠️ It is recommended to start with the [Quickstart guide](quickstart.md) before running these examples. It explains how to run a minimal working example and prepares you for using the CLI and API scripts.

You can download the examples from the [GitHub repository](https://github.com/gtfs4ev/gtfs4ev/tree/main/examples). The specific files to download depend on the examples you want to run:

* CLI examples (`cli_*.py`) require the corresponding `data/` folder.
* API examples (`api_*.py`) require the `data/` folder and the specific Python scripts.

> Alternatively, you can [download the full GTFS4EV repository as a ZIP](https://github.com/gtfs4ev/gtfs4ev/tree/main/zipball/master/) and copy the examples folder.

The `data/` folder needs to be donwloaded in any case. It contains an example dataset derived from the **Digital Matatu Project** for Nairobi, Kenya. It contains a subset of the Nairobi GTFS feed (2 routes) with minor modifications for demonstration.

* Source: Digital Transport For Africa Gitlab (downloaded 01.09.2024)
* Link: [https://gitlab.com/digitaltransport/data/africa/nairobi](https://gitlab.com/digitaltransport/data/africa/nairobi)

## Minimal Working Example

The minimal examples are described in the [Quickstart guide](quickstart.md) and cover both CLI (`cli_basic.py`) and Python API (`api_basic_simulation.py`). Ensure the corresponding `data/` folder and script are in the same directory.

## Specialized API Examples

The following API examples demonstrate other GTFS4EV features such as preprocessing, custom charging strategies, and ex-post impact analyses.

| Script                            | Description                                                                                           |
| --------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `api_gtfs_preprocessing.py`       | Preprocessing of GTFS data: validation, cleaning, filtering, and exporting cleaned GTFS. |
| `api_custom_charging_strategy.py` | Shows how to define custom charging strategies using the API.                                         |
| `api_ex_post_co2savings.py`       | Ex-post analysis of CO₂ savings from the simulation results.                             |
| `api_ex_post_airpollution.py`     | Ex-post analysis of spatial air pollution exposure reduction.                                    |
| `api_ex_post_costsavings.py`      | Ex-post analysis of fuel/cost savings.                                                   |
| `api_ex_post_pv.py`               | Demonstrates the potential of integration of photovoltaic generation with the charging strategy.                         |

## How to run the examples

1. Download the repository or the specific examples and `data/` folder you need.
2. Edit configuration files (for CLI) or parameters in the scripts (for API) as needed.
3. Run the scripts using the CLI or Python interpreter.
4. Inspect outputs in the designated `output_folder` for analysis and visualization.

