import pandas as pd
import numpy as np
import gurobipy as gp
from gurobipy import GRB
import logging
from pathlib import Path
import warnings
import json
import multiprocessing
from functools import partial

warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=log_dir / 'charging_hub_config.log',
    level=logging.DEBUG,
    format='%(asctime)s; %(levelname)s; %(message)s'
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# HARDCODED CONFIGURATION VALUES
# -----------------------------------------------------------------------------
CHARGING_QUOTAS = {
    'NCS': 0.8,
    'HPC': 0.8,
    'MCS': 0.8,
}
CHARGING_TIMES = {
    'Schnell': 45,
    'Nacht': 540,
}
SCENARIO_NAME = "Base"

# -----------------------------------------------------------------------------
# DATA IMPORT
# -----------------------------------------------------------------------------

def datenimport() -> pd.DataFrame:
    """Load incoming‑truck JSON produced by the upstream demand model."""
    project_root = Path(__file__).parent.parent.parent.resolve()
    src = project_root / "data" / "load" / "truckdata" / "eingehende_lkws_ladesaeule.json"

    logger.info("Loading truck data from %s", src)
    if not src.exists():
        raise FileNotFoundError(
            f"Truck data file not found at {src}. "
            "Ensure 'eingehende_lkws_ladesaeule.json' exists under data/load/truckdata."
        )

    with open(src, "r", encoding="utf-8") as f:
        df = pd.DataFrame(json.load(f).get("trucks", []))

    # unify column names
    mapper = {
        "id": "Nummer",
        "arrival_day": "Wochentag",
        "arrival_time_minutes": "Ankunftszeit",
        "pause_type": "Pausentyp",
        "pause_duration_minutes": "Pausenlaenge",
        "assigned_charger": "Ladesäule",
        "capacity_kwh": "capacity_kwh",
        "max_power_kw": "max_power_kw",
        "initial_soc": "initial_soc",
        "target_soc": "target_soc",
        "truck_type_id": "truck_type_id",
    }
    df.rename(columns={k: mapper[k] for k in df.columns if k in mapper}, inplace=True)

    # make sure all columns exist
    for dest in mapper.values():
        if dest not in df.columns:
            df[dest] = pd.NA

    df.dropna(subset=["Nummer", "Ankunftszeit", "Ladesäule"], inplace=True)
    logger.info("Loaded %d trucks", len(df))
    return df

# -----------------------------------------------------------------------------
# MILP (MIN‑S, THEN MAX THROUGHPUT)
# -----------------------------------------------------------------------------

def solve_milp_with_gurobi(df: pd.DataFrame, quota: float = 0.8):
    if df.empty:
        return 0, []

    df_local = df.copy()
    df_local["EffectiveArrival"] = df_local["Ankunftszeit"] + (df_local["Wochentag"] - 1) * 1440
    df_local["EffectiveDeparture"] = df_local["EffectiveArrival"] + df_local["Pausenlaenge"] + 5

    start, end = df_local["EffectiveArrival"].min(), df_local["EffectiveDeparture"].max()
    slots = list(range(int(start), int(end) + 5, 5))

    coverage = {
        i: [t for t in slots if row.EffectiveArrival <= t < row.EffectiveDeparture]
        for i, row in df_local.reset_index(drop=True).iterrows()
    }
    N = len(df_local)

    m = gp.Model("MinStations_MaxThroughput")
    m.setParam("OutputFlag", 0)

    x = m.addVars(N, vtype=GRB.BINARY, name="x")
    S = m.addVar(vtype=GRB.INTEGER, lb=1, name="S")

    # hierarchical objectives - fixing the sense parameter issue
    # The correct syntax might vary by Gurobi version, but this should be compatible with most versions
    m.setObjectiveN(S, 0, priority=2, name="min_stations")
    m.modelSense = GRB.MINIMIZE

    # For the second objective (maximize throughput), we use negative since model is minimizing
    m.setObjectiveN(-gp.quicksum(x[i] for i in range(N)), 1, priority=1, name="max_throughput")

    # quota
    m.addConstr(gp.quicksum(x[i] for i in range(N)) >= quota * N, name="quota")

    # capacity
    for t in slots:
        m.addConstr(gp.quicksum(x[i] for i in range(N) if t in coverage[i]) <= S, name=f"cap_{t}")

    try:
        m.optimize()
    except gp.GurobiError as e:
        logger.error("Gurobi optimisation failed: %s", e)
        raise

    return int(S.X + 0.5), [int(x[i].X + 0.5) for i in range(N)]

