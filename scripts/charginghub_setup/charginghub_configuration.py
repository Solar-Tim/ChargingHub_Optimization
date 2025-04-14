import pandas as pd
import numpy as np
import networkx as nx
import os
import logging
from pathlib import Path
import warnings
import json
import multiprocessing
from functools import partial
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(filename=log_dir/'charging_hub_config.log', 
                   level=logging.DEBUG, 
                   format='%(asctime)s; %(levelname)s; %(message)s')

# HARDCODED CONFIGURATION VALUES
# Instead of parsing them from scenario strings, define them directly
CHARGING_QUOTAS = {
    'NCS': 0.8,  # 80%
    'HPC': 0.8,  # 80% 
    'MCS': 0.8   # 80%
}
CHARGING_TIMES = {
    'Schnell': 45,   # Short charging pause (minutes)
    'Nacht': 540     # Night charging pause (minutes)
}
SCENARIO_NAME = 'Base'  # For output file naming

def datenimport():
    """
    Import truck data from JSON file using the new directory structure.
    Returns a DataFrame with truck data.
    """
    # Get the project root path
    project_root = Path(__file__).parent.parent.parent.resolve()
    
    # Path to truck data file in the new location
    truck_data_path = project_root / "data" / "load" / "truckdata" / "eingehende_lkws_ladesaeule.json"
    
    logging.info(f"Looking for truck data at {truck_data_path}")
    
    try:
        # Check if file exists
        if not truck_data_path.exists():
            logging.warning(f"File not found at new location: {truck_data_path}")
            # Provide helpful error message
            raise FileNotFoundError(f"Truck data file not found at {truck_data_path}. "
                                   f"Please ensure 'eingehende_lkws_ladesaeule.json' exists in the "
                                   f"data/load/truckdata directory.")
            
        # Load existing truck data from JSON
        logging.info(f"Loading truck data from {truck_data_path}")
            
        with open(truck_data_path, 'r') as f:
            json_data = json.load(f)
            
            # Extract trucks array
            trucks = json_data.get("trucks", [])
            
            # Convert to DataFrame with proper column mapping
            df_trucks = pd.DataFrame(trucks)
            
            # Map JSON fields to expected column names
            column_mapping = {
                'id': 'Nummer',
                'arrival_day': 'Wochentag',
                'arrival_time_minutes': 'Ankunftszeit',
                'pause_type': 'Pausentyp',
                'pause_duration_minutes': 'Pausenlaenge',
                'assigned_charger': 'Ladesäule',
                # Add battery-related fields
                'capacity_kwh': 'capacity_kwh',
                'max_power_kw': 'max_power_kw',
                'initial_soc': 'initial_soc',
                'target_soc': 'target_soc',
                'truck_type_id': 'truck_type_id'
            }
            
            # Rename columns that exist
            existing_columns = [col for col in column_mapping.keys() if col in df_trucks.columns]
            df_trucks = df_trucks.rename(columns={col: column_mapping[col] for col in existing_columns})
            
            # Ensure all required columns exist
            for target_col in column_mapping.values():
                if target_col not in df_trucks.columns:
                    df_trucks[target_col] = None
                    
            # Filter out rows with missing essential data
            df_trucks = df_trucks.dropna(subset=['Nummer', 'Ankunftszeit', 'Ladesäule'])
            
            logging.info(f"Successfully loaded {len(df_trucks)} trucks from JSON")
        return df_trucks
                
    except Exception as e:
        logging.error(f"Error in data import: {e}")
        raise

