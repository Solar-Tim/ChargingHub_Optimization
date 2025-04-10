###############################################################################
# Charging Hub Optimization Model
# Author: Tim Sanders
# Purpose: Optimize charging hub design including grid connection, battery storage,
#          and transformer selection to minimize total capital expenditure
###############################################################################

#------------------------------------------------------------------------------
# SECTION 1: IMPORTS AND INITIALIZATION
#------------------------------------------------------------------------------
import os
import sys
import json
import time
import numpy as np
from pathlib import Path  # Add this import here
from gurobipy import Model, GRB
from shapely.geometry import Point
from concurrent.futures import ProcessPoolExecutor

# Add the parent directory (scripts) to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from functions import * 
# Import config_grid before other modules that might depend on it
from grid_optimization.config_grid import *
from config_grid import generate_result_filename as grid_generate_result_filename
from cables import *
from grid_optimization.data_loading import load_data
from grid_optimization.data_extraction import extract_charger_counts

# Fix the import path for distance module
# This line is already correctly handling the path for distance_scripts
from distance_scripts.distance_functions import *
from distance_scripts.distance_lines import *


strategy = all_strategies  # Default strategy for testing
#------------------------------------------------------------------------------
# SECTION 2: DATA LOADING AND PREPROCESSING
#------------------------------------------------------------------------------
def run_optimization_for_strategy(strategy):
    """
    Run the optimization model for a specific charging strategy
    
    Args:
        strategy (str): Charging strategy to use (e.g., "T_min", "Konstant", "Hub")
        
    Returns:
        dict: Optimization results
    """
    print(f"\n{'='*80}\nRunning optimization for strategy: {strategy}\n{'='*80}")
    
    # Get location from environment variables or fall back to config
    location_longitude = float(os.environ.get('CHARGING_HUB_LONGITUDE', Config.DEFAULT_LOCATION['LONGITUDE']))
    location_latitude = float(os.environ.get('CHARGING_HUB_LATITUDE', Config.DEFAULT_LOCATION['LATITUDE']))

    # Print location for verification
    print(f"Using location: Longitude={location_longitude}, Latitude={location_latitude}")
    ref_point = Point(location_longitude, location_latitude)

    # Define a large value for M constraints early - will be refined later
    M_value = 1000000  # Initial large value for big-M constraints
    
    
    # Toggle between calculated distances and manual distances
    if use_distance_calculation: # type: ignore
        distances = calculate_all_distances(ref_point, create_distance_maps) # type: ignore
        print(f"Using calculated distances for coordinates: ({location_longitude}, {location_latitude})")
    else:
        distances = manual_distances # type: ignore
        print("Using manual distances from config file")


    # Load data
    load_profile, timestamps = load_data(strategy)
    results = {}
    print(f"Data loaded successfully using {strategy} strategy")
    print("Running optimization")

    # Safely get the length
    time_periods = len(load_profile) if load_profile is not None else 0
    
    # Refine M_value based on load profile if available
    if load_profile is not None:
        M_value = max(M_value, max(load_profile) * 10)

    # Add distance parameters to model
    distribution_substation_distance = distances['distribution_distance'] or float('inf')
    transmission_substation_distance = distances['transmission_distance'] or float('inf')
    hvline_distance = distances['powerline_distance'] or float('inf')

    # Extract charging data and charger counts
    if not use_manual_charger_count:
        charger_counts = extract_charger_counts(strategy)
        MCS_count = charger_counts.get("MCS", 0)
        HPC_count = charger_counts.get("HPC", 0)
        NCS_count = charger_counts.get("NCS", 0)
        print(f"Charger counts updated: MCS: {MCS_count}, HPC: {HPC_count}, NCS: {NCS_count}")
    else:
        print("Using manual charger counts from config")
        # Keep using the manual values imported previosly from config

    #------------------------------------------------------------------------------
    # SECTION 3: CABLE OPTIONS CALCULATION
    #------------------------------------------------------------------------------
    # Calculate cable options for each connection type
    transmission_cable_options = calculate_cable_options(transmission_substation_distance)
    print(f"Calculated {len(transmission_cable_options)} cable options for transmission connection")

    distribution_cable_options = calculate_cable_options(distribution_substation_distance)
    print(f"Calculated {len(distribution_cable_options)} cable options for distribution connection")

    hvline_cable_options = calculate_cable_options(hvline_distance, HV_Substation_cost)
    print(f"Calculated {len(hvline_cable_options)} cable options for HV line connection")

    transmission_power_points, transmission_cost_points = extract_points_from_options(transmission_cable_options)
    distribution_power_points, distribution_cost_points = extract_points_from_options(distribution_cable_options)
    hvline_power_points, hvline_cost_points = extract_points_from_options(hvline_cable_options)

    #------------------------------------------------------------------------------
    # SECTION 4: MODEL INITIALIZATION
    #------------------------------------------------------------------------------
    # Create optimization model
    model = Model("Charging Hub CAPEX Optimization")

    #------------------------------------------------------------------------------
    # SECTION 5: VARIABLE DEFINITIONS
    #------------------------------------------------------------------------------

    # === 5.1: Grid Connection Variables ===
    # Binary variables for connection type selection
    use_transmission_substation = model.addVar(vtype=GRB.BINARY, name="NewTransmissionSubstationLink")
    use_distribution_substation = model.addVar(vtype=GRB.BINARY, name="NewDistributionSubstationLink")
    use_hv_line = model.addVar(vtype=GRB.BINARY, name="NewHVLine")
    use_existing_mv_line = model.addVar(vtype=GRB.BINARY, name="ExistingMVLine")

    # === 5.2: Substation Expansion Variables ===
    # Variables for capacity expansion of substations
    distribution_expansion = model.addVar(lb=0, ub=distribution_max_expansion, name="DistributionExpansion")
    transmission_expansion = model.addVar(lb=0, ub=transmission_max_expansion, name="TransmissionExpansion")
    # Binary indicators for expansion decisions
    expand_distribution = model.addVar(vtype=GRB.BINARY, name="ExpandDistribution")
    expand_transmission = model.addVar(vtype=GRB.BINARY, name="ExpandTransmission")

    # === 5.3: Grid Capacity Variables ===
    max_grid_load = model.addVar(lb=0, name="GridLoad")
    cap_limit = model.addVar(lb=0, name="CapacityLimit")

    # === 5.4: Cable Selection Variables ===
    # Get cable sizes and capacities from aluminium_kabel
    cable_sizes = aluminium_kabel["Nennquerschnitt"] 
    num_cable_options = len(cable_sizes)

    # Create numpy arrays for capacity and costs
    cable_capacities_vec = np.array([get_cable_capacity(size) for size in cable_sizes])
    transmission_cable_costs_vec = np.array([calculate_total_cable_cost(size, transmission_substation_distance) for size in cable_sizes])
    distribution_cable_costs_vec = np.array([calculate_total_cable_cost(size, distribution_substation_distance) for size in cable_sizes])
    hvline_cable_costs_vec = np.array([calculate_total_cable_cost(size, hvline_distance, HV_Substation_cost) for size in cable_sizes])

    # Create vector binary variables for each possible cable size
    transmission_cable_choice = model.addMVar(num_cable_options, vtype=GRB.BINARY, name="TransmissionCableChoice")
    distribution_cable_choice = model.addMVar(num_cable_options, vtype=GRB.BINARY, name="DistributionCableChoice")
    hvline_cable_choice = model.addMVar(num_cable_options, vtype=GRB.BINARY, name="HVLineCableChoice")

    # === 5.5: Energy System Variables ===
    # Grid energy variables
    grid_energy = model.addVars(time_periods, lb=0, name="GridEnergy")

    # Battery system variables
    use_battery = model.addVar(vtype=GRB.BINARY, name="UseBattery")  # New binary variable for battery toggle
    battery_capacity = model.addVar(lb=0, ub=battery_capacity_max, name="BatteryCapacity")
    battery_charge = model.addVars(time_periods, lb=0, ub=battery_charge_rate_max, name="BatteryCharge")
    battery_discharge = model.addVars(time_periods, lb=0, ub=battery_charge_rate_max, name="BatteryDischarge")
    battery_soc = model.addVars(time_periods, lb=0, ub=battery_max_soc * battery_capacity_max, name="BatterySOC")
    battery_peak_power = model.addVar(lb=0, name="BatteryPeakPower")  # New variable for peak battery power

    # Binary variables for battery operation state
    is_charging = model.addVars(time_periods, vtype=GRB.BINARY, name="IsCharging")
    is_discharging = model.addVars(time_periods, vtype=GRB.BINARY, name="IsDischarging")

    # === 5.6: Cost Tracking Variables ===
    connection_cost_value = model.addVar(name="ConnectionCostValue", lb=0)
    capacity_cost_value = model.addVar(name="CapacityCostValue", lb=0)
    battery_cost_value = model.addVar(name="BatteryCostValue", lb=0)
    battery_capacity_cost = model.addVar(name="BatteryCapacityCost", lb=0)  # New separate cost for battery capacity
    battery_power_cost = model.addVar(name="BatteryPowerCost", lb=0)  # New separate cost for battery power
    transformer_cost_value = model.addVar(name="TransformerCostValue", lb=0)
    expansion_cost_value = model.addVar(name="ExpansionCostValue", lb=0)
    internal_cable_cost_value = model.addVar(name="InternalCableCostValue", lb=0)  # New variable for internal cabling
    charginghub_cost_value = model.addVar(name="ChargingHubCostValue", lb=0)
    charger_cost_value = model.addVar(name="ChargerCostValue", lb=0)  # New variable for charger costs

    # === 5.7: Transformer Selection Variables ===
    # Modified to allow multiple transformers of different types
    transformer_count = model.addVars(len(transformer_capacities), vtype=GRB.INTEGER, lb=0, name="TransformerCount")

    #------------------------------------------------------------------------------
    # SECTION 6: CONSTRAINT DEFINITIONS
    #------------------------------------------------------------------------------

    # === 6.1: Grid Connection Constraints ===
    # Only one grid connection type can be chosen
    model.addConstr(use_distribution_substation + use_transmission_substation + use_existing_mv_line + use_hv_line == 1, 
                    "GridConnectionChoice")

    # === 6.2: Cable Selection Constraints ===
    # Only one cable size can be selected for each connection type (if that connection is used)
    model.addConstr(
        transmission_cable_choice.sum() == use_transmission_substation, 
        "TransmissionCableSelection"
    )
    model.addConstr(
        distribution_cable_choice.sum() == use_distribution_substation, 
        "DistributionCableSelection"
    )
    model.addConstr(
        hvline_cable_choice.sum() == use_hv_line, 
        "HVLineCableSelection"
    )

    # Matrix constraints to ensure the selected cable can handle the required capacity
    # max_grid_load ≤ cable_capacities_vec @ cable_choice + M(1-connection_used)
    model.addConstr(
        max_grid_load <= cable_capacities_vec @ transmission_cable_choice + 
                        M_value * (1 - use_transmission_substation),
        "TransmissionCapacityCheck"
    )
    model.addConstr(
        max_grid_load <= cable_capacities_vec @ distribution_cable_choice + 
                        M_value * (1 - use_distribution_substation),
        "DistributionCapacityCheck"
    )
    model.addConstr(
        max_grid_load <= cable_capacities_vec @ hvline_cable_choice + 
                        M_value * (1 - use_hv_line),
        "HVLineCapacityCheck"
    )

    # === 6.3: Cable Cost Calculations ===
    # Variables for storing cable costs
    transmission_cable_cost = model.addVar(name="TransmissionCableCost", lb=0)
    distribution_cable_cost = model.addVar(name="DistributionCableCost", lb=0)
    hvline_cable_cost = model.addVar(name="HVLineCableCost", lb=0)

    # Calculate cost using dot products of cost vectors and cable choice vectors
    model.addConstr(
        transmission_cable_cost == transmission_cable_costs_vec @ transmission_cable_choice,
        "TransmissionCableCostCalc"
    )
    model.addConstr(
        distribution_cable_cost == distribution_cable_costs_vec @ distribution_cable_choice,
        "DistributionCableCostCalc"
    )
    model.addConstr(
        hvline_cable_cost == hvline_cable_costs_vec @ hvline_cable_choice,
        "HVLineCableCostCalc"
    )

    # Calculate total connection cost using the discrete cable costs
    total_connection_cost = (
        transmission_cable_cost * use_transmission_substation + 
        distribution_cable_cost * use_distribution_substation + 
        hvline_cable_cost * use_hv_line + 
        existing_mv_connection_cost * use_existing_mv_line
    )

    # === 6.4: Two-Stage Grid Capacity Model ===
    # Grid capacity calculation: combines base capacity with expansion capacity for each connection option
    model.addConstr(
        cap_limit == use_existing_mv_line * existing_mv_capacity + 
        use_distribution_substation * (distribution_existing_capacity + distribution_expansion) + 
        use_transmission_substation * (transmission_existing_capacity + transmission_expansion) + 
        use_hv_line * hv_line_capacity,
        "GridCapacityLimit"
    )

    # Ensure grid load doesn't exceed capacity limit
    model.addConstr(max_grid_load <= cap_limit, "GridLoadLimitUpperBound")

    # === 6.5: Capacity-Based Costs ===
    # Calculate capacity-based costs (separate from connection costs)
    capacity_cost = (use_hv_line * hv_capacity_fee * max_grid_load + 
                    (use_distribution_substation + use_transmission_substation + use_existing_mv_line) * 
                    mv_capacity_fee * max_grid_load)

    # === 6.6: Cost Component Constraints ===
    model.addConstr(connection_cost_value == total_connection_cost, "ConnectionCostCapture")
    model.addConstr(capacity_cost_value == capacity_cost, "CapacityCostCapture")

    # Modify battery cost calculation
    # 1. Link battery usage to config parameter
    model.addConstr(use_battery <= include_battery, "BatteryEnabled")

    # 2. Force battery capacity to zero when battery is disabled
    model.addConstr(battery_capacity <= battery_capacity_max * use_battery, "BatteryCapacityToggle")

    # 3. Track peak battery power (max of charge or discharge across all time periods)
    for t in range(time_periods):
        model.addConstr(battery_peak_power >= battery_charge[t], f"PeakPowerCharge_{t}")
        model.addConstr(battery_peak_power >= battery_discharge[t], f"PeakPowerDischarge_{t}")

    # 4. Calculate battery component costs
    model.addConstr(battery_capacity_cost == battery_capacity * battery_cost_per_kwh, "BatteryCapacityCostCalc")
    model.addConstr(battery_power_cost == battery_peak_power * battery_cost_per_kw, "BatteryPowerCostCalc")

    # 5. Calculate total battery cost
    model.addConstr(battery_cost_value == battery_capacity_cost + battery_power_cost, "BatteryCostCapture")

    # 6. Calculate charger costs
    total_charger_cost = MCS_count * MCS_cost + HPC_count * HPC_cost + NCS_count * NCS_cost
    model.addConstr(charger_cost_value == total_charger_cost, "ChargerCostCapture")

    # 7. Calculate internal cable costs and include in charging hub cost
    internal_cable_cost = get_internal_cable_cost(MCS_count, HPC_count, NCS_count)
    model.addConstr(internal_cable_cost_value == internal_cable_cost, "InternalCableCostCapture")

    # Charging hub cost to include both internal cabling and charger costs
    model.addConstr(charginghub_cost_value == internal_cable_cost + charger_cost_value, "ChargingHubCostCapture")

    # === 6.7: Substation Expansion Constraints ===
    # Link expansion variables to binary indicators
    # If expansion > 0, then expand_X must be 1
    model.addConstr(distribution_expansion <= distribution_max_expansion * expand_distribution, "DistributionExpansionLink")
    model.addConstr(transmission_expansion <= transmission_max_expansion * expand_transmission, "TransmissionExpansionLink")

    # Force binary to 0 when expansion is 0
    model.addConstr(
        expand_distribution <= distribution_expansion / 0.001,
        "ExpansionToBinaryLink"
    )

    # Only allow expansion if the corresponding substation is selected
    model.addConstr(expand_distribution <= use_distribution_substation, "OnlyExpandSelectedDistribution")
    model.addConstr(expand_transmission <= use_transmission_substation, "OnlyExpandSelectedTransmission")

    # Calculate expansion cost
    model.addConstr(
        expansion_cost_value == 
        expand_distribution * distribution_expansion_fixed_cost + 
        expand_transmission * transmission_expansion_fixed_cost,
        "ExpansionCostCalc"
    )

    # Force expansion binary to 1 only when grid load exceeds base capacity for distribution
    model.addConstr(
        max_grid_load - distribution_existing_capacity * use_distribution_substation <= 
        distribution_max_expansion * expand_distribution + M_value * (1 - use_distribution_substation),
        "DistributionExpansionNecessity"
    )

    # Force expansion binary to 1 only when grid load exceeds base capacity for transmission
    model.addConstr(
        max_grid_load - transmission_existing_capacity * use_transmission_substation <= 
        transmission_max_expansion * expand_transmission + M_value * (1 - use_transmission_substation),
        "TransmissionExpansionNecessity"
    )

    # Ensure expansion amount exactly matches the needed capacity when expansion is needed
    model.addConstr(
        distribution_expansion >= max_grid_load - distribution_existing_capacity - 
        M_value * (1 - use_distribution_substation) - M_value * (1 - expand_distribution),
        "DistributionExpansionSizing"
    )

    model.addConstr(
        transmission_expansion >= max_grid_load - transmission_existing_capacity - 
        M_value * (1 - use_transmission_substation) - M_value * (1 - expand_transmission),
        "TransmissionExpansionSizing"
    )

    # === 6.8: Transformer Selection Constraints ===
    # Ensure at least one transformer is selected
    model.addConstr(transformer_count.sum() >= 1, "AtLeastOneTransformer")

    # Ensure the sum of selected transformer capacities can handle the maximum grid load
    model.addConstr(
        sum(transformer_capacities[i] * transformer_count[i] for i in range(len(transformer_capacities))) >= max_grid_load, 
        "TransformerCapacityCheck"
    )

    # Calculate transformer cost based on selected transformer options
    model.addConstr(
        transformer_cost_value == sum(transformer_costs[i] * transformer_count[i] for i in range(len(transformer_capacities))), 
        "TransformerCostCapture"
    )

    # === 6.9: Energy Balance and Battery Constraints ===
    # Refine M_value based on the load profile
    M_value = max(M_value, max(load_profile) * 10) if load_profile is not None else M_value

    # Time-dependent constraints
    for t in range(time_periods):
        # Energy balance constraints
        model.addConstr(
            grid_energy[t] + battery_discharge[t] == load_profile[t] + battery_charge[t], # type: ignore
            f"EnergyBalance_{t}"
        )
        
        # Grid capacity constraints
        model.addConstr(grid_energy[t] <= max_grid_load, f"GridSupplyLimit_{t}")
        
        # Battery SOC constraints
        if t == 0:
            model.addConstr(
                battery_soc[t] == battery_charge[t] - 
                battery_discharge[t] / battery_efficiency,
                f"BatterySOC_{t}"
            )
        else:
            model.addConstr(
                battery_soc[t] == battery_soc[t-1] + 
                (battery_charge[t] - 
                battery_discharge[t] / battery_efficiency),
                f"BatterySOC_{t}"
            )
        model.addConstr(battery_soc[t] <= battery_capacity, f"BatterySOC_Limit_{t}")

        # Prevent simultaneous charging and discharging
        model.addConstr(is_charging[t] + is_discharging[t] <= 1, f"NoSimultaneousChargeDischarge_{t}")
        
        # Link binary variables to charging/discharging actions
        model.addConstr(battery_charge[t] <= M_value * is_charging[t], f"ChargeLink_{t}")
        model.addConstr(battery_discharge[t] <= M_value * is_discharging[t], f"DischargeLink_{t}")
        
        # Force battery charge/discharge to zero when battery is disabled
        model.addConstr(battery_charge[t] <= M_value * use_battery, f"ChargeToggle_{t}")
        model.addConstr(battery_discharge[t] <= M_value * use_battery, f"DischargeToggle_{t}")

    #------------------------------------------------------------------------------
    # SECTION 7: OBJECTIVE FUNCTION
    #------------------------------------------------------------------------------
    model.setObjective(
        connection_cost_value +    # Grid connection CAPEX
        capacity_cost_value +      # Grid capacity fees
        battery_cost_value +       # Battery cost
        transformer_cost_value +   # Transformer cost
        expansion_cost_value +     # Substation expansion costs
        charginghub_cost_value,    # Charging hub cost (now includes internal cabling and charger costs)
        GRB.MINIMIZE
    )

    #------------------------------------------------------------------------------
    # SECTION 8: OPTIMIZATION AND RESULTS
    #------------------------------------------------------------------------------
    # Optimize and store results
    model.optimize()

    # Process results
    if model.status == GRB.OPTIMAL:
        # Find selected cable sizes based on power requirements
        transmission_selected_size = calculate_mv_cable(max_grid_load.X, transmission_substation_distance)
        distribution_selected_size = calculate_mv_cable(max_grid_load.X, distribution_substation_distance)
        hv_selected_size = calculate_mv_cable(max_grid_load.X, hvline_distance)
        
        # Calculate power capacities of the selected cables
        transmission_capacity = calculate_max_power_current_capacity(transmission_selected_size)
        distribution_capacity = calculate_max_power_current_capacity(distribution_selected_size)
        hv_capacity = calculate_max_power_current_capacity(hv_selected_size)
        
        # Use aluminium_kabel["Nennquerschnitt"] instead of standard_cable_sizes
        cable_sizes = aluminium_kabel["Nennquerschnitt"]
        
        # Identify which transformers were selected and their counts
        transformer_selections = {i: int(transformer_count[i].X) 
                                for i in range(len(transformer_capacities)) 
                                if transformer_count[i].X > 0.5}
        
        # Calculate total transformer capacity
        total_transformer_capacity = int(sum(transformer_capacities[i] * count for i, count in transformer_selections.items()))
        total_transformer_cost = float(sum(transformer_costs[i] * count for i, count in transformer_selections.items()))
        
        # Create a readable description of transformer selections
        transformer_description = ", ".join([f"{count}x {int(transformer_capacities[i])} kW" 
                                            for i, count in transformer_selections.items()])
        
        results = {
            'total_cost': float(model.objVal),
            'max_grid_load': float(max_grid_load.X),
            'battery_capacity': float(battery_capacity.X),
            'use_hv': float(use_hv_line.X),
            'use_transmission': float(use_transmission_substation.X),
            'use_distribution': float(use_distribution_substation.X),
            'use_existing_mv': float(use_existing_mv_line.X),
            'charging_strategy': strategy,
            'distribution_expansion': float(distribution_expansion.X),
            'transmission_expansion': float(transmission_expansion.X),
            'expand_distribution': float(expand_distribution.X),
            'expand_transmission': float(expand_transmission.X),
            'expansion_cost': float(expansion_cost_value.X),
            'grid_energy': [float(grid_energy[t].X) for t in range(time_periods)],
            'battery_soc': [float(battery_soc[t].X) for t in range(time_periods)],
            'battery_charge': [float(battery_charge[t].X) for t in range(time_periods)],
            'battery_discharge': [float(battery_discharge[t].X) for t in range(time_periods)],
            'connection_cost': float(connection_cost_value.X),
            'capacity_cost': float(capacity_cost_value.X),
            'battery_cost': float(battery_cost_value.X),
            'transformer_cost': float(transformer_cost_value.X),
            'capacity_limit': float(cap_limit.X),
            'distribution_distance': float(distribution_substation_distance),
            'transmission_distance': float(transmission_substation_distance),
            'powerline_distance': float(hvline_distance),
            'transmission_selected_size': float(transmission_selected_size),
            'distribution_selected_size': float(distribution_selected_size),
            'hv_selected_size': float(hv_selected_size),
            'transmission_capacity': float(transmission_capacity),
            'distribution_capacity': float(distribution_capacity),
            'hv_capacity': float(hv_capacity),
            'transformer_capacity': total_transformer_capacity,
            'transformer_cost': total_transformer_cost,
            'transformer_selections': transformer_selections,
            'transformer_description': transformer_description,
            'internal_cable_cost': float(internal_cable_cost_value.X),
            'charger_cost': float(charger_cost_value.X),
            'total_charginghub_cost': float(charginghub_cost_value.X),
            'MCS_count': int(MCS_count),
            'HPC_count': int(HPC_count),
            'NCS_count': int(NCS_count)
        }
        
        # Add charging sessions data
        results = add_charging_sessions_data(results, strategy)

        # Generate standardized filename base
        result_filename_base = generate_result_filename(
            results, 
            strategy,
            include_battery,
            custom_id=Config.RESULT_NAMING['CUSTOM_ID'] if Config.RESULT_NAMING.get('USE_CUSTOM_ID', False) else None
        )
        
        # Save results using the new naming convention
        save_optimization_results(results, result_filename_base, timestamps, load_profile)
        
        # Print organized summary - only call this once
        print_optimization_summary(results, distances)
        
        # Add any additional specific metrics you want to show
        print("\n=== Additional Metrics ===")
        print(f"Max Load: {max(load_profile)}") # type: ignore
        print(f"Max Grid Load: {max_grid_load.X}")
        print(f"Capacity Limit: {cap_limit.X}")
        print(f"Selected Transformer: {total_transformer_capacity} kW (Cost: €{total_transformer_cost:.2f})")
        
        # Add additional metrics for expansions
        print("\n=== Substation Expansion Details ===")
        if results['use_distribution'] > 0.5:
            print(f"Distribution Substation: {distribution_existing_capacity} kW base capacity")
            if results['expand_distribution'] > 0.5:
                print(f"  Expanded by: {results['distribution_expansion']:.2f} kW")
                print(f"  Expansion cost: €{distribution_expansion_fixed_cost:,.2f}")
            else:
                print("  No expansion required")
                
        if results['use_transmission'] > 0.5:
            print(f"Transmission Substation: {transmission_existing_capacity} kW base capacity")
            if results['expand_transmission'] > 0.5:
                print(f"  Expanded by: {results['transmission_expansion']:.2f} kW")
                print(f"  Expansion cost: €{transmission_expansion_fixed_cost:,.2f}")
            else:
                print("  No expansion required")
            
        # Add internal cabling info to the output
        print("\n=== Internal Cabling Details ===")
        print(f"Total Internal Cabling Cost: €{results['internal_cable_cost']:,.2f}")
        
        # Add charger cost details to the output
        print("\n=== Charger Cost Details ===")
        print(f"MCS Chargers: {MCS_count} x €{MCS_cost:,.2f} = €{MCS_count * MCS_cost:,.2f}")
        print(f"HPC Chargers: {HPC_count} x €{HPC_cost:,.2f} = €{HPC_count * HPC_cost:,.2f}")
        print(f"NCS Chargers: {NCS_count} x €{NCS_cost:,.2f} = €{NCS_count * NCS_cost:,.2f}")
        print(f"Total Charger Cost: €{MCS_count * MCS_cost + HPC_count * HPC_cost + NCS_count * NCS_cost:,.2f}")
            
        # Update transformer details output
        print("\n=== Transformer Details ===")
        print(f"Selected transformers: {transformer_description}")
        print(f"Total transformer capacity: {total_transformer_capacity} kW")
        print(f"Total transformer cost: €{total_transformer_cost:,.2f}")
        
        # Add traffic data summary
        print("\n=== Daily Charging Sessions ===")
        for day, sessions in results['daily_charging_sessions'].items():
            print(f"{day}: MCS: {sessions['MCS']}, HPC: {sessions['HPC']}, NCS: {sessions['NCS']}")

        print("\n=== Weekly Charging Totals ===")
        print(f"MCS: {results['weekly_charging_totals']['MCS']} sessions/week")
        print(f"HPC: {results['weekly_charging_totals']['HPC']} sessions/week")
        print(f"NCS: {results['weekly_charging_totals']['NCS']} sessions/week")

        print("\n=== Charger Utilization ===")
        print(f"MCS: {results['charger_utilization']['MCS']:.2f} sessions/charger/day")
        print(f"HPC: {results['charger_utilization']['HPC']:.2f} sessions/charger/day")
        print(f"NCS: {results['charger_utilization']['NCS']:.2f} sessions/charger/day")
            
    # Check for custom ID from environment
    env_custom_id = os.environ.get('CHARGING_HUB_CUSTOM_ID')
    if env_custom_id:
        print(f"DEBUG: Found custom ID in environment: {env_custom_id}")
    else:
        print("DEBUG: No custom ID found in environment")
        
    # Generate filename again to ensure consistency 
    result_filename_base = generate_result_filename(
        results, 
        strategy, 
        include_battery,
        custom_id=env_custom_id  # Use the environment variable instead of None
    )
    plot_optimization_results(results, timestamps, load_profile, create_plot, result_filename_base)
    
    return results


