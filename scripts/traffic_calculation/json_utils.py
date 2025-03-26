"""
Utility functions for JSON data handling and transformation.
"""

import json
import pandas as pd
import numpy as np
import datetime
import os
from pathlib import Path

def dataframe_to_json(df, output_path, metadata=None, structure_type='demand'):
    """
    Convert a DataFrame to a clean JSON structure and save it to a file.
    
    Args:
        df: DataFrame with traffic data
        output_path: Path to save the output file
        metadata: Dictionary with metadata
        structure_type: Type of structure to create ('demand', 'charging_sessions', or 'toll_midpoints')
    """
    # Create initial data structure
    data_dict = {"metadata": metadata or {}, "data": {}}
    
    if structure_type == 'demand':
        # Extract location data
        if 'location' in metadata:
            data_dict["data"]["location"] = metadata["location"]
        
        # Extract breaks data
        breaks_cols = [col for col in df.columns if 'breaks' in col.lower()]
        if breaks_cols:
            data_dict["data"]["breaks"] = {}
            for col in breaks_cols:
                data_dict["data"]["breaks"][col] = df[col].iloc[0] if not df.empty else 0
        
        # Extract charging demand
        years = ["2030", "2035", "2040"]
        data_dict["data"]["charging_demand"] = {}
        for yr in years:
            hpc_col = f"HPC_{yr}"
            ncs_col = f"NCS_{yr}"
            if hpc_col in df.columns and ncs_col in df.columns:
                data_dict["data"]["charging_demand"][yr] = {
                    "HPC": df[hpc_col].iloc[0] if not df.empty else 0,
                    "NCS": df[ncs_col].iloc[0] if not df.empty else 0
                }
        
        # Extract daily demand pattern
        days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        data_dict["data"]["daily_demand"] = {}
        for day in days:
            if day in df.columns:
                dist_factor = df[day].iloc[0] if not df.empty else 0
                hpc_val = df[f"{day}_HPC"].iloc[0] if f"{day}_HPC" in df.columns and not df.empty else 0
                ncs_val = df[f"{day}_NCS"].iloc[0] if f"{day}_NCS" in df.columns and not df.empty else 0
                
                data_dict["data"]["daily_demand"][day] = {
                    "distribution_factor": dist_factor,
                    "HPC": hpc_val,
                    "NCS": ncs_val
                }
    
    elif structure_type == 'charging_sessions':
        # For charging sessions, the DataFrame is already in the right format
        data_dict["data"] = df.to_dict(orient='index')
    
    elif structure_type == 'toll_midpoints':
        # For toll midpoints, directly add the dataframe records to the structure
        data_dict["data"]["toll_sections"] = df.to_dict(orient='records')
    
    # Apply cleaning function to create optimized structure
    clean_data = clean_json_structure(data_dict, structure_type)
    
    # Save to file
    import json
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=2)

