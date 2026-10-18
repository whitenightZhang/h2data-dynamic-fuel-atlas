"""S5: hourly fuel costs and annual-average bias across original k-means groups.

Figure contract: compare cost levels and assessment bias across wind--solar
configurations and three technology scenarios. A--C show hourly costs; D--F
show paired-cost underestimation for the same classified grid cells. Retain
the original membership, equal cell weights, cost windows and violin estimator.
Remove the sampled point cloud; emphasize medians and IQRs in the S4 colors.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "source_data"
QA = ROOT / "qa"
W, H = 528, 328
INK, MUTED = "#26343B", "#6E7B82"
YEARS = (2030, 2035, 2050)
FUELS = ("ammonia", "methanol", "saf")
TITLES = ("Green ammonia", "e-methanol", "e-SAF")
NAMES = {0: "Wind-cluster", 1: "Wind–solar complementary", 2: "Solar-cluster"}
COLORS = {0: "#0072B2", 1: "#009E73", 2: "#E69F00"}
METRICS = ("cost_8760_usd_t", "underestimation_pct")
mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 7.6, "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none", "axes.spines.top": False,
    "axes.spines.right": False, "axes.linewidth": 0.55,
    "axes.grid": False, "savefig.facecolor": "white",
})
nodes = pd.read_csv(DATA / "node_data.csv")
previous = pd.read_csv(DATA / "previous_summary_statistics.csv")
assert len(nodes) == 162144
assert set(nodes.fuel) == set(FUELS) and set(nodes.year) == set(YEARS)
assert set(nodes.cluster_label) == set(NAMES)
assert nodes.groupby(["fuel", "year"]).size().eq(18016).all()
assert np.isfinite(nodes[list(METRICS)].to_numpy()).all()
assert nodes.cluster_label.map(NAMES).eq(nodes.archetype).all()
assert nodes.underestimation_pct.between(-15, 45).all()
reference = previous.set_index(["fuel", "year", "archetype", "metric"])


def cost_window(fuel):
    values = nodes.loc[nodes.fuel.eq(fuel), "cost_8760_usd_t"].to_numpy()
    lo, hi = np.quantile(values, [0.02, 0.98])
    span = hi - lo
    assert span > 0
    return max(0.0, lo - span * 0.08), hi + span * 0.08


fig = plt.figure(figsize=(W / 72, H / 72))
axes = []
statistics = []
maximum_statistic_difference = 0.0
cost_windows = {fuel: cost_window(fuel) for fuel in FUELS}
for row, metric in enumerate(METRICS):
    for col, fuel in enumerate(FUELS):
        label = "ABCDEF"[row * 3 + col]
        x0 = 48 + col * 169
        y0 = 198 if row == 0 else 60
        ax = fig.add_axes([x0 / W, y0 / H, 134 / W, 105 / H], label=label)
        axes.append(ax)
        for yi, year in enumerate(YEARS):
            for cluster in NAMES:
                values = nodes.loc[nodes.fuel.eq(fuel) & nodes.year.eq(year) &
                                   nodes.cluster_label.eq(cluster), metric].to_numpy()
                assert len(values) >= 5
                xpos = yi + (cluster - 1) * 0.20
                body = ax.violinplot([values], positions=[xpos], widths=0.190,
                                     showmeans=False, showmedians=False,
                                     showextrema=False)["bodies"][0]
                body.set_facecolor(COLORS[cluster])
                body.set_edgecolor("none")
                body.set_linewidth(0)
                body.set_alpha(0.22)
                body.set_zorder(1)
                q25, med, q75 = np.percentile(values, [25, 50, 75])
                current = {"n": len(values), "q25": q25, "median": med, "q75": q75,
                           "mean": float(np.mean(values)), "min": float(np.min(values)),
                           "max": float(np.max(values))}
                old = reference.loc[(fuel, year, NAMES[cluster], metric)]
                assert len(values) == int(old.n)
                differences = np.array([current[k] - old[k] for k in
                                        ["q25", "median", "q75", "mean", "min", "max"]])
                assert np.abs(differences).max() < 1e-8
                maximum_statistic_difference = max(maximum_statistic_difference,
                                                   float(np.abs(differences).max()))
                statistics.append({"fuel": fuel, "year": year, "cluster_label": cluster,
                                   "archetype": NAMES[cluster], "metric": metric, **current})
                ax.vlines(xpos, q25, q75, color=COLORS[cluster], linewidth=1.15, zorder=3)
                ax.scatter([xpos], [med], s=23, facecolor=COLORS[cluster],
                           edgecolor="white", linewidth=0.55, zorder=4)
        ax.set_xlim(-0.5, 2.5)
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels([str(year) for year in YEARS])
        for tick, year in zip(ax.get_xticklabels(), YEARS):
            if year == 2035:
                tick.set_fontweight("bold")
        if row == 0:
            ax.set_ylim(*cost_windows[fuel])
        else:
            ax.set_ylim(-15, 45)
            ax.set_yticks([-10, 0, 10, 20, 30, 40])
        ax.tick_params(labelsize=7.4, length=2.5, width=0.5, pad=2.5, colors=INK)
        ax.spines["left"].set_color("#74828A")
        ax.spines["bottom"].set_color("#74828A")
        ax.grid(False)
        ax.text(-0.12, 1.04, label, transform=ax.transAxes, fontsize=9.5,
                 weight="bold", color=INK, ha="left", va="bottom", clip_on=False)
        if col == 0:
            ax.set_ylabel("Hourly production\ncost (USD/t)" if row == 0 else
                          "Annual-average cost\nunderestimation (%)",
                          fontsize=7.8, color=INK, labelpad=6)
        if row == 0:
            fig.text((x0 + 2) / W, 318 / H, TITLES[col], fontsize=9,
                     weight="bold", color=INK, va="center")

fig.text(0.5, 34 / H, "Assessment year", fontsize=8, color=INK,
         ha="center", va="center")
keys = [Line2D([], [], marker="o", markersize=4.8, linestyle="none",
               markerfacecolor=COLORS[c], markeredgecolor="white", markeredgewidth=0.55,
               label=NAMES[c]) for c in NAMES]
fig.legend(handles=keys, loc="center", bbox_to_anchor=(0.5, 14.5 / H),
           ncol=3, frameon=False, fontsize=7.4, handlelength=1.0,
           handletextpad=0.4, columnspacing=1.6, labelcolor=INK)

require_matplotlib_panel_alignment(fig, axes=axes, panel_ids=list("ABCDEF"),
                                   row_groups=[list("ABC"), list("DEF")],
                                   column_groups=[list("AD"), list("BE"), list("CF")],
                                   json_out=QA / "panel_alignment.json",
                                   overlay_svg=QA / "panel_alignment.svg",
                                   tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True)
prefix = ROOT / "Figure_S5_Costs_and_Bias"
fig.savefig(str(prefix) + ".pdf")
fig.savefig(str(prefix) + ".svg")
fig.savefig(str(prefix) + ".png", dpi=600)
plt.close(fig)
pd.DataFrame(statistics).to_csv(DATA / "plotted_summary_statistics.csv", index=False)
(QA / "data_and_display_checks.json").write_text(json.dumps({
    "figure": "S5", "node_rows": len(nodes), "fuel_year_cells": 18016,
    "original_cluster_membership_retained": True, "additional_data_exclusions": 0,
    "all_observations_used_for_distributions_and_statistics": True,
    "statistics_compared": len(statistics),
    "maximum_difference_from_previous_statistics": maximum_statistic_difference,
    "cost_axis_windows_retained": {fuel: list(window) for fuel, window in cost_windows.items()},
    "underestimation_axis_range": [-15, 45],
    "observed_underestimation_range": [float(nodes.underestimation_pct.min()),
                                      float(nodes.underestimation_pct.max())],
    "sampled_scatter_cloud_displayed": False, "gridlines": False,
    "source_size_pt": [W, H], "SI_include_width": "0.98 textwidth",
    "color_mapping_matches_S4": COLORS,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"pdf": str(prefix) + ".pdf", "node_rows": len(nodes),
                  "summary_rows": len(statistics),
                  "maximum_statistic_difference": maximum_statistic_difference}))
