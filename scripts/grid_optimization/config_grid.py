############## Input Parameters for the Optimization ##############
import sys
import os
import numpy as np
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import from the root config
from config import Config

# Map grid settings to variables for backward compatibility
aluminium_kabel = Config.GridSettings.ALUMINIUM_KABEL
kupfer_kabel = Config.GridSettings.KUPFER_KABEL
mv_capacity_fee = Config.GridSettings.MV_CAPACITY_FEE
hv_capacity_fee = Config.GridSettings.HV_CAPACITY_FEE
existing_mv_capacity = Config.GridSettings.CONNECTION_CAPACITIES['EXISTING_MV']
existing_mv_connection_cost = Config.GridSettings.EXISTING_MV_CONNECTION_COST
manual_distances = Config.GridSettings.MANUAL_DISTANCES

# Load charging strategy from central config
current_strategy = Config.GridSettings.CHARGING_STRATEGY

# Load control flags
debug_mode = Config.GridSettings.DEBUG_MODE
use_distance_calculation = Config.GridSettings.USE_DISTANCE_CALCULATION
create_plot = Config.GridSettings.CREATE_PLOT
create_distance_maps = Config.GridSettings.CREATE_DISTANCE_MAPS
include_battery = Config.GridSettings.INCLUDE_BATTERY
use_manual_charger_count = Config.GridSettings.USE_MANUAL_CHARGER_COUNT

# Load optimization parameters
M_value = Config.GridSettings.M_VALUE

# Load charger counts
MCS_count = Config.ChargingInfrastructure.CHARGER_COUNTS['MCS']
HPC_count = Config.ChargingInfrastructure.CHARGER_COUNTS['HPC']
NCS_count = Config.ChargingInfrastructure.CHARGER_COUNTS['NCS']

# Load charger costs
MCS_cost = Config.ChargingInfrastructure.STATION_TYPES['MCS']['cost']
HPC_cost = Config.ChargingInfrastructure.STATION_TYPES['HPC']['cost']
NCS_cost = Config.ChargingInfrastructure.STATION_TYPES['NCS']['cost']

# Load battery parameters
battery_cost_per_kwh = Config.GridSettings.BATTERY_CONFIG['COST_PER_KWH']
battery_cost_per_kw = Config.GridSettings.BATTERY_CONFIG['COST_PER_KW']
battery_capacity_max = Config.GridSettings.BATTERY_CONFIG['MAX_CAPACITY']
battery_charge_rate_max = Config.GridSettings.BATTERY_CONFIG['MAX_POWER']
battery_efficiency = Config.GridSettings.BATTERY_CONFIG['EFFICIENCY']
battery_min_soc = Config.GridSettings.BATTERY_CONFIG['MIN_SOC']
battery_max_soc = Config.GridSettings.BATTERY_CONFIG['MAX_SOC']

# Load line capacities
distribution_substation_capacity = Config.GridSettings.CONNECTION_CAPACITIES['DISTRIBUTION']
transmission_substation_capacity = Config.GridSettings.CONNECTION_CAPACITIES['TRANSMISSION']
hv_line_capacity = Config.GridSettings.CONNECTION_CAPACITIES['HV_LINE']

# Load substation parameters
distribution_existing_capacity = Config.GridSettings.SUBSTATION_PARAMETERS['distribution_existing_capacity']
distribution_max_expansion = Config.GridSettings.SUBSTATION_PARAMETERS['distribution_max_expansion']
transmission_existing_capacity = Config.GridSettings.SUBSTATION_PARAMETERS['transmission_existing_capacity']
transmission_max_expansion = Config.GridSettings.SUBSTATION_PARAMETERS['transmission_max_expansion']
distribution_expansion_fixed_cost = Config.GridSettings.SUBSTATION_PARAMETERS['distribution_expansion_fixed_cost']
transmission_expansion_fixed_cost = Config.GridSettings.SUBSTATION_PARAMETERS['transmission_expansion_fixed_cost']
HV_Substation_cost = Config.GridSettings.SUBSTATION_PARAMETERS['HV_Substation_cost']

# Load transformer base costs
basecost_transformer = Config.GridSettings.TRANSFORMER_BASE_COSTS['basecost_transformer']
cost_transformer_perkW = Config.GridSettings.TRANSFORMER_BASE_COSTS['cost_transformer_perkW']

# Load transformer options
transformers = Config.GridSettings.TRANSFORMERS
transformer_capacities = np.array(transformers["Kapazität"])
transformer_costs = np.array(transformers["Kosten"])

# Load time parameters
time_resolution = Config.GridSettings.TIME_PARAMETERS['TIME_RESOLUTION']
simulation_period = Config.GridSettings.TIME_PARAMETERS['SIMULATION_PERIOD']

# Load LV cable parameters
lv_voltage = Config.GridSettings.LV_CABLE_PARAMETERS['voltage']
lv_voltage_drop_percent = Config.GridSettings.LV_CABLE_PARAMETERS['voltage_drop_percent']
lv_power_factor = Config.GridSettings.LV_CABLE_PARAMETERS['power_factor']
lv_conductivity = Config.GridSettings.LV_CABLE_PARAMETERS['conductivity']

# Load MV cable parameters
mv_voltage = Config.GridSettings.MV_CABLE_PARAMETERS['voltage']
mv_voltage_drop_percent = Config.GridSettings.MV_CABLE_PARAMETERS['voltage_drop_percent']
mv_power_factor = Config.GridSettings.MV_CABLE_PARAMETERS['power_factor']
mv_conductivity = Config.GridSettings.MV_CABLE_PARAMETERS['conductivity']

# Load MV-Cable Construction Cost
digging_cost = Config.GridSettings.CABLE_CONSTRUCTION_COST['digging_cost']
cable_hardware_connection_cost = Config.GridSettings.CABLE_CONSTRUCTION_COST['cable_hardware_connection_cost']
number_cables = Config.GridSettings.CABLE_CONSTRUCTION_COST['number_cables']

# Load cable data
kupfer_kabel = Config.GridSettings.KUPFER_KABEL

# Load internal LV cabling parameters
charger_distance_increment = Config.GridSettings.INTERNAL_CABLING['charger_distance_increment']
mcs_power_kw = Config.GridSettings.INTERNAL_CABLING['mcs_power_kw']
hpc_power_kw = Config.GridSettings.INTERNAL_CABLING['hpc_power_kw']
ncs_power_kw = Config.GridSettings.INTERNAL_CABLING['ncs_power_kw']

# Load charging power ratings
leistung_ladetyp = Config.ChargingInfrastructure.POWER_RATINGS
