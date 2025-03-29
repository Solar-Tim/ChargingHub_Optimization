import sys
import os
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Now import from the root directory
from config import Config

# Reference values from the global Config class
leistung_ladetyp = Config.LEISTUNG_LADETYP

CONFIG = {
    'STRATEGIES': Config.CHARGING_CONFIG['STRATEGIES'],
    # T_min: Minimierung der Ladezeit - Kein Lademanagement
    # Konstant: Möglichst konstante Ladeleistung - Minimierung der Netzanschlusslast - Lademanagement
    # Hub: Minimierung der Hub-Lastspitzen - Globale Lastoptimierung - Hub-Level Lademanagement
    'ladequote': Config.CHARGING_CONFIG['ladequote'],  # Ladequote in Prozent
    'power': Config.CHARGING_CONFIG['power'],  # Ladeleistung in Prozent (NCS-HPC-MCS)
    'pause': Config.CHARGING_CONFIG['pause'],  # Pausenzeiten in Minuten (min-max)
}