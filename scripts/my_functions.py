import pandas as pd
import matplotlib.pyplot as plt
# Import all the needed variables from config_BA
from scripts.config_Optimization import (
    aluminium_kabel, 
    mv_capacity_fee, 
    hv_capacity_fee, 
    existing_mv_capacity,
    existing_mv_connection_cost
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
    
    # Create directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    
    # Convert numpy arrays to lists for JSON serialization
    serializable_results = {k: v if not isinstance(v, np.ndarray) else v.tolist() 
                           for k, v in results.items()}
    
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
        "results": serializable_results,
        "time_periods": time_strings,
        "load_profile": load_profile_list,
    }
    
    # Save to file
    filename = f"results/optimization_{scenario_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Results saved to {filename}")
    return filename

def visualize_results(timestamps, load_profile, result, cluster_name):
    """Create visualization of optimization results"""
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, load_profile, label='Load Profile', alpha=0.7)
    plt.plot(timestamps, result['grid_energy'], label='Grid Energy', alpha=0.7)
    plt.plot(timestamps, result['battery_soc'], label='Battery SOC', alpha=0.7)
    plt.title(f'Energy Flow - {cluster_name}')
    plt.xlabel('Time')
    plt.ylabel('Power (kW)')
    plt.legend()
    plt.savefig(f"./Results/optimization_plot_{cluster_name}.png")
    plt.close()

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

def plot_optimization_results(results, timestamps, load_profile, create_plot=True):
    """
    Visualize optimization results with time-series plots.
    
    Parameters:
    - results: Dictionary containing optimization results
    - timestamps: Time points for the x-axis
    - load_profile: Original load profile data
    - create_plot: Boolean to control whether to create visual plots
    
    Returns:
    - None (displays plots if create_plot is True)
    """
    if not create_plot:
        print("Plot generation disabled in configuration")
        return
        
    import matplotlib.pyplot as plt
    
    # Create a figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # First subplot - Energy flows
    ax1.plot(timestamps, load_profile, label='Load Profile', color='blue')
    ax1.plot(timestamps, results['grid_energy'], label='Grid Energy', color='red')
    ax1.fill_between(timestamps, results['battery_discharge'], 
                     alpha=0.3, color='green', label='Battery Discharge')
    ax1.fill_between(timestamps, [0] * len(timestamps), results['battery_charge'], 
                     alpha=0.3, color='orange', label='Battery Charge')
    
    ax1.axhline(y=results['max_grid_load'], color='red', linestyle='--', 
                label=f"Max Grid Load: {results['max_grid_load']:.2f} kW")
    ax1.set_title('Energy Flows')
    ax1.set_ylabel('Power (kW)')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right')
    
    # Second subplot - Battery state of charge
    ax2.plot(timestamps, results['battery_soc'], label='Battery State of Charge', color='purple')
    if results['battery_capacity'] > 0:
        ax2.axhline(y=results['battery_capacity'], color='purple', linestyle='--', 
                    label=f"Battery Capacity: {results['battery_capacity']:.2f} kWh")
    ax2.set_title('Battery State of Charge')
    ax2.set_ylabel('Energy (kWh)')
    ax2.set_xlabel('Time')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    
    # Add cost information in a text box
    connection_type = ""
    if results['use_hv'] > 0.5:
        connection_type = "HV Line"
    elif results['use_transmission'] > 0.5:
        connection_type = "Transmission Substation"
    elif results['use_distribution'] > 0.5:
        connection_type = "Distribution Substation"
    elif results['use_existing_mv'] > 0.5:
        connection_type = "Existing MV Line"
        
    costinfo = (
        f"Total Cost: €{results['total_cost']:,.2f}\n"
        f"Connection Cost: €{results['connection_cost']:,.2f}\n"
        f"Capacity Cost: €{results['capacity_cost']:,.2f}\n"
        f"Battery Cost: €{results['battery_cost']:,.2f}\n"
        f"Transformer Cost: €{results['transformer_cost']:,.2f}\n"
        f"Connection Type: {connection_type}"
    )
    
    # Add text box to the figure
    plt.figtext(0.02, 0.02, costinfo, fontsize=10, 
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
    
    # Adjust layout and save
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)  # Make room for the cost text box
    
    # Save figure and display
    try:
        plt.savefig("optimization_results.png", dpi=300, bbox_inches='tight')
        print("Plot saved as 'optimization_results.png'")
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

