leistung_ladetyp = {
    'NCS': 100,
    'HPC': 400,
    'MCS': 1000
}

CONFIG = {
    'STRATEGIES': ["Hub"],  # ["T_min", "Konstant", "Hub"]
    # 'STRATEGIES': ["T_min", "Konstant", "Hub"]
    # T_min: Minimierung der Ladezeit - Kein Lademanagement
    # Konstant: Möglichst konstante Ladeleistung - Minimierung der Netzanschlusslast - Lademanagement
    # Hub: Minimierung der Hub-Lastspitzen - Globale Lastoptimierung - Hub-Level Lademanagement
    'ladequote': 0.8,  # Ladequote in Prozent
    'power': '100-100-100',  # Ladeleistung in Prozent (NCS-HPC-MCS)
    'pause': '45-540',  # Pausenzeiten in Minuten (min-max)
}