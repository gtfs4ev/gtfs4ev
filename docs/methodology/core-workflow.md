# Core Workflow

This page describes the **key methodological aspects** of the GTFS4EV core workflow, structured around its three main steps: GTFS data pre-processing, fleet operation simulation, and scenario-based charging.

---

## GTFS data pre-processing

GTFS data pre-processing constitutes the **first step** of the GTFS4EV workflow. This step ensures that the input data are represented as a **complete, consistent, and simulation-ready** data. It also provides additional data manipulation features, such as restricting the analysis to specific operating services or agencies, introducing idle times when these are not explicitly present in the original feed, and producing transit analyses and visualizations.

From a methodological perspective, this step defines the interface between raw data and input data suitable for simulation.

### About GTFS data

The static General Transit Feed Specification (GTFS) is a standard data format with a **relational structure** used to describe public transport schedules and networks. As shown in Fig. 1, a GTFS feed consists of multiple text files, each representing a specific aspect of the transport system (e.g. agencies, trips, shapes, etc).

![GTFS Data Structure](../img/gtfs_data_structure.png)
*Figure 1: Overview of GTFS data structure, showing the link between each table through identifiers.*

These tables are linked through identifiers, and their correct interpretation relies strongly on the **consistency of these links across files**. As a result, additional validation and cleaning is recommended before the data can be used for simulation-based analyses.

> **Note:** While the `frequencies.txt` file is formally optional in the GTFS specification, GTFS4EV relies on headway-based service representations for fleet operation simulation. Hence, GTFS feeds in which every trip is defined as an individual trip (i.e. without a corresponding frequency-based representation), are not supported by the current simulation logic.

### Method for ensuring internal consistency

A key methodological feature of the GTFS data pre-processing stage is to ensure **internal consistency across all GTFS tables**. For simulation-ready analyses, the input data must form **a closed system of mutually referenced entities**. Hence, agencies, routes, services, trips, stop times, stops, shapes, and frequencies must all be connected through valid references, with no isolated or incomplete elements.

The consistency process therefore follows two complementary principles:

1. **Systematic validation of cross-table references**  
   Each GTFS table is checked against the ones it is linked to others to verify that all identifiers point to existing entities. 

2. **Iterative removal of inconsistencies**  
   When inconsistencies are detected, entities that cannot be simulated are removed. Because removing one element may create new inconsistencies elsewhere, the cleaning process is applied **iteratively** until the dataset reaches a stable state in which all remaining elements are mutually consistent.

This iterative cleaning strategy is intentionally restrictive. Trips that lack essential information for fleet operation simulation are removed, and subsequently any remaining entities that are no longer referenced by the retained trips.



