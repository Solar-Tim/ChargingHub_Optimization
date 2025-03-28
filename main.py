"""
Charging Hub Optimization - Main Control Script

This script serves as the global entry point for the charging hub optimization project.
It coordinates the execution of two main components:
1. Traffic Calculation: Calculates charging demand based on traffic patterns
2. Charging Hub Setup: Configures and optimizes the charging hub

Each component will be executed in sequence, with proper error handling.
"""

import os
import sys
import time
import logging
from pathlib import Path
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


def run_traffic_calculation():
    """
    Run the traffic calculation module.
    """
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


def main():
    """
    Main function to orchestrate the entire charging hub optimization process.
    """
    print("\n" + "="*80)
    print("CHARGING HUB OPTIMIZATION - MAIN CONTROL SCRIPT")
    print("="*80)
    
    logging.info("Starting Charging Hub Optimization process")
    
    # Track overall success
    all_phases_successful = True
    overall_start_time = time.time()
    
    # Execute phases in sequence
    phase1_success = run_traffic_calculation()
    all_phases_successful = all_phases_successful and phase1_success
    
    # Continue with phase 2 even if phase 1 failed
    if not phase1_success:
        print("\nWarning: Phase 1 failed. Continuing with Phase 2 anyway...")
        logging.warning("Phase 1 failed. Continuing with Phase 2 anyway.")
    
    phase2_success = run_charging_hub_setup()
    all_phases_successful = all_phases_successful and phase2_success
    
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