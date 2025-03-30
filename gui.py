"""
ChargingHub Optimization - GUI Interface

This GUI provides a user interface for configuring and running the charging hub optimization process.
It allows users to:
1. View and edit configuration parameters
2. Run individual phases or the complete optimization
3. View logs and status updates
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
import importlib
import logging
import io
from contextlib import redirect_stdout

# Add the project directories to the Python path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

# Import config dynamically to handle reloads
def get_config():
    """Dynamically import (or reimport) the Config class"""
    config_module = importlib.import_module('config')
    importlib.reload(config_module)
    return config_module.Config

# Create a custom handler to redirect logs to our GUI
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)

class ChargingHubOptimizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Charging Hub Optimization Tool")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Get initial config
        self.Config = get_config()
        
        # Set up the main frame structure
        self.create_notebook()
        self.create_status_bar()
        
        # Create configuration frames and populate with fields
        self.setup_general_config()
        self.setup_charging_config()
        self.setup_grid_config()
        self.setup_scenario_config()
        
        # Setup execution controls
        self.setup_execution_tab()
        
        # Setup logging area
        self.setup_log_panel()
        
        # Configure logging to GUI
        self.configure_logging()
        
        # Flag to track if optimization is running
        self.optimization_running = False
        
        # Log startup message
        logging.info("Charging Hub Optimization GUI started successfully")

    def create_notebook(self):
        """Create the main notebook interface with tabs"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.general_tab = ttk.Frame(self.notebook)
        self.charging_tab = ttk.Frame(self.notebook)
        self.grid_tab = ttk.Frame(self.notebook)
        self.scenario_tab = ttk.Frame(self.notebook)
        self.execution_tab = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.general_tab, text="General Settings")
        self.notebook.add(self.charging_tab, text="Charging Configuration")
        self.notebook.add(self.grid_tab, text="Grid Configuration")
        self.notebook.add(self.scenario_tab, text="Scenarios")
        self.notebook.add(self.execution_tab, text="Run Optimization")

    def create_status_bar(self):
        """Create a status bar at the bottom of the window"""
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, borderwidth=1)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(
            self.status_bar, orient=tk.HORIZONTAL, length=200, mode='indeterminate'
        )
        self.progress.pack(side=tk.RIGHT, padx=5, pady=2)

    def setup_general_config(self):
        """Set up the general configuration tab"""
        frame = ttk.LabelFrame(self.general_tab, text="General Settings")
        frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        # Project root (display only)
        ttk.Label(frame, text="Project Root:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.project_root_var = tk.StringVar(value=self.Config.PROJECT_ROOT)
        project_root_entry = ttk.Entry(frame, textvariable=self.project_root_var, state="readonly", width=50)
        project_root_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Forecast Year
        ttk.Label(frame, text="Forecast Year:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.forecast_year_var = tk.StringVar(value=self.Config.FORECAST_YEAR)
        forecast_year_combo = ttk.Combobox(frame, textvariable=self.forecast_year_var, 
                                          values=self.Config.SCENARIOS['TARGET_YEARS'],
                                          state="readonly", width=10)
        forecast_year_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Continue on Error
        ttk.Label(frame, text="Continue on Error:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.continue_on_error_var = tk.BooleanVar(value=self.Config.CONTINUE_ON_ERROR)
        continue_on_error_check = ttk.Checkbutton(frame, variable=self.continue_on_error_var)
        continue_on_error_check.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Recalculate settings
        ttk.Label(frame, text="Recalculate Breaks:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.recalc_breaks_var = tk.BooleanVar(value=self.Config.RECALCULATE_BREAKS)
        recalc_breaks_check = ttk.Checkbutton(frame, variable=self.recalc_breaks_var)
        recalc_breaks_check.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(frame, text="Recalculate Toll Midpoints:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.recalc_toll_var = tk.BooleanVar(value=self.Config.RECALCULATE_TOLL_MIDPOINTS)
        recalc_toll_check = ttk.Checkbutton(frame, variable=self.recalc_toll_var)
        recalc_toll_check.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Default Location
        location_frame = ttk.LabelFrame(self.general_tab, text="Default Location")
        location_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        ttk.Label(location_frame, text="Longitude:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.default_lon_var = tk.DoubleVar(value=self.Config.DEFAULT_LOCATION['LONGITUDE'])
        ttk.Entry(location_frame, textvariable=self.default_lon_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(location_frame, text="Latitude:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.default_lat_var = tk.DoubleVar(value=self.Config.DEFAULT_LOCATION['LATITUDE'])
        ttk.Entry(location_frame, textvariable=self.default_lat_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Save Button
        save_btn = ttk.Button(self.general_tab, text="Save General Settings", command=self.save_general_config)
        save_btn.pack(pady=10)

    def setup_charging_config(self):
        """Set up the charging configuration tab"""
        frame = ttk.LabelFrame(self.charging_tab, text="Charging Settings")
        frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        # Charging Strategies
        ttk.Label(frame, text="Charging Strategies:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Use checkbuttons for strategies
        self.strategy_vars = {}
        strategies = ["T_min", "Konstant", "Hub"]
        strategy_frame = ttk.Frame(frame)
        strategy_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        for i, strategy in enumerate(strategies):
            var = tk.BooleanVar(value=(strategy in self.Config.CHARGING_CONFIG['STRATEGIES']))
            self.strategy_vars[strategy] = var
            cb = ttk.Checkbutton(strategy_frame, text=strategy, variable=var)
            cb.grid(row=0, column=i, padx=10)
            
        # Charging Quota
        ttk.Label(frame, text="Charging Quota:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.charging_quota_var = tk.DoubleVar(value=self.Config.CHARGING_CONFIG['ladequote'])
        ttk.Entry(frame, textvariable=self.charging_quota_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Power Setting
        ttk.Label(frame, text="Power Setting (NCS-HPC-MCS):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.power_setting_var = tk.StringVar(value=self.Config.CHARGING_CONFIG['power'])
        ttk.Entry(frame, textvariable=self.power_setting_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Pause Times
        ttk.Label(frame, text="Pause Times (min-max):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.pause_times_var = tk.StringVar(value=self.Config.CHARGING_CONFIG['pause'])
        ttk.Entry(frame, textvariable=self.pause_times_var, width=20).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Charging Types Frame
        types_frame = ttk.LabelFrame(self.charging_tab, text="Charging Types")
        types_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        # Headers
        ttk.Label(types_frame, text="Type").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(types_frame, text="Power (kW)").grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(types_frame, text="Cost (€)").grid(row=0, column=2, padx=5, pady=5)
        
        # Charging type entries
        self.charging_type_vars = {}
        for i, (key, values) in enumerate(self.Config.CHARGING_TYPES.items()):
            ttk.Label(types_frame, text=key).grid(row=i+1, column=0, padx=5, pady=5)
            
            power_var = tk.IntVar(value=values['power_kw'])
            cost_var = tk.IntVar(value=values['cost'])
            
            self.charging_type_vars[key] = {
                'power_kw': power_var,
                'cost': cost_var
            }
            
            ttk.Entry(types_frame, textvariable=power_var, width=10).grid(row=i+1, column=1, padx=5, pady=5)
            ttk.Entry(types_frame, textvariable=cost_var, width=10).grid(row=i+1, column=2, padx=5, pady=5)
            
        # Save Button
        save_btn = ttk.Button(self.charging_tab, text="Save Charging Settings", command=self.save_charging_config)
        save_btn.pack(pady=10)

    def setup_grid_config(self):
        """Set up the grid configuration tab"""
        frame = ttk.LabelFrame(self.grid_tab, text="Grid Settings")
        frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        # Grid Configuration Variables
        self.grid_config_vars = {}
        
        # Use Distance Calculation
        ttk.Label(frame, text="Use Distance Calculation:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.grid_config_vars['USE_DISTANCE_CALCULATION'] = tk.BooleanVar(value=self.Config.GRID_CONFIG['USE_DISTANCE_CALCULATION'])
        ttk.Checkbutton(frame, variable=self.grid_config_vars['USE_DISTANCE_CALCULATION']).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Create Plot
        ttk.Label(frame, text="Create Plot:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.grid_config_vars['CREATE_PLOT'] = tk.BooleanVar(value=self.Config.GRID_CONFIG['CREATE_PLOT'])
        ttk.Checkbutton(frame, variable=self.grid_config_vars['CREATE_PLOT']).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Create Distance Maps
        ttk.Label(frame, text="Create Distance Maps:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.grid_config_vars['CREATE_DISTANCE_MAPS'] = tk.BooleanVar(value=self.Config.GRID_CONFIG['CREATE_DISTANCE_MAPS'])
        ttk.Checkbutton(frame, variable=self.grid_config_vars['CREATE_DISTANCE_MAPS']).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Include Battery
        ttk.Label(frame, text="Include Battery:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.grid_config_vars['INCLUDE_BATTERY'] = tk.BooleanVar(value=self.Config.GRID_CONFIG['INCLUDE_BATTERY'])
        ttk.Checkbutton(frame, variable=self.grid_config_vars['INCLUDE_BATTERY']).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Battery settings
        battery_frame = ttk.LabelFrame(self.grid_tab, text="Battery Settings")
        battery_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        self.battery_config_vars = {}
        battery_params = [
            ('COST_PER_KWH', 'Cost per kWh (€):'),
            ('COST_PER_KW', 'Cost per kW (€):'),
            ('MAX_CAPACITY', 'Maximum Capacity (kWh):'),
            ('EFFICIENCY', 'Efficiency:'),
            ('MIN_SOC', 'Minimum SOC:'),
            ('MAX_SOC', 'Maximum SOC:')
        ]
        
        for i, (key, label) in enumerate(battery_params):
            ttk.Label(battery_frame, text=label).grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)
            if key in ('EFFICIENCY', 'MIN_SOC', 'MAX_SOC'):
                var = tk.DoubleVar(value=self.Config.BATTERY_CONFIG[key])
            else:
                var = tk.IntVar(value=self.Config.BATTERY_CONFIG[key])
            self.battery_config_vars[key] = var
            ttk.Entry(battery_frame, textvariable=var, width=10).grid(row=i, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Grid Capacities
        capacities_frame = ttk.LabelFrame(self.grid_tab, text="Grid Capacities (kW)")
        capacities_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        self.capacity_vars = {}
        for i, (key, value) in enumerate(self.Config.GRID_CAPACITIES.items()):
            ttk.Label(capacities_frame, text=f"{key}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)
            var = tk.IntVar(value=value)
            self.capacity_vars[key] = var
            ttk.Entry(capacities_frame, textvariable=var, width=10).grid(row=i, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Save Button
        save_btn = ttk.Button(self.grid_tab, text="Save Grid Settings", command=self.save_grid_config)
        save_btn.pack(pady=10)

    def setup_scenario_config(self):
        """Set up the scenario configuration tab"""
        # BEV Adoption Rates
        bev_frame = ttk.LabelFrame(self.scenario_tab, text="BEV Adoption Rates")
        bev_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        self.bev_adoption_vars = {}
        for i, year in enumerate(self.Config.SCENARIOS['TARGET_YEARS']):
            ttk.Label(bev_frame, text=f"{year}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)
            var = tk.DoubleVar(value=self.Config.SCENARIOS['R_BEV'][year])
            self.bev_adoption_vars[year] = var
            ttk.Entry(bev_frame, textvariable=var, width=10).grid(row=i, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Vehicle Parameters
        vehicle_frame = ttk.LabelFrame(self.scenario_tab, text="Vehicle Parameters")
        vehicle_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        # Get values with defaults if keys don't exist
        battery_capacity = self.Config.SCENARIOS.get('BATTERY_CAPACITY', 800)
        consumption = self.Config.SCENARIOS.get('CONSUMPTION', 2.0)
        min_soc = self.Config.SCENARIOS.get('MIN_SOC', 0.1)
        max_soc = self.Config.SCENARIOS.get('MAX_SOC', 0.9)
        
        # Battery capacity
        ttk.Label(vehicle_frame, text="Battery Capacity (kWh):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.battery_capacity_var = tk.IntVar(value=battery_capacity)
        ttk.Entry(vehicle_frame, textvariable=self.battery_capacity_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Consumption
        ttk.Label(vehicle_frame, text="Consumption (kWh/km):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.consumption_var = tk.DoubleVar(value=consumption)
        ttk.Entry(vehicle_frame, textvariable=self.consumption_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Min/Max SOC
        ttk.Label(vehicle_frame, text="Minimum SOC:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.min_soc_var = tk.DoubleVar(value=min_soc)
        ttk.Entry(vehicle_frame, textvariable=self.min_soc_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(vehicle_frame, text="Maximum SOC:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_soc_var = tk.DoubleVar(value=max_soc)
        ttk.Entry(vehicle_frame, textvariable=self.max_soc_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Save Button
        save_btn = ttk.Button(self.scenario_tab, text="Save Scenario Settings", command=self.save_scenario_config)
        save_btn.pack(pady=10)

    def setup_execution_tab(self):
        """Set up the execution tab with controls to run the optimization"""
        frame = ttk.LabelFrame(self.execution_tab, text="Execution Controls")
        frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.N)
        
        # Run Optimization Button
        self.run_button = ttk.Button(frame, text="Run Optimization", command=self.run_optimization)
        self.run_button.pack(pady=10)
        
        # Stop Optimization Button
        self.stop_button = ttk.Button(frame, text="Stop Optimization", command=self.stop_optimization, state=tk.DISABLED)
        self.stop_button.pack(pady=10)
        
        # Execution Status
        self.execution_status_var = tk.StringVar(value="Idle")
        ttk.Label(frame, text="Status:").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(frame, textvariable=self.execution_status_var).pack(side=tk.LEFT, padx=5, pady=5)

    def setup_log_panel(self):
        """Set up the log panel to display logs"""
        log_frame = ttk.LabelFrame(self.root, text="Logs")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def configure_logging(self):
        """Configure logging to redirect to the GUI log panel"""
        self.log_handler = TextHandler(self.log_text)
        self.log_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.log_handler.setFormatter(formatter)
        
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def save_general_config(self):
        """Save the general configuration settings"""
        self.Config.PROJECT_ROOT = self.project_root_var.get()
        self.Config.FORECAST_YEAR = self.forecast_year_var.get()
        self.Config.CONTINUE_ON_ERROR = self.continue_on_error_var.get()
        self.Config.RECALCULATE_BREAKS = self.recalc_breaks_var.get()
        self.Config.RECALCULATE_TOLL_MIDPOINTS = self.recalc_toll_var.get()
        self.Config.DEFAULT_LOCATION['LONGITUDE'] = self.default_lon_var.get()
        self.Config.DEFAULT_LOCATION['LATITUDE'] = self.default_lat_var.get()
        
        self.Config.save()
        logging.info("General settings saved successfully")

    def save_charging_config(self):
        """Save the charging configuration settings"""
        self.Config.CHARGING_CONFIG['STRATEGIES'] = [k for k, v in self.strategy_vars.items() if v.get()]
        self.Config.CHARGING_CONFIG['ladequote'] = self.charging_quota_var.get()
        self.Config.CHARGING_CONFIG['power'] = self.power_setting_var.get()
        self.Config.CHARGING_CONFIG['pause'] = self.pause_times_var.get()
        
        for key, vars in self.charging_type_vars.items():
            self.Config.CHARGING_TYPES[key]['power_kw'] = vars['power_kw'].get()
            self.Config.CHARGING_TYPES[key]['cost'] = vars['cost'].get()
        
        self.Config.save()
        logging.info("Charging settings saved successfully")

    def save_grid_config(self):
        """Save the grid configuration settings"""
        for key, var in self.grid_config_vars.items():
            self.Config.GRID_CONFIG[key] = var.get()
        
        for key, var in self.battery_config_vars.items():
            self.Config.BATTERY_CONFIG[key] = var.get()
        
        for key, var in self.capacity_vars.items():
            self.Config.GRID_CAPACITIES[key] = var.get()
        
        self.Config.save()
        logging.info("Grid settings saved successfully")

    def save_scenario_config(self):
        """Save the scenario configuration settings"""
        for year, var in self.bev_adoption_vars.items():
            self.Config.SCENARIOS['R_BEV'][year] = var.get()
        
        # Initialize the keys if they don't exist
        if 'BATTERY_CAPACITY' not in self.Config.SCENARIOS:
            self.Config.SCENARIOS['BATTERY_CAPACITY'] = 0
        if 'CONSUMPTION' not in self.Config.SCENARIOS:
            self.Config.SCENARIOS['CONSUMPTION'] = 0.0
        if 'MIN_SOC' not in self.Config.SCENARIOS:
            self.Config.SCENARIOS['MIN_SOC'] = 0.0
        if 'MAX_SOC' not in self.Config.SCENARIOS:
            self.Config.SCENARIOS['MAX_SOC'] = 0.0
        
        # Now set the values
        self.Config.SCENARIOS['BATTERY_CAPACITY'] = self.battery_capacity_var.get()
        self.Config.SCENARIOS['CONSUMPTION'] = self.consumption_var.get()
        self.Config.SCENARIOS['MIN_SOC'] = self.min_soc_var.get()
        self.Config.SCENARIOS['MAX_SOC'] = self.max_soc_var.get()
        
        self.Config.save()
        logging.info("Scenario settings saved successfully")

    def run_optimization(self):
        """Run the optimization process"""
        if self.optimization_running:
            messagebox.showwarning("Warning", "Optimization is already running")
            return
        
        self.optimization_running = True
        self.execution_status_var.set("Running")
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()
        
        self.optimization_thread = threading.Thread(target=self._run_optimization)
        self.optimization_thread.start()

    def _run_optimization(self):
        """Internal method to run the optimization process"""
        try:
            # Redirect stdout to capture print statements
            with io.StringIO() as buf, redirect_stdout(buf):
                # Import and run the optimization script
                optimization_module = importlib.import_module('optimization')
                importlib.reload(optimization_module)
                optimization_module.run_optimization()
                
                # Capture any print statements
                output = buf.getvalue()
                if output:
                    logging.info(output)
        except Exception as e:
            logging.error(f"Error during optimization: {e}")
        finally:
            self.optimization_running = False
            self.execution_status_var.set("Idle")
            self.run_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress.stop()

    def stop_optimization(self):
        """Stop the optimization process"""
        if not self.optimization_running:
            messagebox.showwarning("Warning", "No optimization is running")
            return
        
        # Implement stopping logic here (e.g., setting a flag to stop the thread)
        self.optimization_running = False
        self.execution_status_var.set("Stopping...")
        self.progress.stop()
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        logging.info("Optimization stopped by user")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChargingHubOptimizerGUI(root)
    root.mainloop()
