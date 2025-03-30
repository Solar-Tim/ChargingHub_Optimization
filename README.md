

# ChargingHub Optimization

*Disclaimer: The use of the repository is only permitted for non-commercial use*

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Introduction
This repository contains the code and models developed for a Bachelor's thesis on the cost-optimal planning of grid connections for high-power electric truck charging hubs. It combines demand estimation, grid infrastructure analysis, and investment cost modeling into a multi-step optimization pipeline.

## Features
- **Demand Estimation**: Predicts the demand for electric truck charging based on various factors.
- **Grid Infrastructure Analysis**: Analyzes the existing grid infrastructure to determine the feasibility and cost of new connections.
- **Investment Cost Modeling**: Models the investment costs associated with different grid connection options.
- **Optimization Pipeline**: Integrates the above components into a pipeline to find the cost-optimal solution.

## Installation
To install the necessary dependencies, run the following command:

```bash
pip install -r requirements.txt
```

## Usage
To run the optimization pipeline, execute the following command:

```bash
python main.py
```

For detailed usage instructions and examples, please refer to the documentation in the `docs` directory.

## Project Structure
```
ChargingHub_Optimization/
│
├── data/                   # Directory for input data
├── models/                 # Directory for models
├── scripts/                # Directory for utility scripts
├── results/                # Directory for output results
├── requirements.txt        # List of dependencies
├── main.py                 # Main script to run the pipeline
├── README.md               # Readme file
└── LICENSE                 # License file
```

## Contributing
I welcome contributions to this project. Please follow these steps to contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## Contact
For any inquiries or questions, please contact me at [tim.sanders@rwth-aachen.de].

---

Feel free to adjust the contact email and any other specific details as needed.
