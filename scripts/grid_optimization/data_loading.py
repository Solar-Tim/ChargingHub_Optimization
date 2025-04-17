import pandas as pd
import numpy as np
import os
from pathlib import Path
# Import necessary functions from config and json_utils
from config import Config
# Assuming json_utils is accessible or moving the helper functions here
# Let's define the helpers directly here for simplicity in this context

def _get_location_id():
    """Helper function to safely get the location ID from Config."""
    if Config.RESULT_NAMING.get('USE_CUSTOM_ID', False):
        return Config.RESULT_NAMING.get('CUSTOM_ID')
    return None

def _add_id_to_path(path, location_id):
    """Adds location_id before the file extension."""
    if location_id:
        p = Path(path)
        return p.parent / f"{p.stem}_{location_id}{p.suffix}"
    return path

def load_charging_hub_profile(strategy):
    """
    Load the charging hub load profile for a given strategy.
    Uses location_id to load the correct file.
    
    Args:
        strategy (str): The charging strategy (e.g., "T_min", "Konstant", "Hub").
    
    Returns:
        tuple: (load_profile, timestamps) or (None, None) if file not found.
    """
    # Get location_id
    location_id = _get_location_id()
    print(f"[data_loading] Loading profile for strategy: {strategy}, location_id: {location_id}")

    # Construct the base file path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path_base = os.path.join(base_dir, 'data', 'load', f'lastgang_{strategy}.csv')
    
    # Add location_id to the file path
    file_path_with_id = _add_id_to_path(file_path_base, location_id)
    
    try:
        df = pd.read_csv(file_path_with_id, sep=Config.CSV['DEFAULT_SEPARATOR'], decimal=Config.CSV['DEFAULT_DECIMAL'])
        
        # Ensure required columns exist
        if 'Leistung_Total' not in df.columns or 'Timestamp' not in df.columns:
            print(f"Error: Required columns ('Leistung_Total', 'Timestamp') not found in {file_path_with_id}")
            return None, None
            
        load_profile = df['Leistung_Total'].tolist()
        timestamps = df['Timestamp'].tolist()
        print(f"Successfully loaded load profile from {file_path_with_id}")
        return load_profile, timestamps
    except FileNotFoundError:
        print(f"Error: Load profile file not found at {file_path_with_id}. Check if ID-specific file exists.")
        return None, None
    except Exception as e:
        print(f"Error loading or processing {file_path_with_id}: {e}")
        return None, None

def load_data(strategy):
    """
    Load all necessary data for the optimization model.
    
    Args:
        strategy (str): The charging strategy.
        
    Returns:
        tuple: (load_profile, timestamps)
    """
    load_profile, timestamps = load_charging_hub_profile(strategy)
    
    if load_profile is None or timestamps is None:
        # Handle the error appropriately, maybe raise an exception or exit
        raise FileNotFoundError(f"Failed to load essential data for strategy {strategy}. Cannot proceed.")
        
    return load_profile, timestamps

# Example usage (optional)
if __name__ == "__main__":
    # Manually set a test ID if needed
    # Config.RESULT_NAMING['USE_CUSTOM_ID'] = True
    # Config.RESULT_NAMING['CUSTOM_ID'] = 'test123'
    
    for strat in ["T_min", "Konstant", "Hub"]:
        print(f"\n--- Testing strategy: {strat} ---")
        profile, times = load_data(strat)
        if profile:
            print(f"  Loaded profile with {len(profile)} entries.")
            print(f"  First timestamp: {times[0]}, Last timestamp: {times[-1]}")