"""
Module for preprocessing toll section data with midpoint calculations.
Creates a cached version of the toll section data with calculated geographic midpoints.
"""

import os
import logging
import pandas as pd
import datetime
from pathlib import Path
from json_utils import dataframe_to_json, json_to_dataframe

# Setup logging
logger = logging.getLogger(__name__)

def process_toll_midpoints(maut_file_path, output_path, skiprows=1, location_id=None):
    """
    Process toll section data to calculate midpoints and clean data.
    Saves a shared cache file (no location_id in filename).
    
    Args:
        maut_file_path (str): Path to the raw toll section data file
        output_path (str): Path where processed data will be saved (shared cache)
        skiprows (int): Number of header rows to skip in the input file
        location_id (str, optional): Location ID (used for metadata, not filename).
        
    Returns:
        pandas.DataFrame: Processed toll section data with midpoints
    """
    logger.info(f"Processing toll section midpoints from {maut_file_path} (shared cache)")
    
    # Load the raw toll section data
    if maut_file_path.endswith('.xlsx') or maut_file_path.endswith('.xls'):
        df_mauttabelle = pd.read_excel(maut_file_path, skiprows=skiprows)
    else:
        df_mauttabelle = pd.read_csv(maut_file_path, skiprows=skiprows)
    
    # Create a deep copy to avoid SettingWithCopyWarning
    df_mauttabelle = df_mauttabelle.copy(deep=True)
    
    # Process the data
    logger.info("Cleaning and calculating midpoints for toll sections")
    df_mauttabelle.loc[:, 'Bundesfernstraße'] = df_mauttabelle['Bundesfernstraße'].str.strip()
    df_mauttabelle.loc[:, 'midpoint_laenge'] = (df_mauttabelle['Länge Von'] + df_mauttabelle['Länge Nach']) / 2
    df_mauttabelle.loc[:, 'midpoint_breite'] = (df_mauttabelle['Breite Von'] + df_mauttabelle['Breite Nach']) / 2
    
    # Save processed data as structured JSON (shared cache, no ID in filename)
    metadata = {
        "source_file": os.path.basename(maut_file_path),
        "skiprows": skiprows,
        "processing_date": datetime.datetime.now().isoformat(),
        "location_id_triggering_process": location_id # Record which location triggered the processing
    }
    # Pass location_id=None to ensure the shared cache path is used
    dataframe_to_json(df_mauttabelle, output_path, metadata=metadata, structure_type='toll_midpoints', location_id=None)
    
    logger.info(f"Processed toll section midpoints saved to shared cache: {output_path}")
    
    return df_mauttabelle

def get_toll_midpoints(maut_file_path, output_path, skiprows=1, force_recalculate=False, location_id=None):
    """
    Get toll section data with midpoints, either from a shared cache or by recalculating.
    
    Args:
        maut_file_path (str): Path to the raw toll section data file
        output_path (str): Path where processed data is/will be saved (shared cache)
        skiprows (int): Number of header rows to skip in the input file
        force_recalculate (bool): Whether to force recalculation even if cached file exists
        location_id (str, optional): Location ID (passed to process_toll_midpoints if recalculating).
        
    Returns:
        pandas.DataFrame: Toll section data with midpoints
    """
    # Check if we need to process the data or can load from the shared cache
    # The cache file itself does not contain the location_id
    if force_recalculate or not os.path.exists(output_path):
        logger.info("Processing toll section midpoints (shared cache)...")
        # Pass location_id to processing function for metadata
        return process_toll_midpoints(maut_file_path, output_path, skiprows, location_id=location_id)
    else:
        logger.info(f"Loading preprocessed toll section midpoints from shared cache: {output_path}")
        # Load from shared cache (no location_id needed for path)
        return json_to_dataframe(output_path, location_id=None)