from gurobipy import Model, GRB, quicksum
import pandas as pd
import time
import os
import config
import logging
import argparse

logging.basicConfig(filename='logs.log', level=logging.DEBUG, format='%(asctime)s; %(levelname)s; %(message)s')

CONFIG = {
    'STRATEGIES': ["Konstant"],
    # 'STRATEGIES': ["T_min", "Konstant"]
    # T_min: Minimierung der Ladezeit - Kein Lademanagement
    # Konstant: Möglichst konstante Ladeleistung - Minimierung der Netzanschlusslast - Lademanagement
}

def modellierung(szenario, target_week=1):
    """
    Optimiert den Ladehub für eine spezifische Woche.
    
    Args:
        szenario: Szenario-String zur Bestimmung der Konfiguration
        target_week: Welche Woche optimiert werden soll (Standard: 1)
    """
    print(f"Optimiere Woche {target_week} für Szenario {szenario}")
    
    base_case = 'cl_2_quote_80-80-80_netz_100_pow_100-100-100_pause_45-540_M_1_Base'
    
    dict_base = {
        'ladequote': '80-80-80', # Ladequote in Prozent für NCS, HPC und MCS
        'cluster': '2',
        'pause': '45-540' # Pausenzeiten in Minuten
    }
    
    dict_szenario = {
        'ladequote': szenario.split('_')[3],
        'cluster': szenario.split('_')[1],
        'pause': szenario.split('_')[9]
    }
    
    # Get script directory and root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir))
    
    print(f"Script directory: {script_dir}")
    print(f"Root directory: {root_dir}")
    
    # First try to find files in expected locations
    if (dict_szenario['ladequote'] == dict_base['ladequote'] and 
        dict_szenario['cluster'] == dict_base['cluster'] and 
        dict_szenario['pause'] == dict_base['pause']):
        lkw_filename = f'eingehende_lkws_loadstatus_{base_case}.csv'
        ladehub_filename = f'anzahl_ladesaeulen_{base_case}.csv'
    else:
        lkw_filename = f'eingehende_lkws_loadstatus_{szenario}.csv'
        ladehub_filename = f'anzahl_ladesaeulen_{szenario}.csv'
    
    # Try different possible paths for LKW data
    lkw_path_options = [
        os.path.join(script_dir, 'data', 'epex', 'lkws', lkw_filename),
        os.path.join(root_dir, 'results', 'lkws', lkw_filename),
        os.path.join(root_dir, 'results', 'lkws', f'eingehende_lkws_loadstatus_cluster_{dict_szenario["cluster"]}_quota_{dict_szenario["ladequote"]}_pause_{dict_szenario["pause"]}_Base.csv')
    ]
    
    lkw_filepath = None
    for path_option in lkw_path_options:
        print(f"Checking path: {path_option}")
        if os.path.exists(path_option):
            lkw_filepath = path_option
            print(f"Found LKW file: {lkw_filepath}")
            break
    
    if not lkw_filepath:
        print("ERROR: Could not find LKW data file in any expected location")
        return None
    
    # Try different possible paths for Ladehub data
    ladehub_path_options = [
        os.path.join(script_dir, 'data', 'flex', 'konfiguration_ladehub', ladehub_filename),
        os.path.join(root_dir, 'results', 'konfiguration_ladehub', ladehub_filename)
    ]
    
    ladehub_filepath = None
    for path_option in ladehub_path_options:
        print(f"Checking path: {path_option}")
        if os.path.exists(path_option):
            ladehub_filepath = path_option
            print(f"Found Ladehub file: {ladehub_filepath}")
            break
    
    if not ladehub_filepath:
        print("WARNING: Could not find Ladehub configuration file. Using default values.")
        # Create a default dataframe for ladehub
        df_ladehub = pd.DataFrame({
            'NCS': [4],
            'HPC': [2],
            'MCS': [1]
        })
    else:
        try:
            print(f"Loading Ladehub config from: {ladehub_filepath}")
            df_ladehub = pd.read_csv(ladehub_filepath, sep=';', decimal=',')
            print(f"Successfully loaded Ladehub data. Columns: {df_ladehub.columns.tolist()}")
        except Exception as e:
            print(f"ERROR loading Ladehub data: {e}")
            print("Using default values instead.")
            df_ladehub = pd.DataFrame({
                'NCS': [4],
                'HPC': [2],
                'MCS': [1]
            })
    
    # Load LKW data and check columns
    try:
        print(f"Loading LKW data from: {lkw_filepath}")
        df_lkw = pd.read_csv(lkw_filepath, sep=';', decimal=',')
        print(f"Successfully loaded LKW data. Shape: {df_lkw.shape}")
        print(f"Columns: {df_lkw.columns.tolist()}")
        
        # Map column names if necessary based on the actual columns in the file
        column_mapping = {
            'Nummer': 'Nummer',
            'Ankunft': 'Ankunftszeit_total',
            'Ankunftszeit_total': 'Ankunftszeit_total',
            'Tag': 'Tag',
            'KW': 'KW',
            'Woche': 'KW',
            'Ladetyp': 'Ladesäule',
            'Pausenlaenge': 'Pausenlaenge',
            'Kapazitaet': 'Kapazitaet',
            'SOC': 'SOC',
            'SOC_Target': 'SOC_Target',
            'Max_Leistung': 'Max_Leistung',
            'LoadStatus': 'LoadStatus'
        }
        
        # Check if columns exist or need to be renamed/created
        if 'Ankunftszeit_total' not in df_lkw.columns and 'Ankunft' in df_lkw.columns:
            df_lkw['Ankunftszeit_total'] = df_lkw['Ankunft']
        
        if 'KW' not in df_lkw.columns:
            if 'Datum' in df_lkw.columns:
                # Create KW from Datum if available
                df_lkw['KW'] = pd.to_datetime(df_lkw['Datum']).dt.isocalendar().week
            else:
                # Assume all data is for the target week
                df_lkw['KW'] = target_week
        
        if 'Ladesäule' not in df_lkw.columns and 'Ladetyp' in df_lkw.columns:
            df_lkw['Ladesäule'] = df_lkw['Ladetyp']
        
        if 'LoadStatus' not in df_lkw.columns:
            # If LoadStatus is missing, try to derive it from other columns or set a default
            if 'LoadStatus' in df_lkw.columns:
                df_lkw['LoadStatus'] = df_lkw['LoadStatus']
            else:
                print("WARNING: LoadStatus column not found. Assuming all entries are valid (LoadStatus=1).")
                df_lkw['LoadStatus'] = 1
        
        # Add missing columns with default values if necessary
        required_cols = ['KW', 'LoadStatus', 'Ankunftszeit_total', 'Pausenlaenge', 
                         'Ladesäule', 'SOC', 'Kapazitaet', 'Max_Leistung', 'SOC_Target']
        for col in required_cols:
            if col not in df_lkw.columns:
                print(f"WARNING: Required column {col} not found in data.")
                return None
        
    except Exception as e:
        print(f"ERROR loading LKW data: {e}")
        return None
    
    # Maximale Leistung pro Ladesäulen-Typ
    ladeleistung = {
        'NCS': int(int(szenario.split('_')[7].split('-')[0]) / 100 * config.leistung_ladetyp['NCS']),
        'HPC': int(int(szenario.split('_')[7].split('-')[1]) / 100 * config.leistung_ladetyp['HPC']),
        'MCS': int(int(szenario.split('_')[7].split('-')[2]) / 100 * config.leistung_ladetyp['MCS'])
    }

    # Anzahl Ladesäulen
    max_saeulen = {
        'NCS': int(df_ladehub['NCS'][0]),
        'HPC': int(df_ladehub['HPC'][0]),
        'MCS': int(df_ladehub['MCS'][0])
    }

    netzanschlussfaktor = float(int(szenario.split('_')[5]) / 100)
    netzanschluss = (
        max_saeulen['NCS'] * ladeleistung['NCS'] +
        max_saeulen['HPC'] * ladeleistung['HPC'] +
        max_saeulen['MCS'] * ladeleistung['MCS']
    ) * netzanschlussfaktor

    
    # -------------------------------------
    # Vorbereitung: Lastgang-Arrays
    # -------------------------------------
    WEEK_MINUTES = 10080  # 7 days * 24 hours * 60 minutes
    TIMESTEP = 5
    N = WEEK_MINUTES // TIMESTEP  # 10080 / 5 = 2016 timesteps for one week
    
    # -------------------------------------
    # Eine Woche = 7 Tage = 2016 Zeitstufen (7*24*60/5)
    # -------------------------------------
    T_7 = 288 * 7  # Timesteps in a week (288 per day * 7 days)
    
    Delta_t = TIMESTEP / 60.0

    # Start date for this specific week
    start_date = pd.Timestamp('2024-01-01 00:00:00') + pd.Timedelta(days=7*(target_week-1))

    # Vorbefüllen der Liste mit allen Zeitpunkten und Strategien - nur für eine Woche
    rows = []
    for strategie in CONFIG['STRATEGIES']:
        for i in range(N):
            rows.append({
                'Datum':                start_date + pd.Timedelta(minutes=i * TIMESTEP),
                'Woche':                target_week,
                'Tag':                  1 + (i // 288) % 7,
                'Zeit':                 (i * TIMESTEP) % 1440,
                'Leistung_Total':       0.0,
                'Leistung_Max_Total':   0.0,
                'Leistung_NCS':         0.0,
                'Leistung_HPC':         0.0,
                'Leistung_MCS':         0.0,
                'Ladestrategie':        strategie,
                'Netzanschluss':        netzanschluss,
                'Ladequote':            0.0,
            })

    # Index-Map für schnellen Zugriff erstellen
    row_index = {(strategie, i): idx for idx, (strategie, i) in enumerate([(r['Ladestrategie'], i) 
                                             for i, r in enumerate(rows)])}

    dict_lkw_lastgang = {
        'LKW_ID': [],
        'Datum': [],
        'Woche': [],
        'Tag': [],
        'Zeit': [],
        'Ladetyp': [],
        'Ladestrategie': [],
        'Ladezeit': [],
        'Leistung': [],
        'SOC': [],
        'Max_Leistung': [],
        'Pplus': [],
        'Pminus': [],
        'z': []
    }

    # Filtern der LKWs nur für die gewählte Woche
    df_lkw_filtered = df_lkw[
        (df_lkw['KW'] == target_week) &
        (df_lkw['LoadStatus'] == 1)
    ].copy() 
            
    if df_lkw_filtered.empty:
        print(f"Keine LKWs in Woche {target_week} gefunden!")
        return None

    # Ankunfts- und Abfahrtszeiten in 5-Minuten-Index - OHNE Wochenoffset
    df_lkw_filtered['t_a'] = (df_lkw_filtered['Ankunftszeit_total'] // TIMESTEP).astype(int) % T_7
    df_lkw_filtered['t_d'] = ((df_lkw_filtered['Ankunftszeit_total'] 
                               + df_lkw_filtered['Pausenlaenge'] 
                               - TIMESTEP) // TIMESTEP).astype(int) % T_7
    
    if df_lkw_filtered.empty:
        return None

    t_in     = df_lkw_filtered['t_a'].tolist()        
    t_out    = df_lkw_filtered['t_d'].tolist()
    l        = df_lkw_filtered['Ladesäule'].tolist()
    SOC_A    = df_lkw_filtered['SOC'].tolist()
    kapaz    = df_lkw_filtered['Kapazitaet'].tolist()
    maxLKW   = df_lkw_filtered['Max_Leistung'].tolist()
    SOC_req  = df_lkw_filtered['SOC_Target'].tolist()

    # Leistungsskalierung
    pow_split = szenario.split('_')[6].split('-')
    if len(pow_split) > 1:
        lkw_leistung_skalierung = float(pow_split[1]) / 100
    else:
        lkw_leistung_skalierung = 1.0

    max_lkw_leistung = [m * lkw_leistung_skalierung for m in maxLKW]
    E_req = [kapaz[i] * (SOC_req[i] - SOC_A[i]) for i in range(len(df_lkw_filtered))]
    I = len(df_lkw_filtered)

    # -------------------------------------
    # Strategien p_max / p_min
    # -------------------------------------
    for strategie in CONFIG['STRATEGIES']:
        # Neues Gurobi-Modell
        model = Model("Ladehub_Optimierung")
        model.setParam('OutputFlag', 0)

        # Variablen
        P, Pplus, Pminus = {}, {}, {}
        P_max_i, P_max_i_2, SoC, z = {}, {}, {}, {}

        for i in range(I):
            for t_step in range(t_in[i], t_out[i] + 1):
                
                P[(i,t_step)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS)

                Pplus[(i,t_step)]  = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
                Pminus[(i,t_step)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
                P_max_i[(i,t_step)]   = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
                P_max_i_2[(i,t_step)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS)
                z[(i,t_step)] = model.addVar(vtype=GRB.BINARY)

            for t_step in range(t_in[i], t_out[i] + 2):
                SoC[(i,t_step)] = model.addVar(lb=0, ub=1, vtype=GRB.CONTINUOUS)

        # CONSTRAINTS
        # 1) Energiebedarf
        for i in range(I):
            model.addConstr(quicksum(P[(i, t_step)]*Delta_t 
                                     for t_step in range(t_in[i], t_out[i]+1)) <= E_req[i])

        # 2) SOC-Fortschreibung
        for i in range(I):
            model.addConstr(SoC[(i, t_in[i])] == SOC_A[i])
            for t_step in range(t_in[i], t_out[i]+1):
                model.addConstr(
                    SoC[(i, t_step+1)] == SoC[(i, t_step)] + P[(i, t_step)] * Delta_t / kapaz[i]
                )

        # 3) Ladekurven
        for i in range(I):
            for t_step in range(t_in[i], t_out[i]+1):
                ml = max_lkw_leistung[i]
                model.addConstr(P_max_i[(i, t_step)]   == (-0.177038*SoC[(i,t_step)] + 0.970903)*ml)
                model.addConstr(P_max_i_2[(i,t_step)] == (-1.51705*SoC[(i,t_step)] + 1.6336)*ml)

                model.addConstr(Pplus[(i,t_step)]  <= P_max_i[(i,t_step)]   * z[(i,t_step)])
                model.addConstr(Pminus[(i,t_step)] <= P_max_i[(i,t_step)]   * (1 - z[(i,t_step)]))
                model.addConstr(Pplus[(i,t_step)]  <= P_max_i_2[(i,t_step)] * z[(i,t_step)])
                model.addConstr(Pminus[(i,t_step)] <= P_max_i_2[(i,t_step)] * (1 - z[(i,t_step)]))

        # 4) Leistungsbegrenzung Ladesäulentyp
        for i in range(I):
            typ = l[i]
            P_max_l = ladeleistung[typ]
            for t_step in range(t_in[i], t_out[i]+1):
                model.addConstr(Pplus[(i,t_step)]  <= z[(i,t_step)] * P_max_l)
                model.addConstr(Pminus[(i,t_step)] <= (1 - z[(i,t_step)]) * P_max_l)

        # 5) Netzanschluss
        for t_step in range(T_7):
            idx = [i for i in range(I) if t_in[i] <= t_step <= t_out[i]]
            if idx:
                model.addConstr(quicksum(Pplus[(i,t_step)] + Pminus[(i,t_step)] 
                                         for i in idx) <= netzanschluss)

        # 6) Kopplungsbedingungen (P = Pplus - Pminus, z monoton steigend)
        for i in range(I):
            for t_step in range(t_in[i], t_out[i]+1):
                model.addConstr(P[(i,t_step)] == Pplus[(i,t_step)] - Pminus[(i,t_step)])
            for t_step in range(t_in[i], t_out[i]):
                model.addConstr(z[(i, t_step+1)] >= z[(i, t_step)])

        # -------------------------------------
        # Zielfunktion
        # -------------------------------------

        if strategie == "T_min":
            obj_expr = quicksum(((1/(t+1)) * (Pplus[(i, t)])) - (t * Pminus[(i, t)]) for i in range(I) for t in range(t_in[i], t_out[i] + 1))

        elif strategie == "Konstant":
            # Hilfsvariablen für Leistungsänderungen zwischen Zeitschritten
            delta = {}
            for i in range(I):
                for t_step in range(t_in[i], t_out[i]):
                    # Variable für die absolute Differenz zwischen aufeinanderfolgenden Zeitschritten
                    delta[(i,t_step)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"delta_{i}_{t_step}")
                    # Berechnung der absoluten Differenz zwischen aufeinanderfolgenden Leistungswerten
                    model.addConstr(delta[(i,t_step)] >= P[(i,t_step+1)] - P[(i,t_step)])
                    model.addConstr(delta[(i,t_step)] >= P[(i,t_step)] - P[(i,t_step+1)])
            
            # Extrem hohe Gewichtung für die Energiemaximierung, um absolute Priorität zu gewährleisten
            M_energy = 1000000  # Sehr hoher Gewichtungsfaktor
            
            # Zielfunktion: Hierarchisches Modell
            # 1. Primäres Ziel mit sehr hoher Gewichtung: Maximiere Energie
            # 2. Sekundäres Ziel: Minimiere Leistungsschwankungen
            obj_expr = quicksum(
                M_energy * Pplus[(i, t)]  # Primärziel mit sehr hoher Gewichtung
                - quicksum(delta[(i, t_step)] for t_step in range(t_in[i], min(t+1, t_out[i])) if t_step < t_out[i])  # Sekundärziel
                for i in range(I) for t in range(t_in[i], t_out[i] + 1)
            )


        model.setObjective(obj_expr, GRB.MAXIMIZE)
        model.optimize()
        
        # -------------------------------------
        # Ergebnisse verarbeiten
        # -------------------------------------
        if model.Status == GRB.OPTIMAL:
            # Ladequote in dieser Woche
            list_volladungen = []
            for i in range(I):
                if SoC[(i, t_out[i]+1)].X >= SOC_req[i] - 0.01:
                    list_volladungen.append(1)
                else:
                    list_volladungen.append(0)
            ladequote_week = sum(list_volladungen) / len(list_volladungen)
            
            # Gesamtkosten
            if strategie == 'T_min':
                print(f"[Szenario={szenario}, Woche={target_week}, Strategie={strategie}] "
                      f"Lösung OK. Ladequote: {ladequote_week:.3f}, "
                      f"Anzahl LKW: {len(df_lkw_filtered)}")
            elif strategie == 'Konstant':
                    print(f"[Szenario={szenario}, Woche={target_week}, Strategie={strategie}] "
                      f"Lösung OK. Ladequote: {ladequote_week:.3f}, "
                      f"Anzahl LKW: {len(df_lkw_filtered)}")
            
            # Lastgang: direkt in rows eintragen
            for t_step in range(T_7):
                sum_p_total = 0.0
                sum_p_total_max = 0.0
                sum_p_ncs = 0.0
                sum_p_hpc = 0.0
                sum_p_mcs = 0.0
                for i in range(I):
                    if t_in[i] <= t_step <= t_out[i]:
                        val = P[(i, t_step)].X
                        sum_p_total += val
                        sum_p_total_max += ladeleistung[l[i]]
                        if l[i] == 'NCS':
                            sum_p_ncs += val
                        elif l[i] == 'HPC':
                            sum_p_hpc += val
                        elif l[i] == 'MCS':
                            sum_p_mcs += val
                
                # Direktes Eintragen in rows mit dem entsprechenden Index
                row_idx = row_index[(strategie, t_step)]
                rows[row_idx]['Leistung_Total'] += sum_p_total
                rows[row_idx]['Leistung_Max_Total'] += sum_p_total_max
                rows[row_idx]['Leistung_NCS'] += sum_p_ncs
                rows[row_idx]['Leistung_HPC'] += sum_p_hpc
                rows[row_idx]['Leistung_MCS'] += sum_p_mcs
                rows[row_idx]['Ladequote'] = ladequote_week  # Überschreiben, nicht addieren

            for i in range(I):
                t_charging = 0
                for t in range(T_7):   
                    if t_in[i] <= t <= t_out[i]+1:
                        dict_lkw_lastgang['Datum'].append(start_date + pd.Timedelta(minutes=t*5))
                        dict_lkw_lastgang['Woche'].append(target_week)
                        dict_lkw_lastgang['Tag'].append(df_lkw_filtered.iloc[i]['Tag'] % 7)
                        dict_lkw_lastgang['Zeit'].append((t * 5) % 1440)
                        dict_lkw_lastgang['Ladestrategie'].append(strategie)
                        dict_lkw_lastgang['LKW_ID'].append(df_lkw_filtered.iloc[i]['Nummer'])
                        dict_lkw_lastgang['Ladetyp'].append(l[i])
                        dict_lkw_lastgang['Ladezeit'].append(t_charging)
                        t_charging += 5
                        if t > t_out[i]:
                            dict_lkw_lastgang['Leistung'].append(None)
                            dict_lkw_lastgang['Pplus'].append(None)
                            dict_lkw_lastgang['Pminus'].append(None)
                            dict_lkw_lastgang['SOC'].append(SoC[(i, t_out[i]+1)].X)
                            dict_lkw_lastgang['z'].append(None)
                            dict_lkw_lastgang['Max_Leistung'].append(None)
                            continue
                        else:       
                            dict_lkw_lastgang['Max_Leistung'].append(min(ladeleistung[l[i]], max_lkw_leistung[i]))
                            dict_lkw_lastgang['z'].append(z[(i, t)].X)
                            dict_lkw_lastgang['Pplus'].append(Pplus[(i, t)].X)
                            dict_lkw_lastgang['Pminus'].append(Pminus[(i, t)].X)
                            dict_lkw_lastgang['Leistung'].append(P[(i, t)].X)
                            dict_lkw_lastgang['SOC'].append(SoC[(i, t)].X)
        else:
            print(f"[Szenario={szenario}, Woche={target_week}, Strategie={strategie}] "
                  f"Keine optimale Lösung gefunden.")

    # -------------------------------------
    # DataFrames bauen und speichern
    # -------------------------------------
    # 1) Lastgang-DF je Strategie
    df_lastgang = pd.DataFrame(rows)

    # 2) LKW-Lastgang als DataFrame
    df_lkw_lastgang_df = pd.DataFrame(dict_lkw_lastgang)
    df_lkw_lastgang_df.sort_values(['LKW_ID', 'Ladestrategie', 'Zeit'], inplace=True)
    
    
    # Ordner anlegen und CSV speichern
    path = script_dir  # Use the script directory path that was already defined
    os.makedirs(os.path.join(path, 'data', 'epex', 'lastgang'), exist_ok=True)
    os.makedirs(os.path.join(path, 'data', 'epex', 'lastgang_lkw'), exist_ok=True)

    df_lastgang.to_csv(
        os.path.join(path, 'data', 'epex', 'lastgang', f'lastgang_{szenario}_w{target_week}.csv'),
        sep=';', decimal=',', index=False
    )
    df_lkw_lastgang_df.to_csv(
        os.path.join(path, 'data', 'epex', 'lastgang_lkw', f'lastgang_lkw_{szenario}_w{target_week}.csv'),
        sep=';', decimal=',', index=False
    )
    return None


def main():
    # Parse command line arguments to allow week selection
    parser = argparse.ArgumentParser(description='Charging Hub Optimization')
    parser.add_argument('--week', type=int, default=1, help='Week to optimize (default: 1)')
    parser.add_argument('--szenario', type=str, default='cl_2_quote_80-80-80_netz_100_pow_100-100-100_pause_45-540_M_1', 
                        help='Scenario to optimize')
    args = parser.parse_args()
    
    print(f"Starte Optimierung für Woche {args.week}: {args.szenario}")
    logging.info(f"Optimierung p_max/p_min: {args.szenario} - Woche {args.week}")
    modellierung(args.szenario, target_week=args.week)

if __name__ == '__main__':
    start = time.time()
    main()
    end = time.time()
    print(f"Gesamtlaufzeit: {end - start:.2f} Sekunden")