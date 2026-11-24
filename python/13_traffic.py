"""Step 13 (phase 2) - Traffic of every RRH during the day.

Reads the phase-1 scenario (phase1/data/scenario.json: RRHs and their traffic pattern) and the week-1
dataset (number of merged stations and technologies of each site), and writes:
  phase2/data/rrh_traffic.csv   busy-hour traffic of every RRH and its 24 h traffic in MBph
  phase2/data/traffic.json      peak hour, network load per hour, totals by pattern
Figures: phase2/figures/fig01_profiles.png (24 h profiles and peak hour),
         fig02_network_load.png (review 1c, thesis fig. 4.21).
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as cfg
import p2_lib as P
from p2_style import save, INK2, TRAFFIC_COLORS, mbph_axis

PATTERNS = ["residential", "office", "mixed"]


def main():
    rrhs, pools, sets = P.load_scenario()
    peak = P.peak_mbph(rrhs)
    pat = [r["traffic"] for r in rrhs]
    T = P.traffic_matrix(peak, pat)
    h_peak = P.balance_hour()
    net = T.sum(axis=0)
    by_pat = {c: T[np.array(pat) == c].sum(axis=0) for c in PATTERNS}

    df = pd.DataFrame({"rrh_id": [r["rrh_id"] for r in rrhs], "traffic": pat,
                       "is_synthetic": [r["is_synthetic"] for r in rrhs], "peak_mbph": peak.round(1)})
    for h in cfg.HOURS:
        df[f"h{h:02d}"] = T[:, h - 1].round(1)
    df.to_csv(cfg.P2_DATA / "rrh_traffic.csv", index=False)

    out = {"peak_hour": h_peak, "peak_hour_rule": cfg.BALANCE_HOUR,
           "sum_of_profiles": [round(float(v), 3) for v in sum(np.array(v) for v in cfg.PROFILES.values())],
           "network_max_hour": int(np.argmax(net)) + 1, "network_min_hour": int(np.argmin(net)) + 1,
           "network_load_mbph": [round(float(v)) for v in net],
           "load_by_pattern_mbph": {c: [round(float(v)) for v in by_pat[c]] for c in PATTERNS},
           "rrh_count_by_pattern": {c: pat.count(c) for c in PATTERNS},
           "peak_mbph_per_rrh": {"min": round(float(peak.min())), "mean": round(float(peak.mean())),
                                 "max": round(float(peak.max()))}}
    (cfg.P2_DATA / "traffic.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    # fig01: the three profiles and their sum (which fixes the peak hour)
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw=dict(width_ratios=[1.35, 1]))
    for c in PATTERNS:
        axs[0].plot(cfg.HOURS, cfg.PROFILES[c], "-o", ms=3, lw=2, color=TRAFFIC_COLORS[c], label=c.capitalize())
    axs[0].set_ylim(0, 1.05); axs[0].set_ylabel("normalised traffic")
    axs[0].set_title("(a) 24 h traffic profiles (thesis fig. E.1)", loc="left", fontsize=10)
    axs[0].legend(loc="upper left", fontsize=8)
    s = np.array(out["sum_of_profiles"])
    axs[1].bar(cfg.HOURS, s, color="#c9c3b8", width=0.75)
    axs[1].bar([h_peak], [s[h_peak - 1]], color=INK2, width=0.75)
    axs[1].text(h_peak, s[h_peak - 1] + 0.05, f"{h_peak}:00", ha="center", fontsize=8.5)
    axs[1].set_ylabel("sum of the three profiles")
    axs[1].set_title("(b) Peak hour: maximum of the sum", loc="left", fontsize=10)
    for ax in axs:
        ax.set_xticks(cfg.HOURS[1::2]); ax.set_xlim(0.3, 24.7); ax.set_xlabel("hour of the day")
    save(fig, "fig01_profiles.png")

    # fig02: overall network load during the day (review 1c, thesis fig. 4.21)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    bottom = np.zeros(24)
    for c in PATTERNS:
        ax.bar(cfg.HOURS, by_pat[c], bottom=bottom, width=0.75, color=TRAFFIC_COLORS[c],
               edgecolor="white", linewidth=0.6, label=f"{c} RRHs ({pat.count(c)})")
        bottom += by_pat[c]
    ax.set_xticks(cfg.HOURS); ax.set_xlim(0.3, 24.7); ax.set_ylim(0, net.max() * 1.15)
    ax.set_xlabel("hour of the day"); ax.set_ylabel("network load [MBph]"); mbph_axis(ax)
    ax.legend(loc="upper left", fontsize=8, ncol=3)
    ax.set_title(f"Overall network load during the day, {len(rrhs)} RRHs (as thesis fig. 4.21)", loc="left",
                 fontsize=10)
    save(fig, "fig02_network_load.png")
    print(json.dumps({k: v for k, v in out.items() if "load" not in k and k != "sum_of_profiles"}, indent=1))


if __name__ == "__main__":
    main()
