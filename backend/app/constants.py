"""Constantes du domaine fixées par la spec (non opérationnelles).

Ces valeurs font partie du contrat (spec §4/§5) et non de la configuration
d'environnement : elles restent stables quelle que soit l'installation.
Les limites opérationnelles (rate limit, upload, densité du graphe,
pagination) sont dans `app.config.Settings`.
"""
from __future__ import annotations

# Criticité des actifs (spec §4 : entier 1–5).
CRITICALITY_MIN: int = 1
CRITICALITY_MAX: int = 5
CRITICALITY_DEFAULT: int = 3

# CVSS (spec §4 : numérique 0–10, arrondi à 0.1 — colonne NUMERIC(4,1)).
CVSS_MIN: float = 0.0
CVSS_MAX: float = 10.0

# Algorithme contractuel des chemins (spec §4, D-10 : non modifiable).
GRAPH_PATH_MIN_EDGES: int = 1
GRAPH_PATH_MAX_EDGES: int = 6
GRAPH_PATH_MAX_RESULTS: int = 20
