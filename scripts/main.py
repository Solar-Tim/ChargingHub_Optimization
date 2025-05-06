"""
Charging Hub Optimization - Main Control Script

This script serves as the global entry point for the charging hub optimization project.
It coordinates the execution of two main components:
1. Traffic Calculation: Calculates charging demand based on traffic patterns
2. Charging Hub Setup: Configures and optimizes the charging hub

Each component will be executed in sequence, with proper error handling.
"""

from pathlib import Path
import os
import sys
import time
import logging
import subprocess

# Configure logging
log_dir = Path("../logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=log_dir/'charging_hub_optimization.log',
    level=logging.INFO,
    format='%(asctime)s; %(levelname)s; %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set up Python path properly
scripts_dir = os.path.dirname(os.path.abspath(__file__))  # Now points to scripts folder
base_dir = os.path.dirname(scripts_dir)  # Project root is parent of scripts dir
traffic_dir = os.path.join(scripts_dir, 'traffic_calculation')
charginghub_dir = os.path.join(scripts_dir, 'charginghub_setup')

# Add all necessary directories to path
sys.path.append(base_dir)  # Add project root
sys.path.append(scripts_dir)
sys.path.append(traffic_dir)
sys.path.append(charginghub_dir)

# Import configuration
from config import Config

# Check for environment variables set by GUI
def apply_environment_overrides():
    """
    Apply any environment variable overrides passed from the GUI
    """
    # Check for execution flags
    if 'CHARGING_HUB_RUN_TRAFFIC_CALCULATION' in os.environ:
        Config.EXECUTION_FLAGS['RUN_TRAFFIC_CALCULATION'] = os.environ['CHARGING_HUB_RUN_TRAFFIC_CALCULATION'] == '1'
        logging.info(f"Environment override: RUN_TRAFFIC_CALCULATION = {Config.EXECUTION_FLAGS['RUN_TRAFFIC_CALCULATION']}")
    
    if 'CHARGING_HUB_RUN_CHARGING_HUB_SETUP' in os.environ:
        Config.EXECUTION_FLAGS['RUN_CHARGING_HUB_SETUP'] = os.environ['CHARGING_HUB_RUN_CHARGING_HUB_SETUP'] == '1'
        logging.info(f"Environment override: RUN_CHARGING_HUB_SETUP = {Config.EXECUTION_FLAGS['RUN_CHARGING_HUB_SETUP']}")
    
    if 'CHARGING_HUB_RUN_GRID_OPTIMIZATION' in os.environ:
        Config.EXECUTION_FLAGS['RUN_GRID_OPTIMIZATION'] = os.environ['CHARGING_HUB_RUN_GRID_OPTIMIZATION'] == '1'
        logging.info(f"Environment override: RUN_GRID_OPTIMIZATION = {Config.EXECUTION_FLAGS['RUN_GRID_OPTIMIZATION']}")
    
    # Check for other settings
    if 'CHARGING_HUB_CUSTOM_ID' in os.environ:
        custom_id = os.environ['CHARGING_HUB_CUSTOM_ID']
        Config.RESULT_NAMING['USE_CUSTOM_ID'] = True
        Config.RESULT_NAMING['CUSTOM_ID'] = custom_id
        logging.info(f"Environment override: CUSTOM_ID = {custom_id}")
    
    if 'CHARGING_HUB_LONGITUDE' in os.environ and 'CHARGING_HUB_LATITUDE' in os.environ:
        try:
            longitude = float(os.environ['CHARGING_HUB_LONGITUDE'])
            latitude = float(os.environ['CHARGING_HUB_LATITUDE'])
            Config.DEFAULT_LOCATION['LONGITUDE'] = longitude
            Config.DEFAULT_LOCATION['LATITUDE'] = latitude
            logging.info(f"Environment override: DEFAULT_LOCATION = ({longitude}, {latitude})")
        except ValueError:
            logging.error("Invalid coordinates in environment variables")
    
    if 'CHARGING_HUB_INCLUDE_BATTERY' in os.environ:
        Config.EXECUTION_FLAGS['INCLUDE_BATTERY'] = os.environ['CHARGING_HUB_INCLUDE_BATTERY'] == '1'
        logging.info(f"Environment override: INCLUDE_BATTERY = {Config.EXECUTION_FLAGS['INCLUDE_BATTERY']}")

def run_traffic_calculation():
    """Run the traffic calculation module."""
    if not Config.EXECUTION_FLAGS['RUN_TRAFFIC_CALCULATION']:
        report_progress(1, "TRAFFIC CALCULATION", "skipped")
        return True
        
    report_progress(1, "TRAFFIC CALCULATION", "started")
    
    try:
        # Define the path to the traffic calculation script
        traffic_script = os.path.join(traffic_dir, 'main.py')
        
        # Set up environment variables
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{base_dir}:{env.get('PYTHONPATH', '')}"
        
        start_time = time.time()
        
        # Run the traffic calculation script as a subprocess
        result = subprocess.run(
            [sys.executable, traffic_script], 
            env=env,
            cwd=base_dir,  
            capture_output=True, 
            text=True, 
            check=False
        )
        
        # Print the output to ensure it's visible
        print(result.stdout)
        
        if result.returncode != 0:
            raise Exception(f"Traffic calculation script failed with error:\n{result.stderr}")
        
        elapsed_time = time.time() - start_time
        report_progress(1, "TRAFFIC CALCULATION", "completed", elapsed_time)
        return True
    except Exception as e:
        report_progress(1, "TRAFFIC CALCULATION", "failed")
        print(f"Error details: {str(e)}")
        return False

def run_charging_hub_setup():
    """
    Run the charging hub setup module.
    """
    if not Config.EXECUTION_FLAGS['RUN_CHARGING_HUB_SETUP']:
        report_progress(2, "CHARGING HUB SETUP", "skipped")
        return True
        
    report_progress(2, "CHARGING HUB SETUP", "started")
    
    try:
        # Change working directory to charginghub_setup folder
        original_dir = os.getcwd()
        os.chdir(charginghub_dir)
        
        # Import here to avoid issues with module paths
        from charginghub_setup.main import main as hub_main # type: ignore
        
        start_time = time.time()
        hub_main()
        elapsed_time = time.time() - start_time
        
        # Change back to original directory
        os.chdir(original_dir)
        
        report_progress(2, "CHARGING HUB SETUP", "completed", elapsed_time)
        return True
    except Exception as e:
        report_progress(2, "CHARGING HUB SETUP", "failed")
        print(f"Error details: {str(e)}")
        return False

def run_grid_optimization():
    """
    Run the grid optimization module.
    """
    if not Config.EXECUTION_FLAGS['RUN_GRID_OPTIMIZATION']:
        report_progress(3, "GRID OPTIMIZATION", "skipped")
        return True
        
    report_progress(3, "GRID OPTIMIZATION", "started")
    
    try:
        # Define the path to the optimization script
        grid_opt_dir = os.path.join(scripts_dir, 'grid_optimization')
        optimization_script = os.path.join(grid_opt_dir, 'optimization.py')
        
        # Save original directory
        original_dir = os.getcwd()
        
        # Run the optimization script with the project root as working directory
        # Set DATA_DIR environment variable to help script locate data files
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{base_dir}:{env.get('PYTHONPATH', '')}"
        
        # Pass custom ID through environment variables
        if Config.RESULT_NAMING.get('USE_CUSTOM_ID', False):
            custom_id = Config.RESULT_NAMING.get('CUSTOM_ID', '')
            env['CHARGING_HUB_CUSTOM_ID'] = custom_id
            print(f"DEBUG: Passing custom ID to subprocess: {custom_id}")
            logging.info(f"DEBUG: Passing custom ID to subprocess: {custom_id}")
            
        # Pass location coordinates through environment variables
        env['CHARGING_HUB_LONGITUDE'] = str(Config.DEFAULT_LOCATION['LONGITUDE'])
        env['CHARGING_HUB_LATITUDE'] = str(Config.DEFAULT_LOCATION['LATITUDE'])
        print(f"DEBUG: Passing coordinates to subprocess: ({Config.DEFAULT_LOCATION['LONGITUDE']}, {Config.DEFAULT_LOCATION['LATITUDE']})")
        logging.info(f"DEBUG: Passing coordinates to subprocess: ({Config.DEFAULT_LOCATION['LONGITUDE']}, {Config.DEFAULT_LOCATION['LATITUDE']})")
        
        # Pass battery status through environment variables
        env['CHARGING_HUB_INCLUDE_BATTERY'] = str(int(Config.EXECUTION_FLAGS['INCLUDE_BATTERY']))
        print(f"DEBUG: Passing battery status to subprocess: {Config.EXECUTION_FLAGS['INCLUDE_BATTERY']}")
        logging.info(f"DEBUG: Passing battery status to subprocess: {Config.EXECUTION_FLAGS['INCLUDE_BATTERY']}")
        
        start_time = time.time()
        
        result = subprocess.run([sys.executable, optimization_script], 
                              env=env,
                              cwd=base_dir,  # Run from project root instead of changing directory
                              capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            raise Exception(f"Optimization script failed with error:\n{result.stderr}")
        
        # Print the output from the optimization
        print(result.stdout)
        
        elapsed_time = time.time() - start_time
        
        report_progress(3, "GRID OPTIMIZATION", "completed", elapsed_time)
        return True
    except Exception as e:
        report_progress(3, "GRID OPTIMIZATION", "failed")
        print(f"Error details: {str(e)}")
        return False


def display_execution_flags():
    """
    Display the current execution flag settings.
    """
    print("\nExecution Configuration:")
    print("  Traffic Calculation Module:", "ENABLED" if Config.EXECUTION_FLAGS['RUN_TRAFFIC_CALCULATION'] else "DISABLED")
    print("  Charging Hub Setup Module:", "ENABLED" if Config.EXECUTION_FLAGS['RUN_CHARGING_HUB_SETUP'] else "DISABLED")
    print("  Grid Optimization Module:", "ENABLED" if Config.EXECUTION_FLAGS['RUN_GRID_OPTIMIZATION'] else "DISABLED")
    
    if Config.EXECUTION_FLAGS['RUN_CHARGING_HUB_SETUP']:
        print("\n  Charging Hub Setup Sub-processes:")
        print("    Truck-Charging Type Matching:", "ENABLED" if Config.EXECUTION_FLAGS['RUN_TRUCK_MATCHING'] else "DISABLED")
        print("    Charging Hub Configuration:", "ENABLED" if Config.EXECUTION_FLAGS['RUN_HUB_CONFIGURATION'] else "DISABLED")
        print("    Demand Optimization:", "ENABLED" if Config.EXECUTION_FLAGS['RUN_DEMAND_OPTIMIZATION'] else "DISABLED")


def report_progress(phase_num, phase_name, status, elapsed_time=None, step_num=None, step_name=None, progress_percent=None):
    """
    Standardized progress reporting function for all phases and steps.
    
    Args:
        phase_num: Phase number (1, 2, or 3)
        phase_name: Phase name (e.g., "TRAFFIC CALCULATION")
        status: Status message (e.g., "started", "completed", "skipped", "failed", "progress")
        elapsed_time: Time taken to complete (for completion messages)
        step_num: Sub-step number within the phase (if applicable)
        step_name: Sub-step name (if applicable)
        progress_percent: Optional progress percentage (0-100)
    """
    # Construct the progress message
    if step_num and step_name:
        # Sub-step progress
        prefix = f"PHASE {phase_num} - STEP {step_num}: {step_name}"
    else:
        # Main phase progress
        prefix = f"PHASE {phase_num}: {phase_name}"
    
    # Append status and time if provided
    if status == "completed" and elapsed_time is not None:
        message = f"{prefix} {status.upper()} in {elapsed_time:.2f} seconds"
    elif status == "progress" and progress_percent is not None:
        message = f"{prefix} {progress_percent}% COMPLETE"
    else:
        message = f"{prefix} {status.upper()}"
    
    # Add progress percentage if provided
    if progress_percent is not None and status != "progress":
        message += f" [{progress_percent}%]"
    
    # Log and print the message
    print("\n" + "="*50)
    print(message)
    print("="*50)
    
    if status == "completed":
        logging.info(message)
    elif status == "failed":
        logging.error(message)
    else:
        logging.info(message)
    
    return message


def main(config=None):
    """
    Main function to orchestrate the entire charging hub optimization process.
    
    Args:
        config: Optional configuration object. If None, uses the global Config.
    """
    # If a config is provided, use it instead of the global one
    if config:
        global Config
        Config = config
        
    # Apply any environment variable overrides from the GUI
    apply_environment_overrides()

    print("\n" + "="*80)
    print("CHARGING HUB OPTIMIZATION - MAIN CONTROL SCRIPT")
    print("="*80)
    
    logging.info("Starting Charging Hub Optimization process")
    
    # Display execution flags to show which components will run
    display_execution_flags()
    
    # Track overall success
    all_phases_successful = True
    overall_start_time = time.time()
    
    # Execute phases in sequence based on flags
    phase1_success = run_traffic_calculation()
    all_phases_successful = all_phases_successful and phase1_success
    
    # Continue with phase 2 even if phase 1 failed, if not disabled
    if not phase1_success and Config.EXECUTION_FLAGS['RUN_TRAFFIC_CALCULATION']:
        print("\nWarning: Phase 1 failed. Continuing with Phase 2 anyway...")
        logging.warning("Phase 1 failed. Continuing with Phase 2 anyway.")
    
    phase2_success = run_charging_hub_setup()
    all_phases_successful = all_phases_successful and phase2_success
    
    # Continue with phase 3 even if phase 2 failed, if not disabled
    if not phase2_success and Config.EXECUTION_FLAGS['RUN_CHARGING_HUB_SETUP']:
        print("\nWarning: Phase 2 failed. Continuing with Phase 3 anyway...")
        logging.warning("Phase 2 failed. Continuing with Phase 3 anyway.")
    
    phase3_success = run_grid_optimization()
    all_phases_successful = all_phases_successful and phase3_success
    
    # Report overall results
    overall_elapsed_time = time.time() - overall_start_time
    
    print("\n" + "="*80)
    if all_phases_successful:
        print(f"CHARGING HUB OPTIMIZATION COMPLETED SUCCESSFULLY in {overall_elapsed_time:.2f} seconds")
        logging.info(f"Charging Hub Optimization process completed successfully in {overall_elapsed_time:.2f} seconds")
    else:
        print(f"CHARGING HUB OPTIMIZATION COMPLETED WITH ERRORS in {overall_elapsed_time:.2f} seconds")
        logging.warning(f"Charging Hub Optimization process completed with errors in {overall_elapsed_time:.2f} seconds")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()