# filepath: c:\Users\sande\OneDrive\Dokumente\GitHub\ChargingHub_Optimization\many_locations.py
import pandas as pd
from pathlib import Path
from config import Config
from main import main as run_all_processes
import logging
import os

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

                run_for_location(location_id, longitude, latitude)

            except Exception as e:
                logging.error(f"Error processing row: {row.to_dict()}. Error: {e}", exc_info=True)
                print(f"Error processing row: {row.to_dict()}. Error: {e}")

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