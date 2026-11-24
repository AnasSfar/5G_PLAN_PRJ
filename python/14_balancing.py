"""Step 14 (phase 2) - Load balancing: only distance vs traffic balancing vs RRH-number balancing.

For every pool case of config.K_CASES (normal / few / many; the active pools of each K come from the
phase-1 backward elimination) it runs:
  delay   Minimise Delay (phase 1): nearest possible pool;
  traffic review steps a-d: balance the traffic (MBph) at the peak hour;
  count   review steps a, b, e, f: balance the number of RRHs per pool;
and, for the reference case, the other analyses of the review:
  - the traffic balancing repeated at every hour (how many RRHs would change pool, review 2b);
  - every RRH residential / every RRH office (review 1b, 2c).
Outputs in phase2/data/: assignment_<case>.csv, pools_<case>.csv, hour_dependence.csv,
single_profile.csv, summary.json.
"""
import json

import numpy as np
import pandas as pd

import config as cfg
import p2_lib as P

ALGOS = ["delay", "traffic", "count"]


def stats(a, D, T, h, m):
    served = a >= 0
    d = D[np.arange(len(a)), np.maximum(a, 0)][served]
    PL = P.pool_load(a, T, m)
    cnt = P.rrh_count(a, m)
    return {"served": int(served.sum()), "unserved": int((~served).sum()),
            "mean_km": float(d.mean()), "max_km": float(d.max()), "mean_rtt_us": float(cfg.rtt_us(d).mean()),
            "max_rtt_us": float(cfg.rtt_us(d).max()),
            "load_at_h": PL[:, h - 1].round(0).tolist(), "load_cv_at_h": P.cv(PL[:, h - 1]),
            "load_max_at_h": float(PL[:, h - 1].max()), "load_min_at_h": float(PL[:, h - 1].min()),
            "avg_capacity": PL.mean(axis=1).round(0).tolist(), "avg_capacity_cv": P.cv(PL.mean(axis=1)),
            "rrh_count": cnt.tolist(), "count_cv": P.cv(cnt), "count_min": int(cnt.min()), "count_max": int(cnt.max())}


def main():
    rrhs, cand, sets = P.load_scenario()
    by_id = {p["pool_id"]: p for p in cand}
    tr = pd.read_csv(cfg.P2_DATA / "rrh_traffic.csv")
    T = tr[[f"h{h:02d}" for h in cfg.HOURS]].to_numpy()
    h = json.loads((cfg.P2_DATA / "traffic.json").read_text(encoding="utf-8"))["peak_hour"]
    summary = {"peak_hour": h, "d_max_km": cfg.d_max_km(), "max_rtt_us": cfg.MAX_RTT_US, "cases": {}}

    for case, K in cfg.K_CASES.items():
        pools = [by_id[q] for q in sets[K]]
        m = len(pools)
        D, ok = P.possible_pools(rrhs, pools, cfg.d_max_km())
        w = T[:, h - 1]
        a = {"delay": P.delay_only(D, ok), "traffic": P.balance(D, ok, w, "traffic"),
             "count": P.balance(D, ok, w, "count")}
        n_opt = ok.sum(axis=1)
        res = {"K": K, "pools": [p["pool_id"] for p in pools], "single_option": int((n_opt == 1).sum()),
               "mean_options": float(n_opt.mean())}
        for alg in ALGOS:
            res[alg] = stats(a[alg], D, T, h, m)
            res[alg]["moved_vs_delay"] = int((a[alg] != a["delay"]).sum())
        summary["cases"][case] = res

        rows = []
        for i, r in enumerate(rrhs):
            row = {"rrh_id": r["rrh_id"], "traffic": r["traffic"], "peak_mbph": tr.peak_mbph[i],
                   "n_options": int(n_opt[i]), "options": " ".join(pools[j]["pool_id"] for j in np.flatnonzero(ok[i]))}
            for alg in ALGOS:
                j = a[alg][i]
                row[f"pool_{alg}"] = pools[j]["pool_id"] if j >= 0 else "UNSERVED"
                row[f"d_km_{alg}"] = round(float(D[i, j]), 3) if j >= 0 else None
            rows.append(row)
        pd.DataFrame(rows).to_csv(cfg.P2_DATA / f"assignment_{case}.csv", index=False)
        prow = []
        for j, p in enumerate(pools):
            pr = {"pool_id": p["pool_id"], "site_rrh": p["site_rrh"], "lat": p["lat"], "lon": p["lon"]}
            for alg in ALGOS:
                pr[f"rrhs_{alg}"] = res[alg]["rrh_count"][j]
                pr[f"load_h{h}_{alg}"] = res[alg]["load_at_h"][j]
                pr[f"avg_capacity_{alg}"] = res[alg]["avg_capacity"][j]
            prow.append(pr)
        pd.DataFrame(prow).to_csv(cfg.P2_DATA / f"pools_{case}.csv", index=False)

        if case != cfg.K_REFERENCE:
            continue
        # review 2b: traffic balancing at every hour vs the one adopted at the peak hour
        hrows = []
        for hh in cfg.HOURS:
            ah = P.balance(D, ok, T[:, hh - 1], "traffic")
            PLh = P.pool_load(ah, T, m)
            hrows.append({"hour": hh, "changed_vs_peak_hour": int((ah != a["traffic"]).sum()),
                          "load_cv_own_hour": P.cv(PLh[:, hh - 1]),
                          "load_cv_with_adopted": P.cv(P.pool_load(a["traffic"], T, m)[:, hh - 1]),
                          "load_cv_delay_only": P.cv(P.pool_load(a["delay"], T, m)[:, hh - 1])})
        pd.DataFrame(hrows).to_csv(cfg.P2_DATA / "hour_dependence.csv", index=False)

        # review 1b / 2c: every RRH residential, every RRH office, real case (peak hour)
        peak = tr.peak_mbph.to_numpy()
        srows = []
        for prof in ("residential", "office", "real"):
            Tp = T if prof == "real" else P.traffic_matrix(peak, tr.traffic, force=prof)
            ap = P.balance(D, ok, Tp[:, h - 1], "traffic")
            for alg, aa in (("delay", a["delay"]), ("traffic", ap)):
                PL = P.pool_load(aa, Tp, m)
                for j, p in enumerate(pools):
                    srows.append({"profile": prof, "algorithm": alg, "pool_id": p["pool_id"],
                                  "rrhs": int((aa == j).sum()), "load_peak_hour": PL[j, h - 1]})
            res.setdefault("single_profile_moved", {})[prof] = int((ap != a["traffic"]).sum())
        pd.DataFrame(srows).to_csv(cfg.P2_DATA / "single_profile.csv", index=False)

    (cfg.P2_DATA / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"peak hour {h}:00, d_max {cfg.d_max_km():.0f} km")
    for case, res in summary["cases"].items():
        for alg in ALGOS:
            s = res[alg]
            print(f"{case:6s} K={res['K']:2d} {alg:7s} CV@{h} {s['load_cv_at_h']:.2f}  load {s['load_min_at_h']:,.0f}-"
                  f"{s['load_max_at_h']:,.0f}  RRHs/pool {s['count_min']}-{s['count_max']}  mean d {s['mean_km']:.2f} km"
                  f"  max {s['max_km']:.1f}  moved {s['moved_vs_delay']}  unserved {s['unserved']}")


if __name__ == "__main__":
    main()
