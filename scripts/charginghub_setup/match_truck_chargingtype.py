"""
Matching Truck Charging Types to Charging Stations
This script simulates the assignment of trucks to charging stations based on their arrival times, charging types, and other parameters. It generates a DataFrame containing truck data for a representative week at a single location, assigns charging stations, and exports the results to a CSV file.

"""

# ======================================================
# Importing Required Libraries
# ======================================================
import pandas as pd
import numpy as np
import os
from scipy.interpolate import interp1d
import config_setup 
from pathlib import Path
import logging


np.random.seed(42)

# ======================================================
# Main Function
# ======================================================
def main():
    """
    Main function to execute the truck simulation pipeline.
    """
    # Load configurations and data
    CONFIG = load_configurations()
    df_verteilungsfunktion, df_ladevorgaenge_daily = load_input_data(CONFIG['path'])

    # Generate truck data
    df_lkws = generate_truck_data(CONFIG, df_verteilungsfunktion, df_ladevorgaenge_daily)
    print("Truck data generated successfully.")
    
    # Assign charging stations
    df_lkws = assign_charging_stations(df_lkws, CONFIG)

    # Add datetime and export results
    finalize_and_export_data(df_lkws, CONFIG)

    # Analyze charging types
    analyze_charging_types(df_lkws)

# ======================================================
# Configuration and Input Data
# ======================================================
def load_configurations():
    """
    Load and return the configurations for the simulation.
    """
    path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Go up to project root
    freq = 5  # Frequency of updates (in minutes)
    return {
        'path': path,
        'freq': freq,
        'lkw_id':{
            '1': 0.093,
            '2': 0.187,
            '3': 0.289,
            '4': 0.431
        },
        'kapazitaeten_lkws': {
            '1': 600,
            '2': 720,
            '3': 840,
            '4': 960
        },
        'leistungen_lkws': {
            '1': 750,
            '2': 750,
            '3': 1200,
            '4': 1200
        },
        'pausentypen': ['Schnelllader', 'Nachtlader'],
        'pausenzeiten_lkws': {
            'Schnelllader': 45,
            'Nachtlader': 540
        },
        'leistung': {'HPC': 350, 'NCS': 100, 'MCS': 1000},
        'energie_pro_abschnitt': 80 * 4.5 * 1.26,
        'sicherheitspuffer': 0.1
    }

