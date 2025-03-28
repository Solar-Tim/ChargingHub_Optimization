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
    FORECAST_YEAR = '2035'  # Default forecast year
    
    # Traffic calculation settings
    RECALCULATE_BREAKS = False
    RECALCULATE_TOLL_MIDPOINTS = False
    DEFAULT_LOCATION = {
        'LONGITUDE': 7.010174004183936,
        'LATITUDE': 51.87423718853557
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
            '2030': 0.05,  # 5% BEV trucks in 2030
            '2035': 0.20,  # 20% BEV trucks in 2035
            '2040': 0.40,  # 40% BEV trucks in 2040
        },
        'R_TRAFFIC': {
            '2030': 1.0,   # No traffic growth for 2030
            '2035': 1.05,  # 5% traffic growth for 2035
            '2040': 1.10,  # 10% traffic growth for 2040
        }
    }
    
    # Charging hub configuration
    CHARGING_CONFIG = {
        'STRATEGIES': ["Hub"],  # ["T_min", "Konstant", "Hub"]
        'ladequote': 0.8,  # Charging quota as percentage
        'power': '25-95-100',  # Power scaling for NCS-HPC-MCS
        'pause': '100-50'  # Pause time scaling for night-short
    }
    
    # Charging station types
    CHARGING_TYPES = {
        'NCS': {'power_kw': 22, 'cost': 35000},
        'HPC': {'power_kw': 150, 'cost': 110000},
        'MCS': {'power_kw': 350, 'cost': 375000}
    }
    
    # Grid optimization settings
    GRID_CONFIG = {
        'USE_DISTANCE_CALCULATION': True,
        'CREATE_PLOT': True,
        'CREATE_DISTANCE_MAPS': False,
        'INCLUDE_BATTERY': True
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