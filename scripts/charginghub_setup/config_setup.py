import sys
import os
from pathlib import Path
import numpy as np

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Now import from the root directory
from config import Config

# Set random seed from config
np.random.seed(Config.Traffic.Settings.TruckSimulation.RANDOM_SEED)

# Reference values from the global Config class
# Get power ratings from the configuration
leistung_ladetyp = {
    'NCS': Config.ChargingInfrastructure.STATION_TYPES['NCS']['power_kw'],
    'HPC': Config.ChargingInfrastructure.STATION_TYPES['HPC']['power_kw'],
    'MCS': Config.ChargingInfrastructure.STATION_TYPES['MCS']['power_kw'],
}

# Set up config dictionary using values from the global Config
CONFIG = {
    'STRATEGIES': Config.ChargingInfrastructure.HUB_CONFIG['STRATEGIES'],
    'ladequote': Config.ChargingInfrastructure.CHARGING_QUOTAS,
    'power': Config.ChargingInfrastructure.STATION_TYPES,
    'pause': {
        'Schnell': Config.ChargingInfrastructure.CHARGING_TIMES['Schnell'],
        'Nacht': Config.ChargingInfrastructure.CHARGING_TIMES['Nacht'],
    },
    'CHARGER_COUNTS': Config.ChargingInfrastructure.CHARGER_COUNTS,
    'TruckSimulation': {
        'PAUSE_TYPES': Config.Traffic.Settings.TruckSimulation.PAUSE_TYPES,
        'PAUSE_DURATIONS': Config.Traffic.Settings.TruckSimulation.PAUSE_DURATIONS,
        'PAUSENTYP_TO_COLUMN': Config.Traffic.Settings.TruckSimulation.PAUSENTYP_TO_COLUMN
    }
}

# For accessing specific TruckSimulation settings:
PAUSE_TYPES = Config.Traffic.Settings.TruckSimulation.PAUSE_TYPES
PAUSE_DURATIONS = Config.Traffic.Settings.TruckSimulation.PAUSE_DURATIONS
PAUSENTYP_TO_COLUMN = Config.Traffic.Settings.TruckSimulation.PAUSENTYP_TO_COLUMN

# Alternative way to format power string if needed
power_string = '-'.join([str(Config.ChargingInfrastructure.POWER_RATINGS[key]) 
                          for key in ['NCS', 'HPC', 'MCS']])

pause_string = '-'.join([str(Config.ChargingInfrastructure.CHARGING_TIMES[key]) 
                          for key in ['Schnell', 'Nacht']])