def build_flow_network(df_filter, anzahl_ladesaeulen):
    """
    Builds a flow network (DiGraph) for the filtered trucks (df_filter).
    - Each truck gets two nodes: LKW{i}_arr and LKW{i}_dep.
    - These are connected to time nodes (5-min grid) for arrival and departure times.
    - Time nodes are connected with capacity = number of charging stations.
    - SuperSource (S) -> LKW{i}_arr and LKW{i}_dep -> SuperSink (T) limit flow to 1 per truck.
    """
    logging.debug(f"Building flow network with {anzahl_ladesaeulen} charging stations for {len(df_filter)} trucks")
    G = nx.DiGraph()

    # Super-Source and Super-Sink
    S = 'SuperSource'
    T = 'SuperSink'
    G.add_node(S)
    G.add_node(T)

    # Effective arrival/departure (in minutes) depending on weekday
    df_filter = df_filter.copy()
    df_filter['EffectiveArrival'] = df_filter['Ankunftszeit'] + (df_filter['Wochentag'] - 1) * 1440
    df_filter['EffectiveDeparture'] = df_filter['EffectiveArrival'] + df_filter['Pausenlaenge'] + 5  # 5 minutes changeover time

    # Earliest start and latest end to create time nodes (5-minute grid)
    if len(df_filter) == 0:
        # Handle empty DataFrame case
        logging.warning("Empty truck filter - creating minimal flow network")
        start, ende = 0, 100
    else:
        start = int(df_filter['EffectiveArrival'].min())
        ende = int(df_filter['EffectiveDeparture'].max())
        logging.debug(f"Time range for network: {start}-{ende} minutes")

    # Create time nodes in 5-minute steps
    times = list(range(start, ende+1, 5))
    for t in times:
        G.add_node(f"time_{t}")
        
    # Edges between time nodes with capacity = number of charging stations
    # Connection from SuperSource (S) to the first time node
    G.add_edge(S, f"time_{times[0]}", capacity=anzahl_ladesaeulen, weight=0)

    # Connection from the last time node to SuperSink (T)
    G.add_edge(f"time_{times[-1]}", T, capacity=anzahl_ladesaeulen, weight=0)
    
    for i in range(len(times) - 1):
        u = f"time_{times[i]}"
        v = f"time_{times[i+1]}"
        G.add_edge(u, v, capacity=anzahl_ladesaeulen, weight=10)

    # For each truck: two nodes + edges to time nodes for arrival/departure
    for idx, row in df_filter.iterrows():
        lkw_id = row['Nummer']
        lkw_arr = f"LKW{lkw_id}_arr"
        lkw_dep = f"LKW{lkw_id}_dep"

        G.add_node(lkw_arr)
        G.add_node(lkw_dep)

        # Connect to time nodes (only arrival/departure, as desired)
        arrival_node = f"time_{int(row['EffectiveArrival'])}"
        departure_node = f"time_{int(row['EffectiveDeparture'])}"

        G.add_edge(arrival_node, lkw_arr, capacity=1, weight=0)
        G.add_edge(lkw_dep, departure_node, capacity=1, weight=0)
        G.add_edge(lkw_arr, lkw_dep, capacity=1, weight=0)
    
    logging.debug(f"Flow network built with {len(G.nodes)} nodes and {len(G.edges)} edges")
    
    # Calculate max flow min cost
    try:
        logging.debug("Calculating max flow min cost")
        flow_dict = nx.max_flow_min_cost(G, S, T)
        logging.debug(f"Flow calculation completed successfully")
        return flow_dict
    except Exception as e:
        logging.error(f"Error calculating flow: {e}")
        # Return empty flow dict as fallback
        return {}

