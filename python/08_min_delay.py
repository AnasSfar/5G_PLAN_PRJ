"""Step 8 (phase 1) - Minimise Delay algorithm and choice of the number of BBU pools.

Reads phase1/data/scenario.json (step 7) and:
  1. runs the Minimise Delay algorithm (thesis fig. 3.5, no capacity limit) with the 25 candidate pools;
  2. reduces the number of pools by backward elimination: remove, one by one, the pool whose removal
     raises the mean round-trip delay the least, never leaving an extra RRH unserved; the order of
     removal says which pools are the least relevant (review, item 1a);
  3. also evaluates the farthest-first prefixes (first K candidates = K-center solution) for comparison;
  4. repeats 2-3 for every delay budget in RTT_SWEEP_US (sensitivity);
  5. picks the active pools (K_ACTIVE = "auto": smallest K whose mean RTT is within KNEE_TOL of the
     25-pool value) and writes, for that K and for the 25 candidates:
       - the list of possible pools of every RRH, its best pool, distance and RTT (review 3d);
       - per pool, the three categories of RRHs (review 3c).

Outputs in phase1/data/: k_analysis.csv, assignment_K<k>.csv, assignment_K25.csv,
pool_categories_K<k>.csv, pool_categories_K25.csv, results.json.
"""
import json

import numpy as np
import pandas as pd

import config as cfg
import p1_lib as L


def assignment_table(rrhs, pools, res):
    rows = []
    for i, r in enumerate(rrhs):
        opts = np.flatnonzero(res["ok"][i])
        opts = opts[np.argsort(res["D"][i, opts])]                    # nearest first
        a = res["assign"][i]
        rows.append({
            "rrh_id": r["rrh_id"], "is_synthetic": r["is_synthetic"], "traffic": r["traffic"],
            "lat": r["lat"], "lon": r["lon"], "x_km": round(r["x"], 3), "y_km": round(r["y"], 3),
            "served": bool(a >= 0), "best_pool": pools[a]["pool_id"] if a >= 0 else "UNSERVED",
            "d_best_km": round(float(res["d"][i]), 3) if a >= 0 else None,
            "rtt_best_us": round(float(res["rtt"][i]), 2) if a >= 0 else None,
            "n_options": int(len(opts)),
            "options": " ".join(pools[p]["pool_id"] for p in opts),
            "options_d_km": " ".join(f"{res['D'][i, p]:.2f}" for p in opts),
            "nearest_pool_any": pools[int(np.argmin(res["D"][i]))]["pool_id"],
            "d_nearest_any_km": round(float(res["D"][i].min()), 3),
        })
    return pd.DataFrame(rows)


def category_table(rrhs, pools, res):
    c1, c2, c3 = L.categories(res, len(pools))
    ids = lambda lst: " ".join(rrhs[i]["rrh_id"] for i in lst)
    rows = []
    for p, pool in enumerate(pools):
        rows.append({"pool_id": pool["pool_id"], "site_rrh": pool["site_rrh"], "lat": pool["lat"],
                     "lon": pool["lon"], "n_only_option": len(c1[p]), "n_optimal_with_alternatives": len(c2[p]),
                     "n_possible_not_optimal": len(c3[p]), "n_assigned": len(c1[p]) + len(c2[p]),
                     "n_reachable": len(c1[p]) + len(c2[p]) + len(c3[p]),
                     "rrhs_only_option": ids(c1[p]), "rrhs_optimal_with_alternatives": ids(c2[p]),
                     "rrhs_possible_not_optimal": ids(c3[p])})
    return pd.DataFrame(rows)


def k_analysis(rrhs, pools):
    rows, hists = [], {}
    for rtt in cfg.RTT_SWEEP_US:
        dmax = cfg.d_max_km(rtt)
        hist = L.backward_elimination(rrhs, pools, dmax)
        hists[rtt] = hist
        prev = None
        for k, active, s in hist:
            removed = "" if prev is None else pools[(set(prev) - set(active)).pop()]["pool_id"]
            rows.append({"rtt_limit_us": rtt, "d_max_km": dmax, "method": "backward_elimination", "K": k,
                         "removed_pool": removed, "active_pools": " ".join(pools[q]["pool_id"] for q in active), **s})
            prev = active
        for k in range(1, len(pools) + 1):
            s = L.summary(L.minimise_delay(rrhs, pools[:k], dmax))
            rows.append({"rtt_limit_us": rtt, "d_max_km": dmax, "method": "farthest_first_prefix", "K": k,
                         "removed_pool": "", "active_pools": " ".join(p["pool_id"] for p in pools[:k]), **s})
    return pd.DataFrame(rows), hists


def run(sc, tag=""):
    rrhs, pools = sc["rrhs"], sc["pools"]
    out = cfg.P1_DATA
    kdf, hists = k_analysis(rrhs, pools)
    kdf.to_csv(out / f"k_analysis{tag}.csv", index=False)

    hist = hists[cfg.MAX_RTT_US]
    if cfg.K_ACTIVE == "auto":
        k_sel, active, s_sel = L.choose_k(hist, cfg.KNEE_TOL)
    else:
        k_sel, active, s_sel = next(h for h in hist if h[0] == int(cfg.K_ACTIVE))
    active = sorted(active)
    k_min = hist[-1][0]
    dmax = cfg.d_max_km()

    results = {"max_rtt_us": cfg.MAX_RTT_US, "d_max_km": dmax, "fibre_km_per_ms": cfg.FIBRE_KM_PER_MS,
               "route_factor": cfg.ROUTE_FACTOR, "n_rrh": len(rrhs),
               "n_synthetic": sum(r["is_synthetic"] for r in rrhs), "n_candidates": len(pools),
               "k_selected": k_sel, "k_min_all_served": k_min, "knee_tol": cfg.KNEE_TOL,
               "active_pools": [pools[q]["pool_id"] for q in active],
               "removal_order": [r for r in kdf[(kdf.method == "backward_elimination") &
                                                 (kdf.rtt_limit_us == cfg.MAX_RTT_US)].removed_pool if r],
               "k_min_by_rtt": {str(int(r)): hists[r][-1][0] for r in cfg.RTT_SWEEP_US},
               "unserved_with_25_by_rtt": {str(int(r)): hists[r][0][2]["unserved"] for r in cfg.RTT_SWEEP_US}}

    for label, act in (("K25", list(range(len(pools)))), (f"K{k_sel}", active)):
        sub = [pools[q] for q in act]
        res = L.minimise_delay(rrhs, sub, dmax)
        assignment_table(rrhs, sub, res).to_csv(out / f"assignment_{label}{tag}.csv", index=False)
        category_table(rrhs, sub, res).to_csv(out / f"pool_categories_{label}{tag}.csv", index=False)
        results[label] = L.summary(res)
        results[label]["single_option_rrhs"] = int(np.sum(res["n_opt"] == 1))
        results[label]["mean_options"] = float(res["n_opt"].mean())
    (out / f"results{tag}.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    return results


def main():
    sc = json.loads((cfg.P1_DATA / "scenario.json").read_text(encoding="utf-8"))
    res = run(sc)
    print(json.dumps({k: v for k, v in res.items() if k not in ("removal_order",)}, indent=1))
    print("removal order (least relevant first):", " ".join(res["removal_order"]))


if __name__ == "__main__":
    main()