# -----------------------------------------------------------------------------
# PER‑CHARGER‑TYPE PIPELINE
# -----------------------------------------------------------------------------

def process_charging_type(ladetyp: str, quotas: dict, df_all: pd.DataFrame):
    quota_target = quotas[ladetyp]
    df_type = df_all[df_all["Ladesäule"] == ladetyp].copy()
    total = len(df_type)

    if total == 0:
        logger.warning("No trucks for charger type %s", ladetyp)
        return {
            "ladetyp": ladetyp,
            "anzahl_ladesaeulen": 0,
            "ladequote": 0.0,
            "df_with_status": None,
            "df_konf_optionen": [],
        }

    stations, accepted = solve_milp_with_gurobi(df_type, quota_target)
    served = sum(accepted)
    quota_real = served / total if total else 0
    per_station = served / stations / 7 if stations else 0

    df_type.reset_index(drop=True, inplace=True)
    df_type["LoadStatus"] = accepted

    logger.info("[%s] stations=%d, served=%d/%d, quota=%.3f", ladetyp, stations, served, total, quota_real)

    return {
        "ladetyp": ladetyp,
        "anzahl_ladesaeulen": stations,
        "ladequote": quota_real,
        "df_with_status": df_type,
        "df_konf_optionen": [
            {
                "Ladetype": ladetyp,
                "Anzahl_Ladesaeulen": stations,
                "Ladequote": quota_real,
                "LKW_pro_Ladesaeule": per_station,
            }
        ],
    }

# -----------------------------------------------------------------------------
# PARALLEL WRAPPER
# -----------------------------------------------------------------------------

def parallel_charging_types_processing(df_trucks: pd.DataFrame):
    pool = multiprocessing.Pool(processes=3)
    func = partial(process_charging_type, quotas=CHARGING_QUOTAS, df_all=df_trucks)
    results = pool.map(func, CHARGING_QUOTAS.keys())
    pool.close(); pool.join()
    return results

# -----------------------------------------------------------------------------
# HUB CONFIGURATION
# -----------------------------------------------------------------------------

def konfiguration_ladehub(df_trucks: pd.DataFrame):
    # adjust pause lengths
    df_trucks.loc[df_trucks["Pausentyp"] == "Nachtlader", "Pausenlaenge"] = CHARGING_TIMES["Nacht"]
    df_trucks.loc[df_trucks["Pausentyp"] == "Schnelllader", "Pausenlaenge"] = CHARGING_TIMES["Schnell"]

    results = parallel_charging_types_processing(df_trucks)

    df_counts = pd.DataFrame(columns=["NCS", "Ladequote_NCS", "HPC", "Ladequote_HPC", "MCS", "Ladequote_MCS"])
    df_status = pd.DataFrame()
    df_opts = pd.DataFrame(columns=["Ladetype", "Anzahl_Ladesaeulen", "Ladequote", "LKW_pro_Ladesaeule"])

    for res in results:
        lt = res["ladetyp"]
        df_counts.loc[0, lt] = res["anzahl_ladesaeulen"]
        df_counts.loc[0, f"Ladequote_{lt}"] = res["ladequote"]
        if res["df_with_status"] is not None:
            df_status = pd.concat([df_status, res["df_with_status"]])
        for opt in res["df_konf_optionen"]:
            df_opts.loc[len(df_opts)] = [
                opt["Ladetype"],
                opt["Anzahl_Ladesaeulen"],
                opt["Ladequote"],
                opt["LKW_pro_Ladesaeule"],
            ]

    out_dir = Path(__file__).parent.parent.parent / "data" / "load" / "truckdata"
    out_dir.mkdir(parents=True, exist_ok=True)
    export_results_as_json(df_counts, df_status, df_opts, out_dir / f"charging_config_{SCENARIO_NAME.lower()}.json")
    return df_counts

