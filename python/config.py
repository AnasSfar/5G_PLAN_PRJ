"""Shared settings for the C-RAN project (week 1: scenario definition).

Every other script imports its constants from here, so the scenario
(centre, size, tile size, thresholds) is defined in exactly one place.
"""
import math
from pathlib import Path

# ---------- folders ----------
ROOT = Path(__file__).resolve().parent.parent          # .../project
RAW_TILES = ROOT / "data" / "raw" / "tiles"            # raw GeoJSON answers (never edited)
RAW_DETAILS = ROOT / "data" / "raw" / "details"        # raw detail pages (never edited)
DATA = ROOT / "data"
JSON_DIR = ROOT / "json"
MAPS = ROOT / "maps"
for d in (RAW_TILES, RAW_DETAILS, DATA, JSON_DIR, MAPS):
    d.mkdir(parents=True, exist_ok=True)

# ---------- scenario ----------
CENTER_LAT, CENTER_LON = 40.4531, -3.6883   # Madrid, around the Santiago Bernabeu stadium
SIDE_KM = 30.0                         # 30 x 30 km box
TILE_KM = 2.0                          # one request per 2 x 2 km tile
N_TILES = int(round(SIDE_KM / TILE_KM))  # 15 -> 15 x 15 = 225 requests

KM_PER_DEG_LAT = 111.19                # approx., good enough at this scale
KM_PER_DEG_LON = KM_PER_DEG_LAT * math.cos(math.radians(CENTER_LAT))

HALF_LAT = SIDE_KM / 2 / KM_PER_DEG_LAT
HALF_LON = SIDE_KM / 2 / KM_PER_DEG_LON
BBOX = (CENTER_LON - HALF_LON, CENTER_LAT - HALF_LAT,   # west, south
        CENTER_LON + HALF_LON, CENTER_LAT + HALF_LAT)   # east, north

# ---------- Infoantenas ----------
BASE_URL = "https://geoportal.minetur.gob.es/VCTEL"
GEOJSON_URL = BASE_URL + "/infoantenasGeoJSON.do"
DETAIL_URL = BASE_URL + "/detalleEstacion.do"
GEOJSON_ZOOM = 3          # the portal's own "zoom" parameter; values 1-6 return all sites, >=8 returns {}
SLEEP_S = 0.5             # pause between requests (be polite to the server)
USER_AGENT = "EETAC-MASTEAM-student-project/1.0 (academic C-RAN scenario)"
RETRIES = 3

# ---------- processing ----------
MERGE_RADIUS_M = 50.0     # towers closer than this become ONE RRH

# Band -> technology rules (MHz, downlink-ish ranges). Infoantenas gives frequencies only, never the
# technology name, so the label is inferred. See week1.txt for the reasoning and its limits.
BANDS_4G = [(791, 862), (1710, 1880), (2500, 2690)]   # 800, 1800, 2600 MHz -> 4G evidence
BANDS_5G = [(3300, 3800), (24250, 27500)]               # 3.5 GHz (n78), 26 GHz (n258) -> 5G evidence
BANDS_AMBIGUOUS = [(703, 788), (880, 960), (1920, 2170)]  # 700, 900, 2100 MHz -> technology cannot be told
# A frequency does not identify the radio technology (700 MHz is used for 4G and 5G, 900/2100 MHz for
# 2G/3G/4G, 1800 MHz can also carry 5G with spectrum sharing). So 700/900/2100 MHz alone give the label
# "ambiguous": the site is kept in the master file but is not counted as 4G or 5G evidence.


def tile_bbox(r: int, c: int):
    """Bounding box (west, south, east, north) of tile row r, column c (0-based, r=0 is the south row)."""
    w0, s0, _, _ = BBOX
    dlon = 2 * HALF_LON / N_TILES
    dlat = 2 * HALF_LAT / N_TILES
    return (w0 + c * dlon, s0 + r * dlat, w0 + (c + 1) * dlon, s0 + (r + 1) * dlat)


# =====================================================================================================
# PHASE 1 - MINIMISE DELAY (thesis section 3.3.3, professor's review "Project review phase 1 min delay")
# Every phase-1 parameter lives here; 07_scenario.py, 08_min_delay.py and 09_figures.py only read them.
# =====================================================================================================
PHASE1 = ROOT / "phase1"                      # all phase-1 outputs
P1_DATA = PHASE1 / "data"                     # CSV / JSON tables
P1_FIG = PHASE1 / "figures"                   # PNG figures
P1_MAPS = PHASE1 / "maps"                     # interactive Folium maps
for d in (PHASE1, P1_DATA, P1_FIG, P1_MAPS):
    d.mkdir(parents=True, exist_ok=True)

