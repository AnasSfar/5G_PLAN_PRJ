"""Step 4 - Folium map of the master dataset (maps/rrh_map.html) + a density figure (maps/density.png)."""
import json

import folium
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import config as cfg

COLORS = {"4G": "#2271c9", "5G": "#d9480f", "4G+5G": "#7c3aed", "ambiguous": "#9ca3af"}


def main():
    master = json.loads((cfg.JSON_DIR / "rrh_master.json").read_text(encoding="utf-8"))
    rrhs = master["rrhs"]
    w, s, e, n = cfg.BBOX

    m = folium.Map(location=[cfg.CENTER_LAT, cfg.CENTER_LON], zoom_start=10, tiles="OpenStreetMap")
    folium.Rectangle([[s, w], [n, e]], color="#333", weight=2, fill=False,
                     tooltip="30 x 30 km scenario").add_to(m)
    for lab, col in COLORS.items():
        grp = folium.FeatureGroup(name=f"{lab} ({sum(r['label'] == lab for r in rrhs)})")
        for r in rrhs:
            if r["label"] != lab:
                continue
            tip = (f"{r['rrh_id']} | {r['label']} | {', '.join(r['operators'])} | "
                   f"{r['n_towers_merged']} tower(s)")
            folium.CircleMarker([r["lat"], r["lon"]], radius=3, color=col, fill=True, fill_opacity=0.8,
                                weight=1, tooltip=tip).add_to(grp)
        grp.add_to(m)
    m.fit_bounds([[s, w], [n, e]])
    folium.LayerControl().add_to(m)
    m.save(str(cfg.MAPS / "rrh_map.html"))

    core = [r for r in rrhs if r["in_core"]]          # density figure: RRHs with real 4G/5G evidence only
    lat = np.array([r["lat"] for r in core]); lon = np.array([r["lon"] for r in core])
    fig, ax = plt.subplots(figsize=(7, 6))
    hb = ax.hexbin(lon, lat, gridsize=30, cmap="viridis", mincnt=1, extent=(w, e, s, n))
    fig.colorbar(hb, label="RRHs per cell")
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    ax.set_title(f"RRH density, {len(core)} RRHs in 30 x 30 km")
    fig.tight_layout(); fig.savefig(cfg.MAPS / "density.png", dpi=130)
    print("map and density figure written to", cfg.MAPS)


if __name__ == "__main__":
    main()
