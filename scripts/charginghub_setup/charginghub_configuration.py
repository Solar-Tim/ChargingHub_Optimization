import pandas as pd
import numpy as np
import networkx as nx
import os
import logging
from pathlib import Path
import warnings
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(filename=log_dir/'charging_hub_config.log', 
                   level=logging.DEBUG, 
                   format='%(asctime)s; %(levelname)s; %(message)s')

# HARDCODED CONFIGURATION VALUES
# Instead of parsing them from scenario strings, define them directly
CLUSTER_ID = 1
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
    Import truck data from CSV file. Creates necessary directories if they don't exist.
    Returns a DataFrame with truck data.
    """
    # Get the project root path (assuming this script is in scripts/charginghub_setup/)
    project_root = Path(__file__).parent.parent.parent.resolve()
    
    # Create data paths
    data_dir = project_root / "data"
    results_dir = project_root / "results"
    lkw_dir = results_dir / "lkw_eingehend"
    
    # Create directories if they don't exist
    data_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)
    lkw_dir.mkdir(exist_ok=True)

    # Path to truck data file
    truck_data_path = lkw_dir / "eingehende_lkws_ladesaeule.csv"
    
    logging.info(f"Looking for truck data at {truck_data_path}")
    
    if not truck_data_path.exists():
        # Create a simple sample DataFrame if the file doesn't exist
        logging.warning(f"Truck data file not found: {truck_data_path}")
        logging.info("Creating sample truck data")
        
        # Create sample data
        sample_data = {
            'Tag': [1, 1, 1, 2, 2],
            'Wochentag': [1, 1, 1, 2, 2],
            'Ankunftszeit': [480, 600, 720, 480, 600],  # 8:00, 10:00, 12:00, 8:00, 10:00
            'Nummer': [1, 2, 3, 4, 5],
            'Pausentyp': ['Schnelllader', 'Schnelllader', 'Nachtlader', 'Schnelllader', 'Nachtlader'],
            'Kapazitaet': [600, 720, 840, 600, 720],
            'Max_Leistung': [750, 750, 1200, 750, 1200],
            'SOC': [0.2, 0.3, 0.4, 0.2, 0.3],
            'SOC_Target': [0.8, 0.8, 1.0, 0.8, 1.0],
            'Pausenlaenge': [45, 45, 540, 45, 540],
            'Lkw_ID': [1, 2, 3, 1, 2],
            'Ladesäule': ['HPC', 'HPC', 'NCS', 'HPC', 'NCS'],
            'Cluster': [1, 1, 1, 1, 1]
        }
        
        df = pd.DataFrame(sample_data)
        
        # Save the sample data
        os.makedirs(os.path.dirname(truck_data_path), exist_ok=True)
        df.to_csv(truck_data_path, sep=';', decimal=',')
        logging.info(f"Created sample data at {truck_data_path}")
        
        return df
    else:
        # Load existing truck data
        try:
            logging.info(f"Loading truck data from {truck_data_path}")
            df = pd.read_csv(truck_data_path, sep=';', decimal=',')
            
            # Add index_col=0 handling if needed
            if 'Unnamed: 0' in df.columns:
                df = df.set_index('Unnamed: 0')
                
            return df
        except Exception as e:
            logging.error(f"Error loading truck data: {e}")
            raise

def build_flow_network(df_filter, anzahl_ladesaeulen):
    """
    Builds a flow network (DiGraph) for the filtered trucks (df_filter).
    - Each truck gets two nodes: LKW{i}_arr and LKW{i}_dep.
    - These are connected to time nodes (5-min grid) for arrival and departure times.
    - Time nodes are connected with capacity = number of charging stations.
    - SuperSource (S) -> LKW{i}_arr and LKW{i}_dep -> SuperSink (T) limit flow to 1 per truck.
    """
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
    
    # Calculate max flow min cost
    try:
        flow_dict = nx.max_flow_min_cost(G, S, T)
        return flow_dict
    except Exception as e:
        logging.error(f"Error calculating flow: {e}")
        # Return empty flow dict as fallback
        return {}

def konfiguration_ladehub(df_eingehende_lkws):
    """
    Main function: Determines for each charging type (HPC/MCS/NCS) how many charging stations
    are needed to achieve a target charging quota. Also saves for each truck whether it was ultimately charged.
    Uses the hardcoded parameters at the top of the file.
    """
    # Create empty DataFrame for load status
    df_eingehende_lkws_loadstatus = pd.DataFrame()
    
    # Get parameters from hardcoded values
    cluster = CLUSTER_ID
    dict_ladequoten = CHARGING_QUOTAS
    dict_ladezeit = CHARGING_TIMES
    
    logging.info(f"Configuration: Cluster={cluster}, Load Quotas={dict_ladequoten}, Charging Times={dict_ladezeit}")

    # Update pause lengths based on hardcoded values
    logging.info(f"Using charging pause times: {dict_ladezeit}")
    for idx, row in df_eingehende_lkws.iterrows():
        if row['Pausentyp'] == 'Nachtlader':
            df_eingehende_lkws.loc[idx, 'Pausenlaenge'] = dict_ladezeit['Nacht']
        elif row['Pausentyp'] == 'Schnelllader':
            df_eingehende_lkws.loc[idx, 'Pausenlaenge'] = dict_ladezeit['Schnell']

    # Initialize output DataFrames
    df_anzahl_ladesaeulen = pd.DataFrame(columns=['Cluster','NCS','Ladequote_NCS','HPC','Ladequote_HPC','MCS','Ladequote_MCS'])
    df_konf_optionen = pd.DataFrame(columns=['Ladetype','Anzahl_Ladesaeulen','Ladequote','LKW_pro_Ladesaeule'])
    
    # Add cluster column if it doesn't exist
    if 'Cluster' not in df_eingehende_lkws.columns:
        df_eingehende_lkws['Cluster'] = cluster
        logging.warning(f"Added missing 'Cluster' column with value {cluster}")
    
    # Loop over the different charging station types
    for ladetyp in dict_ladequoten:
        ladquote_ziel = dict_ladequoten[ladetyp]
        logging.info(f"Processing charging type: {ladetyp}, target quota: {ladquote_ziel:.2f}")

        # Filter matching trucks: correct cluster + correct charging station type
        df_eingehende_lkws_filter = df_eingehende_lkws[
            (df_eingehende_lkws['Cluster'] == cluster) &
            (df_eingehende_lkws['Ladesäule'] == ladetyp)
        ]

        ankommende_lkws = len(df_eingehende_lkws_filter)
        ladequote = 0
        anzahl_ladesaeulen = 1

        if ankommende_lkws == 0:
            logging.warning(f"No trucks found for charging type {ladetyp} in cluster {cluster}")
            df_anzahl_ladesaeulen.loc[0, 'Cluster'] = cluster
            df_anzahl_ladesaeulen.loc[0, ladetyp] = 0
            df_anzahl_ladesaeulen.loc[0, f'Ladequote_{ladetyp}'] = 0
            continue

        # Repeat in steps until the target charging quota
        for durchgang in range(min(ankommende_lkws, 20)):  # Limit iterations to prevent infinite loops
            # Build graph via node-splitting approach
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
            df_konf_optionen.loc[len(df_konf_optionen)] = [ladetyp, anzahl_ladesaeulen, ladequote, lkw_pro_ladesaeule]
            
            # Debug output
            logging.info(f"[{ladetyp}], Stations={anzahl_ladesaeulen}, Quota={ladequote:.2f}, Trucks per station={lkw_pro_ladesaeule:.2f}")
            print(f"[{ladetyp}], Stations={anzahl_ladesaeulen}, Quota={ladequote:.2f}, Trucks per station={lkw_pro_ladesaeule:.2f}")

            # If target charging quota reached/exceeded, save LoadStatus & break
            if ladequote >= ladquote_ziel:
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
                df_eingehende_lkws_loadstatus = pd.concat([df_eingehende_lkws_loadstatus, df_eingehende_lkws_filter_copy])
                break
            else:
                # Adapt number of charging stations and next round
                anzahl_ladesaeulen = np.ceil(anzahl_ladesaeulen / ladequote * ladquote_ziel).astype(int) if ladequote > 0 else anzahl_ladesaeulen + 1

        # Save results
        df_anzahl_ladesaeulen.loc[0, 'Cluster'] = cluster
        df_anzahl_ladesaeulen.loc[0, ladetyp] = anzahl_ladesaeulen
        df_anzahl_ladesaeulen.loc[0, f'Ladequote_{ladetyp}'] = ladequote
    
    # Path for files - use project structure
    project_root = Path(__file__).parent.parent.parent
    results_dir = project_root / "results"
    
    # Create output directories
    output_paths = {
        'konfiguration_ladehub': results_dir / "konfiguration_ladehub",
        'lkws': results_dir / "lkws",
        'konf_optionen': results_dir / "konf_optionen"
    }
    
    # Create directories if they don't exist
    for path in output_paths.values():
        path.mkdir(exist_ok=True)
    
    # Output filename based on hardcoded parameters
    output_filename = f'cluster_{cluster}_quota_{int(CHARGING_QUOTAS["NCS"]*100)}-{int(CHARGING_QUOTAS["HPC"]*100)}-{int(CHARGING_QUOTAS["MCS"]*100)}_pause_{CHARGING_TIMES["Schnell"]}-{CHARGING_TIMES["Nacht"]}_{SCENARIO_NAME}'
    
    # Save to CSV files with generated filename
    try:
        # CSV: Number of charging stations
        df_anzahl_ladesaeulen.to_csv(
            output_paths['konfiguration_ladehub'] / f'anzahl_ladesaeulen_{output_filename}.csv',
            sep=';', decimal=','
        )

        # CSV: Trucks with LoadStatus
        df_eingehende_lkws_loadstatus.to_csv(
            output_paths['lkws'] / f'eingehende_lkws_loadstatus_{output_filename}.csv',
            sep=';', decimal=','
        )
        
        # CSV: Configuration options
        df_konf_optionen.to_csv(
            output_paths['konf_optionen'] / f'konf_optionen_{output_filename}.csv',
            sep=';', decimal=',', index=False
        )
        
        logging.info(f"Results saved with filename: {output_filename}")
    except Exception as e:
        logging.error(f"Error saving results: {e}")
    
    return df_anzahl_ladesaeulen

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