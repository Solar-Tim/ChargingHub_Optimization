import json
import csv
import os

def main():
    # Specific file IDs we're interested in
    file_ids = ["930", "935", "940", "945"]
    
    # Collect grid_energy data for each file
    data_by_file = {}
    
    for file_id in file_ids:
        # Try to find file (look in results directory relative to project root)
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                "results", f"optimization_{file_id}_T_min_noBat.json")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract grid_energy
            grid_energy = data.get('results', {}).get('grid_energy', [])
            data_by_file[file_id] = grid_energy
            print(f"Extracted grid_energy data from ID {file_id}: {len(grid_energy)} values")
            
        except Exception as e:
            print(f"Error reading file for ID {file_id}: {e}")
    
    # Prepare CSV rows
    csv_rows = []
    
    # Add data rows (sorted by ID)
    for file_id in sorted(data_by_file.keys()):
        grid_energy = data_by_file[file_id]
        # Create row with ID first, then all grid_energy values
        row = [file_id] + grid_energy
        csv_rows.append(row)
    
    # Write to CSV
    output_file = 'analyse.csv'
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    main()