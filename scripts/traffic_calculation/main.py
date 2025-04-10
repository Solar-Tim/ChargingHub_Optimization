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
from json_utils import dataframe_to_json, json_to_dataframe, load_json_data
from config_demand import (FILES, OUTPUT_DIR, FINAL_OUTPUT_DIR, get_default_location, CSV, 
                           neue_pausen, neue_toll_midpoints, SPATIAL, year, TIME, 
                           validate_year, get_charging_column, GERMAN_DAYS, SCENARIOS)

# ------------------- Setup Logging -------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create output directory structure
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)
logger.info("Starting charging hub demand calculation...")

# Validate the configured year
try:
    validate_year(year)
    logger.info(f"Using forecast year: {year}")
except ValueError as e:
    logger.error(f"Invalid year configuration: {e}")
    sys.exit(1)

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
    Load data from CSV, Excel, or JSON based on file extension.
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
    elif suffix == '.json':
        logger.info(f"Loading JSON data from {file_path}")
        return json_to_dataframe(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

def save_dataframe(df, output_path, sep=CSV['DEFAULT_SEPARATOR'], decimal=CSV['DEFAULT_DECIMAL']):
    """Save DataFrame to CSV file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, sep=sep, decimal=decimal, index=False)
    logger.info(f"Data saved to {output_path}")

def main():
    # Add debugging for location
    print(f"DEBUG [traffic_main]: Current location from get_default_location() = {get_default_location()}")
    
    # Load shared data files once
    logger.info("Loading shared data files...")
    df_befahrung = load_data_file(FILES['BEFAHRUNGEN'])
    
    # Create a single reference location using the function instead of static import
    current_location = get_default_location()
    df_location = pd.DataFrame({
        'Laengengrad': [current_location['LONGITUDE']],
        'Breitengrad': [current_location['LATITUDE']]
    })
    
    print(f"DEBUG [traffic_main]: df_location = {df_location.to_dict()}")
    
    # Handle breaks calculation
    if neue_pausen:
        logger.info("Calculating new breaks...")
        # Pass the correct input directory path
        input_dir = os.path.dirname(FILES['TRAFFIC_FLOW'])
        df_breaks = calculate_new_breaks(base_path=input_dir)
    else:
        # Load breaks from JSON if file exists, otherwise calculate new breaks
        try:
            df_breaks = json_to_dataframe(FILES['BREAKS_OUTPUT'])
        except FileNotFoundError:
            logger.warning(f"Breaks file not found at {FILES['BREAKS_OUTPUT']}. Calculating new breaks.")
            input_dir = os.path.dirname(FILES['TRAFFIC_FLOW'])
            df_breaks = calculate_new_breaks(base_path=input_dir)
    
    # Handle toll midpoints calculation
    df_mauttabelle = get_toll_midpoints(
        FILES['MAUT_TABLE'], 
        FILES['TOLL_MIDPOINTS_OUTPUT'], 
        skiprows=1,
        force_recalculate=neue_toll_midpoints
    )
    
    # Process breaks and assign to locations
    logger.info("Assigning breaks to locations...")
    breaks_results = assign_breaks_to_locations(
        df_location, df_breaks, FILES['NUTS_DATA'], SPATIAL['BUFFER_RADIUS']
    )
    
    # Extract components from the dictionary
    results_df = breaks_results['results_df']
    short_breaks_count = breaks_results['short_breaks_count']
    long_breaks_count = breaks_results['long_breaks_count']
    
    # Match toll sections and calculate daily demand
    logger.info("Matching toll sections and calculating daily demand...")
    results_df = toll_section_matching_and_daily_demand(results_df, df_mauttabelle, df_befahrung)
    
    # Find nearest traffic point and scale charging sessions
    lat = df_location['Breitengrad'].iloc[0]
    lon = df_location['Laengengrad'].iloc[0]
    reference_id = find_nearest_traffic_point(lat, lon, df_mauttabelle, df_befahrung)
    logger.info(f"Reference toll section ID: {reference_id}")

    # Create enriched metadata with toll section information
    current_location = get_default_location()
    metadata = {
        "forecast_years": SCENARIOS['TARGET_YEARS'],  # Include all target years
        "forecast_year": year,  # Keep current year for backward compatibility
        "base_year": year,
        "buffer_radius_m": SPATIAL['BUFFER_RADIUS'],
        "location": {
            "latitude": current_location['LATITUDE'],
            "longitude": current_location['LONGITUDE']
        },
        "toll_section": {
            "id": reference_id,
            "highway": df_mauttabelle[df_mauttabelle['Abschnitts-ID'] == reference_id]['Bundesfernstraße'].iloc[0] if reference_id in df_mauttabelle['Abschnitts-ID'].values else "Unknown"
        }
    }
    
    # Add traffic information if available
    if reference_id in df_befahrung['Strecken-ID'].values:
        traffic_data = df_befahrung[df_befahrung['Strecken-ID'] == reference_id].iloc[0]
        metadata["toll_section"]["traffic"] = {day: int(traffic_data[day]) for day in GERMAN_DAYS if day in traffic_data}

    # Save results as structured JSON
    dataframe_to_json(results_df, FILES['FINAL_OUTPUT'], metadata=metadata, structure_type='demand')
    
    # Calculate robust charging demand scaling
    try:
        # Use pre-calculated values from results_df with dynamic column names
        hpc_col = get_charging_column('HPC', year)
        ncs_col = get_charging_column('NCS', year)
        annual_hpc_sessions = results_df[hpc_col].iloc[0]  
        annual_ncs_sessions = results_df[ncs_col].iloc[0]

        logger.info(f"Using pre-calculated annual charging sessions - HPC: {annual_hpc_sessions}, NCS: {annual_ncs_sessions}")
        
        robust_sessions = scale_charging_sessions(
            reference_id, 
            annual_hpc_sessions=annual_hpc_sessions,
            annual_ncs_sessions=annual_ncs_sessions,
            df_befahrung=df_befahrung
        )
        
        # Add detailed logging of HPC sessions - FIXED: Removed duplicate logging section
        logger.info("Daily HPC charging sessions breakdown:")
        weekday_sessions = robust_sessions.loc[robust_sessions.index != 'Total', 'HPC_Sessions']
        for day, sessions in weekday_sessions.items():
            logger.info(f"  {day}: {sessions:.0f} sessions")
        
        weekly_total = robust_sessions.loc['Total', 'HPC_Sessions']
        yearly_total = weekly_total * TIME['WEEKS_PER_YEAR']
        
        logger.info(f"Weekly HPC sessions: {weekly_total:.0f}")
        logger.info(f"Yearly HPC sessions: {yearly_total:.0f} (estimated from weekly pattern)")
        
        # Save charging demand as structured JSON
        charging_metadata = {
            "reference_toll_section_id": reference_id,
            "weeks_per_year": TIME['WEEKS_PER_YEAR'],
            "forecast_year": year
        }
        dataframe_to_json(robust_sessions, FILES['CHARGING_DEMAND'], 
                          metadata=charging_metadata, structure_type='charging_sessions')
        
        logger.info("Scaling of charging sessions completed")
    except Exception as e:
        logger.error(f"Error in scaling: {e}")
    
    logger.info(f"Processing complete. Final results saved to {FILES['FINAL_OUTPUT']}")

if __name__ == "__main__":
    main()