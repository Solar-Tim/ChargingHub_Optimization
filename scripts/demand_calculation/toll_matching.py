"""
Functions for matching toll sections to locations, calculating distances,
and determining daily demand distributions.
"""

import pandas as pd
import numpy as np
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Constants
WEEKS_PER_YEAR = 52
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

def find_nearest_traffic_point(lat, lon, df_mauttabelle, df_befahrung):
    """
    Find the nearest traffic measurement point for a given location.
    """
    # Filter to only include Autobahn sections (not B-roads)
    if 'Bundesfernstraße' in df_mauttabelle.columns:
        df_mauttabelle = df_mauttabelle[~df_mauttabelle['Bundesfernstraße'].str.contains('B')]
    
    lat_col = 'Breite Von'
    lon_col = 'Länge Von'
    lat_end_col = 'Breite Nach'
    lon_end_col = 'Länge Nach'
    
    coord_cols = [lat_col, lon_col, lat_end_col, lon_end_col]
    # Convert to numeric if not already
    for col in coord_cols:
        if df_mauttabelle[col].dtype == 'object':
            df_mauttabelle[col] = df_mauttabelle[col].str.replace(',', '.', regex=False)
        df_mauttabelle[col] = pd.to_numeric(df_mauttabelle[col], errors='coerce')
    
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
    section_id = int(closest_row['Abschnitts-ID'])
    highway = closest_row['Bundesfernstraße'] if 'Bundesfernstraße' in closest_row else "Unknown"
    logger.info(f"Nearest traffic point ID: {section_id} on {highway} at distance {closest_row['distance']:.2f} km")
    
    return section_id

def toll_section_matching_and_daily_demand(results_df, df_mauttabelle, df_befahrung):
    """
    Match toll sections to locations and calculate normalized daily demand.
    """
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
        result.loc[day, 'HPC_Sessions'] = round(scale * annual_hpc_sessions / WEEKS_PER_YEAR)
        result.loc[day, 'NCS_Sessions'] = round(scale * annual_ncs_sessions / WEEKS_PER_YEAR)
    result.loc['Total', 'HPC_Sessions'] = result['HPC_Sessions'].sum()
    result.loc['Total', 'NCS_Sessions'] = result['NCS_Sessions'].sum()
    return result