def load_input_data(path):
    """
    Load input data from CSV files for a single location.
    """
    import json
    
    # Convert path to Path object if it's not already
    path = Path(path)
    
    # Define file paths
    verteilungsfunktion_path = path / 'data' / 'traffic' / 'raw_data' / 'verteilungsfunktion_mcs-ncs.csv'
    laden_mauttabelle_path = path / 'data' / 'traffic' / 'final_traffic' / 'laden_mauttabelle.json'
    
    # Create directories if they don't exist
    verteilungsfunktion_path.parent.mkdir(exist_ok=True, parents=True)
    
    try:
        # Load distribution function
        if verteilungsfunktion_path.exists():
            df_verteilungsfunktion = pd.read_csv(verteilungsfunktion_path, sep=',')
        else:
            logging.warning(f"File not found: {verteilungsfunktion_path}")
            # Create a dummy distribution function if the file doesn't exist
            df_verteilungsfunktion = pd.DataFrame({
                'Zeit': list(range(0, 1440, 15)),  # Time in minutes
                'HPC': [1/96] * 96,  # Uniform distribution
                'NCS': [1/96] * 96   # Uniform distribution
            })
        
        # Load traffic data
        if laden_mauttabelle_path.exists():
            with open(laden_mauttabelle_path, 'r') as f:
                laden_data = json.load(f)
        else:
            logging.warning(f"File not found: {laden_mauttabelle_path}")

        
        # Get the forecast year from metadata (default to 2035)
        forecast_year = laden_data.get('metadata', {}).get('forecast_year', '2035')
        
        # Extract traffic data per day from metadata
        traffic_data = laden_data['metadata']['toll_section']['traffic']
        
        # Extract break data for the specified forecast year (2035)
        short_breaks_key = f"short_breaks_{forecast_year}"
        long_breaks_key = f"long_breaks_{forecast_year}"
        
        # Get break counts from the JSON data
        short_breaks = laden_data['data']['breaks'][short_breaks_key]
        long_breaks = laden_data['data']['breaks'][long_breaks_key]
        
        # Create a dataframe for daily charging operations based on the data
        rows = []
        
        # Map German day names to day numbers
        day_to_num = {
            'Montag': 1, 'Dienstag': 2, 'Mittwoch': 3, 'Donnerstag': 4, 
            'Freitag': 5, 'Samstag': 6, 'Sonntag': 7
        }
        
        # Check if daily distribution is available in the JSON
        if 'daily_distribution' in laden_data['data']:
            # Use provided daily distribution data for more precise values
            daily_dist = laden_data['data']['daily_distribution']
            hpc_key = f"HPC_{forecast_year}"
            ncs_key = f"NCS_{forecast_year}"
            
            for entry in daily_dist:
                day = entry['day']
                day_num = day_to_num[day]
                
                # Add Schnelllader (HPC) entry
                rows.append({
                    'Wochentag': day_num,
                    'Ladetype': 'Schnelllader',
                    'Anzahl': entry[hpc_key]
                })
                
                # Add Nachtlader (NCS) entry
                rows.append({
                    'Wochentag': day_num,
                    'Ladetype': 'Nachtlader',
                    'Anzahl': entry[ncs_key]
                })
        else:
            # Calculate distribution based on traffic proportions
            total_traffic = sum(traffic_data.values())
            
            # Default BEV adoption rate (can be parameterized if needed)
            bev_adoption_rate = 0.15
            
            for day, traffic in traffic_data.items():
                # Calculate proportion of traffic for this day
                day_proportion = traffic / total_traffic if total_traffic > 0 else 0
                
                # Calculate number of charging sessions based on break data and traffic proportion
                schnelllader_count = int(short_breaks * day_proportion * bev_adoption_rate)
                nachtlader_count = int(long_breaks * day_proportion * bev_adoption_rate)
                
                # Add to dataframe - Schnelllader
                rows.append({
                    'Wochentag': day_to_num[day],
                    'Ladetype': 'Schnelllader',
                    'Anzahl': schnelllader_count
                })
                
                # Add to dataframe - Nachtlader
                rows.append({
                    'Wochentag': day_to_num[day],
                    'Ladetype': 'Nachtlader',
                    'Anzahl': nachtlader_count
                })
        
        df_ladevorgaenge_daily = pd.DataFrame(rows)
        
        return df_verteilungsfunktion, df_ladevorgaenge_daily
        
    except Exception as e:
        logging.error(f"Error loading input data: {e}")
        raise

# ======================================================
# Helper Functions
# ======================================================
def get_soc(ankunftszeit):
    """
    Calculate the State of Charge (SOC) based on arrival time.
    """
    if ankunftszeit < 360:  # Early morning
        soc = 0.2 + np.random.uniform(-0.1, 0.1)
    else:
        soc = -(0.00028) * ankunftszeit + 0.6
        soc += np.random.uniform(-0.1, 0.1)
    
    # soc = 0.2 + np.random.uniform(-0.1, 0.1)
      
    return soc

def get_leistungsfaktor(soc):
    """
    Adjust power factor based on SOC using the minimum of two linear functions.
    """
    return min(-0.177038 * soc + 0.970903, -1.51705 * soc + 1.6336)


