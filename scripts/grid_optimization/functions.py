import pandas as pd
import matplotlib.pyplot as plt
import datetime
import hashlib
import os
# Import all the needed variables from config using absolute import path
from grid_optimization.config_grid import (
    aluminium_kabel, 
    mv_capacity_fee, 
    hv_capacity_fee, 
    existing_mv_capacity,
    existing_mv_connection_cost, generate_result_filename
)


def loadData():
    # Load Profile for clusters
    file_path = "c:/Users/sande/sciebo/2024_BA_Tim Sanders/07_Python/02_Optimization/Data/lastgang_demo.csv"
    try:
        lastgang_data = pd.read_csv(file_path, sep=";")
    except FileNotFoundError:
        raise FileNotFoundError(f"The file '{file_path}' was not found. Ensure the file path is correct.")

    if lastgang_data.empty:
        raise ValueError("The file 'lastgang_data.csv' is empty. Check the input data.")

    # Extract timestamps from the first column and cluster names from the headers
    timestamps = lastgang_data.iloc[:, 0].values  # First column for timestamps
    cluster_names = lastgang_data.columns[1:]  # Remaining columns as cluster names

    # Extract load profiles for each cluster
    load_profiles = {
        cluster: lastgang_data[cluster].values.astype(float) for cluster in cluster_names
    }
    return(load_profiles,timestamps)

def save_optimization_results(results, scenario_name, timestamps, load_profile):
    """Save optimization results to a JSON file."""
    import json
    import numpy as np
    import os
    from datetime import datetime
    from collections import OrderedDict
    
    # Create directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    
    # Convert numpy arrays to lists for JSON serialization
    serializable_results = {k: v if not isinstance(v, np.ndarray) else v.tolist() 
                           for k, v in results.items()}
    
    # Reorganize results with cost-related entries first
    cost_keys = [
        'total_cost',
        'connection_cost', 
        'capacity_cost',
        'battery_cost',
        'transformer_cost',
        'expansion_cost',
        'internal_cable_cost',
        'charger_cost',
        'total_charginghub_cost'
    ]
    
    # Create an ordered dictionary with costs first
    ordered_results = OrderedDict()
    
    # Add cost items first
    for key in cost_keys:
        if key in serializable_results:
            ordered_results[key] = serializable_results[key]
    
    # Add all remaining items
    for key, value in serializable_results.items():
        if key not in cost_keys:
            ordered_results[key] = value
    
    # Convert timestamps to strings if they are datetime objects
    time_strings = [str(t) for t in timestamps]
    
    # Handle load_profile conversion safely
    if hasattr(load_profile, 'tolist'):
        load_profile_list = load_profile.tolist()
    else:
        # It's already a list or similar structure
        load_profile_list = load_profile
    
    # Final data structure
    data = {
        "scenario": scenario_name,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "results": ordered_results,
        "time_periods": time_strings,
        "load_profile": load_profile_list,
    }
    
    # FIXED: Use generate_result_filename instead of hardcoding the filename format
    # This ensures the custom location ID gets properly used
    # Let generate_result_filename handle battery status based on results
    strategy = results.get('charging_strategy', 'unknown')
    filename_base = generate_result_filename(results=results, 
                                             strategy=strategy)
    
    # Save to file
    filename = f"results/optimization_{filename_base}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Results saved to {filename}")
    return filename

