"""
ChargingHub Optimization - Centralized Configuration

This module contains all configuration parameters for the charging hub optimization pipeline,
organized into logical groups for improved readability and maintenance.
"""

from logging import config as logging_config
import os
from math import inf
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

class Config:
    """Global configuration parameters for the charging hub optimization project."""
    
    # General settings
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    CONTINUE_ON_ERROR = False  # Whether to continue pipeline if a step fails
    FORECAST_YEAR = '2030'
    
    class Paths:
        """File and directory paths used throughout the project."""
        # Compute the project root locally to avoid cross-reference issues during class definition
        PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
        DATA = os.path.join(PROJECT_ROOT, 'data')
        RESULTS = os.path.join(PROJECT_ROOT, 'results')
        LOGS = os.path.join(PROJECT_ROOT, 'logs')
    
    class GridSettings:
        """Grid connection and optimization parameters."""
        # Charging strategy and control flags
        CHARGING_STRATEGY = "Konstant"  # Options: "Hub", "Konstant", "T_min"
        DEBUG_MODE = True
        USE_DISTANCE_CALCULATION = True
        CREATE_PLOT = True
        CREATE_DISTANCE_MAPS = True
        INCLUDE_BATTERY = True
        USE_MANUAL_CHARGER_COUNT = False
        
        # Optimization parameter
        M_VALUE = 1000000
        
        # Manual distances when not calculating automatically (in meters)
        MANUAL_DISTANCES = {
            'distribution_distance': 10000,
            'transmission_distance': 9999999,
            'powerline_distance': 9999999,
        }
        
        # Grid connection and capacity fee parameters
        EXISTING_MV_CONNECTION_COST = 0  # (EUR)
        HV_CAPACITY_FEE = 111.14   # (€/kW) from BKZ (Regionetz)
        MV_CAPACITY_FEE = 183.56   # (€/kW) from BKZ (Regionetz)
        
        # Line capacities (kW)
        CONNECTION_CAPACITIES = {
            'EXISTING_MV': 1500,
            'DISTRIBUTION': 15000,
            'TRANSMISSION': 15000,
            'HV_LINE': 100000,
        }
        
        # Substation expansion parameters (costs in EUR, capacities in kW)
        SUBSTATION_PARAMETERS = {
            'distribution_existing_capacity': 2000,
            'distribution_max_expansion': 5000,
            'transmission_existing_capacity': 10000,
            'transmission_max_expansion': 10000,
            'distribution_expansion_fixed_cost': 500000,
            'transmission_expansion_fixed_cost': 500000,
            'HV_Substation_cost': 2500000,
        }
        
        # Transformer costs (EUR)
        TRANSFORMER_BASE_COSTS = {
            'basecost_transformer': 20000,     # for 1000 kW
            'cost_transformer_perkW': 200,
        }
        
        # Available transformer options (capacities and corresponding costs)
        TRANSFORMERS = {
            "Kapazität": [
                1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 
                10000, 12500, 16000, 20000, 25000, 31500, 40000, 50000
            ],
            "Kosten": [
                220000, 273600, 338261, 407568, 493095, 600236, 735321, 886797, 1096542, 1349608,
                1642456, 1987088, 2457062, 2988281, 3618314, 4406397, 5425984, 6600811
            ]
        }
        
        # Battery storage configuration
        BATTERY_CONFIG = {
            'COST_PER_KWH': 20,
            'COST_PER_KW': 15,
            'MAX_CAPACITY': 999999,
            'MAX_POWER': 999999,
            'EFFICIENCY': 0.95,
            'MIN_SOC': 0,
            'MAX_SOC': 1
        }
        
        # Time parameters for simulation (resolution in minutes, period in hours)
        TIME_PARAMETERS = {
            'TIME_RESOLUTION': 5,
            'SIMULATION_PERIOD': 8760,
        }
        
        # Low voltage cable parameters
        LV_CABLE_PARAMETERS = {
            'voltage': 400,
            'voltage_drop_percent': 2.0,
            'power_factor': 0.95,
            'conductivity': 56,  # Copper
        }
        
        # Medium voltage cable parameters
        MV_CABLE_PARAMETERS = {
            'voltage': 20000,
            'voltage_drop_percent': 3.0,
            'power_factor': 0.90,
            'conductivity': 35,  # Aluminium
        }
        
        # MV cable construction cost parameters
        CABLE_CONSTRUCTION_COST = {
            'digging_cost': 34.0,  # EUR/m
            'cable_hardware_connection_cost': 930,
            'number_cables': 3,
        }
        
        # Cable specifications for aluminium cables
        ALUMINIUM_KABEL = {
            "Nennquerschnitt": [
                16.0, 25.0, 35.0, 50.0, 70.0, 95.0, 120.0, 150.0, 185.0, 240.0,
                300.0, 400.0, 500.0, 630.0, 800.0, 1000.0, 1200.0, 1400.0, 1600.0,
                1800.0, 2000.0, 2500.0, 3000.0, 3200.0, 3500.0, 9999.0
            ],
            "Belastbarkeit": [
                105, 140, 195, 237, 282, 319, 352, 396, 455, 510, 564, 634, 710, 800,
                880, 980, 1080, 1170, 1250, 1320, 1380, 1550, 1700, 1760, 1850, 3000
            ],
            "Kosten": [
                7.77, 10.62, 12.00, 15.00, 20.00, 26.00, 30.00, 35.00, 40.00, 48.00, 55.00,
                70.00, 85.00, 100.00, 120.00, 140.00, 160.00, 180.00, 200.00, 220.00, 240.00,
                300.00, 360.00, 380.00, 420.00, 999.99
            ]
        }
        
        # Cable specifications for copper cables
        KUPFER_KABEL = {
            "Nennquerschnitt": [
                0.5, 0.75, 1.0, 1.5, 2.5, 4.0, 6.0, 10.0, 16.0, 25.0, 35.0, 50.0,
                70.0, 95.0, 120.0, 150.0, 185.0, 240.0, 300.0, 400.0, 9999.0
            ],
            "Kosten": [
                0.50, 0.65, 0.80, 1.10, 1.60, 2.40, 3.50, 5.80, 8.50, 12.80, 17.50,
                24.00, 32.50, 44.00, 55.00, 68.00, 82.00, 105.00, 130.00, 165.00, 500.00
            ]
        }
        
        # Internal low-voltage cabling parameters
        INTERNAL_CABLING = {
            'charger_distance_increment': 4,
            'mcs_power_kw': 350,
            'hpc_power_kw': 150,
            'ncs_power_kw': 22,
        }
    
    class ChargingInfrastructure:
        """Configuration for charging infrastructure."""
        STATION_TYPES = {
            'NCS': {'power_kw': 22, 'cost': 35000},
            'HPC': {'power_kw': 150, 'cost': 110000},
            'MCS': {'power_kw': 350, 'cost': 375000},
        }
        POWER_RATINGS = {
            'NCS': 100,
            'HPC': 400,
            'MCS': 1000,
        }
        HUB_CONFIG = {
            'STRATEGIES': ["T_min", "Konstant", "Hub"],
            'ladequote': 0.8,
            'power': '100-100-100',
            'pause': '45-540',
        }
        CHARGER_COUNTS = {
            'NCS': 25,
            'HPC': 10,
            'MCS': 5,
        }
        CHARGING_QUOTAS = {
            'NCS': 0.8,
            'HPC': 0.8,
            'MCS': 0.8,
        }
        CHARGING_TIMES = {
            'Schnell': 45,
            'Nacht': 540,
        }
        SCENARIO_NAME = 'Base'
    
    class Traffic:
        """Traffic configuration including file paths and simulation settings."""
        # Use an explicit path without referencing the Config class
        # Get project root path directly
        PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
        DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
        
        # File paths for traffic-related data
        INPUT_DIR = os.path.join(DATA_DIR, "traffic", "raw_data")
        OUTPUT_DIR = os.path.join(DATA_DIR, "traffic", "interim_results")
        FINAL_OUTPUT_DIR = os.path.join(DATA_DIR, "traffic", "final_traffic")
        MAUT_TABLE = os.path.join(INPUT_DIR, 'Mauttabelle.xlsx')
        BEFAHRUNGEN = os.path.join(INPUT_DIR, 'Befahrungen_25_1Q.csv')
        NUTS_DATA = os.path.join(INPUT_DIR, "DE_NUTS5000.gpkg")
        TRAFFIC_FLOW = os.path.join(INPUT_DIR, '01_Trucktrafficflow.csv')
        EDGES = os.path.join(INPUT_DIR, '04_network-edges.csv')
        NODES = os.path.join(INPUT_DIR, '03_network-nodes.csv')
        BREAKS_OUTPUT = os.path.join(OUTPUT_DIR, 'breaks.json')
        TOLL_MIDPOINTS_OUTPUT = os.path.join(OUTPUT_DIR, 'toll_midpoints.json')
        CHARGING_DEMAND = os.path.join(OUTPUT_DIR, 'charging_demand.json')
        FINAL_OUTPUT = os.path.join(FINAL_OUTPUT_DIR, 'laden_mauttabelle.json')
        
        class Settings:
            """Traffic flow and simulation settings."""
            RECALCULATE_BREAKS = False
            RECALCULATE_TOLL_MIDPOINTS = False
            DEFAULT_LOCATION = {
                'LONGITUDE': 8.683978444516883,
                'LATITUDE': 51.83920575571095
            }
            BREAKS = {
                'DISTANCE_THRESHOLD': 360,           # km
                'MAX_DISTANCE_SINGLEDRIVER': 4320,     # km
                'RANDOM_RANGE': (-50, 50),
                'TWO_DRIVER_SHORT_BREAKS_BEFORE_LONG': 2
            }
            TIME = {
                'WEEKS_PER_YEAR': 52
            }
            DAY_MAPPING = {
                'Montag': 'Monday',
                'Dienstag': 'Tuesday',
                'Mittwoch': 'Wednesday',
                'Donnerstag': 'Thursday', 
                'Freitag': 'Friday',
                'Samstag': 'Saturday',
                'Sonntag': 'Sunday'
            }
            # Create list of German days based on DAY_MAPPING
            GERMAN_DAYS = list(DAY_MAPPING.keys())
            
            class SpatialSettings:
                """Spatial analysis configuration parameters."""
                DEFAULT_CRS = 'EPSG:4326'   # WGS84
                TARGET_CRS = 'EPSG:32632'   # UTM Zone 32N for Central Europe
                BUFFER_RADIUS = 10000       # in meters
            
            class ForecastScenarios:
                """Forecast scenarios for different years."""
                TARGET_YEARS = ['2030', '2035', '2040']
                R_BEV = {
                    '2030': 0.15,
                    '2035': 0.50,
                    '2040': 0.80,
                }
                R_TRAFFIC = {
                    '2030': 1.00,
                    '2035': 1.06,
                    '2040': 1.12,
                }
            
            class FileFormats:
                """Settings for file formats and parsing."""
                CSV = {
                    'DEFAULT_SEPARATOR': ';',
                    'DEFAULT_DECIMAL': ','
                }
            
            class TruckSimulation:
                """Configuration for truck charging simulation."""
                RANDOM_SEED = 42
                UPDATE_FREQUENCY_MIN = 5           # in minutes
                SIMULATION_HORIZON_DAYS = 7          # one-week simulation
                SIMULATION_START_DATE = '2024-01-01' # Monday reference start date
                CALENDAR_WEEK = 1
                SOC_CALCULATION = {
                    'EARLY_MORNING_THRESHOLD': 360,  # Minutes (6:00 AM)
                    'EARLY_MORNING_BASE_SOC': 0.2,
                    'DAYTIME_SLOPE': -0.00028,         # SOC decrease per minute
                    'DAYTIME_BASE_SOC': 0.6,
                    'RANDOM_VARIATION': 0.1
                }
                POWER_FACTOR_COEFFICIENTS = {
                    'LINE1_SLOPE': -0.177038,
                    'LINE1_INTERCEPT': 0.970903,
                    'LINE2_SLOPE': -1.51705,
                    'LINE2_INTERCEPT': 1.6336
                }
                TRUCK_FLEET = {
                    'TYPE_PROBABILITIES': {
                        '1': 0.093,
                        '2': 0.187,
                        '3': 0.289,
                        '4': 0.431
                    },
                    'BATTERY_CAPACITIES': {
                        '1': 600,
                        '2': 720,
                        '3': 840,
                        '4': 960
                    },
                    'MAX_POWER_RATINGS': {
                        '1': 750,
                        '2': 750,
                        '3': 1200,
                        '4': 1200
                    }
                }
                PAUSE_TYPES = ['Schnelllader', 'Nachtlader']
                PAUSE_DURATIONS = {
                    'Schnelllader': 45,
                    'Nachtlader': 540
                }
                PAUSENTYP_TO_COLUMN = {
                    'Schnelllader': 'HPC',
                    'Nachtlader': 'NCS'
                }
                ENERGY_PER_SECTION = 80 * 4.5 * 1.26  # kWh per route section
                SAFETY_BUFFER = 0.1                   # Additional SOC buffer (10%)
            
            @classmethod
            def validate_year(cls, year_value: str) -> str:
                """Validate that the given year exists in the forecast scenarios."""
                if year_value not in cls.ForecastScenarios.R_BEV:
                    raise ValueError(f"Year {year_value} not found in ForecastScenarios.R_BEV")
                if year_value not in cls.ForecastScenarios.R_TRAFFIC:
                    raise ValueError(f"Year {year_value} not found in ForecastScenarios.R_TRAFFIC")
                return year_value
            
            @classmethod
            def get_breaks_column(cls, break_type: str) -> str:
                """Return a formatted breaks column name using the global forecast year."""
                return f"{break_type}_breaks_{Config.FORECAST_YEAR}"
            
            @classmethod
            def get_charging_column(cls, charging_type: str, target_year: Optional[str] = None) -> str:
                """Return a formatted charging column name for a given type and year."""
                year_to_use = target_year if target_year else Config.FORECAST_YEAR
                return f"{charging_type}_{year_to_use}"
            
            @classmethod
            def get_traffic_flow_column(cls) -> str:
                """Return the traffic flow column name using the global forecast year."""
                return f"Traffic_flow_trucks_{Config.FORECAST_YEAR}"
