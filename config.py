"""
ChargingHub Optimization - Centralized Configuration

This module contains all configuration parameters for the charging hub optimization pipeline.
"""

import os
from pathlib import Path

class Config:
    """Global configuration parameters for the charging hub optimization project."""
    
    # General settings
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    CONTINUE_ON_ERROR = False  # Whether to continue pipeline if a step fails
    
    # Year settings
    FORECAST_YEAR = '2030'  # Default forecast year
    
    # Execution control flags - NEW SECTION
    EXECUTION_FLAGS = {

        'RUN_TRAFFIC_CALCULATION': True,  # Whether to run traffic calculation module
        'RUN_CHARGING_HUB_SETUP': False,   # Whether to run charging hub setup module
        'RUN_GRID_OPTIMIZATION': False,    # Whether to run grid optimization module
        

        # Traffic calculation sub-process flags
        'RECALCULATE_BREAKS': False,      # Whether to recalculate breaks or use cached data
        'RECALCULATE_TOLL_MIDPOINTS': False,  # Whether to recalculate toll midpoints or use cached


        # Sub-process flags for charging hub setup
        'RUN_TRUCK_MATCHING': False,       # Whether to run truck-charging type matching
        'RUN_HUB_CONFIGURATION': False,    # Whether to run charging hub configuration
        'RUN_DEMAND_OPTIMIZATION': False,  # Whether to run demand optimization
        
        
        # Grid optimization sub-process flags
        'USE_DISTANCE_CALCULATION': False,    # Whether to use distance calculation for optimization
        'CREATE_PLOT': False,                # Whether to generate plot of optimization results
        'CREATE_DISTANCE_MAPS': False,       # Whether to generate maps of distance calculations
        'INCLUDE_BATTERY': False,             # Whether to include battery in optimization
        'USE_MANUAL_CHARGER_COUNT': False,   # Whether to use manual charger count instead of optimizing
        'DEBUG_MODE': False,                 # Whether to enable debug mode for detailed output
    }

    # Charging hub configuration
    CHARGING_CONFIG = {
        'ALL_STRATEGIES': ["T_min", "Konstant", "Hub"],  # ["T_min", "Konstant", "Hub"]
        'STRATEGY': ["T_min"],  # ["T_min", "Konstant", "Hub"]
        'ladequote': 0.8,  # Charging quota as percentage
        'power': '100-100-100',  # Power scaling for NCS-HPC-MCS
        'pause': '45-540'  # Kurze Pause - Lange Pause in minutes
    }


    DEFAULT_LOCATION = {
        'LONGITUDE': 7.017641090421456,
        'LATITUDE': 51.205628072068606
    }
    
    # Spatial analysis settings
    SPATIAL = {
        'DEFAULT_CRS': 'EPSG:4326',
        'TARGET_CRS': 'EPSG:32632',  # UTM Zone 32N for Central Europe
        'BUFFER_RADIUS': 10000,  # meters - radius for location buffer
    }
    
    # BEV adoption scenarios
    SCENARIOS = {
        'TARGET_YEARS': ['2030', '2035', '2040'],
        'R_BEV': {
            '2030': 0.15,  # Updated from 0.05 to 0.15
            '2035': 0.50,  # Updated from 0.20 to 0.50
            '2040': 0.80,  # Updated from 0.40 to 0.80
        },
        'R_TRAFFIC': {
            '2030': 1.00,  # Updated from 1.0 to 1.00
            '2035': 1.06,  # Updated from 1.05 to 1.06
            '2040': 1.12,  # Updated from 1.10 to 1.12
        }
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
    
    # CSV file settings
    CSV = {
        'DEFAULT_SEPARATOR': ';',
        'DEFAULT_DECIMAL': ','
    }
    


    
    # Charging station types
    CHARGING_TYPES = {
        'NCS': {'power_kw': 75, 'cost': 35000},
        'HPC': {'power_kw': 400, 'cost': 110000},
        'MCS': {'power_kw': 1000, 'cost': 375000}
    }
    

    
    # Battery parameters
    BATTERY_CONFIG = {
        'COST_PER_KWH': 200,   # Battery storage cost per kWh
        'COST_PER_KW': 150,    # Battery power cost per kW
        'MAX_CAPACITY': 10000, # Maximum battery capacity in kWh
        'EFFICIENCY': 0.95,    # Round-trip battery efficiency
        'MIN_SOC': 0,          # Minimum state of charge
        'MAX_SOC': 1           # Maximum state of charge
    }
    
    # Load power limits for different connection types (kW)
    GRID_CAPACITIES = {
        'EXISTING_MV': 5500,        # 5.5 MW for existing MV line
        'DISTRIBUTION': 15000,      # 15 MW for distribution substation
        'TRANSMISSION': 15000,      # 15 MW for transmission substation
        'HV_LINE': 100000           # 100 MW for HV line
    }
    
    # Directory paths
    PATHS = {
        'DATA': os.path.join(PROJECT_ROOT, 'data'),
        'RESULTS': os.path.join(PROJECT_ROOT, 'results'),
        'LOGS': os.path.join(PROJECT_ROOT, 'logs')
    }
    
    # Traffic data paths
    TRAFFIC_PATHS = {
        'INPUT_DIR': os.path.join(PROJECT_ROOT, "data", "traffic", "raw_data"),
        'OUTPUT_DIR': os.path.join(PROJECT_ROOT, "data", "traffic", "interim_results"),
        'FINAL_OUTPUT_DIR': os.path.join(PROJECT_ROOT, "data", "traffic", "final_traffic")
    }
    
    # Traffic data files
    TRAFFIC_FILES = {
        # Input files
        'MAUT_TABLE': os.path.join(TRAFFIC_PATHS['INPUT_DIR'], 'Mauttabelle.xlsx'),
        'BEFAHRUNGEN': os.path.join(TRAFFIC_PATHS['INPUT_DIR'], 'Befahrungen_25_1Q.csv'),
        'NUTS_DATA': os.path.join(TRAFFIC_PATHS['INPUT_DIR'], "DE_NUTS5000.gpkg"),
        
        # New breaks input files
        'TRAFFIC_FLOW': os.path.join(TRAFFIC_PATHS['INPUT_DIR'], '01_Trucktrafficflow.csv'),
        'EDGES': os.path.join(TRAFFIC_PATHS['INPUT_DIR'], '04_network-edges.csv'),
        'NODES': os.path.join(TRAFFIC_PATHS['INPUT_DIR'], '03_network-nodes.csv'),
        
        # Output files
        'BREAKS_OUTPUT': os.path.join(TRAFFIC_PATHS['OUTPUT_DIR'], 'breaks.json'),
        'TOLL_MIDPOINTS_OUTPUT': os.path.join(TRAFFIC_PATHS['OUTPUT_DIR'], 'toll_midpoints.json'),
        'CHARGING_DEMAND': os.path.join(TRAFFIC_PATHS['OUTPUT_DIR'], 'charging_demand.json'),
        'FINAL_OUTPUT': os.path.join(TRAFFIC_PATHS['FINAL_OUTPUT_DIR'], 'laden_mauttabelle.json')
    }
    
    @classmethod
    def validate_year(cls, year_value):
        """Validate that the given year exists in the SCENARIOS dictionaries."""
        if year_value not in cls.SCENARIOS['R_BEV']:
            raise ValueError(f"Year {year_value} not found in SCENARIOS['R_BEV']")
        if year_value not in cls.SCENARIOS['R_TRAFFIC']:
            raise ValueError(f"Year {year_value} not found in SCENARIOS['R_TRAFFIC']")
        return year_value
    
    @classmethod
    def get_breaks_column(cls, break_type):
        """Return column name for breaks based on break_type and current year."""
        return f"{break_type}_breaks_{cls.FORECAST_YEAR}"
    
    @classmethod
    def get_charging_column(cls, charging_type, target_year=None):
        """Return column name for charging sessions based on charging_type and year."""
        year_to_use = target_year if target_year else cls.FORECAST_YEAR
        return f"{charging_type}_{year_to_use}"
    
    @classmethod
    def get_traffic_flow_column(cls):
        """Return the traffic flow column name using the current year."""
        return f"Traffic_flow_trucks_{cls.FORECAST_YEAR}"