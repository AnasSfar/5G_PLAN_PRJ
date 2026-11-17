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


# =====================================================================================
# WEEK 2 - BBU pools, traffic profiles and load balancing (phase 2 of the assignment)
# =====================================================================================
FIGS = ROOT / "img" / "week2"            # every week-2 figure goes here
RESULTS = ROOT / "json" / "week2"        # every week-2 numeric result goes here
for d in (FIGS, RESULTS):
    d.mkdir(parents=True, exist_ok=True)

# ---------- fronthaul delay ----------
FIBRE_SPEED_KM_PER_MS = 200.0            # 2e8 m/s in fibre (same value as the thesis)
MAX_RTT_US = 100.0                       # round-trip fronthaul budget; thesis uses 150 us (15 km)
D_MAX_KM = FIBRE_SPEED_KM_PER_MS * (MAX_RTT_US / 1000.0) / 2   # (3.3) of the thesis -> 10 km

# ---------- number of pools (farthest-first k-center) ----------
K_SWEEP = list(range(2, 41))             # K values tried for the coverage curve
K_CASES = {"few": 8, "normal": 12, "many": 25}   # the three cases compared (see week2.txt)
K_REFERENCE = "normal"

# ---------- traffic ----------
# Peak (busy-hour) downlink traffic of one operator station, in Mbps (average over the hour).
# 4G: 3 sectors x 20 MHz x 1.5 bit/s/Hz = 90 Mbps capacity, 50 % busy-hour load -> 45 Mbps.
# 5G n78: 3 sectors x 100 MHz x 5 bit/s/Hz = 1500 Mbps capacity, 10 % busy-hour load -> 150 Mbps.
PEAK_4G_MBPS = 45.0
PEAK_5G_MBPS = 150.0

# Office hubs (lat, lon): business districts of the scenario. An RRH closer than OFFICE_RADIUS_KM to
# one of them is an office cell. Mixed hubs (dense centre inside the M-30 with shops, offices and homes;
# airport) -> mixed cell.
# Every other RRH is residential. Rule chosen because we have no real per-site traffic (see week2.txt).
OFFICE_HUBS = {
    "AZCA / Nuevos Ministerios": (40.4497, -3.6925),
    "Cuatro Torres / Plaza de Castilla": (40.4766, -3.6874),
    "Distrito Telefonica (Las Tablas)": (40.5150, -3.6625),
    "Campo de las Naciones / IFEMA": (40.4636, -3.6150),
    "Mendez Alvaro": (40.3960, -3.6780),
    "Julian Camarillo (San Blas)": (40.4380, -3.6250),
    "Ciudad Universitaria": (40.4450, -3.7280),
    "Alcobendas business park": (40.5300, -3.6400),
}
OFFICE_RADIUS_KM = 1.5
MIXED_HUBS = {
    "Central almond inside the M-30 (Sol)": ((40.4250, -3.7000), 3.5),
    "Barajas airport": ((40.4915, -3.5932), 2.5),
}

# Normalised 24 h profiles digitised from Figure E.1 of the thesis. Index h = traffic of the hour
# ending at h:00 (h = 1..24, 24 = midnight). 1.0 = peak hour of that profile.
PROFILES = {
    "residential": [0.90, 0.645, 0.59, 0.52, 0.32, 0.165, 0.145, 0.225, 0.175, 0.215, 0.26, 0.265,
                    0.30, 0.34, 0.435, 0.42, 0.60, 0.795, 0.805, 0.465, 0.79, 1.00, 0.93, 0.86],
    "office":      [0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.32, 0.19, 0.245, 0.53, 0.975,
                    0.40, 0.945, 0.79, 1.00, 0.55, 0.12, 0.035, 0.075, 0.005, 0.005, 0.005, 0.005],
    "mixed":       [0.36, 0.36, 0.275, 0.11, 0.065, 0.13, 0.165, 0.335, 0.49, 0.52, 0.59, 0.65,
                    0.70, 0.72, 0.92, 0.94, 0.87, 1.00, 0.85, 0.78, 0.595, 0.76, 0.885, 0.76],
}
HOURS = list(range(1, 25))
REPORT_HOURS = [8, 15, 21]               # the three hours asked for the "before" figures
