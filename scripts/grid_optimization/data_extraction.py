import json
import os
import pandas as pd
from pathlib import Path
from config import Config

def _get_location_id():
    """Helper function to safely get the location ID from Config or environment."""
    # Prioritize environment variable if set (passed from main.py)
    env_id = os.environ.get('CHARGING_HUB_CUSTOM_ID')
    if env_id:
        return env_id
    # Fallback to Config setting
    if Config.RESULT_NAMING.get('USE_CUSTOM_ID', False):
        return Config.RESULT_NAMING.get('CUSTOM_ID')
    return None

def _add_id_to_path(path, location_id):
    """Adds location_id before the file extension."""
    if location_id:
        p = Path(path)
        return p.parent / f"{p.stem}_{location_id}{p.suffix}"
    return path

def extract_charging_data(strategy):
    """
    Extract charging data for a specified strategy.
    
    Parameters:
    -----------
    strategy : str
        The charging strategy name (e.g., "T_min", "Hub", or "Konstant")
    
    Returns:
    --------
    tuple
        - lastgang_df: DataFrame with Leistung_Total, Tag, Zeit columns
        - stations_count: Dictionary with counts of each charging station type
    """
    # Construct file path for simplified charging data
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "load", f"simplified_charging_data_{strategy}.json"
    )
    
    try:
        # Load the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Extract charging station counts
        stations_count = {}
        if "metadata" in data and "charging_stations" in data["metadata"]:
            for station_type, info in data["metadata"]["charging_stations"].items():
                if "count" in info:
                    stations_count[station_type] = info["count"]
        
        # Extract Lastgang data with the required fields
        lastgang_data = []
        for entry in data.get("lastgang", []):
            # Only include entries that have all required fields
            if all(field in entry for field in ["Leistung_Total", "Tag", "Zeit"]):
                lastgang_data.append({
                    "Leistung_Total": entry["Leistung_Total"],
                    "Tag": entry["Tag"],
                    "Zeit": entry["Zeit"]
                })
        
        # Convert to DataFrame
        lastgang_df = pd.DataFrame(lastgang_data)
        
        if lastgang_df.empty:
            print(f"Warning: No valid Lastgang data found for strategy '{strategy}'.")
            
        return lastgang_df, stations_count
    
    except FileNotFoundError:
        print(f"Error: File not found for strategy '{strategy}'.")
        return pd.DataFrame(), {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file for strategy '{strategy}'.")
        return pd.DataFrame(), {}
    except Exception as e:
        print(f"Error: {str(e)}")
        return pd.DataFrame(), {}


def extract_charger_counts(strategy):
    """
    Extract the number of NCS, HPC, and MCS chargers for a given strategy.
    Loads the location_id specific configuration file.
    
    Args:
        strategy (str): The charging strategy (e.g., "T_min", "Konstant", "Hub").
        
    Returns:
        tuple: (ncs_count, hpc_count, mcs_count) or (0, 0, 0) if file/data not found.
    """
    # Get location_id
    location_id = _get_location_id()
    print(f"[data_extraction] Extracting charger counts for strategy: {strategy}, location_id: {location_id}")

    # Construct the base file path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # The config file is saved in the charginghub_setup output directory
    # Assuming it's saved relative to the project root or a known path
    # Let's assume it's in the 'results' directory based on previous steps
    # UPDATE: Based on charginghub_configuration.py, it saves to charginghub_setup/results
    config_file_base = os.path.join(base_dir, 'scripts', 'charginghub_setup', 'results', 'charging_config_base.json')
    
    # Add location_id to the file path
    config_file_with_id = _add_id_to_path(config_file_base, location_id)
    
    try:
        with open(config_file_with_id, 'r') as f:
            config_data = json.load(f)
            
        # Find the configuration for the specified strategy
        strategy_config = None
        for config_item in config_data:
            if config_item.get('strategy') == strategy:
                strategy_config = config_item
                break
        
        if strategy_config is None:
            print(f"Error: Strategy '{strategy}' not found in {config_file_with_id}")
            return 0, 0, 0
            
        # Extract charger counts
        ncs_count = strategy_config.get('Anzahl_NCS', 0)
        hpc_count = strategy_config.get('Anzahl_HPC', 0)
        mcs_count = strategy_config.get('Anzahl_MCS', 0)
        
        print(f"Successfully extracted charger counts from {config_file_with_id}: NCS={ncs_count}, HPC={hpc_count}, MCS={mcs_count}")
        return ncs_count, hpc_count, mcs_count
        
    except FileNotFoundError:
        print(f"Error: Charger configuration file not found at {config_file_with_id}. Check if ID-specific file exists.")
        return 0, 0, 0
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {config_file_with_id}.")
        return 0, 0, 0
    except Exception as e:
        print(f"Error extracting charger counts from {config_file_with_id}: {e}")
        return 0, 0, 0

# Example usage (optional)
if __name__ == "__main__":
    # Manually set a test ID if needed via environment variable or Config
    # os.environ['CHARGING_HUB_CUSTOM_ID'] = 'test123' 
    # Config.RESULT_NAMING['USE_CUSTOM_ID'] = True
    # Config.RESULT_NAMING['CUSTOM_ID'] = 'test123'
    
    for strat in ["T_min", "Konstant", "Hub"]:
        print(f"\n--- Testing strategy: {strat} ---")
        ncs, hpc, mcs = extract_charger_counts(strat)
        print(f"  Charger counts: NCS={ncs}, HPC={hpc}, MCS={mcs}")


