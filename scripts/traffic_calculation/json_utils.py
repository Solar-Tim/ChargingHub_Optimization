"""
Utility functions for JSON data handling and transformation.
"""

import json
import pandas as pd
import numpy as np
import datetime
import os
from pathlib import Path

def dataframe_to_json(df, output_path, metadata=None, structure_type=None):
    """
    Convert DataFrame to a well-structured JSON file with metadata.
    
    Args:
        df: DataFrame to convert
        output_path: Path to save the JSON file
        metadata: Optional dictionary of metadata to include
        structure_type: Optional string indicating specific structure to use
    """
    # Create directory if it doesn't exist
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Default metadata
    if metadata is None:
        metadata = {}
        
    metadata.update({
        "created_at": datetime.datetime.now().isoformat(),
        "rows": len(df),
        "columns": list(df.columns)
    })
    
    # Base JSON structure
    result = {
        "metadata": metadata,
        "data": {}
    }
    
    # Apply specific structure based on type
    if structure_type == "breaks":
        # Group breaks by type with summaries
        short_breaks = df[df['Break_Type'] == 'short']
        long_breaks = df[df['Break_Type'] == 'long']
        
        result["data"] = {
            "summary": {
                "total_breaks": len(df),
                "short_breaks_count": len(short_breaks),
                "long_breaks_count": len(long_breaks),
                "total_break_volume": df['Break_Number'].sum(),
                "short_breaks_volume": short_breaks['Break_Number'].sum(),
                "long_breaks_volume": long_breaks['Break_Number'].sum()
            },
            "breaks": json.loads(df.to_json(orient='records'))
        }
    
    elif structure_type == "demand":
        # Structure charging demand by year and type
        result["data"] = {
            "location": {
                "latitude": df['Breitengrad'].iloc[0] if 'Breitengrad' in df else None,
                "longitude": df['Laengengrad'].iloc[0] if 'Laengengrad' in df else None
            },
            "breaks": {},
            "charging_demand": {},
            "daily_demand": {}
        }
        
        # Extract break counts
        break_columns = [col for col in df.columns if "breaks" in col]
        for col in break_columns:
            result["data"]["breaks"][col] = df[col].iloc[0]
        
        # Extract charging demand by year and type
        demand_columns = [col for col in df.columns if "HPC_" in col or "NCS_" in col]
        years = sorted(set(col.split('_')[1] for col in demand_columns))
        
        for year in years:
            result["data"]["charging_demand"][year] = {
                "HPC": df[f'HPC_{year}'].iloc[0],
                "NCS": df[f'NCS_{year}'].iloc[0]
            }
        
        # Extract daily demand if available
        days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        for day in days:
            if f"{day}_HPC" in df and f"{day}_NCS" in df:
                result["data"]["daily_demand"][day] = {
                    "HPC": df[f'{day}_HPC'].iloc[0],
                    "NCS": df[f'{day}_NCS'].iloc[0],
                    "distribution_factor": df[day].iloc[0] if day in df else None
                }
    
    elif structure_type == "toll_midpoints":
        # Structure toll section data with geographic info
        result["data"]["toll_sections"] = json.loads(df.to_json(orient='records'))
        result["data"]["summary"] = {
            "section_count": len(df),
            "highways": list(df['Bundesfernstraße'].unique()) if 'Bundesfernstraße' in df else []
        }
    
    elif structure_type == "charging_sessions":
        # For daily charging sessions breakdown
        result["data"] = {
            "daily_sessions": {},
            "weekly_total": {},
            "annual_projection": {}
        }
        
        # Process each day (excluding the Total row)
        for idx, row in df.loc[df.index != 'Total'].iterrows():
            result["data"]["daily_sessions"][idx] = {
                "HPC": float(row['HPC_Sessions']),
                "NCS": float(row['NCS_Sessions'])
            }
        
        # Get the weekly totals
        if 'Total' in df.index:
            total_row = df.loc['Total']
            result["data"]["weekly_total"] = {
                "HPC": float(total_row['HPC_Sessions']),
                "NCS": float(total_row['NCS_Sessions'])
            }
            
            # Calculate annual projection (weeks per year from metadata if available)
            weeks_per_year = metadata.get('weeks_per_year', 52)
            result["data"]["annual_projection"] = {
                "HPC": float(total_row['HPC_Sessions'] * weeks_per_year),
                "NCS": float(total_row['NCS_Sessions'] * weeks_per_year),
                "weeks_per_year": weeks_per_year
            }
    
    else:
        # Default structure - convert dataframe to records
        result["data"]["records"] = json.loads(df.to_json(orient='records'))
    
    # Handle NaN values for JSON serialization
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, pd.Series):
                return obj.tolist()
            if pd.isna(obj):
                return None
            return super(NpEncoder, self).default(obj)
    
    # Write to file with pretty formatting
    with open(output_path, 'w') as f:
        json.dump(result, f, cls=NpEncoder, indent=2)

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
    
# ------------------- Clear Terminal -------------------
def clear_terminal():
    os.system('cls')