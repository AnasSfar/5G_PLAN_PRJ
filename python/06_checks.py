"""Step 6 - sanity checks on the data collection and on the technology rule.

A. Cap test: re-query the busiest tile as 4 and 16 sub-tiles. If the sub-tile totals equal the tile
   total, the service did not truncate the answer.
B. Sensitivity of the dataset to the technology rule (stations -> RRHs after the 50 m merge).
C. Manifest of the raw data (dates, counts, parameters) written to data/raw/manifest.json.
"""
import importlib.util
import json
import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import config as cfg


def load_module(name, file):
    spec = importlib.util.spec_from_file_location(name, cfg.ROOT / "python" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


proc = load_module("proc", "03_process.py")


def feats_of(bbox):
    w, s, e, n = bbox
    r = requests.get(cfg.GEOJSON_URL, params={"idCapa": "null", "bbox": f"{w:.6f},{s:.6f},{e:.6f},{n:.6f}",
                                              "zoom": cfg.GEOJSON_ZOOM}, timeout=60,
                     headers={"User-Agent": cfg.USER_AGENT})
    r.raise_for_status()
    t = r.content.decode("latin-1").strip()
    return {f["properties"]["Gis_Codigo"] for f in json.loads(t or "{}").get("features", [])}


def cap_test():
    best = max(cfg.RAW_TILES.glob("tile_*.json"),
               key=lambda f: len(json.loads(f.read_bytes().decode("latin-1").strip() or "{}").get("features", [])))
    r, c = int(best.stem.split("_")[1]), int(best.stem.split("_")[2])
    w, s, e, n = cfg.tile_bbox(r, c)
    total = len(feats_of((w, s, e, n)))
    out = {"tile": best.name, "tile_total": total}
    for k in (2, 4):
        codes = set()
        for i in range(k):
            for j in range(k):
                codes |= feats_of((w + (e - w) * i / k, s + (n - s) * j / k,
                                   w + (e - w) * (i + 1) / k, s + (n - s) * (j + 1) / k))
                time.sleep(cfg.SLEEP_S)
        out[f"distinct_in_{k*k}_subtiles"] = len(codes)
    return out


# ---- B. sensitivity ----
BAND = {"700": (703, 788), "800": (791, 862), "1800": (1710, 1880), "2100": (1920, 2170),
        "2600": (2500, 2690), "900": (880, 960), "3500": (3300, 3800), "26G": (24250, 27500)}


def has(bands, key):
    lo, hi = BAND[key]
    return any(a < hi and b > lo for a, b in bands)


def sensitivity():
    sites, _ = proc.load_raw_sites()
    rows = []
    for code, s in sites.items():
        d = cfg.RAW_DETAILS / (proc.re.sub(r"[^A-Za-z0-9._-]+", "_", code) + ".html")
        b = proc.parse_bands(d.read_bytes())
        rows.append({**s, "g4_ev": has(b, "800") or has(b, "1800") or has(b, "2600"),
                     "g5_ev": has(b, "3500") or has(b, "26G"),
                     "amb": has(b, "700") or has(b, "900") or has(b, "2100")})
    df = pd.DataFrame(rows)

    def rrh_count(mask):
        sub = df[mask].reset_index(drop=True)
        grp, _, _ = proc.merge_within(sub, cfg.MERGE_RADIUS_M)
        sub["grp"] = grp
        g = sub.groupby("grp").agg(g4=("g4_ev", "any"), g5=("g5_ev", "any"), amb=("amb", "any"))
        return {"stations": int(mask.sum()), "rrh": len(g),
                "4G+5G": int((g.g4 & g.g5).sum()), "4G": int((g.g4 & ~g.g5).sum()),
                "5G": int((~g.g4 & g.g5).sum()), "ambiguous_only": int((~g.g4 & ~g.g5).sum())}

    return {
        "stations_total": len(df),
        "stations_by_evidence": {"4G evidence (800/1800/2600)": int(df.g4_ev.sum()),
                                 "5G evidence (3.5G/26G)": int(df.g5_ev.sum()),
                                 "only ambiguous bands (700/900/2100)": int((~df.g4_ev & ~df.g5_ev & df.amb).sum()),
                                 "no recognised band": int((~df.g4_ev & ~df.g5_ev & ~df.amb).sum())},
        "A_strict_evidence_only": rrh_count(df.g4_ev | df.g5_ev),
        "B_strict_plus_ambiguous": rrh_count(df.g4_ev | df.g5_ev | df.amb),
    }


def manifest():
    files = list(cfg.RAW_TILES.glob("*.json")) + list(cfg.RAW_DETAILS.glob("*.html"))
    mt = [f.stat().st_mtime for f in files]
    m = {"source": cfg.BASE_URL, "geojson_params": {"idCapa": "null", "zoom": cfg.GEOJSON_ZOOM},
         "centre": [cfg.CENTER_LAT, cfg.CENTER_LON], "bbox_w_s_e_n": [round(v, 6) for v in cfg.BBOX],
         "tiles": len(list(cfg.RAW_TILES.glob("*.json"))),
         "detail_pages_on_disk": len(list(cfg.RAW_DETAILS.glob("*.html"))),
         "files_modified_between": [datetime.fromtimestamp(min(mt)).isoformat(timespec="minutes"),
                                    datetime.fromtimestamp(max(mt)).isoformat(timespec="minutes")],
         "merge_radius_m": cfg.MERGE_RADIUS_M, "bands_4g": cfg.BANDS_4G, "bands_5g": cfg.BANDS_5G,
         "note": "detail pages dir may also hold pages of an archived earlier scenario"}
    (cfg.DATA / "raw" / "manifest.json").write_text(json.dumps(m, indent=1), encoding="utf-8")


if __name__ == "__main__":
    print("A. cap test:", json.dumps(cap_test(), indent=1))
    print("B. sensitivity:", json.dumps(sensitivity(), indent=1))
    manifest()
    print("manifest written")
