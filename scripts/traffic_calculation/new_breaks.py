"""
Functions for calculating new break points and distributions based on traffic patterns.
"""

import os
import time
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any
from functools import lru_cache
from config_demand import BREAKS, FILES, CSV, get_traffic_flow_column, BASE_YEAR
from json_utils import dataframe_to_json, json_to_dataframe

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1024)
def parse_edge_string(edge_str: str) -> list:
    """
    Parse a string containing edge IDs in square brackets into a list of integers.
    Example: '[12,13,14]' -> [12, 13, 14]
    
    Args:
        edge_str: String containing edge IDs in square brackets format
    
    Returns:
        List of edge IDs as integers
    """
    try:
        if not edge_str or edge_str == '[]':
            return []
        edges_parsed = list(map(int, edge_str.strip('[]').split(',')))
        return edges_parsed
    except Exception as e:
        logger.warning(f"Failed to parse edge string '{edge_str}': {e}")
        return []


def load_data(base_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load input data from CSV files.
    
    Args:
        base_path: Base directory path
    
    Returns:
        Tuple of (traffic_flow_df, edges_df, nodes_df)
    """
    # Use base_path directly rather than joining with 'Input'
    input_dir = base_path
    
    logger.info(f"Loading input data from {input_dir}...")
    traffic_flow_path = os.path.join(input_dir, os.path.basename(FILES['TRAFFIC_FLOW']))
    edges_path = os.path.join(input_dir, os.path.basename(FILES['EDGES']))
    nodes_path = os.path.join(input_dir, os.path.basename(FILES['NODES']))
    
    df_traffic_flow = pd.read_csv(traffic_flow_path, sep=',', decimal='.', index_col=0)
    df_edges = pd.read_csv(edges_path, sep=',', decimal='.', index_col=0)
    df_nodes = pd.read_csv(nodes_path, sep=',', decimal='.', index_col=0)
    
    logger.info(f"Loaded {len(df_traffic_flow)} traffic flows, {len(df_edges)} edges, {len(df_nodes)} nodes")
    
    return df_traffic_flow, df_edges, df_nodes


def filter_traffic_flows(df_traffic_flow: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter traffic flows into single-driver and two-driver categories.
    
    Args:
        df_traffic_flow: DataFrame with traffic flow data
    
    Returns:
        Tuple of (single_driver_df, two_driver_df)
    """
    max_singledriver_dist = BREAKS['MAX_DISTANCE_SINGLEDRIVER']
    
    # Calculate total distance once
    df_traffic_flow['total_distance'] = (
        df_traffic_flow['Distance_from_origin_region_to_E_road'] + 
        df_traffic_flow['Distance_within_E_road']
    )
    
    # Filter for single-driver trips
    single_driver_mask = (
        (df_traffic_flow['total_distance'] > 0) & 
        (df_traffic_flow['total_distance'] <= max_singledriver_dist) & 
        (df_traffic_flow['Traffic_flow_trucks_2030'] > 0)
    )
    
    # Filter for two-driver trips
    two_driver_mask = (
        (df_traffic_flow['total_distance'] > max_singledriver_dist) & 
        (df_traffic_flow['Traffic_flow_trucks_2030'] > 0)
    )
    
    df_single_driver = df_traffic_flow[single_driver_mask].copy().reset_index(drop=True)
    df_two_driver = df_traffic_flow[two_driver_mask].copy().reset_index(drop=True)
    
    logger.info(f"Filtered {len(df_single_driver)} single-driver and {len(df_two_driver)} two-driver trips")
    
    return df_single_driver, df_two_driver


def create_lookup_dictionaries(df_edges: pd.DataFrame, df_nodes: pd.DataFrame) -> Dict[str, Dict]:
    """
    Create lookup dictionaries for efficient data access.
    
    Args:
        df_edges: DataFrame with edge data
        df_nodes: DataFrame with node data
    
    Returns:
        Dictionary containing lookup dictionaries
    """
    return {
        'edge_length': df_edges.set_index('Network_Edge_ID')['Distance'].to_dict(),
        'edge_node_b': df_edges.set_index('Network_Edge_ID')['Network_Node_B_ID'].to_dict(),
        'node_lat': df_nodes.set_index('Network_Node_ID')['Network_Node_Y'].to_dict(),
        'node_lon': df_nodes.set_index('Network_Node_ID')['Network_Node_X'].to_dict()
    }


def process_single_driver_breaks(
    trip_edges_list: List[List[int]], 
    origin_distances: List[float],
    traffic_flows: List[float],
    lookups: Dict[str, Dict],
    random_seed: int = None
) -> Dict[str, List]:
    """
    Process breaks for single-driver trips using vectorized operations where possible.
    
    Args:
        trip_edges_list: List of edge ID lists for each trip
        origin_distances: List of distances from origin to E-road
        traffic_flows: List of traffic flows for each trip
        lookups: Dictionary with lookup dictionaries
        random_seed: Seed for random number generation (optional)
    
    Returns:
        Dictionary with break data
    """
    if random_seed is not None:
        np.random.seed(random_seed)
    
    trip_distance_threshold = BREAKS['DISTANCE_THRESHOLD']
    random_range = BREAKS['RANDOM_RANGE']
    
    # Pre-allocate results
    breaks_data = {
        'Trip_ID': [],
        'Driver': [],
        'Break_Nr': [],
        'Break_Type': [],
        'Edge': [],
        'Edge_length': [],
        'Node_B': [],
        'Latitude_B': [],
        'Longitude_B': [],
        'Break_Number': []
    }
    
    # Process each trip
    for trip_idx, edge_list in enumerate(trip_edges_list):
        if not edge_list:
            continue
            
        travel_distance = origin_distances[trip_idx]
        breaks = 0
        
        for edge_id in edge_list:
            travel_distance += lookups['edge_length'].get(edge_id, 0)
            
            # Random threshold with optimization to avoid generating a random number each time
            threshold = trip_distance_threshold + np.random.randint(*random_range)
            
            if travel_distance > threshold:
                travel_distance = 0
                breaks += 1
                
                break_edge_id = edge_id
                break_edge_length = lookups['edge_length'].get(break_edge_id, 0)
                break_node_id = lookups['edge_node_b'].get(edge_id, 0)
                break_node_lat = lookups['node_lat'].get(break_node_id, 0)
                break_node_lon = lookups['node_lon'].get(break_node_id, 0)
                break_traffic_number = traffic_flows[trip_idx]
                
                # Determine break type (odd = short, even = long)
                break_type = 'short' if breaks % 2 == 1 else 'long'
                
                # Append to results
                breaks_data['Trip_ID'].append(trip_idx)
                breaks_data['Driver'].append(1)
                breaks_data['Break_Nr'].append(breaks)
                breaks_data['Break_Type'].append(break_type)
                breaks_data['Edge'].append(break_edge_id)
                breaks_data['Edge_length'].append(break_edge_length)
                breaks_data['Node_B'].append(break_node_id)
                breaks_data['Latitude_B'].append(break_node_lat)
                breaks_data['Longitude_B'].append(break_node_lon)
                breaks_data['Break_Number'].append(break_traffic_number)
    
    return breaks_data


def process_two_driver_breaks(
    trip_edges_list: List[List[int]], 
    origin_distances: List[float],
    traffic_flows: List[float],
    lookups: Dict[str, Dict],
    random_seed: int = None
) -> Dict[str, List]:
    """
    Process breaks for two-driver trips.
    
    Args:
        trip_edges_list: List of edge ID lists for each trip
        origin_distances: List of distances from origin to E-road
        traffic_flows: List of traffic flows for each trip
        lookups: Dictionary with lookup dictionaries
        random_seed: Seed for random number generation (optional)
    
    Returns:
        Dictionary with break data
    """
    if random_seed is not None:
        np.random.seed(random_seed)
    
    trip_distance_threshold = BREAKS['DISTANCE_THRESHOLD']
    random_range = BREAKS['RANDOM_RANGE']
    short_breaks_before_long = BREAKS['TWO_DRIVER_SHORT_BREAKS_BEFORE_LONG']
    
    # Pre-allocate results
    breaks_data = {
        'Trip_ID': [],
        'Driver': [],
        'Break_Nr': [],
        'Break_Type': [],
        'Edge': [],
        'Edge_length': [],
        'Node_B': [],
        'Latitude_B': [],
        'Longitude_B': [],
        'Break_Number': []
    }
    
    # Process each trip
    for trip_idx, edge_list in enumerate(trip_edges_list):
        if not edge_list:
            continue
            
        travel_distance = origin_distances[trip_idx]
        breaks = 0
        breaks_reset = 0  # Counts short breaks until next long break
        
        for edge_id in edge_list:
            travel_distance += lookups['edge_length'].get(edge_id, 0)
            
            # Random threshold
            threshold = trip_distance_threshold + np.random.randint(*random_range)
            
            if travel_distance > threshold:
                travel_distance = 0
                breaks += 1
                
                # Get break location data
                break_edge_id = edge_id
                break_edge_length = lookups['edge_length'].get(break_edge_id, 0)
                break_node_id = lookups['edge_node_b'].get(edge_id, 0)
                break_node_lat = lookups['node_lat'].get(break_node_id, 0)
                break_node_lon = lookups['node_lon'].get(break_node_id, 0)
                break_traffic_number = traffic_flows[trip_idx]
                
                # Determine break type
                if breaks_reset <= short_breaks_before_long:
                    break_type = 'short'
                    breaks_reset += 1
                else:
                    break_type = 'long'
                    breaks_reset = 0
                
                # Append to results
                breaks_data['Trip_ID'].append(trip_idx)
                breaks_data['Driver'].append(2)
                breaks_data['Break_Nr'].append(breaks)
                breaks_data['Break_Type'].append(break_type)
                breaks_data['Edge'].append(break_edge_id)
                breaks_data['Edge_length'].append(break_edge_length)
                breaks_data['Node_B'].append(break_node_id)
                breaks_data['Latitude_B'].append(break_node_lat)
                breaks_data['Longitude_B'].append(break_node_lon)
                breaks_data['Break_Number'].append(break_traffic_number)
    
    return breaks_data


def calculate_new_breaks(base_path=None, random_seed=None, export=True):
    """
    Calculate new breaks based on traffic patterns.
    
    Args:
        base_path: Base directory path (defaults to script directory if None)
        random_seed: Seed for random number generation (optional)
        export: Whether to export the results to JSON (default: True)
    
    Returns:
        DataFrame containing break data
    """
    time_start = time.time()
    
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    logger.info("Starting new break calculation...")
    
    # 1. Load data
    df_traffic_flow, df_edges, df_nodes = load_data(base_path)
    
    # 2. Filter traffic flows
    df_single_driver, df_two_driver = filter_traffic_flows(df_traffic_flow)
    
    # 3. Parse edge strings to lists
    single_driver_edges = [
        parse_edge_string(s) for s in df_single_driver['Edge_path_E_road'].tolist()
    ]
    
    two_driver_edges = [
        parse_edge_string(s) for s in df_two_driver['Edge_path_E_road'].tolist()
    ]
    
    # 4. Create lookup dictionaries
    lookups = create_lookup_dictionaries(df_edges, df_nodes)
    
    # 5. Get lists of origin distances and traffic flows
    # Use dynamic column name based on configuration
    traffic_flow_column = get_traffic_flow_column()
    
    single_driver_origin_distances = df_single_driver['Distance_from_origin_region_to_E_road'].tolist()
    single_driver_traffic_flows = df_single_driver[traffic_flow_column].tolist()
    
    two_driver_origin_distances = df_two_driver['Distance_from_origin_region_to_E_road'].tolist()
    two_driver_traffic_flows = df_two_driver[traffic_flow_column].tolist()
    
    # 6. Process breaks
    logger.info("Processing single-driver breaks...")
    single_driver_breaks = process_single_driver_breaks(
        single_driver_edges,
        single_driver_origin_distances,
        single_driver_traffic_flows,
        lookups,
        random_seed
    )
    
    logger.info("Processing two-driver breaks...")
    two_driver_breaks = process_two_driver_breaks(
        two_driver_edges,
        two_driver_origin_distances,
        two_driver_traffic_flows,
        lookups,
        random_seed
    )
    
    # 7. Combine results
    all_breaks = {k: single_driver_breaks[k] + two_driver_breaks[k] for k in single_driver_breaks.keys()}
    df_breaks = pd.DataFrame(all_breaks)
    
    # 8. Sort and reset index
    df_breaks.sort_values(by=['Trip_ID', 'Break_Nr'], inplace=True)
    df_breaks.reset_index(drop=True, inplace=True)
    
    # 9. Generate unique Break_ID and select final columns
    df_breaks['Break_ID'] = df_breaks.index
    
    # Select and rearrange columns for final output
    final_columns = [
        'Break_ID', 'Latitude_B', 'Longitude_B', 'Break_Type', 'Break_Number'
    ]
    
    result_df = df_breaks[final_columns].copy()
    
    # 10. Export results if required
    if export:
        output_path = FILES['BREAKS_OUTPUT']
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save as JSON with structured format
        metadata = {
            'base_year': BASE_YEAR,
            'random_seed': random_seed,
            'calculation_time': time.time() - time_start
        }
        dataframe_to_json(result_df, output_path, metadata=metadata, structure_type='breaks')
        logger.info(f"Results exported to: {output_path}")
    
    # Log summary statistics
    short_breaks_count = len(df_breaks[df_breaks['Break_Type'] == 'short'])
    long_breaks_count = len(df_breaks[df_breaks['Break_Type'] == 'long'])
    logger.info(f"Generated {short_breaks_count} short breaks and {long_breaks_count} long breaks")
    
    time_end = time.time()
    logger.info(f"Break calculation completed in {time_end - time_start:.2f} seconds")
    
    return result_df


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run main function
    df_breaks = calculate_new_breaks()