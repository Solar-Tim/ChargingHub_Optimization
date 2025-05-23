"""
ChargingHub Optimization - Centralized Configuration

This module contains all configuration parameters for the charging hub optimization pipeline.
"""
import os
from pathlib import Path


class Config:
    """Global configuration parameters for the charging hub optimization project."""
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    CONTINUE_ON_ERROR = False
    FORECAST_YEAR = '2030'
    RESULT_NAMING = {'USE_CUSTOM_ID': True, 'CUSTOM_ID': '999'}

    EXECUTION_FLAGS = {'RUN_TRAFFIC_CALCULATION': True,
        'RUN_CHARGING_HUB_SETUP': True, 'RUN_GRID_OPTIMIZATION': True,
        'RECALCULATE_BREAKS': False, 'RECALCULATE_TOLL_MIDPOINTS': False,
        'RUN_TRUCK_MATCHING': True, 'RUN_HUB_CONFIGURATION': True,
        'RUN_DEMAND_OPTIMIZATION': True, 'USE_DISTANCE_CALCULATION': True,
        'CREATE_PLOT': False, 'CREATE_DISTANCE_MAPS': False,
        'INCLUDE_BATTERY': False, 'USE_MANUAL_CHARGER_COUNT': False,
        'DEBUG_MODE': False}
    CHARGING_CONFIG = {'ALL_STRATEGIES': ['T_min', 'Konstant', 'Hub'],
        'STRATEGY': ['T_min', 'Konstant', 'Hub'], 'ladequote': 0.8, 'power':
        '100-100-100', 'pause': '45-540'}
    MANUAL_CHARGER_COUNT = {'NCS': 4, 'HPC': 6, 'MCS': 2}
    MANUAL_DISTANCES = {'distribution_distance': 1000,
        'transmission_distance': 25000, 'powerline_distance': 500}
    DEFAULT_LOCATION = {'LONGITUDE': 6.778693, 'LATITUDE': 50.928634}
    SPATIAL = {'DEFAULT_CRS': 'EPSG:4326', 'TARGET_CRS': 'EPSG:3857',
        'BUFFER_RADIUS': 10000}

    SCENARIOS = {'TARGET_YEARS': ['2030', '2035', '2040', '2045'], 'R_BEV':
        {'2030': 0.15, '2035': 0.61, '2040': 0.94, '2045': 1}, 'R_TRAFFIC':
        {'2030': 1, '2035': 1.0462, '2040': 1.0549, '2045': 1.1672}}
    BREAKS = {'DISTANCE_THRESHOLD': 360, 'MAX_DISTANCE_SINGLEDRIVER': 4320,
        'RANDOM_RANGE': (0, 0), 'TWO_DRIVER_SHORT_BREAKS_BEFORE_LONG': 2}
    DAY_MAPPING = {'Montag': 'Monday', 'Dienstag': 'Tuesday', 'Mittwoch':
        'Wednesday', 'Donnerstag': 'Thursday', 'Freitag': 'Friday',
        'Samstag': 'Saturday', 'Sonntag': 'Sunday'}
    GERMAN_DAYS = list(DAY_MAPPING.keys())
    TIME = {'WEEKS_PER_YEAR': 52, 'RESOLUTION_MINUTES': 5,
        'SIMULATION_HOURS': 8760, 'WEEK_MINUTES': 10080,
        'TIMESTEPS_PER_DAY': 288, 'TIMESTEPS_PER_WEEK': 2016}
    CSV = {'DEFAULT_SEPARATOR': ';', 'DEFAULT_DECIMAL': ','}
    CHARGING_TYPES = {'NCS': {'power_kw': 100, 'cost': 35000}, 'HPC': {
        'power_kw': 400, 'cost': 110000}, 'MCS': {'power_kw': 1000, 'cost':
        375000}}
    BATTERY_CONFIG = {'COST_PER_KWH': 175, 'COST_PER_KW': 100,
        'MAX_CAPACITY': 99999, 'MAX_POWER': 99999, 'EFFICIENCY': 0.95,
        'MIN_SOC': 0, 'MAX_SOC': 1}
    CAPACITY_FEES = {'HV': 111.14, 'MV': 183.56}
    GRID_CAPACITIES = {'EXISTING_MV': 5500, 'DISTRIBUTION': 15000,
        'TRANSMISSION': 15000, 'HV_LINE': 100000}
    SUBSTATION_CONFIG = {'DISTRIBUTION': {'EXISTING_CAPACITY': 15000,
        'MAX_EXPANSION': 20000, 'EXPANSION_FIXED_COST': 500000},
        'TRANSMISSION': {'EXISTING_CAPACITY': 15000, 'MAX_EXPANSION': 20000,
        'EXPANSION_FIXED_COST': 500000}, 'HV_SUBSTATION_COST': 2500000}
    TRANSFORMER_CONFIG = {'CAPACITIES': [1000, 1250, 1600, 2000, 2500, 3150
        ], 'COSTS': [120000, 145000, 180000, 220000, 270000, 335000]}
    CABLE_CONFIG = {'LV': {'VOLTAGE': 400, 'VOLTAGE_DROP_PERCENT': 2,
        'POWER_FACTOR': 0.95, 'CONDUCTIVITY': 56, 'NUM_DC_CABLES': 1}, 'MV':
        {'VOLTAGE': 20000, 'VOLTAGE_DROP_PERCENT': 3, 'POWER_FACTOR': 0.9,
        'CONDUCTIVITY': 35, 'NUM_CABLES': 3}, 'CONSTRUCTION': {
        'DIGGING_COST': 34, 'HARDWARE_CONNECTION_COST': 930}}
    aluminium_kabel = {'Nennquerschnitt': [16, 25, 35, 50, 70, 95, 120, 150,
        185, 240, 300, 400, 500, 630, 800, 1000, 1200, 1400, 1600, 1800, 
        2000, 2500, 3000, 3200, 3500, 9999], 'Belastbarkeit': [105, 140, 
        195, 237, 282, 319, 352, 396, 455, 510, 564, 634, 710, 800, 880, 
        980, 1080, 1170, 1250, 1320, 1380, 1550, 1700, 1760, 1850, 3000],
        'Kosten': [7.77, 10.62, 12, 15, 20, 26, 30, 35, 40, 48, 55, 70, 85,
        100, 120, 140, 160, 180, 200, 220, 240, 300, 360, 380, 420, 999.99]}
    kupfer_kabel = {'Nennquerschnitt': [0.5, 0.75, 1, 1.5, 2.5, 4, 6, 10, 
        16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 9999],
        'Kosten': [0.5, 0.65, 0.8, 1.1, 1.6, 2.4, 3.5, 5.8, 8.5, 12.8, 17.5,
        24, 32.5, 44, 55, 68, 82, 105, 130, 165, 165]}
    PATHS = {'DATA': os.path.join(PROJECT_ROOT, 'data'), 'RESULTS': os.path
        .join(PROJECT_ROOT, 'results'), 'LOGS': os.path.join(PROJECT_ROOT,
        'logs')}
    TRAFFIC_PATHS = {'INPUT_DIR': os.path.join(PROJECT_ROOT, 'data',
        'traffic', 'raw_data'), 'OUTPUT_DIR': os.path.join(PROJECT_ROOT,
        'data', 'traffic', 'interim_results'), 'FINAL_OUTPUT_DIR': os.path.
        join(PROJECT_ROOT, 'data', 'traffic', 'final_traffic')}
    TRAFFIC_FILES = {'MAUT_TABLE': os.path.join(TRAFFIC_PATHS['INPUT_DIR'],
        'Mauttabelle.xlsx'), 'BEFAHRUNGEN': os.path.join(TRAFFIC_PATHS[
        'INPUT_DIR'], 'Befahrungen_25_1Q.csv'), 'NUTS_DATA': os.path.join(
        TRAFFIC_PATHS['INPUT_DIR'], 'DE_NUTS5000.gpkg'), 'TRAFFIC_FLOW': os
        .path.join(TRAFFIC_PATHS['INPUT_DIR'], '01_Trucktrafficflow.csv'),
        'EDGES': os.path.join(TRAFFIC_PATHS['INPUT_DIR'],
        '04_network-edges.csv'), 'NODES': os.path.join(TRAFFIC_PATHS[
        'INPUT_DIR'], '03_network-nodes.csv'), 'BREAKS_OUTPUT': os.path.
        join(TRAFFIC_PATHS['OUTPUT_DIR'], 'breaks.json'),
        'TOLL_MIDPOINTS_OUTPUT': os.path.join(TRAFFIC_PATHS['OUTPUT_DIR'],
        'toll_midpoints.json'), 'CHARGING_DEMAND': os.path.join(
        TRAFFIC_PATHS['OUTPUT_DIR'], 'charging_demand.json'),
        'FINAL_OUTPUT': os.path.join(TRAFFIC_PATHS['FINAL_OUTPUT_DIR'],
        'laden_mauttabelle.json')}

    @classmethod
    def validate_year(cls, year_value):
        """Validate that the given year exists in the SCENARIOS dictionaries."""
        if year_value not in cls.SCENARIOS['R_BEV']:
            raise ValueError(
                f"Year {year_value} not found in SCENARIOS['R_BEV']")
        if year_value not in cls.SCENARIOS['R_TRAFFIC']:
            raise ValueError(
                f"Year {year_value} not found in SCENARIOS['R_TRAFFIC']")
        return year_value

    @classmethod
    def get_breaks_column(cls, break_type):
        """Return column name for breaks based on break_type and current year."""
        return f'{break_type}_breaks_{cls.FORECAST_YEAR}'

    @classmethod
    def get_charging_column(cls, charging_type, target_year=None):
        """Return column name for charging sessions based on charging_type and year."""
        year_to_use = target_year if target_year else cls.FORECAST_YEAR
        return f'{charging_type}_{year_to_use}'

    @classmethod
    def get_traffic_flow_column(cls):
        """Return the traffic flow column name using the current year."""
        return f'Traffic_flow_trucks_{cls.FORECAST_YEAR}'

    @classmethod
    def generate_result_filename(cls, results=None, strategy=None,
        battery_allowed=None, custom_id=None):
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
        print(
            f'DEBUG: Config.generate_result_filename called with custom_id={custom_id}'
            )
        print(f'DEBUG: Config.RESULT_NAMING={cls.RESULT_NAMING}')
        strategy_name = strategy
        if not strategy_name and results:
            strategy_name = results.get('charging_strategy', 'unknown')
        if battery_allowed is not None:
            battery_status = 'withBat' if battery_allowed else 'noBat'
        else:
            battery_status = 'withBat' if cls.EXECUTION_FLAGS.get(
                'INCLUDE_BATTERY', True) else 'noBat'
        if custom_id:
            file_id = custom_id
            print(f'DEBUG: Using provided custom_id: {custom_id}')
        elif cls.RESULT_NAMING.get('USE_CUSTOM_ID', False):
            file_id = cls.RESULT_NAMING.get('CUSTOM_ID', '000')
            print(f'DEBUG: Using RESULT_NAMING custom_id: {file_id}')
        else:
            if results:
                hash_input = (
                    f"{strategy_name}_{results.get('max_grid_load', 0)}_{results.get('total_cost', 0)}"
                    )
            else:
                now = datetime.datetime.now()
                hash_input = f"{now.strftime('%Y%m%d%H%M%S')}{strategy_name}"
            file_id = hashlib.md5(hash_input.encode()).hexdigest()[:8]
            print(f'DEBUG: Using generated hash: {file_id}')
        filename = f'{file_id}_{strategy_name}_{battery_status}'
        print(f'DEBUG: Final filename: {filename}')
        return filename
