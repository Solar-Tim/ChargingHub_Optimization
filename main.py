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
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=log_dir/'charging_hub_optimization.log',
    level=logging.INFO,
    format='%(asctime)s; %(levelname)s; %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set up Python path properly
base_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(base_dir, 'scripts')
traffic_dir = os.path.join(scripts_dir, 'traffic_calculation')
charginghub_dir = os.path.join(scripts_dir, 'charginghub_setup')

# Add all necessary directories to path
sys.path.append(scripts_dir)
sys.path.append(traffic_dir)
sys.path.append(charginghub_dir)

# Import configuration
from config import Config


def run_traffic_calculation():
    """
    Run the traffic calculation module.
    """
    if not Config.EXECUTION_FLAGS['RUN_TRAFFIC_CALCULATION']:
        logging.info("Traffic calculation module skipped (disabled in config)")
        print("\n" + "="*80)
        print("PHASE 1: TRAFFIC CALCULATION - SKIPPED (disabled in config)")
        print("="*80)
        return True
        
    print("\n" + "="*80)
    print("PHASE 1: TRAFFIC CALCULATION")
    print("="*80)
    
    logging.info("Starting Phase 1: Traffic Calculation")
    
    try:
        # Change working directory to traffic_calculation folder
        original_dir = os.getcwd()
        os.chdir(traffic_dir)
        
        # Import here to avoid issues with module paths
        from traffic_calculation.main import main as traffic_main
        
        start_time = time.time()
        traffic_main()
        elapsed_time = time.time() - start_time
        
        # Change back to original directory
        os.chdir(original_dir)
        
        logging.info(f"Phase 1 completed successfully in {elapsed_time:.2f} seconds")
        print(f"\nPhase 1 completed successfully in {elapsed_time:.2f} seconds")
        return True
    except Exception as e:
        logging.error(f"Error in Phase 1: {str(e)}")
        print(f"\nError in Phase 1: {str(e)}")
        return False


def run_charging_hub_setup():
    """
    Run the charging hub setup module.
    """
    if not Config.EXECUTION_FLAGS['RUN_CHARGING_HUB_SETUP']:
        logging.info("Charging hub setup module skipped (disabled in config)")
        print("\n" + "="*80)
        print("PHASE 2: CHARGING HUB SETUP - SKIPPED (disabled in config)")
        print("="*80)
        return True
    
    print("\n" + "="*80)
    print("PHASE 2: CHARGING HUB SETUP")
    print("="*80)
    
    logging.info("Starting Phase 2: Charging Hub Setup")
    
    try:
        # Change working directory to charginghub_setup folder
        original_dir = os.getcwd()
        os.chdir(charginghub_dir)
        
        # Import here to avoid issues with module paths
        from charginghub_setup.main import main as hub_main
        
        start_time = time.time()
        hub_main()
        elapsed_time = time.time() - start_time
        
        # Change back to original directory
        os.chdir(original_dir)
        
        logging.info(f"Phase 2 completed successfully in {elapsed_time:.2f} seconds")
        print(f"\nPhase 2 completed successfully in {elapsed_time:.2f} seconds")
        return True
    except Exception as e:
        logging.error(f"Error in Phase 2: {str(e)}")
        print(f"\nError in Phase 2: {str(e)}")
        return False

def run_grid_optimization():
    """
    Run the grid optimization module.
    """
    if not Config.EXECUTION_FLAGS['RUN_GRID_OPTIMIZATION']:
        logging.info("Grid optimization module skipped (disabled in config)")
        print("\n" + "="*80)
        print("PHASE 3: GRID OPTIMIZATION - SKIPPED (disabled in config)")
        print("="*80)
        return True
    
    print("\n" + "="*80)
    print("PHASE 3: GRID OPTIMIZATION")
    print("="*80)
    
    logging.info("Starting Phase 3: Grid Optimization")
    
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
        
        logging.info(f"Phase 3 completed successfully in {elapsed_time:.2f} seconds")
        print(f"\nPhase 3 completed successfully in {elapsed_time:.2f} seconds")
        return True
    except Exception as e:
        logging.error(f"Error in Phase 3: {str(e)}")
        print(f"\nError in Phase 3: {str(e)}")
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


def main():
    """
    Main function to orchestrate the entire charging hub optimization process.
    """
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