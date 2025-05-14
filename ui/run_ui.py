"""
ChargingHub Optimization - UI Launcher

This script launches the UI for the ChargingHub Optimization project.
It's a simple wrapper around the Flask app that sets up any necessary
environment variables and configuration before starting the server.
"""

import os
import sys
import webbrowser
import threading
import time
from pathlib import Path

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Add scripts directory to path to find config.py
scripts_dir = os.path.join(parent_dir, 'scripts')
sys.path.append(scripts_dir)

# Import app and configs
from app import app, socketio

def open_browser():
    """
    Wait a bit and then open the browser to the UI URL
    """
    time.sleep(1.0)
    webbrowser.open_new('http://localhost:5000/')

if __name__ == '__main__':
    # Change working directory to project root to ensure proper paths for running scripts
    os.chdir(parent_dir)
    print(f"Changed working directory to: {os.getcwd()}")
    
    # Create any necessary directories
    for directory in ['logs', 'data/load', 'results/maps']:
        path = Path(parent_dir) / directory
        if not path.exists():
            print(f"Creating directory: {path}")
            path.mkdir(parents=True, exist_ok=True)
    
    # Start browser in a new thread
    threading.Thread(target=open_browser).start()
    
    # Set default config for development
    app.config['DEBUG'] = True
    
    # Start Flask app with Socket.IO
    print("Starting ChargingHub Optimization UI at http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=True)

