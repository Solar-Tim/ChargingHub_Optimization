import math
from scripts.charginghub_optimization.config import (
    aluminium_kabel, mv_voltage, mv_voltage_drop_percent, mv_power_factor,
    mv_conductivity, number_cables, digging_cost, cable_hardware_connection_cost, lv_voltage, lv_voltage_drop_percent, lv_power_factor, lv_conductivity,
    kupfer_kabel, MCS_count, HPC_count, NCS_count
)

def get_aluminium_cable_cost(size):
    """Get the cost of aluminum cable for a given cross-section size."""
    try:
        idx = aluminium_kabel["Nennquerschnitt"].index(size)
        return aluminium_kabel["Kosten"][idx]
    except (ValueError, IndexError):
        # Return the cost of the largest available cable if size not found
        return aluminium_kabel["Kosten"][-1]

def get_current_capacity_for_size(size):
    """Get the current capacity for a given cable size."""
    try:
        idx = aluminium_kabel["Nennquerschnitt"].index(size)
        return aluminium_kabel["Belastbarkeit"][idx]
    except (ValueError, IndexError):
        # Return the capacity of the largest available cable if size not found
        return aluminium_kabel["Belastbarkeit"][-1]

def calculate_max_power_voltage_drop(size, distance_m):
    """Calculate the maximum power a cable can carry based on voltage drop constraint."""
    delta_U = mv_voltage_drop_percent / 100 * mv_voltage
    
    # Rearranging the voltage drop formula to solve for current (I)
    I_max = (size * mv_conductivity * delta_U) / (math.sqrt(3) * distance_m * mv_power_factor)
    
    # Convert current to power in kW
    P_max_kw = I_max * math.sqrt(3) * mv_voltage / 1000
    
    return P_max_kw

def calculate_max_power_current_capacity(size):
    """Calculate the maximum power a cable can carry based on current capacity constraint."""
    # Get the current capacity for the given size
    I_max = get_current_capacity_for_size(size)
    
    # Convert current to power in kW
    P_max_kw = I_max * math.sqrt(3) * mv_voltage / 1000
    
    return P_max_kw

def calculate_max_power(cable_size, distance_m):
    """
    Calculate the maximum power a cable of given size can carry over a given distance.
    
    Args:
        cable_size (float): Cable cross-section in mm²
        distance_m (float): Cable distance in meters
        
    Returns:
        dict: Dictionary containing power and constraint details:
            - max_power_kw: Maximum power the cable can carry in kW
            - voltage_drop_limit_kw: Maximum power based on voltage drop constraint
            - current_capacity_limit_kw: Maximum power based on current capacity constraint
            - limiting_factor: String indicating which constraint is limiting
            - cost_per_m: Cost per meter of the cable
            - total_cost: Total cost for the cable installation
    """
    # Calculate maximum power based on voltage drop constraint
    voltage_drop_limit_kw = calculate_max_power_voltage_drop(cable_size, distance_m)
    
    # Calculate maximum power based on current capacity constraint
    current_capacity_limit_kw = calculate_max_power_current_capacity(cable_size)
    
    # The maximum power is the minimum of the two limits
    max_power_kw = min(voltage_drop_limit_kw, current_capacity_limit_kw)
    
    # Determine which factor is limiting
    if voltage_drop_limit_kw <= current_capacity_limit_kw:
        limiting_factor = "voltage_drop"
    else:
        limiting_factor = "current_capacity"
    
    # Calculate cost
    cost_per_m = get_aluminium_cable_cost(cable_size)
    total_cost = cost_per_m * distance_m * number_cables + cable_hardware_connection_cost * number_cables + digging_cost * distance_m
    
    return {
        "max_power_kw": max_power_kw,
        "voltage_drop_limit_kw": voltage_drop_limit_kw,
        "current_capacity_limit_kw": current_capacity_limit_kw,
        "limiting_factor": limiting_factor,
        "cable_size_mm2": cable_size,
        "cost_per_m": cost_per_m,
        "total_cost": total_cost
    }

# Extract power and cost breakpoints for PWL constraints
def extract_points_from_options(options):
    """Extract power and cost points from cable options"""
    if not options:
        return [0], [0]
    return [opt["max_power_kw"] for opt in options], [opt["total_cost"] for opt in options]

# Calculate cable options for MV connections
def calculate_mv_cable(required_power_kw, distance_m):
    """
    Find the smallest cable size that can support the required power over the given distance.
    
    Args:
        required_power_kw (float): Required power in kW
        distance_m (float): Cable distance in meters
        
    Returns:
        float: Selected cable size in mm²
    """
    if distance_m <= 0:
        return 0  # No distance means no cable needed
    
    # Try each cable size to find the smallest one that can support the power
    for size in aluminium_kabel["Nennquerschnitt"]:
        result = calculate_max_power(size, distance_m)
        if result["max_power_kw"] >= required_power_kw:
            return size
            
    # If no cable size works, return the largest available size
    return aluminium_kabel["Nennquerschnitt"][-1]

