import math

# Default cable database in SI units:
# Cable size in mm², Resistance in Ω/m, Reactance in Ω/m, and maximum current in A.
default_cable_database = [
    {"Size_mm2": 50,  "Resistance_ohm_per_m": 0.387 / 1000, "Reactance_ohm_per_m": 0.08 / 1000, "Max_Current_A": 145},
    {"Size_mm2": 95,  "Resistance_ohm_per_m": 0.206 / 1000, "Reactance_ohm_per_m": 0.08 / 1000, "Max_Current_A": 230},
    {"Size_mm2": 150, "Resistance_ohm_per_m": 0.132 / 1000, "Reactance_ohm_per_m": 0.08 / 1000, "Max_Current_A": 290},
    {"Size_mm2": 240, "Resistance_ohm_per_m": 0.0817/ 1000, "Reactance_ohm_per_m": 0.08 / 1000, "Max_Current_A": 400},
    {"Size_mm2": 400, "Resistance_ohm_per_m": 0.0493/ 1000, "Reactance_ohm_per_m": 0.08 / 1000, "Max_Current_A": 530}
]

def cable_sizing_iec60287(
    P_W: float,
    U_V: float,
    pf: float = 0.9,
    length_m: float = 1000.0,
    material: str = 'Cu',
    voltage_drop_limit: float = 0.05,
    installation_factor: float = 1.0,
    cable_config: str = 'three_phase',
    cable_db: list = None # type: ignore
) -> dict:
    """
    Calculate the minimum required cable cross-section for AC systems (LV/MV) based on IEC 60287,
    using universal SI units.
    
    Parameters:
    -----------
    P_W : float
        Power demand in Watts.
    U_V : float
        System voltage in Volts.
    pf : float, default=0.9
        Power factor.
    length_m : float, default=1000.0
        Cable length in meters.
    material : str, default='Cu'
        Conductor material ('Cu' for copper, 'Al' for aluminum).
    voltage_drop_limit : float, default=0.05
        Maximum allowable voltage drop as a fraction of the nominal voltage.
    installation_factor : float, default=1.0
        Derating factor for current due to installation conditions.
    cable_config : str, default='three_phase'
        Cable configuration; either 'three_phase' or 'single_phase'.
    cable_db : list, optional
        Custom cable database; if None, a default SI database is used.
        
    Returns:
    --------
    dict
        Dictionary containing:
         - "Calculated Current (A)"
         - "Allowed Voltage Drop (V)"
         - "Required Minimum Cross-Section (mm²) [Voltage Drop Criterion]"
         - "Selected Cable (mm²)"
         - "Calculated Voltage Drop (V)"
         - "Thermal Constraint Satisfied" (bool)
    """
    
    # Use default cable database if not provided
    if cable_db is None:
        cable_db = default_cable_database

    # Calculate line current based on configuration:
    # Three-phase: I = P / (√3 * U * pf)
    # Single-phase: I = P / (U * pf)
    if cable_config == 'three_phase':
        I = P_W / (math.sqrt(3) * U_V * pf)
    elif cable_config == 'single_phase':
        I = P_W / (U_V * pf)
    else:
        raise ValueError("Invalid cable configuration. Choose 'three_phase' or 'single_phase'.")

    # Apply installation derating: effective current that the cable must carry
    I_effective = I / installation_factor

    # Allowed voltage drop in Volts
    allowed_vdrop = voltage_drop_limit * U_V

    # Phase angle (φ) from the power factor
    phi = math.acos(pf)

    # Set material resistivity in Ω·m
    if material.lower() in ['cu', 'copper']:
        resistivity = 1.724e-8  # Ω·m
    elif material.lower() in ['al', 'aluminum', 'alu']:
        resistivity = 2.8e-8    # Ω·m
    else:
        raise ValueError("Unsupported material. Use 'Cu' for copper or 'Al' for aluminum.")

    # Default reactance per meter (Ω/m), converted from 0.08 Ω/km.
    X_per_m = 0.08 / 1000

    # Determine the voltage drop factor based on configuration:
    # For three-phase: factor = √3 * I_effective * L
    # For single-phase:  factor = 2 * I_effective * L
    if cable_config == 'three_phase':
        factor = math.sqrt(3) * I_effective * length_m
    else:
        factor = 2 * I_effective * length_m

    # Voltage drop (ΔV) is given by:
    #   ΔV = factor * [ (ρ * L * 1e6 * cosφ / A_mm2) + (X_per_m * sinφ) ]
    # where A_mm2 is the cross-sectional area in mm² (recall: 1 mm² = 1e-6 m²).
    # To ensure ΔV <= allowed_vdrop, solve for A_mm2:
    #
    #   (ρ * length_m * 1e6 * cosφ) / A_mm2 <= (allowed_vdrop/factor) - (X_per_m * sinφ)
    term = (allowed_vdrop / factor) - (X_per_m * math.sin(phi))
    if term <= 0:
        raise ValueError("Voltage drop limit too strict or system parameters too high; cannot satisfy voltage drop criteria.")

    A_min = (resistivity * length_m * 1e6 * math.cos(phi)) / term

    # Evaluate cable candidates from the database that meet both:
    # 1. Thermal current rating (Max_Current_A >= I_effective)
    # 2. Cross-section at least A_min
    candidates = []
    for cable in cable_db:
        cable_area = cable.get("Size_mm2")
        max_current = cable.get("Max_Current_A")
        if cable_area is None or max_current is None:
            continue
        if max_current >= I_effective and cable_area >= A_min:
            candidates.append(cable)

    # If no cable meets both criteria, relax the cross-section requirement and choose one
    if not candidates:
        for cable in cable_db:
            cable_area = cable.get("Size_mm2")
            max_current = cable.get("Max_Current_A")
            if cable_area is None or max_current is None:
                continue
            if max_current >= I_effective:
                candidates.append(cable)

    if candidates:
        # Choose the cable with the smallest cross-section among candidates
        selected_cable = min(candidates, key=lambda c: c.get("Size_mm2"))
        selected_area = selected_cable.get("Size_mm2")
        # Calculate the actual voltage drop using the cable's resistance and reactance values
        R_cable = selected_cable.get("Resistance_ohm_per_m")
        X_cable = selected_cable.get("Reactance_ohm_per_m")
        if cable_config == 'three_phase':
            actual_vdrop = math.sqrt(3) * I_effective * length_m * (R_cable * math.cos(phi) + X_cable * math.sin(phi))
        else:
            actual_vdrop = 2 * I_effective * length_m * (R_cable * math.cos(phi) + X_cable * math.sin(phi))
        thermal_ok = True
    else:
        selected_cable = None
        selected_area = None
        actual_vdrop = None
        thermal_ok = False

    return {
        "Calculated Current (A)": I_effective,
        "Allowed Voltage Drop (V)": allowed_vdrop,
        "Required Minimum Cross-Section (mm²) [Voltage Drop Criterion]": A_min,
        "Selected Cable (mm²)": selected_area if selected_area is not None else "None",
        "Calculated Voltage Drop (V)": actual_vdrop,
        "Thermal Constraint Satisfied": thermal_ok
    }

# Example usage in SI units:
if __name__ == "__main__":
    # Low-voltage (LV) installation (three-phase)
    result_LV = cable_sizing_iec60287(
        P_W=100e3,    # 100 kW
        U_V=400,      # 400 V
        pf=0.9,
        length_m=50,  # 50 meters
        material='Cu',
        voltage_drop_limit=0.05,
        installation_factor=0.85,
        cable_config='three_phase'
    )
    
    # Medium-voltage (MV) installation (three-phase)
    result_MV = cable_sizing_iec60287(
        P_W=10e6,       # 5 MW
        U_V=20000,     # 20 kV
        pf=0.9,
        length_m=1000, # 1000 meters
        material='Cu',
        voltage_drop_limit=0.05,
        installation_factor=0.9,
        cable_config='three_phase'
    )
    
    print("LV Result:", result_LV)
    print("MV Result:", result_MV)
