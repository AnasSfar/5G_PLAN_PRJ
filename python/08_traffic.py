"""Step 8 (week 2) - traffic profiles: classify each core RRH as office / residential / mixed,
give it a peak traffic in Mbps, and draw the 24 h profiles and the overall network load.

Outputs: json/week2/rrh_traffic.json, img/week2/profiles.png, img/week2/classification.png,
         img/week2/network_load_24h.png
"""
import json
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import config as cfg
import cran

COL = {"residential": "#2e9e44", "office": "#d62728", "mixed": "#1f5bd6"}


def classify(x, y):
    cls = np.array(["residential"] * len(x), dtype=object)
    for lat, lon in cfg.OFFICE_HUBS.values():
        hx, hy = cran.to_km(lat, lon)
        cls[np.hypot(x - hx, y - hy) <= cfg.OFFICE_RADIUS_KM] = "office"
    for (lat, lon), rad in cfg.MIXED_HUBS.values():
        hx, hy = cran.to_km(lat, lon)
        cls[(np.hypot(x - hx, y - hy) <= rad) & (cls == "residential")] = "mixed"
    return cls


def peak_mbps(r):
    """Busy-hour DL traffic of an RRH: every merged station carries 4G and/or 5G traffic."""
    per_station = cfg.PEAK_4G_MBPS * r["has_4g"] + cfg.PEAK_5G_MBPS * r["has_5g"]
    return r["n_towers_merged"] * per_station


def main():
    rrhs, x, y = cran.load_core_rrhs()
    cls = classify(x, y)
    peak = np.array([peak_mbps(r) for r in rrhs])
    prof = {k: np.array(v) for k, v in cfg.PROFILES.items()}

    # traffic matrix RRH x hour (Mbps)
    T = np.vstack([peak[i] * prof[cls[i]] for i in range(len(rrhs))])
    net = T.sum(0)
    sum3 = sum(prof.values())
    out = {
        "classes": dict(Counter(cls)),
        "hour_max_sum_of_profiles": int(cfg.HOURS[int(np.argmax(sum3))]),
        "hour_max_network_load": int(cfg.HOURS[int(np.argmax(net))]),
        "network_load_mbps": [round(v, 1) for v in net],
        "peak_mbps_total": float(peak.sum()),
        "peak_by_class": {c: float(peak[cls == c].sum()) for c in COL},
        "rrhs": [{"rrh_id": r["rrh_id"], "x_km": round(float(x[i]), 4), "y_km": round(float(y[i]), 4),
                  "profile": cls[i], "peak_mbps": float(peak[i])} for i, r in enumerate(rrhs)],
    }
    (cfg.RESULTS / "rrh_traffic.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    # fig: profiles
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for c in COL:
        ax.plot(cfg.HOURS, prof[c], color=COL[c], lw=2, marker="o", ms=3, label=f"{c.capitalize()} profile")
    ax.plot(cfg.HOURS, sum3 / 3, color="k", lw=1.2, ls="--", label="Mean of the three")
    ax.axvline(out["hour_max_sum_of_profiles"], color="grey", lw=0.8, ls=":")
    ax.set_xlabel("Time [hour]"); ax.set_ylabel("Normalised traffic"); ax.set_xticks(cfg.HOURS)
    ax.set_xlim(0.5, 24.5); ax.set_ylim(0, 1.05); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout(); fig.savefig(cfg.FIGS / "profiles.png", dpi=200); plt.close(fig)

    # fig: classification map
    fig, ax = plt.subplots(figsize=(6.2, 6))
    for c in ["residential", "mixed", "office"]:
        m = cls == c
        ax.scatter(x[m], y[m], s=5, color=COL[c], label=f"{c.capitalize()} ({m.sum()})")
    for name, (lat, lon) in cfg.OFFICE_HUBS.items():
        hx, hy = cran.to_km(lat, lon)
        ax.add_patch(plt.Circle((hx, hy), cfg.OFFICE_RADIUS_KM, fill=False, ec=COL["office"], lw=0.8))
    for name, ((lat, lon), rad) in cfg.MIXED_HUBS.items():
        hx, hy = cran.to_km(lat, lon)
        ax.add_patch(plt.Circle((hx, hy), rad, fill=False, ec=COL["mixed"], lw=0.8))
    ax.set_xlim(-15, 15); ax.set_ylim(-15, 15); ax.set_aspect("equal")
    ax.set_xlabel("x [km] (east)"); ax.set_ylabel("y [km] (north)"); ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="lower left", markerscale=2)
    fig.tight_layout(); fig.savefig(cfg.FIGS / "classification.png", dpi=200); plt.close(fig)

    # fig: overall network load (like fig 4.21)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.plot(cfg.HOURS, net / 1000, color="#1f3fbf", lw=2, marker="o", ms=3)
    ax.set_xlabel("Time [hour]"); ax.set_ylabel("Network load [Gbps]"); ax.set_xticks(cfg.HOURS)
    ax.set_xlim(0.5, 24.5); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(cfg.FIGS / "network_load_24h.png", dpi=200); plt.close(fig)

    # combined figure for the report: profiles (left) + network load (right)
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.1))
    for c in COL:
        axs[0].plot(cfg.HOURS, prof[c], color=COL[c], lw=1.8, marker="o", ms=2.5, label=c.capitalize())
    axs[0].set_ylabel("Normalised traffic"); axs[0].set_ylim(0, 1.05); axs[0].legend(fontsize=8)
    axs[1].plot(cfg.HOURS, net / 1000, color="#1f3fbf", lw=1.8, marker="o", ms=2.5)
    axs[1].set_ylabel("Network load [Gbps]")
    for ax, t in zip(axs, ("(a) Traffic profiles", "(b) Overall network load")):
        ax.set_xlabel("Time [hour]"); ax.set_xticks(cfg.HOURS[1::2]); ax.set_xlim(0.5, 24.5)
        ax.grid(alpha=0.3); ax.set_title(t, fontsize=9)
    fig.tight_layout(); fig.savefig(cfg.FIGS / "profiles_and_load.png", dpi=200); plt.close(fig)

    print(json.dumps({k: v for k, v in out.items() if k != "rrhs"}, indent=1))


if __name__ == "__main__":
    main()
