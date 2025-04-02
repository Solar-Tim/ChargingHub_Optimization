import pandas as pd
import numpy as np
import os

def load_charging_hub_profile(file_path=None):
    """
    Load the charging hub load profile from CSV data.
    
    Args:
        file_path (str, optional): Path to the load profile CSV file. If None, 
                                   uses the default path.
    
    Returns:
        tuple: (load_profile, timestamps) where load_profile is a list of power values in kW
               and timestamps is a list of time values in minutes
    """
    if file_path is None:
        # Default path relative to the project structure
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(base_dir, 'data', 'load', 'lastgang_Hub.csv')
    
    # Load the CSV file with proper delimiter
    try:
        df = pd.read_csv(file_path, delimiter=';')
        print(f"Successfully loaded data from: {file_path}")
    except Exception as e:
        print(f"Error loading data: {e}")
        return [], []
    
    # Extract time values and load values
    timestamps = df['time (5min steps)'].values  # Time in minutes
    load_profile = df['Last'].values  # Load in kW
    
    print(f"Loaded {len(load_profile)} data points for charging hub profile")
    
    return load_profile.tolist(), timestamps.tolist()

def load_data(strategy):
    """
    Load load profile data based on the specified strategy.
    
    Args:
        strategy (str): The charging strategy to use. Supports "T_min", "Konstant", and "Hub".
    
    Returns:
        tuple: (load_profile, timestamps) for the selected strategy
    """
    # Define valid strategies
    valid_strategies = ["T_min", "Konstant", "Hub"]
    
    if strategy in valid_strategies:
        # Generate file path for the requested strategy
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(base_dir, 'data', 'load', f'lastgang_{strategy}.csv')
        
        # Try to load the data for the specified strategy
        try:
            return load_charging_hub_profile(file_path)
        except Exception as e:
            print(f"Error loading data for strategy '{strategy}': {e}")
            print("Falling back to Hub strategy.")
    else:
        print(f"Strategy '{strategy}' not implemented. Falling back to Hub strategy.")
    
    # Fallback to Hub strategy
    return load_charging_hub_profile()

if __name__ == "__main__":
    # Test the data loading functions
    load_profile, timestamps = load_charging_hub_profile()
    print(f"First 5 timestamps: {timestamps[:5]}")
    print(f"First 5 load values: {load_profile[:5]}")
    print(f"Max load: {max(load_profile)} kW")