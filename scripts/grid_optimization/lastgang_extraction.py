import json
import pandas as pd
import os
from pathlib import Path

def extract_lastgang(file_path):
    """
    Extract lastgang data from JSON file and convert to pandas DataFrame.
    
    Args:
        file_path (str): Path to the JSON file
    
    Returns:
        dict: Dictionary containing:
            - lastgang_df: DataFrame with load profile data
            - metadata: Dictionary of metadata from the JSON
            - grid_connection_kw: Grid connection capacity in kW
    """
    # Load JSON file
    print(f"Attempting to open file: {file_path}")
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    # Extract lastgang data
    lastgang_data = data.get("lastgang", [])
    
    # Convert to DataFrame
    df = pd.DataFrame(lastgang_data)
    
    # Get metadata if available
    metadata = data.get("metadata", {})
    
    return {
        "lastgang_df": df,
        "metadata": metadata,
        "grid_connection_kw": metadata.get("grid_connection_kw")
    }

def save_lastgang_as_csv(data, output_path):
    """
    Save lastgang data to CSV.
    
    Args:
        data (dict): Dictionary returned by extract_lastgang
        output_path (str): Path to save the CSV file
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the DataFrame to CSV
    data["lastgang_df"].to_csv(output_path, index=False)
    print(f"Saved lastgang data to {output_path}")

if __name__ == "__main__":
    import sys
    
    # Define possible file paths
    default_paths = [
        # Relative path from current script
        "../charginghub_setup/data/epex/json_output/simplified_charging_data_100-100-100.json",
        # Alternative with absolute path
        str(Path(__file__).parent.parent / "charginghub_setup/data/epex/json_output/simplified_charging_data_100-100-100.json"),
        # Demo data
        str(Path(__file__).parent.parent.parent / "data/load/lastgang_demo.csv")
    ]
    
    # Get file path from command line or try default paths
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Try each default path until one exists
        file_path = None
        for path in default_paths:
            print(f"Checking if file exists: {path}")
            if os.path.isfile(path):
                file_path = path
                print(f"Using file: {file_path}")
                break
        
        if file_path is None:
            print("Error: Could not find a valid input file.")
            print(f"Current directory: {os.getcwd()}")
            print("Please provide a valid file path as a command line argument.")
            sys.exit(1)
    
    # Extract the data
    try:
        result = extract_lastgang(file_path)
        
        # Print basic information about the data
        print(f"Extracted {len(result['lastgang_df'])} lastgang data points")
        print(f"Grid connection: {result['grid_connection_kw']} kW")
        
        # Show a sample of the data
        if not result['lastgang_df'].empty:
            print("\nSample of lastgang data:")
            print(result['lastgang_df'].head())
        
        # Optionally save to CSV
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        file_name = Path(file_path).stem + "_extracted.csv"
        save_lastgang_as_csv(result, os.path.join(output_dir, file_name))
        
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)