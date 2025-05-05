import sys
import os
from gurobipy import Model, GRB, quicksum
import pandas as pd
import time
import json
import logging
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

# Add the project root and scripts directory to the path first
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
project_root = os.path.abspath(os.path.join(scripts_dir, '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, scripts_dir)
sys.path.insert(0, os.path.dirname(__file__))

# Now import from config_setup
from scripts.charginghub_setup.config_setup import *

# Create a working copy of the config that can be modified
CONFIG = CHARGING_CONFIG.copy()

logging.basicConfig(filename='logs.log', level=logging.DEBUG, format='%(asctime)s; %(levelname)s; %(message)s')

def datetime_to_iso(dt_obj):
    """Convert datetime objects to ISO 8601 format strings"""
    if isinstance(dt_obj, pd.Timestamp):
        return dt_obj.isoformat()
    return str(dt_obj)

def validate_truck_data(df):
    """Validate and standardize truck data"""
    # Map JSON structure to expected columns
    column_mapping = {
        'id': 'Nummer',
        'arrival_day': 'Tag',
        'arrival_time_minutes': 'Ankunftszeit_total',
        'pause_duration_minutes': 'Pausenlaenge',
        'assigned_charger': 'Ladesäule',
        'initial_soc': 'SOC',
        'capacity_kwh': 'Kapazitaet',
        'max_power_kw': 'Max_Leistung',
        'target_soc': 'SOC_Target',
        'load_status': 'load_status'
    }
    
    # Rename columns that exist in the DataFrame
    for json_col, req_col in column_mapping.items():
        if json_col in df.columns:
            df.rename(columns={json_col: req_col}, inplace=True)
    
    return df

def modellierung():
    """
    Optimizes the charging hub for a specific week using configuration from charging_config_base.json file.
    The optimization prioritizes using trucks data from this file if available.
    
    Returns:
        None: Results are saved to a JSON file
    """
    logging.info(f"Optimizing for scenario {CONFIG['STRATEGIES']}")
    print(f"Optimizing for scenario {CONFIG['STRATEGIES']}")
 
    # Extract parameters from configuration
    dict_config = {
        'ladequote': CONFIG['ladequote'],
        'power': CONFIG['power'],
        'pause': CONFIG['pause']
    }
    logging.info(f"Using configuration parameters: {dict_config}")

    # Get script directory and root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir))
    
    logging.info(f"Script directory: {script_dir}")
    logging.info(f"Root directory: {root_dir}")
    print(f"Script directory: {script_dir}")
    print(f"Root directory: {root_dir}")
    
    # ------------------------------
    # Load charging hub configuration from JSON - this is our primary data source
    # ------------------------------
    ladehub_filepath = os.path.join(root_dir, 'data', 'load', 'truckdata', 'charging_config_base.json')
    
    logging.info(f"Checking charging config path: {ladehub_filepath}")
    print(f"Checking path: {ladehub_filepath}")
    


    try:
        logging.info(f"Loading charging hub config from: {ladehub_filepath}")
        print(f"Loading charging hub config from: {ladehub_filepath}")
        with open(ladehub_filepath, 'r') as f:
            charging_config = json.load(f)
        logging.info(f"Successfully loaded charging hub config")
        print(f"Successfully loaded charging hub config")
            
        # Try to extract truck data from charging_config_base.json
        if "trucks" in charging_config and charging_config["trucks"]:
            truck_data_from_config = {"trucks": charging_config["trucks"]}
            logging.info(f"Using truck data from charging_config_base.json - {len(charging_config['trucks'])} trucks found")
            print(f"Using truck data from charging_config_base.json - {len(charging_config['trucks'])} trucks found")
        else:
            truck_data_from_config = None
            logging.warning("No truck data found in charging_config_base.json")
            print("WARNING: No truck data found in charging_config_base.json")
                
    except Exception as e:
        logging.error(f"Error loading charging hub config: {e}")
        print(f"ERROR loading charging hub data: {e}")

    
    # ------------------------------
    # Only load truck data from separate file if not found in charging_config_base.json
    # ------------------------------
    if truck_data_from_config is None:
        lkw_filepath = os.path.join(root_dir, 'data', 'load', 'truckdata', 'eingehende_lkws_ladesaeule.json')
        
        logging.info(f"Checking truck data path: {lkw_filepath}")
        print(f"Checking path: {lkw_filepath}")
        
        if not os.path.exists(lkw_filepath):
            logging.error("Could not find truck data file and no truck data in charging config")
            print("ERROR: Could not find truck data file and no truck data in charging config")
            return None
        
        # Load truck data from separate file
        try:
            logging.info(f"Loading truck data from: {lkw_filepath}")
            print(f"Loading truck data from: {lkw_filepath}")
            with open(lkw_filepath, 'r') as f:
                truck_data = json.load(f)
            
            print(f"Successfully loaded truck data. Found {len(truck_data['trucks'])} trucks.")
            logging.info(f"Successfully loaded truck data from external file.")
        except Exception as e:
            logging.error(f"Error loading truck data: {e}")
            print(f"ERROR loading truck data: {e}")
            return None
    else:
        # Use truck data from charging_config_base.json
        truck_data = truck_data_from_config
    
    # Convert truck list to DataFrame
    df_lkw = pd.DataFrame(truck_data["trucks"])
    
    # Validate and standardize the truck data columns
    df_lkw = validate_truck_data(df_lkw)
    
    if df_lkw.empty:
        logging.error("Truck data is empty after validation")
        print("ERROR: Truck data is empty after validation")
        return None
    
        # *** UPDATED: Account for day offset ***
    # Update arrival times: add day offset (in minutes) to the arrival_time_minutes field.
    df_lkw['Ankunftszeit_total'] = (df_lkw['Tag'] - 1) * 1440 + df_lkw['Ankunftszeit_total']
    
    
    # Add after loading truck data
    day_counts = df_lkw['Tag'].value_counts().sort_index()
    print(f"Truck distribution by day: {day_counts.to_dict()}")
    
    # Extract charging station counts from JSON
    max_saeulen = {
        'NCS': charging_config["charging_stations"]["NCS"]["count"],
        'HPC': charging_config["charging_stations"]["HPC"]["count"],
        'MCS': charging_config["charging_stations"]["MCS"]["count"]
    }
    
    # Calculate charging power based on scenario
    power_values = CONFIG['power'].split('-')
    ladeleistung = {
        'NCS': int(int(power_values[0]) / 100 * leistung_ladetyp['NCS']),
        'HPC': int(int(power_values[1]) / 100 * leistung_ladetyp['HPC']),
        'MCS': int(int(power_values[2]) / 100 * leistung_ladetyp['MCS'])
    }
    
    # -------------------------------------
    # Vorbereitung: Lastgang-Arrays
    # -------------------------------------
    WEEK_MINUTES = TIME_CONFIG['WEEK_MINUTES']  # 7 days * 24 hours * 60 minutes
    TIMESTEP = TIME_CONFIG['TIMESTEP']          # 5 minutes per timestep
    N = WEEK_MINUTES // TIMESTEP                # 10080 / 5 = 2016 timesteps for one week
    
    # -------------------------------------
    # Eine Woche = 7 Tage = 2016 Zeitstufen (7*24*60/5)
    # -------------------------------------
    T_7 = TIME_CONFIG['TIMESTEPS_PER_WEEK']     # Timesteps in a week (288 per day * 7 days)
    
    Delta_t = TIMESTEP / 60.0

    # Vorbefüllen der Liste mit allen Zeitpunkten und Strategien - nur für eine Woche
    rows = []
    row_index = {}  # Pre-initialize empty dict for clarity
    
    for strategie_idx, strategie in enumerate(CONFIG['STRATEGIES']):
        for time_idx in range(N):
            row_dict = {
                'Tag':                  1 + (time_idx // 288) % 7,
                'Zeit':                 (time_idx * TIMESTEP) % 1440,
                'Leistung_Total':       0.0,
                'Leistung_Max_Total':   0.0,
                'Leistung_NCS':         0.0,
                'Leistung_HPC':         0.0,
                'Leistung_MCS':         0.0,
                'Ladestrategie':        strategie,
                'Ladequote':            0.0,
            }
            rows.append(row_dict)
            
            # Store index with proper key structure
            row_index[(strategie, time_idx)] = len(rows) - 1

    # Verify index mapping is correct
    logging.info(f"Created rows: {len(rows)}, Index mapping entries: {len(row_index)}")

    dict_lkw_lastgang = {
        'LKW_ID': [],
        'Tag': [],
        'Zeit': [],
        'Ladetyp': [],
        'Ladestrategie': [],
        'Ladezeit': [],
        'Leistung': [],
        'SOC': [],
        'Max_Leistung': [],
        'Pplus': [],
        'Pminus': [],
        'z': []
    }

    # Calculate arrival and departure indices with the updated arrival times
    df_lkw['t_a'] = (df_lkw['Ankunftszeit_total'] // TIMESTEP).astype(int)
    df_lkw['t_d'] = ((df_lkw['Ankunftszeit_total'] + df_lkw['Pausenlaenge'] - TIMESTEP) // TIMESTEP).astype(int)

    # Bound checking to ensure we stay within T_7
    df_lkw['t_a'] = df_lkw['t_a'].clip(0, T_7-1)
    df_lkw['t_d'] = df_lkw['t_d'].clip(0, T_7-1)
    
    if df_lkw.empty:
        logging.warning("Filtered truck data is empty after calculating arrival/departure times")
        return None

    t_in     = df_lkw['t_a'].tolist()        
    t_out    = df_lkw['t_d'].tolist()
    l        = df_lkw['Ladesäule'].tolist()
    SOC_A    = df_lkw['SOC'].tolist()
    kapaz    = df_lkw['Kapazitaet'].tolist()
    maxLKW   = df_lkw['Max_Leistung'].tolist()
    SOC_req  = df_lkw['SOC_Target'].tolist()

    # Leistungsskalierung
    power_values = CONFIG['power'].split('-')
    if len(power_values) >= 1:
        # Use first power value (NCS) as truck power scaling
        lkw_leistung_skalierung = float(power_values[0]) / 100
    else:
        lkw_leistung_skalierung = 1.0
        logging.warning("No power values found in CONFIG, using default scaling of 1.0")

    max_lkw_leistung = [m * lkw_leistung_skalierung for m in maxLKW]
    E_req = [kapaz[i] * (SOC_req[i] - SOC_A[i]) for i in range(len(df_lkw))]
    I = len(df_lkw)

    # -------------------------------------
    # Strategien p_max / p_min
    # -------------------------------------
    for strategie in CONFIG['STRATEGIES']:
        # Neues Gurobi-Modell
        model = Model("Ladehub_Optimierung")
        model.setParam('OutputFlag', 0)

        # Variablen
        P, Pplus, Pminus = {}, {}, {}
        P_max_i, P_max_i_2, SoC, z = {}, {}, {}, {}

        for i in range(I):
            for t_step in range(t_in[i], t_out[i] + 1):
                
                P[(i,t_step)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS)

                Pplus[(i,t_step)]  = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
                Pminus[(i,t_step)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
                P_max_i[(i,t_step)]   = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
                P_max_i_2[(i,t_step)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
                z[(i,t_step)] = model.addVar(vtype=GRB.BINARY)

            for t_step in range(t_in[i], t_out[i] + 2):
                SoC[(i,t_step)] = model.addVar(lb=0, ub=1, vtype=GRB.CONTINUOUS)

        # CONSTRAINTS
        # 1) Energiebedarf
        for i in range(I):
            model.addConstr(quicksum(P[(i, t_step)]*Delta_t 
                                     for t_step in range(t_in[i], t_out[i]+1)) <= E_req[i])

        # 2) SOC-Fortschreibung
        for i in range(I):
            model.addConstr(SoC[(i, t_in[i])] == SOC_A[i])
            for t_step in range(t_in[i], t_out[i]+1):
                model.addConstr(
                    SoC[(i, t_step+1)] == SoC[(i, t_step)] + P[(i, t_step)] * Delta_t / kapaz[i]
                )

        # 3) Ladekurven
        for i in range(I):
            for t_step in range(t_in[i], t_out[i]+1):
                ml = max_lkw_leistung[i]
                model.addConstr(P_max_i[(i, t_step)]   == (-0.177038*SoC[(i,t_step)] + 0.970903)*ml)
                model.addConstr(P_max_i_2[(i,t_step)] == (-1.51705*SoC[(i,t_step)] + 1.6336)*ml)

                model.addConstr(Pplus[(i,t_step)]  <= P_max_i[(i,t_step)]   * z[(i,t_step)])
                model.addConstr(Pminus[(i,t_step)] <= P_max_i[(i,t_step)]   * (1 - z[(i,t_step)]))
                model.addConstr(Pplus[(i,t_step)]  <= P_max_i_2[(i,t_step)] * z[(i,t_step)])
                model.addConstr(Pminus[(i,t_step)] <= P_max_i_2[(i,t_step)] * (1 - z[(i,t_step)]))

        # 4) Leistungsbegrenzung Ladesäulentyp
        for i in range(I):
            typ = l[i]
            P_max_l = ladeleistung[typ]
            for t_step in range(t_in[i], t_out[i]+1):
                model.addConstr(Pplus[(i,t_step)]  <= z[(i,t_step)] * P_max_l)
                model.addConstr(Pminus[(i,t_step)] <= (1 - z[(i,t_step)]) * P_max_l)

        # 6) Kopplungsbedingungen (P = Pplus - Pminus, z monoton steigend)
        for i in range(I):
            for t_step in range(t_in[i], t_out[i]+1):
                model.addConstr(P[(i,t_step)] == Pplus[(i,t_step)] - Pminus[(i,t_step)])
            for t_step in range(t_in[i], t_out[i]):
                model.addConstr(z[(i, t_step+1)] >= z[(i, t_step)])
                

        # -------------------------------------
        # Zielfunktion
        # -------------------------------------

        if strategie == "T_min":
            obj_expr = quicksum(((1/(t+1)) * (Pplus[(i, t)])) - (t * Pminus[(i, t)]) 
                                for i in range(I) 
                                for t in range(t_in[i], t_out[i]+1))

        elif strategie == "Konstant":
            # Hilfsvariablen für Leistungsänderungen zwischen Zeitschritten
            delta = {}
            for i in range(I):
                for t_step in range(t_in[i], t_out[i]):
                    # Variable für die absolute Differenz zwischen aufeinanderfolgenden Zeitschritten
                    delta[(i,t_step)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"delta_{i}_{t_step}")
                    # Berechnung der absoluten Differenz zwischen aufeinanderfolgenden Leistungswerten
                    model.addConstr(delta[(i,t_step)] >= P[(i,t_step+1)] - P[(i,t_step)])
                    model.addConstr(delta[(i,t_step)] >= P[(i,t_step)] - P[(i,t_step+1)])
            
            # Extrem hohe Gewichtung für die Energiemaximierung, um absolute Priorität zu gewährleisten
            M_energy = 1000000  # Sehr hoher Gewichtungsfaktor
            
            # Zielfunktion: Hierarchisches Modell mit verbessertem Range-Handling
            obj_expr = 0
            for i in range(I):
                # Primary objective: maximize energy
                for t in range(t_in[i], t_out[i] + 1):
                    obj_expr += M_energy * Pplus[(i, t)]
                
                # Secondary objective: minimize power fluctuations
                for t_step in range(t_in[i], t_out[i]):
                    obj_expr -= delta[(i, t_step)]

        elif strategie == "Hub":
            # Hub-Optimierungsstrategie: Minimiert Lastspitzen über den gesamten Hub
            # 1. Definiere Variable für die Spitzenlast (peak load) im Hub
            peak_load = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="peak_load")
            
            # 2. Berechne die Gesamtlast zu jedem Zeitschritt
            hub_load = {}
            for t_step in range(T_7):
                # Alle aktiven LKWs zu dieser Zeit
                active_trucks = [i for i in range(I) if t_in[i] <= t_step <= t_out[i]]
                if active_trucks:
                    # Füge temporäre Variable für die Gesamtlast zu diesem Zeitpunkt hinzu
                    hub_load[t_step] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"hub_load_{t_step}")
                    
                    # Die Gesamtlast ist die Summe der Leistungen aller aktiven LKWs
                    model.addConstr(hub_load[t_step] == 
                                   quicksum(Pplus[(i, t_step)] + Pminus[(i, t_step)] 
                                           for i in active_trucks))
                    
                    # Die Spitzenlast muss größer oder gleich jeder Gesamtlast sein
                    model.addConstr(peak_load >= hub_load[t_step])
            
            # 3. Parametrierung der Zielfunktion
            M_energy = 1000000  # Hoher Gewichtungsfaktor für Energiemaximierung
            gamma = 10000     # Gewichtungsfaktor für Minimierung der Spitzenlast
            
            # 4. Zielfunktion: Maximiere Energie und minimiere Spitzenlast
            obj_expr = 0
            
            # Primäres Ziel: Maximierung der Energielieferung
            for i in range(I):
                for t in range(t_in[i], t_out[i] + 1):
                    obj_expr += M_energy * Pplus[(i, t)]
            
            # Sekundäres Ziel: Minimierung der Spitzenlast
            obj_expr -= gamma * peak_load
            
            # 5. Logging und Debugging
            logging.info(f"Optimizing with Hub strategy - minimizing peak load")
            print(f"Optimizing with Hub strategy - minimizing peak load")

        model.setObjective(obj_expr, GRB.MAXIMIZE)
        model.optimize()
        
        # -------------------------------------
        # Ergebnisse verarbeiten
        # -------------------------------------
        if model.Status == GRB.OPTIMAL:
            # Ladequote in dieser Woche
            list_volladungen = []
            for i in range(I):
                if SoC[(i, t_out[i]+1)].X >= SOC_req[i] - 0.01:
                    list_volladungen.append(1)
                else:
                    list_volladungen.append(0)
            ladequote_week = sum(list_volladungen) / len(list_volladungen)
            
            # Check if charging quota is below target due to charger constraints
            target_quota = float(CONFIG['ladequote'])
            if EXECUTION_FLAGS.get('USE_MANUAL_CHARGER_COUNT', False) and ladequote_week < target_quota:
                logging.warning(f"Strategy {strategie}: Achieved charging quota ({ladequote_week:.3f}) is below target ({target_quota:.3f}) due to charger count constraints.")
                print(f"WARNING: Strategy {strategie}: Achieved charging quota ({ladequote_week:.3f}) is below target ({target_quota:.3f}) due to charger count constraints.")
            # Gesamtkosten
            if strategie == 'T_min':
                print(f"[Strategie={strategie}] Lösung OK. Ladequote: {ladequote_week:.3f}, Anzahl LKW: {len(df_lkw)}")
            elif strategie == 'Konstant':
                print(f"[Strategie={strategie}] Lösung OK. Ladequote: {ladequote_week:.3f}, Anzahl LKW: {len(df_lkw)}")
            elif strategie == 'Hub':
                # Get the peak load value from the model
                peak_load_value = peak_load.X if model.Status == GRB.OPTIMAL else "N/A"
                print(f"[Strategie={strategie}] Lösung OK. Ladequote: {ladequote_week:.3f}, Anzahl LKW: {len(df_lkw)}, Peak Load: {peak_load_value:.2f} kW")

            
            # Lastgang: direkt in rows eintragen
            for t_step in range(T_7):
                sum_p_total = 0.0
                sum_p_total_max = 0.0
                sum_p_ncs = 0.0
                sum_p_hpc = 0.0
                sum_p_mcs = 0.0
                for i in range(I):
                    if t_in[i] <= t_step <= t_out[i]:
                        val = P[(i, t_step)].X
                        sum_p_total += val
                        sum_p_total_max += ladeleistung[l[i]]
                        if l[i] == 'NCS':
                            sum_p_ncs += val
                        elif l[i] == 'HPC':
                            sum_p_hpc += val
                        elif l[i] == 'MCS':
                            sum_p_mcs += val
                
                # Direktes Eintragen in rows mit dem entsprechenden Index
                # Verify key exists before accessing
                if (strategie, t_step) in row_index:
                    row_idx = row_index[(strategie, t_step)]
                    rows[row_idx]['Leistung_Total'] += sum_p_total
                    rows[row_idx]['Leistung_Max_Total'] += sum_p_total_max
                    rows[row_idx]['Leistung_NCS'] += sum_p_ncs
                    rows[row_idx]['Leistung_HPC'] += sum_p_hpc
                    rows[row_idx]['Leistung_MCS'] += sum_p_mcs
                    rows[row_idx]['Ladequote'] = ladequote_week  # Überschreiben, nicht addieren
                else:
                    logging.warning(f"Missing index for (strategie={strategie}, t_step={t_step})")

            for i in range(I):
                t_charging = 0
                for t in range(T_7):   
                    if t_in[i] <= t <= t_out[i]+1:
                        dict_lkw_lastgang['LKW_ID'].append(df_lkw.iloc[i]['Nummer'])
                        dict_lkw_lastgang['Tag'].append(df_lkw.iloc[i]['Tag'] % 7)
                        dict_lkw_lastgang['Zeit'].append((t * 5) % 1440)
                        dict_lkw_lastgang['Ladestrategie'].append(strategie)
                        dict_lkw_lastgang['Ladetyp'].append(l[i])
                        dict_lkw_lastgang['Ladezeit'].append(t_charging)
                        t_charging += 5
                        if t > t_out[i]:
                            dict_lkw_lastgang['Leistung'].append(None)
                            dict_lkw_lastgang['Pplus'].append(None)
                            dict_lkw_lastgang['Pminus'].append(None)
                            dict_lkw_lastgang['SOC'].append(SoC[(i, t_out[i]+1)].X)
                            dict_lkw_lastgang['z'].append(None)
                            dict_lkw_lastgang['Max_Leistung'].append(None)
                            continue
                        else:       
                            dict_lkw_lastgang['Max_Leistung'].append(min(ladeleistung[l[i]], max_lkw_leistung[i]))
                            dict_lkw_lastgang['z'].append(z[(i, t)].X)
                            dict_lkw_lastgang['Pplus'].append(Pplus[(i, t)].X)
                            dict_lkw_lastgang['Pminus'].append(Pminus[(i, t)].X)
                            dict_lkw_lastgang['Leistung'].append(P[(i, t)].X)
                            dict_lkw_lastgang['SOC'].append(SoC[(i, t)].X)
        else:
            logging.error(f"No optimal solution found for strategy {strategie}")
            print(f"Keine optimale Lösung gefunden für Strategie {strategie}.")

    # -------------------------------------
    # DataFrames bauen und speichern
    # -------------------------------------
    # 1) Lastgang-DF je Strategie
    df_lastgang = pd.DataFrame(rows)

    # 2) LKW-Lastgang als DataFrame
    df_lkw_lastgang_df = pd.DataFrame(dict_lkw_lastgang)
    df_lkw_lastgang_df.sort_values(['LKW_ID', 'Ladestrategie', 'Zeit'], inplace=True)
    
    # Create a simplified JSON structure focused on the load profile
    # Convert dataframe to list of records for the lastgang part
    lastgang_records = []
    load_detailed_by_time = {}  # Initialize dictionary for detailed load tracking
    for record in df_lastgang.to_dict(orient='records'):
        # Process only the essential fields for the load profile
        processed_record = {
            'Tag': record['Tag'],
            'Zeit': record['Zeit'],
            'Leistung_Total': record['Leistung_Total'],
            'Leistung_NCS': record['Leistung_NCS'],
            'Leistung_HPC': record['Leistung_HPC'],
            'Leistung_MCS': record['Leistung_MCS'],
            'Ladequote': record['Ladequote']
        }
        lastgang_records.append(processed_record)
        
        # Track individual power types for detailed CSV
        time_minutes = (record['Tag'] - 1) * 1440 + record['Zeit']
        if time_minutes not in load_detailed_by_time:
            load_detailed_by_time[time_minutes] = {
                'Leistung_Total': record['Leistung_Total'],
                'Leistung_NCS': record['Leistung_NCS'],
                'Leistung_HPC': record['Leistung_HPC'],
                'Leistung_MCS': record['Leistung_MCS']
            }
        else:
            # Accumulate values for same time step (across strategies)
            load_detailed_by_time[time_minutes]['Leistung_Total'] += record['Leistung_Total']
            load_detailed_by_time[time_minutes]['Leistung_NCS'] += record['Leistung_NCS']
            load_detailed_by_time[time_minutes]['Leistung_HPC'] += record['Leistung_HPC'] 
            load_detailed_by_time[time_minutes]['Leistung_MCS'] += record['Leistung_MCS']
    
    # Build the simplified output structure focusing on the load profile
    output_data = {
        "metadata": {
            "config": CONFIG,
            "charging_stations": {
                "NCS": {"count": max_saeulen['NCS'], "power_kw": ladeleistung['NCS']},
                "HPC": {"count": max_saeulen['HPC'], "power_kw": ladeleistung['HPC']},
                "MCS": {"count": max_saeulen['MCS'], "power_kw": ladeleistung['MCS']}
            },
            "generated_at": datetime.now().isoformat(),
            "data_source": "charging_config_base.json" if truck_data_from_config else "eingehende_lkws_ladesaeule.json",
            "manual_charger_count": EXECUTION_FLAGS.get('USE_MANUAL_CHARGER_COUNT', False),
            "target_charging_quota": float(CONFIG['ladequote']),
            "achieved_charging_quota": ladequote_week
        }
    }

    # Create directory structure if needed (changed to use load folder)
    json_dir = os.path.join(root_dir, 'data', 'load')
    os.makedirs(json_dir, exist_ok=True)

    # Define the output JSON filename
    # Create a filename that includes the strategy
    strategies_string = "_".join(CONFIG['STRATEGIES'])
    json_filename = f'metadata_charginghub_{strategies_string}.json'
    json_filepath = os.path.join(json_dir, json_filename)

    # Save the simplified data to a pretty-printed JSON file
    logging.info(f"Saving simplified load profile data to load folder")
    print(f"Saving simplified load profile data to load folder...")
    
    try:
        with open(json_filepath, 'w', encoding='utf-8') as json_file:
            json.dump(output_data, json_file, indent=2)
        logging.info(f"Successfully saved load profile data to: {json_filepath}")
        print(f"Successfully saved load profile data to: {json_filepath}")
    except Exception as e:
        logging.error(f"Error saving JSON file: {e}")
        print(f"ERROR: Failed to save JSON data: {e}")
    
    # Create a CSV file with the same structure as lastgang_demo.csv
    try:
        # Create a CSV filename that includes the strategy
        csv_filename = f'lastgang_{strategies_string}.csv'
        csv_filepath = os.path.join(json_dir, csv_filename)
        
        logging.info(f"Creating load profile CSV file")
        print(f"Creating load profile CSV file...")
        
        # Create a DataFrame with exactly 2016 entries (full week in 5-min steps)
        # Initialize with zeros
        csv_df = pd.DataFrame({
            'time (5min steps)': range(0, 10080, 5),  # 0, 5, 10, ..., 10075
            'Last': [0.0] * T_7  # Initialize all values with 0
        })
        
        # Create a dictionary to store load values by timestep
        load_by_time = {}
        
        # Process the load records to populate the dictionary
        for record in lastgang_records:
            # Calculate absolute time in minutes
            time_minutes = (record['Tag'] - 1) * 1440 + record['Zeit']
            # Store the load value for this timestep - handle multiple entries for same time
            # For accumulating demand across strategies
            if time_minutes in load_by_time:
                load_by_time[time_minutes] += record['Leistung_Total']
            else:
                load_by_time[time_minutes] = record['Leistung_Total']
        
        # Update the load values in our DataFrame
        for time_step, load_value in load_by_time.items():
            if 0 <= time_step < 10080:  # Ensure time step is within range
                # Find the row index in our DataFrame that corresponds to this time step
                idx = time_step // 5
                if idx < len(csv_df):
                    csv_df.loc[idx, 'Last'] = load_value
        
        # Write to CSV with semicolon separator
        csv_df.to_csv(csv_filepath, sep=';', index=False)
        
        logging.info(f"Successfully saved load profile CSV to: {csv_filepath}")
        print(f"Successfully saved load profile CSV to: {csv_filepath}")
    except Exception as e:
        logging.error(f"Error saving CSV file: {e}")
        print(f"ERROR: Failed to save CSV data: {e}")
    
    # Create a detailed CSV file with power breakdown by charging type
    try:
        # Create a detailed CSV filename that includes the strategy
        detailed_csv_filename = f'lastgang_detailed_{strategies_string}.csv'
        detailed_csv_filepath = os.path.join(json_dir, detailed_csv_filename)
        
        logging.info(f"Creating detailed load profile CSV file")
        print(f"Creating detailed load profile CSV file...")
        
        # Create a DataFrame with exactly 2016 entries (full week in 5-min steps)
        # Initialize with zeros
        detailed_csv_df = pd.DataFrame({
            'time (5min steps)': range(0, 10080, 5),  # 0, 5, 10, ..., 10075
            'Last': [0.0] * T_7,               # Total load
            'Last_NCS': [0.0] * T_7,           # NCS charger load
            'Last_HPC': [0.0] * T_7,           # HPC charger load
            'Last_MCS': [0.0] * T_7            # MCS charger load
        })
        
        # Update the load values in our detailed DataFrame
        for time_step, load_details in load_detailed_by_time.items():
            if 0 <= time_step < 10080:  # Ensure time step is within range
                # Find the row index in our DataFrame that corresponds to this time step
                idx = time_step // 5
                if idx < len(detailed_csv_df):
                    detailed_csv_df.loc[idx, 'Last'] = load_details['Leistung_Total']
                    detailed_csv_df.loc[idx, 'Last_NCS'] = load_details['Leistung_NCS']
                    detailed_csv_df.loc[idx, 'Last_HPC'] = load_details['Leistung_HPC']
                    detailed_csv_df.loc[idx, 'Last_MCS'] = load_details['Leistung_MCS']
        
        # Write to CSV with semicolon separator
        detailed_csv_df.to_csv(detailed_csv_filepath, sep=';', index=False)
        
        logging.info(f"Successfully saved detailed load profile CSV to: {detailed_csv_filepath}")
        print(f"Successfully saved detailed load profile CSV to: {detailed_csv_filepath}")
    except Exception as e:
        logging.error(f"Error saving detailed CSV file: {e}")
        print(f"ERROR: Failed to save detailed CSV data: {e}")
    
    return None


def process_single_strategy(strategy, config):
    # Process a single strategy
    # Return results
    global CONFIG  # Declare at the beginning of the function
    print(f"Processing strategy: {strategy}")
    logging.info(f"Processing strategy: {strategy}")
    
    # Create a temporary config with just this strategy
    temp_config = config.copy()
    temp_config['STRATEGIES'] = [strategy]
    
    # Temporarily override the global CONFIG
    original_config = config.copy()
    CONFIG = temp_config
    
    try:
        # Run the optimization for this single strategy
        modellierung()
    except Exception as e:
        logging.error(f"Error processing strategy {strategy}: {e}")
        print(f"ERROR processing strategy {strategy}: {e}")
    finally:
        # Restore the original CONFIG
        CONFIG = original_config


def main():
    with ProcessPoolExecutor(max_workers=min(len(CONFIG['STRATEGIES']), os.cpu_count())) as executor:
        futures = {executor.submit(process_single_strategy, strategy, CONFIG.copy()): strategy 
                  for strategy in CONFIG['STRATEGIES']}
        # Handle results

if __name__ == '__main__':
    start = time.time()
    main()
    end = time.time()
    print(f"Total runtime: {end - start:.2f} seconds")