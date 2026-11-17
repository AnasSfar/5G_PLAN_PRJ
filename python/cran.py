"""Shared helpers for week 2: loading RRHs, local km coordinates, k-center, delay assignment."""
import json

import numpy as np
import config as cfg


def load_core_rrhs():
    """Core RRHs (4G or 5G evidence) of the master dataset, plus x/y in km around the centre."""
    master = json.loads((cfg.JSON_DIR / "rrh_master.json").read_text(encoding="utf-8"))
    rrhs = [r for r in master["rrhs"] if r["in_core"]]
    lat = np.array([r["lat"] for r in rrhs]); lon = np.array([r["lon"] for r in rrhs])
    x, y = to_km(lat, lon)
    return rrhs, x, y


def to_km(lat, lon):
    """Local plane used in week 1: x east, y north, in km from the scenario centre."""
    return (np.asarray(lon) - cfg.CENTER_LON) * cfg.KM_PER_DEG_LON, \
           (np.asarray(lat) - cfg.CENTER_LAT) * cfg.KM_PER_DEG_LAT


def farthest_first(x, y, k):
    """Farthest-first traversal (Gonzalez 2-approximation of k-center).

    Candidates = every RRH. The first pool is the RRH closest to the centroid of all RRHs
    (deterministic); each next pool is the RRH farthest from the pools already chosen.
    Returns the list of chosen RRH indices (in order) and the covering radius per step.
    """
    first = int(np.argmin((x - x.mean()) ** 2 + (y - y.mean()) ** 2))
    chosen = [first]
    d = np.hypot(x - x[first], y - y[first])
    radius = [float(d.max())]
    for _ in range(1, k):
        nxt = int(np.argmax(d))
        chosen.append(nxt)
        d = np.minimum(d, np.hypot(x - x[nxt], y - y[nxt]))
        radius.append(float(d.max()))
    return chosen, radius


def distance_matrix(x, y, pool_idx):
    """RRH x pool distance matrix in km (straight line)."""
    px, py = x[pool_idx], y[pool_idx]
    return np.hypot(x[:, None] - px[None, :], y[:, None] - py[None, :])


def rtt_us(d_km):
    """Two-way fronthaul propagation delay in microseconds for a distance in km (eq. 3.3)."""
    return 2 * np.asarray(d_km) / cfg.FIBRE_SPEED_KM_PER_MS * 1000.0
