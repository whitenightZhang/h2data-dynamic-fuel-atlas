"""Weather-year robustness of paired methanol costs at the three Fig. 6 sites.

Uses the supplied nine optimized results without solving or altering inputs.
Annual-average and hourly estimates are paired within, never between, years.

Figure contract: a quantitative grid testing weather-year robustness of the
annual-average cost underestimate, stratified by the three renewable clusters.
The upper tier gives paired absolute costs; the lower tier gives the defined
relative discrepancy. All nine deterministic scenarios are retained without
aggregation or inferential intervals. Style-only revision of the supplied plot.
"""
from pathlib import Path
from io import BytesIO
import csv
import hashlib
import json
import sys

import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_panel_alignment import require_matplotlib_panel_alignment

WIDTH_PT, HEIGHT_PT = 528, 294
FINAL_WIDTH_PT = 456.9
INK = "#263238"
TEAL = "#286879"
ORANGE = "#CF8A30"
GRAY = "#89969B"
YEARS = (2021, 2022, 2023)
SITES = (
    ("W", "Wind-cluster", 61.5, -99.75),
    ("H", "Wind–solar complementary", 17.5, 18.25),
    ("S", "Solar-cluster", 37.5, 34.75),
)

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size": 7.6,
    "axes.labelsize": 8,
    "xtick.labelsize": 7.4,
    "ytick.labelsize": 7.2,
    "legend.fontsize": 7.6,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "axes.linewidth": 0.55,
    "axes.edgecolor": GRAY,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.major.size": 0,
    "ytick.major.size": 2.5,
    "ytick.major.width": 0.55,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "legend.frameon": False,
    "savefig.facecolor": "white",
})


def load_data():
    source = HERE / "source_data" / "weather_sensitivity_results.csv"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == (
        "b84811ff907add313d68998c9234c8994130a08da79230d00ad1050dcc9ea1fe")
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 9, "Expected all nine site-year results."
    keyed = {(r["site"], int(r["weather_year"])): r for r in rows}
    assert len(keyed) == 9, "Site-year keys must be unique."
    assert set(keyed) == {(s[0], y) for s in SITES for y in YEARS}
    for key, row in keyed.items():
        assert int(row["technology_year"]) == 2035
        assert int(row["solver_status"]) == 2
        site = next(s for s in SITES if s[0] == key[0])
        assert (float(row["latitude"]), float(row["longitude"])) == site[2:]
        annual = float(row["annual_average_cost_USD_per_t"])
        hourly = float(row["hourly_cost_USD_per_t"])
        under = float(row["underestimation_percent"])
        assert np.isfinite([annual, hourly, under]).all()
        assert hourly > 0
        np.testing.assert_allclose(under, 100 * (hourly - annual) / hourly,
                                   rtol=0, atol=1e-10)
    return source, keyed


