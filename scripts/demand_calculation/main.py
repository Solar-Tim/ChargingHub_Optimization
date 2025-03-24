"""
Main script for charging hub demand calculation.
Orchestrates the overall workflow for break assignment, toll section matching, and demand calculation.
"""

import os
import sys
import logging
from functools import wraps
from pathlib import Path
from turtle import Turtle

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

from breaks_assignement import assign_breaks_to_locations
from toll_matching import toll_section_matching_and_daily_demand, find_nearest_traffic_point, scale_charging_sessions
from new_breaks import calculate_new_breaks

# ------------------- Setup Logging -------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ------------------- Define Directories -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))  # Up two levels to project root
INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "traffic", "raw_data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "traffic", "interim_results")
FINAL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "traffic", "final_traffic")

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
def load_csv_file(file_path, skiprows=0, sep=';', decimal=','):
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

def save_dataframe(df, output_path, sep=';', decimal=','):
    """Save DataFrame to CSV file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, sep=sep, decimal=decimal, index=False)
    logger.info(f"Data saved to {output_path}")

def main():
    # Load shared data files once
    logger.info("Loading shared data files...")
    maut_file = os.path.join(INPUT_DIR, 'Mauttabelle.xlsx')
    befahrungen_file = os.path.join(INPUT_DIR, 'Befahrungen_25_1Q.csv')
    df_mauttabelle = load_data_file(maut_file, skiprows=1)
    df_befahrung = load_data_file(befahrungen_file)
    
    # Create a single reference location
    df_location = pd.DataFrame({
        'Laengengrad': [6.214618953523452],
        'Breitengrad': [50.816300910540406]
    })
    
    # Load Germany NUTS data
    nuts_file = os.path.join(INPUT_DIR, "DE_NUTS5000.gpkg")
    
    # Decide whether to calculate new breaks or load existing ones
    neue_pausen = False  # Set to True to calculate new breaks, False to load existing ones
    if neue_pausen:
        logger.info("Calculating new breaks...")
        # Pass the correct input directory path
        df_breaks = calculate_new_breaks(base_path=INPUT_DIR)
        save_dataframe(df_breaks, os.path.join(OUTPUT_DIR, 'breaks.csv'))
    else:
        breaks_file = os.path.join(OUTPUT_DIR, 'breaks.csv')
        df_breaks = pd.read_csv(breaks_file, sep=';', decimal=',', index_col=0)
    
    # Process breaks and assign to locations
    logger.info("Assigning breaks to locations...")
    results_df, grouped_short, grouped_long = assign_breaks_to_locations(df_location, df_breaks, nuts_file)
    
    # Match toll sections and calculate daily demand
    logger.info("Matching toll sections and calculating daily demand...")
    # Create a deep copy of the dataframe to avoid SettingWithCopyWarning
    df_mauttabelle = df_mauttabelle.copy(deep=True)
    # Use .loc accessor for setting values
    df_mauttabelle.loc[:, 'Bundesfernstraße'] = df_mauttabelle['Bundesfernstraße'].str.strip()
    df_mauttabelle.loc[:, 'midpoint_laenge'] = (df_mauttabelle['Länge Von'] + df_mauttabelle['Länge Nach']) / 2
    df_mauttabelle.loc[:, 'midpoint_breite'] = (df_mauttabelle['Breite Von'] + df_mauttabelle['Breite Nach']) / 2
    results_df = toll_section_matching_and_daily_demand(results_df, df_mauttabelle, df_befahrung)
    final_output = os.path.join(FINAL_OUTPUT_DIR, "laden_mauttabelle.csv")
    save_dataframe(results_df, final_output)
    
    # Calculate robust charging demand scaling
    try:
        lat = df_location['Breitengrad'].iloc[0]
        lon = df_location['Laengengrad'].iloc[0]
        
        # Find nearest traffic point and scale charging sessions
        reference_id = find_nearest_traffic_point(lat, lon, df_mauttabelle, df_befahrung)
        logger.info(f"Reference toll section ID: {reference_id}")
        
        robust_sessions = scale_charging_sessions(reference_id, 
                                                annual_hpc_sessions=10000, 
                                                annual_ncs_sessions=3000,
                                                df_befahrung=df_befahrung)
        
        save_dataframe(robust_sessions, os.path.join(OUTPUT_DIR, "charging_demand.csv"))
        logger.info("Robust charging sessions scaling completed")
    except Exception as e:
        logger.error(f"Error in robust scaling: {e}")
    
    logger.info(f"Processing complete. Final results saved to {final_output}")

if __name__ == "__main__":
    main()