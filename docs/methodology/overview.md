# Overview of the simulation workflow

Based on General Transit Feed Specification (GTFS) data, GTFS4EV allows planners and researchers to quickly simulate bus operations and explore electrification scenarios without requiring proprietary or vehicle-level operational data. It bridges the gap between detailed agent-based simulators and simplified first-order calculators, providing a modular workflow for GTFS data pre-processing, fleet operation and charging simulation, and ex-post analysis of electrification impacts (CO2 savings, reduction of exposure to air pollution, fuel cost savings) and the potential integration of photovoltaic energy.

The core functionality of `GTFS4EV` spans three main dimensions, which together form also the high-level simulation workflow (see Figure 1):

1. **GTFS data pre-processing**: GTFS data validation and cleaning.
2. **Fleet operation simulation**: Data-based simulation of bus fleet operations, estimating the number of vehicles in operation and their travel patterns.
3. **Scenario-based charging**: Spatio-temporal charging demand, scenario feasibility, and infrastructure requirements (required number of chargers, required bus battery capacities) under user-defined electrification scenarios (i.e., available charging powers, charging strategy, and electric bus energy consumption)

<br>

![Workflow Diagram](../img/workflow_schematic.png)
*Figure 1: The GTFS4EV three-step workflow: GTFS data pre-processing, fleet simulation, and scenario-based charging.*

<br>

After the completion of the three steps, **ex-post** analysis can be performed, including:

* **Environmental impact assessment**: Calculation of CO₂ emissions savings and reduction in spatial exposure to air pollution resulting from bus fleet electrification.
* **Economic evaluation**: Estimation of fuel cost savings due to the shift from conventional to electric bus operations.
* **PV energy integration potential**: Analysis of the alignment between charging demand and local photovoltaic (PV) generation to assess opportunities for maximizing the use of on-site solar energy.

This ex-post evaluation provides insights to guide sustainable public transit planning and supports the strategic integration of local renewable energy.