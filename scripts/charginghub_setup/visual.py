import json
import matplotlib.pyplot as plt
import os

def load_json_file(file_path):
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def main():
    # File paths
    base_dir = "c:/Users/sande/OneDrive/Dokumente/GitHub/ChargingHub_Optimization/data/load/"
    hub_file = os.path.join(base_dir, "simplified_charging_data_Hub.json")
    konstant_file = os.path.join(base_dir, "simplified_charging_data_Konstant.json")
    tmin_file = os.path.join(base_dir, "simplified_charging_data_T_min.json")

    # Load JSON data
    hub_data = load_json_file(hub_file)
    konstant_data = load_json_file(konstant_file)
    tmin_data = load_json_file(tmin_file)

    if not all([hub_data, konstant_data, tmin_data]):
        print("Failed to load one or more data files.")
        return

    try:
        # Extract "Leistung_Total" values from each dataset
        hub_values = [entry["Leistung_Total"] for entry in hub_data["lastgang"]]
        konstant_values = [entry["Leistung_Total"] for entry in konstant_data["lastgang"]]
        tmin_values = [entry["Leistung_Total"] for entry in tmin_data["lastgang"]]
        
        # Create time axis (minutes)
        time_steps = list(range(len(hub_values)))
        
        # Get peak load from Hub data (if available)
        hub_peak_load = hub_data.get("metadata", {}).get("peak_load_kw")
        peak_load_info = f" (Peak load: {hub_peak_load:.2f} kW)" if hub_peak_load else ""
        
        # Create the plot
        plt.figure(figsize=(12, 6))
        
        # Plot each strategy with different line styles for clarity
        plt.plot(time_steps, hub_values, label='Hub', linewidth=2)
        plt.plot(time_steps, konstant_values, label='Konstant', linestyle='--', linewidth=2)
        plt.plot(time_steps, tmin_values, label='T_min', linestyle=':', linewidth=2)
        
        # Add labels and title
        plt.xlabel('Time (minutes)')
        plt.ylabel('Leistung_Total (kW)')
        plt.title(f'Comparison of Charging Strategies{peak_load_info}')
        
        # Add legend and grid
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Display the plot
        plt.tight_layout()
        plt.show()
        
    except KeyError as e:
        print(f"Error: Expected data field not found in JSON: {e}")
        print("Available fields in the JSON data:")
        print(f"Hub data keys: {list(hub_data['lastgang'][0].keys())}")
        print(f"Konstant data keys: {list(konstant_data['lastgang'][0].keys())}")
        print(f"T_min data keys: {list(tmin_data['lastgang'][0].keys())}")
    except Exception as e:
        print(f"An error occurred during plotting: {e}")

if __name__ == "__main__":
    main()