"""
Charging Hub Setup - Main Control Script

This script serves as the central entry point for the charging hub setup process.
It coordinates the execution of three main components:
1. Truck-Charging Type Matching: Generates truck data and assigns charging stations
2. Charging Hub Configuration: Determines optimal number of charging stations
3. Demand Optimization: Optimizes the charging process using mathematical optimization
"""

import os
import sys
import time
import logging
from pathlib import Path

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=log_dir/'charging_hub_setup.log',
    level=logging.INFO,
    format='%(asctime)s; %(levelname)s; %(message)s'
)

# Add root directory to Python path for configuration access
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import configuration
from config import Config

# Import local modules
try:
    import match_truck_chargingtype
    import charginghub_configuration
    import demand_optimization
    from config_setup import CONFIG
except ImportError as e:
    logging.error(f"Error importing required modules: {e}")
    print(f"Error: {e}. Make sure all required modules are in the same directory.")
    sys.exit(1)

def run_truck_matching():
    """Run Step 1: Match trucks to charging types and generate truck data."""
    if not Config.EXECUTION_FLAGS['RUN_TRUCK_MATCHING']:
        logging.info("Step 1: Truck-Charging Type Matching - SKIPPED (disabled in config)")
        print("\n" + "="*50)
        print("STEP 1: TRUCK-CHARGING TYPE MATCHING - SKIPPED (disabled in config)")
        print("="*50)
        return True
        
    print("\n" + "="*50)
    print("STEP 1: Match Trucks to Charging Types")
    print("="*50)
    
    logging.info("Starting Step 1: Truck-Charging Type Matching")
    
    try:
        start_time = time.time()
        match_truck_chargingtype.main()
        elapsed_time = time.time() - start_time
        
        logging.info(f"Step 1 completed successfully in {elapsed_time:.2f} seconds")
        print(f"\nStep 1 completed successfully in {elapsed_time:.2f} seconds")
        return True
    except Exception as e:
        logging.error(f"Error in Step 1: {str(e)}")
        print(f"\nError in Step 1: {str(e)}")
        return False

def run_hub_configuration():
    """Run Step 2: Configure charging hub based on truck data."""
    if not Config.EXECUTION_FLAGS['RUN_HUB_CONFIGURATION']:
        logging.info("Step 2: Charging Hub Configuration - SKIPPED (disabled in config)")
        print("\n" + "="*50)
        print("STEP 2: CHARGING HUB CONFIGURATION - SKIPPED (disabled in config)")
        print("="*50)
        return True
        
    print("\n" + "="*50)
    print("STEP 2: Charging Hub Configuration")
    print("="*50)
    
    logging.info("Starting Step 2: Charging Hub Configuration")
    
    try:
        start_time = time.time()
        charginghub_configuration.main()
        elapsed_time = time.time() - start_time
        
        logging.info(f"Step 2 completed successfully in {elapsed_time:.2f} seconds")
        print(f"\nStep 2 completed successfully in {elapsed_time:.2f} seconds")
        return True
    except Exception as e:
        logging.error(f"Error in Step 2: {str(e)}")
        print(f"\nError in Step 2: {str(e)}")
        return False

def run_demand_optimization():
    """Run Step 3: Optimize charging demand."""
    if not Config.EXECUTION_FLAGS['RUN_DEMAND_OPTIMIZATION']:
        logging.info("Step 3: Demand Optimization - SKIPPED (disabled in config)")
        print("\n" + "="*50)
        print("STEP 3: DEMAND OPTIMIZATION - SKIPPED (disabled in config)")
        print("="*50)
        return True
        
    print("\n" + "="*50)
    print("STEP 3: Demand Optimization")
    print("="*50)
    
    logging.info("Starting Step 3: Demand Optimization")
    
    try:
        start_time = time.time()
        demand_optimization.main()
        elapsed_time = time.time() - start_time
        
        logging.info(f"Step 3 completed successfully in {elapsed_time:.2f} seconds")
        print(f"\nStep 3 completed successfully in {elapsed_time:.2f} seconds")
        return True
    except Exception as e:
        logging.error(f"Error in Step 3: {str(e)}")
        print(f"\nError in Step 3: {str(e)}")
        return False

def display_config():
    """Display the current configuration settings."""
    print("\nCurrent Configuration:")
    print(f"  Charging Strategies: {CONFIG['STRATEGIES']}")
    print(f"  Target Charge Quota: {CONFIG['ladequote']}")
    print(f"  Power Setting: {CONFIG['power']} (NCS-HPC-MCS)")
    print(f"  Pause Times: {CONFIG['pause']} (short-long break minutes)\n")

def display_execution_flags():
    """Display the execution flags for sub-processes."""
    print("\nSub-process Execution Configuration:")
    print(f"  Truck-Charging Type Matching: {'ENABLED' if Config.EXECUTION_FLAGS['RUN_TRUCK_MATCHING'] else 'DISABLED'}")
    print(f"  Charging Hub Configuration: {'ENABLED' if Config.EXECUTION_FLAGS['RUN_HUB_CONFIGURATION'] else 'DISABLED'}")
    print(f"  Demand Optimization: {'ENABLED' if Config.EXECUTION_FLAGS['RUN_DEMAND_OPTIMIZATION'] else 'DISABLED'}\n")

def main():
    """Main function to orchestrate the charging hub setup process."""
    print("\n" + "="*50)
    print("CHARGING HUB SETUP - MAIN CONTROL SCRIPT")
    print("="*50)
    
    logging.info("Starting Charging Hub Setup process")
    display_config()
    display_execution_flags()
    
    # Track overall success
    all_steps_successful = True
    overall_start_time = time.time()
    
    # Execute steps in sequence based on flags
    step1_success = run_truck_matching()
    all_steps_successful = all_steps_successful and step1_success
    
    # Continue with step 2 if step 1 was skipped or successful, otherwise warn
    if not step1_success and Config.EXECUTION_FLAGS['RUN_TRUCK_MATCHING']:
        print("\nWarning: Step 1 failed. Continuing with Step 2 anyway...")
        logging.warning("Step 1 failed. Continuing with Step 2 anyway.")
    
    step2_success = run_hub_configuration()
    all_steps_successful = all_steps_successful and step2_success
    
    # Continue with step 3 if step 2 was skipped or successful, otherwise warn
    if not step2_success and Config.EXECUTION_FLAGS['RUN_HUB_CONFIGURATION']:
        print("\nWarning: Step 2 failed. Continuing with Step 3 anyway...")
        logging.warning("Step 2 failed. Continuing with Step 3 anyway.")
    
    step3_success = run_demand_optimization()
    all_steps_successful = all_steps_successful and step3_success
    
    # Report overall results
    overall_elapsed_time = time.time() - overall_start_time
    
    print("\n" + "="*50)
    if all_steps_successful:
        print(f"CHARGING HUB SETUP COMPLETED SUCCESSFULLY in {overall_elapsed_time:.2f} seconds")
        logging.info(f"Charging Hub Setup process completed successfully in {overall_elapsed_time:.2f} seconds")
    else:
        print(f"CHARGING HUB SETUP COMPLETED WITH ERRORS in {overall_elapsed_time:.2f} seconds")
        logging.warning(f"Charging Hub Setup process completed with errors in {overall_elapsed_time:.2f} seconds")
    print("="*50 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        logging.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        logging.error(f"Unexpected error: {str(e)}")
        sys.exit(1)