############## Input Parameters for the Optimization ##############
from math import inf
import numpy as np
import sys
import os
from data_loading import load_data
# Add the project root to path to import from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import Config

DEFAULT_LOCATION = Config.DEFAULT_LOCATION

# Define charging strategy
# STRATEGY = 'T_min'  # T_min: Minimierung der Ladezeit - Kein Lademanagement
# STRATEGY = 'Konstant'  # Konstant: Möglichst konstante Ladeleistung - Minimierung der Netzanschlusslast - Lademanagement
# STRATEGY = 'Hub'  # Hub: Minimierung der Hub-Lastspitzen - Globale Lastoptimierung - Hub-Level Lademanagement
current_strategy = Config.CHARGING_CONFIG['STRATEGY'][0]

# Load data
load_profile, timestamps = load_data(current_strategy)


debug_mode = True                  # Set to True to enable debug mode for detailed output

use_distance_calculation = True    # Set to False to use manual distances instead

create_plot = True                  # Set to False to disable plot generation of optimization results

create_distance_maps = True        # Set to True to generate maps of distance calculations

include_battery = False              # Toggle for including battery in optimization

use_manual_charger_count = False    # Set to True to use manual charger count instead of optimization

M_value = 1000000  # Big M value for the optimization

existing_mv_connection_cost = 0  # Cost of existing MV connection (EUR) - Hier ist nur die Rede von Kabelkosten, nicht von dem Baukostenzuschuss

# Manual distance values when not using distance calculation
manual_distances = {
    'distribution_distance': 10000,    # Distance to nearest distribution substation (m)
    'transmission_distance': 9999999,   # Distance to nearest transmission substation (m)
    'powerline_distance': 9999999,      # Distance to nearest HV power line (m)
}



# Placeholder for the number of chargers - Wird bei der Optimierung automatisch ermittelt
MCS_count = 5  # Default manual count
HPC_count = 10
NCS_count = 25



# Charger fixed costs (EUR) - Akutell Werte aus Felix MA - Problematisch weil die Charger oft die Gleichrichter mit beinhalten und sie aktuell doppelt bezahlt werden
MCS_cost = 375000  # Cost per MCS charger
HPC_cost = 110000  # Cost per HPC charger
NCS_cost = 35000  # Cost per NCS charger

# Battery parameters
battery_cost_per_kwh = 175    # Battery storage cost per kWh - Burges & Kippelt Cost für 2030
battery_cost_per_kw = 100     # New parameter: Battery power cost per kW - Burges & Kippelt Cost für 2030
battery_capacity_max = 999999    # Maximum battery capacity in kWh
battery_charge_rate_max = 999999 # Maximum charge/discharge rate in kW
battery_efficiency = 0.90      # Round-trip battery efficiency - Burges & Kippelt
battery_min_soc = 0        # Minimum state of charge
battery_max_soc = 1         # Maximum state of charge



# Define capacity fee parameters (€/kW) - Baukostenzuschuss https://www.regionetz.de/fileadmin/regionetz/content/Dokumente/Preisbl%C3%A4tter/2025_Preisblatt_Baukostenzuschuss_oberhalb_der_Niederspannung.pdf
hv_capacity_fee = 111.14   # Based of BKZ from Regionetz OHNE Reduzierung durch Regionetz *0.5 
mv_capacity_fee = 183.56   # Based of BKZ from Regionetz OHNE Reduzierung durch Regionetz *0.5 


# Line capacities (in kW) - in Anlehnung an https://www.regionetz.de/fileadmin/regionetz/content/Dokumente/TAB/TAB_MS_2023_Regionetz.pdf
existing_mv_capacity       = 1500  # 5,5 MW capacity for existing MV line
distribution_substation_capacity = 15000  # 15 MW for distribution substation
transmission_substation_capacity = 15000  # 15 MW for transmission substation
hv_line_capacity           = 100000  # 100 MW for HV line and a new substation