def process_strategy(strategy):
    """Process a single strategy in a separate process"""
    try:
        return run_optimization_for_strategy(strategy)
    except Exception as e:
        print(f"Error processing strategy {strategy}: {str(e)}")
        return {'charging_strategy': strategy, 'error': str(e)}


def main():
    """Main function to run the optimization for all strategies"""
    start_time = time.time()
    print(f"Starting optimization for {len(Config.CHARGING_CONFIG['ALL_STRATEGIES'])} strategies")

    # Option 1: Sequential execution
    # all_results = []
    # for strategy in Config.CHARGING_CONFIG['ALL_STRATEGIES']:
    #    result = process_strategy(strategy)
    #    all_results.append(result)

    # Option 2: Parallel execution with ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=min(len(Config.CHARGING_CONFIG['ALL_STRATEGIES']), os.cpu_count() or 1)) as executor:
        # Submit all strategies for processing
        futures = {executor.submit(process_strategy, strategy): strategy 
                   for strategy in Config.CHARGING_CONFIG['ALL_STRATEGIES']}
        
        # Collect results as they complete
        all_results = []
        for future in futures:
            strategy = futures[future]
            try:
                result = future.result()
                all_results.append(result)
                print(f"Completed optimization for strategy: {strategy}")
            except Exception as e:
                print(f"Error in strategy {strategy}: {e}")
                all_results.append({'charging_strategy': strategy, 'error': str(e)})

    # Summarize all results
    print("\n\n" + "="*80)
    print("OPTIMIZATION COMPLETE - SUMMARY OF RESULTS")
    print("="*80)
    
    # Create comparison table of key metrics
    print(f"{'Strategy':<10} | {'Total Cost':<15} | {'Grid Load':<12} | {'Battery':<10} | {'Connection'}")
    print("-" * 80)
    
    for result in all_results:
        if 'error' in result:
            print(f"{result['charging_strategy']:<10} | {'ERROR':<15} | {'N/A':<12} | {'N/A':<10} | {'N/A'}")
        else:
            connection_type = "HV Line" if result.get('use_hv', 0) > 0.5 else \
                            "Transmission" if result.get('use_transmission', 0) > 0.5 else \
                            "Distribution" if result.get('use_distribution', 0) > 0.5 else "Existing MV"
            
            print(f"{result['charging_strategy']:<10} | €{result['total_cost']:,.2f} | {result['max_grid_load']:.2f} kW | {result['battery_capacity']:.2f} kWh | {connection_type}")

    # Print execution time
    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")


