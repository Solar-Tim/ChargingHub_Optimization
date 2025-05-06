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
import astor
import ast


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

def update_config_file(settings):
    """
    Update the config.py file with new settings using AST (Abstract Syntax Tree)
    
    Args:
        settings (dict): Dictionary containing the new settings
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Updating config.py with settings: {settings}")
    
    try:
        # Create a backup of the config file
        backup_path = f"{config_module_path}.bak"
        with open(config_module_path, 'r') as f:
            original_content = f.read()
            
        # Save backup
        with open(backup_path, 'w') as f:
            f.write(original_content)
        
        # Special handling for TIME dictionary
        if 'TIME' in settings:
            # Get current TIME values from Config
            current_time = Config.TIME.copy()
            
            # Only update values that are actually provided and valid
            for key, value in settings['TIME'].items():
                if key in current_time:
                    try:
                        # Validate the value (ensure it's an integer and makes sense)
                        if key == 'RESOLUTION_MINUTES':
                            # Must be > 0 and divide evenly into 60
                            if value <= 0 or 60 % value != 0:
                                logger.warning(f"Invalid {key} value: {value}. Must be > 0 and divide evenly into 60.")
                                continue
                        elif key in ['TIMESTEPS_PER_DAY', 'TIMESTEPS_PER_WEEK']:
                            # These should be calculated values, not directly set
                            # TIMESTEPS_PER_DAY = 24 hours * 60 minutes / RESOLUTION_MINUTES
                            # TIMESTEPS_PER_WEEK = TIMESTEPS_PER_DAY * 7
                            continue
                        
                        # For other values, just ensure they're positive integers
                        if value <= 0:
                            logger.warning(f"Invalid {key} value: {value}. Must be > 0.")
                            continue
                            
                        # Update the value in the current_time dict
                        current_time[key] = value
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid {key} value: {value}. Must be an integer.")
                        continue
            
            # Recalculate dependent values
            if 'RESOLUTION_MINUTES' in current_time:
                resolution = current_time['RESOLUTION_MINUTES']
                current_time['TIMESTEPS_PER_DAY'] = 24 * 60 // resolution
                current_time['TIMESTEPS_PER_WEEK'] = current_time['TIMESTEPS_PER_DAY'] * 7
                
            # Replace the settings TIME with our validated version
            settings['TIME'] = current_time

        # Special handling for array synchronization (aluminium_kabel, kupfer_kabel)
        if 'aluminium_kabel' in settings:
            # Get current values
            current_values = Config.aluminium_kabel.copy()
            new_values = settings['aluminium_kabel']
            
            # Check that all arrays have the same length
            lengths = [len(new_values.get(key, [])) for key in ['Nennquerschnitt', 'Belastbarkeit', 'Kosten']]
            if len(set(lengths)) > 1:
                logger.warning(f"aluminium_kabel arrays have inconsistent lengths: {lengths}. Using current values.")
            else:
                # Update values while preserving structure
                for key in current_values:
                    if key in new_values and isinstance(new_values[key], list):
                        current_values[key] = new_values[key]
            
            settings['aluminium_kabel'] = current_values

        # Similar handling for kupfer_kabel
        if 'kupfer_kabel' in settings:
            # Get current values
            current_values = Config.kupfer_kabel.copy()
            new_values = settings['kupfer_kabel']
            
            # Check that all arrays have the same length
            lengths = [len(new_values.get(key, [])) for key in ['Nennquerschnitt', 'Kosten']]
            if len(set(lengths)) > 1:
                logger.warning(f"kupfer_kabel arrays have inconsistent lengths: {lengths}. Using current values.")
            else:
                # Update values while preserving structure
                for key in current_values:
                    if key in new_values and isinstance(new_values[key], list):
                        current_values[key] = new_values[key]
            
            settings['kupfer_kabel'] = current_values

        # Special handling for TRANSFORMER_CONFIG
        if 'TRANSFORMER_CONFIG' in settings:
            current_config = Config.TRANSFORMER_CONFIG.copy()
            new_config = settings['TRANSFORMER_CONFIG']
            
            # Check that CAPACITIES and COSTS have the same length
            if ('CAPACITIES' in new_config and 'COSTS' in new_config and 
                len(new_config['CAPACITIES']) != len(new_config['COSTS'])):
                logger.warning("TRANSFORMER_CONFIG has inconsistent lengths for CAPACITIES and COSTS. Using current values.")
            else:
                # Update values while preserving structure
                for key in current_config:
                    if key in new_config:
                        current_config[key] = new_config[key]
            
            settings['TRANSFORMER_CONFIG'] = current_config

        # Special handling for SCENARIOS
        if 'SCENARIOS' in settings:
            current_scenarios = Config.SCENARIOS.copy()
            new_scenarios = settings['SCENARIOS']
            
            # Make sure TARGET_YEARS is consistent with the years in R_BEV and R_TRAFFIC
            if 'TARGET_YEARS' in new_scenarios:
                target_years = new_scenarios['TARGET_YEARS']
                
                # Ensure R_BEV and R_TRAFFIC are consistent with TARGET_YEARS
                for key in ['R_BEV', 'R_TRAFFIC']:
                    if key in new_scenarios:
                        # Check if all target years exist in the dictionary
                        missing_years = [year for year in target_years if year not in new_scenarios[key]]
                        if missing_years:
                            logger.warning(f"Missing years {missing_years} in {key}. Using current values.")
                            # Keep the current values for this dictionary
                            new_scenarios[key] = current_scenarios[key]
            
            # Update values while preserving structure
            for key in current_scenarios:
                if key in new_scenarios:
                    current_scenarios[key] = new_scenarios[key]
            
            settings['SCENARIOS'] = current_scenarios
            
        # Apply the changes to the in-memory configuration
        changes_made = False
        for section, values in settings.items():
            if hasattr(Config, section):
                section_obj = getattr(Config, section)
                
                if isinstance(section_obj, dict):
                    for key, value in values.items():
                        if key in section_obj:
                            # Only mark as changed if the value is actually different
                            if section_obj[key] != value:
                                section_obj[key] = value
                                changes_made = True
                                logger.info(f"Updated Config.{section}['{key}'] = {value}")
        
        # If changes were made, we need to update the file
        if changes_made:
            
            # Parse the original code into an AST
            tree = ast.parse(original_content)
            
            # Define a transformer to modify the AST
            class ConfigTransformer(ast.NodeTransformer):
                def visit_ClassDef(self, node):
                    # Only process the Config class
                    if node.name == 'Config':
                        # Process class body
                        for i, item in enumerate(node.body):
                            # Look for assignments
                            if isinstance(item, ast.Assign):
                                # Check if this is a section we want to modify
                                if len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
                                    section_name = item.targets[0].id
                                    if section_name in settings:
                                        # Update the value based on its type
                                        item.value = self.transform_value(item.value, settings[section_name], 
                                                                         path=[section_name])
                    return node
                
                def transform_value(self, node, new_value, path=None):
                    """
                    Recursively transform an AST node based on new_value.
                    
                    Args:
                        node: The existing AST node
                        new_value: The new value to apply
                        path: List representing the current path in the config hierarchy
                    
                    Returns:
                        Updated AST node
                    """
                    path = path or []
                    current_path = '.'.join(path)
                    
                    # Handle dictionaries recursively
                    if isinstance(node, ast.Dict) and isinstance(new_value, dict):
                        # Process each key-value pair in the dict
                        for j, (key, value) in enumerate(zip(node.keys, node.values)):
                            if isinstance(key, ast.Str) and key.s in new_value:
                                node_path = path + [key.s]
                                node.values[j] = self.transform_value(value, new_value[key.s], node_path)
                        return node
                    
                    # Handle lists recursively
                    elif isinstance(node, ast.List) and isinstance(new_value, list):
                        # If the list has the same length, update each element
                        if len(node.elts) == len(new_value):
                            for j, (elt, new_elt) in enumerate(zip(node.elts, new_value)):
                                node_path = path + [f"[{j}]"]
                                node.elts[j] = self.create_node_for_value(new_elt, node_path)
                        else:
                            # If lengths differ, create a new list
                            return self.create_node_for_value(new_value, path)
                        return node
                    
                    # Handle tuples recursively
                    elif isinstance(node, ast.Tuple) and isinstance(new_value, (list, tuple)):
                        # Convert tuple to the right size
                        if len(node.elts) == len(new_value):
                            for j, (elt, new_elt) in enumerate(zip(node.elts, new_value)):
                                node_path = path + [f"[{j}]"]
                                node.elts[j] = self.create_node_for_value(new_elt, node_path)
                        else:
                            # If lengths differ, create a new tuple
                            return self.create_node_for_value(new_value, path)
                        return node
                    
                    # Handle special case: os.path.join() for TRAFFIC_PATHS
                    elif (isinstance(node, ast.Call) and 
                          current_path.startswith('TRAFFIC_PATHS') and
                          isinstance(node.func, ast.Attribute) and 
                          node.func.attr == 'join' and 
                          hasattr(node.func.value, 'attr') and 
                          node.func.value.attr == 'path'):
                        
                        # For path joins, update the last argument while preserving the structure
                        if isinstance(new_value, str) and len(node.args) > 0:
                            # Split the new path and update the last component
                            path_parts = new_value.split('/')
                            if len(path_parts) > 0:
                                last_part = path_parts[-1]
                                # Keep the original path structure but update the final folder
                                if isinstance(node.args[-1], ast.Str):
                                    node.args[-1] = ast.Str(s=last_part)
                        return node
                    
                    # For all other nodes, create an appropriate AST node based on the new value
                    return self.create_node_for_value(new_value, path)
                
                def create_node_for_value(self, value, path=None):
                    """
                    Create an appropriate AST node for a given value.
                    
                    Args:
                        value: The value to convert to an AST node
                        path: List representing the current path in the config hierarchy
                    
                    Returns:
                        AST node representing the value
                    """
                    path = path or []
                    current_path = '.'.join(path)
                    
                    # Handle different value types
                    if isinstance(value, bool):
                        return ast.NameConstant(value=value)
                    elif isinstance(value, int):
                        return ast.Num(n=value)
                    elif isinstance(value, float):
                        return ast.Num(n=value)
                    elif isinstance(value, str):
                        return ast.Str(s=value)
                    elif isinstance(value, dict):
                        # Create a new dictionary node
                        keys = []
                        values = []
                        for k, v in value.items():
                            keys.append(ast.Str(s=k))
                            node_path = path + [k]
                            values.append(self.create_node_for_value(v, node_path))
                        return ast.Dict(keys=keys, values=values)
                    elif isinstance(value, list):
                        # Create a new list node
                        elts = []
                        for i, item in enumerate(value):
                            node_path = path + [f"[i]"]
                            elts.append(self.create_node_for_value(item, node_path))
                        return ast.List(elts=elts, ctx=ast.Load())
                    elif isinstance(value, tuple):
                        # Create a new tuple node
                        elts = []
                        for i, item in enumerate(value):
                            node_path = path + [f"[i]"]
                            elts.append(self.create_node_for_value(item, node_path))
                        return ast.Tuple(elts=elts, ctx=ast.Load())
                    elif value is None:
                        return ast.NameConstant(value=None)
                    else:
                        # For unsupported types, convert to string
                        return ast.Str(s=str(value))
            
            # Apply our transformer
            new_tree = ConfigTransformer().visit(tree)
            ast.fix_missing_locations(new_tree)
            
            # Convert the modified AST back to code
            new_code = astor.to_source(new_tree)
            
            # Write the modified code back to the file
            with open(config_module_path, 'w') as f:
                f.write(new_code)
            
            # Reload the config module to apply changes
            reload_config()
            logger.info("Configuration file updated successfully")
            return True
        else:
            logger.warning("No changes were made to the configuration")
            return False
            
    except Exception as e:
        logger.error(f"Error updating config file: {e}")
        logger.exception("Detailed traceback:")
        # Try to restore from backup if it exists
        try:
            if os.path.exists(backup_path):
                with open(backup_path, 'r') as f:
                    backup_content = f.read()
                with open(config_module_path, 'w') as f:
                    f.write(backup_content)
                logger.info("Restored config file from backup after error")
        except Exception as restore_error:
            logger.error(f"Failed to restore config from backup: {restore_error}")
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
    scenarios = Config.SCENARIOS
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
        scenarios=scenarios,
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