"""Phase 1 library: scenario building and the Minimise Delay algorithm (thesis section 3.3.3, fig. 3.5).

Imported by 07_scenario.py, 08_min_delay.py, 09_figures.py and 10_robustness.py. Every parameter
comes from config.py; the functions take them as arguments so the robustness runs can change them.
"""
import json
import math

import numpy as np

import config as cfg

TYPES = ("residential", "office", "mixed")


# ----------------------------------------------------------------------------------------- geometry
def to_xy(lat, lon):
    """Local plane in km centred on the scenario centre (same projection as week 1)."""
    lat = np.asarray(lat, float); lon = np.asarray(lon, float)
    return (lon - cfg.CENTER_LON) * cfg.KM_PER_DEG_LON, (lat - cfg.CENTER_LAT) * cfg.KM_PER_DEG_LAT


def to_latlon(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    return cfg.CENTER_LAT + y / cfg.KM_PER_DEG_LAT, cfg.CENTER_LON + x / cfg.KM_PER_DEG_LON


def dist_matrix(ax, ay, bx, by):
    """Euclidean distance (km) between every point of A (rows) and every point of B (columns)."""
    return np.hypot(np.subtract.outer(ax, bx), np.subtract.outer(ay, by))


# ----------------------------------------------------------------------------------------- RRHs
def load_core():
    master = json.loads((cfg.JSON_DIR / "rrh_master.json").read_text(encoding="utf-8"))
    return [r for r in master["rrhs"] if r["in_core"]]


def sample_real(core, n, seed):
    """Simple random sample of n real core RRHs (None = all). Keeps the real density pattern."""
    if n is None or n >= len(core):
        chosen = list(core)
    else:
        idx = np.random.default_rng(seed).choice(len(core), size=n, replace=False)
        chosen = [core[i] for i in sorted(idx)]
    out = []
    for r in chosen:
        x, y = to_xy(r["lat"], r["lon"])
        out.append({"rrh_id": r["rrh_id"], "lat": r["lat"], "lon": r["lon"], "x": float(x), "y": float(y),
                    "label": r["label"], "operators": r["operators"], "is_synthetic": False})
    return out


def add_synthetic(rrhs, n, min_dist_m, seed):
    """Append n synthetic RRHs, uniform in the box, >= min_dist_m from every other RRH. Labelled SYNxxx."""
    rng = np.random.default_rng(seed)
    half = cfg.SIDE_KM / 2
    px = [r["x"] for r in rrhs]; py = [r["y"] for r in rrhs]
    dmin = min_dist_m / 1000.0
    out = list(rrhs); k = 0; tries = 0
    while k < n:
        tries += 1
        if tries > 1000 * max(n, 1):
            raise RuntimeError("cannot place the synthetic RRHs with this minimum distance")
        x, y = rng.uniform(-half, half, 2)
        if px and np.min(np.hypot(np.array(px) - x, np.array(py) - y)) < dmin:
            continue
        k += 1
        lat, lon = to_latlon(x, y)
        out.append({"rrh_id": f"SYN{k:03d}", "lat": round(float(lat), 6), "lon": round(float(lon), 6),
                    "x": float(x), "y": float(y), "label": "synthetic", "operators": [],
                    "is_synthetic": True})
        px.append(x); py.append(y)
    return out


# ----------------------------------------------------------------------------------------- traffic type
def _in_zone(lat, lon, zone):
    """Circle (name, lat, lon, r) or corridor (name, lat1, lon1, lat2, lon2, half-width)."""
    if len(zone) == 4:
        zone = (zone[0], zone[1], zone[2], zone[1], zone[2], zone[3])
    _, la1, lo1, la2, lo2, rad = zone
    ax, ay = to_xy(la1, lo1); bx, by = to_xy(la2, lo2); x, y = to_xy(lat, lon)
    ax, ay, bx, by, x, y = map(float, (ax, ay, bx, by, x, y))
    vx, vy = bx - ax, by - ay
    t = 0.0 if vx == vy == 0 else max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)))
    return math.hypot(x - (ax + t * vx), y - (ay + t * vy)) <= rad


def assign_traffic(rrhs, mode, shares=None, seed=0, core=None):
    """Give every RRH a traffic pattern: residential, office or mixed.

    mode "random": exact shares (rounded), shuffled with the seed.
    mode "geo": office districts > mixed-use zones > low-density outskirts (mixed) > residential.
    The reason is stored in rrh["traffic_reason"] so the map can show it.
    """
    if mode == "random":
        shares = shares or cfg.TRAFFIC_SHARES
        tot = sum(shares.values())
        n = len(rrhs)
        counts = {t: int(round(n * shares.get(t, 0) / tot)) for t in TYPES}
        diff = n - sum(counts.values())              # fix rounding on the largest class
        counts[max(counts, key=counts.get)] += diff
        pool = [t for t in TYPES for _ in range(counts[t])]
        np.random.default_rng(seed).shuffle(pool)
        for r, t in zip(rrhs, pool):
            r["traffic"] = t; r["traffic_reason"] = f"random ({shares.get(t, 0):.0%} share)"
        return rrhs

    core = core if core is not None else load_core()
    cx, cy = to_xy([c["lat"] for c in core], [c["lon"] for c in core])
    for r in rrhs:
        zone = next((z for z in cfg.OFFICE_ZONES if _in_zone(r["lat"], r["lon"], z)), None)
        if zone:
            r["traffic"], r["traffic_reason"] = "office", zone[0]
            continue
        zone = next((z for z in cfg.MIXED_ZONES if _in_zone(r["lat"], r["lon"], z)), None)
        if zone:
            r["traffic"], r["traffic_reason"] = "mixed", zone[0]
            continue
        nb = int(np.sum(np.hypot(cx - r["x"], cy - r["y"]) <= cfg.DENSITY_RADIUS_KM)) - (0 if r["is_synthetic"] else 1)
        r["local_density"] = nb
        if nb <= cfg.LOW_DENSITY_MAX:
            r["traffic"], r["traffic_reason"] = "mixed", f"outskirts ({nb} sites within {cfg.DENSITY_RADIUS_KM:g} km)"
        else:
            r["traffic"], r["traffic_reason"] = "residential", f"urban fabric ({nb} sites within {cfg.DENSITY_RADIUS_KM:g} km)"
    return rrhs