# ======================================================
# Truck Data Generation
# ======================================================
def generate_truck_data(config, df_verteilungsfunktion, df_ladevorgaenge_daily):
    """
    Generate truck data for a single representative week at one location.
    """
    # Create mapping from pausentyp to column name in CSV
    pausentyp_to_column = {
        'Schnelllader': 'HPC',  # Schnelllader maps to HPC column
        'Nachtlader': 'NCS'     # Nachtlader maps to NCS column
    }
    
    dict_lkws = {
        'Tag': [],
        'Ankunftszeit': [],
        'Nummer': [],
        'Pausentyp': [],
        'Kapazitaet': [],
        'Max_Leistung': [],
        'SOC': [],
        'SOC_Target': [],
        'Pausenlaenge': [],
        'Lkw_ID': []
    }
    
    # Always use a 7-day horizon (one week)
    horizon = 7
    
    for day in range(horizon):  # Loop through 7 days
        wochentag = day + 1  # Monday is 1, Sunday is 7
        
        # Simplified to directly access data without cluster filtering
        anzahl_lkws = {
            pausentyp: df_ladevorgaenge_daily[(df_ladevorgaenge_daily['Wochentag'] == wochentag) & 
                                            (df_ladevorgaenge_daily['Ladetype'] == pausentyp)]['Anzahl'].values[0]
            for pausentyp in config['pausentypen']
        }
        
        # Rest of function remains similar
        for pausentyp in config['pausentypen']:
            for _ in range(int(anzahl_lkws[pausentyp])):
                lkw_id = np.random.choice(
                    list(config['lkw_id'].keys()),
                    p=list(config['lkw_id'].values())
                )
                
                pausenzeit = config['pausenzeiten_lkws'][pausentyp]
                kapazitaet = config['kapazitaeten_lkws'][lkw_id]
                leistung = config['leistungen_lkws'][lkw_id]
                
                # Use the mapping to get the correct column name
                column_name = pausentyp_to_column[pausentyp]
                
                minuten = np.random.choice(
                    df_verteilungsfunktion['Zeit'],
                    p=df_verteilungsfunktion[column_name]
                )
                soc = get_soc(minuten)
                
                if pausentyp == 'Nachtlader':
                    soc_target = 1.0
                else:
                    soc_target = config['energie_pro_abschnitt'] / kapazitaet + config['sicherheitspuffer']
                    soc_target = min(soc_target, 1.0)
                    soc_target = max(soc_target, soc)
                
                dict_lkws['Tag'].append(day + 1)
                dict_lkws['Kapazitaet'].append(kapazitaet)
                dict_lkws['Max_Leistung'].append(leistung)
                dict_lkws['Nummer'].append(None)  # Placeholder for ID
                dict_lkws['SOC'].append(soc)
                dict_lkws['SOC_Target'].append(soc_target)
                dict_lkws['Pausentyp'].append(pausentyp)
                dict_lkws['Pausenlaenge'].append(pausenzeit)
                dict_lkws['Ankunftszeit'].append(minuten)
                dict_lkws['Lkw_ID'].append(int(lkw_id))

    df_lkws = pd.DataFrame(dict_lkws)
    df_lkws.sort_values(by=['Tag', 'Ankunftszeit'], inplace=True)
    df_lkws.reset_index(drop=True, inplace=True)
    
    # Modify the numbering to not depend on clusters
    df_lkws['Nummer'] = range(1, len(df_lkws) + 1)
    df_lkws['Nummer'] = df_lkws['Nummer'].apply(lambda x: f'{x:04}')
    return df_lkws

# ======================================================
# Assign Charging Stations
# ======================================================
def assign_charging_stations(df_lkws, config):
    """
    Assign charging stations to each truck based on configurations.
    """
    df_lkws['Ladesäule'] = None
    count = 0
    for index in range(len(df_lkws)):
        
        kapazitaet = float(df_lkws.loc[index, 'Kapazitaet'])
        soc_init = df_lkws.loc[index, 'SOC']
        pausentyp = df_lkws.loc[index, 'Pausentyp']
        pausenzeit = df_lkws.loc[index, 'Pausenlaenge']
        max_leistung_lkw = df_lkws.loc[index, 'Max_Leistung']
        soc_target = df_lkws.loc[index, 'SOC_Target']
        df_lkws.loc[index, 'SOC_Target'] = soc_target

        if pausentyp == 'Nachtlader':
            df_lkws.loc[index, 'Ladesäule'] = 'NCS'
            continue
        
        if soc_target < soc_init:
            print(f"Warning: Truck {df_lkws.loc[index, 'Nummer']} has a target SOC less than initial SOC!")
            # raise ValueError("Error: Target SOC is less than initial SOC!")

        ladezeiten = {}

        for station, leistung_init in config['leistung'].items():
            ladezeit = 0
            soc = soc_init
            while soc < soc_target:
                ladezeit += config['freq']
                leistungsfaktor = get_leistungsfaktor(soc)
                aktuelle_leistung = min(leistung_init, leistungsfaktor * max_leistung_lkw)
                energie = aktuelle_leistung * config['freq'] / 60
                soc += energie / kapazitaet
            ladezeiten[station] = pausenzeit - ladezeit

        if ladezeiten['HPC'] >= 0:
            df_lkws.loc[index, 'Ladesäule'] = 'HPC'
        elif ladezeiten['MCS'] >= 0:
            df_lkws.loc[index, 'Ladesäule'] = 'MCS'
        else:
            df_lkws.loc[index, 'Ladesäule'] = 'MCS'
            count += 1
    if count > 0:
        print(f"Warning: {count} trucks have been assigned to MCS due to insufficient charging capacity.")
        
    dict_anteile = {
        1: df_lkws[df_lkws['Lkw_ID'] == 1].shape[0] / df_lkws.shape[0],
        2: df_lkws[df_lkws['Lkw_ID'] == 2].shape[0] / df_lkws.shape[0],
        3: df_lkws[df_lkws['Lkw_ID'] == 3].shape[0] / df_lkws.shape[0],
        4: df_lkws[df_lkws['Lkw_ID'] == 4].shape[0] / df_lkws.shape[0]
    }

    print(dict_anteile)
    
    return df_lkws

