import sys
import os
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Now import from the root directory
from config import Config

# Reference values from the global Config class - update to new structure
leistung_ladetyp = Config.ChargingInfrastructure.POWER_RATINGS

CONFIG = {
    'STRATEGIES': Config.ChargingInfrastructure.HUB_CONFIG['STRATEGIES'],
    'ladequote': Config.ChargingInfrastructure.HUB_CONFIG['ladequote'],
    'power': Config.ChargingInfrastructure.HUB_CONFIG['power'],
    'pause': Config.ChargingInfrastructure.HUB_CONFIG['pause'],
}