# -----------------------------------------------------------------------------
# JSON EXPORT (BACKWARD‑COMPATIBLE)
# -----------------------------------------------------------------------------

def export_results_as_json(df_counts: pd.DataFrame, df_status: pd.DataFrame, df_opts: pd.DataFrame, dest: Path):
    from datetime import datetime

    result = {
        "metadata": {
            "scenario": SCENARIO_NAME,
            "charging_quotas": CHARGING_QUOTAS,
            "charging_times": CHARGING_TIMES,
            "timestamp": datetime.now().isoformat(),  # local time to match legacy files
            "description": "Charging hub configuration results",
        },
        "charging_stations": {},
        "configuration_options": [],
        "trucks": [],
    }

    # ------------------------------------------------------------------
    # charging_stations block (same keys as legacy)
    # ------------------------------------------------------------------
    for lt in ["NCS", "HPC", "MCS"]:
        if lt in df_counts.columns:
            result["charging_stations"][lt] = {
                "count": int(df_counts[lt].iloc[0]),
                "quota": float(df_counts[f"Ladequote_{lt}"].iloc[0]),
            }

    # ------------------------------------------------------------------
    # configuration_options block (English keys expected by legacy dashboards)
    # ------------------------------------------------------------------
    for _, row in df_opts.iterrows():
        result["configuration_options"].append({
            "charging_type": row["Ladetype"],
            "stations": int(row["Anzahl_Ladesaeulen"]),
            "quota": float(row["Ladequote"]),
            "trucks_per_station": float(row["LKW_pro_Ladesaeule"]),
        })

    # ------------------------------------------------------------------
    # trucks list with battery defaults if missing (unchanged from legacy)
    # ------------------------------------------------------------------
    battery_defaults = {
        "NCS": {"capacity_kwh": 600, "max_power_kw": 300, "initial_soc": 0.2, "target_soc": 0.8},
        "HPC": {"capacity_kwh": 400, "max_power_kw": 350, "initial_soc": 0.3, "target_soc": 0.8},
        "MCS": {"capacity_kwh": 500, "max_power_kw": 400, "initial_soc": 0.2, "target_soc": 0.8},
    }

    for _, row in df_status.iterrows():
        lt = row["Ladesäule"]
        defaults = battery_defaults.get(lt, battery_defaults["MCS"])
        truck = {
            "id": row["Nummer"],
            "arrival_day": int(row["Wochentag"]),
            "arrival_time_minutes": int(row["Ankunftszeit"]),
            "pause_type": row["Pausentyp"],
            "pause_duration_minutes": int(row["Pausenlaenge"]),
            "assigned_charger": lt,
            "load_status": int(row["LoadStatus"]),
            "capacity_kwh": float(row.get("capacity_kwh", defaults["capacity_kwh"])),
            "max_power_kw": float(row.get("max_power_kw", defaults["max_power_kw"])),
            "initial_soc": float(row.get("initial_soc", defaults["initial_soc"])),
            "target_soc": float(row.get("target_soc", defaults["target_soc"])),
        }
        if pd.notna(row.get("truck_type_id")):
            truck["truck_type_id"] = int(row["truck_type_id"])
        result["trucks"].append(truck)

    # ------------------------------------------------------------------
    # write file --------------------------------------------------------
    # ------------------------------------------------------------------
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info("Configuration results exported to JSON: %s", dest)

# -----------------------------------------------------------------------------
# MAIN ENTRY
# -----------------------------------------------------------------------------

def main():
    print("Starting charging hub configuration")
    logger.info("Starting charging hub configuration")
    df_trucks = datenimport()
    konfiguration_ladehub(df_trucks)
    print("Charging hub configuration completed successfully")
    logger.info("Charging hub configuration completed successfully")

if __name__ == "__main__":
    main()
