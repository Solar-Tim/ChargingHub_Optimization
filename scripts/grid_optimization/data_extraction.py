import os
import sys
import json
import pandas as pd
from pathlib import Path
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import from root
from config import Config

# Import from this module
from data_loading import get_location_id_suffix, get_location_specific_filename

def extract_charger_counts(strategy):
    """
    Extract charger counts from charging hub metadata file.
    
    Args:
        strategy: The charging strategy name
        
    Returns:
        dict: Dictionary with counts for each charger type
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    # Get location-specific file path
    filename = f'metadata_charginghub_{strategy}.json'
    metadata_file = get_location_specific_filename(filename)
    file_path = os.path.join(project_root, 'data', 'load', metadata_file)
    
    # Fallback to other possible filenames if the specific one isn't found
    if not os.path.exists(file_path):
        # Try with multiple strategies in the filename
        strategies = Config.CHARGING_CONFIG.get('ALL_STRATEGIES', ['T_min', 'Konstant', 'Hub'])
        strategy_suffix = '_'.join(strategies)
        filename = f'metadata_charginghub_{strategy_suffix}.json'
        metadata_file = get_location_specific_filename(filename)
        file_path = os.path.join(project_root, 'data', 'load', metadata_file)
    
    if not os.path.exists(file_path):
        # Final fallback to most basic filename
        filename = f'metadata_charginghub.json'
        metadata_file = get_location_specific_filename(filename)
        file_path = os.path.join(project_root, 'data', 'load', metadata_file)
    
    # If we still can't find it, try any metadata file in the directory
    if not os.path.exists(file_path):
        load_dir = os.path.join(project_root, 'data', 'load')
        location_suffix = get_location_id_suffix()
        
        # Look for any metadata file with the location suffix
        if location_suffix:
            for f in os.listdir(load_dir):
                if f.startswith('metadata_charginghub_') and location_suffix in f:
                    file_path = os.path.join(load_dir, f)
                    break
        
        # If still not found, look for any metadata file
        if not os.path.exists(file_path):
            for f in os.listdir(load_dir):
                if f.startswith('metadata_charginghub_'):
                    file_path = os.path.join(load_dir, f)
                    break
    
    try:
        print(f"Loading charger count data from: {file_path}")
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        stations_count = {}
        
        # Extract from "charging_stations" key in the JSON
        charging_stations = data.get("metadata", {}).get("charging_stations", {})
        for station_type, info in charging_stations.items():
            if "count" in info:
                stations_count[station_type] = info["count"]
        
        return stations_count
    
    except FileNotFoundError:
        print(f"Error: Could not find metadata file for strategy '{strategy}'.")
        return {"MCS": 4, "HPC": 4, "NCS": 42}  # Default values
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in metadata file for strategy '{strategy}'.")
        return {"MCS": 4, "HPC": 4, "NCS": 42}  # Default values
    except Exception as e:
        print(f"Error extracting charger counts: {e}")
        return {"MCS": 4, "HPC": 4, "NCS": 42}  # Default values

def extract_charging_data(strategy):
    """
    Extract charging data from lastgang CSV files.
    
    Args:
        strategy: The charging strategy name
        
    Returns:
        tuple: (lastgang_df, stations_count)
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    # Extract charger counts first
    stations_count = extract_charger_counts(strategy)
    
    # Get location-specific lastgang file
    filename = f'lastgang_{strategy}.csv'
    lastgang_file = get_location_specific_filename(filename)
    file_path = os.path.join(project_root, 'data', 'load', lastgang_file)
    
    # Try detailed file if main file not found
    if not os.path.exists(file_path):
        filename = f'lastgang_detailed_{strategy}.csv'
        lastgang_file = get_location_specific_filename(filename)
        file_path = os.path.join(project_root, 'data', 'load', lastgang_file)
    
    try:
        print(f"Loading charging data from: {file_path}")
        df = pd.read_csv(file_path, sep=';')
        
        # Process the dataframe to match expected format
        if 'time (5min steps)' in df.columns:
            # Convert time in minutes to day and time columns
            df['Tag'] = (df['time (5min steps)'] // (24*60)) + 1
            df['Zeit'] = df['time (5min steps)'] % (24*60)
            
            # Use 'Last' column as 'Leistung_Total'
            if 'Last' in df.columns:
                df['Leistung_Total'] = df['Last']
            
            # Add separate charger type loads if available
            if 'Last_NCS' in df.columns:
                df['Leistung_NCS'] = df['Last_NCS']
            if 'Last_HPC' in df.columns:
                df['Leistung_HPC'] = df['Last_HPC']
            if 'Last_MCS' in df.columns:
                df['Leistung_MCS'] = df['Last_MCS']
        
        # Ensure we have the required columns
        required_columns = ['Tag', 'Zeit', 'Leistung_Total']
        for col in required_columns:
            if col not in df.columns:
                print(f"Error: Required column '{col}' not found in lastgang file.")
                return pd.DataFrame(), stations_count
        
        return df, stations_count
    
    except FileNotFoundError:
        print(f"Error: File not found for strategy '{strategy}'.")
        return pd.DataFrame(), stations_count
    except Exception as e:
        print(f"Error extracting charging data: {e}")
        return pd.DataFrame(), stations_count

if __name__ == "__main__":
    # Test extraction functions
    charger_counts = extract_charger_counts("Hub")
    print(f"Extracted charger counts: {charger_counts}")
    
    lastgang_df, _ = extract_charging_data("Hub")
    if not lastgang_df.empty:
        print(f"Extracted lastgang data shape: {lastgang_df.shape}")
        print(f"First few rows:\n{lastgang_df.head()}")
    else:
        print("No lastgang data extracted.")


