"""Hydrogen benchmark sensitivity: directly labelled empirical curves.

Figure contract: the share of paired finite-cost grid cells classified as
competitive only by annual-average costs depends on both benchmark and year.
One quantitative hero panel retains every threshold observation; the unboxed
readout identifies the fixed 2 USD/kg benchmark used in the main text.
The CSV maps year to series, benchmark_usd_kg to x, and share_percent to y.
Counts and matched_locations verify the equal-grid-cell denominator.
No uncertainty interval applies to these complete empirical grid-cell shares.
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
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_panel_alignment import require_matplotlib_panel_alignment

WIDTH_PT, HEIGHT_PT = 528, 260
FINAL_WIDTH_PT = 456.9
BENCHMARK = 2.0
YEARS = (2030, 2035, 2050)
COLORS = {2030: "#277A89", 2035: "#CF8A30", 2050: "#8A759C"}
MARKERS = {2030: "o", 2035: "s", 2050: "D"}
DENOMINATORS = {2030: 228090, 2035: 228093, 2050: 228046}
SOURCE_SHA256 = "3a854751680d563784b05ed4a199d3d91c43f77584c4279996c78f6afc440cca"
INK, AXIS, MUTED = "#263238", "#89969B", "#647278"

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size": 7.6,
    "axes.labelsize": 8.2,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "path.simplify": False,
    "axes.linewidth": 0.55,
    "axes.edgecolor": AXIS,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.major.size": 2.6,
    "ytick.major.size": 2.6,
    "xtick.major.width": 0.55,
    "ytick.major.width": 0.55,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "savefig.facecolor": "white",
})


def load_data():
    source = HERE / "source_data/benchmark_sensitivity_curve.csv"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1053
    assert {int(row["year"]) for row in rows} == set(YEARS)
    data, summary = {}, []
    for year in YEARS:
        group = [row for row in rows if int(row["year"]) == year]
        x = np.array([float(row["benchmark_usd_kg"]) for row in group])
        y = np.array([float(row["share_percent"]) for row in group])
        counts = np.array([int(row["static_pass_hourly_fail_count"]) for row in group])
        n = np.array([int(row["matched_locations"]) for row in group])
        np.testing.assert_array_equal(x, np.round(np.arange(0.5, 4.001, 0.01), 2))
        assert np.all(np.diff(x) > 0)
        assert np.all(np.isfinite(y)) and np.all((y >= 0) & (y <= 100))
        assert np.all(n == DENOMINATORS[year])
        np.testing.assert_allclose(y, 100 * counts / n, rtol=0, atol=1e-12)
        baseline = float(y[x == BENCHMARK][0])
        peak = int(np.argmax(y))
        data[year] = (x, y)
        summary.append({
            "year": year, "curve_points": len(group),
            "paired_grid_cells": int(n[0]),
            "benchmark_USD_per_kg": BENCHMARK,
            "share_percent": baseline, "display_share": f"{baseline:.1f}%",
            "peak_benchmark_USD_per_kg": float(x[peak]),
            "peak_share_percent": float(y[peak]),
        })
    return source, data, summary


def main():
    source, data, summary = load_data()
    qa = HERE / "qa"
    qa.mkdir(exist_ok=True)
    fig = plt.figure(figsize=(WIDTH_PT / 72, HEIGHT_PT / 72), facecolor="white")
    ax = fig.add_axes([59 / WIDTH_PT, 43 / HEIGHT_PT,
                       452 / WIDTH_PT, 182 / HEIGHT_PT], label="S14")
    ax.set_xlim(0.5, 4.0)
    ax.set_ylim(0, 53)
    ax.set_xticks([0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4],
                  ["0.5", "1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "4.0"])
    ax.set_yticks([0, 10, 20, 30, 40, 50])
    ax.spines["left"].set_bounds(0, 50)
    ax.tick_params(axis="both", pad=3.2)
    ax.grid(False)
    ax.set_xlabel("Hydrogen cost benchmark (USD/kg)", labelpad=8.2)
    ax.set_ylabel("Share of grid cells (%)", labelpad=10,
                  rotation_mode="anchor")
    fig.text(59 / WIDTH_PT, 246 / HEIGHT_PT,
             "Annual-average cost ≤ benchmark < hourly cost",
             fontsize=8.2, ha="left", va="center", color=INK)

    # The sole threshold guide links the curves to the main-text benchmark.
    ax.plot([BENCHMARK, BENCHMARK], [0, 50], color="#AEB9BE",
            linewidth=0.65, linestyle=(0, (2.5, 3.0)), zorder=0)

    for year in YEARS:
        x, y = data[year]
        color = COLORS[year]
        line, = ax.plot(x, y, color=color, linewidth=1.5,
                        solid_capstyle="round", solid_joinstyle="round", zorder=3)
        np.testing.assert_array_equal(line.get_xdata(), x)
        np.testing.assert_array_equal(line.get_ydata(), y)
        baseline = float(y[x == BENCHMARK][0])
        ax.plot(BENCHMARK, baseline, linestyle="none", marker=MARKERS[year],
                markersize=5, markerfacecolor=color, markeredgecolor="white",
                markeredgewidth=0.7, zorder=5)
        peak = int(np.argmax(y))
        ax.annotate(str(year), xy=(x[peak], y[peak]), xytext=(0, 8),
                    textcoords="offset points", ha="center", va="bottom",
                    color=color, fontsize=8.4, fontweight="bold", zorder=6)

    # Compact numeric readout occupies the empty upper-right data region.
    ax.text(3.01, 48.6, "At 2 USD/kg", fontsize=8.4, fontweight="bold",
            ha="left", va="center")
    ax.text(3.01, 44.7, "Main-text benchmark", fontsize=7.2, color=MUTED,
            ha="left", va="center")
    for record, row_y in zip(summary, (39.4, 34.8, 30.2)):
        year = record["year"]
        ax.plot(3.025, row_y, linestyle="none", marker=MARKERS[year],
                markersize=4.5, color=COLORS[year], markeredgewidth=0)
        ax.text(3.105, row_y, str(year), fontsize=7.8, ha="left", va="center")
        ax.text(3.78, row_y, record["display_share"], fontsize=9.2,
                color=COLORS[year], fontweight="bold", ha="right", va="center")

    ax.get_xticklabels()[3].set_fontweight("bold")
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig, axes=[ax], panel_ids=["S14"], require_panel_labels=False,
        json_out=qa / "panel_alignment.json", overlay_svg=qa / "panel_alignment.svg",
        tolerance_pt=1.5, strict=True)

    filename = HERE / "Figure_S14_Hydrogen_Benchmark_Sensitivity"
    fig.savefig(filename.with_suffix(".pdf"))
    fig.savefig(filename.with_suffix(".svg"))
    fig.savefig(filename.with_suffix(".png"), dpi=300)
    buffer = BytesIO()
    fig.savefig(buffer, format="tiff", dpi=600)
    with Image.open(buffer) as rendered:
        rgb = BytesIO()
        rendered.convert("RGB").save(rgb, format="TIFF", compression="tiff_lzw", dpi=(600, 600))
        filename.with_suffix(".tiff").write_bytes(rgb.getvalue())
    scale = FINAL_WIDTH_PT / WIDTH_PT
    plt.close(fig)
    (qa / "data_integrity.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "rows_supplied": 1053, "rows_displayed": 1053, "exclusions": 0,
        "coordinates": "exact source benchmark and share values",
        "path_simplification": False,
        "smoothing": False, "resampling": False, "model_solves": 0,
        "source_dimensions_pt": [WIDTH_PT, HEIGHT_PT],
        "intended_insert_width_pt": FINAL_WIDTH_PT,
        "intended_insert_height_pt": HEIGHT_PT * scale,
        "smallest_source_glyph_pt": 7.2,
        "smallest_inserted_glyph_pt": 7.2 * scale,
        "series": summary,
    }, indent=2), encoding="utf-8")
    print("S14 exported; all 1,053 source values retained without path simplification.")
    print("2 USD/kg: " + ", ".join(f"{r['year']}: {r['display_share']}" for r in summary))


if __name__ == "__main__":
    main()
