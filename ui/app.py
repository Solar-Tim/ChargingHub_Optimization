"""
ChargingHub Optimization - Web UI

This script provides a web interface for the Charging Hub Optimization project.
It allows users to configure parameters, run optimizations, and view results.
"""

import os
import sys
import json
import logging
import threading
import time
import re
import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, send_from_directory, send_file
from flask_socketio import SocketIO, emit
import subprocess
import importlib
import logging


# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Add scripts directory to path to find config.py
scripts_dir = os.path.join(parent_dir, 'scripts')
sys.path.append(scripts_dir)

# Import project modules
try:
    from scripts.config import Config
    config_module_path = os.path.join(scripts_dir, 'config.py')
except ImportError:
    try:
        from config import Config
        config_module_path = os.path.join(parent_dir, 'config.py')
    except ImportError:
        raise ImportError("Could not import Config module. Make sure config.py exists in the proper location.")

# Set up logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Create unique log filename with timestamp
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir/f'gui_log_{timestamp}.txt'

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s; %(levelname)s; %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'charginghub-secret-key'
socketio = SocketIO(app)

# Global variables for process management
active_processes = {}
process_logs = {}

# Helper function to read the latest log entries
def get_latest_logs(log_file, num_lines=50):
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            return lines[-num_lines:]
    except Exception as e:
        logger.error(f"Error reading log file {log_file}: {e}")
        return [f"Error reading log file: {str(e)}"]

# Function to reload configuration
def reload_config():
    """Reload the Config module to get the latest changes"""
    global Config
    try:
        # Reload the config module
        import importlib
        import scripts.config
        importlib.reload(scripts.config)
        Config = scripts.config.Config
        logger.info("Config module reloaded successfully")
        return True
    except Exception as e:
        logger.error(f"Error reloading config module: {e}")
        return False

