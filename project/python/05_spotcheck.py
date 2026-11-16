"""Step 5 - spot-check Infoantenas against OpenCelliD in three small areas.

OpenCelliD is crowd-sourced (positions are estimates, rows are CELLS not sites), so we do not
expect equal numbers. We only look for big disagreements. Infoantenas stays the source of truth.
The key is read from the OPENCELLID_KEY environment variable and never written to a file.
"""
import json
import os
import time

import pandas as pd
import requests
import config as cfg

AREAS = {  # name: (lat_south, lon_west)  -> box of 0.010 deg lat x 0.012 deg lon (~1.1 x 0.9 km)
    "dense: Salamanca": (40.420, -3.690),
    "medium: Alcobendas": (40.535, -3.645),
    "sparse: Monte de El Pardo": (40.515, -3.795),
}
DLAT, DLON = 0.010, 0.012


def fetch_opencellid(key, s, w):
    cache = cfg.DATA / "raw" / "opencellid" / f"area_{s}_{w}.json"     # raw answers are kept: never ask twice
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    cells = _fetch(key, s, w)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(cells), encoding="utf-8")
    return cells


def _fetch(key, s, w):
    cells, offset = [], 0
    while True:
        params = {"key": key, "BBOX": f"{s},{w},{s + DLAT},{w + DLON}", "format": "json",
                  "limit": 50, "offset": offset}
        for attempt in range(6):                      # the free API rate-limits (429): wait and retry
            r = requests.get("https://opencellid.org/cell/getInArea", params=params, timeout=60)
            if r.status_code != 429:
                break
            time.sleep(20 * (attempt + 1))
        r.raise_for_status()
        data = r.json()
        page = data.get("cells", [])
        cells += page
        if len(page) < 50:          # 'count' is the size of THIS page, so a short page means the last one
            return cells
        offset += 50
        time.sleep(cfg.SLEEP_S)


def main():
    key = os.environ.get("OPENCELLID_KEY")
    if not key:
        raise SystemExit("Set OPENCELLID_KEY first (setx OPENCELLID_KEY ... then reopen the terminal)")
    rrhs = json.loads((cfg.JSON_DIR / "rrh_master.json").read_text(encoding="utf-8"))["rrhs"]
    rows = []
    for name, (s, w) in AREAS.items():
        cells = fetch_opencellid(key, s, w)
        df = pd.DataFrame(cells)
        lte_nr = df[df["radio"].isin(["LTE", "NR"])] if len(df) else df
        # distinct positions at ~100 m resolution = rough number of OpenCelliD "sites"
        n_sites = len(lte_nr[["lat", "lon"]].round(3).drop_duplicates()) if len(lte_nr) else 0
        inside = [r for r in rrhs if r["in_core"] and s <= r["lat"] < s + DLAT and w <= r["lon"] < w + DLON]
        # Of our RRHs, how many have an OpenCelliD LTE/NR cell within 500 m? (OpenCelliD cells outside the
        # box can match too, so we fetched with the box only; RRHs near the edge may miss a match.)
        pts = lte_nr[["lat", "lon"]].values if len(lte_nr) else []
        def near(r):
            for la, lo in pts:
                dy = (la - r["lat"]) * cfg.KM_PER_DEG_LAT * 1000
                dx = (lo - r["lon"]) * cfg.KM_PER_DEG_LON * 1000
                if dx * dx + dy * dy <= 500 ** 2:
                    return True
            return False
        matched = sum(near(r) for r in inside)
        rows.append({"area": name, "opencellid_lte_nr_positions": n_sites, "infoantenas_rrh": len(inside),
                     "rrh_with_opencellid_cell_within_500m": matched,
                     "match_rate": round(matched / len(inside), 2) if inside else None})
        time.sleep(cfg.SLEEP_S)
    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    out.to_csv(cfg.DATA / "spotcheck_opencellid.csv", index=False)


if __name__ == "__main__":
    main()