# ======================================================
# Finalize and Export Data
# ======================================================
def finalize_and_export_data(df_lkws, config):
    """
    Finalize the DataFrame, add datetime, and export to CSV and JSON files.
    """
    # Use a generic week starting from Monday
    df_lkws['Zeit_DateTime'] = pd.to_datetime(
        df_lkws['Ankunftszeit'] + ((df_lkws['Tag'] - 1) * 1440),
        unit='m',
        origin='2024-01-01'  # This could be any Monday, date doesn't matter much
    )
    df_lkws['Ankunftszeit_total'] = df_lkws['Ankunftszeit'] + ((df_lkws['Tag'] - 1) * 1440)
    df_lkws['Wochentag'] = df_lkws['Tag']  # Since day 1-7 already represents the weekday
    df_lkws['KW'] = 1  # Just use week 1 since we're only modeling one representative week
    
    # Sort by datetime
    df_lkws.sort_values(by=['Zeit_DateTime'], inplace=True)
    
    # Reorder columns without cluster
    df_lkws = df_lkws[[
        'Zeit_DateTime', 'Ankunftszeit_total', 'Tag', 'KW','Wochentag',
        'Ankunftszeit', 'Nummer', 'Pausentyp', 'Kapazitaet', 'Max_Leistung', 'SOC',
        'SOC_Target', 'Pausenlaenge', 'Lkw_ID', 'Ladesäule'
    ]]
    
    # Ensure the directories exist
    output_dir = os.path.join(config['path'], 'data', 'load', 'truckdata')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a structured JSON output
    # First, prepare the metadata
    charger_counts = df_lkws['Ladesäule'].value_counts().to_dict()
    
    # Create JSON structure
    json_output = {
        "metadata": {
            "total_trucks": len(df_lkws),
            "simulation_period_days": 7,
            "start_date": "2024-01-01",
            "charging_types": charger_counts
        },
        "trucks": []
    }
    
    # Convert each truck row to a JSON object
    for _, row in df_lkws.iterrows():
        truck_obj = {
            "id": row['Nummer'],
            "arrival_day": int(row['Tag']),
            "arrival_time_minutes": int(row['Ankunftszeit']),
            "pause_type": row['Pausentyp'],
            "capacity_kwh": float(row['Kapazitaet']),
            "max_power_kw": float(row['Max_Leistung']),
            "initial_soc": float(row['SOC']),
            "target_soc": float(row['SOC_Target']),
            "pause_duration_minutes": int(row['Pausenlaenge']),
            "truck_type_id": int(row['Lkw_ID']),
            "assigned_charger": row['Ladesäule'],
            "arrival_datetime": row['Zeit_DateTime'].strftime('%Y-%m-%d %H:%M:%S')
        }
        json_output["trucks"].append(truck_obj)
    
    # Export to JSON file
    json_path = os.path.join(output_dir, 'eingehende_lkws_ladesaeule.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        import json
        json.dump(json_output, f, ensure_ascii=False, indent=2)
        
    print(f"Data exported to JSON: {json_path}")

# ======================================================
# Analyze Charging Types
# ======================================================
def analyze_charging_types(df_lkws):
    """
    Analyze and print the proportion of each charging type.
    """
    # No changes needed here if you don't reference clusters
    df_ladetypen = df_lkws.groupby('Ladesäule').size().reset_index(name='Anzahl')
    print(df_ladetypen)

# ======================================================
# Main Execution
# ======================================================
if __name__ == "__main__":
    main()