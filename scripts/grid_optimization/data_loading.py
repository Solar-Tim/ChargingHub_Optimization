import os
import sys
import pandas as pd
from pathlib import Path
import logging

# Add the project root to path to import from parent directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(project_root)

from config import Config

def get_location_id_suffix():
    """Get location ID suffix from config if available."""
    if Config.RESULT_NAMING.get('USE_CUSTOM_ID', False):
        return f"_{Config.RESULT_NAMING.get('CUSTOM_ID', '')}"
    return ""

def get_location_specific_filename(filename_pattern, location_id_suffix=None):
    """
    Construct a location-specific filename by adding the location ID suffix.
    
    Args:
        filename_pattern: Base filename pattern without location ID
        location_id_suffix: Optional explicit suffix. If None, will be determined from Config.
        
    Returns:
        Modified filename with location ID suffix
    """
    if location_id_suffix is None:
        location_id_suffix = get_location_id_suffix()
    
    if not location_id_suffix:
        return filename_pattern
        
    # Extract parts of the filename
    path_obj = Path(filename_pattern)
    new_name = f"{path_obj.stem}{location_id_suffix}{path_obj.suffix}"
    return str(path_obj.parent / new_name)

def load_charging_hub_profile(strategy=None):
    """
    Load charging hub profile data from CSV file output by demand_optimization.py.
    
    Args:
        strategy: Strategy name (T_min, Konstant, or Hub), defaults to 'Hub'
        
    Returns:
        tuple: (load_profile, timestamps)
    """
    if strategy is None:
        # Default to Hub strategy
        strategy = 'Hub'
    
    # Location ID suffix from Config
    location_suffix = get_location_id_suffix()
    
    # Define load directory
    load_dir = os.path.join(project_root, "data", "load")
    
    # Try to find the file with location suffix first
    # Look for files with the pattern lastgang_{strategy}{_location_id}.csv 
    filename = get_location_specific_filename(f"lastgang_{strategy}.csv", location_suffix)
    file_path = os.path.join(load_dir, filename)
    
    if not os.path.exists(file_path):
        # Try detailed file
        filename = get_location_specific_filename(f"lastgang_detailed_{strategy}.csv", location_suffix)
        file_path = os.path.join(load_dir, filename)
    
    if not os.path.exists(file_path):
        # Fallback to basic filename without strategy
        filename = get_location_specific_filename(f"lastgang.csv", location_suffix)
        file_path = os.path.join(load_dir, filename)
    
    if not os.path.exists(file_path):
        # Fallback to default demo file if location-specific files don't exist
        fallback_file = os.path.join(load_dir, "lastgang_demo.csv")
        print(f"Warning: Could not find location-specific file ({file_path}). Using fallback: {fallback_file}")
        if os.path.exists(fallback_file):
            file_path = fallback_file
        else:
            raise FileNotFoundError(f"Could not find any valid load profile file. Tried location-specific: {file_path} and fallback: {fallback_file}")
    
    try:
        # Load data from CSV
        print(f"Loading load profile data from: {file_path}")
        df = pd.read_csv(file_path, sep=';')
        
        if df.empty:
            print(f"Warning: Load profile file {file_path} is empty.")
            return [], []
        
        # Extract load column (might be 'Last' or 'Leistung_Total')
        load_column = 'Last' if 'Last' in df.columns else 'Leistung_Total'
        load_profile = df[load_column].values
        
        # Extract timestamps
        if 'time (5min steps)' in df.columns:
            timestamps = df['time (5min steps)'].values
        else:
            # If no timestamp column, generate 5-minute intervals
            timestamps = list(range(0, len(load_profile) * 5, 5))
        
        return load_profile, timestamps
    
    except Exception as e:
        print(f"Error loading charging hub profile: {e}")
        # Return empty arrays as fallback
        return [], []

def load_data(strategy=None):
    """
    Load the appropriate load profile data based on the strategy.
    
    Args:
        strategy: Strategy name (T_min, Konstant, or Hub)
        
    Returns:
        tuple: (load_profile, timestamps)
    """
    if strategy is None:
        # Default to Hub strategy
        return load_charging_hub_profile()
    
    if strategy in ['Hub', 'T_min', 'Konstant']:
        return load_charging_hub_profile(strategy)
    
    # Fallback to Hub strategy
    return load_charging_hub_profile()

if __name__ == "__main__":
    # Test the data loading functions
    load_profile, timestamps = load_charging_hub_profile()
    print(f"First 5 timestamps: {timestamps[:5]}")
    print(f"First 5 load values: {load_profile[:5]}")
    print(f"Max load: {max(load_profile)} kW")