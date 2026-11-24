"""Common matplotlib style of the phase-2 figures (same look as phase 1)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as cfg

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
TRAFFIC_COLORS = cfg.TRAFFIC_COLORS
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "legend.frameon": False, "savefig.dpi": 150, "figure.dpi": 100})


def save(fig, name):
    fig.tight_layout(); fig.savefig(cfg.P2_FIG / name); plt.close(fig)


def mbph_axis(ax, axis="y"):
    """Thousands separators on a load axis in MBph (e.g. 4,000,000)."""
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _: f"{v:,.0f}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)
