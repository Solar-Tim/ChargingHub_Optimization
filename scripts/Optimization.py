###############################################################################
# Charging Hub Optimization Model
# Author: Tim Sanders
# Purpose: Optimize charging hub design including grid connection, battery storage,
#          and transformer selection to minimize total capital expenditure
###############################################################################

#------------------------------------------------------------------------------
# SECTION 1: IMPORTS AND INITIALIZATION
#------------------------------------------------------------------------------
from calendar import c
from gurobipy import Model, GRB, quicksum
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pyparsing import Char
from my_functions import * # type: ignore

from config_BA import *  
from my_cables import * # type: ignore
from shapely.geometry import Point
import sys
import os
import subprocess

# Define base project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Add the path to the distance calculation module
sys.path.append(os.path.join(BASE_DIR, '01_Distance-Calc'))

from distance_functions import calculate_all_distances # type: ignore

# Clear the console for better readability
subprocess.run('cls', shell=True) # Clear the console

#------------------------------------------------------------------------------
# SECTION 2: DATA LOADING AND PREPROCESSING
#------------------------------------------------------------------------------
# Define charging hub location
ref_point = Point(6.214699333123033, 50.81648528837548)  # Example coordinates

# Toggle between calculated distances and manual distances
if use_distance_calculation:
    distances = calculate_all_distances(ref_point, create_map=False)
    print("Using calculated distances")
else:
    distances = manual_distances
    print("Using manual distances from config file")

# Load data
load_profiles, timestamps = loadData()
results = {}
print("Data loaded successfully")

# Process single load profile
print("Running optimization")

# Fix load_profile handling - convert to properly indexed structure
if isinstance(load_profiles, dict):
    # If load_profiles is a dictionary, get the first profile
    load_profile = next(iter(load_profiles.values()))
else:
    # Otherwise just use it directly
    load_profile = load_profiles

# Ensure it's a list or array for proper indexing
if hasattr(load_profile, 'tolist'):
    load_profile = load_profile.tolist()
elif not isinstance(load_profile, (list, tuple, np.ndarray)) and load_profile is not None:
    # Convert to list if it's not already a sequence type but exists
    load_profile = [load_profile]
    
# Safely get the length
time_periods = len(load_profile) if load_profile is not None else 0 # type: ignore

# Add distance parameters to model
distribution_substation_distance = distances['distribution_distance'] or float('inf')
transmission_substation_distance = distances['transmission_distance'] or float('inf')
hvline_distance = distances['powerline_distance'] or float('inf')

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
transformer_choice = model.addMVar(len(transformer_capacities), vtype=GRB.BINARY, name="TransformerChoice")

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

# Calculate charger costs
total_charger_cost = MCS_count * MCS_cost + HPC_count * HPC_cost + NCS_count * NCS_cost
model.addConstr(charger_cost_value == total_charger_cost, "ChargerCostCapture")

# Calculate internal cable costs and include in charging hub cost
internal_cable_cost = get_internal_cable_cost()
model.addConstr(internal_cable_cost_value == internal_cable_cost, "InternalCableCostCapture")

# Update charging hub cost to include both internal cabling and charger costs
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
# Ensure exactly one transformer is selected
model.addConstr(transformer_choice.sum() == 1, "TransformerSelection")

# Ensure the selected transformer can handle the maximum grid load
model.addConstr(transformer_capacities @ transformer_choice >= max_grid_load, "TransformerCapacityCheck")

# Calculate transformer cost based on selected transformer option
model.addConstr(transformer_cost_value == transformer_costs @ transformer_choice, "TransformerCostCapture")

# === 6.9: Energy Balance and Battery Constraints ===
# Calculate a reasonable Big-M value based on the load profile
M_value = max(100000, max(load_profile) * 10)  # type: ignore

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
    
    # Identify which transformer was selected
    selected_transformer_idx = [i for i in range(len(transformer_capacities)) 
                               if transformer_choice[i].X > 0.5][0]
    selected_transformer_capacity = int(transformer_capacities[selected_transformer_idx])  # Convert to Python int
    selected_transformer_cost = float(transformer_costs[selected_transformer_idx])  # Convert to Python float
    
    results = {
        'total_cost': float(model.objVal),
        'max_grid_load': float(max_grid_load.X),
        'battery_capacity': float(battery_capacity.X),
        'use_hv': float(use_hv_line.X),
        'use_transmission': float(use_transmission_substation.X),
        'use_distribution': float(use_distribution_substation.X),
        'use_existing_mv': float(use_existing_mv_line.X),
        
        # Add new result fields
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
        'transformer_capacity': selected_transformer_capacity,
        'transformer_cost': selected_transformer_cost,
        'internal_cable_cost': float(internal_cable_cost_value.X),
        'charger_cost': float(charger_cost_value.X),  # Add charger cost to results
        'total_charginghub_cost': float(charginghub_cost_value.X),  # Total charging hub cost
    }
    
    save_optimization_results(results, "single_sequence", timestamps, load_profile)
    
    # Print organized summary - only call this once
    print_optimization_summary(results, distances)
    
    # Add any additional specific metrics you want to show
    print("\n=== Additional Metrics ===")
    print(f"Max Load: {max(load_profile)}") # type: ignore
    print(f"Max Grid Load: {max_grid_load.X}")
    print(f"Capacity Limit: {cap_limit.X}")
    print(f"Selected Transformer: {selected_transformer_capacity} kW (Cost: €{selected_transformer_cost:.2f})")
    
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
        
# Plotting results - keep this outside the if statement if you want it to run even if optimization failed
plot_optimization_results(results, timestamps, load_profile, create_plot)
