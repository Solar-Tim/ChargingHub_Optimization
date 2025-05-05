############## Input Parameters for the Optimization ##############
from math import inf
import numpy as np
import sys
import os
# Change the relative import to absolute import
from grid_optimization.data_loading import load_data
# Add the project root to path to import from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import Config

# Export location configuration
DEFAULT_LOCATION = Config.DEFAULT_LOCATION

# Define charging strategy
# STRATEGY = 'T_min'  # T_min: Minimierung der Ladezeit - Kein Lademanagement
# STRATEGY = 'Konstant'  # Konstant: Möglichst konstante Ladeleistung - Minimierung der Netzanschlusslast - Lademanagement
# STRATEGY = 'Hub'  # Hub: Minimierung der Hub-Lastspitzen - Globale Lastoptimierung - Hub-Level Lademanagement
current_strategy = Config.CHARGING_CONFIG['STRATEGY'][0]
all_strategies = Config.CHARGING_CONFIG['ALL_STRATEGIES']

# Load data - Make this conditional to avoid errors when importing as a module
try:
    load_profile, timestamps = load_data(current_strategy)
except Exception as e:
    print(f"Note: Could not load data profiles in config_grid.py module import: {e}")
    load_profile, timestamps = [], []

# Access grid optimization flags from EXECUTION_FLAGS dictionary
debug_mode = Config.EXECUTION_FLAGS['DEBUG_MODE']  # Set to True to enable debug mode for detailed output
use_distance_calculation = Config.EXECUTION_FLAGS['USE_DISTANCE_CALCULATION']  # Set to True to use distance calculation for optimization
create_plot = Config.EXECUTION_FLAGS['CREATE_PLOT']  # Set to True to generate plot of optimization results
create_distance_maps = Config.EXECUTION_FLAGS['CREATE_DISTANCE_MAPS']  # Set to True to generate maps of distance calculations
include_battery = Config.EXECUTION_FLAGS['INCLUDE_BATTERY']  # Set to True to include battery in optimization
use_manual_charger_count = Config.EXECUTION_FLAGS['USE_MANUAL_CHARGER_COUNT']  # Set to True to use manual charger count instead of optimization

# Add these variables from Config.RESULT_NAMING
use_custom_result_id = Config.RESULT_NAMING.get('USE_CUSTOM_ID', False)
custom_result_id = Config.RESULT_NAMING.get('CUSTOM_ID', None)

# Centralized function for generating result filenames - use this throughout grid optimization scripts
def generate_result_filename(results=None, strategy=None, battery_allowed=None, custom_id=None):
    """
    Centralized function for generating result filenames.
    This acts as an intermediary that calls Config.generate_result_filename
    with the correct parameters.
    
    Args:
        results: Dictionary containing optimization results (optional)
        strategy: Strategy name (optional)
        battery_allowed: Boolean indicating if battery was allowed (optional)
        custom_id: User-defined unique identifier (optional)
        
    Returns:
        String: Filename in format {id}_{strategy}_{battery_status}
    """
    # First check if we received a custom ID via environment variable
    env_custom_id = os.environ.get('CHARGING_HUB_CUSTOM_ID')
    if env_custom_id:
        print(f"DEBUG: Using custom ID from environment: {env_custom_id}")
        custom_id = env_custom_id
    
    # If custom_id is still not provided, use the one from Config.RESULT_NAMING
    if custom_id is None and Config.RESULT_NAMING.get('USE_CUSTOM_ID', False):
        custom_id = Config.RESULT_NAMING.get('CUSTOM_ID', None)
        print(f"DEBUG: Using custom ID from Config: {custom_id}")
    
    # Call the centralized function in Config
    return Config.generate_result_filename(results, strategy, battery_allowed, custom_id)

M_value = 1000000  # Big M value for the optimization

existing_mv_connection_cost = 0  # Cost of existing MV connection (EUR) - Hier ist nur die Rede von Kabelkosten, nicht von dem Baukostenzuschuss

# Manual distance values when not using distance calculation
manual_distances = Config.MANUAL_DISTANCES  # Load manual distances from config


# Placeholder for the number of chargers - Wird bei der Optimierung automatisch ermittelt
# Load charger counts from Config instead of hardcoded values
MCS_count = Config.MANUAL_CHARGER_COUNT['MCS']   # Load MCS count from config
HPC_count = Config.MANUAL_CHARGER_COUNT['HPC']   # Load HPC count from config
NCS_count = Config.MANUAL_CHARGER_COUNT['NCS']   # Load NCS count from config



# Charger fixed costs (EUR) - Akutell Werte aus Felix MA - Problematisch weil die Charger oft die Gleichrichter mit beinhalten und sie aktuell doppelt bezahlt werden
MCS_cost = Config.CHARGING_TYPES['MCS']['cost']  # Cost per MCS charger
HPC_cost = Config.CHARGING_TYPES['HPC']['cost']  # Cost per HPC charger
NCS_cost = Config.CHARGING_TYPES['NCS']['cost']  # Cost per NCS charger

# Internal LV cabling parameters
charger_distance_increment = 4  # Distance increment between charger positions (m)
mcs_power_kw = Config.CHARGING_TYPES['MCS']['power_kw']  # Power rating of MCS chargers (kW)
hpc_power_kw = Config.CHARGING_TYPES['HPC']['power_kw']  # Power rating of HPC chargers (kW)
ncs_power_kw = Config.CHARGING_TYPES['NCS']['power_kw']  # Power rating of NCS chargers (kW)

