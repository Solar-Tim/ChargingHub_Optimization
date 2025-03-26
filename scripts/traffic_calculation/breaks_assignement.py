"""
Functions for processing breaks data, creating GeoDataFrames, performing spatial joins,
and calculating break distributions.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import logging
import os
from config_demand import SPATIAL, SCENARIOS, get_breaks_column, get_charging_column, BASE_YEAR, validate_year
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
    def calculate_year(df, year):
        r_bev = SCENARIOS['R_BEV'][year]
        r_traffic = SCENARIOS['R_TRAFFIC'][year]
        df[f'HPC_{year}'] = df['short_breaks_2030'] * r_bev * r_traffic
        df[f'NCS_{year}'] = df['long_breaks_2030'] * r_bev * r_traffic
        return df
        
    results_df = df_location.copy()
    results_df['short_breaks_2030'] = grouped_short.get(0, 0)
    results_df['long_breaks_2030'] = grouped_long.get(0, 0)
    
    for year in SCENARIOS['TARGET_YEARS']:
        results_df = calculate_year(results_df, year)
    
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
    
    # Create a buffer around the location
    gdf_location_buffer = gdf_location.copy()
    gdf_location_buffer['geometry'] = gdf_location['geometry'].buffer(buffer_radius)
    
    # Spatial join: Filter breaks within Germany
    gdf_short_breaks_germany = gpd.sjoin(gdf_short_breaks, gdf_deutschland_nuts0, predicate='within', how='inner').reset_index(drop=True)
    gdf_long_breaks_germany = gpd.sjoin(gdf_long_breaks, gdf_deutschland_nuts0, predicate='within', how='inner').reset_index(drop=True)
    
    # Remove index_right if it exists
    gdf_short_breaks_germany = gdf_short_breaks_germany.drop(columns=['index_right'] if 'index_right' in gdf_short_breaks_germany.columns else [])
    gdf_long_breaks_germany = gdf_long_breaks_germany.drop(columns=['index_right'] if 'index_right' in gdf_long_breaks_germany.columns else [])
    
    # For a single location, we don't need IDs - just find breaks within the buffer
    short_breaks_within = gpd.sjoin(gdf_short_breaks_germany, gdf_location_buffer[['geometry']], predicate='within')
    long_breaks_within = gpd.sjoin(gdf_long_breaks_germany, gdf_location_buffer[['geometry']], predicate='within')
    
    # Calculate total breaks
    short_breaks_count = short_breaks_within['Break_Number'].sum() if not short_breaks_within.empty else 0
    long_breaks_count = long_breaks_within['Break_Number'].sum() if not long_breaks_within.empty else 0
    
    logger.info(f"Found {short_breaks_count} short breaks and {long_breaks_count} long breaks within buffer")
    
    # Calculate estimated charging sessions based on base year BEV adoption rate
    r_bev_base = SCENARIOS['R_BEV'][BASE_YEAR]
    estimated_hpc_sessions = short_breaks_count * r_bev_base
    estimated_ncs_sessions = long_breaks_count * r_bev_base
    
    logger.info(f"Estimated potential charging demand for {BASE_YEAR} (with {r_bev_base*100:.0f}% BEV adoption):")
    logger.info(f"  - HPC potential: {estimated_hpc_sessions:.0f} sessions (from {short_breaks_count} short breaks)")
    logger.info(f"  - NCS potential: {estimated_ncs_sessions:.0f} sessions (from {long_breaks_count} long breaks)")
    logger.info(f"Note: Actual charging sessions will depend on BEV adoption rates, traffic growth, and charging behavior")
    
    # Create simplified results dataframe with direct counts using dynamic column names
    results_df = df_location.copy()
    results_df[get_breaks_column('short')] = short_breaks_count
    results_df[get_breaks_column('long')] = long_breaks_count
    
    # Calculate scenarios for charging demand
    for target_year in SCENARIOS['TARGET_YEARS']:
        try:
            # Validate year exists in scenarios
            validate_year(target_year)
            
            r_bev = SCENARIOS['R_BEV'][target_year]
            r_traffic = SCENARIOS['R_TRAFFIC'][target_year]
            
            # Use dynamic column names
            short_breaks_col = get_breaks_column('short')
            results_df[get_charging_column('HPC', target_year)] = results_df[short_breaks_col] * r_bev * r_traffic
            
            long_breaks_col = get_breaks_column('long')
            results_df[get_charging_column('NCS', target_year)] = results_df[long_breaks_col] * r_bev * r_traffic
        except ValueError as e:
            logger.warning(f"Skipping year {target_year}: {e}")
    
    # Also prepare a detailed breakdown of the assigned breaks
    if not short_breaks_within.empty or not long_breaks_within.empty:
        assigned_breaks = pd.concat([short_breaks_within, long_breaks_within], ignore_index=True)
        breaks_metadata = {
            'buffer_radius_m': buffer_radius,
            'location': {
                'latitude': df_location['Breitengrad'].iloc[0],
                'longitude': df_location['Laengengrad'].iloc[0]
            },
            'summary': {
                'short_breaks_count': short_breaks_count,
                'long_breaks_count': long_breaks_count,
                'estimated_hpc': estimated_hpc_sessions,
                'estimated_ncs': estimated_ncs_sessions,
                'base_year': BASE_YEAR,
                'bev_adoption_rate': r_bev_base
            }
        }
        
        # We could save this to a separate file if needed
        # dataframe_to_json(assigned_breaks, 'assigned_breaks.json', 
        #                   metadata=breaks_metadata, structure_type='breaks')
    
    return {
        'results_df': results_df,
        'short_breaks_count': short_breaks_count,
        'long_breaks_count': long_breaks_count
    }