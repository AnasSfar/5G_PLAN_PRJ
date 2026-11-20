"""Step 12 (phase 1) - Static PNG map figures over a real basemap (for the report and the poster).

Same content and colours as fig01, fig02, fig03, fig11 and fig12c, drawn in Web Mercator over map tiles
downloaded by contextily. NEEDS INTERNET (the tiles are fetched once and cached by contextily).

    pip install contextily
    python 12_basemap_figures.py                       # light grey Esri basemap (default)
    python 12_basemap_figures.py --basemap osm         # OpenStreetMap
    python 12_basemap_figures.py --basemap satellite   # Esri World Imagery

Output: phase1/figures/map_fig01_scenario.png ... map_fig12c_options_50us.png
"""
import argparse
import json

import contextily as cx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import config as cfg
import p1_lib as L

INK, INK2 = "#0b0b0b", "#52514e"
R_EARTH = 6378137.0
BASEMAPS = {"grey": cx.providers.Esri.WorldGrayCanvas, "osm": cx.providers.OpenStreetMap.Mapnik,
            "satellite": cx.providers.Esri.WorldImagery}
plt.rcParams.update({"font.size": 9, "legend.frameon": True, "legend.framealpha": 0.92, "savefig.dpi": 170})


def merc(lat, lon):
    lat = np.radians(np.asarray(lat, float)); lon = np.radians(np.asarray(lon, float))
    return R_EARTH * lon, R_EARTH * np.log(np.tan(np.pi / 4 + lat / 2))


def pool_colors(ids):
    cm = plt.get_cmap("tab20")
    return {pid: matplotlib.colors.to_hex(cm(i % 20)) for i, pid in enumerate(ids)}


class Fig:
    def __init__(self, source, zoom):
        self.source, self.zoom = source, zoom
        w, s, e, n = cfg.BBOX
        self.bx, self.by = merc([s, s, n, n, s], [w, e, e, w, w])

    def axes(self, ax, title):
        pad = 600
        ax.set_xlim(self.bx.min() - pad, self.bx.max() + pad); ax.set_ylim(self.by.min() - pad, self.by.max() + pad)
        ax.set_aspect("equal")
        cx.add_basemap(ax, source=self.source, crs="EPSG:3857", zoom=self.zoom, attribution_size=6)
        ax.plot(self.bx, self.by, color="#333", lw=1.2, ls="--", zorder=3)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        # 5 km scale bar (Mercator metres are stretched by 1/cos(lat))
        k = 1 / np.cos(np.radians(cfg.CENTER_LAT))
        x0, y0 = self.bx.max() - 7000 * k, self.by.min() + 1200 * k
        ax.plot([x0, x0 + 5000 * k], [y0, y0], color=INK, lw=3, solid_capstyle="butt", zorder=8)
        ax.text(x0 + 2500 * k, y0 + 350 * k, "5 km", ha="center", fontsize=8, zorder=8,
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))


def pools_on(ax, pools, act_ids, counts=None, fill=None, show_off=True):
    for p in pools:
        on = p["pool_id"] in act_ids
        if not on and not show_off:
            continue
        x, y = merc(p["lat"], p["lon"])
        ax.scatter(x, y, marker="s", s=60, zorder=7, edgecolor=INK, lw=1.3,
                   color=(fill or {}).get(p["pool_id"], INK) if on else "white")
        lab = p["pool_id"] + (f" ({int(counts.get(p['pool_id'], 0))})" if counts is not None and on else "")
        ax.annotate(lab, (x, y), xytext=(5, 4), textcoords="offset points", fontsize=7, zorder=8, weight="bold",
                    bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.5))


