"""Step 10 (phase 1) - Robustness: synthetic RRHs, full real dataset, and consistency checks.

The candidate pools (and the K active pools chosen in step 8) stay fixed. For each variant the Minimise
Delay algorithm is run again, with the reference budget and with the strict one, and the invariants of
the algorithm are checked:
  - a served RRH is connected to its nearest pool, within d_max;
  - an RRH is unserved if and only if no pool is within d_max;
  - for every pool, categories 1 + 2 = RRHs assigned to it, and summed over pools 1 + 2 + 3 = all options.

Outputs: phase1/data/robustness.csv, phase1/figures/fig13_robustness_cdf.png, fig14_robustness_synthetic.png
"""
import importlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as cfg
import p1_lib as L

scen = importlib.import_module("07_scenario")
fig9 = importlib.import_module("09_figures")       # shared plot style


def check(rrhs, pools, res):
    D, ok, a = res["D"], res["ok"], res["assign"]
    served = a >= 0
    assert np.array_equal(served, ok.any(axis=1)), "unserved <=> no pool within d_max"
    assert np.all(a[served] == np.argmin(D[served], axis=1)), "served RRH must use its nearest pool"
    assert np.all(D[served, a[served]] <= res["dmax"] + 1e-9), "assigned distance within d_max"
    c1, c2, c3 = L.categories(res, len(pools))
    for p in range(len(pools)):
        assert len(c1[p]) + len(c2[p]) == int(np.sum(a == p))
    assert sum(len(c1[p]) + len(c2[p]) + len(c3[p]) for p in range(len(pools))) == int(ok.sum())
    return True


def main():
    ref = json.loads((cfg.P1_DATA / "scenario.json").read_text(encoding="utf-8"))
    out = json.loads((cfg.P1_DATA / "results.json").read_text(encoding="utf-8"))
    pools = ref["pools"]; act = [p for p in pools if p["pool_id"] in out["active_pools"]]
    K = len(act); strict = min(cfg.RTT_SWEEP_US)

    variants = [("reference: 200 real", cfg.N_RRH_REAL, 0)]
    variants += [(f"200 real + {n} synthetic", cfg.N_RRH_REAL, n) for n in (50, 100, 200, 400)]
    variants += [("all 2,085 real", None, 0)]
    rows, dists = [], {}
    for name, n_real, n_syn in variants:
        sc = scen.build(n_real, n_syn, cfg.TRAFFIC_MODE, pools=pools)
        rrhs = sc["rrhs"]; syn = np.array([r["is_synthetic"] for r in rrhs])
        row = {"variant": name, "n_rrh": len(rrhs), "n_synthetic": int(syn.sum())}
        for rtt in (cfg.MAX_RTT_US, strict):
            res = L.minimise_delay(rrhs, act, cfg.d_max_km(rtt))
            check(rrhs, act, res)
            s = L.summary(res)
            tag = f"{int(rtt)}us"
            row.update({f"unserved_{tag}": s["unserved"],
                        f"unserved_synthetic_{tag}": int(np.sum((res["assign"] < 0) & syn)),
                        f"mean_rtt_{tag}": round(s["mean_rtt_us"], 2), f"std_rtt_{tag}": round(s["std_rtt_us"], 2),
                        f"max_rtt_{tag}": round(s["max_rtt_us"], 2),
                        f"single_option_{tag}": int(np.sum(res["n_opt"] == 1)),
                        f"mean_options_{tag}": round(float(res["n_opt"].mean()), 2)})
            if rtt == cfg.MAX_RTT_US:
                dists[name] = np.sort(res["D"].min(axis=1))
        hist = L.backward_elimination(rrhs, pools, cfg.d_max_km())
        row["k_selected_auto"] = L.choose_k(hist, cfg.KNEE_TOL)[0]
        row["checks"] = "passed"
        rows.append(row)
        print(name, "->", {k: v for k, v in row.items() if "unserved" in k or k == "k_selected_auto"})
    df = pd.DataFrame(rows)
    df.to_csv(cfg.P1_DATA / "robustness.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 4))
    cols = plt.get_cmap("Blues")(np.linspace(0.4, 1, 5))
    for (name, d), c in zip(dists.items(), list(cols) + ["#eb6834"]):
        lw = 2.2 if name.startswith("reference") else 1.3
        ax.step(d, np.arange(1, len(d) + 1) / len(d), where="post", lw=lw, color=c,
                label=f"{name} (mean {d.mean():.2f} km)")
    ax.set_xlabel(f"distance RRH - nearest active pool [km], K = {K}"); ax.set_ylabel("CDF")
    ax.set_xlim(0, 8); ax.set_ylim(0, 1.01)
    ax.set_title("Robustness: distance CDF with synthetic RRHs and with the full dataset", loc="left", fontsize=10)
    ax.legend(fontsize=7.5, loc="lower right")
    fig9.save(fig, "fig13_robustness_cdf.png")

    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
    syn_rows = df[df.variant.str.contains("synthetic") | df.variant.str.startswith("reference")]
    x = np.arange(len(syn_rows)); labels = [str(n) for n in syn_rows.n_synthetic]
    axs[0].bar(x - 0.2, syn_rows[f"unserved_{int(cfg.MAX_RTT_US)}us"], 0.38, color=fig9.CAT3[0], label=f"RTT <= {cfg.MAX_RTT_US:g} us")
    axs[0].bar(x + 0.2, syn_rows[f"unserved_{int(strict)}us"], 0.38, color=fig9.CAT3[1], label=f"RTT <= {strict:g} us")
    axs[0].set_xticks(x, labels); axs[0].set_xlabel("synthetic RRHs added"); axs[0].set_ylabel("unserved RRHs")
    axs[0].set_title(f"Unserved RRHs, K = {K} fixed pools", loc="left", fontsize=10); axs[0].legend(fontsize=7.5)
    axs[1].plot(x, syn_rows[f"mean_rtt_{int(cfg.MAX_RTT_US)}us"], "o-", color=fig9.CAT3[0])
    axs[1].set_xticks(x, labels); axs[1].set_xlabel("synthetic RRHs added"); axs[1].set_ylabel("mean round-trip delay [us]")
    axs[1].set_ylim(0, None)
    axs[1].set_title(f"Mean RTT (budget {cfg.MAX_RTT_US:g} us), K = {K}", loc="left", fontsize=10)
    fig9.save(fig, "fig14_robustness_synthetic.png")
    print(df.to_string())


if __name__ == "__main__":
    main()
