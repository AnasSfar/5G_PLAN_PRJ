"""Shared functions of phase 2 (load balancing). Used by 13_traffic.py, 14_balancing.py, 15_figures.py."""
import json

import numpy as np
import pandas as pd

import config as cfg
import p1_lib as L


# ----------------------------------------------------------------------------- inputs from phase 1
def load_scenario():
    """Phase-1 scenario (RRHs with traffic pattern, 25 candidate pools) and the active pool set of every K,
    taken from the backward elimination at the reference delay budget (phase1/data/k_analysis.csv)."""
    sc = json.loads((cfg.P1_DATA / "scenario.json").read_text(encoding="utf-8"))
    k = pd.read_csv(cfg.P1_DATA / "k_analysis.csv")
    k = k[(k.method == "backward_elimination") & (k.rtt_limit_us == cfg.MAX_RTT_US)]
    sets = {int(r.K): r.active_pools.split() for r in k.itertuples()}
    return sc["rrhs"], sc["pools"], sets


def balance_hour():
    """Hour where the sum of the three normalised profiles is maximum (review a), unless fixed in config."""
    if cfg.BALANCE_HOUR != "auto":
        return int(cfg.BALANCE_HOUR)
    s = sum(np.array(v) for v in cfg.PROFILES.values())
    return int(cfg.HOURS[int(np.argmax(s))])


# ----------------------------------------------------------------------------- traffic
def peak_gbph(rrhs):
    """Busy-hour traffic of each RRH in GBph, from the technologies and the number of merged stations."""
    master = {r["rrh_id"]: r for r in json.loads((cfg.JSON_DIR / "rrh_master.json").read_text(encoding="utf-8"))["rrhs"]}
    out = []
    for r in rrhs:
        m = master.get(r["rrh_id"])
        if m is None or r.get("is_synthetic"):                       # synthetic: one 4G + 5G station
            n, g4, g5 = 1, True, True
        else:
            n, g4, g5 = m["n_towers_merged"], m["has_4g"], m["has_5g"]
        out.append(n * (cfg.PEAK_4G_MBPS * g4 + cfg.PEAK_5G_MBPS * g5) * cfg.MBPS_TO_GBPH)
    return np.array(out)


def traffic_matrix(peak, patterns, force=None):
    """RRH x 24 h traffic in GBph. force = "residential" / "office" gives every RRH that profile."""
    prof = {k: np.array(v) for k, v in cfg.PROFILES.items()}
    return np.vstack([p * prof[force or c] for p, c in zip(peak, patterns)])


# ----------------------------------------------------------------------------- assignments
def possible_pools(rrhs, pools, dmax_km):
    x = np.array([r["x"] for r in rrhs]); y = np.array([r["y"] for r in rrhs])
    D = L.dist_matrix(x, y, np.array([p["x"] for p in pools]), np.array([p["y"] for p in pools]))
    return D, D <= dmax_km + 1e-9


def delay_only(D, ok):
    """Minimise Delay (phase 1): nearest possible pool, -1 if none."""
    Dm = np.where(ok, D, np.inf)
    a = np.argmin(Dm, axis=1)
    a[~ok.any(axis=1)] = -1
    return a


def balance(D, ok, w, by="traffic", slack_km=None):
    """Load balancing of the phase-2 review.

    b. first iteration: RRHs with a single possible pool go to it; the pool load is updated.
    c./e. second iteration, order of the remaining RRHs:
          by="traffic": fewest possible pools, then highest traffic w, then nearest possible pool;
          by="count":   fewest possible pools, then nearest possible pool.
    d./f. each RRH goes to its possible pool with the lowest load (traffic in GBph, or number of RRHs);
          ties -> the nearest pool. The load is updated after every assignment.
    w: traffic of every RRH at the balancing hour (ignored for by="count"). Returns pool index, -1 = unserved.
    slack_km: optional distance-aware variant (not in the review): an RRH may only use the possible pools at
    most slack_km farther than its nearest possible pool. None = every possible pool (review algorithm).
    """
    n, m = ok.shape
    a = np.full(n, -1)
    load = np.zeros(m)
    weight = w if by == "traffic" else np.ones(n)
    n_opt = ok.sum(axis=1)
    for i in np.flatnonzero(n_opt == 1):                           # first iteration
        j = int(np.flatnonzero(ok[i])[0]); a[i] = j; load[j] += weight[i]
    d_near = np.where(ok, D, np.inf).min(axis=1)
    rest = np.flatnonzero(n_opt > 1)
    if by == "traffic":
        order = rest[np.lexsort((d_near[rest], -w[rest], n_opt[rest]))]
    else:
        order = rest[np.lexsort((d_near[rest], n_opt[rest]))]
    scale = weight.max() if weight.max() > 0 else 1.0               # loads compared on a relative scale, so
    for i in order:                                                # that ties do not depend on the units
        cand = np.flatnonzero(ok[i])
        if slack_km is not None:
            cand = cand[D[i, cand] <= d_near[i] + slack_km + 1e-9]
        j = int(cand[np.lexsort((D[i, cand], np.round(load[cand] / scale, 9)))[0]])
        a[i] = j; load[j] += weight[i]
    return a


# ----------------------------------------------------------------------------- metrics
def pool_load(a, T, m):
    """Load of every pool for every hour (pools x 24), GBph."""
    out = np.zeros((m, T.shape[1]))
    for j in range(m):
        out[j] = T[a == j].sum(axis=0)
    return out


def rrh_count(a, m):
    return np.bincount(a[a >= 0], minlength=m)


def cv(v):
    v = np.asarray(v, float)
    return float(v.std() / v.mean()) if v.mean() else 0.0


def mux_gain(a, T, m):
    """Multiplexing gain per pool, thesis eq. (3.20): sum of RRH peaks / peak of the pool, and overall (3.21)."""
    peaks = T.max(axis=1)
    PL = pool_load(a, T, m)
    g = np.array([peaks[a == j].sum() / PL[j].max() if PL[j].max() > 0 else np.nan for j in range(m)])
    overall = peaks[a >= 0].sum() / PL.max(axis=1).sum()
    return g, float(overall)
