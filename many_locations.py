# filepath: c:\Users\sande\OneDrive\Dokumente\GitHub\ChargingHub_Optimization\many_locations.py
import pandas as pd
from pathlib import Path
from config import Config
from main import main as run_all_processes
import logging
import os
from concurrent.futures import ProcessPoolExecutor
import copy
import traceback

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=log_dir/'many_locations.log',  # Separate log file
    level=logging.INFO,
    format='%(asctime)s; %(levelname)s; %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def process_single_location(location_data):
    """Process a single location in its own process."""
    try:
        location_id, longitude, latitude = location_data
        
        # Create a local Config instance to avoid modifying the global one
        local_config = copy.deepcopy(Config)
        local_config.DEFAULT_LOCATION = {'LONGITUDE': float(longitude), 'LATITUDE': float(latitude)}
        
        # Set result naming configuration
        if not hasattr(local_config, 'RESULT_NAMING'):
            local_config.RESULT_NAMING = {}
        local_config.RESULT_NAMING['USE_CUSTOM_ID'] = True
        local_config.RESULT_NAMING['CUSTOM_ID'] = str(location_id)
        
        # Debug output
        print(f"Processing location {location_id} with coordinates ({longitude}, {latitude})")
        
        # Run the optimization with the local config
        # Need to modify run_all_processes to accept a config parameter
        run_all_processes(config=local_config)
        
        return f"Location {location_id} completed successfully"
    except Exception as e:
        error_msg = f"Error processing location {location_id}: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return error_msg

def run_for_location(location_id, longitude, latitude):
    """Runs the optimization process for a specific location."""
    try:
        # Update the default location
        Config.DEFAULT_LOCATION = {'LONGITUDE': float(longitude), 'LATITUDE': float(latitude)}

        # Set a custom result ID
        if not hasattr(Config, 'RESULT_NAMING'):
            Config.RESULT_NAMING = {}
        Config.RESULT_NAMING['USE_CUSTOM_ID'] = True
        Config.RESULT_NAMING['CUSTOM_ID'] = str(location_id)
        
        # Debug output
        print(f"DEBUG: Setting custom ID to: {str(location_id)}")
        logging.info(f"DEBUG: Setting custom ID to: {str(location_id)}")

        logging.info(f"Running optimization for location {location_id} with coordinates ({longitude}, {latitude})")
        print(f"\nRunning optimization for location {location_id} with coordinates ({longitude}, {latitude})")

        run_all_processes()  # Execute the main optimization process

        logging.info(f"Optimization completed successfully for location {location_id}")

    except Exception as e:
        logging.error(f"Error running optimization for location {location_id}: {e}", exc_info=True)
        print(f"Error running optimization for location {location_id}: {e}")

def main():
    """Main function to iterate through locations and run the optimization."""
    # Get absolute path to locations file relative to script location
    script_dir = Path(__file__).parent.absolute()
    locations_file = script_dir / "locations_all.csv"
    
    try:
        # Read CSV with explicit path and error handling
        logging.info(f"Attempting to read locations from: {locations_file}")
        print(f"Reading locations from: {locations_file}")
        
        # Read with proper encoding and separator 
        df_locations = pd.read_csv(
            locations_file,
            delimiter=';',
            encoding='utf-8',
            dtype={
                'id': str,
                'longitude': float, 
                'latitude': float
            }
        )
        
        location_data_list = []
        
        for _, row in df_locations.iterrows():
            try:
                location_id = row['id']
                longitude = row['longitude'] 
                latitude = row['latitude']

                # Format location_id
                if not isinstance(location_id, (int, str)):
                    try:
                        location_id = int(location_id)
                        location_id = str(location_id).zfill(3)
                    except ValueError:
                        raise ValueError(f"Invalid location_id type: {type(location_id)}")
                else:
                    try:
                        location_id = str(int(location_id)).zfill(3)
                    except ValueError:
                        raise ValueError(f"Invalid location_id type: {type(location_id)}")
                
                longitude = float(longitude)
                latitude = float(latitude)
                
                location_data_list.append((location_id, longitude, latitude))
                
            except Exception as e:
                logging.error(f"Error preparing row: {row.to_dict()}. Error: {e}", exc_info=True)
                print(f"Error preparing row: {row.to_dict()}. Error: {e}")
        
        # Determine number of workers (adjust based on your system's capabilities)
        max_workers = min(os.cpu_count() or 1, len(location_data_list))
        print(f"Processing {len(location_data_list)} locations with {max_workers} parallel workers")
        
        # Process locations in parallel
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_single_location, location_data_list))
        
        # Log results
        for result in results:
            if "completed successfully" in result:
                logging.info(result)
            else:
                logging.error(result)

    except FileNotFoundError:
        logging.error(f"locations_all.csv not found at {locations_file}")
        print(f"Error: locations_all.csv not found at {locations_file}")
    except pd.errors.EmptyDataError:
        logging.error(f"locations_all.csv is empty")
        print("Error: locations_all.csv is empty")
    except pd.errors.ParserError as e:
        logging.error(f"Error parsing locations_all.csv: {e}")
        print(f"Error parsing locations_all.csv: {e}")
    except ValueError as e:
        logging.error(f"Data validation error: {e}")
        print(f"Data validation error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()