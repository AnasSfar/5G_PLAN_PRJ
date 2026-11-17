"""Step 9 (week 2) - BBU pools and load balancing.

For each K case (few / normal / many pools):
  1. place K pools with farthest-first k-center (candidates = every core RRH);
  2. list, for every RRH, the pools within D_MAX_KM (fronthaul delay limit);
  3. assign RRHs with three strategies:
       - delay only : nearest pool (baseline, output of the delay algorithm);
       - algorithm A: load balancing by traffic (Mbps) at the balancing hour;
       - algorithm B: load balancing by number of RRHs;
  4. compute every output asked in the phase-2 review and draw the figures.

Needs json/week2/rrh_traffic.json (run 08_traffic.py first).
Outputs: json/week2/balancing_<case>.json, json/week2/summary.json, img/week2/*.png
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import config as cfg
import cran

C_DELAY, C_A, C_B = "#1f1fbf", "#1f8fbf", "#2ee08a"    # colours close to the thesis figures
LABELS = {"delay": "Delay only (nearest pool)", "A": "Alg. A: traffic balancing",
          "B": "Alg. B: RRH-number balancing"}
COLS = {"delay": C_DELAY, "A": C_A, "B": C_B}


# ----------------------------------------------------------------------------- algorithms
def assign_delay(D, ok):
    """Nearest pool. Unserved RRHs (no pool within D_MAX) get -1."""
    a = np.argmin(D, axis=1)
    a[~ok.any(1)] = -1
    return a


def first_iteration(ok, w):
    """Step b: RRHs with exactly one possible pool are assigned to it. Returns assignment + load."""
    n_opt = ok.sum(1)
    a = np.full(len(ok), -1)
    single = n_opt == 1
    a[single] = np.argmax(ok[single], axis=1)
    load = np.bincount(a[single], weights=w[single], minlength=ok.shape[1]).astype(float)
    return a, load, n_opt


def assign_balanced(D, ok, w, by_count=False):
    """Load balancing (Figure 3.6 of the thesis).

    by_count=False -> algorithm A: w is the traffic of each RRH at the balancing hour; the order of
        the second iteration is (number of possible pools ascending, traffic descending, distance to
        the nearest possible pool ascending), so the constrained and heavy RRHs are placed first.
    by_count=True  -> algorithm B: the load of a pool is its number of RRHs; order = number of
        possible pools ascending (step e), ties by distance to the nearest pool.
    Each RRH goes to the possible pool with the lowest current load; ties -> the closest pool.
    """
    weight = np.ones(len(w)) if by_count else np.asarray(w, float)
    a, load, n_opt = first_iteration(ok, weight)
    todo = np.where(n_opt > 1)[0]
    dnear = np.where(ok, D, np.inf).min(1)
    if by_count:
        order = todo[np.lexsort((dnear[todo], n_opt[todo]))]
    else:
        order = todo[np.lexsort((dnear[todo], -weight[todo], n_opt[todo]))]
    for i in order:
        cand = np.where(ok[i])[0]
        best = cand[np.lexsort((D[i, cand], load[cand]))[0]]
        a[i] = best
        load[best] += weight[i]
    return a


# ----------------------------------------------------------------------------- metrics
def pool_load(a, T, K):
    """Pool x hour traffic (Mbps). Unserved RRHs (a = -1) are left out."""
    m = a >= 0
    L = np.zeros((K, T.shape[1]))
    np.add.at(L, a[m], T[m])
    return L


def stats(v):
    v = np.asarray(v, float)
    return {"mean": float(v.mean()), "std": float(v.std()), "max": float(v.max()), "min": float(v.min()),
            "cv": float(v.std() / v.mean()) if v.mean() else 0.0}


def link_dist(a, D):
    m = a >= 0
    return D[np.where(m)[0], a[m]]


# ----------------------------------------------------------------------------- figures
def bars(ax, groups, labels, colours, ylab, K):
    n = len(groups)
    wdt = 0.8 / n
    xs = np.arange(1, K + 1)
    for j, (g, lab, c) in enumerate(zip(groups, labels, colours)):
        ax.bar(xs - 0.4 + wdt * (j + 0.5), g, wdt, label=lab, color=c, edgecolor="black", lw=0.3)
    ax.set_xticks(xs); ax.set_xlabel("BBU pool index"); ax.set_ylabel(ylab)
    ax.grid(axis="y", alpha=0.3); ax.set_xlim(0.4, K + 0.6)
    if n > 1:
        ax.legend(fontsize=7.5)


def save(fig, name):
    fig.tight_layout(); fig.savefig(cfg.FIGS / name, dpi=200); plt.close(fig)


# ----------------------------------------------------------------------------- one K case
def run_case(case, K, x, y, T, prof_of, peak, hb, chosen, draw):
    pools = chosen[:K]
    D = cran.distance_matrix(x, y, pools)
    ok = D <= cfg.D_MAX_KM
    served = ok.any(1)
    n_opt = ok.sum(1)
    h = hb - 1                                           # column index of the balancing hour

    prof = {k: np.array(v) for k, v in cfg.PROFILES.items()}
    T_res = peak[:, None] * prof["residential"][None, :]
    T_off = peak[:, None] * prof["office"][None, :]

    a = {"delay": assign_delay(D, ok),
         "A": assign_balanced(D, ok, T[:, h]),
         "B": assign_balanced(D, ok, T[:, h], by_count=True)}
    L = {k: pool_load(v, T, K) for k, v in a.items()}
    cnt = {k: np.bincount(v[v >= 0], minlength=K) for k, v in a.items()}
    dist = {k: link_dist(v, D) for k, v in a.items()}

    # hour dependence of algorithm A: re-run at every hour, compare with the balancing hour
    changes = {}
    for hh in cfg.HOURS:
        ah = assign_balanced(D, ok, T[:, hh - 1])
        changes[hh] = int((ah != a["A"]).sum())

    # all residential / all office: before (delay only) and after (algorithm A) balancing
    a_res = assign_balanced(D, ok, T_res[:, h]); a_off = assign_balanced(D, ok, T_off[:, h])
    homog = {
        "before": {"real": L["delay"][:, h], "res": pool_load(a["delay"], T_res, K)[:, h],
                   "off": pool_load(a["delay"], T_off, K)[:, h]},
        "after": {"real": L["A"][:, h], "res": pool_load(a_res, T_res, K)[:, h],
                  "off": pool_load(a_off, T_off, K)[:, h]},
        "after_count": {"real": cnt["A"], "res": np.bincount(a_res[a_res >= 0], minlength=K),
                        "off": np.bincount(a_off[a_off >= 0], minlength=K)},
        "changed_vs_real": {"res": int((a_res != a["A"]).sum()), "off": int((a_off != a["A"]).sum())},
    }

    bins = np.arange(0, np.ceil(cfg.D_MAX_KM) + 1)
    hist = {k: np.histogram(v, bins=bins)[0] for k, v in dist.items()}

    res = {
        "K": K, "pool_rrh_index": [int(p) for p in pools],
        "covering_radius_km": float(D.min(1).max()),
        "unserved": int((~served).sum()), "single_option": int((n_opt == 1).sum()),
        "mean_options": float(n_opt[served].mean()),
        "options_hist": np.bincount(n_opt, minlength=K + 1).tolist(),
        "balancing_hour": hb,
        "rrh_count": {k: v.tolist() for k, v in cnt.items()},
        "rrh_count_stats": {k: stats(v) for k, v in cnt.items()},
        "load_at_hour_mbps": {k: {hh: L[k][:, hh - 1].round(1).tolist() for hh in cfg.REPORT_HOURS + [hb]}
                              for k in L},
        "load_stats_balancing_hour": {k: stats(L[k][:, h]) for k in L},
        "load_stats_by_hour": {k: {hh: stats(L[k][:, hh - 1]) for hh in cfg.REPORT_HOURS + [hb]} for k in L},
        "avg_capacity_stats": {k: stats(L[k].mean(1)) for k in L},
        "peak_capacity_stats": {k: stats(L[k].max(1)) for k in L},
        "distance_km": {k: {"mean": float(v.mean()), "std": float(v.std()), "max": float(v.max()),
                            "p95": float(np.percentile(v, 95))} for k, v in dist.items()},
        "rtt_us": {k: {"mean": float(cran.rtt_us(v).mean()), "std": float(cran.rtt_us(v).std())}
                   for k, v in dist.items()},
        "distance_hist": {k: v.tolist() for k, v in hist.items()},
        "changes_vs_balancing_hour": changes,
        "moved_from_delay": {k: int((a[k] != a["delay"]).sum()) for k in ("A", "B")},
        "homogeneous": {s: {k: (np.asarray(v).round(1).tolist()) for k, v in d.items()}
                        for s, d in homog.items() if s != "changed_vs_real"},
        "homogeneous_changed_vs_real": homog["changed_vs_real"],
        "homogeneous_stats": {s: {k: stats(v) for k, v in homog[s].items()} for s in ("before", "after")},
    }

    if not draw:
        return res, a, pools

    tag = f"_{case}"
    # map of pools and assignments (three strategies)
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.6))
    cmap = plt.get_cmap("tab20", K)
    for ax, k in zip(axs, ("delay", "A", "B")):
        m = a[k] >= 0
        ax.scatter(x[m], y[m], s=3, c=[cmap(i % 20) for i in a[k][m]])
        ax.scatter(x[~m], y[~m], s=8, c="k", marker="x", label="unserved")
        ax.scatter(x[pools], y[pools], s=70, marker="s", c="red", edgecolor="k", zorder=3)
        for j, p in enumerate(pools):
            ax.annotate(str(j + 1), (x[p], y[p]), fontsize=7, ha="center", va="center", color="white",
                        zorder=4, weight="bold")
        ax.set_title(LABELS[k], fontsize=9); ax.set_aspect("equal")
        ax.set_xlim(-15.5, 15.5); ax.set_ylim(-15.5, 15.5); ax.set_xlabel("x [km]")
    axs[0].set_ylabel("y [km]")
    save(fig, f"map_assign{tag}.png")

    # 1a: load per pool, delay only, at 8:00, 15:00, 21:00 (three figures)
    ymax = max(L["delay"][:, hh - 1].max() for hh in cfg.REPORT_HOURS) / 1000 * 1.08
    for hh in cfg.REPORT_HOURS:
        fig, ax = plt.subplots(figsize=(6.6, 2.9))
        bars(ax, [L["delay"][:, hh - 1] / 1000], ["delay only"], [C_DELAY], "Pool load [Gbps]", K)
        ax.set_ylim(0, ymax); ax.set_title(f"{hh:02d}:00", fontsize=9)
        save(fig, f"1a_load_{hh:02d}h{tag}.png")

    # 1a combined: the three hours side by side (report)
    fig, axs = plt.subplots(1, 3, figsize=(12, 2.9), sharey=True)
    for ax, hh, t in zip(axs, cfg.REPORT_HOURS, "abc"):
        bars(ax, [L["delay"][:, hh - 1] / 1000], ["delay only"], [C_DELAY], "", K)
        ax.set_title(f"({t}) {hh:02d}:00", fontsize=9)
        ax.tick_params(axis="x", labelsize=7)
    axs[0].set_ylabel("Pool load [Gbps]")
    save(fig, f"1a_load_3h{tag}.png")

    # 1b: all residential / all office / real, delay only, balancing hour
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    hb_ = homog["before"]
    bars(ax, [hb_["res"] / 1000, hb_["off"] / 1000, hb_["real"] / 1000],
         ["All residential", "All office", "Real mix"], ["#2e9e44", "#d62728", C_DELAY], "Pool load [Gbps]", K)
    save(fig, f"1b_homog_before{tag}.png")

    # 2a: number of RRHs per pool, three strategies
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    bars(ax, [cnt["delay"], cnt["A"], cnt["B"]], [LABELS[k] for k in ("delay", "A", "B")],
         [C_DELAY, C_A, C_B], "Number of RRHs", K)
    save(fig, f"2a_rrh_per_pool{tag}.png")

    # 2a bis: load per pool at the balancing hour, three strategies
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    bars(ax, [L[k][:, h] / 1000 for k in ("delay", "A", "B")], [LABELS[k] for k in ("delay", "A", "B")],
         [C_DELAY, C_A, C_B], f"Pool load at {hb:02d}:00 [Gbps]", K)
    save(fig, f"2a_load_per_pool{tag}.png")

    # 2b: RRHs that change pool when algorithm A is run at another hour
    fig, ax = plt.subplots(figsize=(6.8, 2.8))
    ax.bar(cfg.HOURS, [changes[hh] for hh in cfg.HOURS], color=C_A, edgecolor="black", lw=0.3)
    ax.set_xticks(cfg.HOURS); ax.set_xlabel("Hour used for balancing"); ax.grid(axis="y", alpha=0.3)
    ax.set_ylabel(f"RRHs in another pool\nthan at {hb:02d}:00", fontsize=9)
    save(fig, f"2b_changes_by_hour{tag}.png")

    # 2c: balancing when all RRHs are residential / office (after algorithm A)
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.2))
    ha = homog["after"]
    bars(axs[0], [ha["res"] / 1000, ha["off"] / 1000, ha["real"] / 1000],
         ["All residential", "All office", "Real mix"], ["#2e9e44", "#d62728", C_A],
         f"Pool load at {hb:02d}:00 [Gbps]", K)
    hc = homog["after_count"]
    bars(axs[1], [hc["res"], hc["off"], hc["real"]], ["All residential", "All office", "Real mix"],
         ["#2e9e44", "#d62728", C_A], "Number of RRHs", K)
    save(fig, f"2c_homog_after{tag}.png")

    # 2d: share of RRHs per fronthaul distance band (like fig 4.3)
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    n_srv = served.sum()
    nb = len(bins) - 1
    wdt = 0.8 / 3
    for j, k in enumerate(("delay", "A", "B")):
        ax.bar(np.arange(nb) - 0.4 + wdt * (j + 0.5), hist[k] / n_srv * 100, wdt, color=COLS[k],
               label=LABELS[k], edgecolor="black", lw=0.3)
    ax.set_xticks(np.arange(nb)); ax.set_xticklabels([f"]{int(b)},{int(b) + 1}]" for b in bins[:-1]],
                                                     rotation=90, fontsize=8)
    ax.set_xlabel("Fronthaul distance [km]"); ax.set_ylabel("Share of RRHs [%]")
    ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=7.5)
    save(fig, f"2d_distance_hist{tag}.png")

    # 2e: average capacity per pool over 24 h (like fig 4.4)
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    bars(ax, [L[k].mean(1) / 1000 for k in ("delay", "A", "B")], [LABELS[k] for k in ("delay", "A", "B")],
         [C_DELAY, C_A, C_B], "Average capacity [Gbps]", K)
    save(fig, f"2e_avg_capacity{tag}.png")
    return res, a, pools


def main():
    rrhs, x, y = cran.load_core_rrhs()
    tr = json.loads((cfg.RESULTS / "rrh_traffic.json").read_text(encoding="utf-8"))
    assert [r["rrh_id"] for r in rrhs] == [r["rrh_id"] for r in tr["rrhs"]]
    prof_of = np.array([r["profile"] for r in tr["rrhs"]])
    peak = np.array([r["peak_mbps"] for r in tr["rrhs"]])
    prof = {k: np.array(v) for k, v in cfg.PROFILES.items()}
    T = np.vstack([peak[i] * prof[prof_of[i]] for i in range(len(rrhs))])
    hb = tr["hour_max_sum_of_profiles"]

    chosen, radius = cran.farthest_first(x, y, max(cfg.K_SWEEP))

    # K sweep: covering radius and served share
    sweep = []
    for K in cfg.K_SWEEP:
        D = cran.distance_matrix(x, y, chosen[:K])
        ok = D <= cfg.D_MAX_KM
        sweep.append({"K": K, "radius_km": radius[K - 1], "unserved": int((~ok.any(1)).sum()),
                      "single": int((ok.sum(1) == 1).sum()), "mean_nearest_km": float(D.min(1).mean())})
    fig, ax1 = plt.subplots(figsize=(6.8, 3.2))
    ks = [s["K"] for s in sweep]
    ax1.plot(ks, [s["radius_km"] for s in sweep], "o-", ms=3, color=C_DELAY, label="Covering radius (max distance)")
    ax1.plot(ks, [s["mean_nearest_km"] for s in sweep], "s-", ms=3, color=C_A, label="Mean distance to nearest pool")
    ax1.axhline(cfg.D_MAX_KM, color="red", ls="--", lw=1, label=f"D_max = {cfg.D_MAX_KM:.0f} km")
    for name, K in cfg.K_CASES.items():
        ax1.axvline(K, color="grey", ls=":", lw=0.8)
        ax1.text(K + 0.3, 1.2, name, fontsize=7.5, rotation=90, va="bottom")
    ax1.set_xlabel("Number of BBU pools K"); ax1.set_ylabel("Distance [km]"); ax1.grid(alpha=0.3)
    ax2 = ax1.twinx()
    ax2.bar(ks, [s["unserved"] / len(x) * 100 for s in sweep], color="orange", alpha=0.35, label="Unserved RRHs [%]")
    ax2.set_ylabel("Unserved RRHs [%]")
    h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper right", bbox_to_anchor=(0.98, 0.98))
    ax1.set_ylim(0, 21)
    save(fig, "k_sweep.png")

    summary = {"n_rrh": len(x), "d_max_km": cfg.D_MAX_KM, "max_rtt_us": cfg.MAX_RTT_US,
               "balancing_hour": hb, "k_sweep": sweep, "cases": {}}
    assign_out = {}
    for case, K in cfg.K_CASES.items():
        res, a, pools = run_case(case, K, x, y, T, prof_of, peak, hb, chosen, draw=True)
        summary["cases"][case] = res
        assign_out[case] = {k: v.tolist() for k, v in a.items()}
        (cfg.RESULTS / f"balancing_{case}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        s = res["load_stats_balancing_hour"]; c = res["rrh_count_stats"]; d = res["distance_km"]
        print(f"\n== {case} K={K}: unserved {res['unserved']}, single {res['single_option']}, "
              f"mean options {res['mean_options']:.2f}")
        for k in ("delay", "A", "B"):
            print(f"  {k:5s} load@{hb}h mean {s[k]['mean']/1000:7.2f} std {s[k]['std']/1000:6.2f} "
                  f"max {s[k]['max']/1000:7.2f} min {s[k]['min']/1000:6.2f} Gbps | RRHs std {c[k]['std']:6.1f} "
                  f"max {c[k]['max']:.0f} min {c[k]['min']:.0f} | dist mean {d[k]['mean']:.2f} max {d[k]['max']:.2f}")
        print("  moved from delay:", res["moved_from_delay"], " changes by hour:",
              {hh: res["changes_vs_balancing_hour"][hh] for hh in (8, 12, 15, 21, 22)})

    # K comparison figure: CV of the pool load at the balancing hour, three strategies, three K
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.2))
    cases = list(cfg.K_CASES)
    xs = np.arange(len(cases)); wdt = 0.8 / 3
    for j, k in enumerate(("delay", "A", "B")):
        axs[0].bar(xs - 0.4 + wdt * (j + 0.5),
                   [summary["cases"][c]["load_stats_balancing_hour"][k]["cv"] * 100 for c in cases], wdt,
                   color=COLS[k], label=LABELS[k], edgecolor="black", lw=0.3)
        axs[1].bar(xs - 0.4 + wdt * (j + 0.5), [summary["cases"][c]["distance_km"][k]["mean"] for c in cases],
                   wdt, color=COLS[k], label=LABELS[k], edgecolor="black", lw=0.3)
    for ax in axs:
        ax.set_xticks(xs); ax.set_xticklabels([f"{c} (K={cfg.K_CASES[c]})" for c in cases])
        ax.grid(axis="y", alpha=0.3)
    axs[0].set_ylabel(f"CV of pool load at {hb:02d}:00 [%]"); axs[1].set_ylabel("Mean fronthaul distance [km]")
    h_, l_ = axs[0].get_legend_handles_labels()
    fig.legend(h_, l_, loc="upper center", ncol=3, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(cfg.FIGS / "k_comparison.png", dpi=200); plt.close(fig)

    (cfg.RESULTS / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    (cfg.RESULTS / "assignments.json").write_text(json.dumps(assign_out), encoding="utf-8")


if __name__ == "__main__":
    main()