# ----------------------------------------------------------------------------------------- pools
def farthest_first(rrhs, k, min_dist_km):
    """Farthest-first k-center on the real RRH sites (every real RRH is a candidate pool site).

    Starts from the RRH nearest to the scenario centre, then repeatedly adds the RRH farthest from the
    pools already chosen. The first K pools of the list are the K-center solution for every K <= k.
    """
    cand = [r for r in rrhs if not r["is_synthetic"]]
    x = np.array([r["x"] for r in cand]); y = np.array([r["y"] for r in cand])
    first = int(np.argmin(np.hypot(x, y)))
    chosen = [first]
    dmin = np.hypot(x - x[first], y - y[first])
    while len(chosen) < k:
        j = int(np.argmax(dmin))
        if dmin[j] < min_dist_km:
            break
        chosen.append(j)
        dmin = np.minimum(dmin, np.hypot(x - x[j], y - y[j]))
    pools = []
    for i, j in enumerate(chosen, 1):
        r = cand[j]
        pools.append({"pool_id": f"P{i:02d}", "site_rrh": r["rrh_id"], "lat": r["lat"], "lon": r["lon"],
                      "x": r["x"], "y": r["y"], "ff_order": i})
    return pools


# ----------------------------------------------------------------------------------------- algorithm
def minimise_delay(rrhs, pools, dmax_km):
    """Minimise Delay algorithm, thesis fig. 3.5, without capacity limits.

    For each RRH: distance to every pool -> list of possible pools (distance <= dmax) ->
      0 possible pools  -> unserved (by distance)
      1 possible pool   -> connect to it
      >1 possible pools -> connect to the nearest one
    Returns a dict with the distance matrix, the option lists and the assignment.
    """
    rx = np.array([r["x"] for r in rrhs]); ry = np.array([r["y"] for r in rrhs])
    px = np.array([p["x"] for p in pools]); py = np.array([p["y"] for p in pools])
    D = dist_matrix(rx, ry, px, py)                      # [n_rrh, n_pool] km
    ok = D <= dmax_km + 1e-9
    n_opt = ok.sum(axis=1)
    nearest = np.argmin(D, axis=1)
    assign = np.where(n_opt > 0, nearest, -1)            # -1 = unserved
    d_assigned = np.where(assign >= 0, D[np.arange(len(rrhs)), nearest], np.nan)
    return {"D": D, "ok": ok, "n_opt": n_opt, "assign": assign, "d": d_assigned,
            "rtt": cfg.rtt_us(d_assigned), "unserved": int(np.sum(assign < 0)), "dmax": dmax_km}


def categories(res, n_pool):
    """Per pool: c1 = RRHs whose only option is this pool; c2 = optimal (nearest) here but other options
    exist; c3 = this pool is possible but not the nearest. Returns three lists of RRH indices per pool."""
    ok, n_opt, assign = res["ok"], res["n_opt"], res["assign"]
    c1 = [[] for _ in range(n_pool)]; c2 = [[] for _ in range(n_pool)]; c3 = [[] for _ in range(n_pool)]
    for i in range(ok.shape[0]):
        for p in np.flatnonzero(ok[i]):
            if assign[i] == p:
                (c1 if n_opt[i] == 1 else c2)[p].append(i)
            else:
                c3[p].append(i)
    return c1, c2, c3


def summary(res):
    rtt = res["rtt"][~np.isnan(res["rtt"])]
    return {"unserved": res["unserved"], "served": int(len(rtt)),
            "mean_rtt_us": float(rtt.mean()) if len(rtt) else float("nan"),
            "std_rtt_us": float(rtt.std()) if len(rtt) else float("nan"),
            "max_rtt_us": float(rtt.max()) if len(rtt) else float("nan"),
            "mean_d_km": float(np.nanmean(res["d"])) if len(rtt) else float("nan")}


def backward_elimination(rrhs, pools, dmax_km):
    """Start with every candidate pool active and remove, one at a time, the pool whose removal increases
    the mean RTT the least, as long as no extra RRH becomes unserved. Returns the removal history:
    a list of (K, active pool indices, summary) from K = len(pools) down to the smallest feasible K."""
    active = list(range(len(pools)))
    base = minimise_delay(rrhs, pools, dmax_km)
    hist = [(len(active), list(active), summary(base))]
    while len(active) > 1:
        best = None
        for p in active:
            trial = [q for q in active if q != p]
            s = summary(minimise_delay(rrhs, [pools[q] for q in trial], dmax_km))
            if s["unserved"] > base["unserved"]:
                continue
            if best is None or s["mean_rtt_us"] < best[2]["mean_rtt_us"]:
                best = (p, trial, s)
        if best is None:
            break
        active = best[1]
        hist.append((len(active), list(active), best[2]))
    return hist


def choose_k(hist, tol):
    """Smallest K of the backward-elimination history whose mean RTT is within tol of the all-pools value."""
    ref = hist[0][2]["mean_rtt_us"]
    ok = [h for h in hist if h[2]["mean_rtt_us"] <= (1 + tol) * ref]
    return min(ok, key=lambda h: h[0])
