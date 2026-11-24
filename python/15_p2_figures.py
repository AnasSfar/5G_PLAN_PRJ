"""Step 15 (phase 2) - Figures of the load balancing (review item in brackets).

Reads phase2/data/* (steps 13 and 14) and writes phase2/figures/:
  fig03_load_<hh>h        load per pool with the delay-only assignment at 8:00, 15:00, 21:00   [1a]
  fig04_single_profile    load per pool at the peak hour: all residential / all office / real    [1b]
  fig05_rrhs_per_pool     RRHs per pool: only distance / traffic balancing / RRH balancing      [2a]
  fig06_hour_dependence   RRHs that change pool if the balancing is done at another hour        [2b]
  fig07_single_profile_balanced  traffic balancing with all residential / all office / real     [2c]
  fig08_distance_bands    RRHs per 1 km fronthaul band, three algorithms (thesis fig. 4.3)      [2d]
  fig09_avg_capacity      average capacity per pool over 24 h, three algorithms (thesis fig. 4.4) [2e]
  fig10_k_comparison      normal / few / many pools                                              [final]
Figures 05, 08, 09 are also written for the few / many cases (suffix _few, _many).
Loads are in MBph (review unit).
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
from p2_style import save, INK, INK2, TRAFFIC_COLORS, mbph_axis

ALGOS = ["delay", "traffic", "count"]
AC, AL = cfg.ALGO_COLORS, cfg.ALGO_LABELS
S = json.loads((cfg.P2_DATA / "summary.json").read_text(encoding="utf-8"))
H = S["peak_hour"]
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
    """Review 1a: three separate figures, load per pool with the delay-only assignment."""
    pools, asg = case_data(case)
    tr = pd.read_csv(cfg.P2_DATA / "rrh_traffic.csv")
    ids = list(pools.pool_id)
    loads = {hh: np.array([tr[f"h{hh:02d}"][asg.pool_delay == p].sum() for p in ids]) for hh in cfg.REPORT_HOURS}
    top = max(v.max() for v in loads.values()) * 1.12
    for hh, v in loads.items():
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.bar(range(len(ids)), v, color=AC["delay"], width=0.7, zorder=3)
        ax.axhline(v.mean(), color=INK2, ls=":", lw=1)
        ax.set_xticks(range(len(ids)), ids, rotation=90, fontsize=8); ax.grid(axis="x", visible=False)
        ax.set_ylim(0, top); ax.set_xlabel("BBU pool"); ax.set_ylabel("total load [MBph]"); mbph_axis(ax)
        ax.set_title(f"Load per BBU pool at {hh}:00, only distance (K = {S['cases'][case]['K']}): "
                     f"total {v.sum():,.0f} MBph, mean (dotted) {v.mean():,.0f}, CV {P.cv(v):.2f}", loc="left", fontsize=10)
        save(fig, f"fig03_load_{hh:02d}h.png")


def fig_single_profile():
    """Review 1b: three columns per pool (all residential, all office, real case) at the peak hour."""
    sp = pd.read_csv(cfg.P2_DATA / "single_profile.csv")
    d = sp[sp.algorithm == "delay"]
    ids = list(d[d.profile == "real"].pool_id)
    cols = {"residential": TRAFFIC_COLORS["residential"], "office": TRAFFIC_COLORS["office"], "real": INK2}
    fig, ax = plt.subplots(figsize=(12, 3.9))
    ser, names = [], []
    for prof in ("residential", "office", "real"):
        g = d[d.profile == prof].set_index("pool_id").loc[ids]
        ser.append(g.load_peak_hour.to_numpy())
        lab = {"residential": "all residential", "office": "all office", "real": "real case"}[prof]
        names.append(f"{lab}, total {g.load_peak_hour.sum():,.0f} MBph")
    grouped(ax, ids, ser, [cols[p] for p in ("residential", "office", "real")], names)
    ax.set_xlabel("BBU pool"); ax.set_ylabel(f"load at {H}:00 [MBph]"); mbph_axis(ax); ax.legend(fontsize=8)
    ax.set_title(f"Load per pool at the peak hour ({H}:00), only distance (K = {S['cases'][cfg.K_REFERENCE]['K']})",
                 loc="left", fontsize=10)
    save(fig, "fig04_single_profile.png")


def fig_per_pool(case, key, fname, ylabel, title):
    pools, _ = case_data(case)
    ser = [pools[f"{key}_{a}"].to_numpy() for a in ALGOS]
    fig, ax = plt.subplots(figsize=(12 if len(pools) > 10 else 8, 3.9))
    names = [f"{AL[a]} (CV {P.cv(v):.2f}, {v.min():,.0f}-{v.max():,.0f})" for a, v in zip(ALGOS, ser)]
    grouped(ax, list(pools.pool_id), ser, [AC[a] for a in ALGOS], names)
    ax.set_xlabel("BBU pool"); ax.set_ylabel(ylabel)
    if "MBph" in ylabel:
        mbph_axis(ax)
    ax.legend(fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.02), ncol=3)
    ax.set_title(title.format(K=S["cases"][case]["K"]), loc="left", fontsize=10, pad=26)
    save(fig, fname)


def fig_hour_dependence():
    hd = pd.read_csv(cfg.P2_DATA / "hour_dependence.csv")
    n = S["cases"][cfg.K_REFERENCE]["traffic"]["served"]
    fig, axs = plt.subplots(1, 2, figsize=(13, 3.9))
    ax = axs[0]
    ax.bar(hd.hour, hd.changed_vs_peak_hour, color=AC["traffic"], width=0.75, zorder=3)
    ax.set_xticks(cfg.HOURS[1::2]); ax.set_xlim(0.3, 24.7); ax.set_ylim(0, n)
    ax.axhline(n, color=INK2, ls=":", lw=1)
    ax.text(H, 4, "adopted", rotation=90, ha="center", va="bottom", fontsize=8, color=INK2)
    ax.set_xlabel("hour used for the traffic balancing"); ax.set_ylabel(f"RRHs in another pool (of {n})")
    ax.set_title(f"(a) RRHs that change pool vs the balancing at the peak hour ({H}:00)", loc="left", fontsize=10)
    ax = axs[1]
    ax.plot(hd.hour, hd.load_cv_delay_only, "-o", ms=3, color=AC["delay"], lw=2, label="only distance")
    ax.plot(hd.hour, hd.load_cv_with_adopted, "-o", ms=3, color=AC["traffic"], lw=2,
            label=f"traffic balancing at the peak hour {H}:00 (adopted)")
    ax.plot(hd.hour, hd.load_cv_own_hour, "--", color=AC["traffic"], lw=1.4, label="balancing redone every hour")
    ax.set_xticks(cfg.HOURS[1::2]); ax.set_xlim(0.3, 24.7); ax.set_ylim(0, None)
    ax.set_xlabel("hour of the day"); ax.set_ylabel("CV of the pool load")
    ax.set_title("(b) Imbalance of the pool load during the day", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    save(fig, "fig06_hour_dependence.png")


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
        names.append({"residential": "all residential", "office": "all office", "real": "real case"}[prof])
    grouped(axs[0], ids, ser, [cols[p] for p in ("residential", "office", "real")], names)
    axs[0].set_xlabel("BBU pool"); axs[0].set_ylabel("RRHs per pool"); axs[0].legend(fontsize=8)
    axs[0].set_title(f"(a) RRHs per pool after traffic balancing at the peak hour ({H}:00)", loc="left", fontsize=10)
    ax = axs[1]
    x = np.arange(3)
    for k, alg in enumerate(("delay", "traffic")):
        v = []
        for prof in ("residential", "office", "real"):
            g = sp[(sp.profile == prof) & (sp.algorithm == alg)].load_peak_hour.to_numpy()
            v.append(P.cv(g))
        ax.bar(x + (k - 0.5) * 0.38, v, width=0.34, color=AC[alg], label=AL[alg], zorder=3)
        for xi, vi in zip(x, v):
            ax.text(xi + (k - 0.5) * 0.38, vi + 0.02, f"{vi:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x, ["all residential", "all office", "real case"]); ax.grid(axis="x", visible=False)
    ax.set_ylabel(f"CV of the pool load at {H}:00"); ax.legend(fontsize=8, loc="upper left")
    ax.set_ylim(0, 1.45)
    ax.set_title("(b) Imbalance before and after", loc="left", fontsize=10)
    save(fig, "fig07_single_profile_balanced.png")


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


def fig_k_comparison():
    cases = list(cfg.K_CASES)
    labels = [f"{c}\nK = {S['cases'][c]['K']}" for c in cases]
    metrics = [("load_cv_at_h", f"CV of the pool load at {H}:00", "(a) Load imbalance"),
               ("count_cv", "CV of RRHs per pool", "(b) RRH-number imbalance"),
               ("mean_km", "mean fronthaul distance [km]", "(c) Distance")]
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, (key, yl, ttl) in zip(axs, metrics):
        ser = [[S["cases"][c][a][key] for c in cases] for a in ALGOS]
        grouped(ax, labels, ser, [AC[a] for a in ALGOS], [AL[a] for a in ALGOS])
        ax.set_ylabel(yl); ax.set_title(ttl, loc="left", fontsize=10)
    axs[0].legend(fontsize=7.5, loc="upper left")
    save(fig, "fig10_k_comparison.png")


def main():
    fig_load_hours(cfg.K_REFERENCE)
    fig_single_profile()
    for case in cfg.K_CASES:
        sfx = "" if case == cfg.K_REFERENCE else f"_{case}"
        fig_per_pool(case, "rrhs", f"fig05_rrhs_per_pool{sfx}.png", "RRHs per pool",
                     "Number of RRHs per BBU pool, K = {K}")
        fig_distance_bands(case, f"fig08_distance_bands{sfx}.png")
        fig_per_pool(case, "avg_capacity", f"fig09_avg_capacity{sfx}.png", "average capacity [MBph]",
                     "Average capacity per pool over 24 h, K = {K} (as thesis fig. 4.4)")
    fig_hour_dependence()
    fig_single_profile_balanced()
    fig_k_comparison()
    print("figures written to", cfg.P2_FIG)


if __name__ == "__main__":
    main()
