#!/usr/bin/env python
"""
Master_V2.py
-------------
This version integrates the original break processing and toll matching with additional,
robust functions for file operations, scaling charging demand, and finding the nearest
traffic measurement point.
"""

import os
import sys
import logging
from pathlib import Path
from functools import wraps

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt

# ------------------- Setup Logging -------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ------------------- Define Directories -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "Input")
# Output directories are structured into subfolders similar to the original master code
OUTPUT_DIR = os.path.join(BASE_DIR, "Output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "1-Output"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "2-Output"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "3-Output"), exist_ok=True)

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
    if file_path.suffix.lower() in ['.csv']:
        return load_csv_file(file_path, skiprows=skiprows)
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

def convert_to_numeric(df, columns):
    """Convert specified columns to numeric values."""
    for col in columns:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def find_column(df, possible_names):
    """Find the first matching column from a list of possible names."""
    return next((col for col in possible_names if col in df.columns), None)

def save_dataframe(df, output_path, sep=';', decimal=','):
    """Save DataFrame to CSV file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, sep=sep, decimal=decimal, index=False)
    logger.info(f"Data saved to {output_path}")

# ------------------- Robust Charging Demand Functions -------------------
# Constants for day names and weeks per year
DAY_MAPPING = {
    'Montag': 'Monday',
    'Dienstag': 'Tuesday',
    'Mittwoch': 'Wednesday',
    'Donnerstag': 'Thursday', 
    'Freitag': 'Friday',
    'Samstag': 'Saturday',
    'Sonntag': 'Sunday'
}
GERMAN_DAYS = list(DAY_MAPPING.keys())
WEEKS_PER_YEAR = 52

def scale_charging_demand(reference_point_id, 
                          df_befahrung=None,
                          befahrungen_path=os.path.join(INPUT_DIR, 'Befahrungen_25_1Q.csv'), 
                          output_path=None):
    """
    Scale charging demand for a single reference point based on traffic patterns.
    """
    if df_befahrung is None:
        df_befahrung = load_data_file(befahrungen_path)
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
    if output_path:
        save_dataframe(result, output_path)
    return result

def scale_charging_sessions(reference_point_id, annual_hpc_sessions, annual_ncs_sessions,
                            df_befahrung=None, 
                            befahrungen_path=os.path.join(INPUT_DIR, 'Befahrungen_25_1Q.csv'), 
                            output_path=None):
    """
    Calculate weekly charging sessions for HPC and NCS based on annual targets.
    """
    scaling_factors = scale_charging_demand(reference_point_id, df_befahrung, befahrungen_path)
    result = pd.DataFrame(index=scaling_factors.index)
    for day in result.index:
        scale = scaling_factors.loc[day, 'ScalingFactor']
        result.loc[day, 'HPC_Sessions'] = round(scale * annual_hpc_sessions / WEEKS_PER_YEAR)
        result.loc[day, 'NCS_Sessions'] = round(scale * annual_ncs_sessions / WEEKS_PER_YEAR)
    result.loc['Total', 'HPC_Sessions'] = result['HPC_Sessions'].sum()
    result.loc['Total', 'NCS_Sessions'] = result['NCS_Sessions'].sum()
    if output_path:
        save_dataframe(result, output_path)
    return result

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

def find_nearest_traffic_point(lat, lon, 
                               df_mauttabelle=None, df_befahrung=None,
                               befahrungen_path=os.path.join(INPUT_DIR, 'Befahrungen_25_1Q.csv'), 
                               maut_path=os.path.join(INPUT_DIR, 'Mauttabelle.xlsx')):
    """
    Find the nearest traffic measurement point for a given location without requiring autobahn info.
    """
    if df_mauttabelle is None:
        df_mauttabelle = load_data_file(maut_path, skiprows=1)
    
    # Filter to only include Autobahn sections (not B-roads)
    if 'Bundesfernstraße' in df_mauttabelle.columns:
        df_mauttabelle = df_mauttabelle[~df_mauttabelle['Bundesfernstraße'].str.contains('B')]
    
    lat_col = find_column(df_mauttabelle, ['Breite Von', 'Latitude From'])
    lon_col = find_column(df_mauttabelle, ['Länge Von', 'Longitude From'])
    lat_end_col = find_column(df_mauttabelle, ['Breite Nach', 'Latitude To'])
    lon_end_col = find_column(df_mauttabelle, ['Länge Nach', 'Longitude To'])
    
    if not all([lat_col, lon_col, lat_end_col, lon_end_col]):
        raise ValueError("Coordinate columns not found")
    
    coord_cols = [lat_col, lon_col, lat_end_col, lon_end_col]
    df_mauttabelle = convert_to_numeric(df_mauttabelle, coord_cols)
    df_mauttabelle = df_mauttabelle.dropna(subset=coord_cols)
    
    if df_mauttabelle.empty:
        raise ValueError("No valid coordinate data after filtering")
    
    df_mauttabelle['mid_lat'] = (df_mauttabelle[lat_col] + df_mauttabelle[lat_end_col]) / 2
    df_mauttabelle['mid_lon'] = (df_mauttabelle[lon_col] + df_mauttabelle[lon_end_col]) / 2
    
    df_mauttabelle['distance'] = df_mauttabelle.apply(
        lambda row: haversine_distance(lat, lon, row['mid_lat'], row['mid_lon']),
        axis=1
    )
    
    closest_row = df_mauttabelle.loc[df_mauttabelle['distance'].idxmin()]
    section_id = int(closest_row['Abschnitts-ID']) # type: ignore
    highway = closest_row['Bundesfernstraße'] if 'Bundesfernstraße' in closest_row else "Unknown"
    logger.info(f"Nearest traffic point ID: {section_id} on {highway} at distance {closest_row['distance']:.2f} km")
    
    return section_id

def create_point_gdf(df, lon_col, lat_col, crs='EPSG:4326'):
    """Create a GeoDataFrame from latitude/longitude columns and transform to a target CRS."""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs=crs
    ).drop(columns=[lon_col, lat_col])
    return gdf.to_crs(epsg=32632)

def calculate_scenarios(df_location, grouped_short, grouped_long):
    """
    Calculate charging scenarios (e.g. for 2030, 2035, 2040) using break counts.
    """
    def calculate_year(df, year):
        r_bev_values = {'2030': 0.15, '2035': 0.5, '2040': 0.8}
        r_traffic_values = {'2030': 1.0, '2035': 1.06, '2040': 1.12}
        r_bev = r_bev_values[year]
        r_traffic = r_traffic_values[year]
        df[f'HPC_{year}'] = df['short_breaks_2030'] * r_bev * r_traffic
        df[f'NCS_{year}'] = df['long_breaks_2030'] * r_bev * r_traffic
        return df
    results_df = df_location.copy()
    results_df['short_breaks_2030'] = grouped_short.get(0, 0)
    results_df['long_breaks_2030'] = grouped_long.get(0, 0)
    for year in ['2030', '2035', '2040']:
        results_df = calculate_year(results_df, year)
    return results_df

# ------------------- Toll Section Matching and Daily Demand -------------------

def toll_section_matching_and_daily_demand(results_df, df_mauttabelle=None, df_befahrung=None):
    """
    Match toll sections to locations and calculate normalized daily demand without requiring Bundesautobahn.
    """
    if df_mauttabelle is None or df_befahrung is None:
        maut_file = os.path.join(INPUT_DIR, 'Mauttabelle.xlsx')
        befahrungen_file = os.path.join(INPUT_DIR, 'Befahrungen_25_1Q.csv')
        df_mauttabelle = load_data_file(maut_file, skiprows=1) if df_mauttabelle is None else df_mauttabelle
        df_befahrung = load_data_file(befahrungen_file) if df_befahrung is None else df_befahrung
    
    # Data cleaning
    df_mauttabelle = df_mauttabelle[~df_mauttabelle['Bundesfernstraße'].str.contains('B')]
    df_mauttabelle['Bundesfernstraße'] = df_mauttabelle['Bundesfernstraße'].str.strip()
    
    # Pre-calculate midpoints for toll sections
    df_mauttabelle['midpoint_laenge'] = (df_mauttabelle['Länge Von'] + df_mauttabelle['Länge Nach']) / 2
    df_mauttabelle['midpoint_breite'] = (df_mauttabelle['Breite Von'] + df_mauttabelle['Breite Nach']) / 2
    
    weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
    traffic_mapping = df_befahrung.set_index('Strecken-ID')
    df_mauttabelle = df_mauttabelle.join(traffic_mapping[weekdays], on='Abschnitts-ID', how='left')

    min_distances = []
    def find_closest_row(ausschreibung_row):
        laengengrad = ausschreibung_row['Laengengrad']
        breitengrad = ausschreibung_row['Breitengrad']
        
        # Calculate distance to all toll sections
        distances = np.sqrt(
            (df_mauttabelle['midpoint_laenge'] - laengengrad)**2 +
            (df_mauttabelle['midpoint_breite'] - breitengrad)**2
        )
        
        min_idx = distances.idxmin()
        min_distances.append(distances[min_idx])
        return df_mauttabelle.loc[min_idx]
        
    closest_rows = results_df.apply(find_closest_row, axis=1)
    results_df = pd.concat([results_df, closest_rows], axis=1)

    weekly_totals = results_df[weekdays].sum(axis=1)
    for day in weekdays:
        results_df[day] = results_df[day].div(weekly_totals, fill_value=0)
        results_df[f'{day}_HPC'] = (results_df[day] * results_df['HPC_2035'] / WEEKS_PER_YEAR).round()
        results_df[f'{day}_NCS'] = (results_df[day] * results_df['NCS_2035'] / WEEKS_PER_YEAR).round()
    
    return results_df

# ------------------- Main Workflow -------------------

def main():
    # Load shared data files once
    logger.info("Loading shared data files...")
    maut_file = os.path.join(INPUT_DIR, 'Mauttabelle.xlsx')
    befahrungen_file = os.path.join(INPUT_DIR, 'Befahrungen_25_1Q.csv')
    df_mauttabelle = load_data_file(maut_file, skiprows=1)
    df_befahrung = load_data_file(befahrungen_file)
    
    # --- Break Processing ---
    # Create a single reference location
    df_location = pd.DataFrame({
        'Laengengrad': [6.214618953523452],
        'Breitengrad': [50.816300910540406]
    })
    # Load Germany NUTS data
    nuts_file = os.path.join(INPUT_DIR, "DE_NUTS5000.gpkg")
    gdf_deutschland_nuts1 = gpd.read_file(nuts_file, layer='nuts5000_n1')
    
    # Decide whether to calculate new breaks or load existing ones
    neue_pausen = False
    if neue_pausen:
        logger.info("New break calculation not implemented in this version.")
        sys.exit(0)
    else:
        breaks_file = os.path.join(OUTPUT_DIR, '1-Output', 'breaks.csv')
        df_breaks = pd.read_csv(breaks_file, sep=';', decimal=',', index_col=0)
    
    # Split breaks into short and long types
    df_short_break = df_breaks[df_breaks['Break_Type'] == 'short']
    df_long_break = df_breaks[df_breaks['Break_Type'] == 'long']
    
    # Create GeoDataFrames for breaks and location
    gdf_short_breaks = create_point_gdf(df_short_break, 'Longitude_B', 'Latitude_B')
    gdf_long_breaks = create_point_gdf(df_long_break, 'Longitude_B', 'Latitude_B')
    gdf_location = create_point_gdf(df_location, 'Laengengrad', 'Breitengrad')
    
    # Prepare and transform Germany NUTS data
    gdf_deutschland_nuts0 = gdf_deutschland_nuts1.dissolve(by='NUTS_LEVEL')[['geometry']]
    gdf_deutschland_nuts0.reset_index(drop=True, inplace=True)
    gdf_short_breaks = gdf_short_breaks.to_crs(epsg=32632)
    gdf_long_breaks = gdf_long_breaks.to_crs(epsg=32632)
    gdf_location = gdf_location.to_crs(epsg=32632)
    gdf_deutschland_nuts0 = gdf_deutschland_nuts0.to_crs(epsg=32632)
    
    # Create a buffer around the location
    gdf_location_buffer = gdf_location.copy()
    gdf_location_buffer['geometry'] = gdf_location['geometry'].buffer(25000)
    gdf_location_buffer['kreis_id'] = gdf_location_buffer.index
    
    # Spatial join: Filter breaks within Germany
    gdf_short_breaks_germany = gpd.sjoin(gdf_short_breaks, gdf_deutschland_nuts0, predicate='within', how='inner').reset_index(drop=True)
    gdf_long_breaks_germany = gpd.sjoin(gdf_long_breaks, gdf_deutschland_nuts0, predicate='within', how='inner').reset_index(drop=True)
    gdf_short_breaks_germany = gdf_short_breaks_germany.drop(columns=['index_right'] if 'index_right' in gdf_short_breaks_germany.columns else [])
    gdf_long_breaks_germany = gdf_long_breaks_germany.drop(columns=['index_right'] if 'index_right' in gdf_long_breaks_germany.columns else [])
    
    # Prepare a clean GeoDataFrame for the location buffer
    gdf_location_kreis = gdf_location.copy()
    gdf_location_kreis['geometry'] = gdf_location['geometry'].buffer(25000)
    gdf_location_kreis = gdf_location_kreis.reset_index(drop=True)
    gdf_location_kreis['kreis_id'] = gdf_location_kreis.index
    
    # Assign breaks to the location using spatial join
    joined_short = gpd.sjoin(gdf_short_breaks_germany, gdf_location_kreis[['geometry', 'kreis_id']], predicate='within', how='left')
    grouped_short = joined_short.groupby('kreis_id')['Break_Number'].sum()
    
    joined_long = gpd.sjoin(gdf_long_breaks_germany, gdf_location_kreis[['geometry', 'kreis_id']], predicate='within', how='left')
    grouped_long = joined_long.groupby('kreis_id')['Break_Number'].sum()
    
    logger.info("Calculating scenarios for charging demand...")
    results_df = calculate_scenarios(df_location, grouped_short, grouped_long)
    # Removed intermediate Excel save
    
    # --- Toll Section Matching and Daily Demand Calculation ---
    
    logger.info("Matching toll sections and calculating daily demand...")
    results_df = toll_section_matching_and_daily_demand(results_df, df_mauttabelle, df_befahrung)
    final_output = os.path.join(OUTPUT_DIR, "3-Output", "ausschreibung_deutschlandnetz_laden_mauttabelle.csv")
    results_df.to_csv(final_output, sep=';', decimal=',', index=False)
    
    # --- New Robust Charging Demand Scaling Section ---
    lat = 50.816300910540406
    lon = 6.214618953523452
    
    try:
        # Call the modified function without the autobahn parameter
        reference_id = find_nearest_traffic_point(lat, lon, df_mauttabelle, df_befahrung)
        logger.info(f"Reference toll section ID: {reference_id}")
        robust_sessions = scale_charging_sessions(reference_id, annual_hpc_sessions=10000, 
                                                annual_ncs_sessions=3000,
                                                df_befahrung=df_befahrung,
                                                output_path=os.path.join(OUTPUT_DIR, "charging_demand.csv"))
        logger.info("Robust Charging Sessions Scaling Result:")
        logger.info(robust_sessions)
    except Exception as e:
        logger.error(f"Error in robust scaling: {e}")
    
    logger.info(f"Processing complete. Final results saved to {final_output}")

if __name__ == "__main__":
    main()
