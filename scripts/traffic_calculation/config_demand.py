"""
Compatibility module for traffic calculation scripts.
This module imports configuration from the global Config class.
"""

import sys
import os
# Add the project root to path to import from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import Config

# Backwards compatibility variables
year = Config.FORECAST_YEAR
neue_pausen = Config.Traffic.Settings.RECALCULATE_BREAKS
neue_toll_midpoints = Config.Traffic.Settings.RECALCULATE_TOLL_MIDPOINTS
DEFAULT_LOCATION = Config.Traffic.Settings.DEFAULT_LOCATION
BREAKS = Config.Traffic.Settings.BREAKS
DAY_MAPPING = Config.Traffic.Settings.DAY_MAPPING
GERMAN_DAYS = Config.Traffic.Settings.GERMAN_DAYS
TIME = Config.Traffic.Settings.TIME
CSV = Config.Traffic.Settings.FileFormats.CSV

# Access nested class properties correctly
SPATIAL = {
    'DEFAULT_CRS': Config.Traffic.Settings.SpatialSettings.DEFAULT_CRS,
    'TARGET_CRS': Config.Traffic.Settings.SpatialSettings.TARGET_CRS,
    'BUFFER_RADIUS': Config.Traffic.Settings.SpatialSettings.BUFFER_RADIUS
}

# Access forecast scenarios correctly
SCENARIOS = {
    'TARGET_YEARS': Config.Traffic.Settings.ForecastScenarios.TARGET_YEARS,
    'R_BEV': Config.Traffic.Settings.ForecastScenarios.R_BEV,
    'R_TRAFFIC': Config.Traffic.Settings.ForecastScenarios.R_TRAFFIC
}

# Set up file paths for backward compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
INPUT_DIR = Config.Traffic.INPUT_DIR
OUTPUT_DIR = Config.Traffic.OUTPUT_DIR
FINAL_OUTPUT_DIR = Config.Traffic.FINAL_OUTPUT_DIR
FILES = {
    'MAUT_TABLE': Config.Traffic.MAUT_TABLE,
    'BEFAHRUNGEN': Config.Traffic.BEFAHRUNGEN,
    'NUTS_DATA': Config.Traffic.NUTS_DATA,
    'TRAFFIC_FLOW': Config.Traffic.TRAFFIC_FLOW,
    'EDGES': Config.Traffic.EDGES,
    'NODES': Config.Traffic.NODES,
    'BREAKS_OUTPUT': Config.Traffic.BREAKS_OUTPUT,
    'TOLL_MIDPOINTS_OUTPUT': Config.Traffic.TOLL_MIDPOINTS_OUTPUT,
    'CHARGING_DEMAND': Config.Traffic.CHARGING_DEMAND,
    'FINAL_OUTPUT': Config.Traffic.FINAL_OUTPUT
}

# Import utility methods directly from Config.Traffic.Settings
validate_year = Config.Traffic.Settings.validate_year
get_breaks_column = Config.Traffic.Settings.get_breaks_column
get_charging_column = Config.Traffic.Settings.get_charging_column
get_traffic_flow_column = Config.Traffic.Settings.get_traffic_flow_column

# Extract TruckSimulation settings to a dictionary for backward compatibility
TRUCK_SIMULATION = {k: v for k, v in vars(Config.Traffic.Settings.TruckSimulation).items()
                  if not k.startswith('__') and not callable(getattr(Config.Traffic.Settings.TruckSimulation, k))}

