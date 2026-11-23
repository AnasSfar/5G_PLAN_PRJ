"""Step 15 (phase 2) - Figures of the load balancing (review item in brackets).

Reads phase2/data/* (steps 13 and 14) and writes phase2/figures/:
  fig03_load_<hh>h        load per pool with the delay-only assignment at 8:00, 15:00, 21:00   [1a]
  fig03_load_3hours       the same three figures side by side (for the report)                  [1a]
  fig04_single_profile    load per pool: all residential / all office / real case               [1b]
  fig05_rrhs_per_pool     RRHs per pool: only distance / traffic balancing / RRH balancing      [2a]
  fig06_load_per_pool     load per pool at the balancing hour, three algorithms                  [2a]
  fig07_hour_dependence   RRHs that change pool if the balancing is done at another hour        [2b]
  fig08_single_profile_balanced  traffic balancing with all residential / all office / real     [2c]
  fig09_distance_bands    RRHs per 1 km fronthaul band, three algorithms (thesis fig. 4.3)      [2d]
  fig10_avg_capacity      average capacity per pool over 24 h, three algorithms (thesis fig. 4.4) [2e]
  fig11_mux_gain          multiplexing gain per pool (thesis fig. 4.5)                           [extra]
  fig12_k_comparison      normal / few / many pools                                              [final]
  fig13_maps              assignment maps of the three algorithms                                [extra]
  fig14_slack             distance-aware traffic balancing: balance vs distance                  [extra]
Figures 05, 09, 10 are also written for the few / many cases (suffix _few, _many).
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import config as cfg
import p2_lib as P
from p2_style import save, INK, INK2, TRAFFIC_COLORS

ALGOS = ["delay", "traffic", "count"]
AC, AL = cfg.ALGO_COLORS, cfg.ALGO_LABELS
S = json.loads((cfg.P2_DATA / "summary.json").read_text(encoding="utf-8"))
TR = json.loads((cfg.P2_DATA / "traffic.json").read_text(encoding="utf-8"))
H = S["balance_hour"]
HALF = cfg.SIDE_KM / 2


def grouped(ax, labels, series, colors, names, width=0.8):
    n = len(series); w = width / n; x = np.arange(len(labels))
    for k, (v, c, nm) in enumerate(zip(series, colors, names)):
        ax.bar(x + (k - (n - 1) / 2) * w, v, width=w * 0.9, color=c, label=nm, zorder=3)
    ax.set_xticks(x, labels, rotation=90 if len(labels) > 12 else 0, fontsize=8)
    ax.grid(axis="x", visible=False)


def case_data(case):
    pools = pd.read_csv(cfg.P2_DATA / f"pools_{case}.csv")
    asg = pd.read_csv(cfg.P2_DATA / f"assignment_{case}.csv")
    return pools, asg


def fig_load_hours(case):
    pools, asg = case_data(case)
    tr = pd.read_csv(cfg.P2_DATA / "rrh_traffic.csv")
    ids = list(pools.pool_id)
    loads = {}
    for hh in cfg.REPORT_HOURS:
        loads[hh] = np.array([tr[f"h{hh:02d}"][asg.pool_delay == p].sum() for p in ids])
    top = max(v.max() for v in loads.values()) * 1.12
    fig3, axs = plt.subplots(1, 3, figsize=(14, 3.8), sharey=True)
    for ax, hh in zip(axs, cfg.REPORT_HOURS):
        for target in (ax, None):
            if target is None:
                f, target = plt.subplots(figsize=(7.5, 3.6))
            v = loads[hh]
            target.bar(range(len(ids)), v, color=AC["delay"], width=0.7, zorder=3)
            target.axhline(v.mean(), color=INK2, ls=":", lw=1)
            target.text(-0.4, v.mean() + top * 0.02, f"mean {v.mean():.0f}", ha="left", fontsize=8, color=INK2)
            target.set_xticks(range(len(ids)), ids, rotation=90, fontsize=8); target.grid(axis="x", visible=False)
            target.set_ylim(0, top); target.set_xlabel("BBU pool")
            target.set_title(f"{hh}:00, total {v.sum() / 1000:.1f} TBph, CV {P.cv(v):.2f}", loc="left", fontsize=10)
            target.set_ylabel("load [GBph]")
            if target is not ax:
                save(f, f"fig03_load_{hh:02d}h.png")
                break
    fig3.suptitle(f"Load per BBU pool before balancing (only distance, K = {S['cases'][case]['K']})",
                  x=0.01, ha="left", fontsize=11)
    save(fig3, "fig03_load_3hours.png")


def fig_single_profile():
    sp = pd.read_csv(cfg.P2_DATA / "single_profile.csv")
    d = sp[sp.algorithm == "delay"]
    ids = list(d[d.profile == "real"].pool_id)
    cols = {"residential": TRAFFIC_COLORS["residential"], "office": TRAFFIC_COLORS["office"], "real": INK2}
    fig, axs = plt.subplots(2, 1, figsize=(12, 6.6))
    for ax, (col, ttl) in zip(axs, (("load_balance_hour", f"(a) {H}:00, balancing hour"),
                                    ("load_peak_hour", "(b) busiest hour of each case"))):
        ser, names = [], []
        for prof in ("residential", "office", "real"):
            g = d[d.profile == prof].set_index("pool_id").loc[ids]
            ser.append(g[col].to_numpy())
            lab = {"residential": "all residential", "office": "all office", "real": "real mix"}[prof]
            extra = f" ({int(g.network_peak_hour.iloc[0])}:00)" if col == "load_peak_hour" else ""
            names.append(lab + extra + f", total {g[col].sum() / 1000:.1f} TBph")
        grouped(ax, ids, ser, [cols[p] for p in ("residential", "office", "real")], names)
        ax.set_ylabel("load [GBph]"); ax.set_title(ttl, loc="left", fontsize=10); ax.legend(fontsize=8)
    axs[1].set_xlabel("BBU pool")
    fig.suptitle(f"Load per pool, only distance (K = {S['cases'][cfg.K_REFERENCE]['K']}): all residential, all office, real case",
                 x=0.01, ha="left", fontsize=11)
    save(fig, "fig04_single_profile.png")


def fig_per_pool(case, key, fname, ylabel, title):
    pools, _ = case_data(case)
    ser = [pools[f"{key}_{a}"].to_numpy() for a in ALGOS]
    fig, ax = plt.subplots(figsize=(12 if len(pools) > 10 else 8, 3.9))
    names = [f"{AL[a]} (CV {P.cv(v):.2f}, {v.min():.0f}-{v.max():.0f})" for a, v in zip(ALGOS, ser)]
    grouped(ax, list(pools.pool_id), ser, [AC[a] for a in ALGOS], names)
    ax.set_xlabel("BBU pool"); ax.set_ylabel(ylabel)
    ax.legend(fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.02), ncol=3)
    ax.set_title(title.format(K=S["cases"][case]["K"]), loc="left", fontsize=10, pad=26)
    save(fig, fname)


def fig_hour_dependence():
    hd = pd.read_csv(cfg.P2_DATA / "hour_dependence.csv")
    n = S["cases"][cfg.K_REFERENCE]["traffic"]["served"]
    fig, axs = plt.subplots(1, 2, figsize=(13, 3.9))
    ax = axs[0]
    ax.bar(hd.hour, hd.changed_vs_balance_hour, color=AC["traffic"], width=0.75, zorder=3)
    ax.set_xticks(cfg.HOURS[1::2]); ax.set_xlim(0.3, 24.7); ax.set_ylim(0, n)
    ax.axhline(n, color=INK2, ls=":", lw=1)
    ax.text(H, 4, "adopted", rotation=90, ha="center", va="bottom", fontsize=8, color=INK2)
    ax.set_xlabel("hour used for the traffic balancing"); ax.set_ylabel(f"RRHs in another pool (of {n})")
    ax.set_title(f"(a) RRHs that change pool vs the balancing at {H}:00", loc="left", fontsize=10)
    ax = axs[1]
    ax.plot(hd.hour, hd.load_cv_delay_only, "-o", ms=3, color=AC["delay"], lw=2, label="only distance")
    ax.plot(hd.hour, hd.load_cv_with_adopted, "-o", ms=3, color=AC["traffic"], lw=2,
            label=f"traffic balancing done at {H}:00 (adopted)")
    ax.plot(hd.hour, hd.load_cv_own_hour, "--", color=AC["traffic"], lw=1.4, label="balancing redone every hour")
    ax.set_xticks(cfg.HOURS[1::2]); ax.set_xlim(0.3, 24.7); ax.set_ylim(0, None)
    ax.set_xlabel("hour of the day"); ax.set_ylabel("CV of the pool load")
    ax.set_title("(b) Imbalance of the pool load during the day", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    save(fig, "fig07_hour_dependence.png")


def fig_single_profile_balanced():
    sp = pd.read_csv(cfg.P2_DATA / "single_profile.csv")
    t = sp[sp.algorithm == "traffic"]
    ids = list(t[t.profile == "real"].pool_id)
    cols = {"residential": TRAFFIC_COLORS["residential"], "office": TRAFFIC_COLORS["office"], "real": INK2}
    fig, axs = plt.subplots(1, 2, figsize=(14, 3.9), gridspec_kw=dict(width_ratios=[1.6, 1]))
    ser, names = [], []
    for prof in ("residential", "office", "real"):
        g = t[t.profile == prof].set_index("pool_id").loc[ids]
        ser.append(g.rrhs.to_numpy())
        names.append({"residential": "all residential", "office": "all office", "real": "real mix"}[prof])
    grouped(axs[0], ids, ser, [cols[p] for p in ("residential", "office", "real")], names)
    axs[0].set_xlabel("BBU pool"); axs[0].set_ylabel("RRHs per pool"); axs[0].legend(fontsize=8)
    axs[0].set_title(f"(a) RRHs per pool after traffic balancing at {H}:00", loc="left", fontsize=10)
    ax = axs[1]
    x = np.arange(3)
    for k, alg in enumerate(("delay", "traffic")):
        v = []
        for prof in ("residential", "office", "real"):
            g = sp[(sp.profile == prof) & (sp.algorithm == alg)].load_balance_hour.to_numpy()
            v.append(P.cv(g))
        ax.bar(x + (k - 0.5) * 0.38, v, width=0.34, color=AC[alg], label=AL[alg], zorder=3)
        for xi, vi in zip(x, v):
            ax.text(xi + (k - 0.5) * 0.38, vi + 0.02, f"{vi:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x, ["all residential", "all office", "real mix"]); ax.grid(axis="x", visible=False)
    ax.set_ylabel(f"CV of the pool load at {H}:00"); ax.legend(fontsize=8, loc="upper left")
    ax.set_ylim(0, 1.45)
    ax.set_title("(b) Imbalance before and after", loc="left", fontsize=10)
    save(fig, "fig08_single_profile_balanced.png")


def fig_distance_bands(case, fname):
    _, asg = case_data(case)
    top = int(np.ceil(cfg.d_max_km()))
    bins = np.arange(0, top + 1)
    ser = [np.histogram(asg[f"d_km_{a}"].dropna(), bins)[0] for a in ALGOS]
    fig, ax = plt.subplots(figsize=(11, 3.9))
    names = [f"{AL[a]} (mean {asg[f'd_km_{a}'].mean():.1f} km)" for a in ALGOS]
    grouped(ax, [f"]{a},{a + 1}]" for a in bins[:-1]], ser, [AC[a] for a in ALGOS], names)
    ax.set_xlabel("fronthaul distance [km]"); ax.set_ylabel("number of RRHs"); ax.legend(fontsize=8, loc="upper right")
    ax.set_title(f"RRHs per fronthaul distance band, K = {S['cases'][case]['K']} (as thesis fig. 4.3)",
                 loc="left", fontsize=10)
    save(fig, fname)


def fig_mux():
    pools, _ = case_data(cfg.K_REFERENCE)
    ser = [pools[f"mux_gain_{a}"].to_numpy() for a in ALGOS]
    fig, ax = plt.subplots(figsize=(12, 3.6))
    names = [f"{AL[a]} (overall {S['cases'][cfg.K_REFERENCE][a]['mux_gain_overall']:.2f})" for a in ALGOS]
    grouped(ax, list(pools.pool_id), ser, [AC[a] for a in ALGOS], names)
    ax.axhline(1, color=INK2, lw=0.8); ax.set_ylim(0.9, None)
    ax.set_xlabel("BBU pool"); ax.set_ylabel("multiplexing gain")
    ax.legend(fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.02), ncol=3)
    ax.set_title("Multiplexing gain per pool: sum of RRH peaks / pool peak (thesis eq. 3.20, fig. 4.5)",
                 loc="left", fontsize=10, pad=26)
    save(fig, "fig11_mux_gain.png")


def fig_k_comparison():
    cases = list(cfg.K_CASES)
    labels = [f"{c}\nK = {S['cases'][c]['K']}" for c in cases]
    metrics = [("load_cv_at_h", f"CV of the pool load at {H}:00", "(a) Load imbalance"),
               ("count_cv", "CV of RRHs per pool", "(b) RRH-number imbalance"),
               ("mean_km", "mean fronthaul distance [km]", "(c) Distance"),
               ("mux_gain_overall", "overall multiplexing gain", "(d) Multiplexing gain")]
    fig, axs = plt.subplots(1, 4, figsize=(15, 3.8))
    for ax, (key, yl, ttl) in zip(axs, metrics):
        ser = [[S["cases"][c][a][key] for c in cases] for a in ALGOS]
        grouped(ax, labels, ser, [AC[a] for a in ALGOS], [AL[a] for a in ALGOS])
        ax.set_ylabel(yl); ax.set_title(ttl, loc="left", fontsize=10)
        if key == "mux_gain_overall":
            ax.set_ylim(1, None)
    axs[0].legend(fontsize=7.5, loc="upper left")
    save(fig, "fig12_k_comparison.png")


def fig_maps():
    rrhs, cand, sets = P.load_scenario()
    pools, asg = case_data(cfg.K_REFERENCE)
    pos = {r["rrh_id"]: (r["x"], r["y"]) for r in rrhs}
    pxy = {p["pool_id"]: (p["x"], p["y"]) for p in cand}
    cm = plt.get_cmap("tab20")
    col = {p: matplotlib.colors.to_hex(cm(i % 20)) for i, p in enumerate(pools.pool_id)}
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.4))
    for ax, a in zip(axs, ALGOS):
        for _, r in asg.iterrows():
            x, y = pos[r.rrh_id]; px, py = pxy[r[f"pool_{a}"]]
            ax.plot([x, px], [y, py], color=col[r[f"pool_{a}"]], lw=0.6, alpha=0.7, zorder=2)
            ax.scatter(x, y, s=8, color=col[r[f"pool_{a}"]], zorder=3, lw=0)
        for p in pools.pool_id:
            ax.scatter(*pxy[p], marker="s", s=40, color=col[p], edgecolor=INK, lw=0.8, zorder=4)
        ax.plot([-HALF, HALF, HALF, -HALF, -HALF], [-HALF, -HALF, HALF, HALF, -HALF], color=INK2, lw=0.8)
        ax.set_xlim(-HALF - 0.5, HALF + 0.5); ax.set_ylim(-HALF - 0.5, HALF + 0.5); ax.set_aspect("equal")
        st = S["cases"][cfg.K_REFERENCE][a]
        ax.set_title(f"{AL[a]}\nmean {st['mean_km']:.1f} km, load CV {st['load_cv_at_h']:.2f}", loc="left",
                     fontsize=9.5)
        ax.set_xlabel("x [km]"); ax.set_ylabel("y [km]")
    save(fig, "fig13_maps.png")


def fig_slack():
    sk = pd.read_csv(cfg.P2_DATA / "slack_sweep.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(sk.mean_km, sk.load_cv_at_h, "-o", color=AC["traffic"], lw=2, ms=5)
    for r in sk.itertuples():
        if r.slack_km == 1:
            continue
        ax.annotate(f"{r.slack_km:g} km" + (" (only distance)" if r.slack_km == 0 else ""), (r.mean_km, r.load_cv_at_h), xytext=(5, 4), textcoords="offset points",
                    fontsize=7.5, color=INK2)
    ax.set_xlabel("mean fronthaul distance [km]"); ax.set_ylabel(f"CV of the pool load at {H}:00")
    ax.set_title("Traffic balancing limited to pools at most s km farther than the nearest one", loc="left",
                 fontsize=10)
    ax.set_ylim(0, None); ax.set_xlim(0, None)
    save(fig, "fig14_slack.png")


def main():
    fig_load_hours(cfg.K_REFERENCE)
    fig_single_profile()
    for case in cfg.K_CASES:
        sfx = "" if case == cfg.K_REFERENCE else f"_{case}"
        fig_per_pool(case, "rrhs", f"fig05_rrhs_per_pool{sfx}.png", "RRHs per pool",
                     "Number of RRHs per BBU pool, K = {K}")
        fig_distance_bands(case, f"fig09_distance_bands{sfx}.png")
        fig_per_pool(case, "avg_capacity", f"fig10_avg_capacity{sfx}.png", "average capacity [GBph]",
                     "Average capacity per pool over 24 h, K = {K} (as thesis fig. 4.4)")
    fig_per_pool(cfg.K_REFERENCE, f"load_h{H}", "fig06_load_per_pool.png", f"load at {H}:00 [GBph]",
                 f"Load per BBU pool at the balancing hour ({H}:00), K = {{K}}")
    fig_hour_dependence()
    fig_single_profile_balanced()
    fig_mux()
    fig_k_comparison()
    fig_maps()
    fig_slack()
    print("figures written to", cfg.P2_FIG)


if __name__ == "__main__":
    main()