# Battery parameters
battery_cost_per_kwh = Config.BATTERY_CONFIG['COST_PER_KWH']  # Cost per kWh of battery storage (EUR/kWh)
battery_cost_per_kw = Config.BATTERY_CONFIG['COST_PER_KW']  # Cost per kW of battery storage (EUR/kW)
battery_capacity_max = Config.BATTERY_CONFIG['MAX_CAPACITY']  # Maximum battery capacity (kWh)
battery_charge_rate_max = Config.BATTERY_CONFIG['MAX_POWER']  # Maximum charge/discharge rate (kW)
battery_efficiency = Config.BATTERY_CONFIG['EFFICIENCY']  # Round-trip efficiency of battery storage
battery_min_soc = Config.BATTERY_CONFIG['MIN_SOC']  # Minimum state of charge (SOC) of battery storage
battery_max_soc = Config.BATTERY_CONFIG['MAX_SOC']  # Maximum state of charge (SOC) of battery storage


# Define capacity fee parameters (€/kW) - Load from central Config
hv_capacity_fee = Config.CAPACITY_FEES['HV']  # Load HV capacity fee from config
mv_capacity_fee = Config.CAPACITY_FEES['MV']  # Load MV capacity fee from config

# Line capacities (in kW) - in Anlehnung an https://www.regionetz.de/fileadmin/regionetz/content/Dokumente/TAB/TAB_MS_2023_Regionetz.pdf
existing_mv_capacity = Config.GRID_CAPACITIES['EXISTING_MV']  # Capacity for existing MV line
distribution_substation_capacity = Config.GRID_CAPACITIES['DISTRIBUTION']  # Capacity for distribution substation
transmission_substation_capacity = Config.GRID_CAPACITIES['TRANSMISSION']  # Capacity for transmission substation
hv_line_capacity = Config.GRID_CAPACITIES['HV_LINE']  # Capacity for HV line and a new substation

# Substation expansion parameters - Load from central Config
distribution_existing_capacity = Config.SUBSTATION_CONFIG['DISTRIBUTION']['EXISTING_CAPACITY']  # Initial available capacity (kW)
distribution_max_expansion = Config.SUBSTATION_CONFIG['DISTRIBUTION']['MAX_EXPANSION']      # Maximum additional expansion (kW)
transmission_existing_capacity = Config.SUBSTATION_CONFIG['TRANSMISSION']['EXISTING_CAPACITY'] # Initial available capacity (kW)
transmission_max_expansion = Config.SUBSTATION_CONFIG['TRANSMISSION']['MAX_EXPANSION']     # Maximum additional expansion (kW)
distribution_expansion_fixed_cost = Config.SUBSTATION_CONFIG['DISTRIBUTION']['EXPANSION_FIXED_COST']  # Fixed cost for expanding distribution substation (EUR)
transmission_expansion_fixed_cost = Config.SUBSTATION_CONFIG['TRANSMISSION']['EXPANSION_FIXED_COST'] # Fixed cost for expanding transmission substation (EUR)

# HV Substation Cost estimate - Load from central Config
HV_Substation_cost = Config.SUBSTATION_CONFIG['HV_SUBSTATION_COST'] # Cost of a new HV substation ~2.5M EUR

# === Define discrete transformer options from central Config ===
# Load transformer options from central configuration
transformers = {
    "Kapazität": Config.TRANSFORMER_CONFIG["CAPACITIES"],  # Load capacities from config
    "Kosten": Config.TRANSFORMER_CONFIG["COSTS"]  # Load costs from config
}

# For compatibility with existing code:
transformer_capacities = np.array(transformers["Kapazität"])
transformer_costs = np.array(transformers["Kosten"])

# Time parameters - Load from central Config
time_resolution = Config.TIME['RESOLUTION_MINUTES']  # Time resolution in minutes
simulation_period = Config.TIME['SIMULATION_HOURS']  # Hours in a year

################################ Others ################################

# Low voltage cable parameters - Load from central Config
lv_voltage = Config.CABLE_CONFIG['LV']['VOLTAGE']  # V
lv_voltage_drop_percent = Config.CABLE_CONFIG['LV']['VOLTAGE_DROP_PERCENT']
lv_power_factor = Config.CABLE_CONFIG['LV']['POWER_FACTOR']
lv_conductivity = Config.CABLE_CONFIG['LV']['CONDUCTIVITY']  # Copper
number_dc_cables = Config.CABLE_CONFIG['LV']['NUM_DC_CABLES']  # Number of cables for DC connections

# Medium voltage cable parameters - Load from central Config
mv_voltage = Config.CABLE_CONFIG['MV']['VOLTAGE']  # V
mv_voltage_drop_percent = Config.CABLE_CONFIG['MV']['VOLTAGE_DROP_PERCENT']
mv_power_factor = Config.CABLE_CONFIG['MV']['POWER_FACTOR']
mv_conductivity = Config.CABLE_CONFIG['MV']['CONDUCTIVITY']  # Aluminium

# MV-Cable Construction Cost - Load from central Config
digging_cost = Config.CABLE_CONFIG['CONSTRUCTION']['DIGGING_COST']  # Cost of digging per meter (EUR/m)
cable_hardware_connection_cost = Config.CABLE_CONFIG['CONSTRUCTION']['HARDWARE_CONNECTION_COST']  # Cable mounting costs (EUR)
number_cables = Config.CABLE_CONFIG['MV']['NUM_CABLES']  # Number of cables in parallel (for MV)

# Cable Cost
aluminium_kabel = Config.aluminium_kabel
kupfer_kabel = Config.kupfer_kabel