# Helper function to update configuration file
def update_config_file(settings):
    """
    Update the config.py file with new settings
    
    Args:
        settings (dict): Dictionary containing the new settings
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Updating config.py with settings: {settings}")

    try:
        # Read the current config file
        with open(config_module_path, 'r') as f:
            config_content = f.read()
        
        # Process each setting and update the file
        for section, values in settings.items():
            if section == 'EXECUTION_FLAGS':
                for flag_name, flag_value in values.items():
                    # More flexible pattern to match the flag regardless of formatting
                    # This will match the flag name and its value, capturing any comments
                    pattern = rf"'{flag_name}':\s*(True|False)(\s*#[^\n]*)?"
                    
                    # If there was a comment, preserve it in the replacement
                    def replace_func(match):
                        comment = match.group(2) or ''
                        return f"'{flag_name}': {str(flag_value)}{comment}"
                    
                    # Use the replacement function
                    new_content = re.sub(pattern, replace_func, config_content)
                    
                    # Check if replacement actually happened
                    if new_content == config_content:
                        # Log warning if no replacement was made
                        logger.warning(f"No replacement made for '{flag_name}': {flag_value}. Pattern may not match.")
                        
                        # Try a more aggressive pattern as fallback
                        alt_pattern = rf"'{flag_name}':\s*[^,\n]+"
                        new_content = re.sub(alt_pattern, f"'{flag_name}': {str(flag_value)}", config_content)
                    
                    config_content = new_content
            
            elif section == 'CHARGING_CONFIG':
                for param, value in values.items():
                    # Format depends on the parameter type
                    if param == 'STRATEGY' or param == 'ALL_STRATEGIES':
                        # These are lists of strings
                        str_value = json.dumps(value) if isinstance(value, list) else f'["{value}"]'
                        pattern = rf"'{param}':\s*\[.*?\]"
                        replacement = f"'{param}': {str_value}"
                    else:
                        # Other parameters could be strings, floats, etc.
                        if isinstance(value, str):
                            str_value = f"'{value}'"
                        else:
                            str_value = str(value)
                        pattern = rf"'{param}':\s*(?:(?:'[^']*')|(?:\d+(?:\.\d+)?))"
                        replacement = f"'{param}': {str_value}"
                    
                    # Apply replacement and check if it worked
                    new_content = re.sub(pattern, replacement, config_content)
                    if new_content == config_content:
                        logger.warning(f"No replacement made for '{param}': {value} in CHARGING_CONFIG")
                    config_content = new_content
            
            # Rest of the function remains the same
            elif section == 'DEFAULT_LOCATION':
                for coord_name, coord_value in values.items():
                    pattern = rf"'{coord_name}':\s*[\d\.]+"
                    replacement = f"'{coord_name}': {float(coord_value)}"
                    config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'MANUAL_DISTANCES':
                for distance_name, distance_value in values.items():
                    pattern = rf"'{distance_name}':\s*[\d\.]+"
                    replacement = f"'{distance_name}': {float(distance_value)}"
                    config_content = re.sub(pattern, replacement, config_content)

            elif section == 'RESULT_NAMING':
                for param, value in values.items():
                    if param == 'USE_CUSTOM_ID':
                        pattern = rf"'USE_CUSTOM_ID':\s*(True|False)(\s*#[^\n]*)?"
                        def replace_func(match):
                            comment = match.group(2) or ''
                            return f"'USE_CUSTOM_ID': {str(value)}{comment}"
                        config_content = re.sub(pattern, replace_func, config_content)
                    elif param == 'CUSTOM_ID':
                        pattern = rf"'CUSTOM_ID':\s*'[^']*'"
                        replacement = f"'CUSTOM_ID': '{value}'"
                        config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'BATTERY_CONFIG':
                for param, value in values.items():
                    pattern = rf"'{param}':\s*[\d\.]+"
                    replacement = f"'{param}': {float(value)}"
                    config_content = re.sub(pattern, replacement, config_content)
                    
            elif section == 'GRID_CAPACITIES':
                for param, value in values.items():
                    pattern = rf"'{param}':\s*[\d\.]+"
                    replacement = f"'{param}': {float(value)}"
                    config_content = re.sub(pattern, replacement, config_content)
                    
            elif section == 'SPATIAL':
                for param, value in values.items():
                    if isinstance(value, str):
                        pattern = rf"'{param}':\s*'[^']*'"
                        replacement = f"'{param}': '{value}'"
                    else:
                        pattern = rf"'{param}':\s*[\d\.]+"
                        replacement = f"'{param}': {float(value)}"
                    config_content = re.sub(pattern, replacement, config_content)
            
            # NEW SECTIONS BELOW
            
            elif section == 'FORECAST_YEAR':
                # Update the forecast year
                pattern = r"FORECAST_YEAR\s*=\s*'[^']*'"
                replacement = f"FORECAST_YEAR = '{values}'"
                config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'SCENARIOS':
                # Handle TARGET_YEARS list
                if 'TARGET_YEARS' in values:
                    target_years = values['TARGET_YEARS']
                    str_value = json.dumps(target_years) if isinstance(target_years, list) else f"['{target_years}']"
                    pattern = r"'TARGET_YEARS':\s*\[.*?\]"
                    replacement = f"'TARGET_YEARS': {str_value}"
                    config_content = re.sub(pattern, replacement, config_content)
                
                # Handle R_BEV and R_TRAFFIC dictionaries
                for scenario_type in ['R_BEV', 'R_TRAFFIC']:
                    if scenario_type in values:
                        for year, value in values[scenario_type].items():
                            pattern = rf"'{year}':\s*[\d\.]+\s*(?:#.*)?"  # Match year and value, including optional comment
                            replacement = f"'{year}': {float(value)}  #"  # Keep comment format
                            # Look for pattern within the specific scenario section
                            scenario_pattern = rf"'{scenario_type}':\s*{{.*?{pattern}.*?}}"
                            if re.search(scenario_pattern, config_content, re.DOTALL):
                                config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'CAPACITY_FEES':
                for fee_type, fee_value in values.items():
                    pattern = rf"'{fee_type}':\s*[\d\.]+"
                    replacement = f"'{fee_type}': {float(fee_value)}"
                    config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'CHARGING_TYPES':
                for charger_type, charger_config in values.items():
                    for param, value in charger_config.items():
                        pattern = rf"'{charger_type}':\s*{{.*?'({param})':\s*([\d\.]+).*?}}"
                        # We need to preserve the structure, so we'll use a function for replacement
                        config_content = re.sub(
                            pattern,
                            lambda m: m.group(0).replace(f"'{param}': {m.group(2)}", f"'{param}': {float(value)}"),
                            config_content,
                            flags=re.DOTALL
                        )
            
            elif section == 'MANUAL_CHARGER_COUNT':
                for charger_type, count in values.items():
                    pattern = rf"'{charger_type}':\s*[\d]+"
                    replacement = f"'{charger_type}': {int(count)}"
                    config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'SUBSTATION_CONFIG':
                # Handle the nested dictionaries for DISTRIBUTION and TRANSMISSION
                for substation_type in ['DISTRIBUTION', 'TRANSMISSION']:
                    if substation_type in values:
                        for param, value in values[substation_type].items():
                            pattern = rf"'{substation_type}':\s*{{.*?'({param})':\s*([\d\.]+).*?}}"
                            config_content = re.sub(
                                pattern,
                                lambda m: m.group(0).replace(f"'{param}': {m.group(2)}", f"'{param}': {float(value)}"),
                                config_content,
                                flags=re.DOTALL
                            )
                
                # Handle HV_SUBSTATION_COST
                if 'HV_SUBSTATION_COST' in values:
                    pattern = r"'HV_SUBSTATION_COST':\s*[\d\.]+"
                    replacement = f"'HV_SUBSTATION_COST': {float(values['HV_SUBSTATION_COST'])}"
                    config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'TRANSFORMER_CONFIG':
                if 'CAPACITIES' in values:
                    capacities = values['CAPACITIES']
                    str_value = f"[{', '.join(str(c) for c in capacities)}]"
                    pattern = r"\"CAPACITIES\":\s*\[.*?\]"
                    replacement = f"\"CAPACITIES\": {str_value}"
                    config_content = re.sub(pattern, replacement, config_content)
                
                if 'COSTS' in values:
                    costs = values['COSTS']
                    str_value = f"[{', '.join(str(c) for c in costs)}]"
                    pattern = r"\"COSTS\":\s*\[.*?\]"
                    replacement = f"\"COSTS\": {str_value}"
                    config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'CABLE_CONFIG':
                # Handle nested structure for LV, MV, and CONSTRUCTION sections
                for cable_section in ['LV', 'MV', 'CONSTRUCTION']:
                    if cable_section in values:
                        for param, value in values[cable_section].items():
                            pattern = rf"'{cable_section}':\s*{{.*?'({param})':\s*([\d\.]+).*?}}"
                            config_content = re.sub(
                                pattern,
                                lambda m: m.group(0).replace(f"'{param}': {m.group(2)}", f"'{param}': {float(value)}"),
                                config_content,
                                flags=re.DOTALL
                            )
            
            elif section == 'BREAKS':
                for param, value in values.items():
                    if param == 'RANDOM_RANGE':
                        # Special handling for tuple
                        if isinstance(value, list) and len(value) == 2:
                            pattern = r"'RANDOM_RANGE':\s*\([\d\.]*,\s*[\d\.]*\)"
                            replacement = f"'RANDOM_RANGE': ({value[0]},{value[1]})"
                            config_content = re.sub(pattern, replacement, config_content)
                    else:
                        pattern = rf"'{param}':\s*[\d\.]+"
                        replacement = f"'{param}': {float(value)}"
                        config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'TIME':
                for param, value in values.items():
                    pattern = rf"'{param}':\s*[\d]+"
                    replacement = f"'{param}': {int(value)}"
                    config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'CSV':
                for param, value in values.items():
                    pattern = rf"'{param}':\s*'[^']*'"
                    replacement = f"'{param}': '{value}'"
                    config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'PATHS' or section == 'TRAFFIC_PATHS':
                for path_name, path_value in values.items():
                    # Need to be careful with path separators in regex
                    path_value_escaped = path_value.replace('\\', '\\\\')
                    pattern = rf"'{path_name}':\s*os\.path\.join\(.*?\)"
                    replacement = f"'{path_name}': '{path_value_escaped}'"
                    config_content = re.sub(pattern, replacement, config_content)
            
            elif section == 'aluminium_kabel' or section == 'kupfer_kabel':
                for prop, values_list in values.items():
                    # Convert list to string representation
                    values_str = f"[{', '.join([str(val) for val in values_list])}]"
                    pattern = rf'"{prop}":\s*\[.*?\]'
                    replacement = f'"{prop}": {values_str}'
                    config_content = re.sub(pattern, replacement, config_content, flags=re.DOTALL)
            
            # Add any other sections as needed
                    
        # Write the updated config back to file
        with open(config_module_path, 'w') as f:
            f.write(config_content)
        
        # Reload the config module to apply changes
        reload_config()
        
        return True
    except Exception as e:
        logger.error(f"Error updating config file: {e}")
        logger.exception("Detailed traceback:")
        return False

# Helper function to run a command and stream output to client
def run_command_with_output(process_id, cmd, cwd=None, env=None):
    process_logs[process_id] = []

    def run_and_stream():
        logger.info(f"Starting process {process_id}: {cmd}")
        
        # Use the provided environment or copy the current environment
        process_env = env if env else os.environ.copy()
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            cwd=cwd,
            env=process_env
        )
        active_processes[process_id] = process
        
        socketio.emit('process_started', {'id': process_id})
        
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            process_logs[process_id].append(line)
            socketio.emit('process_output', {'id': process_id, 'output': line})
            logger.debug(f"Process {process_id} output: {line}")
        
        process.wait()
        exit_code = process.returncode
        logger.info(f"Process {process_id} completed with exit code {exit_code}")
        socketio.emit('process_completed', {
            'id': process_id,
            'exitCode': exit_code,
            'success': exit_code == 0
        })
        
    thread = threading.Thread(target=run_and_stream)
    thread.daemon = True
    thread.start()
    return True

# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')

# Route for the dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Route for the map
@app.route('/map')
def map_page():
    # Find all map files
    map_dir = Path(parent_dir) / 'results' / 'maps'
    map_files = []
    
    if map_dir.exists():
        # Get all HTML files in the maps directory
        map_files = list(map_dir.glob('*.html'))
        
        # Categorize maps by type
        combined_maps = [f for f in map_files if 'combined' in f.name.lower()]
        power_line_maps = [f for f in map_files if 'power' in f.name.lower() or 'line' in f.name.lower()]
        substation_maps = [f for f in map_files if 'substation' in f.name.lower()]
        
        # Sort each category by modification time (newest first)
        for map_list in [combined_maps, power_line_maps, substation_maps]:
            map_list.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Create a dictionary with the most recent map of each type
        latest_maps = {
            'combined': combined_maps[0].name if combined_maps else None,
            'power_line': power_line_maps[0].name if power_line_maps else None,
            'substation': substation_maps[0].name if substation_maps else None
        }
    else:
        latest_maps = {
            'combined': None,
            'power_line': None,
            'substation': None
        }
    
    # Get all map files for the dropdown
    all_maps = []
    if map_dir.exists():
        for map_file in map_dir.glob('*.html'):
            map_type = None
            if 'combined' in map_file.name.lower():
                map_type = 'Combined Map'
            elif 'power' in map_file.name.lower() or 'line' in map_file.name.lower():
                map_type = 'Power Line Map'
            elif 'substation' in map_file.name.lower():
                map_type = 'Substation Map'
            else:
                map_type = 'Other Map'
                
            all_maps.append({
                'name': map_file.name,
                'type': map_type,
                'date': datetime.datetime.fromtimestamp(map_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            })
            
        # Sort by date (newest first)
        all_maps.sort(key=lambda x: x['date'], reverse=True)
        
    return render_template('map.html', latest_maps=latest_maps, all_maps=all_maps)

# Route to serve map files
@app.route('/maps/<map_name>')
def serve_map(map_name):
    map_dir = os.path.join(parent_dir, 'results', 'maps')
    
    # Validate the filename to prevent directory traversal attacks
    if '..' in map_name or '/' in map_name:
        return "Invalid map name", 400
        
    # Check if the file exists
    if not os.path.exists(os.path.join(map_dir, map_name)):
        return "Map not found", 404
        
    # Serve the file directly
    return send_from_directory(map_dir, map_name)

# Route for the configuration page
@app.route('/configuration')
def configuration():
    # Load current configuration from config.py
    reload_config()  # Ensure we have the latest config
    
    # Get all configuration sections we want to expose
    charging_config = Config.CHARGING_CONFIG
    execution_flags = Config.EXECUTION_FLAGS
    result_naming = Config.RESULT_NAMING
    default_location = Config.DEFAULT_LOCATION
    battery_config = Config.BATTERY_CONFIG
    
    # Add missing configuration data needed by templates
    charging_types = Config.CHARGING_TYPES
    manual_charger_count = Config.MANUAL_CHARGER_COUNT
    spatial = Config.SPATIAL
    manual_distances = Config.MANUAL_DISTANCES
    grid_capacities = Config.GRID_CAPACITIES
    capacity_fees = Config.CAPACITY_FEES
    substation_config = Config.SUBSTATION_CONFIG
    transformer_config = Config.TRANSFORMER_CONFIG
    cable_config = Config.CABLE_CONFIG
    breaks = Config.BREAKS
    day_mapping = Config.DAY_MAPPING
    scenarios = Config.SCENARIOS
    time_config = Config.TIME
    csv_config = Config.CSV
    paths = Config.PATHS
    traffic_paths = Config.TRAFFIC_PATHS
    forecast_year = Config.FORECAST_YEAR
    
    # Add aluminum and copper cable data
    aluminium_kabel = Config.aluminium_kabel
    kupfer_kabel = Config.kupfer_kabel
    
    return render_template(
        'configuration.html',
        charging_config=charging_config,
        execution_flags=execution_flags,
        result_naming=result_naming,
        default_location=default_location,
        battery_config=battery_config,
        charging_types=charging_types,
        manual_charger_count=manual_charger_count,
        spatial=spatial,
        manual_distances=manual_distances,
        grid_capacities=grid_capacities,
        capacity_fees=capacity_fees,
        substation_config=substation_config,
        transformer_config=transformer_config,
        cable_config=cable_config,
        breaks=breaks,
        day_mapping=day_mapping,
        scenarios=scenarios,
        time=time_config,
        csv=csv_config,
        paths=paths,
        traffic_paths=traffic_paths,
        forecast_year=forecast_year,
        aluminium_kabel=aluminium_kabel,
        kupfer_kabel=kupfer_kabel
    )

# Route for the logs page
@app.route('/logs')
def logs():
    # Get available log files
    log_files = []
    for file in os.listdir(log_dir):
        if file.endswith('.log') or file.endswith('.txt'):
            log_files.append({
                'name': file,
                'path': os.path.join('logs', file),
                'date': os.path.getmtime(os.path.join(log_dir, file))
            })
    
    # Sort by date (newest first)
    log_files.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('logs.html', log_files=log_files)

# Route for the results page
def results_page():
    # Provide initial list of result files to template
    files = get_result_files()
    return render_template('results.html', result_files=files)
app.add_url_rule('/results', 'results_page', results_page)

# Helper function to list result files
def get_result_files():
    result_dir = Path(parent_dir) / 'results'
    files = []
    if result_dir.exists():
        for file_path in result_dir.glob('optimization_*.json'):
            file_name = file_path.name
            base = file_name.replace('optimization_', '').replace('.json', '')
            parts = base.split('_', 1)
            id_part = parts[0]
            type_part = parts[1] if len(parts) > 1 else ''
            try:
                date = file_path.stat().st_mtime
            except:
                date = 0
            files.append({
                'name': file_name,
                'id': id_part,
                'type': type_part,
                'date': date,
                'date_formatted': datetime.datetime.fromtimestamp(date).strftime('%Y-%m-%d')
            })
    return files

# API endpoint to get list of result files
@app.route('/api/results/list')
def api_results_list():
    results = get_result_files()
    return jsonify({ 'success': True, 'results': results })

# API endpoint to get content of a specific result file
@app.route('/api/results/<result_name>')
def api_results_content(result_name):
    result_dir = Path(parent_dir) / 'results'
    file_path = result_dir / result_name
    if not file_path.exists() or not file_path.is_file():
        return jsonify({ 'error': 'Result file not found' }), 404
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({ 'error': str(e) }), 500

# API endpoint to download a result file
def api_results_download(result_name):
    result_dir = Path(parent_dir) / 'results'
    file_path = result_dir / result_name
    if not file_path.exists() or not file_path.is_file():
        return jsonify({ 'error': 'Result file not found' }), 404
    fmt = request.args.get('format', 'json')
    if fmt != 'json':
        return jsonify({ 'error': 'Unsupported format' }), 400
    return send_from_directory(str(result_dir), result_name, as_attachment=True)
app.add_url_rule('/api/results/download/<result_name>', 'api_results_download', api_results_download)

# API route to get log content
@app.route('/api/logs/<log_name>')
def get_log_content(log_name):
    log_path = os.path.join(log_dir, log_name)
    if not os.path.exists(log_path):
        return jsonify({'error': 'Log file not found'}), 404
    
    try:
        lines = get_latest_logs(log_path, 500)
        return jsonify({'content': lines})
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return jsonify({'error': str(e)}), 500

# API route to save configuration
@app.route('/api/config/save', methods=['POST'])
def save_config():
    try:
        data = request.json
        logger.info(f"Received configuration update: {data}")
        
        # Update config.py file with the new settings
        success = update_config_file(data)
        
        if success:
            logger.info("Configuration updated successfully")
            resp = jsonify({'success': True})
            # Add no-cache headers
            resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            resp.headers['Pragma'] = 'no-cache'
            resp.headers['Expires'] = '0'
            return resp
        else:
            error_msg = "Failed to update configuration"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'details': 'Check server logs for more information'}), 500
    except Exception as e:
        error_msg = f"Error saving configuration: {str(e)}"
        logger.error(error_msg)
        logger.exception("Detailed traceback:")  # Add full traceback
        
        # Return a more detailed error response
        return jsonify({
            'error': error_msg,
            'details': 'An exception occurred during configuration update',
            'exception_type': type(e).__name__
        }), 500

# API route to get current configuration
@app.route('/api/config')
def get_config():
    try:
        # Reload config to ensure we have the latest
        reload_config()
        
        return jsonify({
            'success': True,
            'config': {
                'CHARGING_CONFIG': Config.CHARGING_CONFIG,
                'EXECUTION_FLAGS': Config.EXECUTION_FLAGS,
                'DEFAULT_LOCATION': Config.DEFAULT_LOCATION,
                'RESULT_NAMING': Config.RESULT_NAMING,
                'BATTERY_CONFIG': Config.BATTERY_CONFIG
            }
        })
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        return jsonify({'error': str(e)}), 500

# API route to run the main optimization
@app.route('/api/run/main', methods=['POST'])
def run_main():
    try:
        # Get any configuration updates from the request
        config_updates = request.json.get('config', {})
        if config_updates:
            # Update configuration before running
            update_config_file(config_updates)
        
        # Prepare environment
        env = os.environ.copy()
        
        # Use python from sys.executable to ensure we use the same Python as the UI
        python_exec = sys.executable
        cmd = f"{python_exec} {os.path.join(scripts_dir, 'main.py')}"
        
        # Run from project root
        run_command_with_output('main', cmd, cwd=parent_dir, env=env)
        return jsonify({'success': True, 'processId': 'main'})
    except Exception as e:
        logger.error(f"Error running main.py: {e}")
        return jsonify({'error': str(e)}), 500

# API routes for individual optimization steps
@app.route('/api/run/traffic_calculation', methods=['POST'])
def run_traffic():
    try:
        # Get any configuration updates from the request
        config_updates = request.json.get('config', {})
        if config_updates:
            # Update configuration before running
            update_config_file(config_updates)
        
        # Set environment variables to run only traffic calculation
        env = os.environ.copy()
        env['CHARGING_HUB_RUN_TRAFFIC_CALCULATION'] = '1'
        env['CHARGING_HUB_RUN_CHARGING_HUB_SETUP'] = '0'
        env['CHARGING_HUB_RUN_GRID_OPTIMIZATION'] = '0'
        
        # Use python from sys.executable to ensure we use the same Python as the UI
        python_exec = sys.executable
        cmd = f"{python_exec} {os.path.join(scripts_dir, 'main.py')}"
        
        run_command_with_output('traffic', cmd, cwd=parent_dir, env=env)
        return jsonify({'success': True, 'processId': 'traffic'})
    except Exception as e:
        logger.error(f"Error running traffic calculation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/run/charging_hub_setup', methods=['POST'])
def run_charging_hub_setup():
    try:
        # Get any configuration updates from the request
        config_updates = request.json.get('config', {})
        if config_updates:
            # Update configuration before running
            update_config_file(config_updates)
        
        # Set environment variables to run only charging hub setup
        env = os.environ.copy()
        env['CHARGING_HUB_RUN_TRAFFIC_CALCULATION'] = '0'
        env['CHARGING_HUB_RUN_CHARGING_HUB_SETUP'] = '1'
        env['CHARGING_HUB_RUN_GRID_OPTIMIZATION'] = '0'
        
        # Use python from sys.executable to ensure we use the same Python as the UI
        python_exec = sys.executable
        cmd = f"{python_exec} {os.path.join(scripts_dir, 'main.py')}"
        
        run_command_with_output('charging_hub', cmd, cwd=parent_dir, env=env)
        return jsonify({'success': True, 'processId': 'charging_hub'})
    except Exception as e:
        logger.error(f"Error running charging hub setup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/run/grid_optimization', methods=['POST'])
def run_grid_optimization():
    try:
        # Get any configuration updates from the request
        config_updates = request.json.get('config', {})
        if config_updates:
            # Update configuration before running
            update_config_file(config_updates)
        
        # Set environment variables to run only grid optimization
        env = os.environ.copy()
        env['CHARGING_HUB_RUN_TRAFFIC_CALCULATION'] = '0'
        env['CHARGING_HUB_RUN_CHARGING_HUB_SETUP'] = '0'
        env['CHARGING_HUB_RUN_GRID_OPTIMIZATION'] = '1'
        
        # If custom ID is provided in the configuration, pass it to the subprocess
        if Config.RESULT_NAMING.get('USE_CUSTOM_ID', False):
            custom_id = Config.RESULT_NAMING.get('CUSTOM_ID', '')
            env['CHARGING_HUB_CUSTOM_ID'] = custom_id
            logger.info(f"Passing custom ID to subprocess: {custom_id}")
            
        # Pass location coordinates through environment variables
        env['CHARGING_HUB_LONGITUDE'] = str(Config.DEFAULT_LOCATION['LONGITUDE'])
        env['CHARGING_HUB_LATITUDE'] = str(Config.DEFAULT_LOCATION['LATITUDE'])
        logger.info(f"Passing coordinates to subprocess: ({Config.DEFAULT_LOCATION['LONGITUDE']}, {Config.DEFAULT_LOCATION['LATITUDE']})")
        
        # Pass battery status through environment variables
        env['CHARGING_HUB_INCLUDE_BATTERY'] = str(int(Config.EXECUTION_FLAGS['INCLUDE_BATTERY']))
        logger.info(f"Passing battery status to subprocess: {Config.EXECUTION_FLAGS['INCLUDE_BATTERY']}")
        
        # Use python from sys.executable to ensure we use the same Python as the UI
        python_exec = sys.executable
        cmd = f"{python_exec} {os.path.join(scripts_dir, 'main.py')}"
        
        run_command_with_output('grid_opt', cmd, cwd=parent_dir, env=env)
        return jsonify({'success': True, 'processId': 'grid_opt'})
    except Exception as e:
        logger.error(f"Error running grid optimization: {e}")
        return jsonify({'error': str(e)}), 500

# API route to get process status
@app.route('/api/process/<process_id>/status')
def get_process_status(process_id):
    if process_id not in active_processes:
        return jsonify({'running': False, 'logs': process_logs.get(process_id, [])})
    
    process = active_processes[process_id]
    is_running = process.poll() is None
    
    return jsonify({
        'running': is_running,
        'logs': process_logs.get(process_id, [])
    })

# API route to stop a process
@app.route('/api/process/<process_id>/stop', methods=['POST'])
def stop_process(process_id):
    if process_id not in active_processes:
        return jsonify({'error': 'Process not found'}), 404
    
    process = active_processes[process_id]
    if process.poll() is None:  # Process still running
        try:
            process.terminate()
            time.sleep(1)
            if process.poll() is None:  # Still running after terminate
                process.kill()
            logger.info(f"Process {process_id} stopped by user")
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Error stopping process {process_id}: {e}")
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'success': True, 'message': 'Process already completed'})

# Run the server
if __name__ == '__main__':
    # Log that the server is starting
    logger.info("Starting ChargingHub Optimization Web UI")
    print(f"Starting ChargingHub Optimization Web UI on http://localhost:5000")
    print(f"Log file: {log_file}")
    
    # Start the server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)