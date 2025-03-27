"""
Utility functions for JSON data handling and transformation.
"""

import json
import pandas as pd
import numpy as np
import datetime
import os
from config_demand import get_breaks_column, get_charging_column, year
from pathlib import Path

def dataframe_to_json(df, output_path, metadata=None, structure_type='demand'):
    """
    Convert a DataFrame to a clean JSON structure and save it to a file.
    
    Args:
        df: DataFrame with traffic data
        output_path: Path to save the output file
        metadata: Dictionary with metadata
        structure_type: Type of structure to create ('demand', 'charging_sessions', etc.)
    """
    # Create initial data structure
    data_dict = {"metadata": metadata or {}, "data": {}}
    
    if structure_type == 'demand':
        # Extract breaks data for all years
        breaks_data = {}
        for break_type in ["short", "long"]:
            for yr in ["2030", "2035", "2040"]:
                # Try year-specific column first
                col_name = f"{break_type}_breaks_{yr}"
                if col_name in df.columns:
                    breaks_data[col_name] = df[col_name].iloc[0] if not df.empty else 0
                else:
                    # Fall back to general column if needed
                    from config_demand import get_breaks_column
                    general_col = get_breaks_column(break_type)
                    if general_col in df.columns:
                        breaks_data[col_name] = df[general_col].iloc[0] if not df.empty else 0
        
        data_dict["data"]["breaks"] = breaks_data
        
        # Extract charging demand for all years
        charging_demand = {}
        for yr in ["2030", "2035", "2040"]:
            hpc_col = f"HPC_{yr}"
            ncs_col = f"NCS_{yr}"
            if hpc_col in df.columns and ncs_col in df.columns:
                charging_demand[yr] = {
                    "HPC": df[hpc_col].iloc[0] if not df.empty else 0,
                    "NCS": df[ncs_col].iloc[0] if not df.empty else 0
                }
        
        data_dict["data"]["charging_demand"] = charging_demand
        
        # Extract daily demand pattern for all years
        days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        daily_demand = {}
        for day in days:
            if day in df.columns:
                daily_info = {
                    "distribution_factor": df[day].iloc[0] if not df.empty else 0
                }
                
                # Add HPC and NCS values for each year
                for yr in ["2030", "2035", "2040"]:
                    # Try year-specific day columns first
                    hpc_day_col = f"{day}_HPC_{yr}"
                    ncs_day_col = f"{day}_NCS_{yr}"
                    
                    # Fall back to general day columns if needed
                    if hpc_day_col not in df.columns:
                        hpc_day_col = f"{day}_HPC"
                    if ncs_day_col not in df.columns:
                        ncs_day_col = f"{day}_NCS"
                    
                    if hpc_day_col in df.columns:
                        daily_info[f"HPC_{yr}"] = df[hpc_day_col].iloc[0] if not df.empty else 0
                    if ncs_day_col in df.columns:
                        daily_info[f"NCS_{yr}"] = df[ncs_day_col].iloc[0] if not df.empty else 0
                
                daily_demand[day] = daily_info
        
        data_dict["data"]["daily_demand"] = daily_demand
    
    # Other structure types remain unchanged
    elif structure_type == 'charging_sessions':
        data_dict["data"] = df.to_dict(orient='index')
    
    elif structure_type == 'toll_midpoints':
        data_dict["data"]["toll_sections"] = df.to_dict(orient='records')
    
    elif structure_type == 'breaks':
        data_dict["data"] = df.to_dict(orient='records')
    
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
        structure_type: Type of structure to create ('demand', 'charging_sessions', etc.)
        
    Returns:
        Dict with cleaned structure
    """
    if structure_type == 'demand':
        # Create new demand structure with all forecast years
        clean_data = {
            "metadata": {
                "forecast_years": data_dict.get("metadata", {}).get("forecast_years", ["2030", "2035", "2040"]),
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
            "breaks": {},
            "charging_demand": {},
            "daily_distribution": []
        }
        
        # Add break data for all years
        breaks_data = data_dict.get("data", {}).get("breaks", {})
        for break_type in ["short", "long"]:
            for year in ["2030", "2035", "2040"]:
                break_key = f"{break_type}_breaks_{year}"
                
                # Try to get the specific year's break data
                if break_key in breaks_data:
                    clean_data["data"]["breaks"][break_key] = round(breaks_data[break_key])
                else:
                    # If not found, use the column from the dataframe if available
                    generic_key = get_breaks_column(break_type)
                    if generic_key in breaks_data:
                        clean_data["data"]["breaks"][break_key] = round(breaks_data[generic_key])
        
        # Add charging demand data for all years
        daily_demand = data_dict.get("data", {}).get("daily_demand", {})
        charging_demand = data_dict.get("data", {}).get("charging_demand", {})
        
        for target_year in ["2030", "2035", "2040"]:
            # Try to get from charging_demand structure
            if target_year in charging_demand:
                clean_data["data"]["charging_demand"][target_year] = {
                    "HPC": round(charging_demand[target_year].get("HPC", 0)),
                    "NCS": round(charging_demand[target_year].get("NCS", 0))
                }
            else:
                # Calculate from columns if available
                hpc_col = f"HPC_{target_year}"
                ncs_col = f"NCS_{target_year}"
                
                hpc_value = 0
                ncs_value = 0
                
                # Check in daily_demand first
                for day, day_data in daily_demand.items():
                    if hpc_col in day_data:
                        hpc_value += day_data[hpc_col]
                    if ncs_col in day_data:
                        ncs_value += day_data[ncs_col]
                
                # If no daily values found, check direct columns
                if hpc_value == 0 and ncs_value == 0:
                    for key, val in data_dict.get("data", {}).items():
                        if key == hpc_col:
                            hpc_value = val
                        elif key == ncs_col:
                            ncs_value = val
                
                clean_data["data"]["charging_demand"][target_year] = {
                    "HPC": round(hpc_value),
                    "NCS": round(ncs_value)
                }
        
        # Add daily distribution data
        daily_demand = data_dict.get("data", {}).get("daily_demand", {})
        for day, values in daily_demand.items():
            day_data = {
                "day": day,
                "distribution_factor": values.get("distribution_factor", 0),
            }
            
            # Add charging demand for each day for all years
            for target_year in ["2030", "2035", "2040"]:
                hpc_col = f"HPC_{target_year}"
                ncs_col = f"NCS_{target_year}"
                
                # Try to get specific year values or use default
                day_data[hpc_col] = round(values.get(hpc_col, 0))
                day_data[ncs_col] = round(values.get(ncs_col, 0))
            
            clean_data["data"]["daily_distribution"].append(day_data)
    
    # Other structure types remain the same
    elif structure_type == 'charging_sessions':
        # Existing charging_sessions code
        clean_data = {
            "metadata": data_dict.get("metadata", {}),
            "data": []
        }
        
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
        # Existing toll_midpoints code
        clean_data = {
            "metadata": data_dict.get("metadata", {}),
            "data": {
                "toll_sections": data_dict.get("data", {}).get("toll_sections", [])
            }
        }
    
    elif structure_type == 'breaks':
        # Existing breaks code
        clean_data = {
            "metadata": data_dict.get("metadata", {}),
            "data": {
                "breaks": data_dict.get("data", {}) if isinstance(data_dict.get("data"), list) else []
            }
        }
            
    else:
        # Return original data if structure_type is not recognized
        clean_data = data_dict
        
    return clean_data

# ------------------- Clear Terminal -------------------
def clear_terminal():
    os.system('cls')