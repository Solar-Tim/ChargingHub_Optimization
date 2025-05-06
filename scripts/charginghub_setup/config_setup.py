import sys
import os
from pathlib import Path

# Add the project root to path to import from parent directory
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, scripts_dir)

# Now import from config (which is in the scripts directory)
from config import Config

# Reference values from the global Config class
charging_types = Config.CHARGING_TYPES
leistung_ladetyp = {
    charger_type: values['power_kw'] 
    for charger_type, values in charging_types.items()
}

CHARGING_CONFIG = {
    'STRATEGIES': Config.CHARGING_CONFIG['STRATEGY'],
    # T_min: Minimierung der Ladezeit - Kein Lademanagement
    # Konstant: Möglichst konstante Ladeleistung - Minimierung der Netzanschlusslast - Lademanagement
    # Hub: Minimierung der Hub-Lastspitzen - Globale Lastoptimierung - Hub-Level Lademanagement
    'ladequote': Config.CHARGING_CONFIG['ladequote'],  # Ladequote in Prozent
    'power': Config.CHARGING_CONFIG['power'],  # Ladeleistung in Prozent (NCS-HPC-MCS)
    'pause': Config.CHARGING_CONFIG['pause'],  # Pausenzeiten in Minuten (min-max)
}

EXECUTION_FLAGS = Config.EXECUTION_FLAGS

# Add time constants
TIME_CONFIG = {
    'WEEK_MINUTES': Config.TIME['WEEK_MINUTES'],
    'TIMESTEP': Config.TIME['RESOLUTION_MINUTES'],
    'TIMESTEPS_PER_DAY': Config.TIME['TIMESTEPS_PER_DAY'],
    'TIMESTEPS_PER_WEEK': Config.TIME['TIMESTEPS_PER_WEEK']
}