# Substation expansion parameters - Unsicher ab wann die Erweiterung notwendig ist
distribution_existing_capacity = 2000  # Initial available capacity (kW)
distribution_max_expansion = 5000      # Maximum additional expansion (kW)
transmission_existing_capacity = 10000 # Initial available capacity (kW)
transmission_max_expansion = 10000     # Maximum additional expansion (kW)
distribution_expansion_fixed_cost = 500000  # Fixed cost for expanding distribution substation (EUR)
transmission_expansion_fixed_cost = 500000 # Fixed cost for expanding transmission substation (EUR)

# HV Substation Cost estimate - Fixe Annahme auf Basis von Omexon
HV_Substation_cost = 2500000 # Cost of a new HV substation ~2.5M EUR

# Grid connection cost (EUR/kW for connectivity) - Nicht genutzt aber ein guter Daumenwert zur Orientierung
basecost_transformer = 20000    # Base transformer cost 1000kW
cost_transformer_perkW = 200    # Cost per kW for transformer

# === Define discrete transformer options in structured dictionary format ===
transformers = {
    "Kapazität": [
        1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 
        10000, 12500, 16000, 20000, 25000, 31500, 40000, 50000
    ],
    "Kosten": [
        220000,    # 1000 kW: 20000*1 + 200*1000 = 220000 €
        273600,    # 1250 kW: 20000*1.18 + 200*1250 = 273600 €
        338261,    # 1600 kW: 20000*1.44 + 200*1600 = 338261 €
        407568,    # 2000 kW: 20000*1.68 + 200*2000 = 407568 €
        493095,    # 2500 kW: 20000*1.97 + 200*2500 = 493095 €
        600236,    # 3150 kW: 20000*2.33 + 200*3150 = 600236 €
        735321,    # 4000 kW: 20000*2.83 + 200*4000 = 735321 €
        886797,    # 5000 kW: 20000*3.43 + 200*5000 = 886797 €
        1096542,   # 6300 kW: 20000*4.18 + 200*6300 = 1096542 €
        1349608,   # 8000 kW: 20000*5.12 + 200*8000 = 1349608 €
        1642456,   # 10000 kW: 20000*6.21 + 200*10000 = 1642456 €
        1987088,   # 12500 kW: 20000*7.44 + 200*12500 = 1987088 €
        2457062,   # 16000 kW: 20000*9.29 + 200*16000 = 2457062 €
        2988281,   # 20000 kW: 20000*11.44 + 200*20000 = 2988281 €
        3618314,   # 25000 kW: 20000*13.91 + 200*25000 = 3618314 €
        4406397,   # 31500 kW: 20000*17.03 + 200*31500 = 4406397 €
        5425984,   # 40000 kW: 20000*21.30 + 200*40000 = 5425984 €
        6600811    # 50000 kW: 20000*26.00 + 200*50000 = 6600811 €
    ]
}

# For compatibility with existing code:
transformer_capacities = np.array(transformers["Kapazität"])
transformer_costs = np.array(transformers["Kosten"])


# Time parameters
time_resolution = 5          # Time resolution in minutes
simulation_period = 8760      # Hours in a year


################################ Others ################################


# Low voltage cable parameters
lv_voltage = 400  # V
lv_voltage_drop_percent = 2.0
lv_power_factor = 0.95
lv_conductivity = 56  # Copper

# Medium voltage cable parameters
mv_voltage = 20000  # V
mv_voltage_drop_percent = 3.0
mv_power_factor = 0.90
mv_conductivity = 35  # Aluminium

# MV-Cable Construction Cost
digging_cost = 34.0  # Cost of digging per meter (EUR/m)
cable_hardware_connection_cost = 930  # Kosten für die Kabelmontage (pro Stück) - EUR
number_cables = 3  # Number of cables in parallel (for MV)

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
        500.00   # 9999.0 mm²: placeholder for larger sizes
    ]
}

# Internal LV cabling parameters
charger_distance_increment = 4  # Distance increment between charger positions (m)
mcs_power_kw = 350  # Power rating of MCS chargers (kW)
hpc_power_kw = 150  # Power rating of HPC chargers (kW)
ncs_power_kw = 22   # Power rating of NCS chargers (kW)

leistung_ladetyp = {
    'NCS': 100,
    'HPC': 400,
    'MCS': 1000
} # Max Ladeleistung pro Ladepunkt in kW
