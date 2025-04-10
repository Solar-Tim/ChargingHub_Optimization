import os
import json
import csv
import re

def extract_metrics_from_results(results_dir, csv_file):
    """
    Extract all static metrics from optimization result JSON files and write them to a CSV file.
    Excludes time-series data such as grid_energy, battery_soc, etc.
    
    Parameters:
    -----------
    results_dir : str
        Directory containing optimization result JSON files
    csv_file : str
        Path to the CSV file to update
    """
    # Track all fields we've seen to build comprehensive headers
    all_fields = set()
    
    # First pass: gather all fields from all JSON files to build complete header
    json_files = []
    for filename in os.listdir(results_dir):
        if filename.endswith('.json') and 'optimization_' in filename:
            file_path = os.path.join(results_dir, filename)
            match = re.match(r'optimization_(.+?)_(.+?)_(.+?)\.json', filename)
            
            if match:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Add this file to our list for second pass
                    json_files.append((file_path, filename))
                    
                    # Extract static fields from results
                    results = data.get('results', {})
                    for key, value in results.items():
                        # Skip time-series data (arrays) and complex objects except transformer_selections
                        if not isinstance(value, (list, dict)) or key == 'transformer_selections':
                            all_fields.add(key)
                    
                except Exception as e:
                    print(f"Error reading {filename} for header collection: {e}")
    
    # Create standard fields that should always be at the beginning
    standard_fields = ['ID', 'Strategy', 'Battery_Allowed', 'Timestamp']
    
    # Sort the other fields for consistency
    sorted_fields = sorted(list(all_fields))
    header_fields = standard_fields + sorted_fields
    
    # Check if CSV exists and create it with headers if not
    if not os.path.exists(csv_file):
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(header_fields)
    
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
    
    # Second pass: process each file and extract all metrics
    new_entries = []
    for file_path, filename in json_files:
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
                
                # Start with standard fields
                row_data = {
                    'ID': file_id,
                    'Strategy': strategy,
                    'Battery_Allowed': "Yes" if "withbat" in battery_config else "No",
                    'Timestamp': data.get('timestamp', '')
                }
                
                # Extract all static fields from results
                results = data.get('results', {})
                for key, value in results.items():
                    # Skip time-series data (arrays) and specific time-related fields
                    if key in ['grid_energy', 'battery_soc', 'battery_charge', 'battery_discharge']:
                        continue
                    
                    # Special handling for transformer_selections (convert to string)
                    if key == 'transformer_selections' and isinstance(value, dict):
                        row_data[key] = str(value)
                    # Skip any other arrays
                    elif not isinstance(value, list):
                        # Round numeric values for readability
                        if isinstance(value, (float, int)):
                            row_data[key] = round(value, 2)
                        else:
                            row_data[key] = value
                
                # Create row in correct order according to headers
                ordered_row = []
                for field in header_fields:
                    ordered_row.append(row_data.get(field, ''))
                
                new_entries.append(ordered_row)
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    # Read the current headers from the CSV file to ensure we're adding data correctly
    current_headers = []
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='') as f:
            reader = csv.reader(f, delimiter=';')
            try:
                current_headers = next(reader)
            except StopIteration:
                # Empty file, will use header_fields instead
                pass
    
    # Update the CSV file if there are new entries
    if new_entries:
        # If the headers in the file don't match what we need, rewrite the file
        if current_headers and current_headers != header_fields:
            # Read all existing data
            existing_data = []
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f, delimiter=';')
                next(reader)  # Skip header
                existing_data = list(reader)
            
            # Write all data with new headers
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(header_fields)
                writer.writerows(existing_data)
                writer.writerows(new_entries)
        else:
            # Just append new entries
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