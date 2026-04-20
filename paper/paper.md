---
title: 'GTFS4EV: A Python framework for electric bus planning using GTFS data'
tags:
  - Python
  - e-mobility
  - electric vehicles
  - electric bus
  - GTFS
  - GTFS-static
  - transport planning
  - solar energy
authors:
  - name: Jérémy Dumoulin
    orcid: 0000-0002-8991-8349
    corresponding: true 
    affiliation: "1" 
  - name: Cheikh Mouhamed Fadel Kebe
    orcid: 0009-0000-4121-5751
    affiliation: "1, 3"
  - name: David Wannier
    orcid: 0000-0001-9712-8366 
    affiliation: "4"
  - name: David Gianadda
    orcid: 0009-0006-5460-7061
    affiliation: "4"
  - name: Noémie Jeannin
    orcid: 0000-0001-5476-2375
    affiliation: "1"
  - name: Christophe Ballif
    orcid: 0000-0001-8989-0545
    affiliation: "1"
  - name: Nicolas Wyrsch
    orcid: 0000-0002-4588-0166
    affiliation: "1"
affiliations:
 - name: Photovoltaics and thin film electronics laboratory (PV-LAB), École Polytechnique Fédérale de Lausanne (EPFL), Institute of Electrical and Microengineering (IEM), Neuchâtel, Switzerland
   index: 1
 - name: Centre de Test des Systèmes Solaires (CT2S) of Dakar, Senegal
   index: 2
 - name: Laboratoire Eau, Energie, Environnement et Procédés Industriels (LE3PI), Ecole Supérieure Polytechnique, Cheikh Anta Diop University of Dakar, Senegal
   index: 3
 - name: Institute of Informatics (II), HES-SO Valais/Wallis, Sierre, Switzerland
   index: 4
bibliography: paper.bib
---

# Summary

Planning the electrification of public bus fleets is a complex task, that requires modelling multiple interacting components, including electric vehicle characteristics, travel patterns, available charging infrastructure, and context-specific operational constraints and objectives. However, this typically requires detailed operational data on bus movements, which are often unavailable or incomplete in many regions, creating a major barrier to public transport electrification.

To address this gap, we introduce GTFS4EV, an open-source tool that leverages the widely available General Transit Feed Specification (GTFS) data to support electric bus planning. Relying on GTFS as the primary data input, GTFS4EV enables the simulation of bus operations, the estimation of charging demand, and a feasibility assessment of various electrification pathways, while providing insights into key technical requirements such as battery sizing and charging infrastructure needs. The tool supports flexible exploration of context-specific scenarios, notably by enabling the user to implement custom charging strategies alongside predefined ones. As such, GTFS4EV serves as a powerful decision-support tool for identifying effective and tailored electrification pathways.

The tool is implemented as a modular Python library and provides a command-line interface for non-programming users. It enables rapid, data-driven exploration of realistic electrification scenarios, supporting bus operators and urban planners in assessing the requirements and benefits of different fleet electrification pathways. GTFS4EV also serves as a bridge between transport modelling and power system analysis by generating  charging demand profiles that can be directly used in power system models (e.g., pandapower [@pandapower2018] or OpenTEPES [@Ramos2022]), enabling grid impact assessments and integrated transport–power system analyses.

# Statement of need

The electrification of public transport systems is a central pillar of the transition to sustainable transport. Compared to conventional diesel buses, electric buses offer reductions in greenhouse gas emissions, air pollution, noise, and operating costs [@Boren2019; @Holland2020; @Ghotge2025]. However, planning for bus electrification remains a complex task. It requires jointly considering bus operations, charging strategies, and investments in both charging infrastructure and electric buses [@Shyam2021; @Alyson2021]. These factors, in turn, shape the broader benefits and challenges for electrification, notably the potential impact on local electricity grids [@Alyson2021].

In this context, GTFS4EV addresses the need for an open-source, GTFS-based framework for electric bus planning. It is designed for data-light, scenario-based simulation of fleet electrification pathways, supporting decision-making around fleet operations, charging strategies, infrastructure requirements, PV integration potential, and broader economic and environmental implications.

# State of the field

A number of modelling tools and studies have been developed to support the electric bus planning process. Many existing tools - often commercial and proprietary - provide detailed operational simulations based on vehicle-level datasets such as high-resolution GPS traces and detailed schedules (e.g., EVopt Planner [@evopt_planner], eDepotPlanner [@edepotplanner], eflips-X [@Heide2025]). While such data-rich models are well suited for advanced planning and operational fine-tuning, they are less appropriate for exploratory assessments that require a rapid evaluation of multiple electrification scenarios. Moreover, they rely on vehicle-level data that are often unavailable, particularly in emerging economies. At the other end of the spectrum, simplified tools based on generic operational assumptions (e.g., [@IEA_EV_Charging_Grid_Tool_TechnicalNote_2023]) enable quick first-order analyses but lack spatial analysis and the ability to capture local operational specificities. Together, these limitations reveal a gap for open modelling approaches that operate with limited data requirements while retaining sufficient operational realism to deliver context-specific quantitative insights.

In parallel, the increasing availability of open public transport data has created new opportunities for modelling bus electrification using openly accessible information. In particular, the General Transit Feed Specification has emerged as a widely adopted open standard, providing harmonized data on routes, stops, timetables, and service frequencies. Beyond the growing number of transit agencies publishing GTFS feeds, data collection initiatives have further expanded coverage [@DT4A]. As a result, a broad ecosystem of open-source tools has emerged to generate, process, analyze, and visualize GTFS data [@gtfs_org]. However, only a limited number of these tools explicitly leverage GTFS data for bus electrification planning, and these address only part of the functionality needed to support informed decision-making:

