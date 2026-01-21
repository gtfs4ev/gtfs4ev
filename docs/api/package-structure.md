# Package structure

The `gtfs4ev` package is organized into several key submodules, each encapsulating distinct functionalities.

## Overview

```
gtfs4ev/
├── analysis/       # Post‑processing analysis modules
├── cli/            # Command‑line interface scripts (internal)
├── core/           # Core simulation engine and GTFS data processing
└── utils/          # Internal helper functions (internal)
```

### Public API vs. Internal modules

**Public API modules:**

  - `analysis/` — users will commonly interact with classes and functions here when performing post‑simulation analyses (e.g., energy synergies, emission and cost savings).  
  - `core/` — contains the primary simulation classes that users instantiate and run.  

**Internal modules** (not intended for direct public use):

  - `cli/` — internal CLI scripts used by the package executable.  
  - `utils/` — helper functions used across modules but not part of the documented API surface.

> Modules under `cli` and `utils` exist to support the package’s internal functioning and are *not intended* for direct use in user code.

---

## Submodule descriptions

### `core/`

This submodule implements the **simulation engine** of GTFS4EV with three core classes (`GTFSManager`, `FleetSimulator`, and `ChargingSimulator`). 

These are the foundational building blocks users import when setting up and running simulations.

**Typical imports:**

```python
from gtfs4ev.core.gtfs_manager import GTFSManager
from gtfs4ev.core.fleet_simulator import FleetSimulator
```

---

### `analysis/`

Contains **post‑processing analysis modules** that take simulation outputs and compute indicators such as:

- EV–PV energy synergy metrics  
- CO₂ emission reductions  
- Economic operating cost savings  
- Air pollution exposure

Each analysis class encapsulates a specific set of analytical routines and metrics.

**Example usage:**

```python
from gtfs4ev.analysis.evpvsynergies import EVPVSynergies
from gtfs4ev.analysis.co2savings import CO2Savings
```