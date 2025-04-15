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
year = '2030'
neue_pausen = Config.EXECUTION_FLAGS['RECALCULATE_BREAKS']
neue_toll_midpoints = Config.EXECUTION_FLAGS['RECALCULATE_TOLL_MIDPOINTS']

# Instead of copying these values, create property functions that always get the current value
def get_default_location():
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
INPUT_DIR = Config.TRAFFIC_PATHS['INPUT_DIR']
OUTPUT_DIR = Config.TRAFFIC_PATHS['OUTPUT_DIR']
FINAL_OUTPUT_DIR = Config.TRAFFIC_PATHS['FINAL_OUTPUT_DIR']
FILES = Config.TRAFFIC_FILES

# Import utility functions for backward compatibility
validate_year = Config.validate_year
get_breaks_column = Config.get_breaks_column
get_charging_column = Config.get_charging_column
get_traffic_flow_column = Config.get_traffic_flow_column

