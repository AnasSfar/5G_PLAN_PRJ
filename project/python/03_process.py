"""Step 3 - raw files -> clean master dataset.

raw tiles -> remove duplicates -> read bands from detail pages -> label 4G/5G -> drop sites
without 4G/5G -> merge towers within 50 m into ONE RRH -> master JSON + CSV.
The raw files are only read, never modified.
"""
import json
import re
from collections import Counter

import numpy as np
import pandas as pd
import config as cfg

def short_operator(name: str) -> str:
    up = name.upper()
    for key, val in (("ORANGE", "Orange"), ("TELEFONICA", "Movistar"), ("VODAFONE", "Vodafone"),
                     ("XFERA", "MasMovil/Yoigo"), ("MASMOVIL", "MasMovil/Yoigo")):
        if key in up:
            return val
    return name.title()


def overlaps(lo, hi, ranges):
    return any(lo < b and hi > a for a, b in ranges)


def parse_bands(html_bytes: bytes):
    """Return a list of (low, high) MHz pairs found in the 'Banda Asignada' table."""
    text = html_bytes.decode("latin-1")
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    head = text.split("NIVELES MEDIDOS")[0]               # band table comes before the field measurements
    return [(float(a), float(b)) for a, b in re.findall(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", head)
            if float(a) > 100]                           # ignore ids such as "B B -2300351"


def load_raw_sites():
    sites, n_raw = {}, 0
    for f in sorted(cfg.RAW_TILES.glob("tile_*.json")):
        text = f.read_bytes().decode("latin-1").strip()
        for ft in json.loads(text or "{}").get("features", []):
            n_raw += 1
            p = ft["properties"]
            code = p["Gis_Codigo"]
            if code in sites:                                # same site seen in two tiles
                continue
            lon, lat = ft["geometry"]["coordinates"]
            sites[code] = {"code": code, "site_id": p["Gis_ID"], "lat": lat, "lon": lon,
                           "operator": short_operator(code.split(" - ")[0])}
    return sites, n_raw


def label_site(bands):
    g4 = any(overlaps(lo, hi, cfg.BANDS_4G) for lo, hi in bands)
    g5 = any(overlaps(lo, hi, cfg.BANDS_5G) for lo, hi in bands)
    amb = any(overlaps(lo, hi, cfg.BANDS_AMBIGUOUS) for lo, hi in bands)
    return g4, g5, amb


def merge_within(df: pd.DataFrame, radius_m: float):
    """Single-linkage clustering: sites closer than radius_m end up in the same group."""
    x = (df["lon"].values - cfg.CENTER_LON) * cfg.KM_PER_DEG_LON * 1000
    y = (df["lat"].values - cfg.CENTER_LAT) * cfg.KM_PER_DEG_LAT * 1000
    parent = list(range(len(df)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    cell = {}
    for i, (xi, yi) in enumerate(zip(x, y)):                 # grid hashing keeps this fast
        cell.setdefault((int(xi // radius_m), int(yi // radius_m)), []).append(i)
    for i, (xi, yi) in enumerate(zip(x, y)):
        cx, cy = int(xi // radius_m), int(yi // radius_m)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cell.get((cx + dx, cy + dy), []):
                    if j > i and (x[j] - xi) ** 2 + (y[j] - yi) ** 2 <= radius_m ** 2:
                        parent[find(j)] = find(i)
    return np.array([find(i) for i in range(len(df))]), x, y


def main():
    sites, n_raw = load_raw_sites()
    stats = {"raw_features": n_raw, "distinct_sites": len(sites)}

    rows, missing = [], 0
    for code, s in sites.items():
        detail = cfg.RAW_DETAILS / (re.sub(r"[^A-Za-z0-9._-]+", "_", code) + ".html")
        if not detail.exists():
            missing += 1
            continue
        bands = parse_bands(detail.read_bytes())
        g4, g5, amb = label_site(bands)
        rows.append({**s, "has_4g": g4, "has_5g": g5, "amb": amb, "bands": sorted({f"{lo:g}-{hi:g}" for lo, hi in bands})})
    stats["no_detail_page"] = missing
    df = pd.DataFrame(rows)
    stats["with_detail"] = len(df)

    stats["stations_with_4g_or_5g_evidence"] = int((df["has_4g"] | df["has_5g"]).sum())
    stats["stations_ambiguous_only"] = int((~df["has_4g"] & ~df["has_5g"] & df["amb"]).sum())
    df = df[df["has_4g"] | df["has_5g"] | df["amb"]].reset_index(drop=True)   # keep ambiguous, flagged
    stats["dropped_no_recognised_band"] = stats["with_detail"] - len(df)

    grp, x, y = merge_within(df, cfg.MERGE_RADIUS_M)
    df["grp"] = grp
    rrhs = []
    for k, (_, g) in enumerate(df.groupby("grp"), 1):
        g4, g5 = bool(g["has_4g"].any()), bool(g["has_5g"].any())
        rrhs.append({
            "rrh_id": f"RRH{k:04d}",
            "lat": round(float(g["lat"].mean()), 6),
            "lon": round(float(g["lon"].mean()), 6),
            "operators": sorted(g["operator"].unique()),
            "site_ids": sorted(g["code"]),
            "n_towers_merged": int(len(g)),
            "has_4g": g4, "has_5g": g5,
            "label": "4G+5G" if g4 and g5 else ("5G" if g5 else ("4G" if g4 else "ambiguous")),
            "in_core": bool(g4 or g5),   # True = at least one band that is real 4G/5G evidence
            "bands": sorted({b for bl in g["bands"] for b in bl}, key=lambda b: float(b.split("-")[0])),
            "is_synthetic": False,
        })
    stats["rrh_after_merge"] = len(rrhs)
    stats["rrh_core_4g5g_evidence"] = sum(r["in_core"] for r in rrhs)
    stats["rrh_ambiguous_only"] = sum(not r["in_core"] for r in rrhs)
    stats["label_counts"] = dict(Counter(r["label"] for r in rrhs))
    stats["operator_counts"] = dict(Counter(o for r in rrhs for o in r["operators"]))
    stats["max_towers_in_one_rrh"] = max(r["n_towers_merged"] for r in rrhs)

    master = {"scenario": {"centre": [cfg.CENTER_LAT, cfg.CENTER_LON], "side_km": cfg.SIDE_KM,
                           "bbox_w_s_e_n": [round(v, 6) for v in cfg.BBOX], "merge_radius_m": cfg.MERGE_RADIUS_M,
                           "source": "Infoantenas (MINETUR) GeoJSON + detail pages"},
              "stats": stats, "rrhs": rrhs}
    (cfg.JSON_DIR / "rrh_master.json").write_text(json.dumps(master, indent=1, ensure_ascii=False), encoding="utf-8")

    flat = pd.DataFrame(rrhs)
    for col in ("operators", "site_ids", "bands"):
        flat[col] = flat[col].apply(lambda v: "|".join(v))
    flat.to_csv(cfg.DATA / "rrh_master.csv", index=False, encoding="utf-8")

    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
