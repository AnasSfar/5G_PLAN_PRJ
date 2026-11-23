"""Step 14 (phase 2) - Load balancing: only distance vs traffic balancing vs RRH-number balancing.

For every pool case of config.K_CASES (normal / few / many; the active pools of each K come from the
phase-1 backward elimination) it runs:
  delay   Minimise Delay (phase 1): nearest possible pool;
  traffic review steps a-d: balance the traffic (GBph) at the balancing hour;
  count   review steps a, b, e, f: balance the number of RRHs per pool;
and, for the reference case, the extra analyses asked in the review:
  - the traffic balancing repeated at every hour (how many RRHs would change pool, review 2b);
  - the traffic balancing with every RRH residential / every RRH office (review 1b, 2c);
  - a distance-aware variant with a slack in km (extra, not in the review).
Outputs in phase2/data/: assignment_<case>.csv, pools_<case>.csv, hour_dependence.csv,
single_profile.csv, slack_sweep.csv, summary.json.
"""
import json

import numpy as np
import pandas as pd

import config as cfg
import p2_lib as P

ALGOS = ["delay", "traffic", "count"]


def run_case(rrhs, pools, T, h, force=None):
    D, ok = P.possible_pools(rrhs, pools, cfg.d_max_km())
    w = T[:, h - 1]
    a = {"delay": P.delay_only(D, ok), "traffic": P.balance(D, ok, w, "traffic"), "count": P.balance(D, ok, w, "count")}
    return D, ok, a


def stats(a, D, T, h, m):
    served = a >= 0
    d = D[np.arange(len(a)), np.maximum(a, 0)][served]
    PL = P.pool_load(a, T, m)
    g, g_all = P.mux_gain(a, T, m)
    cnt = P.rrh_count(a, m)
    return {"served": int(served.sum()), "unserved": int((~served).sum()),
            "mean_km": float(d.mean()), "max_km": float(d.max()), "mean_rtt_us": float(cfg.rtt_us(d).mean()),
            "max_rtt_us": float(cfg.rtt_us(d).max()),
            "load_at_h": PL[:, h - 1].round(2).tolist(), "load_cv_at_h": P.cv(PL[:, h - 1]),
            "load_max_at_h": float(PL[:, h - 1].max()), "load_min_at_h": float(PL[:, h - 1].min()),
            "avg_capacity": PL.mean(axis=1).round(2).tolist(), "avg_capacity_cv": P.cv(PL.mean(axis=1)),
            "peak_capacity_sum": float(PL.max(axis=1).sum()),
            "rrh_count": cnt.tolist(), "count_cv": P.cv(cnt), "count_min": int(cnt.min()), "count_max": int(cnt.max()),
            "mux_gain": [None if np.isnan(x) else round(float(x), 3) for x in g], "mux_gain_overall": g_all}


