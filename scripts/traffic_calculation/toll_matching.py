"""
Functions for matching toll sections to locations, calculating distances,
and determining daily demand distributions.
"""

import pandas as pd
import numpy as np
import logging
from functools import wraps
from config_demand import DAY_MAPPING, GERMAN_DAYS, TIME, year, get_charging_column, validate_year

logger = logging.getLogger(__name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the Haversine distance (in km) between two points.
    """
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371  # Earth's radius in km
    return c * r

def standardize_coordinates(df, coord_columns):
    """
    Standardize coordinate columns to numeric values.
    
    Args:
        df: DataFrame containing coordinate columns
        coord_columns: List of column names containing coordinates
        
    Returns:
        DataFrame with standardized coordinate values
    """
    df = df.copy(deep=True)
    
    for col in coord_columns:
        if col not in df.columns:
            logger.warning(f"Column {col} not found in DataFrame")
            continue
            
        if df[col].dtype == 'object':
            # Replace comma with period for decimal separator
            df.loc[:, col] = df[col].str.replace(',', '.', regex=False)
        
        # Convert to numeric, coercing errors to NaN
        df.loc[:, col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

def find_nearest_traffic_point(lat, lon, df_mauttabelle, df_befahrung):
    """
    Find the nearest traffic measurement point for a given location.
    """
    # Make a copy to avoid SettingWithCopyWarning
    df_mauttabelle = df_mauttabelle.copy(deep=True)
    
    # Filter to only include Autobahn sections (not B-roads)
    if 'Bundesfernstraße' in df_mauttabelle.columns:
        df_mauttabelle = df_mauttabelle[~df_mauttabelle['Bundesfernstraße'].str.contains('B')]
    
    lat_col = 'Breite Von'
    lon_col = 'Länge Von'
    lat_end_col = 'Breite Nach'
    lon_end_col = 'Länge Nach'
    
    coord_cols = [lat_col, lon_col, lat_end_col, lon_end_col]
    # Standardize coordinates
    df_mauttabelle = standardize_coordinates(df_mauttabelle, coord_cols)
    
    df_mauttabelle = df_mauttabelle.dropna(subset=coord_cols)
    
    if df_mauttabelle.empty:
        raise ValueError("No valid coordinate data after filtering")
    
    df_mauttabelle.loc[:, 'mid_lat'] = (df_mauttabelle[lat_col] + df_mauttabelle[lat_end_col]) / 2
    df_mauttabelle.loc[:, 'mid_lon'] = (df_mauttabelle[lon_col] + df_mauttabelle[lon_end_col]) / 2
    
    df_mauttabelle.loc[:, 'distance'] = df_mauttabelle.apply(
        lambda row: haversine_distance(lat, lon, row['mid_lat'], row['mid_lon']),
        axis=1
    )
    
    closest_row = df_mauttabelle.loc[df_mauttabelle['distance'].idxmin()]
    section_id = int(closest_row['Abschnitts-ID'])
    highway = closest_row['Bundesfernstraße'] if 'Bundesfernstraße' in closest_row else "Unknown"
    logger.info(f"Nearest traffic point ID: {section_id} on {highway} at distance {closest_row['distance']:.2f} km")
    
    return section_id

def toll_section_matching_and_daily_demand(results_df, df_mauttabelle, df_befahrung):
    """
    Match toll sections to locations and calculate normalized daily demand.
    """
    # Make a deep copy to avoid SettingWithCopyWarning
    df_mauttabelle = df_mauttabelle.copy(deep=True)
    
    # Data cleaning
    df_mauttabelle = df_mauttabelle[~df_mauttabelle['Bundesfernstraße'].str.contains('B')]
    df_mauttabelle.loc[:, 'Bundesfernstraße'] = df_mauttabelle['Bundesfernstraße'].str.strip()
    
    # Standardize coordinate columns
    coord_cols = ['Länge Von', 'Länge Nach', 'Breite Von', 'Breite Nach']
    df_mauttabelle = standardize_coordinates(df_mauttabelle, coord_cols)
    
    # Pre-calculate midpoints for toll sections
    df_mauttabelle.loc[:, 'midpoint_laenge'] = (df_mauttabelle['Länge Von'] + df_mauttabelle['Länge Nach']) / 2
    df_mauttabelle.loc[:, 'midpoint_breite'] = (df_mauttabelle['Breite Von'] + df_mauttabelle['Breite Nach']) / 2
    
    weekdays = GERMAN_DAYS
    traffic_mapping = df_befahrung.set_index('Strecken-ID')
    df_mauttabelle = df_mauttabelle.join(traffic_mapping[weekdays], on='Abschnitts-ID', how='left')

    min_distances = []
    def find_closest_row(ausschreibung_row):
        laengengrad = ausschreibung_row['Laengengrad']
        breitengrad = ausschreibung_row['Breitengrad']
        
        # Check for missing coordinates
        if pd.isna(laengengrad) or pd.isna(breitengrad):
            logger.warning(f"Missing coordinates for row {ausschreibung_row.name}")
            return pd.Series(index=df_mauttabelle.columns)
        
        # Calculate Haversine distance instead of Euclidean distance
        df_mauttabelle['distance'] = df_mauttabelle.apply(
            lambda row: haversine_distance(breitengrad, laengengrad, row['midpoint_breite'], row['midpoint_laenge']),
            axis=1
        )
        
        min_idx = df_mauttabelle['distance'].idxmin()
        min_distances.append(df_mauttabelle.loc[min_idx, 'distance'])
        return df_mauttabelle.loc[min_idx]
        
    closest_rows = results_df.apply(find_closest_row, axis=1)
    results_df = pd.concat([results_df, closest_rows], axis=1)

    # Create a copy of results_df to avoid warnings
    results_df = results_df.copy(deep=True)
    
    # Ensure the forecast year is valid
    try:
        current_year = validate_year(year)
        logger.info(f"Calculating daily demand using {current_year} projections")
        
        weekly_totals = results_df[weekdays].sum(axis=1)
        for day in weekdays:
            # Handle division by zero
            results_df.loc[:, day] = results_df[day].div(weekly_totals, fill_value=0)
            
            # Use the dynamic column name function
            hpc_col = get_charging_column('HPC', current_year)
            ncs_col = get_charging_column('NCS', current_year)
            
            results_df.loc[:, f'{day}_HPC'] = (results_df[day] * results_df[hpc_col] / TIME['WEEKS_PER_YEAR']).round()
            results_df.loc[:, f'{day}_NCS'] = (results_df[day] * results_df[ncs_col] / TIME['WEEKS_PER_YEAR']).round()
    except ValueError as e:
        logger.error(f"Error in year validation: {e}")
        raise
    
    return results_df

def scale_charging_demand(reference_point_id, df_befahrung):
    """
    Scale charging demand for a single reference point based on traffic patterns.
    """
    reference_data = df_befahrung[df_befahrung['Strecken-ID'] == reference_point_id]
    if reference_data.empty:
        raise ValueError(f"Reference point ID {reference_point_id} not found")
        
    traffic_data = reference_data.iloc[0]
    total_traffic = sum(traffic_data[day] for day in GERMAN_DAYS)
    scaling_factors = {day: traffic_data[day] / total_traffic for day in GERMAN_DAYS}
    result = pd.DataFrame({
        'Weekday': [DAY_MAPPING[day] for day in GERMAN_DAYS],
        'ScalingFactor': [scaling_factors[day] for day in GERMAN_DAYS]
    })
    result.set_index('Weekday', inplace=True)
    return result

def scale_charging_sessions(reference_point_id, annual_hpc_sessions, annual_ncs_sessions, df_befahrung):
    """
    Calculate weekly charging sessions for HPC and NCS based on annual targets.
    """
    scaling_factors = scale_charging_demand(reference_point_id, df_befahrung)
    result = pd.DataFrame(index=scaling_factors.index)
    for day in result.index:
        scale = scaling_factors.loc[day, 'ScalingFactor']
        result.loc[day, 'HPC_Sessions'] = round(scale * annual_hpc_sessions / TIME['WEEKS_PER_YEAR'])
        result.loc[day, 'NCS_Sessions'] = round(scale * annual_ncs_sessions / TIME['WEEKS_PER_YEAR'])
    result.loc['Total', 'HPC_Sessions'] = result['HPC_Sessions'].sum()
    result.loc['Total', 'NCS_Sessions'] = result['NCS_Sessions'].sum()
    return result