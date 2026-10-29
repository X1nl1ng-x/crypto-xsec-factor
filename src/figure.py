"""Figure 1: mean and median weekly return of the five cv90 groups, in-sample and out-of-sample."""
import matplotlib.pyplot as plt
import helpers
from helpers import load_weekly, quintile_returns

INK, MUTED, GRID, ZERO = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
COLORS = {"mean": "#2a78d6", "median": "#eb6834"}        # blue and orange

fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
for ax, period, title in [(axes[0], "in", "In-sample (May 2020 - Dec 2024)"),
                          (axes[1], "out", "Out-of-sample (Jan 2025 - Sep 2026)")]:
    helpers.PERIOD = period                                # which sample load_weekly returns
    all_contracts, contracts_90d = load_weekly()
    for stat in ["mean", "median"]:
        avg = quintile_returns(contracts_90d, "cv90", stat=stat).mean() * 100   # % per week
        y = [avg[1], avg[2], avg[3], avg[4], avg[5]]
        ax.plot([1, 2, 3, 4, 5], y, color=COLORS[stat], linewidth=2, marker="o", markersize=6, label=stat)
        ax.text(5.15, y[4], stat, color=INK, fontsize=9, va="center")            # label at the line end
    ax.axhline(0, color=ZERO, linewidth=1)                                         # zero line
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.set_xticks([1, 2, 3, 4, 5], ["Q1\nstable", "Q2", "Q3", "Q4", "Q5\nunstable"])
    ax.set_xlim(0.7, 5.9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=MUTED, labelsize=9)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(ZERO)

axes[0].set_ylabel("Weekly return (%)", color=MUTED, fontsize=9)
axes[0].legend(loc="lower left", frameon=False, fontsize=9)
fig.supxlabel("Groups of coins sorted by the variability of daily dollar volume (cv90)", color=MUTED, fontsize=9)
fig.tight_layout()
fig.savefig("results/figure1_mean_vs_median.png", dpi=200)
print("saved results/figure1_mean_vs_median.png")