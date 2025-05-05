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

        # Add this to your Config class or configuration section
    RESULT_NAMING = {
        'USE_CUSTOM_ID': True,  # Set to True to use custom ID instead of hash
        'CUSTOM_ID': '988'  # The custom ID to use when USE_CUSTOM_ID is True
    }
    
    
    # Execution control flags - NEW SECTION
    EXECUTION_FLAGS = {

        'RUN_TRAFFIC_CALCULATION': True,  # Whether to run traffic calculation module
        'RUN_CHARGING_HUB_SETUP': True,   # Whether to run charging hub setup module
        'RUN_GRID_OPTIMIZATION': True,    # Whether to run grid optimization module
        

        # Traffic calculation sub-process flags
        'RECALCULATE_BREAKS': False,      # Whether to recalculate breaks or use cached data
        'RECALCULATE_TOLL_MIDPOINTS': False,  # Whether to recalculate toll midpoints or use cached


        # Sub-process flags for charging hub setup
        'RUN_TRUCK_MATCHING': True,       # Whether to run truck-charging type matching
        'RUN_HUB_CONFIGURATION': True,    # Whether to run charging hub configuration
        'RUN_DEMAND_OPTIMIZATION': True,  # Whether to run demand optimization
        
        
        # Grid optimization sub-process flags
        'USE_DISTANCE_CALCULATION': True,    # Whether to use distance calculation for optimization
        'CREATE_PLOT': False,                # Whether to generate plot of optimization results
        'CREATE_DISTANCE_MAPS': True,       # Whether to generate maps of distance calculations
        'INCLUDE_BATTERY': True,             # Whether to include battery in optimization
        'USE_MANUAL_CHARGER_COUNT': False,   # Whether to use manual charger count instead of optimizing
        'DEBUG_MODE': False,                 # Whether to enable debug mode for detailed output
    }

    # Charging hub configuration
    CHARGING_CONFIG = {
        'ALL_STRATEGIES': ["T_min", "Konstant", "Hub"],  # ["T_min", "Konstant", "Hub"]
        'STRATEGY': ["T_min", "Konstant", "Hub"],  # ["T_min", "Konstant", "Hub"]
        'ladequote': 0.8,  # Charging quota as percentage
        'power': '100-100-100',  # Power scaling for NCS-HPC-MCS
        'pause': '45-540'  # Kurze Pause - Lange Pause in minutes
    }
    
    MANUAL_CHARGER_COUNT = {
        'NCS': 4,  # Number of NCS chargers
        'HPC': 6,   # Number of HPC chargers
        'MCS': 2    # Number of MCS chargers
    }

    # Manual distance values when not using distance calculation
    MANUAL_DISTANCES = {
        'distribution_distance': 10,    # Distance to nearest distribution substation (m)
        'transmission_distance': 9999999,   # Distance to nearest transmission substation (m)
        'powerline_distance': 9999999,      # Distance to nearest HV power line (m)
    }

    DEFAULT_LOCATION = {
        'LONGITUDE': 6.60414,
        'LATITUDE': 51.12994
    }


    # Spatial analysis settings
    SPATIAL = {
        'DEFAULT_CRS': 'EPSG:4326',
        'TARGET_CRS': 'EPSG:32632',  # UTM Zone 32N for Central Europe
        'BUFFER_RADIUS': 1,  # meters - radius for location buffer
    }
    
    # BEV adoption scenarios
    SCENARIOS = {
        'TARGET_YEARS': ['2030', '2035', '2040', '2045'],
        'R_BEV': {
            '2030': 0.15,  #
            '2035': 0.61,  #
            '2040': 0.94,  #
            '2045': 1.00   #
        },
        'R_TRAFFIC': {
            '2030': 1.00,  #
            '2035': 1.0462,  #
            '2040': 1.0549,  #
            '2045': 1.1672   #
        }
    }
    
    # Driver break calculation settings
    BREAKS = {
        'DISTANCE_THRESHOLD': 360,  # km - Distance after which a break is required
        'MAX_DISTANCE_SINGLEDRIVER': 4320,  # km - Limit between single and double driver routes
        'RANDOM_RANGE': (0,0),  # Random variation for break distances
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
        'WEEKS_PER_YEAR': 52,
        'RESOLUTION_MINUTES': 5,     # Time resolution in minutes
        'SIMULATION_HOURS': 8760,    # Hours in a year for simulation
        'WEEK_MINUTES': 10080,       # 7 days * 24 hours * 60 minutes
        'TIMESTEPS_PER_DAY': 288,    # 24 hours * 60 minutes / 5 minutes
        'TIMESTEPS_PER_WEEK': 2016,  # 288 timesteps per day * 7 days
    }
    
    # CSV file settings
    CSV = {
        'DEFAULT_SEPARATOR': ';',
        'DEFAULT_DECIMAL': ','
    }

    # Charging station types
    CHARGING_TYPES = {
        'NCS': {'power_kw': 100, 'cost': 35000},
        'HPC': {'power_kw': 400, 'cost': 110000},
        'MCS': {'power_kw': 1000, 'cost': 375000}
    }
    
    # Battery parameters
    BATTERY_CONFIG = {
        'COST_PER_KWH': 175.0,   # Battery storage cost per kWh
        'COST_PER_KW': 100.0,    # Battery power cost per kW
        'MAX_CAPACITY': 99999.0, # Maximum battery capacity in kWh
        'MAX_POWER': 99999.0,    # Maximum battery power in kW
        'EFFICIENCY': 0.95,    # Round-trip battery efficiency
        'MIN_SOC': 0.0,          # Minimum state of charge
        'MAX_SOC': 1.0           # Maximum state of charge
    }
    
    # Grid capacity fees (€/kW) - Baukostenzuschuss
    CAPACITY_FEES = {
        'HV': 111.14,  # Based of BKZ from Regionetz OHNE Reduzierung durch Regionetz *0.5
        'MV': 183.56   # Based of BKZ from Regionetz OHNE Reduzierung durch Regionetz *0.5
    }
    
    # Load power limits for different connection types (kW)
    GRID_CAPACITIES = {
        'EXISTING_MV': 5500,        # 5.5 MW for existing MV line
        'DISTRIBUTION': 15000,      # 15 MW for distribution substation
        'TRANSMISSION': 15000,      # 15 MW for transmission substation
        'HV_LINE': 100000           # 100 MW for HV line
    }

    # Substation configuration parameters
    SUBSTATION_CONFIG = {
        'DISTRIBUTION': {
            'EXISTING_CAPACITY': 20000,  # Initial available capacity (kW)
            'MAX_EXPANSION': 20000,      # Maximum additional expansion (kW)
            'EXPANSION_FIXED_COST': 500000  # Fixed cost for expanding distribution substation (EUR)
        },
        'TRANSMISSION': {
            'EXISTING_CAPACITY': 20000,  # Initial available capacity (kW)
            'MAX_EXPANSION': 20000,      # Maximum additional expansion (kW)
            'EXPANSION_FIXED_COST': 500000  # Fixed cost for expanding transmission substation (EUR)
        },
        'HV_SUBSTATION_COST': 2500000  # Cost of a new HV substation ~2.5M EUR
    }

    # Transformer configuration
    # Formula: Cost = 120,000€ + (capacity_kW - 1,000) × 100€/kW
    TRANSFORMER_CONFIG = {
        "CAPACITIES": [
            1000, 1250, 1600, 2000, 2500, 3150
        ],
        "COSTS": [
            120000,   # 1000 kW: 120,000€ (base cost)
            145000,   # 1250 kW: 120,000€ + (1,250-1,000)×100€ = 145,000€
            180000,   # 1600 kW: 120,000€ + (1,600-1,000)×100€ = 180,000€
            220000,   # 2000 kW: 120,000€ + (2,000-1,000)×100€ = 220,000€
            270000,   # 2500 kW: 120,000€ + (2,500-1,000)×100€ = 270,000€
            335000    # 3150 kW: 120,000€ + (3,150-1,000)×100€ = 335,000€
        ]
    }

    # Cable configuration parameters
    CABLE_CONFIG = {
        # Low voltage cable parameters
        'LV': {
            'VOLTAGE': 400,  # V
            'VOLTAGE_DROP_PERCENT': 2.0,
            'POWER_FACTOR': 0.95,
            'CONDUCTIVITY': 56,  # Copper
            'NUM_DC_CABLES': 1  # Number of cables for DC connections
        },
        
        # Medium voltage cable parameters
        'MV': {
            'VOLTAGE': 20000,  # V
            'VOLTAGE_DROP_PERCENT': 3.0,
            'POWER_FACTOR': 0.90,
            'CONDUCTIVITY': 35,  # Aluminium
            'NUM_CABLES': 3  # Number of cables in parallel
        },
        
        # Construction costs
        'CONSTRUCTION': {
            'DIGGING_COST': 34.0,  # Cost of digging per meter (EUR/m)
            'HARDWARE_CONNECTION_COST': 930  # Cable mounting costs per piece (EUR)
        }
    }


    # Cable Cost
    aluminium_kabel = {
        "Nennquerschnitt": [
            16.0, 25.0, 35.0, 50.0, 70.0, 95.0, 120.0, 150.0, 185.0, 240.0,
            300.0, 400.0, 500.0, 630.0, 800.0, 1000.0, 1200.0, 1400.0, 1600.0,
            1800.0, 2000.0, 2500.0, 3000.0, 3200.0, 3500.0, 9999.0
        ],
        "Belastbarkeit": [
            105,   # 16 mm²: estimated
            140,   # 25 mm²: estimated
            195,   # 35 mm²: 195 A (Belastbarkeit für Einzelanordnung in Erde nach Norm VDE 0276-620, 12/20 kV) 
            237,   # 50 mm²: 237 A
            282,   # 70 mm²: 282 A
            319,   # 95 mm²: 319 A
            352,   # 120 mm²: 352 A
            396,   # 150 mm²: estimated
            455,   # 185 mm²: 455 A
            510,   # 240 mm²: 510 A
            564,   # 300 mm²: 564 A
            634,   # 400 mm²: 634 A
            710,   # 500 mm²: estimated
            800,   # 630 mm²: estimated
            880,   # 800 mm²: estimated
            980,   # 1000 mm²: estimated
            1080,  # 1200 mm²: estimated
            1170,  # 1400 mm²: estimated
            1250,  # 1600 mm²: estimated
            1320,  # 1800 mm²: estimated
            1380,  # 2000 mm²: estimated
            1550,  # 2500 mm²: estimated
            1700,  # 3000 mm²: estimated
            1760,  # 3200 mm²: estimated
            1850,  # 3500 mm²: estimated
            3000   # 9999 mm²: Fantasy value for larger sizes
        ],
        "Kosten": [
            7.77,    # 16 mm²: ca. 8,00 €/m (NA2XSY 12/20 kV) [Quelle: Helukabel - 6.27 bis 9.28]
            10.62,   # 25 mm²: ca. 10,00 €/m (NA2XSY 12/20 kV) [Quelle: Helukabel - 9.35 bis 11.89]
            12.00,   # 35 mm²: ca. 12,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            15.00,   # 50 mm²: ca. 15,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            20.00,   # 70 mm²: ca. 20,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            26.00,   # 95 mm²: ca. 26,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            30.00,   # 120 mm²: ca. 30,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            35.00,   # 150 mm²: ca. 35,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            40.00,   # 185 mm²: ca. 40,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            48.00,   # 240 mm²: ca. 48,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            55.00,   # 300 mm²: ca. 55,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            70.00,   # 400 mm²: ca. 70,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            85.00,   # 500 mm²: ca. 85,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            100.00,  # 630 mm²: ca. 100,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            120.00,  # 800 mm²: ca. 120,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            140.00,  # 1000 mm²: ca. 140,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            160.00,  # 1200 mm²: ca. 160,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            180.00,  # 1400 mm²: ca. 180,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            200.00,  # 1600 mm²: ca. 200,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            220.00,  # 1800 mm²: ca. 220,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            240.00,  # 2000 mm²: ca. 240,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            300.00,  # 2500 mm²: ca. 300,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            360.00,  # 3000 mm²: ca. 360,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            380.00,  # 3200 mm²: ca. 380,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            420.00,  # 3500 mm²: ca. 420,00 €/m (NA2XSY 12/20 kV) [Quelle: Temo-Elektro, AMS-Elektro]
            999.99   # 9999 mm²: Fantasy value for larger sizes
        ]
    }

    kupfer_kabel = {
        "Nennquerschnitt": [
            0.5, 0.75, 1.0, 1.5, 2.5, 4.0, 6.0, 10.0, 16.0, 25.0, 35.0, 50.0, 70.0, 95.0, 120.0, 150.0, 185.0, 240.0, 300.0, 400.0, 9999.0
        ],
        "Kosten": [
            0.50,    # 0.5 mm²: ~0.50 €/m for standard copper cable
            0.65,    # 0.75 mm²: ~0.65 €/m
            0.80,    # 1.0 mm²: ~0.80 €/m
            1.10,    # 1.5 mm²: ~1.10 €/m
            1.60,    # 2.5 mm²: ~1.60 €/m
            2.40,    # 4.0 mm²: ~2.40 €/m
            3.50,    # 6.0 mm²: ~3.50 €/m
            5.80,    # 10.0 mm²: ~5.80 €/m
            8.50,    # 16.0 mm²: ~8.50 €/m
            12.80,   # 25.0 mm²: ~12.80 €/m
            17.50,   # 35.0 mm²: ~17.50 €/m
            24.00,   # 50.0 mm²: ~24.00 €/m
            32.50,   # 70.0 mm²: ~32.50 €/m
            44.00,   # 95.0 mm²: ~44.00 €/m
            55.00,   # 120.0 mm²: ~55.00 €/m
            68.00,   # 150.0 mm²: ~68.00 €/m
            82.00,   # 185.0 mm²: ~82.00 €/m
            105.00,  # 240.0 mm²: ~105.00 €/m
            130.00,  # 300.0 mm²: ~130.00 €/m
            165.00,  # 400.0 mm²: ~165.00 €/m
            165.00   # 9999.0 mm²: placeholder for larger sizes
        ]
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

    @classmethod
    def generate_result_filename(cls, results=None, strategy=None, battery_allowed=None, custom_id=None):
        """
        Generate a standardized filename for optimization results.
        
        Args:
            results: Dictionary containing optimization results (optional)
            strategy: Strategy name (optional)
            battery_allowed: Boolean indicating if battery was allowed (optional)
            custom_id: User-defined unique identifier (optional)
        
        Returns:
            String: Filename in format {id}_{strategy}_{battery_status}
        """
        import hashlib
        import datetime
        
        print(f"DEBUG: Config.generate_result_filename called with custom_id={custom_id}")
        print(f"DEBUG: Config.RESULT_NAMING={cls.RESULT_NAMING}")
        
        # Get strategy name
        strategy_name = strategy
        if not strategy_name and results:
            strategy_name = results.get('charging_strategy', 'unknown')
        
        # Determine battery status - prioritize the explicit parameter
        if battery_allowed is not None:
            battery_status = "withBat" if battery_allowed else "noBat"
        else:
            # If not provided, check the global config flag
            battery_status = "withBat" if cls.EXECUTION_FLAGS.get('INCLUDE_BATTERY', True) else "noBat"
        
        # Priority order for ID determination:
        # 1. custom_id parameter if provided (highest priority)
        # 2. Value from RESULT_NAMING if USE_CUSTOM_ID is True
        # 3. Generate hash if neither is available
        if custom_id:  # Highest priority - use custom_id if provided
            file_id = custom_id
            print(f"DEBUG: Using provided custom_id: {custom_id}")
        elif cls.RESULT_NAMING.get('USE_CUSTOM_ID', False):
            file_id = cls.RESULT_NAMING.get('CUSTOM_ID', '000')
            print(f"DEBUG: Using RESULT_NAMING custom_id: {file_id}")
        else:
            # Create a hash based on the key parameters
            if results:
                hash_input = f"{strategy_name}_{results.get('max_grid_load', 0)}_{results.get('total_cost', 0)}"
            else:
                now = datetime.datetime.now()
                hash_input = f"{now.strftime('%Y%m%d%H%M%S')}{strategy_name}"
            file_id = hashlib.md5(hash_input.encode()).hexdigest()[:8]
            print(f"DEBUG: Using generated hash: {file_id}")
        
        # Combine parts
        filename = f"{file_id}_{strategy_name}_{battery_status}"
        print(f"DEBUG: Final filename: {filename}")
        return filename