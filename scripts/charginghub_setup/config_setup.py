import sys
import os
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Now import from the root directory
from config import Config

# Reference values from the global Config class
charging_types = Config.CHARGING_TYPES
leistung_ladetyp = {
    charger_type: values['power_kw'] 
    for charger_type, values in charging_types.items()
}

CONFIG = {
    'STRATEGIES': Config.CHARGING_CONFIG['STRATEGY'],
    # T_min: Minimierung der Ladezeit - Kein Lademanagement
    # Konstant: Möglichst konstante Ladeleistung - Minimierung der Netzanschlusslast - Lademanagement
    # Hub: Minimierung der Hub-Lastspitzen - Globale Lastoptimierung - Hub-Level Lademanagement
    'ladequote': Config.CHARGING_CONFIG['ladequote'],  # Ladequote in Prozent
    'power': Config.CHARGING_CONFIG['power'],  # Ladeleistung in Prozent (NCS-HPC-MCS)
    'pause': Config.CHARGING_CONFIG['pause'],  # Pausenzeiten in Minuten (min-max)
}