- RouteZero [@Hendriks2024] focuses on depot charging optimization using mixed-integer linear programming. While effective for depot-centric analyses, it does not support opportunity or mixed charging strategies and is limited to charging demand and power analyses, without considering broader implications such as greenhouse gas emissions, air pollution, or integration with renewable energy sources.

- gtfs2emis [@Vieira2023] estimates vehicle movements and emissions from GTFS data and is primarily designed for environmental impact assessment. Hence, it does not model charging behavior or infrastructure requirements, limiting its applicability for electrification planning.

- GTFS_PowerTransNet [@zhao2023gridaware] generates coupled representations of transit networks and simplified power grid topologies using GTFS data to identify candidate charging locations. While valuable for co-planning studies, it offers limited other decision-support capabilities for electrification planning.

- Eventually, some microtraffic simulation frameworks that integrate GTFS data import (e.g., tools such as EV-Fleet-Sim [@Abraham2021]) can be used to model transport operations and associated vehicle electric energy consumption. While useful to fine-tune the charging demand and, in some cases, perform rerouting studies, they do not support strategic planning of charging infrastructure or battery capacity which requires to simulate not only the energy consumption but also the charging behaviour.

# Software design

GTFS4EV is a simulation framework that combines data-driven modelling of bus fleet operations with user-defined electrification scenarios to assess the feasibility and spatio-temporal charging demand of bus fleet electrification. The framework is designed for rapid exploration of scenarios rather than detailed operational optimisation. It assumes fixed, GTFS-defined bus operations, thereby isolating electrification analyses from service planning decisions.

The core functionality of GTFS4EV spans three main dimensions, which together form also the high-level simulation workflow as illustrated in Figure 1:

1. **GTFS data pre-processing**: The input GTFS feed is validated and cleaned, and can optionally be filtered (e.g. suppression of services) or enriched (e.g. addition of extra idle times at stops or terminals). The output is a consistent GTFS dataset.
2. **Fleet operation simulation**: Using the pre-processed GTFS data, GTFS4EV simulates bus fleet operations. The number of vehicles in operation and their movements are estimated to meet the GTFS schedule, enabling the simulation of individual vehicle travel patterns throughout the service day.
3. **Scenario-based charging**: Based on user-defined electrification scenarios (i.e., available charging powers, charging strategy, and electric bus energy consumption) the model estimates the charging schedules for each individual vehicle. This enables the assessment of electrification feasibility, spatio-temporal charging demand, and associated infrastructure requirements (required number of chargers at various locations, required battery capacities). 

![Overview of the three main steps of the simulation workflow](workflow_schematic.png)

GTFS4EV also includes supporting features such as built-in visualization and basic GTFS feed analysis, as well as a flexible charging strategy logic (i.e., multiple charging strategies can be defined and applied sequentially). The framework provides default rule-based depot and opportunity charging strategies, while remaining explicitly designed to accommodate additional user-defined strategies.Beyond the core simulation, GTFS4EV supports a set of ex-post analyses derived from the simulated fleet operation and charging demand. In particular, it enables a preliminary assessment of PV integration potential by evaluating the temporal alignment between locally estimated PV generation and the aggregated charging demand. Additional ex-post analyses include the estimation of CO$_2$ emissions savings, reductions in air pollution exposure, and fuel cost savings relative to conventional diesel operations. Together, these complementary analyses broaden the decision space addressed by GTFS4EV and support the needs of the various stakeholders involved in public bus fleet electrification.

The model is implemented as a modular Python package with an object-oriented design. Core classes correspond to the main workflow steps: GTFS data preprocessing, fleet operation simulation, and scenario-based charging demand estimation. Two additional classes support the assessment of local PV production and PV integration potential. Other classes provide ex-post impact analysis, including emissions and cost savings.

The package can be executed via a command-line interface, enabling rapid case studies and use by non-programmers. For greater flexibility and advanced usage, it can also be imported within Python scripts, allowing customized analyses and integration into other simulation workflows.

# Research impact statement

GTFS4EV has been developed within the HORIZON OpenMod4Africa project, supporting energy and transport modelling in data-constrained regions. By relying on widely available GTFS inputs and transparent modelling assumptions, the framework enables reproducible and transferable analyses. The software is released as open source and designed for easy extension, with the aim of adoption by a wide community.

It has already been applied in several studies, including a published paper on the benefits and challenges of minibus electrification in African cities [@Dumoulin2026], a master’s thesis on bus electrification in Addis Ababa [@Yifru2025], and ongoing work on the solarisation of bus rapid transit (BRT) systems in Dakar [@OpenMod4Africa2025WACREKeynote] and other transport modes. 

# Acknowledgements

This project was supported by the HORIZON OpenMod4Africa project (Grant number 101118123), with funding from the European Union and the State Secretariat for Education, Research and Innovation (SERI) for the Swiss partners. We gratefully acknowledge the support of all OpenMod4Africa partners for their contributions and collaboration. We also express our  gratitude to the developers of the PVlib toolbox [@pvlib], which is used to support the calculation of the local PV production.

# AI usage disclosure

ChatGPT (OpenAI, GPT-3.5) was used to assist with language editing and structural refinement of the manuscript. In addition, it was used to improve software documentation (docstrings) and to assist in drafting unit tests.

No generative AI tools were used to make scientific or methodological decisions, nor to define the core model architecture or implementation logic of GTFS4EV. All software design choices, methodological developments, and validation steps were conducted by the authors. Any AI-generated suggestions were critically reviewed, modified where necessary, and validated by the authors prior to inclusion. The authors take full responsibility for all submitted content.

# References

