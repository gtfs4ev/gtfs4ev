    ###############################################################################
    ############################ STEP 4: PV Simulation ############################ 
    ###############################################################################

    pv = PVSimulator(
        environment={
            'latitude': 0.17094549,  
            'longitude': 37.9039685,  
            'year': 2020  
        }, 
        pv_module={
            'efficiency': 0.22,
            'temperature_coefficient': -0.004  
        }, 
        installation={
            'type': 'rooftop',  # Options: 'rooftop' or 'groundmounted_fixed'
            'system_losses': 0.14
        }
    )

    pv.compute_pv_production() # Calculate PV production based on the defined parameters
    pv.results.to_csv("output/PV_production.csv") # Save PV production data

    ###############################################################################
    ######################## STEP 5: EV-PV Complementarity ######################## 
    ###############################################################################

    evpv = EVPVSynergies(pv=pv, load_curve=load_curve, pv_capacity_MW=10)

    # Calculate daily synergy metrics for the first week of January, adjusting recompute_probability as needed
    synergy_metrics = evpv.daily_metrics("01-01", "01-03")
    synergy_metrics.to_csv("output/EVPVSynergies.csv") # Save synergy metrics data
    