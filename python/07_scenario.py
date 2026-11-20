"""Step 7 (phase 1) - Build the simulation scenario.

  1. draw N_RRH_REAL real core RRHs from json/rrh_master.json (None = all of them);
  2. add N_SYNTHETIC synthetic RRHs (uniform in the box, >= SYNTH_MIN_DIST_M from any RRH, id SYNxxx);
  3. give every RRH a traffic pattern (residential / office / mixed), "random" or "geo";
  4. choose N_POOL_CANDIDATES candidate BBU-pool sites among the real RRHs with farthest-first k-center.
     The candidate sites are computed once on the real RRHs and saved, so adding synthetic RRHs never
     moves the pools (review, item 1a: "fixing the possible positions").

Output: phase1/data/scenario.json (+ rrhs.csv, pool_candidates.csv).
Command-line options override config.py for quick tests, e.g.  python 07_scenario.py --n-synth 100
"""
import argparse
import json

import pandas as pd

import config as cfg
import p1_lib as L


def build(n_real=cfg.N_RRH_REAL, n_synth=cfg.N_SYNTHETIC, mode=cfg.TRAFFIC_MODE, shares=None,
          pools=None):
    core = L.load_core()
    rrhs = L.sample_real(core, n_real, cfg.RRH_SAMPLE_SEED)
    if pools is None:
        pools = L.farthest_first(rrhs, cfg.N_POOL_CANDIDATES, cfg.POOL_MIN_DIST_KM)
    rrhs = L.add_synthetic(rrhs, n_synth, cfg.SYNTH_MIN_DIST_M, cfg.SYNTH_SEED)
    L.assign_traffic(rrhs, mode, shares or cfg.TRAFFIC_SHARES, cfg.TRAFFIC_SEED, core)
    params = {"n_real": len([r for r in rrhs if not r["is_synthetic"]]), "n_synthetic": n_synth,
              "traffic_mode": mode, "traffic_shares": shares or cfg.TRAFFIC_SHARES,
              "sample_seed": cfg.RRH_SAMPLE_SEED, "synth_seed": cfg.SYNTH_SEED,
              "n_pool_candidates": len(pools), "pool_min_dist_km": cfg.POOL_MIN_DIST_KM,
              "bbox_wsen": cfg.BBOX, "centre": [cfg.CENTER_LAT, cfg.CENTER_LON]}
    return {"params": params, "rrhs": rrhs, "pools": pools}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-real", type=int, default=cfg.N_RRH_REAL)
    ap.add_argument("--n-synth", type=int, default=cfg.N_SYNTHETIC)
    ap.add_argument("--mode", default=cfg.TRAFFIC_MODE, choices=["geo", "random"])
    a = ap.parse_args()
    sc = build(a.n_real, a.n_synth, a.mode)
    (cfg.P1_DATA / "scenario.json").write_text(json.dumps(sc, indent=1, ensure_ascii=False), encoding="utf-8")
    df = pd.DataFrame(sc["rrhs"])
    df.drop(columns=["operators"]).to_csv(cfg.P1_DATA / "rrhs.csv", index=False)
    pd.DataFrame(sc["pools"]).to_csv(cfg.P1_DATA / "pool_candidates.csv", index=False)
    print(f"{len(df)} RRHs ({sc['params']['n_real']} real, {a.n_synth} synthetic), "
          f"{len(sc['pools'])} candidate pools, traffic mode {a.mode}")
    print(df["traffic"].value_counts().to_string())


if __name__ == "__main__":
    main()
