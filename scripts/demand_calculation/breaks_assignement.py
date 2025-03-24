"""
Functions for processing breaks data, creating GeoDataFrames, performing spatial joins,
and calculating break distributions.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

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

def assign_breaks_to_locations(df_location, df_breaks, nuts_data_file, buffer_radius=25000):
    """
    Assign breaks to locations based on spatial proximity.
    
    Parameters:
    -----------
    df_location : DataFrame
        DataFrame containing location data with latitude and longitude columns
    df_breaks : DataFrame
        DataFrame containing breaks data
    nuts_data_file : str
        Path to the NUTS GeoPackage file
    buffer_radius : int, optional
        Radius in meters for the buffer around locations, defaults to 25000
        
    Returns:
    --------
    tuple
        (results_df, grouped_short, grouped_long) containing the calculated scenarios and 
        grouped break counts
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
    gdf_deutschland_nuts0 = gdf_deutschland_nuts0.to_crs(epsg=32632)
    
    # Create a buffer around the location
    gdf_location_buffer = gdf_location.copy()
    gdf_location_buffer['geometry'] = gdf_location['geometry'].buffer(buffer_radius)
    gdf_location_buffer['kreis_id'] = gdf_location_buffer.index
    
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
    
    return results_df, grouped_short, grouped_long