def print_optimization_summary(results, distances=None):
    """Print key optimization results to the terminal."""
    print("\n" + "="*50)
    print("============== OPTIMIZATION RESULTS ==============")
    print("="*50)
    print(f"Total Cost: €{results['total_cost']:,.2f}")
    
    # Print cost breakdown if available
    if 'connection_cost' in results:
        print("\n--- Cost Breakdown ---")
        print(f"Connection Cost: €{results['connection_cost']:,.2f}")
        print(f"Capacity Cost: €{results['capacity_cost']:,.2f}")
        print(f"Battery Cost: €{results['battery_cost']:,.2f}")
        print(f"Transformer Cost: €{results['transformer_cost']:,.2f}")
    
    print(f"\nGrid Capacity: {results['max_grid_load']:.2f} kW")
    print(f"Battery Capacity: {results['battery_capacity']:.2f} kWh")
    
    # Add detailed connection information
    print("\n--- Connection Details ---")
    connection_type = ""
    distance = 0
    cable_size = "N/A"
    cost_per_meter = 0
    total_cable_cost = 0
    
    # Use distances from results if available, otherwise use the distances parameter
    if distances is None and 'distribution_distance' in results:
        distances = {
            'distribution_distance': results['distribution_distance'],
            'transmission_distance': results['transmission_distance'],
            'powerline_distance': results['powerline_distance']
        }
    
    # Determine connection type and calculate cable costs
    if results['use_hv'] > 0.5:
        connection_type = "HV Line"
        distance = results['powerline_distance']
        cable_size = results['hv_selected_size']
        
    elif results['use_transmission'] > 0.5:
        connection_type = "Transmission Substation"
        distance = results['transmission_distance']
        cable_size = results['transmission_selected_size']
        
    elif results['use_distribution'] > 0.5:
        connection_type = "Distribution Substation"
        distance = results['distribution_distance']
        cable_size = results['distribution_selected_size']
        
    elif results['use_existing_mv'] > 0.5:
        connection_type = "Existing MV Line"
        cable_size = "N/A (existing)"
        distance = 0
    
    # Calculate cable cost once we know the cable size
    if isinstance(cable_size, (int, float)):
        try:
            idx = aluminium_kabel["Nennquerschnitt"].index(cable_size)
            cost_per_meter = aluminium_kabel["Kosten"][idx]
            total_cable_cost = cost_per_meter * distance
        except (ValueError, IndexError):
            cost_per_meter = 0
            total_cable_cost = 0
    
    print(f"Connection Type: {connection_type}")
    print(f"Distance: {distance} m")
    print(f"Cable Cross-Section: {cable_size} mm²")
    
    if isinstance(cable_size, (int, float)) and cost_per_meter > 0:
        print(f"Cable Cost per Meter: €{cost_per_meter:.2f}")
        print(f"Total Cable Cost: €{total_cable_cost:,.2f}")
    
    print("="*50)

def print_distances(distances):
    """Print distances between clusters."""
    print("\n=== DISTANCES ===")
    print("Distance calculation completed")
    print(f"Distribution substation distance: {distances['distribution_distance']:.0f}m")
    print(f"Transmission substation distance: {distances['transmission_distance']:.0f}m")
    print(f"Powerline distance: {distances['powerline_distance']:.0f}m")
    print("===================================")