def process_charging_type(ladetyp, dict_ladequoten, df_eingehende_lkws, df_konf_optionen_shared):
    """Process a single charging type in parallel"""
    ladquote_ziel = dict_ladequoten[ladetyp]
    logging.info(f"Processing charging type: {ladetyp}, target quota: {ladquote_ziel:.2f}")

    # Filter matching trucks: correct charging station type only
    df_eingehende_lkws_filter = df_eingehende_lkws[
        df_eingehende_lkws['Ladesäule'] == ladetyp
    ]

    ankommende_lkws = len(df_eingehende_lkws_filter)
    logging.info(f"Found {ankommende_lkws} trucks for charging type {ladetyp}")
    
    ladequote = 0
    anzahl_ladesaeulen = 1
    df_eingehende_lkws_filter_with_status = None
    df_konf_optionen_local = []

    if ankommende_lkws == 0:
        logging.warning(f"No trucks found for charging type {ladetyp}")
        return {
            'ladetyp': ladetyp,
            'anzahl_ladesaeulen': 0,
            'ladequote': 0,
            'df_with_status': None,
            'df_konf_optionen': df_konf_optionen_local
        }

    # Repeat in steps until the target charging quota
    for durchgang in range(min(ankommende_lkws, 20)):  # Limit iterations to prevent infinite loops
        logging.info(f"[{ladetyp}] Iteration {durchgang+1}: Starting with {anzahl_ladesaeulen} charging stations")
        
        # Build graph via node-splitting approach
        logging.info(f"[{ladetyp}] Building flow network with {anzahl_ladesaeulen} charging stations for {len(df_eingehende_lkws_filter)} trucks")
        flow_dict = build_flow_network(df_eingehende_lkws_filter, anzahl_ladesaeulen)

        # Determine how many trucks were actually charged
        lkw_geladen = 0
        for idx, row in df_eingehende_lkws_filter.iterrows():
            # Check if flow through LKW{i}_arr -> LKW{i}_dep > 0
            lkw_id = row['Nummer']
            lkw_arr = f"LKW{lkw_id}_arr"
            lkw_dep = f"LKW{lkw_id}_dep"
            flow_val = flow_dict.get(lkw_arr, {}).get(lkw_dep, 0)
            if flow_val > 0:
                lkw_geladen += 1

        # Calculate charging quota
        ladequote = lkw_geladen / ankommende_lkws if ankommende_lkws > 0 else 0
        lkw_pro_ladesaeule = lkw_geladen / anzahl_ladesaeulen / 7 if anzahl_ladesaeulen > 0 else 0

        # Document configuration options
        df_konf_optionen_local.append({
            'Ladesäule': ladetyp, 
            'Anzahl': anzahl_ladesaeulen, 
            'Ladequote': ladequote, 
            'LKW_pro_Ladesaeule': lkw_pro_ladesaeule
        })
        
        # Debug output
        logging.info(f"[{ladetyp}] Results: Stations={anzahl_ladesaeulen}, Charged trucks={lkw_geladen}/{ankommende_lkws}, Quota={ladequote:.2f}, Trucks per station={lkw_pro_ladesaeule:.2f}")
        print(f"[{ladetyp}], Stations={anzahl_ladesaeulen}, Quota={ladequote:.2f}, Trucks per station={lkw_pro_ladesaeule:.2f}")

        # If target charging quota reached/exceeded, save LoadStatus & break
        if ladequote >= ladquote_ziel:
            logging.info(f"[{ladetyp}] Target quota of {ladquote_ziel:.2f} reached with {anzahl_ladesaeulen} charging stations")
            liste_lkw_status = []
            for idx, row in df_eingehende_lkws_filter.iterrows():
                lkw_id = row['Nummer']
                lkw_arr = f"LKW{lkw_id}_arr"
                lkw_dep = f"LKW{lkw_id}_dep"
                flow_of_this_truck = flow_dict.get(lkw_arr, {}).get(lkw_dep, 0)
                if flow_of_this_truck > 0:
                    liste_lkw_status.append(1)
                else:
                    liste_lkw_status.append(0)

            # Append LoadStatus column
            df_eingehende_lkws_filter_copy = df_eingehende_lkws_filter.copy()
            df_eingehende_lkws_filter_copy['LoadStatus'] = liste_lkw_status
            df_eingehende_lkws_filter_with_status = df_eingehende_lkws_filter_copy
            break
        else:
            # Adapt number of charging stations and next round
            anzahl_ladesaeulen = np.ceil(anzahl_ladesaeulen / ladequote * ladquote_ziel).astype(int) if ladequote > 0 else anzahl_ladesaeulen + 1

    # Return results
    return {
        'ladetyp': ladetyp,
        'anzahl_ladesaeulen': anzahl_ladesaeulen,
        'ladequote': ladequote,
        'df_with_status': df_eingehende_lkws_filter_with_status,
        'df_konf_optionen': df_konf_optionen_local
    }

# Replace the loop over charging types with parallel processing
def parallel_charging_types_processing(dict_ladequoten, df_eingehende_lkws, df_konf_optionen):
    # Setup multiprocessing
    num_cores = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=3)  # Leave one core free for system
    
    logging.info(f"Starting parallel processing using 3 cores")
    
    # Create partial function with fixed parameters
    process_func = partial(process_charging_type, 
                           dict_ladequoten=dict_ladequoten, 
                           df_eingehende_lkws=df_eingehende_lkws,
                           df_konf_optionen_shared=df_konf_optionen)
    
    # Run processing in parallel
    results = pool.map(process_func, dict_ladequoten.keys())
    
    # Close the pool
    pool.close()
    pool.join()
    
    return results

