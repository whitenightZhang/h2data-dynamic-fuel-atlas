"""Carbon-price sensitivity of the potential-weighted competitiveness discrepancy.

All defined samples from the selected scenarios are drawn unchanged. NaN ratios
break the plotted line. The original CSV retains all supplied scenarios.
No production model is solved, and no smoothing or resampling is performed.
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

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_panel_alignment import require_matplotlib_panel_alignment

WIDTH_PT, HEIGHT_PT = 528, 230
FINAL_WIDTH_PT = 456.9
INK = "#263238"
ORANGE = "#CF8A30"
GRAY = "#89969B"
X_FIELD = "carbon_price_USD_per_tCO2"
Y_FIELD = "uncompetitive_share_of_annual_average_potential_percent"
INPUT_SERIES = (("ammonia", 2030), ("methanol", 2035), ("saf", 2035), ("saf", 2050))
SERIES = (("ammonia", 2030), ("methanol", 2035), ("saf", 2050))

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size": 7.6,
    "axes.labelsize": 8,
    "xtick.labelsize": 7.2,
    "ytick.labelsize": 7.2,
    "legend.fontsize": 7.4,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "axes.linewidth": 0.55,
    "axes.edgecolor": GRAY,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.major.size": 2.8,
    "ytick.major.size": 2.8,
    "xtick.major.width": 0.55,
    "ytick.major.width": 0.55,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "legend.frameon": False,
    "savefig.facecolor": "white",
})


def load_data():
    source = HERE / "source_data" / "carbon_price_sensitivity_plot.csv"
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 164
    assert {(r["fuel"], int(r["technology_year"])) for r in rows} == set(INPUT_SERIES)
    data, summary = {}, []
    for key in SERIES:
        group = [r for r in rows if (r["fuel"], int(r["technology_year"])) == key]
        x = np.array([float(r[X_FIELD]) for r in group])
        y = np.array([float(r[Y_FIELD]) if r[Y_FIELD] else np.nan for r in group])
        denominator = np.array([float(r["annual_average_qualified_potential_Mt_per_year"]) for r in group])
        np.testing.assert_array_equal(x, np.arange(0, 201, 5))
        np.testing.assert_array_equal(np.isnan(y), denominator == 0)
        defined = np.isfinite(y)
        assert np.all((y[defined] >= -1e-10) & (y[defined] <= 100 + 1e-10))
        data[key] = (x, y)
        baseline = float(y[x == 100][0])
        summary.append({"fuel": key[0], "technology_year": key[1],
                        "rows": len(group), "defined_points": int(defined.sum()),
                        "undefined_points": int(np.isnan(y).sum()),
                        "first_defined_carbon_price": float(x[defined][0]),
                        "baseline_share": baseline,
                        "baseline_display": f"{baseline:.1f}%"})
    return source, data, summary


def main():
    source, data, summary = load_data()
    qa = HERE / "qa"
    qa.mkdir(exist_ok=True)
    fig = plt.figure(figsize=(WIDTH_PT / 72, HEIGHT_PT / 72), facecolor="white")
    axes, headings, panel_labels = [], [], []
    lefts = (59, 217, 375)
    panel_width, panel_bottom, panel_height = 136, 45, 150
    titles = ("Green ammonia, 2030", "e-Methanol, 2035", "e-SAF, 2050")

    for index, left in enumerate(lefts):
        letter = "ABC"[index]
        ax = fig.add_axes([left / WIDTH_PT, panel_bottom / HEIGHT_PT,
                           panel_width / WIDTH_PT, panel_height / HEIGHT_PT], label=letter)
        axes.append(ax)
        panel_labels.append(fig.text(left / WIDTH_PT, 217 / HEIGHT_PT, letter,
                                     fontsize=9.2, fontweight="bold", va="center"))
        headings.append(fig.text((left + 14) / WIDTH_PT, 217 / HEIGHT_PT,
                                  titles[index], fontsize=8, fontweight="bold", va="center"))
        ax.set_xlim(0, 200)
        ax.set_ylim(-3, 106)
        ax.set_xticks([0, 50, 100, 150, 200])
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.spines["left"].set_bounds(-3, 100)
        ax.spines["bottom"].set_position(("data", -3))
        ax.tick_params(axis="both", pad=3)
        ax.grid(False)
        # This line marks the common carbon-price reference, not a threshold fit.
        ax.axvline(100, color=GRAY, linewidth=0.75, linestyle=(0, (3, 3)), zorder=1)
        for tick in ax.get_xticklabels():
            if tick.get_text() == "100":
                tick.set_fontweight("bold")
        if index:
            ax.set_yticklabels([])
        else:
            ax.set_ylabel("Hourly-uncompetitive share of\nannual-average competitive potential (%)",
                          labelpad=9, fontsize=7.6, linespacing=1.25)

        keys = [SERIES[index]]
        for key in keys:
            x, y = data[key]
            color = ORANGE
            linestyle = "-"
            # Mark every actual defined sample; NaNs remain in the arrays.
            ax.plot(x, y, color=color, linewidth=1.3, linestyle=linestyle,
                    marker="o", markersize=1.9, markeredgewidth=0,
                    solid_capstyle="round", dash_capstyle="round", zorder=3,
                    clip_on=False)
            baseline = float(y[x == 100][0])
            ax.plot(100, baseline, marker="o", markersize=4.6,
                    markerfacecolor=color, markeredgecolor="white",
                    markeredgewidth=0.6, linestyle="none", zorder=5)
            offset = (7, -13) if key == ("saf", 2035) else (7, 4)
            ax.annotate(f"{baseline:.1f}%", xy=(100, baseline), xytext=offset,
                        textcoords="offset points", ha="left", va="bottom",
                        fontsize=8, fontweight="bold", color=INK, zorder=6)

    # Editable Arial text runs keep the chemical subscript and reciprocal unit
    # above the 5 pt floor after insertion, without font fallback or math shrinkage.
    label_parts = [("Carbon price (USD tCO", 8, 0), ("2", 6.2, -2.0),
                   ("-1", 6.2, 3.1), (")", 8, 0)]
    parts = [fig.text(0, (11 + dy) / HEIGHT_PT, text,
                      fontsize=size, ha="left", va="baseline")
             for text, size, dy in label_parts]
    fig.canvas.draw()
    text_renderer = fig.canvas.get_renderer()
    widths = [part.get_window_extent(text_renderer).width * 72 / fig.dpi for part in parts]
    cursor = 285 - sum(widths) / 2
    for part, width in zip(parts, widths):
        part.set_x(cursor / WIDTH_PT)
        cursor += width

    # Final rendered plot areas, before writing any submission assets.
    fig.canvas.draw()
    alignment = require_matplotlib_panel_alignment(
        fig, axes=axes, panel_ids=list("ABC"), row_groups=[list("ABC")],
        json_out=qa / "panel_alignment.json", overlay_svg=qa / "panel_alignment.svg",
        tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True)
    renderer = fig.canvas.get_renderer()
    rendered_headings = []
    for artist in panel_labels + headings:
        bbox = artist.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted())
        anchor = artist.get_transform().transform(artist.get_position())
        anchor_pt = fig.dpi_scale_trans.inverted().transform(anchor) * 72
        rendered_headings.append({"text": artist.get_text(), "anchor_pt": anchor_pt.tolist(),
                                  "bbox_pt": [float(v * 72) for v in bbox.extents]})
    assert np.ptp([entry["anchor_pt"][1] for entry in rendered_headings]) <= 1.5
    (qa / "heading_alignment.json").write_text(json.dumps({
        "verdict": "PASS", "tolerance_pt": 1.5,
        "note": "Uppercase panel letters follow the manuscript convention.",
        "rendered_headings": rendered_headings,
    }, indent=2), encoding="utf-8")

    filename = HERE / "Figure_S12_Carbon_Price_Sensitivity"
    fig.savefig(filename.with_suffix(".png"), dpi=300)
    fig.savefig(filename.with_suffix(".pdf"))
    fig.savefig(filename.with_suffix(".svg"))
    # RGB TIFF, produced from the same Matplotlib render without geometry edits.
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
        "rows_supplied": 164, "rows_retained": sum(item["rows"] for item in summary),
        "exclusions": 41,
        "exclusion_rule": "e-SAF 2035 omitted from the figure at the user's request; original CSV unchanged",
        "undefined_values": int(sum(item["undefined_points"] for item in summary)),
        "undefined_handling": "NaN in plotted arrays; no connecting line across NaN",
        "smoothing": False, "resampling": False, "model_solves": 0,
        "source_dimensions_pt": [WIDTH_PT, HEIGHT_PT],
        "intended_insert_width_pt": FINAL_WIDTH_PT,
        "series": summary,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
