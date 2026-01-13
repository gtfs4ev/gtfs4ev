# Welcome to the GTFS4EV Documentation

## Introduction

<p>
  <img src="img/logo_with_text.png" style="float:left; width:60%;">
</p>
<div style="clear: both;"></div>


**GTFS4EV** is an open-source Python tool designed to support the **planning of public bus electrification**. 

Leveraging the standardized General Transit Feed Specification (GTFS), it allows planners and researchers to quickly **simulate bus operations** and explore **electrification scenarios** without requiring proprietary or vehicle-level operational data. It bridges the gap between detailed agent-based simulators and simplified first-order calculators, providing a modular workflow for *GTFS data pre-processing*, *fleet operation* and *charging simulation*, and *ex-post analysis of impacts* (CO2 savings, exposure to air pollution, fuel cost savings) and the potential integration of *photovoltaic energy*.

By relying on GTFS feeds as primary inputs, GTFS4EV provides a **simple and data-driven workflow** for analyzing electrification scenarios in public transport systems.

The tool is flexible, allowing users to adapt simulations and analyses to different assumptions, technologies, and scenarios. It can be imported as a Python library or used with a command-line interface (CLI). The API of GTFS4EV has been designed in an object-oriented manner and is easily extendable.

---

## Getting Started

To start using our software, refer to the **Getting Started** section, which will guide
you through the following steps:

1. **Install the package**  
   Instructions for installing GTFS4EV and its dependencies are provided in the
   [Installation](getting-started/installation.md) section.

2. **Run your first simulation**  
   The [Quickstart](getting-started/quickstart.md) guide walks through a minimal example,
   using either the command-line interface (CLI) or the GTFS4EV classes in your own
   Python code.

3. **Explore practical examples**  
   The [Examples](getting-started/examples.md) section demonstrates common use cases
   and illustrates different features of GTFS4EV.

For a deeper understanding of the underlying methods and assumptions, refer to the
[Methodology](methodology/overview.md) section.

Detailed technical documentation of the available modules is provided in the 
[API Reference](api/package-structure.md). This section is intended for users and 
developers who want to integrate GTFS4EV into their own python workflows or extend 
its functionality.

---

## Authors

`GTFS4EV` is initially developed by EPFL (Switzerland), within the Photovoltaics and Thin Film Electronics Laboratory ([PV-Lab](https://www.epfl.ch/labs/pvlab/)). 

A full list of contributors can be found in the project’s GitHub repository.

---

## Suggestions and contributions

We welcome any contributions or suggestions! Please see our [Contributing](appendix/contributing.md) section. If you encounter a bug or have a feature request, please open an issue on Github or contact us.

---

## Acknowledgment

This project was supported by the HORIZON [OpenMod4Africa](https://openmod4africa.eu/) project (Grant number 101118123), with funding from the European Union and the State Secretariat for Education, Research and Innovation (SERI) for the Swiss partners. We also gratefully acknowledge the support of OpenMod4Africa partners for their contributions and collaboration.

---