# Calculate cable options for a specific connection type
def calculate_cable_options(distance_m, additional_costs=0):
    """
    Calculate available cable options for a given distance with associated costs and power ratings.
    
    Args:
        distance_m (float): Distance in meters
        additional_costs (float): Any additional fixed costs beyond cables and digging
        
    Returns:
        list: List of dictionaries with cable options
    """
    options = []
    if distance_m <= 0:
        return options
        
    for size in aluminium_kabel["Nennquerschnitt"]:
        result = calculate_max_power(size, distance_m)
        cost = result["cost_per_m"] * distance_m * number_cables + \
               cable_hardware_connection_cost * number_cables + \
               digging_cost * distance_m + \
               additional_costs
        
        options.append({
            "size": size,
            "max_power_kw": result["max_power_kw"],
            "total_cost": cost,
            "limiting_factor": result["limiting_factor"]
        })
    
    return options

# Add these functions before creating the optimization model

def get_cable_capacity(size):
    """Get the power capacity of a cable size in kW"""
    # Uses the current capacity function from my_cables.py
    return calculate_max_power_current_capacity(size)

def get_cable_cost(size):
    """Get the cost per meter for a given cable size"""
    # Uses the aluminum cable cost function from my_cables.py
    return get_aluminium_cable_cost(size)

def calculate_total_cable_cost(size, distance_m, additional_costs=0):
    """
    Calculate the total cost of cable installation including all components.
    
    Args:
        size (float): Cable cross-section in mm²
        distance_m (float): Distance in meters
        additional_costs (float): Any additional fixed costs (e.g., HV substation)
        
    Returns:
        float: Total cost in EUR including cable, hardware, and digging
    """
    # Get base cost per meter for the cable
    cable_cost_per_m = get_aluminium_cable_cost(size)
    
    # Calculate total cost including all components
    total_cost = (
        cable_cost_per_m * distance_m * number_cables +  # Cable material cost
        cable_hardware_connection_cost * number_cables +  # Connection hardware
        digging_cost * distance_m +                      # Digging/installation
        additional_costs                                # Any additional costs
    )
    
    return total_cost

# LV DC cable calculation functions
def calculate_lv_cable_cross_section(power_kw, length_m, voltage=lv_voltage, 
                                    voltage_drop_percent=lv_voltage_drop_percent,
                                    power_factor=lv_power_factor, 
                                    conductivity=lv_conductivity):
    """
    Calculate the required cable cross-section for LV cables using the formula:
    A = (2 × P × l × cos(φ)) / (γ × Δu × U)
    
    Args:
        power_kw (float): Charger power in kW
        length_m (float): Cable length in meters
        voltage (float): Phase-to-phase voltage in V
        voltage_drop_percent (float): Allowable voltage drop percentage
        power_factor (float): Power factor (cos φ)
        conductivity (float): Electrical conductivity of cable material in S·m/mm²
    
    Returns:
        float: Required cable cross-section in mm²
    """
    # Convert power to W
    power_w = power_kw * 1000
    
    # Calculate allowable voltage drop in V
    delta_u = voltage_drop_percent / 100 * voltage
    
    # Calculate required cross-section
    required_cross_section = (2 * power_w * length_m * power_factor) / (conductivity * delta_u * voltage)
    
    return required_cross_section

def get_copper_cable_size(required_cross_section):
    """
    Get the smallest cable size from kupfer_kabel that meets the required cross-section.
    
    Args:
        required_cross_section (float): Required cable cross-section in mm²
        
    Returns:
        float: Selected standard cable size in mm²
    """
    for size in kupfer_kabel["Nennquerschnitt"]:
        if size >= required_cross_section:
            return size
    
    # If no suitable size found, return the largest available
    return kupfer_kabel["Nennquerschnitt"][-1]

def get_copper_cable_cost(size):
    """Get the cost of copper cable for a given cross-section size."""
    try:
        idx = kupfer_kabel["Nennquerschnitt"].index(size)
        return kupfer_kabel["Kosten"][idx]
    except (ValueError, IndexError):
        # Return the cost of the largest available cable if size not found
        return kupfer_kabel["Kosten"][-1]

