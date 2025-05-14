"""
Compatibility module for traffic calculation scripts.
This module imports configuration from the global Config class.
"""

import sys
import os
# Add the parent directory to path to import from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config

# Backwards compatibility variables
year = Config.FORECAST_YEAR
neue_pausen = Config.EXECUTION_FLAGS['RECALCULATE_BREAKS']
neue_toll_midpoints = Config.EXECUTION_FLAGS['RECALCULATE_TOLL_MIDPOINTS']

# Instead of copying these values, create property functions that always get the current value
def get_default_location():
    """
    Get the default location, with support for environmental override.
    This allows per-process location customization.
    """
    # Check if environment variables are set to override the default location
    if 'OVERRIDE_LONGITUDE' in os.environ and 'OVERRIDE_LATITUDE' in os.environ:
        return {
            'LONGITUDE': float(os.environ['OVERRIDE_LONGITUDE']),
            'LATITUDE': float(os.environ['OVERRIDE_LATITUDE'])
        }
    
    # Otherwise return the default configuration
    return Config.DEFAULT_LOCATION

# Replace static variables with property functions
SCENARIOS = Config.SCENARIOS
SPATIAL = Config.SPATIAL
BREAKS = Config.BREAKS
DAY_MAPPING = Config.DAY_MAPPING
GERMAN_DAYS = Config.GERMAN_DAYS
TIME = Config.TIME
CSV = Config.CSV

# Set up file paths for backward compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # traffic_calculation folder
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))  # Go up two levels to reach project root
INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "traffic", "raw_data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "traffic", "interim_results")
FINAL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "traffic", "final_traffic")

# Create a mapping for traffic files with absolute paths
FILES = {
    # Input files
    'MAUT_TABLE': os.path.join(INPUT_DIR, 'Mauttabelle.xlsx'),
    'BEFAHRUNGEN': os.path.join(INPUT_DIR, 'Befahrungen_25_1Q.csv'),
    'NUTS_DATA': os.path.join(INPUT_DIR, "DE_NUTS5000.gpkg"),
        
    # New breaks input files
    'TRAFFIC_FLOW': os.path.join(INPUT_DIR, '01_Trucktrafficflow.csv'),
    'EDGES': os.path.join(INPUT_DIR, '04_network-edges.csv'),
    'NODES': os.path.join(INPUT_DIR, '03_network-nodes.csv'),
        
    # Output files
    'BREAKS_OUTPUT': os.path.join(OUTPUT_DIR, 'breaks.json'),
    'TOLL_MIDPOINTS_OUTPUT': os.path.join(OUTPUT_DIR, 'toll_midpoints.json'),
    'CHARGING_DEMAND': os.path.join(OUTPUT_DIR, 'charging_demand.json'),
    'FINAL_OUTPUT': os.path.join(FINAL_OUTPUT_DIR, 'laden_mauttabelle.json')
}

# Import utility functions for backward compatibility
validate_year = Config.validate_year
get_breaks_column = Config.get_breaks_column
get_charging_column = Config.get_charging_column
get_traffic_flow_column = Config.get_traffic_flow_column

