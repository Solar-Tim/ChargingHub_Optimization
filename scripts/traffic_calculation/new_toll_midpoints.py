"""
Module for preprocessing toll section data with midpoint calculations.
Creates a cached version of the toll section data with calculated geographic midpoints.
"""

import os
import logging
import pandas as pd
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

def process_toll_midpoints(maut_file_path, output_path, skiprows=1):
    """
    Process toll section data to calculate midpoints and clean data.
    
    Args:
        maut_file_path (str): Path to the raw toll section data file
        output_path (str): Path where processed data will be saved
        skiprows (int): Number of header rows to skip in the input file
        
    Returns:
        pandas.DataFrame: Processed toll section data with midpoints
    """
    logger.info(f"Processing toll section midpoints from {maut_file_path}")
    
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
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Save processed data
    df_mauttabelle.to_csv(output_path, sep=';', decimal=',', index=False)
    logger.info(f"Processed toll section midpoints saved to {output_path}")
    
    return df_mauttabelle

def get_toll_midpoints(maut_file_path, output_path, skiprows=1, force_recalculate=False):
    """
    Get toll section data with midpoints, either from cache or by recalculating.
    
    Args:
        maut_file_path (str): Path to the raw toll section data file
        output_path (str): Path where processed data is/will be saved
        skiprows (int): Number of header rows to skip in the input file
        force_recalculate (bool): Whether to force recalculation even if cached file exists
        
    Returns:
        pandas.DataFrame: Toll section data with midpoints
    """
    # Check if we need to process the data or can load from cache
    if force_recalculate or not os.path.exists(output_path):
        logger.info("Processing toll section midpoints...")
        return process_toll_midpoints(maut_file_path, output_path, skiprows)
    else:
        logger.info(f"Loading preprocessed toll section midpoints from {output_path}")
        return pd.read_csv(output_path, sep=';', decimal=',')