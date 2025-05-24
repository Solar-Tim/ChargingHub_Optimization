# ChargingHub Optimization

*Disclaimer: The use of this repository is only permitted for non-commercial use*

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Web Interface](#web-interface)
- [Installation](#installation)
- [Required Data](#required-data)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [Contact](#contact)

## Introduction
This repository contains a comprehensive optimization tool developed for planning cost-optimal grid connections for high-power electric truck charging hubs. The application combines traffic analysis, charging demand optimization, and grid infrastructure optimization into a multi-phase process with an intuitive web interface.

## Features
- **Traffic Analysis**: Analyzes truck traffic patterns to determine charging demand at hub locations
- **Charging Hub Setup**: 
  - Matches trucks to appropriate charging types (NCS, HPC, MCS)
  - Determines optimal number of chargers needed
  - Optimizes charging demand using different strategies (T_min, Konstant, Hub)
- **Grid Infrastructure Optimization**:
  - Calculates optimal grid connection sizing
  - Determines cable requirements and distances
  - Evaluates battery storage options
  - Finds the minimum cost solution for grid connections
- **Visualization**:
  - Interactive charts for power load, battery state, cost breakdown
  - Map visualization of charging hubs, power lines, and substations
  - Detailed results comparison

## Web Interface
The application features a complete web interface with:
- Dashboard for monitoring optimization progress
- Configuration page for setting all optimization parameters
- Results page with detailed charts and analysis tools
- Map visualization for geographical context
- Log viewer for debugging and process monitoring

## Installation
To install the necessary dependencies, run:

```bash
pip install -r requirements.txt
```

## Required Data
The optimization process requires several types of input data:

1. **Traffic Data**:
   - Truck traffic volumes by road segment (`Befahrungen_25_1Q.csv`)
   - Highway toll information (`Mauttabelle.csv`)
   - Network graph with nodes and edges (`03_network-nodes.csv`, `04_network-edges.csv`)
   - Regional information (NUTS-3 regions in `02_NUTS-3-Regions.csv`)
   - Geographic boundaries (`DEU.geo.json`)

2. **Charging Demand Data**:
   - Distribution of charging types (NCS, HPC, MCS) by duration (`verteilungsfunktion_mcs-ncs.csv`)
   - Driver break patterns and preferred stopping locations
   - Vehicle energy consumption models

3. **Grid Infrastructure Data**:
   - Power line locations (stored in `data/osm/`)
   - Substation locations and capacities
   - Grid connection costs and constraints

4. **Charging Infrastructure Parameters**:
   - Charger specifications (power output, efficiency)
   - Installation and operational costs
   - Battery storage parameters and costs
   - Land availability and site suitability data


## Usage
### Using the Web Interface
1. Start the web server:
   ```bash
   python -m ui.app
   ```
2. Open your browser and navigate to `http://localhost:5000`
3. Configure parameters in the Configuration page
4. Run the optimization from the Dashboard
5. View and analyze results in the Results and Map pages

### Running from Command Line
For headless operation:
```bash
python main.py
```

## Project Structure
```
ChargingHub_Optimization/
│
├── data/                   # Directory for input data (user must provide required CSV/GeoJSON files)
│   ├── load/               # (optional) Load profiles and metadata
│   ├── osm/                # (optional) Power infrastructure GIS data
│   └── traffic/            # (optional) Traffic analysis data
│
├── logs/                   # Log files from various processes
│
├── results/                # Optimization results
│
├── scripts/                # Core scripts for optimization modules
│   ├── charginghub_setup/  # Charging hub optimization
│   ├── grid_optimization/  # Grid connection optimization
│   ├── traffic_calculation/# Traffic demand and break assignment
│   ├── distance_scripts/   # Distance and routing calculations
│   ├── visuals/            # Visualization generation
│   ├── main.py             # Entry Point for the whole Optimization Pipeline
│   ├── extract_results_to_csv.py # Export results to CSV
│   └── config.py           # Central configuration
│
├── ui/                     # Web interface components
│   ├── static/             # JavaScript, CSS, images
│   ├── templates/          # HTML templates
│   ├── app.py              # Flask web application (main entry point for UI)
│   └── run_ui.py           # Alternative script to start the UI
│
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Hinweise zum Datenordner
Die benötigten Eingabedateien (CSV, GeoJSON) sind aus urheberrechtlichen Gründen nicht im Repository enthalten und müssen vom Nutzer bereitgestellt werden. Die genaue Struktur und Dateinamen sind im Abschnitt "Required Data" beschrieben.

## Hinweise zum Starten des Webservers
Um das Web-UI zu starten, führen Sie folgenden Befehl aus:

```bash
python -m ui.app
```

Das UI ist dann unter http://localhost:5000 erreichbar. Alternativ kann auch `python ui/run_ui.py` verwendet werden.

## Contributing
Contributions to this project are welcome. Please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature-branch`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature-branch`)
5. Create a new Pull Request

## Contact
If you have any questions or would like to get in touch, feel free to contact me at [tim.sanders@rwth-aachen.de].

If you're interested in using this work for commercial purposes, I'm open to discussions.