def generate_result_filename(results, strategy, include_battery=True, custom_id=None):
    return grid_generate_result_filename(results, strategy, include_battery, custom_id)


def add_charging_sessions_data(results, strategy):
    """
    Add charging sessions data per day per charger type to the results dictionary.
    
    Args:
        results (dict): The results dictionary to update
        strategy (str): The charging strategy used
        
    Returns:
        dict: The updated results dictionary with charging sessions data
    """
    try:
        # Define paths to relevant JSON files
        project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        traffic_data_path = project_root / "data" / "traffic" / "final_traffic" / "laden_mauttabelle.json"
        
        # Initialize daily sessions data structure with German day names
        daily_sessions = {
            "Montag": {"MCS": 0, "HPC": 0, "NCS": 0},
            "Dienstag": {"MCS": 0, "HPC": 0, "NCS": 0},
            "Mittwoch": {"MCS": 0, "HPC": 0, "NCS": 0},
            "Donnerstag": {"MCS": 0, "HPC": 0, "NCS": 0},
            "Freitag": {"MCS": 0, "HPC": 0, "NCS": 0},
            "Samstag": {"MCS": 0, "HPC": 0, "NCS": 0},
            "Sonntag": {"MCS": 0, "HPC": 0, "NCS": 0}
        }
        
        # Define reverse mapping from English to German day names
        english_to_german = {value: key for key, value in Config.DAY_MAPPING.items()}
        
        if traffic_data_path.exists():
            with open(traffic_data_path, 'r') as f:
                traffic_data = json.load(f)
            
            # Extract daily distribution data if available
            if "data" in traffic_data and "daily_distribution" in traffic_data["data"]:
                forecast_year = traffic_data.get("metadata", {}).get("forecast_year", "2030")
                
                for day_data in traffic_data["data"]["daily_distribution"]:
                    day = day_data["day"]
                    # Convert English day name to German
                    german_day = english_to_german.get(day, day)
                    
                    # Map charger types to forecast year columns
                    hpc_key = f"HPC_{forecast_year}"
                    ncs_key = f"NCS_{forecast_year}"
                    
                    # Get values or default to 0
                    hpc_value = day_data.get(hpc_key, 0)
                    ncs_value = day_data.get(ncs_key, 0)
                    
                    # Calculate MCS value based on ratio (approx 1:5 of HPC)
                    mcs_value = day_data.get(f"MCS_{forecast_year}", round(hpc_value * 0.2))
                    
                    daily_sessions[german_day] = {
                        "MCS": round(mcs_value),
                        "HPC": round(hpc_value),
                        "NCS": round(ncs_value)
                    }
        
        # Add to results dictionary
        results['daily_charging_sessions'] = daily_sessions
        
        # Calculate weekly totals
        weekly_totals = {
            "MCS": sum(day["MCS"] for day in daily_sessions.values()),
            "HPC": sum(day["HPC"] for day in daily_sessions.values()),
            "NCS": sum(day["NCS"] for day in daily_sessions.values())
        }
        results['weekly_charging_totals'] = weekly_totals
        
        # Calculate charger utilization metrics
        results['charger_utilization'] = {
            "MCS": weekly_totals["MCS"] / (results['MCS_count'] * 7) if results['MCS_count'] > 0 else 0,
            "HPC": weekly_totals["HPC"] / (results['HPC_count'] * 7) if results['HPC_count'] > 0 else 0,
            "NCS": weekly_totals["NCS"] / (results['NCS_count'] * 7) if results['NCS_count'] > 0 else 0
        }
        
        return results
    except Exception as e:
        print(f"Warning: Could not add charging sessions data: {e}")
        return results


if __name__ == "__main__":
    main()