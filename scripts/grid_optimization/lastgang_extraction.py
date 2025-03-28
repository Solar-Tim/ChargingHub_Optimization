import json
import os
import pandas as pd


def extract_charging_data(strategy):
    """
    Extract charging data for a specified strategy.
    
    Parameters:
    -----------
    strategy : str
        The charging strategy name (e.g., "T_min", "Hub", or "Konstant")
    
    Returns:
    --------
    tuple
        - lastgang_df: DataFrame with Leistung_Total, Tag, Zeit columns
        - stations_count: Dictionary with counts of each charging station type
    """
    # Construct file path
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "load", f"simplified_charging_data_{strategy}.json"
    )
    
    try:
        # Load the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Extract charging station counts
        stations_count = {}
        if "metadata" in data and "charging_stations" in data["metadata"]:
            for station_type, info in data["metadata"]["charging_stations"].items():
                if "count" in info:
                    stations_count[station_type] = info["count"]
        
        # Extract Lastgang data with the required fields
        lastgang_data = []
        for entry in data.get("lastgang", []):
            # Only include entries that have all required fields
            if all(field in entry for field in ["Leistung_Total", "Tag", "Zeit"]):
                lastgang_data.append({
                    "Leistung_Total": entry["Leistung_Total"],
                    "Tag": entry["Tag"],
                    "Zeit": entry["Zeit"]
                })
        
        # Convert to DataFrame
        lastgang_df = pd.DataFrame(lastgang_data)
        
        if lastgang_df.empty:
            print(f"Warning: No valid Lastgang data found for strategy '{strategy}'.")
            
        return lastgang_df, stations_count
    
    except FileNotFoundError:
        print(f"Error: File not found for strategy '{strategy}'.")
        return pd.DataFrame(), {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file for strategy '{strategy}'.")
        return pd.DataFrame(), {}
    except Exception as e:
        print(f"Error: {str(e)}")
        return pd.DataFrame(), {}


if __name__ == "__main__":
    # Example usage
    strategy = "Hub"  # Change this to test other strategies: "T_min", "Konstant"
    lastgang, stations = extract_charging_data(strategy)
    
    if not lastgang.empty:
        print(f"\nLastgang data for {strategy} strategy:")
        print(lastgang.head())
    
    if stations:
        print(f"\nCharging station counts for {strategy} strategy:")
        for station_type, count in stations.items():
            print(f"{station_type}: {count}")
    else:
        print(f"\nNo charging station data found for {strategy} strategy.")