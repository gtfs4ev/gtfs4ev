# Ex-post solar integration, environmental, and economic analyses

This page describes the **methodological principles** underlying the analytical modules that build on GTFS4EV fleet operation and charging simulation outputs. These analyses translate simulated vehicle activity into indicators related to **energy synergies**, **greenhouse gas emissions**, **economic costs**, and **air pollution exposure**.

All analyses are conducted as **post-processing steps** and do not affect the fleet operation simulation itself.

---

## PV simulation and EV–PV synergy analysis

The EV–PV synergy analysis quantifies the degree of alignment between electric vehicle (EV) charging demand and photovoltaic (PV) electricity production. PV generation is modeled using a **capacity factor approach**, in which normalized PV profiles are scaled by an installed capacity. 

The local **PV production potential** is calculated using the [PVLib toolbox](https://pvlib-python.readthedocs.io) (Anderson et al., 2023), which allows detailed yet computationally efficient simulations by integrating environmental conditions, PV module specifications, and installation parameters. Hourly weather data are sourced from the **PVGIS-SARAH3** database (Jensen et al., 2023) and include irradiance, temperature, and other relevant environmental variables.  

At each time step \( t \), the **plane-of-array irradiance** \( G_{\text{POA}}(t) \) [W/m²] is computed based on the global, diffuse, and direct irradiance components and the PV module’s installation angles (tilt and azimuth). These angles are either optimized for maximum annual yield (freestanding systems) or fixed (horizontal roof-mounted systems).  

The **instantaneous PV power** \( P_{\text{PV}}(t) \) is calculated using a **PVWatts-style model**:

\[
P_{\text{PV}}(t) = \eta_{\text{PV}} \cdot G_{\text{POA}}(t) \cdot \Big[ 1 + \beta \cdot \big(T_{\text{cell}}(t) - T_{\text{ref}}\big) \Big]
\]

where:  

- \( \eta_{\text{PV}} \) = nominal module efficiency  
- \( \beta \) = temperature coefficient [1/°C]  
- \( T_{\text{cell}}(t) \) = module operating temperature calculated using the PVsyst temperature model  
- \( T_{\text{ref}} \) = reference temperature (25 °C)  

Angular losses are incorporated at each time step using the analytical **Martin–Ruiz model** (2001). Additional system losses are applied **ex-post** through a loss factor.  

The **capacity factor** for each hour is then obtained as:

\[
CF(t) = \frac{P_{\text{PV}}(t)}{P_{\text{PV}}^{\text{inst}}}
\]

where \( P_{\text{PV}}^{\text{inst}} \) is the installed PV capacity. Total daily PV energy is computed by integrating hourly power over 24 hours:

\[
E_{\text{PV}} = \int_0^{24} P_{\text{PV}}(t)\, dt
\]

**EV–PV synergy metrics** are derived by combining PV generation with simulated EV charging demand \( P_{\text{EV}}(t) \), including:

- **Energy coverage ratio:** \( E_{\text{PV}} / E_{\text{EV}} \)  
- **Self-sufficiency ratio:** \( \frac{\int_0^{24} \min(P_{\text{PV}}(t), P_{\text{EV}}(t))\, dt}{E_{\text{EV}}} \)  
- **Self-consumption ratio:** coincident PV divided by total PV production  
- **Excess PV ratio:** fraction of PV not consumed by EVs  
- **Spearman correlation** between PV and EV profiles  

> **Notes:**  

> 1. Two predefined PV simulation **presets** are available: (1) **freestanding with optimal tilt**: Ground-mounted, tilt optimized for maximum annual yield ; (2) **flat roof**: Horizontal roof-mounted (tilt = 0°), reduced ventilation. 

> 2. The simulator assumes **ideal inverter** operation, with **system losses applied ex-post**.

> 3. No degradation, curtailment, or grid constraints are modeled.

> 4. The methodology is designed for **annual simulations** (single year).

> 5. Results represent **theoretical energy synergies**, not operational dispatch. Also, the EV-PV synergy analysis uses the charging profiles **as provided**. To model battery storage or demand-shifting strategies, dedicated charging strategy inputs are required. 

---

## CO₂ emission impact analysis

The CO₂ emission analysis estimates greenhouse gas emission reductions achieved by replacing diesel vehicles with electric vehicles. The methodology relies on a **per-kilometer comparison** between diesel and electric drivetrains.

Diesel emissions per kilometer are computed as:

\[
e_{\text{diesel}} = c_{\text{diesel}} \cdot \gamma_{\text{diesel}}
\]

where \( c_{\text{diesel}} \) is fuel consumption (L/km) and \( \gamma_{\text{diesel}} \) is the CO₂ intensity of diesel fuel (kgCO₂/L).

Electric vehicle emissions per kilometer are computed from electricity consumption and grid carbon intensity:

\[
e_{\text{EV}} =
\frac{c_{\text{EV}}}{\eta_{\text{charge}}} \cdot \gamma_{\text{el}}
\]

where \( c_{\text{EV}} \) is electricity consumption (kWh/km), \( \eta_{\text{charge}} \) is charging efficiency, and \( \gamma_{\text{el}} \) is electricity CO₂ intensity (kgCO₂/kWh).

Total annual CO₂ emission reduction is then computed as:

\[
\Delta \text{CO}_2 =
D_{\text{year}} \cdot \left(e_{\text{diesel}} - e_{\text{EV}}\right)
\]

where \( D_{\text{year}} \) is the total annual distance driven.

---

## Economic cost analysis

The economic analysis estimates **operational energy cost savings** associated with electrifying vehicle operations. As in the emissions analysis, costs are computed on a per-kilometer basis.

Diesel operating cost per kilometer is defined as:

\[
c_{\text{diesel}}^{\text{cost}} = c_{\text{diesel}} \cdot p_{\text{diesel}}
\]

where \( p_{\text{diesel}} \) is the diesel price (currency/L). Electric operating cost per kilometer is defined as:

\[
c_{\text{EV}}^{\text{cost}} =
\frac{c_{\text{EV}}}{\eta_{\text{charge}}} \cdot p_{\text{el}}
\]

where \( p_{\text{el}} \) is the electricity price (currency/kWh).

Total annual economic savings are computed as:

\[
\Delta C =
D_{\text{year}} \cdot
\left(c_{\text{diesel}}^{\text{cost}} - c_{\text{EV}}^{\text{cost}}\right)
\]

This analysis focuses on **energy-related operating costs only** and excludes capital expenditures, maintenance costs, and infrastructure investments.

---

## Air pollution exposure analysis

The air pollution exposure analysis estimates changes in population exposure to traffic-related air pollutants (TRAP) from vehicle operations, emphasizing the spatial variability of health impacts due to emissions.

Exposure to TRAP is indirectly assessed using a **distance-weighted traffic volume indicator** based on vehicle-kilometers traveled (FKT) and spatial dispersion. For each location (pixel) \( k \), the **local TRAP exposure indicator** \( I_k \) is computed as the sum of emissions from nearby pixels \( g \) within a buffer radius (300 m by default), weighted by an exponential decay function representing pollutant dispersion with distance:

\[
I_k = \sum_{g \in D_k} \epsilon_g \cdot e^{-\lambda d_{gk}}
\]

where:  

- \( D_k \) is the buffer zone around pixel \( k \) (300 m radius) capturing near-road exposure,  
- \( \epsilon_g \) is the local emission index at pixel \( g \), calculated from the fraction of vehicle-kilometers traveled within that pixel based on vehicle trajectories and travel distances from the fleet operation simulation,  
- \( d_{gk} \) is the distance between pixels \( g \) and \( k \),  
- \( \lambda \) is the pollutant decay rate with distance (set conservatively high by default to avoid overestimation).

This approach captures the rapid decrease in pollutant concentrations near roads, consistent with established air pollution studies. The indicator \( I_k \) effectively represents the cumulative TRAP exposure at location \( k \)..

Based on this, a **local population exposure** can then derived by *combining the TRAP exposure index with high-resolution population density data*. The final output is a spatially explicit, population-weighted indicator of air pollution exposure, highlighting health-relevant benefits from electrifying vehicle fleets. This method does not explicitly model atmospheric dispersion or secondary pollutants but provides a robust, relative measure of local exposure reduction.