def load_json_data(file_path):
    """
    Load data from a JSON file, handling the specific structure we create.
    
    Args:
        file_path: Path to the JSON file
    
    Returns:
        Dictionary containing the loaded data
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} does not exist")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    return data

def json_to_dataframe(json_path_or_data):
    """
    Convert a structured JSON file back to a pandas DataFrame.
    
    Args:
        json_path_or_data: Either a path to a JSON file or a loaded JSON dictionary
    
    Returns:
        DataFrame containing the data
    """
    if isinstance(json_path_or_data, (str, Path)):
        data = load_json_data(json_path_or_data)
    else:
        data = json_path_or_data
    
    # Determine structure by checking the content
    if "breaks" in data["data"] and isinstance(data["data"]["breaks"], list):
        # Break data in list format
        return pd.DataFrame(data["data"]["breaks"])
    
    elif "records" in data["data"]:
        # Default structure with records
        return pd.DataFrame(data["data"]["records"])
    
    elif "toll_sections" in data["data"]:
        # Toll section data
        return pd.DataFrame(data["data"]["toll_sections"])
    
    elif "daily_sessions" in data["data"]:
        # Daily charging sessions
        sessions = data["data"]["daily_sessions"]
        df = pd.DataFrame({day: {
            "HPC_Sessions": info["HPC"],
            "NCS_Sessions": info["NCS"]
        } for day, info in sessions.items()}).T
        
        # Add the weekly total if available
        if "weekly_total" in data["data"]:
            df.loc["Total"] = {
                "HPC_Sessions": data["data"]["weekly_total"]["HPC"],
                "NCS_Sessions": data["data"]["weekly_total"]["NCS"]
            }
            
        return df
    
    elif "charging_demand" in data["data"]:
        # Complex demand structure - convert to flattened dataframe
        location = data["data"]["location"]
        breaks = data["data"]["breaks"]
        charging_demand = data["data"]["charging_demand"]
        daily_demand = data["data"].get("daily_demand", {})
        
        # Create a single row dataframe with all the data
        df_data = {
            "Breitengrad": location.get("latitude"),
            "Laengengrad": location.get("longitude")
        }
        
        # Add breaks columns
        for break_type, count in breaks.items():
            df_data[break_type] = count
            
        # Add charging demand columns
        for year, values in charging_demand.items():
            for charge_type, value in values.items():
                df_data[f"{charge_type}_{year}"] = value
                
        # Add daily demand columns
        for day, values in daily_demand.items():
            df_data[day] = values.get("distribution_factor")
            df_data[f"{day}_HPC"] = values.get("HPC")
            df_data[f"{day}_NCS"] = values.get("NCS")
            
        return pd.DataFrame([df_data])
    
    else:
        # If we can't determine the structure, return the raw data
        return pd.DataFrame(data["data"])

def clean_json_structure(data_dict, structure_type='demand'):
    """
    Transform the raw data into a cleaned, optimized JSON structure.
    
    Args:
        data_dict: Original data dictionary with redundant information
        structure_type: Type of structure to create ('demand' or 'charging_sessions')
        
    Returns:
        Dict with cleaned structure
    """
    if structure_type == 'demand':
        # Create new demand structure
        clean_data = {
            "metadata": {
                "forecast_year": data_dict.get("metadata", {}).get("forecast_year", ""),
                "base_year": data_dict.get("metadata", {}).get("base_year", ""),
                "buffer_radius_m": data_dict.get("metadata", {}).get("buffer_radius_m", 0),
                "location": data_dict.get("metadata", {}).get("location", {}),
            }
        }
        
        # Add toll section information if available
        if "toll_section" in data_dict.get("metadata", {}):
            clean_data["metadata"]["toll_section"] = data_dict["metadata"]["toll_section"]
        
        # Add data section
        clean_data["data"] = {
            "breaks": {
                "short_breaks_2030": round(data_dict.get("data", {}).get("breaks", {}).get("short_breaks_2030", 0)),
                "long_breaks_2030": round(data_dict.get("data", {}).get("breaks", {}).get("long_breaks_2030", 0))
            },
            "charging_demand": {},
            "daily_distribution": []
        }
        
        # Rest of the function remains unchanged

    elif structure_type == 'charging_sessions':
        # Handle charging sessions format
        clean_data = {
            "metadata": data_dict.get("metadata", {}),
            "data": []
        }
        
        # Extract data from DataFrame format
        sessions_data = data_dict.get("data", {})
        for day, row in sessions_data.items():
            if day != 'Total':  # Skip the total row
                clean_data["data"].append({
                    "day": day,
                    "HPC_Sessions": round(row.get("HPC_Sessions", 0)),
                    "NCS_Sessions": round(row.get("NCS_Sessions", 0))
                })
        
        # Add a summary section
        if 'Total' in sessions_data:
            clean_data["summary"] = {
                "total_weekly_HPC": round(sessions_data.get('Total', {}).get("HPC_Sessions", 0)),
                "total_weekly_NCS": round(sessions_data.get('Total', {}).get("NCS_Sessions", 0)),
                "estimated_yearly_HPC": round(sessions_data.get('Total', {}).get("HPC_Sessions", 0) * 
                                          data_dict.get("metadata", {}).get("weeks_per_year", 52)),
                "estimated_yearly_NCS": round(sessions_data.get('Total', {}).get("NCS_Sessions", 0) * 
                                          data_dict.get("metadata", {}).get("weeks_per_year", 52))
            }
            
    elif structure_type == 'toll_midpoints':
        # Create structure for toll midpoints
        clean_data = {
            "metadata": data_dict.get("metadata", {}),
            "data": {
                "toll_sections": data_dict.get("data", {}).get("toll_sections", [])
            }
        }
            
    else:
        # Return original data if structure_type is not recognized
        clean_data = data_dict
        
    return clean_data

# ------------------- Clear Terminal -------------------
def clear_terminal():
    os.system('cls')