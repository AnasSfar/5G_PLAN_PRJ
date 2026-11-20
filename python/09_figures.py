"""Step 9 (phase 1) - Figures, tables and the interactive map of the Minimise Delay results.

Reads phase1/data/scenario.json, results.json, k_analysis.csv, assignment_*.csv, pool_categories_*.csv
(steps 7 and 8) and writes phase1/figures/*.png. The map figures on a real basemap are made by 11_maps.py
(interactive) and 12_basemap_figures.py (static PNG, needs internet).

Figures (review item in brackets):
  fig01 scenario: RRHs by traffic pattern + candidate / active pools                      [1, 2b]
  fig02 traffic pattern: random shares vs geographic rule                                  [2a, 2b]
  fig03 assignment map: one colour per pool, line RRH -> pool, unserved RRHs               [3a]
  fig04 CDF of the RRH -> nearest-pool distance (and RTT)                                  [3b]
  fig05 share of RRHs per 1 km fronthaul band (as thesis fig. 4.3)                         [3b]
  fig06 mean +- std round-trip delay vs number of pools (as thesis fig. 4.17)              [3c]
  fig07 unserved RRHs vs number of pools for several delay budgets                         [3c]
  fig08 per pool: only option / optimal with alternatives / possible not optimal, K active [3c]
  fig09 same for the 25 candidate pools (which ones are irrelevant)                        [1a, 3c]
  fig10 per RRH: number of reachable pools                                                 [3d]
  fig11 map of the number of reachable pools                                               [3d]
  fig12 strict budget (50 us): categories per pool and options per RRH                     [extra]
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import config as cfg
import p1_lib as L

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
CAT3 = ["#2a78d6", "#eb6834", "#1baf7a"]           # palette slots 1-3 (validated all-pairs)
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "legend.frameon": False, "savefig.dpi": 150, "figure.dpi": 100})
HALF = cfg.SIDE_KM / 2


def pool_colors(n):
    cm = plt.get_cmap("tab20")
    return [matplotlib.colors.to_hex(cm(i % 20)) for i in range(n)]


def frame(ax, title):
    ax.set_xlim(-HALF - 0.5, HALF + 0.5); ax.set_ylim(-HALF - 0.5, HALF + 0.5); ax.set_aspect("equal")
    ax.plot([-HALF, HALF, HALF, -HALF, -HALF], [-HALF, -HALF, HALF, HALF, -HALF], color=INK2, lw=0.8)
    ax.set_xlabel("x [km] (west - east)"); ax.set_ylabel("y [km] (south - north)")
    ax.set_title(title, loc="left", fontsize=10, color=INK)


def background(ax, core):
    x, y = L.to_xy([c["lat"] for c in core], [c["lon"] for c in core])
    ax.scatter(x, y, s=2, color="#c9c8c2", lw=0, zorder=1, label=f"all {len(core)} real core RRHs")


def save(fig, name):
    fig.tight_layout(); fig.savefig(cfg.P1_FIG / name); plt.close(fig)


def draw_pools(ax, pools, active_ids, labels=True):
    for p in pools:
        on = p["pool_id"] in active_ids
        ax.scatter(p["x"], p["y"], marker="s", s=60, zorder=6, edgecolor=INK, lw=1.2,
                   color=INK if on else "white")
        if labels:
            ax.annotate(p["pool_id"], (p["x"], p["y"]), xytext=(4, 4), textcoords="offset points",
                        fontsize=7, color=INK, zorder=7)


def main():
    sc = json.loads((cfg.P1_DATA / "scenario.json").read_text(encoding="utf-8"))
    res = json.loads((cfg.P1_DATA / "results.json").read_text(encoding="utf-8"))
    kdf = pd.read_csv(cfg.P1_DATA / "k_analysis.csv")
    rrhs, pools = sc["rrhs"], sc["pools"]
    K = res["k_selected"]; act_ids = res["active_pools"]
    act = [p for p in pools if p["pool_id"] in act_ids]
    core = L.load_core()
    asg = pd.read_csv(cfg.P1_DATA / f"assignment_K{K}.csv")
    rx = np.array([r["x"] for r in rrhs]); ry = np.array([r["y"] for r in rrhs])
    syn = np.array([r["is_synthetic"] for r in rrhs])
    traffic = np.array([r["traffic"] for r in rrhs])

    # ---------------- fig01 scenario
    fig, ax = plt.subplots(figsize=(7.2, 7))
    background(ax, core)
    for t, c in cfg.TRAFFIC_COLORS.items():
        m = (traffic == t) & ~syn
        ax.scatter(rx[m], ry[m], s=16, color=c, edgecolor="white", lw=0.5, zorder=4, label=f"{t} ({m.sum()})")
        m = (traffic == t) & syn
        if m.any():
            ax.scatter(rx[m], ry[m], s=22, marker="^", color=c, edgecolor=INK, lw=0.5, zorder=4)
    if syn.any():
        ax.scatter([], [], marker="^", color="white", edgecolor=INK, label=f"synthetic RRH ({syn.sum()})")
    draw_pools(ax, pools, act_ids)
    ax.scatter([], [], marker="s", color=INK, label=f"active pool ({len(act_ids)})")
    ax.scatter([], [], marker="s", color="white", edgecolor=INK, label=f"candidate, switched off ({len(pools) - len(act_ids)})")
    frame(ax, f"Madrid 30 x 30 km: {len(rrhs)} RRHs and {len(pools)} candidate BBU pools")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=7.5, ncol=3, markerscale=1.2)
    save(fig, "fig01_scenario.png")

    # ---------------- fig02 traffic pattern random vs geo
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.6))
    rnd = L.assign_traffic([dict(r) for r in rrhs], "random", cfg.TRAFFIC_SHARES, cfg.TRAFFIC_SEED)
    for ax, lst, title in ((axs[0], rnd, "Random: " + ", ".join(f"{v:.0%} {k}" for k, v in cfg.TRAFFIC_SHARES.items())),
                           (axs[1], rrhs, "Geographic rule (districts, centre, airport, outskirts)")):
        background(ax, core)
        tt = np.array([r["traffic"] for r in lst])
        for t, c in cfg.TRAFFIC_COLORS.items():
            m = tt == t
            ax.scatter(rx[m], ry[m], s=14, color=c, edgecolor="white", lw=0.4, zorder=4, label=f"{t} ({m.sum()})")
        frame(ax, title); ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), fontsize=7.5, ncol=4)
    for z in cfg.OFFICE_ZONES + cfg.MIXED_ZONES:
        col = cfg.TRAFFIC_COLORS["office" if z in cfg.OFFICE_ZONES else "mixed"]
        if len(z) == 4:
            x, y = L.to_xy(z[1], z[2])
            axs[1].add_patch(plt.Circle((float(x), float(y)), z[3], fill=False, ls="--", lw=0.8, color=col, zorder=3))
        else:
            x1, y1 = L.to_xy(z[1], z[2]); x2, y2 = L.to_xy(z[3], z[4])
            axs[1].plot([x1, x2], [y1, y2], color=col, lw=6, alpha=0.25, solid_capstyle="round", zorder=3)
    save(fig, "fig02_traffic_patterns.png")

    # ---------------- fig03 assignment map
    cols = dict(zip([p["pool_id"] for p in act], pool_colors(len(act))))
    pos = {p["pool_id"]: (p["x"], p["y"]) for p in pools}
    fig, ax = plt.subplots(figsize=(7.2, 7))
    for _, r in asg.iterrows():
        if r.served:
            px, py = pos[r.best_pool]
            ax.plot([r.x_km, px], [r.y_km, py], color=cols[r.best_pool], lw=0.7, alpha=0.8, zorder=2)
            ax.scatter(r.x_km, r.y_km, s=12, color=cols[r.best_pool], edgecolor="white", lw=0.4, zorder=4)
    uns = asg[~asg.served]
    ax.scatter(uns.x_km, uns.y_km, marker="x", s=30, color=INK, zorder=5, label=f"unserved ({len(uns)})")
    for pid, (px, py) in pos.items():
        if pid in cols:
            ax.scatter(px, py, marker="s", s=70, color=cols[pid], edgecolor=INK, lw=1.2, zorder=6)
            ax.annotate(f"{pid} ({(asg.best_pool == pid).sum()})", (px, py), xytext=(4, 4),
                        textcoords="offset points", fontsize=7, zorder=7)
    frame(ax, f"Minimise Delay, K = {K} pools, RTT <= {cfg.MAX_RTT_US:g} us (d <= {cfg.d_max_km():g} km)")
    ax.legend(handles=[Line2D([], [], marker="s", ls="", color="#888", mec=INK, label="pool (number of RRHs)"),
                       Line2D([], [], marker="x", ls="", color=INK, label=f"unserved RRH ({len(uns)})")],
              loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=7.5, ncol=2)
    save(fig, "fig03_assignment_map.png")

    # ---------------- fig04 CDF of distance to the serving (nearest) pool
    hist = kdf[(kdf.method == "backward_elimination") & (kdf.rtt_limit_us == cfg.MAX_RTT_US)]
    ks = [k for k in (1, 4, 8, 12, K, len(pools)) if k in set(hist.K)]
    ks = sorted(set(ks))
    fig, ax = plt.subplots(figsize=(7, 4.3))
    seq = plt.get_cmap("Blues")(np.linspace(0.35, 1.0, len(ks)))
    for c, k in zip(seq, ks):
        ids = hist[hist.K == k].active_pools.iloc[0].split()
        sub = [p for p in pools if p["pool_id"] in ids]
        d = np.sort(L.minimise_delay(rrhs, sub, cfg.d_max_km())["D"].min(axis=1))
        ax.step(d, np.arange(1, len(d) + 1) / len(d), where="post", color=c, lw=2.2 if k == K else 1.4,
                label=f"K = {k}{' (selected)' if k == K else ''}: mean {d.mean():.2f} km")
    ax.axvline(cfg.d_max_km(), color=INK2, ls="--", lw=1)
    ax.text(cfg.d_max_km(), 0.55, f" d_max = {cfg.d_max_km():g} km\n ({cfg.MAX_RTT_US:g} us)", fontsize=7.5, color=INK2)
    ax.set_xlim(0, cfg.d_max_km() + 1.5); ax.set_ylim(0, 1.01)
    ax.set_xlabel("distance RRH - nearest active BBU pool [km]"); ax.set_ylabel("CDF")
    sec = ax.secondary_xaxis("top", functions=(cfg.rtt_us, lambda u: u * cfg.FIBRE_KM_PER_MS / 2000 / cfg.ROUTE_FACTOR))
    sec.set_xlabel("round-trip fronthaul delay [us]", color=INK2)
    ax.set_title("CDF of the RRH - BBU pool distance (Minimise Delay)", loc="left", fontsize=10)
    ax.legend(loc="center right", bbox_to_anchor=(0.9, 0.42), fontsize=7.5)
    save(fig, "fig04_cdf_distance.png")

    # ---------------- fig05 share per 1 km band (thesis fig. 4.3)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    bins = np.arange(0, int(np.ceil(cfg.d_max_km())) + 1)
    sel = [hist.K.max(), K, hist.K.min()] if hist.K.min() != K else [hist.K.max(), K]
    w = 0.8 / len(sel)
    for j, (k, c) in enumerate(zip(sel, CAT3)):
        ids = hist[hist.K == k].active_pools.iloc[0].split()
        d = L.minimise_delay(rrhs, [p for p in pools if p["pool_id"] in ids], cfg.d_max_km())["d"]
        h, _ = np.histogram(d[~np.isnan(d)], bins=bins)
        ax.bar(bins[:-1] + 0.1 + j * w + w / 2, 100 * h / len(d), width=w * 0.9, color=c, label=f"K = {k}")
    ax.set_xticks(bins[:-1] + 0.5, [f"[{a},{a + 1}[" for a in bins[:-1]], rotation=90, fontsize=7)
    ax.set_xlabel("fronthaul distance [km]"); ax.set_ylabel("share of RRHs [%]")
    ax.set_title("Share of RRHs per fronthaul distance band (as thesis fig. 4.3)", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    save(fig, "fig05_share_per_km.png")

    # ---------------- fig06 delay vs number of pools (thesis fig. 4.17)
    fig, ax = plt.subplots(figsize=(7, 4))
    for (meth, lab), c, off in ((("backward_elimination", "backward elimination (min. mean delay)"), CAT3[0], -0.18),
                                (("farthest_first_prefix", "farthest-first prefix (k-center)"), CAT3[1], 0.18)):
        h = kdf[(kdf.method == meth) & (kdf.rtt_limit_us == cfg.MAX_RTT_US)].sort_values("K")
        ax.errorbar(h.K + off, h.mean_rtt_us, yerr=h.std_rtt_us, fmt="o-", ms=3.5, lw=1.4, capsize=2,
                    color=c, elinewidth=0.8, label=lab)
    ref = hist[hist.K == hist.K.max()].mean_rtt_us.iloc[0]
    ax.axhline(ref * (1 + cfg.KNEE_TOL), color=INK2, ls=":", lw=1)
    ax.text(1.3, ref * (1 + cfg.KNEE_TOL) - 6, f"25-pool mean + {cfg.KNEE_TOL:.0%}", fontsize=7.5, color=INK2)
    ax.axvline(K, color=INK2, ls="--", lw=1); ax.text(K + 0.2, ax.get_ylim()[1] * 0.9, f"K = {K}", fontsize=8)
    ax.set_xlabel("number of active BBU pools K"); ax.set_ylabel("two-way delay, mean +- std [us]")
    ax.set_xticks(range(1, len(pools) + 1))
    ax.set_title("Average round-trip fronthaul delay vs number of pools (as thesis fig. 4.17)", loc="left", fontsize=10)
    ax.legend(fontsize=8)
    save(fig, "fig06_delay_vs_K.png")

    # ---------------- fig07 unserved RRHs vs K, several budgets (farthest-first prefix)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for c, rtt in zip(["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"], cfg.RTT_SWEEP_US):
        h = kdf[(kdf.method == "farthest_first_prefix") & (kdf.rtt_limit_us == rtt)].sort_values("K")
        kmin = res["k_min_by_rtt"][str(int(rtt))]
        ax.plot(h.K, h.unserved, "o-", ms=3.5, lw=1.4, color=c,
                label=f"RTT <= {rtt:g} us (d <= {cfg.d_max_km(rtt):g} km); backward-elim. K_min = {kmin}")
    ax.set_xlabel("number of pools K (first K farthest-first candidates)"); ax.set_ylabel("unserved RRHs")
    ax.set_xticks(range(1, len(pools) + 1))
    ax.set_title("Unserved RRHs vs number of pools and delay budget", loc="left", fontsize=10)
    ax.legend(fontsize=7.5)
    save(fig, "fig07_unserved_vs_K.png")

    # ---------------- fig08 / fig09 / fig12a categories per pool
    def cat_fig(df, title, name):
        fig, ax = plt.subplots(figsize=(max(7, 0.42 * len(df) + 2), 4))
        x = np.arange(len(df)); w = 0.27
        for j, (col, lab) in enumerate((("n_only_option", "1. only this pool"),
                                        ("n_optimal_with_alternatives", "2. optimal (nearest), has alternatives"),
                                        ("n_possible_not_optimal", "3. possible, not the nearest"))):
            ax.bar(x + (j - 1) * w, df[col], width=w * 0.92, color=CAT3[j], label=lab)
        if df.n_only_option.sum() == 0:
            ax.text(0.01, 0.97, "category 1 is empty: every RRH reaches at least two pools", transform=ax.transAxes,
                    fontsize=8, color=INK2, va="top")
        ax.set_xticks(x, df.pool_id, rotation=90 if len(df) > 20 else 0)
        ax.set_xlabel("BBU pool"); ax.set_ylabel("number of RRHs")
        ax.set_title(title, loc="left", fontsize=10); ax.legend(fontsize=7.5, ncol=3, loc="upper center",
                                                                 bbox_to_anchor=(0.5, -0.18))
        save(fig, name)

    cat_fig(pd.read_csv(cfg.P1_DATA / f"pool_categories_K{K}.csv"),
            f"RRHs per pool by category, K = {K}, RTT <= {cfg.MAX_RTT_US:g} us", f"fig08_pool_categories_K{K}.png")
    cat_fig(pd.read_csv(cfg.P1_DATA / "pool_categories_K25.csv"),
            f"RRHs per pool by category, all {len(pools)} candidates, RTT <= {cfg.MAX_RTT_US:g} us",
            "fig09_pool_categories_K25.png")

    # ---------------- fig10 options per RRH
    def opt_fig(df, title, name):
        df = df.sort_values("rrh_id").reset_index(drop=True)
        fig, ax = plt.subplots(figsize=(11, 3.8))
        for t, c in cfg.TRAFFIC_COLORS.items():
            m = df.traffic == t
            ax.bar(df.index[m], df.n_options[m], width=0.85, color=c, label=t)
        ax.set_xlim(-1, len(df))
        step = max(1, len(df) // 40)
        ax.set_xticks(df.index[::step], df.rrh_id[::step], rotation=90, fontsize=6)
        ax.set_xlabel("RRH identifier (ids follow the scraping tiles: roughly south to north)")
        ax.set_ylabel("reachable BBU pools")
        ax.set_title(title + f"  (mean {df.n_options.mean():.1f}, single option {int((df.n_options == 1).sum())}, "
                     f"unserved {int((df.n_options == 0).sum())})", loc="left", fontsize=10)
        ax.legend(fontsize=7.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.32))
        save(fig, name)

    opt_fig(asg, f"Number of reachable pools per RRH, K = {K}, RTT <= {cfg.MAX_RTT_US:g} us", f"fig10_rrh_options_K{K}.png")

    # ---------------- fig11 map of number of options
    def opt_map(df, title, name, dmax):
        fig, ax = plt.subplots(figsize=(7.2, 7))
        top = int(max(df.n_options.max(), 1))
        cmap = plt.get_cmap("Blues", top + 1)
        norm = matplotlib.colors.BoundaryNorm(np.arange(-0.5, top + 1.5), cmap.N)
        sca = ax.scatter(df.x_km, df.y_km, c=df.n_options, cmap=cmap, norm=norm, s=22, edgecolor=INK2, lw=0.4, zorder=4)
        fig.colorbar(sca, ax=ax, shrink=0.75, label="reachable pools", ticks=range(0, top + 1, max(1, top // 10)))
        u = df[df.n_options == 0]
        ax.scatter(u.x_km, u.y_km, marker="x", s=30, color="#e34948", zorder=5, label=f"unserved ({len(u)})")
        draw_pools(ax, act, act_ids)
        for p in (act if dmax <= 8 else []):          # 20 km circles would cover the whole map
            ax.add_patch(plt.Circle((p["x"], p["y"]), dmax, fill=False, color=INK2, lw=0.4, ls=":", zorder=2))
        frame(ax, title); ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=7.5)
        save(fig, name)

    opt_map(asg, f"Reachable pools per RRH, K = {K}, RTT <= {cfg.MAX_RTT_US:g} us", f"fig11_options_map_K{K}.png",
            cfg.d_max_km())

    # ---------------- fig12 strict budget with the same K active pools
    strict = min(cfg.RTT_SWEEP_US)
    import importlib
    md = importlib.import_module("08_min_delay")
    r_s = L.minimise_delay(rrhs, act, cfg.d_max_km(strict))
    a_s = md.assignment_table(rrhs, act, r_s); c_s = md.category_table(rrhs, act, r_s)
    a_s.to_csv(cfg.P1_DATA / f"assignment_K{K}_rtt{int(strict)}.csv", index=False)
    c_s.to_csv(cfg.P1_DATA / f"pool_categories_K{K}_rtt{int(strict)}.csv", index=False)
    cat_fig(c_s, f"RRHs per pool by category, K = {K}, strict RTT <= {strict:g} us (d <= {cfg.d_max_km(strict):g} km)",
            f"fig12a_pool_categories_K{K}_rtt{int(strict)}.png")
    opt_fig(a_s, f"Reachable pools per RRH, K = {K}, RTT <= {strict:g} us", f"fig12b_rrh_options_K{K}_rtt{int(strict)}.png")
    opt_map(a_s, f"Reachable pools per RRH, K = {K}, RTT <= {strict:g} us", f"fig12c_options_map_K{K}_rtt{int(strict)}.png",
            cfg.d_max_km(strict))

    print("figures in", cfg.P1_FIG, "(map versions: 11_maps.py, 12_basemap_figures.py)")


if __name__ == "__main__":
    main()
