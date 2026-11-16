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
