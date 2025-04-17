# filepath: c:\Users\sande\OneDrive\Dokumente\GitHub\ChargingHub_Optimization\many_locations.py
import pandas as pd
from pathlib import Path
from config import Config
from main import main as run_all_processes
import logging
import os
import concurrent.futures
from os import cpu_count # Import cpu_count

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=log_dir/'many_locations.log',  # Separate log file
    level=logging.INFO,
    format='%(asctime)s; %(levelname)s; %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


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

        # Debug output - Use location_id in log message for clarity
        print(f"DEBUG: [{location_id}] Setting custom ID to: {str(location_id)}")
        logging.info(f"DEBUG: [{location_id}] Setting custom ID to: {str(location_id)}")

        logging.info(f"[{location_id}] Running optimization for location {location_id} with coordinates ({longitude}, {latitude})")
        print(f"\n[{location_id}] Running optimization for location {location_id} with coordinates ({longitude}, {latitude})")

        # It's crucial that run_all_processes and its subprocesses
        # correctly use the Config settings (location, custom_id) set above
        # for this specific process/worker.
        run_all_processes()  # Execute the main optimization process

        logging.info(f"[{location_id}] Optimization completed successfully for location {location_id}")
        print(f"[{location_id}] Optimization completed successfully for location {location_id}")

    except Exception as e:
        logging.error(f"Error running optimization for location {location_id}: {e}", exc_info=True)
        print(f"Error running optimization for location {location_id}: {e}")


def main():
    """Main function to iterate through locations and run the optimization in parallel."""
    locations_file = Path("locations.csv")
    if not locations_file.exists():
        logging.error("locations.csv not found.")
        print("Error: locations.csv not found.")
        return

    try:
        df_locations = pd.read_csv(locations_file, sep=";")

        # Validate required columns
        required_columns = ['id', 'longitude', 'latitude']
        for col in required_columns:
            if col not in df_locations.columns:
                raise ValueError(f"Required column '{col}' missing in locations.csv")

        # Determine the number of workers
        # Use slightly less than max CPUs to leave resources for OS/other tasks
        max_workers = max(1, cpu_count() - 1 if cpu_count() else 1)
        print(f"Using {max_workers} workers for parallel processing.")
        logging.info(f"Initializing ProcessPoolExecutor with {max_workers} workers.")

        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for _, row in df_locations.iterrows():
                try:
                    location_id = row['id']
                    longitude = row['longitude']
                    latitude = row['latitude']

                    # Validate data types and format location_id
                    if not isinstance(location_id, (int, str)):
                        try:
                            location_id = int(location_id)  # Convert to int first to handle floats like 7.0
                            location_id = str(location_id).zfill(3)  # Convert to string and pad with leading zeros
                        except ValueError:
                            raise ValueError(f"Invalid location_id type: {type(location_id)}. Could not convert to string.")
                    else:
                        try:
                            location_id = str(int(location_id)).zfill(3) # Ensure it's an integer before padding
                        except ValueError:
                             raise ValueError(f"Invalid location_id type: {type(location_id)}. Could not convert to string.")
                    longitude = float(longitude)
                    latitude = float(latitude)

                    # Submit task to the executor
                    futures.append(executor.submit(run_for_location, location_id, longitude, latitude))

                except Exception as e:
                    logging.error(f"Error processing row before submission: {row.to_dict()}. Error: {e}", exc_info=True)
                    print(f"Error processing row before submission: {row.to_dict()}. Error: {e}")

            # Wait for all futures to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()  # Retrieve result or raise exception if task failed
                except Exception as e:
                    # Error is already logged within run_for_location, but log completion status here too
                    logging.error(f"A location task failed: {e}", exc_info=True)
                    print(f"A location task failed: {e}")

    except FileNotFoundError:
        logging.error(f"locations.csv not found at {locations_file}")
        print(f"Error: locations.csv not found at {locations_file}")
    except pd.errors.EmptyDataError:
        logging.error(f"locations.csv is empty")
        print("Error: locations.csv is empty")
    except pd.errors.ParserError as e:
        logging.error(f"Error parsing locations.csv: {e}")
        print(f"Error parsing locations.csv: {e}")
    except ValueError as e:
        logging.error(f"Data validation error: {e}")
        print(f"Data validation error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()