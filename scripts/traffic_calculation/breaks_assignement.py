"""
Functions for processing breaks data, creating GeoDataFrames, performing spatial joins,
and calculating break distributions.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import logging
import os
from config_demand import SPATIAL, SCENARIOS, get_breaks_column, get_charging_column, year, validate_year
from json_utils import dataframe_to_json

logger = logging.getLogger(__name__)

def create_point_gdf(df, lon_col, lat_col, crs=SPATIAL['DEFAULT_CRS']):
    """Create a GeoDataFrame from latitude/longitude columns and transform to a target CRS."""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs=crs
    ).drop(columns=[lon_col, lat_col])
    return gdf.to_crs(epsg=int(SPATIAL['TARGET_CRS'].split(':')[1]))

def calculate_scenarios(df_location, grouped_short, grouped_long):
    """
    Calculate charging scenarios (e.g. for 2030, 2035, 2040) using break counts.
    """
    results_df = df_location.copy()
    
    # Store base break counts using the current year format for backward compatibility
    short_breaks_col = get_breaks_column('short')
    long_breaks_col = get_breaks_column('long')
    results_df[short_breaks_col] = grouped_short.get(0, 0)
    results_df[long_breaks_col] = grouped_long.get(0, 0)
    
    # Store break data for all years explicitly
    for target_year in SCENARIOS['TARGET_YEARS']:
        # Store break counts for each specific year
        results_df[f'short_breaks_{target_year}'] = grouped_short.get(0, 0)
        results_df[f'long_breaks_{target_year}'] = grouped_long.get(0, 0)
        
        # Calculate charging demand based on breaks for each year
        r_bev = SCENARIOS['R_BEV'][target_year]
        r_traffic = SCENARIOS['R_TRAFFIC'][target_year]
        results_df[f'HPC_{target_year}'] = grouped_short.get(0, 0) * r_bev * r_traffic
        results_df[f'NCS_{target_year}'] = grouped_long.get(0, 0) * r_bev * r_traffic
    
    return results_df

def assign_breaks_to_locations(df_location, df_breaks, nuts_data_file, buffer_radius):
    """
    Assign breaks to a single location based on spatial proximity.
    
    Parameters:
    -----------
    df_location : DataFrame
        DataFrame containing a single location with latitude and longitude columns
    df_breaks : DataFrame
        DataFrame containing breaks data
    nuts_data_file : str
        Path to the NUTS GeoPackage file
    buffer_radius : int
        Radius in meters for the buffer around location
        
    Returns:
    --------
    dict
        A dictionary containing:
        - 'results_df': DataFrame with the calculated charging demand scenarios
        - 'short_breaks_count': Total number of short breaks assigned to the location
        - 'long_breaks_count': Total number of long breaks assigned to the location
    """
    # Load Germany NUTS data
    gdf_deutschland_nuts1 = gpd.read_file(nuts_data_file, layer='nuts5000_n1')
    
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
    gdf_deutschland_nuts0 = gdf_deutschland_nuts0.to_crs(epsg=int(SPATIAL['TARGET_CRS'].split(':')[1]))
    
    # Spatial join: Filter breaks within Germany
    gdf_short_breaks_germany = gpd.sjoin(gdf_short_breaks, gdf_deutschland_nuts0, predicate='within', how='inner').reset_index(drop=True)
    gdf_long_breaks_germany = gpd.sjoin(gdf_long_breaks, gdf_deutschland_nuts0, predicate='within', how='inner').reset_index(drop=True)
    
    # Remove index_right if it exists
    gdf_short_breaks_germany = gdf_short_breaks_germany.drop(columns=['index_right'] if 'index_right' in gdf_short_breaks_germany.columns else [])
    gdf_long_breaks_germany = gdf_long_breaks_germany.drop(columns=['index_right'] if 'index_right' in gdf_long_breaks_germany.columns else [])
    
    # Prepare a clean GeoDataFrame for the location buffer
    gdf_location_kreis = gdf_location.copy()
    gdf_location_kreis['geometry'] = gdf_location['geometry'].buffer(buffer_radius)
    gdf_location_kreis = gdf_location_kreis.reset_index(drop=True)
    gdf_location_kreis['kreis_id'] = gdf_location_kreis.index
    
    # Assign breaks to the location using spatial join
    joined_short = gpd.sjoin(gdf_short_breaks_germany, gdf_location_kreis[['geometry', 'kreis_id']], predicate='within', how='left')
    grouped_short = joined_short.groupby('kreis_id')['Break_Number'].sum()
    
    joined_long = gpd.sjoin(gdf_long_breaks_germany, gdf_location_kreis[['geometry', 'kreis_id']], predicate='within', how='left')
    grouped_long = joined_long.groupby('kreis_id')['Break_Number'].sum()
    
    logger.info("Calculating scenarios for charging demand...")
    results_df = calculate_scenarios(df_location, grouped_short, grouped_long)
    
    # Calculate total break counts
    short_breaks_count = grouped_short.get(0, 0)  # Fixed missing variable
    long_breaks_count = grouped_long.get(0, 0)  # Fixed missing variable
    
    return {
        'results_df': results_df,
        'short_breaks_count': short_breaks_count,
        'long_breaks_count': long_breaks_count
    }