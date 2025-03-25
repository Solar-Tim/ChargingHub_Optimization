"""
Centralized configuration for the charging hub demand calculation pipeline.

This module contains all configuration parameters used across the demand calculation
modules, including file paths, scenario parameters, spatial analysis settings, and
break calculation thresholds.
"""

import os
from pathlib import Path

# Decide whether to calculate new breaks or load existing ones
neue_pausen = False  # Set to True to calculate new breaks, False to load existing ones
# Decide whether to preprocess toll midpoints or load existing ones
neue_toll_midpoints = False  # Set to True to recalculate toll midpoints, False to load existing ones

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))  # Up two levels to project root

# Input/output directories
INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "traffic", "raw_data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "traffic", "interim_results")
FINAL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "traffic", "final_traffic")

# File paths
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
    'BREAKS_OUTPUT': os.path.join(OUTPUT_DIR, 'breaks.csv'),
    'TOLL_MIDPOINTS_OUTPUT': os.path.join(OUTPUT_DIR, 'toll_midpoints.csv'),
    'CHARGING_DEMAND': os.path.join(OUTPUT_DIR, 'charging_demand.csv'),
    'FINAL_OUTPUT': os.path.join(FINAL_OUTPUT_DIR, 'laden_mauttabelle.csv')
}

# Spatial analysis settings
SPATIAL = {
    'DEFAULT_CRS': 'EPSG:4326',
    'TARGET_CRS': 'EPSG:32632',  # UTM Zone 32N for Central Europe
    'BUFFER_RADIUS': 25000,  # meters - radius for location buffer
}

# Driver break calculation settings
BREAKS = {
    'DISTANCE_THRESHOLD': 360,  # km - Distance after which a break is required
    'MAX_DISTANCE_SINGLEDRIVER': 4320,  # km - Limit between single and double driver routes
    'RANDOM_RANGE': (-50, 50),  # Random variation for break distances
    'TWO_DRIVER_SHORT_BREAKS_BEFORE_LONG': 2  # Number of short breaks before a long break for two drivers
}

# Day mappings (German to English)
DAY_MAPPING = {
    'Montag': 'Monday',
    'Dienstag': 'Tuesday',
    'Mittwoch': 'Wednesday',
    'Donnerstag': 'Thursday', 
    'Freitag': 'Friday',
    'Samstag': 'Saturday',
    'Sonntag': 'Sunday'
}
GERMAN_DAYS = list(DAY_MAPPING.keys())

# Time constants
TIME = {
    'WEEKS_PER_YEAR': 52
}

# Scenario parameters for future years
SCENARIOS = {
    # BEV adoption rates for different years
    'R_BEV': {
        '2030': 0.15,
        '2035': 0.50,
        '2040': 0.80
    },
    # Traffic growth factors for different years
    'R_TRAFFIC': {
        '2030': 1.00,
        '2035': 1.06,
        '2040': 1.12
    },
    # Default target years for scenario calculation
    'TARGET_YEARS': ['2030', '2035', '2040']
}

# Default parameters for charging demand scaling
CHARGING_DEMAND = {
    'DEFAULT_ANNUAL_HPC_SESSIONS': 10000,
    'DEFAULT_ANNUAL_NCS_SESSIONS': 3000
}

# CSV file settings
CSV = {
    'DEFAULT_SEPARATOR': ';',
    'DEFAULT_DECIMAL': ','
}

# Default test location (for demo/default runs)
DEFAULT_LOCATION = {
    'LONGITUDE': 7.010174004183936,
    'LATITUDE': 51.87423718853557
}