def konfiguration_ladehub(df_eingehende_lkws):
    """
    Main function: Determines for each charging type (HPC/MCS/NCS) how many charging stations
    are needed to achieve a target charging quota. Also saves for each truck whether it was ultimately charged.
    Uses the hardcoded parameters at the top of the file.
    """
    logging.info("Starting charging hub configuration calculation")
    
    # Create empty DataFrame for load status
    df_eingehende_lkws_loadstatus = pd.DataFrame()
    
    # Get parameters from hardcoded values
    dict_ladequoten = CHARGING_QUOTAS
    dict_ladezeit = CHARGING_TIMES
    
    logging.info(f"Configuration parameters: Target charging quotas={dict_ladequoten}, Charging times={dict_ladezeit}")
    logging.info(f"Processing {len(df_eingehende_lkws)} trucks")

    # Update pause lengths based on hardcoded values
    for idx, row in df_eingehende_lkws.iterrows():
        if row['Pausentyp'] == 'Nachtlader':
            df_eingehende_lkws.loc[idx, 'Pausenlaenge'] = dict_ladezeit['Nacht']
        elif row['Pausentyp'] == 'Schnelllader':
            df_eingehende_lkws.loc[idx, 'Pausenlaenge'] = dict_ladezeit['Schnell']

    # Initialize output DataFrames
    df_anzahl_ladesaeulen = pd.DataFrame(columns=['NCS','Ladequote_NCS','HPC','Ladequote_HPC','MCS','Ladequote_MCS'])
    df_konf_optionen = pd.DataFrame(columns=['Ladetype','Anzahl_Ladesaeulen','Ladequote','LKW_pro_Ladesaeule'])
    
    # Replace the loop with this code:
    results = parallel_charging_types_processing(dict_ladequoten, df_eingehende_lkws, df_konf_optionen)

    # Process results
    df_eingehende_lkws_loadstatus = pd.DataFrame()
    for result in results:
        ladetyp = result['ladetyp']
        anzahl_ladesaeulen = result['anzahl_ladesaeulen']
        ladequote = result['ladequote']
        
        # Save results
        df_anzahl_ladesaeulen.loc[0, ladetyp] = anzahl_ladesaeulen
        df_anzahl_ladesaeulen.loc[0, f'Ladequote_{ladetyp}'] = ladequote
        
        # Process LoadStatus data
        if result['df_with_status'] is not None:
            df_eingehende_lkws_loadstatus = pd.concat([df_eingehende_lkws_loadstatus, result['df_with_status']])
        
        # Add configuration options
        for opt in result['df_konf_optionen']:
            df_konf_optionen.loc[len(df_konf_optionen)] = [
                opt['Ladesäule'], opt['Anzahl'], opt['Ladequote'], opt['LKW_pro_Ladesaeule']
            ]
    
    # Path for files - use project structure
    project_root = Path(__file__).parent.parent.parent
    
    # Output directory for truck data
    truckdata_dir = project_root / "data" / "load" / "truckdata"
    truckdata_dir.mkdir(exist_ok=True, parents=True)
    
    # Simplified output filenames
    base_filename = f'charging_config_{SCENARIO_NAME.lower()}'
    json_filename = f'{base_filename}.json'
    
    try:
        # Export to the new location only
        json_output_path = truckdata_dir / json_filename
        export_results_as_json(df_anzahl_ladesaeulen, df_eingehende_lkws_loadstatus, df_konf_optionen, json_output_path)
        logging.info(f"Results saved to JSON file: {json_output_path}")
    except Exception as e:
        logging.error(f"Error saving results: {e}")
    
    return df_anzahl_ladesaeulen