def save(fig, name):
    fig.tight_layout(); fig.savefig(cfg.P1_FIG / name); plt.close(fig)
    print("written", name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basemap", default="grey", help="grey | osm | satellite | path to a local GeoTIFF")
    ap.add_argument("--zoom", default="auto")
    a = ap.parse_args()
    src = BASEMAPS.get(a.basemap, a.basemap)
    F = Fig(src, a.zoom if a.zoom == "auto" else int(a.zoom))

    sc = json.loads((cfg.P1_DATA / "scenario.json").read_text(encoding="utf-8"))
    res = json.loads((cfg.P1_DATA / "results.json").read_text(encoding="utf-8"))
    rrhs, pools = sc["rrhs"], sc["pools"]
    K = res["k_selected"]; act_ids = res["active_pools"]
    act = [p for p in pools if p["pool_id"] in act_ids]
    pcol = pool_colors(act_ids)
    core = L.load_core()
    strict = min(cfg.RTT_SWEEP_US)
    asg = pd.read_csv(cfg.P1_DATA / f"assignment_K{K}.csv").set_index("rrh_id")
    asg_s = pd.read_csv(cfg.P1_DATA / f"assignment_K{K}_rtt{int(strict)}.csv").set_index("rrh_id")
    rx, ry = merc([r["lat"] for r in rrhs], [r["lon"] for r in rrhs])
    traffic = np.array([r["traffic"] for r in rrhs]); syn = np.array([r["is_synthetic"] for r in rrhs])
    ids = [r["rrh_id"] for r in rrhs]
    pos = {p["pool_id"]: merc(p["lat"], p["lon"]) for p in pools}

    # fig01 scenario
    fig, ax = plt.subplots(figsize=(8, 8.4))
    F.axes(ax, f"Madrid 30 x 30 km: {len(rrhs)} RRHs and {len(pools)} candidate BBU pools")
    cx_, cy_ = merc([c["lat"] for c in core], [c["lon"] for c in core])
    ax.scatter(cx_, cy_, s=2, color="#7d7c76", lw=0, alpha=0.6, zorder=4, label=f"all {len(core)} real core RRHs")
    for t, c in cfg.TRAFFIC_COLORS.items():
        m = (traffic == t) & ~syn
        ax.scatter(rx[m], ry[m], s=22, color=c, edgecolor="white", lw=0.6, zorder=5, label=f"{t} ({m.sum()})")
        m = (traffic == t) & syn
        if m.any():
            ax.scatter(rx[m], ry[m], s=30, marker="^", color=c, edgecolor=INK, lw=0.6, zorder=5)
    pools_on(ax, pools, act_ids)
    h, _ = ax.get_legend_handles_labels()
    h += [Line2D([], [], marker="s", ls="", color=INK, label=f"active pool ({len(act_ids)})"),
          Line2D([], [], marker="s", ls="", mfc="white", mec=INK, label=f"switched off ({len(pools) - len(act_ids)})")]
    if syn.any():
        h.append(Line2D([], [], marker="^", ls="", mfc="white", mec=INK, label=f"synthetic RRH ({syn.sum()})"))
    ax.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=3, fontsize=8)
    save(fig, "map_fig01_scenario.png")

    # fig02 random vs geo
    fig, axs = plt.subplots(1, 2, figsize=(14, 7.6))
    rnd = L.assign_traffic([dict(r) for r in rrhs], "random", cfg.TRAFFIC_SHARES, cfg.TRAFFIC_SEED)
    for ax, lst, title in ((axs[0], rnd, "Random: " + ", ".join(f"{v:.0%} {k}" for k, v in cfg.TRAFFIC_SHARES.items())),
                           (axs[1], rrhs, "Geographic rule (dashed: office / mixed zones)")):
        F.axes(ax, title)
        tt = np.array([r["traffic"] for r in lst])
        for t, c in cfg.TRAFFIC_COLORS.items():
            m = tt == t
            ax.scatter(rx[m], ry[m], s=20, color=c, edgecolor="white", lw=0.5, zorder=5, label=f"{t} ({m.sum()})")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=3, fontsize=8)
    mapsmod = __import__("importlib").import_module("11_maps")
    for z in cfg.OFFICE_ZONES + cfg.MIXED_ZONES:
        col = cfg.TRAFFIC_COLORS["office" if z in cfg.OFFICE_ZONES else "mixed"]
        ll = np.array(mapsmod.zone_shape(z)); zx, zy = merc(ll[:, 0], ll[:, 1])
        axs[1].fill(zx, zy, color=col, alpha=0.12, zorder=4); axs[1].plot(np.r_[zx, zx[:1]], np.r_[zy, zy[:1]],
                                                                         color=col, ls="--", lw=1, zorder=4)
    save(fig, "map_fig02_traffic_patterns.png")

    # fig03 assignment
    fig, ax = plt.subplots(figsize=(8, 8.4))
    F.axes(ax, f"Minimise Delay, K = {K} pools, RTT <= {cfg.MAX_RTT_US:g} us (d <= {cfg.d_max_km():g} km)")
    for i, rid in enumerate(ids):
        r = asg.loc[rid]
        if r.served:
            px, py = pos[r.best_pool]
            ax.plot([rx[i], px], [ry[i], py], color=pcol[r.best_pool], lw=1.0, alpha=0.9, zorder=5)
            ax.scatter(rx[i], ry[i], s=16, color=pcol[r.best_pool], edgecolor="white", lw=0.5, zorder=6)
        else:
            ax.scatter(rx[i], ry[i], marker="x", s=40, color="#e34948", lw=2, zorder=6)
    pools_on(ax, pools, act_ids, counts=asg.best_pool.value_counts(), fill=pcol, show_off=False)
    ax.legend(handles=[Line2D([], [], marker="s", ls="", color="#999", mec=INK, label="pool (number of RRHs); colour = pool"),
                       Line2D([], [], color="#999", label="link RRH -> nearest reachable pool"),
                       Line2D([], [], marker="x", ls="", color="#e34948", label=f"unserved RRH ({int((~asg.served).sum())})")],
              loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=3, fontsize=8)
    save(fig, "map_fig03_assignment.png")

    # fig11 / fig12c options
    def options(a_df, rtt, name, circles, links):
        fig, ax = plt.subplots(figsize=(8.6, 8.4))
        dmax = cfg.d_max_km(rtt)
        F.axes(ax, f"Reachable pools per RRH, K = {K}, RTT <= {rtt:g} us (d <= {dmax:g} km)")
        top = int(max(a_df.n_options.max(), 1))
        cmap = plt.get_cmap("Blues", top + 1)
        norm = matplotlib.colors.BoundaryNorm(np.arange(-0.5, top + 1.5), cmap.N)
        if circles:
            k = 1 / np.cos(np.radians(cfg.CENTER_LAT))
            for p in act:
                x, y = pos[p["pool_id"]]
                ax.add_patch(plt.Circle((x, y), dmax * 1000 * k, fill=False, color=INK2, lw=0.6, ls=":", zorder=4))
        if links:
            for i, rid in enumerate(ids):
                r = a_df.loc[rid]
                if r.served:
                    px, py = pos[r.best_pool]
                    ax.plot([rx[i], px], [ry[i], py], color=pcol[r.best_pool], lw=0.8, alpha=0.75, zorder=5)
        nopt = np.array([a_df.loc[rid].n_options for rid in ids])
        m = nopt > 0
        sca = ax.scatter(rx[m], ry[m], c=nopt[m], cmap=cmap, norm=norm, s=30, edgecolor=INK2, lw=0.5, zorder=6)
        ax.scatter(rx[~m], ry[~m], marker="x", s=50, color="#e34948", lw=2, zorder=6)
        fig.colorbar(sca, ax=ax, shrink=0.7, pad=0.01, label="reachable pools",
                     ticks=range(0, top + 1, max(1, top // 10)))
        pools_on(ax, pools, act_ids, counts=a_df.best_pool.value_counts(), fill=pcol if links else None, show_off=False)
        hl = [Line2D([], [], marker="s", ls="", color=INK if not links else "#999", mec=INK, label="active pool (number of RRHs)"),
              Line2D([], [], marker="x", ls="", color="#e34948", label=f"unserved RRH ({int((~m).sum())})")]
        if circles:
            hl.append(Line2D([], [], ls=":", color=INK2, label=f"{dmax:g} km reach of a pool"))
        ax.legend(handles=hl, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=3, fontsize=8)
        save(fig, name)

    options(asg, cfg.MAX_RTT_US, f"map_fig11_options_{int(cfg.MAX_RTT_US)}us.png", circles=False, links=False)
    options(asg_s, strict, f"map_fig12c_options_{int(strict)}us.png", circles=True, links=True)


if __name__ == "__main__":
    main()