def main():
    source, keyed = load_data()
    qa = HERE / "qa"
    qa.mkdir(exist_ok=True)
    fig = plt.figure(figsize=(WIDTH_PT / 72, HEIGHT_PT / 72))
    xs, panel_width = (59, 217, 375), 136
    axes, identifiers, heading_artists, label_artists = [], [], [], []
    display_rows = []

    for index, (site, title, _, _) in enumerate(SITES):
        letter = chr(65 + index)
        left = xs[index]
        cost_ax = fig.add_axes([left / WIDTH_PT, 129 / HEIGHT_PT,
                                panel_width / WIDTH_PT, 111 / HEIGHT_PT],
                               label=f"{letter}-cost")
        bias_ax = fig.add_axes([left / WIDTH_PT, 39 / HEIGHT_PT,
                                panel_width / WIDTH_PT, 64 / HEIGHT_PT],
                               label=f"{letter}-underestimation")
        axes.extend([cost_ax, bias_ax])
        identifiers.extend([f"{letter}-cost", f"{letter}-underestimation"])

        label_artists.append(fig.text(left / WIDTH_PT, 281 / HEIGHT_PT,
                                      letter, fontsize=9.2, fontweight="bold",
                                      va="center", ha="left"))
        heading_artists.append(fig.text((left + 14) / WIDTH_PT, 281 / HEIGHT_PT,
                                        title, fontsize=8, fontweight="bold",
                                        va="center", ha="left"))

        for axis in (cost_ax, bias_ax):
            axis.set_facecolor("none")
            axis.set_xlim(-0.52, 2.52)
            axis.set_xticks([0, 1, 2])
            axis.tick_params(axis="y", pad=3)
            axis.set_axisbelow(True)
        cost_ax.set_ylim(430, 780)
        cost_ax.set_yticks([450, 550, 650, 750])
        cost_ax.set_xticklabels([])
        cost_ax.spines["bottom"].set_visible(False)
        bias_ax.set_ylim(0, 32)
        bias_ax.set_yticks([0, 10, 20, 30])
        bias_ax.set_xticklabels([str(year) for year in YEARS])
        bias_ax.tick_params(axis="x", pad=6)

        if index:
            cost_ax.set_yticklabels([])
            bias_ax.set_yticklabels([])
        else:
            cost_ax.set_ylabel("Production cost (USD/t)", labelpad=10)
            bias_ax.set_ylabel("Cost underestimation (%)", labelpad=10)

        for x, year in enumerate(YEARS):
            row = keyed[(site, year)]
            annual = float(row["annual_average_cost_USD_per_t"])
            hourly = float(row["hourly_cost_USD_per_t"])
            under = float(row["underestimation_percent"])
            # Each segment links the two resolutions for one weather year.
            cost_ax.plot([x, x], [annual, hourly], color=ORANGE,
                         linewidth=1.6, solid_capstyle="butt", zorder=2)
            cost_ax.plot(x, annual, marker="o", markersize=4.8,
                         markerfacecolor="white", markeredgecolor=GRAY,
                         markeredgewidth=1.05, linestyle="none", zorder=3)
            cost_ax.plot(x, hourly, marker="o", markersize=4.8,
                         markerfacecolor=TEAL, markeredgecolor=TEAL,
                         markeredgewidth=0.8, linestyle="none", zorder=3)
            cost_ax.annotate(f"{annual:.1f}", (x, annual), xytext=(0, -6),
                             textcoords="offset points", ha="center", va="top",
                             fontsize=7.5, color=INK)
            cost_ax.annotate(f"{hourly:.1f}", (x, hourly), xytext=(0, 6),
                             textcoords="offset points", ha="center", va="bottom",
                             fontsize=7.5, color=INK)
            bias_ax.bar(x, under, width=0.34, color=ORANGE,
                        linewidth=0, zorder=2)
            bias_ax.annotate(f"{under:.1f}%", (x, under), xytext=(0, 4),
                             textcoords="offset points", ha="center", va="bottom",
                             fontsize=7.5, color=INK)
            display_rows.append({
                "site": site, "weather_year": year,
                "annual_average_cost_USD_per_t": annual,
                "hourly_cost_USD_per_t": hourly,
                "underestimation_percent": under,
                "annual_average_display": f"{annual:.1f}",
                "hourly_display": f"{hourly:.1f}",
                "underestimation_display": f"{under:.1f}%",
            })

    handles = [
        Line2D([], [], marker="o", markersize=4.8, markerfacecolor="white",
               markeredgecolor=GRAY, markeredgewidth=1.05, linestyle="none"),
        Line2D([], [], marker="o", markersize=4.8, markerfacecolor=TEAL,
               markeredgecolor=TEAL, markeredgewidth=0.8, linestyle="none"),
        Line2D([], [], color=ORANGE, linewidth=1.6),
    ]
    fig.legend(handles, ["Annual-average", "Hourly", "Cost gap"], loc="center",
               bbox_to_anchor=(285 / WIDTH_PT, 258 / HEIGHT_PT), ncol=3,
               handlelength=1.25, handletextpad=0.6, columnspacing=2.0,
               borderpad=0)
    fig.text(285 / WIDTH_PT, 9 / HEIGHT_PT, "Weather year",
             ha="center", va="center", fontsize=8)

    # Physical plot-area measurements, after final font/layout rendering.
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig, axes=axes, panel_ids=identifiers,
        row_groups=[["A-cost", "B-cost", "C-cost"],
                    ["A-underestimation", "B-underestimation", "C-underestimation"]],
        column_groups=[[f"{p}-cost", f"{p}-underestimation"] for p in "ABC"],
        json_out=qa / "panel_alignment.json",
        overlay_svg=qa / "panel_alignment.svg",
        tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True,
    )
    renderer = fig.canvas.get_renderer()
    labels = []
    for artist in label_artists + heading_artists:
        bbox = artist.get_window_extent(renderer).transformed(
            fig.dpi_scale_trans.inverted())
        anchor = artist.get_transform().transform(artist.get_position())
        anchor_pt = fig.dpi_scale_trans.inverted().transform(anchor) * 72
        labels.append({"text": artist.get_text(),
                       "anchor_pt": anchor_pt.tolist(),
                       "bbox_pt": [float(v * 72) for v in bbox.extents]})
    assert np.ptp([item["anchor_pt"][1] for item in labels]) <= 1.5
    (qa / "heading_alignment.json").write_text(json.dumps({
        "verdict": "PASS", "tolerance_pt": 1.5,
        "note": "Uppercase labels follow the manuscript figure convention.",
        "rendered_labels": labels,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    filename = HERE / "Figure_S11_Methanol_Weather_Sensitivity"
    fig.savefig(filename.with_suffix(".png"), dpi=300)
    fig.savefig(filename.with_suffix(".pdf"), dpi=600)
    fig.savefig(filename.with_suffix(".svg"))
    buffer = BytesIO()
    fig.savefig(buffer, format="tiff", dpi=600,
                 pil_kwargs={"compression": "tiff_lzw"})
    from PIL import Image
    with Image.open(buffer) as rendered:
        rgb_buffer = BytesIO()
        rendered.convert("RGB").save(rgb_buffer, format="TIFF",
                                     compression="tiff_lzw", dpi=(600, 600))
        filename.with_suffix(".tiff").write_bytes(rgb_buffer.getvalue())
    plt.close(fig)

    (qa / "data_integrity.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "observations": 9, "sites": 3, "weather_years": list(YEARS),
        "technology_year": 2035, "optimal_status_rows": 9,
        "exclusions": 0, "recomputed_model_solutions": 0,
        "source_dimensions_pt": [WIDTH_PT, HEIGHT_PT],
        "intended_insert_width_pt": FINAL_WIDTH_PT,
        "percentage_formula": "100 * (hourly - annual_average) / hourly",
        "percentage_check_absolute_tolerance": 1e-10,
        "rows": display_rows,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
