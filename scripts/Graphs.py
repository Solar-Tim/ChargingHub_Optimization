import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.lines import Line2D

# Define the path to the Results folder
results_folder = os.path.join(os.getcwd(), 'Results')
print(f"Results folder: {results_folder}")

# List to collect all optimization result files from the Results folder
result_files = [f for f in os.listdir(results_folder) if f.startswith("optimization_results_") and f.endswith(".npz")]
print(f"Result files: {result_files}")

# Split result files into groups of 3 for better visualization
num_clusters = len(result_files)
clusters_per_plot = 3
num_plots = (num_clusters + clusters_per_plot - 1) // clusters_per_plot  # Calculate number of frames

# Define colors and styles for clarity
colors = {"Load Profile": "#1f77b4", "Grid Energy": "#2ca02c", "Battery SOC": "#ff7f0e"}
line_styles = {"Load Profile": "-", "Grid Energy": "--", "Battery SOC": ":"}

# Loop through result files and create grouped plots
for i in range(num_plots):
    start_idx = i * clusters_per_plot
    end_idx = min(start_idx + clusters_per_plot, num_clusters)
    group_files = result_files[start_idx:end_idx]
    print(f"Group files for plot {i}: {group_files}")

    fig, axes = plt.subplots(len(group_files), 1, figsize=(12, 4 * len(group_files)), sharex=True)
    if len(group_files) == 1:
        axes = [axes]  # Ensure axes is iterable

    # Loop through files in the current group
    for ax, result_file in zip(axes, group_files):
        # Load data
        data = np.load(os.path.join(results_folder, result_file))
        time_values = data["time_values"]
        load_profile = data["load_profile"]
        grid_energy = data["grid_energy"]
        battery_soc = data["battery_soc"]

        # Extract cluster name from filename
        cluster_name = result_file.replace("optimization_results_", "").replace(".npz", "")

        # Plot Load Profile, Grid Energy, and Battery SOC
        ax.plot(time_values, load_profile, label="Load Profile (kW)", color=colors["Load Profile"], linestyle=line_styles["Load Profile"], linewidth=1.5)
        ax.plot(time_values, grid_energy, label="Grid Energy (kW)", color=colors["Grid Energy"], linestyle=line_styles["Grid Energy"], linewidth=1.5)
        ax.plot(time_values, battery_soc, label="Battery SOC (kWh)", color=colors["Battery SOC"], linestyle=line_styles["Battery SOC"], linewidth=1.5)

        # Calculate peak values
        max_load = np.max(load_profile)
        max_grid = np.max(grid_energy)
        max_soc = np.max(battery_soc)

        # Add peak values below the legend
        handles, labels = ax.get_legend_handles_labels()
        handles += [Line2D([0], [0], color='none')] * 3
        handles += [Line2D([0], [0], color='none')] * 3
        extra_labels = [f"Peak Load: {max_load:.2f} kW", f"Peak Grid: {max_grid:.2f} kW", f"Peak SOC: {max_soc:.2f} kWh"]
        labels += extra_labels
        ax.legend(handles, labels, loc="upper right", fontsize=8, frameon=False)

        # Set plot properties
        ax.set_title(f"Optimization Results for Cluster: {cluster_name}")
        ax.set_ylabel("Values")
        ax.grid(True, linestyle='--', alpha=0.5)

    # Final adjustments
    axes[-1].set_xlabel("Time (hours)", fontsize=10)  # Set xlabel only on the last subplot
    plt.suptitle(f"Optimization Results (Clusters {start_idx + 1} to {end_idx})", fontsize=14, fontweight="bold")
    plt.show()