def main():
    rrhs, cand, sets = P.load_scenario()
    by_id = {p["pool_id"]: p for p in cand}
    tr = pd.read_csv(cfg.P2_DATA / "rrh_traffic.csv")
    T = tr[[f"h{h:02d}" for h in cfg.HOURS]].to_numpy()
    h = json.loads((cfg.P2_DATA / "traffic.json").read_text(encoding="utf-8"))["balance_hour"]
    summary = {"balance_hour": h, "d_max_km": cfg.d_max_km(), "max_rtt_us": cfg.MAX_RTT_US, "cases": {}}

    for case, K in cfg.K_CASES.items():
        pools = [by_id[q] for q in sets[K]]
        m = len(pools)
        D, ok, a = run_case(rrhs, pools, T, h)
        n_opt = ok.sum(axis=1)
        res = {"K": K, "pools": [p["pool_id"] for p in pools], "single_option": int((n_opt == 1).sum()),
               "mean_options": float(n_opt.mean())}
        for alg in ALGOS:
            res[alg] = stats(a[alg], D, T, h, m)
            res[alg]["moved_vs_delay"] = int((a[alg] != a["delay"]).sum())
        summary["cases"][case] = res

        rows = []
        for i, r in enumerate(rrhs):
            row = {"rrh_id": r["rrh_id"], "traffic": r["traffic"], "peak_gbph": tr.peak_gbph[i],
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
                pr[f"mux_gain_{alg}"] = res[alg]["mux_gain"][j]
            prow.append(pr)
        pd.DataFrame(prow).to_csv(cfg.P2_DATA / f"pools_{case}.csv", index=False)

        if case != cfg.K_REFERENCE:
            continue
        # review 2b: traffic balancing at every hour vs the one adopted at the balancing hour
        hrows = []
        for hh in cfg.HOURS:
            ah = P.balance(D, ok, T[:, hh - 1], "traffic")
            PLh = P.pool_load(ah, T, m)
            hrows.append({"hour": hh, "changed_vs_balance_hour": int((ah != a["traffic"]).sum()),
                          "load_cv_own_hour": P.cv(PLh[:, hh - 1]),
                          "load_cv_with_adopted": P.cv(P.pool_load(a["traffic"], T, m)[:, hh - 1]),
                          "load_cv_delay_only": P.cv(P.pool_load(a["delay"], T, m)[:, hh - 1])})
        pd.DataFrame(hrows).to_csv(cfg.P2_DATA / "hour_dependence.csv", index=False)

        # review 1b / 2c: every RRH residential, every RRH office, real case
        peak = tr.peak_gbph.to_numpy()
        srows = []
        for prof in ("residential", "office", "real"):
            Tp = T if prof == "real" else P.traffic_matrix(peak, tr.traffic, force=prof)
            hp = h
            ap = P.balance(D, ok, Tp[:, hp - 1], "traffic")
            for alg, aa in (("delay", a["delay"]), ("traffic", ap)):
                PL = P.pool_load(aa, Tp, m)
                for j, p in enumerate(pools):
                    srows.append({"profile": prof, "algorithm": alg, "pool_id": p["pool_id"],
                                  "rrhs": int((aa == j).sum()), "load_balance_hour": PL[j, hp - 1],
                                  "load_peak_hour": PL[j, int(np.argmax(Tp.sum(0)))],
                                  "network_peak_hour": int(np.argmax(Tp.sum(0))) + 1, "avg_capacity": PL[j].mean()})
            res.setdefault("single_profile_moved", {})[prof] = int((ap != a["traffic"]).sum())
        pd.DataFrame(srows).to_csv(cfg.P2_DATA / "single_profile.csv", index=False)

        # extra: distance-aware traffic balancing (slack over the nearest possible pool)
        krows = []
        for sl in cfg.SLACK_SWEEP_KM:
            asl = P.balance(D, ok, T[:, h - 1], "traffic", slack_km=sl)
            st = stats(asl, D, T, h, m)
            krows.append({"slack_km": sl, "load_cv_at_h": st["load_cv_at_h"], "mean_km": st["mean_km"],
                          "max_km": st["max_km"], "mean_rtt_us": st["mean_rtt_us"],
                          "moved_vs_delay": int((asl != a["delay"]).sum())})
        pd.DataFrame(krows).to_csv(cfg.P2_DATA / "slack_sweep.csv", index=False)

    (cfg.P2_DATA / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"balancing hour {h}:00, d_max {cfg.d_max_km():.0f} km")
    for case, res in summary["cases"].items():
        for alg in ALGOS:
            s = res[alg]
            print(f"{case:6s} K={res['K']:2d} {alg:7s} CV@{h} {s['load_cv_at_h']:.2f}  RRHs/pool {s['count_min']}-{s['count_max']}"
                  f"  mean d {s['mean_km']:.2f} km  max {s['max_km']:.1f}  moved {s['moved_vs_delay']}"
                  f"  Gmux {s['mux_gain_overall']:.2f}  unserved {s['unserved']}")


if __name__ == "__main__":
    main()
