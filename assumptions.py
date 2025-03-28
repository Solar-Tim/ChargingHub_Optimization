"""
ChargingHub Optimization - Business Assumptions

This module contains all business assumptions and constants used across the charging hub optimization pipeline.
"""

class Assumptions:
    """Business assumptions for the charging hub optimization project."""
    
    # Truck types and their properties
    TRUCK_TYPES = {
        '1': {'capacity_kwh': 600, 'max_power_kw': 750, 'probability': 0.093},
        '2': {'capacity_kwh': 720, 'max_power_kw': 750, 'probability': 0.187},
        '3': {'capacity_kwh': 840, 'max_power_kw': 1200, 'probability': 0.289},
        '4': {'capacity_kwh': 960, 'max_power_kw': 1200, 'probability': 0.431}
    }
    
    # Break types
    BREAK_TYPES = {
        'Schnelllader': {'name': 'HPC', 'min_duration_minutes': 45},
        'Nachtlader': {'name': 'NCS', 'min_duration_minutes': 480}
    }
    
    # Driver break requirements
    DRIVER_BREAKS = {
        'DISTANCE_THRESHOLD': 360,  # km - Distance after which a break is required
        'MAX_DISTANCE_SINGLEDRIVER': 4320,  # km - Limit between single and double driver routes
        'TWO_DRIVER_SHORT_BREAKS_BEFORE_LONG': 2  # Number of short breaks before a long break for two drivers
    }
    
    # Energy consumption assumptions
    ENERGY_CONSUMPTION = {
        'KWH_PER_KM': 1.2,  # kWh per km for heavy-duty electric truck
        'SAFETY_BUFFER': 0.1  # 10% safety buffer for SoC
    }
    
    # Grid connection costs
    GRID_CONNECTION = {
        # Capacity fee in €/kW (Baukostenzuschuss)
        'HV_CAPACITY_FEE': 111.14,
        'MV_CAPACITY_FEE': 183.56,
        
        # Substation costs
        'HV_SUBSTATION_COST': 2500000,  # Cost of a new HV substation ~2.5M EUR
        'BASE_TRANSFORMER_COST': 20000,  # Base cost for transformers
        'TRANSFORMER_COST_PER_KW': 200,  # Cost per kW for transformer
        
        # Substation expansion parameters
        'DISTRIBUTION_EXPANSION_FIXED_COST': 500000,
        'TRANSMISSION_EXPANSION_FIXED_COST': 500000
    }
    
    # Cable parameters
    CABLE_PARAMETERS = {
        # Low voltage parameters
        'LV_VOLTAGE': 400,  # V
        'LV_VOLTAGE_DROP_PERCENT': 2.0,
        'LV_POWER_FACTOR': 0.95,
        'LV_CONDUCTIVITY': 56,  # Copper
        
        # Medium voltage parameters
        'MV_VOLTAGE': 20000,  # V
        'MV_VOLTAGE_DROP_PERCENT': 3.0,
        'MV_POWER_FACTOR': 0.90,
        'MV_CONDUCTIVITY': 35,  # Aluminium
        
        # Cable construction costs
        'DIGGING_COST': 34.0,  # Cost of digging per meter (EUR/m)
        'CABLE_HARDWARE_CONNECTION_COST': 930,  # Cost for cable assembly (per piece) - EUR
        'NUMBER_CABLES': 3  # Number of cables in parallel (for MV)
    }