def export_results_as_json(df_anzahl_ladesaeulen, df_eingehende_lkws_loadstatus, df_konf_optionen, output_path):
    """
    Export configuration results as a structured JSON file.
    Includes battery information and standardized field names for compatibility with demand_optimization.py.
    """
    import json
    from datetime import datetime
    
    # Create the JSON structure
    result = {
        "metadata": {
            "scenario": SCENARIO_NAME,
            "charging_quotas": CHARGING_QUOTAS,
            "charging_times": CHARGING_TIMES,
            "timestamp": datetime.now().isoformat(),
            "description": "Charging hub configuration results"
        },
        "charging_stations": {},
        "configuration_options": [],
        "trucks": []
    }
    
    # Add charging station counts and quotas
    for ladetyp in ["NCS", "HPC", "MCS"]:
        if ladetyp in df_anzahl_ladesaeulen:
            result["charging_stations"][ladetyp] = {
                "count": int(df_anzahl_ladesaeulen[ladetyp].iloc[0]),
                "quota": float(df_anzahl_ladesaeulen[f'Ladequote_{ladetyp}'].iloc[0])
            }
    
    # Add configuration options data
    for _, row in df_konf_optionen.iterrows():
        result["configuration_options"].append({
            "charging_type": row['Ladetype'],
            "stations": int(row['Anzahl_Ladesaeulen']),
            "quota": float(row['Ladequote']),
            "trucks_per_station": float(row['LKW_pro_Ladesaeule'])
        })
    
    # Default battery info as fallback
    battery_defaults = {
        "NCS": {"capacity_kwh": 600, "max_power_kw": 300, "initial_soc": 0.2, "target_soc": 0.8},
        "HPC": {"capacity_kwh": 400, "max_power_kw": 350, "initial_soc": 0.3, "target_soc": 0.8},
        "MCS": {"capacity_kwh": 500, "max_power_kw": 400, "initial_soc": 0.2, "target_soc": 0.8}
    }
    
    # Add truck load status data with battery information and standardized field names
    for _, row in df_eingehende_lkws_loadstatus.iterrows():
        # Get charging type for default fallback
        charging_type = row['Ladesäule']
        default_battery_info = battery_defaults.get(charging_type, {
            "capacity_kwh": 500, "max_power_kw": 350, "initial_soc": 0.2, "target_soc": 0.8
        })
        
        # Use original battery info if available, fallback to defaults if not
        capacity_kwh = row['capacity_kwh'] if pd.notna(row.get('capacity_kwh')) else default_battery_info["capacity_kwh"]
        max_power_kw = row['max_power_kw'] if pd.notna(row.get('max_power_kw')) else default_battery_info["max_power_kw"]
        initial_soc = row['initial_soc'] if pd.notna(row.get('initial_soc')) else default_battery_info["initial_soc"]
        target_soc = row['target_soc'] if pd.notna(row.get('target_soc')) else default_battery_info["target_soc"]
        
        truck_data = {
            "id": row['Nummer'],
            "arrival_day": int(row['Wochentag']),
            "arrival_time_minutes": int(row['Ankunftszeit']),
            "pause_type": row['Pausentyp'],
            "pause_duration_minutes": int(row['Pausenlaenge']),
            "assigned_charger": row['Ladesäule'],
            "load_status": int(row['LoadStatus']),
            
            # Use original battery information when available
            "capacity_kwh": float(capacity_kwh),
            "max_power_kw": float(max_power_kw),
            "initial_soc": float(initial_soc),
            "target_soc": float(target_soc)
        }
        
        # Add truck type ID if available
        if pd.notna(row.get('truck_type_id')):
            truck_data["truck_type_id"] = int(row['truck_type_id'])
            
        result["trucks"].append(truck_data)
    
    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logging.info(f"Configuration results exported to JSON: {output_path}")
    logging.info(f"Preserved original battery information for {len(result['trucks'])} trucks")

def main():
    """Main execution function."""
    logging.info('Starting charging hub configuration')
    print('Starting charging hub configuration')
    
    try:
        # Import truck data
        df_eingehende_lkws = datenimport()
        
        # Process with hardcoded parameters
        result = konfiguration_ladehub(df_eingehende_lkws)
        
        logging.info('Charging hub configuration completed successfully')
        print('Charging hub configuration completed successfully')
        return result
    except Exception as e:
        logging.error(f"Error in charging hub configuration: {e}")
        print(f"Error in charging hub configuration: {e}")
        raise

# -------------------------------------
# Main call
# -------------------------------------
if __name__ == '__main__':
    main()