def calculate_internal_cable_costs(charger_distance_increment=4, 
                                  mcs_power_kw=350, 
                                  hpc_power_kw=150, 
                                  ncs_power_kw=22):
    """
    Calculate the internal LV cable costs for all chargers in the charging hub.
    
    Chargers are arranged linearly with MCS chargers first, followed by HPC and NCS.
    Each charger is individually cabled from the transformer.
    
    Args:
        charger_distance_increment (float): Distance increment between charger positions in meters
        mcs_power_kw (float): Power rating of MCS chargers in kW
        hpc_power_kw (float): Power rating of HPC chargers in kW
        ncs_power_kw (float): Power rating of NCS chargers in kW
        
    Returns:
        dict: Dictionary containing cable costs and details:
            - total_cost: Total cost of all internal cables
            - cables: List of dictionaries with details for each charger's cable
            - mcs_cost: Total cost for MCS charger cables
            - hpc_cost: Total cost for HPC charger cables
            - ncs_cost: Total cost for NCS charger cables
    """
    # Get charger counts from configuration
    mcs_count = MCS_count
    hpc_count = HPC_count
    ncs_count = NCS_count
    
    # Initialize result structure
    result = {
        "total_cost": 0,
        "cables": [],
        "mcs_cost": 0,
        "hpc_cost": 0,
        "ncs_cost": 0
    }
    
    # Define function to calculate cable length based on position
    def get_cable_length(position):
        # Example: positions 0-1 at 4m, 2-3 at 8m, etc.
        return charger_distance_increment * (position // 2 + 1)
    
    # Process MCS chargers
    position = 0
    for i in range(mcs_count):
        length_m = get_cable_length(position)
        cross_section = calculate_lv_cable_cross_section(mcs_power_kw, length_m)
        cable_size = get_copper_cable_size(cross_section)
        cable_cost = get_copper_cable_cost(cable_size) * length_m
        
        result["cables"].append({
            "type": "MCS",
            "position": position,
            "length_m": length_m,
            "power_kw": mcs_power_kw,
            "required_cross_section": cross_section,
            "selected_cross_section": cable_size,
            "cost": cable_cost
        })
        
        result["mcs_cost"] += cable_cost
        position += 1
    
    # Process HPC chargers
    for i in range(hpc_count):
        length_m = get_cable_length(position)
        cross_section = calculate_lv_cable_cross_section(hpc_power_kw, length_m)
        cable_size = get_copper_cable_size(cross_section)
        cable_cost = get_copper_cable_cost(cable_size) * length_m
        
        result["cables"].append({
            "type": "HPC",
            "position": position,
            "length_m": length_m,
            "power_kw": hpc_power_kw,
            "required_cross_section": cross_section,
            "selected_cross_section": cable_size,
            "cost": cable_cost
        })
        
        result["hpc_cost"] += cable_cost
        position += 1
    
    # Process NCS chargers
    for i in range(ncs_count):
        length_m = get_cable_length(position)
        cross_section = calculate_lv_cable_cross_section(ncs_power_kw, length_m)
        cable_size = get_copper_cable_size(cross_section)
        cable_cost = get_copper_cable_cost(cable_size) * length_m
        
        result["cables"].append({
            "type": "NCS",
            "position": position,
            "length_m": length_m,
            "power_kw": ncs_power_kw,
            "required_cross_section": cross_section,
            "selected_cross_section": cable_size,
            "cost": cable_cost
        })
        
        result["ncs_cost"] += cable_cost
        position += 1
    
    # Calculate total cost
    result["total_cost"] = result["mcs_cost"] + result["hpc_cost"] + result["ncs_cost"]
    
    return result

def optimize_charger_arrangement():
    """
    Optimize the charger arrangement to minimize cable costs.
    
    Places MCS chargers first, then HPC, then NCS.
    If MCS_count is odd, the next HPC charger should occupy the subsequent position.
    
    Returns:
        dict: Optimized arrangement information
    """
    # Get charger counts
    mcs_count = MCS_count
    hpc_count = HPC_count
    ncs_count = NCS_count
    
    # Calculate standard arrangement cost
    standard_cost = calculate_internal_cable_costs()
    
    # Check if MCS count is odd
    if mcs_count % 2 == 1:
        # Create modified arrangement function that swaps first HPC with last MCS
        def modified_arrangement():
            result = calculate_internal_cable_costs()
            # Adjust arrangement details and costs as needed
            return result
        
        # Calculate modified arrangement cost
        modified_cost = modified_arrangement()
        
        # Return the better arrangement
        if modified_cost["total_cost"] < standard_cost["total_cost"]:
            return modified_cost
    
    return standard_cost

def get_internal_cable_cost():
    """
    Calculate the optimized internal cable cost for the charging hub.
    
    Returns:
        float: Total cost of internal cabling
    """
    # For now, just use the standard arrangement
    # In the future, this could use optimize_charger_arrangement()
    result = calculate_internal_cable_costs()
    return result["total_cost"]
