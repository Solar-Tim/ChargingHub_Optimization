import os
import json
import csv
import re

def extract_metrics_from_results(results_dir, csv_file):
    """
    Extract key metrics from optimization result JSON files and write them to a CSV file.
    
    Parameters:
    -----------
    results_dir : str
        Directory containing optimization result JSON files
    csv_file : str
        Path to the CSV file to update
    """
    # Check if CSV exists and create it with headers if not
    if not os.path.exists(csv_file):
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['ID', 'Strategy', 'Total Cost', 'Grid Load', 'Battery_Allowed', 'Battery_Size', 'Connection'])
    
    # Read existing entries to avoid duplicates
    existing_ids = set()
    try:
        with open(csv_file, 'r', newline='') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)  # Skip header
            for row in reader:
                if row and len(row) > 0:
                    # Create a unique identifier combining ID and strategy
                    if len(row) >= 2:
                        existing_ids.add(f"{row[0]}_{row[1]}")
    except Exception as e:
        print(f"Error reading existing CSV: {e}")
        # Continue with empty set if file couldn't be read
    
    # Find all result JSON files
    new_entries = []
    for filename in os.listdir(results_dir):
        if filename.endswith('.json') and 'optimization_' in filename:
            file_path = os.path.join(results_dir, filename)
            
            # Extract ID from filename (pattern: optimization_{id}_{strategy}_{battery})
            match = re.match(r'optimization_(.+?)_(.+?)_(.+?)\.json', filename)
            
            if match:
                file_id = match.group(1)
                strategy = match.group(2)
                battery_config = match.group(3).lower()
                
                # Skip if already in CSV (using combined ID_Strategy as key)
                unique_id = f"{file_id}_{strategy}"
                if unique_id in existing_ids:
                    continue
                
                try:
                    # Load the JSON file
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Extract required metrics - note data is nested under "results" key
                    results = data.get('results', {})
                    total_cost = round(results.get('total_cost', 0), 2)
                    grid_load = round(results.get('max_grid_load', 0), 2)
                    battery_size = round(results.get('battery_capacity', 0), 2)
                    
                    # Determine if battery was allowed based on filename
                    battery_allowed = "Yes" if "withbat" in battery_config else "No"
                    
                    # Determine connection type
                    connection = "Unknown"
                    if results.get('use_hv', 0) > 0.5:
                        connection = "HV Line"
                    elif results.get('use_transmission', 0) > 0.5:
                        connection = "Transmission"
                    elif results.get('use_distribution', 0) > 0.5:
                        connection = "Distribution"
                    elif results.get('use_existing_mv', 0) > 0.5:
                        connection = "Existing MV"
                    
                    # Add to new entries
                    new_entries.append([file_id, strategy, total_cost, grid_load, battery_allowed, battery_size, connection])
                    
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
    
    # Append new entries to CSV
    if new_entries:
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerows(new_entries)
        print(f"Added {len(new_entries)} new entries to {csv_file}")
    else:
        print("No new entries to add")

if __name__ == "__main__":
    # Get project root directory - using dirname(dirname(abspath)) to get parent directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Define paths
    results_dir = os.path.join(project_root, "results")
    csv_file = os.path.join(project_root, "ID_Results.csv")
    
    # Extract metrics and update CSV
    extract_metrics_from_results(results_dir, csv_file)
    print(f"Updated metrics in {csv_file}")