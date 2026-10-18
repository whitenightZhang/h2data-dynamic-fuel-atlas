"""Regional CAPEX inputs as unconnected scenario dots.

Figure contract: compare the absolute regional cost assumptions for three
technology scenarios, without implying a continuous annual learning path.
Panel A is solar PV; panel B is onshore wind. All 31 regional cost assignments
are retained, ordered by the corresponding S2 display regions. Literature
percentile intervals retain the existing study-scenario interpolation rule.
The model inputs and production results are not modified by this figure.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "source_data"
QA = ROOT / "qa"
W, H = 528, 636
INK = "#26343B"
MUTED = "#6E7B82"
YEARS = (2030, 2035, 2050)
YEAR_COLORS = ("#4B729B", "#D69453", "#428E80")
YEAR_MARKERS = ("o", "D", "s")
GROUPS = ("Americas", "Europe", "Africa and Middle East", "Asia and Oceania")
mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 7.6, "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none", "axes.spines.top": False,
    "axes.spines.right": False, "axes.spines.left": False,
    "axes.linewidth": 0.5, "savefig.facecolor": "white",
})

costs = pd.read_csv(DATA / "regional_capex_inputs.csv")
regions = pd.read_csv(DATA / "display_region_mapping.csv")
literature = pd.read_csv(DATA / "literature_capex_scenarios.csv")
assert len(costs) == 62 and costs.groupby("Type").size().eq(31).all()
assert not costs.duplicated(["region_code", "Type"]).any()
assert np.isfinite(costs[[f"{year}ATB" for year in YEARS]].to_numpy()).all()

code_lookup = {}
for row in regions.to_dict("records"):
    for code in str(row["raster_codes"]).split(";"):
        code_lookup[int(code)] = row
assert set(costs.region_code) == set(code_lookup)

rows = []
headers = []
y = 0.0
for group in GROUPS:
    headers.append((group, y))
    y += 1.0
    for display in regions.loc[regions.legend_group.eq(group)].to_dict("records"):
        for code_text in str(display["raster_codes"]).split(";"):
            code = int(code_text)
            label = display["display_name"]
            # Retain both separate cost assignments within these mapped regions.
            if code == 6:
                label = "Colombia"
            elif code == 27:
                label = "Pakistan"
            rows.append({"code": code, "label": label, "color": display["color"],
                         "group": group, "y": y})
            y += 1.0
    y += 0.1
assert len(rows) == 31 and len({r["code"] for r in rows}) == 31
literature_header_y = y + 0.9
literature_rows = {year: literature_header_y + 1.0 + j for j, year in enumerate(YEARS)}
ymax = max(literature_rows.values()) + 0.75


def reference_percentiles(sector):
    d = literature.loc[literature.sector.eq(sector)].copy()
    matrix = []
    scenario_names = []
    for name, g in d.groupby("Study_and_Scenario", sort=True):
        g = g.dropna(subset=["year", "value"]).drop_duplicates("year").sort_values("year")
        if len(g) < 2:
            values = np.full(len(YEARS), np.nan)
        else:
            # Same PCHIP interpolation and terminal-value extension as the prior
            # literature comparison. No regional model cost is interpolated.
            values = PchipInterpolator(g.year.to_numpy(), g.value.to_numpy(),
                                       extrapolate=False)(np.array(YEARS))
            values[np.array(YEARS) > g.year.iloc[-1]] = g.value.iloc[-1]
        matrix.append(values)
        scenario_names.append(name)
    matrix = np.array(matrix)
    n = np.isfinite(matrix).sum(axis=0)
    assert (n > 0).all()
    return np.nanpercentile(matrix, [0, 5, 25, 75, 95, 100], axis=0), n, scenario_names


fig = plt.figure(figsize=(W / 72, H / 72))
axes = [fig.add_axes([168 / W, 81 / H, 164 / W, 500 / H], label="solar_pv"),
        fig.add_axes([354 / W, 81 / H, 164 / W, 500 / H], label="onshore_wind")]
sectors = ("Solar PV", "Onshore Wind")
limits = ((0, 1500), (0, 2600))
reference_records = []

for ax, sector, lim in zip(axes, sectors, limits):
    ax.set_xlim(*lim)
    ax.set_ylim(ymax, -0.8)
    ax.set_yticks([])
    ax.set_xticks([0, 500, 1000, 1500] if sector == "Solar PV" else [0, 1000, 2000])
    ax.tick_params(axis="x", labelsize=7.4, length=2.5, width=0.5, colors=INK, pad=3.5)
    ax.set_xlabel("Installed capital cost (USD/kW)", fontsize=7.8, color=INK, labelpad=7)
    ax.grid(axis="x", color="#E7EAEC", linewidth=0.4, zorder=0)
    ax.spines["bottom"].set_color("#7B878D")
    for _, hy in headers[1:]:
        ax.axhline(hy - 0.45, color="#D6DDE0", linewidth=0.4, zorder=0)
    ax.axhline(literature_header_y - 0.5, color="#BBC5CA", linewidth=0.5, zorder=0)
    subset = costs.loc[costs.Type.eq(sector)].set_index("region_code")
    for j, year in enumerate(YEARS):
        offset = (j - 1) * 0.20
        values = np.array([subset.at[r["code"], f"{year}ATB"] for r in rows])
        ypos = np.array([r["y"] for r in rows]) + offset
        ax.scatter(values, ypos, s=12, marker=YEAR_MARKERS[j],
                   facecolor=YEAR_COLORS[j], edgecolor="white", linewidth=0.25,
                   zorder=3, label=str(year))
    pct, n, names = reference_percentiles(sector)
    for j, year in enumerate(YEARS):
        ry = literature_rows[year]
        ax.plot(pct[[0, 5], j], [ry, ry], color="#D3DADF", linewidth=1.2,
                solid_capstyle="butt", zorder=2)
        ax.plot(pct[[1, 4], j], [ry, ry], color="#ADB8BF", linewidth=3.6,
                solid_capstyle="butt", zorder=2)
        ax.plot(pct[[2, 3], j], [ry, ry], color="#6F818B", linewidth=5.8,
                solid_capstyle="butt", zorder=2)
        reference_records.append({"sector": sector, "year": year,
                                  "scenario_count": int(n[j]),
                                  **{key: float(pct[k, j]) for k, key in
                                     enumerate(["min", "p05", "p25", "p75", "p95", "max"])}})

fig.canvas.draw()


def row_height(yvalue):
    return fig.transFigure.inverted().transform(axes[0].transData.transform((0, yvalue)))[1]


for group, hy in headers:
    fig.text(8 / W, row_height(hy), group, ha="left", va="center",
             fontsize=7.8, color=INK, weight="bold")
for row in rows:
    fy = row_height(row["y"])
    fig.text(149 / W, fy, row["label"], ha="right", va="center", fontsize=7.6, color=INK)
fig.text(8 / W, row_height(literature_header_y), "Literature ranges", ha="left", va="center",
         fontsize=7.8, weight="bold", color=INK)
for year, ry in literature_rows.items():
    fig.text(149 / W, row_height(ry), str(year), ha="right", va="center", fontsize=7.6, color=MUTED)

fig.text(168 / W, 599 / H, "A", fontsize=10.2, weight="bold", color=INK, va="center")
fig.text(181 / W, 599 / H, "Solar PV", fontsize=9, weight="bold", color=INK, va="center")
fig.text(354 / W, 599 / H, "B", fontsize=10.2, weight="bold", color=INK, va="center")
fig.text(367 / W, 599 / H, "Onshore wind", fontsize=9, weight="bold", color=INK, va="center")

# A compact year key replaces the former region-color legend.
for j, year in enumerate(YEARS):
    px = 185 + j * 70
    fig.add_artist(plt.Line2D([px / W], [621 / H], transform=fig.transFigure,
                             marker=YEAR_MARKERS[j], markersize=3.7, linestyle="none",
                             markerfacecolor=YEAR_COLORS[j], markeredgecolor="white",
                             markeredgewidth=0.25))
    fig.text((px + 9) / W, 621 / H, str(year), fontsize=7.8, va="center", color=INK)

for px, color, lw, label in [(164, "#D3DADF", 1.2, "Min-max"),
                           (264, "#ADB8BF", 3.6, "5th-95th"),
                           (367, "#6F818B", 5.8, "25th-75th")]:
    fig.add_artist(plt.Line2D([px / W, (px + 16) / W], [28 / H, 28 / H],
                             transform=fig.transFigure, linewidth=lw, color=color,
                             solid_capstyle="butt"))
    fig.text((px + 22) / W, 28 / H, label, fontsize=7.2, va="center", color=MUTED)

require_matplotlib_panel_alignment(fig, json_out=QA / "panel_alignment.json",
                                   overlay_svg=QA / "panel_alignment.svg",
                                   row_groups=[["solar_pv", "onshore_wind"]],
                                   tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True)
prefix = ROOT / "Figure_S3_Regional_CAPEX"
fig.savefig(str(prefix) + ".pdf")
fig.savefig(str(prefix) + ".svg")
fig.savefig(str(prefix) + ".png", dpi=600)
plt.close(fig)
pd.DataFrame(reference_records).to_csv(DATA / "literature_percentile_intervals.csv", index=False)
(QA / "data_and_display_checks.json").write_text(json.dumps({
    "figure": "S3", "source_assignment_count": 31, "technology_count": 2,
    "scenario_years": list(YEARS), "regional_points": 186,
    "regional_cost_interpolation": False, "annual_path_lines": False,
    "regional_color_swatches": False,
    "cost_inputs_or_model_results_changed": False,
    "separate_cost_assignments_retained": ["Colombia", "Pakistan"],
    "literature_rule": "PCHIP per study-scenario; constant extension after terminal year; equal scenario weights",
    "literature_intervals": reference_records,
    "physical_size_pt": [W, H], "SI_include_width": "0.95 textwidth",
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"pdf": str(prefix) + ".pdf", "regional_points": 186,
                  "size_pt": [W, H], "reference_intervals": reference_records}))