# ---------- RRHs ----------
N_RRH_REAL = 200            # real (Infoantenas, core) RRHs drawn for the reference scenario; None = all 2,085
RRH_SAMPLE_SEED = 42        # simple random sample: keeps the real density (dense centre, sparse edges)
N_SYNTHETIC = 0             # extra synthetic RRHs, uniform at random in the 30 x 30 km box (input variable)
SYNTH_MIN_DIST_M = 200.0    # a synthetic RRH is placed at least this far from any other RRH
SYNTH_SEED = 7

# ---------- traffic pattern of each RRH ----------
TRAFFIC_MODE = "geo"        # "random" (shares below) or "geo" (realistic, from the map of Madrid)
TRAFFIC_SHARES = {"mixed": 0.50, "office": 0.30, "residential": 0.20}   # used by "random" (input variable)
TRAFFIC_SEED = 11
TRAFFIC_COLORS = {"residential": "#2a78d6", "office": "#eb6834", "mixed": "#1baf7a"}   # validated palette slots 1-3
# "geo" rule, in order of precedence: inside an office district -> office; inside a mixed-use zone -> mixed;
# low local site density (outskirts, large cells covering several land uses, as in thesis fig. 4.2) -> mixed;
# otherwise -> residential. A zone is a circle (name, lat, lon, radius km) or a corridor around a segment
# (name, lat1, lon1, lat2, lon2, half-width km). Positions are approximate; check them on the map.
OFFICE_ZONES = [
    ("Paseo de la Castellana axis (Colon - Plaza de Castilla)", 40.4253, -3.6903, 40.4665, -3.6889, 0.6),
    ("AZCA / Nuevos Ministerios",               40.4495, -3.6925, 1.0),
    ("Cuatro Torres Business Area",             40.4770, -3.6880, 0.7),
    ("Distrito Telefonica (Las Tablas)",        40.5155, -3.6635, 0.8),
    ("Arroyo de la Vega business park",         40.5310, -3.6430, 1.0),
    ("Campo de las Naciones / IFEMA",           40.4640, -3.6180, 1.0),
    ("Julian Camarillo business area",          40.4370, -3.6260, 0.7),
    ("Mendez Alvaro offices",                   40.3960, -3.6780, 0.6),
    ("Ciudad Universitaria",                    40.4470, -3.7280, 1.2),
    ("Ciudad de la Imagen (Pozuelo)",           40.3960, -3.7780, 0.8),
]
MIXED_ZONES = [
    ("Historic centre (Sol, Gran Via)",         40.4170, -3.7035, 1.8),
    ("Madrid-Barajas airport",                  40.4800, -3.5750, 2.5),
]
DENSITY_RADIUS_KM = 1.0     # local density = real core RRHs within this radius (full 2,085 dataset)
LOW_DENSITY_MAX = 4         # at most this many neighbours -> outskirts -> mixed

# ---------- fronthaul delay ----------
MAX_RTT_US = 200.0          # maximum round-trip (two-way) fronthaul delay, review: 200 us
FIBRE_KM_PER_MS = 200.0     # propagation speed in fibre, 2e8 m/s (thesis section 4.1)
ROUTE_FACTOR = 1.0          # fibre length / straight-line distance; 1.0 = straight line as in the thesis
RTT_SWEEP_US = [200.0, 150.0, 100.0, 50.0]   # sensitivity: 150 us = thesis reference, 50 us ~ "5x stricter for 5G"


def d_max_km(rtt_us: float = MAX_RTT_US) -> float:
    """Maximum RRH-pool straight-line distance for a round-trip budget, eq. (3.3): d = v * RTT / 2."""
    return FIBRE_KM_PER_MS * (rtt_us / 1000.0) / 2.0 / ROUTE_FACTOR


def rtt_us(dist_km):
    """Round-trip fronthaul delay (us) of a straight-line distance (km), inverse of d_max_km."""
    return 2.0 * dist_km * ROUTE_FACTOR / FIBRE_KM_PER_MS * 1000.0


# ---------- BBU pools ----------
N_POOL_CANDIDATES = 25      # possible pool sites, fixed once (review: start large, e.g. 25, then reduce)
POOL_MIN_DIST_KM = 2.0      # two candidate pools are never closer than this
# Selection of the active pools: "auto" = smallest K whose mean RTT is within KNEE_TOL of the 25-pool value
# (backward elimination from 25), or an integer to force K.
K_ACTIVE = "auto"
KNEE_TOL = 0.10
