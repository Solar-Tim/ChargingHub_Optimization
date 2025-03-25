"""
Main script for charging hub demand calculation.
Orchestrates the overall workflow for break assignment, toll section matching, and demand calculation.
"""

import os
import sys
import logging
from functools import wraps
from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from breaks_assignement import assign_breaks_to_locations
from toll_matching import toll_section_matching_and_daily_demand, find_nearest_traffic_point, scale_charging_sessions
from new_breaks import calculate_new_breaks
from new_toll_midpoints import get_toll_midpoints
from config_demand import (FILES, OUTPUT_DIR, FINAL_OUTPUT_DIR, DEFAULT_LOCATION, 
                           CHARGING_DEMAND, CSV, neue_pausen, neue_toll_midpoints, SPATIAL)

# ------------------- Setup Logging -------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create output directory structure
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)

# ------------------- Robust File Operation Functions -------------------
def safe_file_operation(func):
    """Decorator for safe file operations with proper error handling."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    return wrapper

@safe_file_operation
def load_csv_file(file_path, skiprows=0, sep=CSV['DEFAULT_SEPARATOR'], decimal=CSV['DEFAULT_DECIMAL']):
    """
    Load a CSV file with support for different encodings.
    """
    file_path = Path(file_path)
    logger.info(f"Loading CSV data from {file_path}")
    df = pd.read_csv(file_path, sep=sep, skiprows=skiprows, decimal=decimal)
    return df

@safe_file_operation
def load_data_file(file_path, skiprows=0):
    """
    Load data from CSV or Excel based on file extension.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} does not exist")
    
    suffix = file_path.suffix.lower()
    if suffix == '.csv':
        return load_csv_file(file_path, skiprows=skiprows)
    elif suffix in ['.xlsx', '.xls']:
        logger.info(f"Loading Excel data from {file_path}")
        return pd.read_excel(file_path, skiprows=skiprows)
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

def save_dataframe(df, output_path, sep=CSV['DEFAULT_SEPARATOR'], decimal=CSV['DEFAULT_DECIMAL']):
    """Save DataFrame to CSV file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, sep=sep, decimal=decimal, index=False)
    logger.info(f"Data saved to {output_path}")

def main():
    # Load shared data files once
    logger.info("Loading shared data files...")
    df_befahrung = load_data_file(FILES['BEFAHRUNGEN'])
    
    # Create a single reference location
    df_location = pd.DataFrame({
        'Laengengrad': [DEFAULT_LOCATION['LONGITUDE']],
        'Breitengrad': [DEFAULT_LOCATION['LATITUDE']]
    })
    
    # Handle breaks calculation
    if neue_pausen:
        logger.info("Calculating new breaks...")
        # Pass the correct input directory path
        input_dir = os.path.dirname(FILES['TRAFFIC_FLOW'])
        df_breaks = calculate_new_breaks(base_path=input_dir)
        save_dataframe(df_breaks, FILES['BREAKS_OUTPUT'])
    else:
        df_breaks = load_csv_file(FILES['BREAKS_OUTPUT'])
    
    # Handle toll midpoints calculation
    df_mauttabelle = get_toll_midpoints(
        FILES['MAUT_TABLE'], 
        FILES['TOLL_MIDPOINTS_OUTPUT'], 
        skiprows=1,
        force_recalculate=neue_toll_midpoints
    )
    
    # Process breaks and assign to locations
    logger.info("Assigning breaks to locations...")
    results_df, grouped_short, grouped_long = assign_breaks_to_locations(
        df_location, df_breaks, FILES['NUTS_DATA'], SPATIAL['BUFFER_RADIUS']
    )
    
    # Match toll sections and calculate daily demand
    logger.info("Matching toll sections and calculating daily demand...")
    results_df = toll_section_matching_and_daily_demand(results_df, df_mauttabelle, df_befahrung)
    save_dataframe(results_df, FILES['FINAL_OUTPUT'])
    
    # Calculate robust charging demand scaling
    try:
        lat = df_location['Breitengrad'].iloc[0]
        lon = df_location['Laengengrad'].iloc[0]
        
        # Find nearest traffic point and scale charging sessions
        reference_id = find_nearest_traffic_point(lat, lon, df_mauttabelle, df_befahrung)
        logger.info(f"Reference toll section ID: {reference_id}")
        
        robust_sessions = scale_charging_sessions(
            reference_id, 
            annual_hpc_sessions=CHARGING_DEMAND['DEFAULT_ANNUAL_HPC_SESSIONS'], 
            annual_ncs_sessions=CHARGING_DEMAND['DEFAULT_ANNUAL_NCS_SESSIONS'],
            df_befahrung=df_befahrung
        )
        
        save_dataframe(robust_sessions, FILES['CHARGING_DEMAND'])
        logger.info("Robust charging sessions scaling completed")
    except Exception as e:
        logger.error(f"Error in robust scaling: {e}")
    
    logger.info(f"Processing complete. Final results saved to {FILES['FINAL_OUTPUT']}")

if __name__ == "__main__":
    main()