def plot_optimization_results(results, timestamps, load_profile, create_plot=True, filename_base=None):
    """
    Visualize optimization results with time-series plots.
    
    Parameters:
    - results: Dictionary containing optimization results
    - timestamps: Time points for the x-axis
    - load_profile: Original load profile data
    - create_plot: Boolean to control whether to create visual plots
    - filename_base: Base filename for the output plot (without extension)
    
    Returns:
    - None (displays plots if create_plot is True)
    """
    if not create_plot:
        print("Plot generation disabled in configuration")
        return
        
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import datetime
    import numpy as np
    
    # Determine if battery was used in the optimization
    battery_used = results['battery_capacity'] > 0
    
    # Convert timestamps to numeric values (assuming they're minutes from start)
    # If timestamps are already datetime objects, adjust accordingly
    if isinstance(timestamps[0], str):
        # Try to parse timestamps if they're strings
        try:
            # Attempt to parse as datetime
            datetime_timestamps = [datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts in timestamps]
        except ValueError:
            # If that fails, assume they're minutes and create dummy datetimes
            base_date = datetime.datetime(2023, 1, 1)  # Arbitrary start date
            datetime_timestamps = [base_date + datetime.timedelta(minutes=float(ts)) for ts in timestamps]
    elif isinstance(timestamps[0], (int, float)):
        # Assume timestamps are minutes from start
        base_date = datetime.datetime(2023, 1, 1)  # Arbitrary start date
        datetime_timestamps = [base_date + datetime.timedelta(minutes=t) for t in timestamps]
    else:
        # Assume they're already datetime objects
        datetime_timestamps = timestamps
    
    # Create day labels for x-axis
    # Calculate elapsed days for each timestamp
    start_date = datetime_timestamps[0].date()
    day_numbers = [(dt.date() - start_date).days + 1 for dt in datetime_timestamps]
    
    # Find indices where a new day starts
    day_change_indices = [i for i in range(1, len(day_numbers)) if day_numbers[i] > day_numbers[i-1]]
    # Add start of first day
    day_change_indices = [0] + day_change_indices
    
    # Create figure with appropriate number of subplots
    if battery_used:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True, 
                                      gridspec_kw={'height_ratios': [3, 2]})
    else:
        fig, ax1 = plt.subplots(figsize=(14, 6))
    
    # First subplot - Energy flows
    ax1.plot(datetime_timestamps, load_profile, label='Demand', color='blue', linewidth=2)
    ax1.plot(datetime_timestamps, results['grid_energy'], label='Grid Energy', color='red', linewidth=2)
    
    # Add battery-related plots only if battery was used
    if battery_used:
        # Use fill_between with positive values for better visualization 
        ax1.fill_between(datetime_timestamps, results['battery_discharge'], 
                        alpha=0.4, color='green', label='Battery Discharge')
        ax1.fill_between(datetime_timestamps, [0] * len(datetime_timestamps), results['battery_charge'], 
                        alpha=0.4, color='orange', label='Battery Charge')
    
    ax1.axhline(y=results['max_grid_load'], color='red', linestyle='--', linewidth=1.5,
                label=f"Max Grid Load: {results['max_grid_load']:.2f} kW")
    ax1.set_title('Energy Flows Over Time', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Power [kW]', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right', fontsize=10)
    
    # Set custom x-tick labels showing days
    unique_days = sorted(set(day_numbers))
    day_positions = [datetime_timestamps[day_change_indices[i]] for i in range(len(day_change_indices))]
    day_labels = [f"Day {day}" for day in unique_days]
    
    ax1.set_xticks(day_positions)
    ax1.set_xticklabels(day_labels)
    
    # Format the x-axis to show vertical lines at day boundaries
    for day_idx in day_change_indices:
        ax1.axvline(x=datetime_timestamps[day_idx], color='gray', linestyle='-', alpha=0.2)
    
    # Only create the second subplot if battery was used
    if battery_used:
        # Second subplot - Battery state of charge
        ax2.plot(datetime_timestamps, results['battery_soc'], 
                 label='Battery State of Charge', color='purple', linewidth=2)
        ax2.axhline(y=results['battery_capacity'], color='purple', linestyle='--', linewidth=1.5,
                    label=f"Battery Capacity: {results['battery_capacity']:.2f} kWh")
        ax2.set_title('Battery State of Charge', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Energy [kWh]', fontsize=12)
        ax2.set_xlabel('Time', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='upper right', fontsize=10)
        
        # Set the same x-ticks for battery SOC plot
        ax2.set_xticks(day_positions)
        ax2.set_xticklabels(day_labels)
        
        # Format the x-axis to show vertical lines at day boundaries
        for day_idx in day_change_indices:
            ax2.axvline(x=datetime_timestamps[day_idx], color='gray', linestyle='-', alpha=0.2)
    else:
        # If no battery, add x-label to the first plot
        ax1.set_xlabel('Time', fontsize=12)
    
    # Connection type determination
    connection_type = ""
    if results['use_hv'] > 0.5:
        connection_type = "HV Line"
    elif results['use_transmission'] > 0.5:
        connection_type = "Transmission Substation"
    elif results['use_distribution'] > 0.5:
        connection_type = "Distribution Substation"
    elif results['use_existing_mv'] > 0.5:
        connection_type = "Existing MV Line"
    
    # Create a more compact, organized summary box
    costinfo = (
        f"Total Cost: €{results['total_cost']:,.2f}\n"
        f"Connection: {connection_type} (€{results['connection_cost']:,.2f})\n"
        f"Capacity: €{results['capacity_cost']:,.2f}\n"
        f"Battery: {results['battery_capacity']:.1f} kWh (€{results['battery_cost']:,.2f})\n"
        f"Transformer: €{results['transformer_cost']:,.2f}"
    )
    
    # Add text box to the figure
    plt.figtext(0.02, 0.02, costinfo, fontsize=10, 
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5', edgecolor='gray'))
    
    # Add a subtitle with the charging strategy
    plt.figtext(0.5, 0.01, f"Charging Strategy: {results['charging_strategy']}", 
                fontsize=10, ha='center')
    
    # Adjust layout and save
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)  # Make room for the cost text box
    
    # Determine filename
    if filename_base:
        filename = f"results/{filename_base}.png"
    else:
        filename = "results/optimization_results.png"
    
    # Save figure and display
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Plot saved as '{filename}'")
        plt.show()
    except Exception as e:
        print(f"Error saving plot: {e}")

def print_cable_selection_details(model, distances, cable_options=None, power_cost_points=None):
    """
    Print detailed debug information about cable selection.
    
    Parameters:
    - model: Gurobi model with optimization results
    - distances: Dictionary with connection distances
    - cable_options: Dictionary with cable options for each connection type
    - power_cost_points: Dictionary with power and cost points for PWL functions
    """
    # Extract variables from model
    use_transmission = model.getVarByName("NewTransmissionSubstationLink")
    use_distribution = model.getVarByName("NewDistributionSubstationLink")
    use_hv_line = model.getVarByName("NewHVLine")
    use_existing_mv = model.getVarByName("ExistingMVLine")
    
    max_grid_load = model.getVarByName("GridLoad")
    
    # Get the cost variables for each connection type
    transmission_cable_cost = model.getVarByName("TransmissionCableCost")
    distribution_cable_cost = model.getVarByName("DistributionCableCost")
    hvline_cable_cost = model.getVarByName("HVLineCableCost")
    
    # Initialize all point variables to empty lists by default
    transmission_power_points = []
    transmission_cost_points = []
    distribution_power_points = []
    distribution_cost_points = []
    hvline_power_points = []
    hvline_cost_points = []
    
    # Unpack power_cost_points if provided
    if power_cost_points:
        transmission_power_points = power_cost_points.get('transmission_power_points', [])
        transmission_cost_points = power_cost_points.get('transmission_cost_points', [])
        distribution_power_points = power_cost_points.get('distribution_power_points', [])
        distribution_cost_points = power_cost_points.get('distribution_cost_points', [])
        hvline_power_points = power_cost_points.get('hvline_power_points', [])
        hvline_cost_points = power_cost_points.get('hvline_cost_points', [])
    
    print("\n=== Cable Selection Analysis ===")
    print(f"Distribution substation distance: {distances['distribution_distance']} m")
    print(f"Transmission substation distance: {distances['transmission_distance']} m")
    print(f"HV line distance: {distances['powerline_distance']} m")
    print(f"Max grid load value: {max_grid_load.X:.2f} kW")
    
    print("\n=== Cable Selection Details ===")
    if use_transmission.X > 0.5:
        print(f"SELECTED CONNECTION TYPE: Transmission Substation")
        print(f"  Distance: {distances['transmission_distance']:.2f} m")
        print(f"  Capacity needed: {max_grid_load.X:.2f} kW")
        print(f"  Connection cost: {transmission_cable_cost.X:.2f} EUR")
        print(f"  Capacity fee: {mv_capacity_fee * max_grid_load.X:.2f} EUR")
        
        # Print PWL points if available
        if power_cost_points:
            print("\n=== PWL Points for Transmission Connection ===")
            for i, (p, c) in enumerate(zip(transmission_power_points, transmission_cost_points)):
                print(f"  Power: {p:.2f} kW, Cost: {c:.2f} EUR")
        
    elif use_distribution.X > 0.5:
        print(f"SELECTED CONNECTION TYPE: Distribution Substation")
        print(f"  Distance: {distances['distribution_distance']:.2f} m")
        print(f"  Capacity needed: {max_grid_load.X:.2f} kW")
        print(f"  Connection cost: {distribution_cable_cost.X:.2f} EUR")
        print(f"  Capacity fee: {mv_capacity_fee * max_grid_load.X:.2f} EUR")
        
        # Print PWL points if available
        if power_cost_points:
            print("\n=== PWL Points for Distribution Connection ===")
            for i, (p, c) in enumerate(zip(distribution_power_points, distribution_cost_points)):
                print(f"  Power: {p:.2f} kW, Cost: {c:.2f} EUR")
        
    elif use_hv_line.X > 0.5:
        print(f"SELECTED CONNECTION TYPE: HV Line")
        print(f"  Distance: {distances['powerline_distance']:.2f} m")
        print(f"  Capacity needed: {max_grid_load.X:.2f} kW")
        print(f"  Connection cost: {hvline_cable_cost.X:.2f} EUR")
        print(f"  Capacity fee: {hv_capacity_fee * max_grid_load.X:.2f} EUR")
        
        # Print PWL points if available
        if power_cost_points:
            print("\n=== PWL Points for HV Line Connection ===")
            for i, (p, c) in enumerate(zip(hvline_power_points, hvline_cost_points)):
                print(f"  Power: {p:.2f} kW, Cost: {c:.2f} EUR")
        
    elif use_existing_mv.X > 0.5:
        print(f"SELECTED CONNECTION TYPE: Existing MV Line")
        print(f"  Capacity: {existing_mv_capacity:.2f} kW")
        print(f"  Connection cost: {existing_mv_connection_cost:.2f} EUR")
        print(f"  Capacity fee: {mv_capacity_fee * max_grid_load.X:.2f} EUR")




