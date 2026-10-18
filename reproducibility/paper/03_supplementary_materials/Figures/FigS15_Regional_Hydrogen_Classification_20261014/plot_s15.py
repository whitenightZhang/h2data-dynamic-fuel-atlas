"""Regional low-cost hydrogen classifications at the fixed 2 USD/kg benchmark.

Three aligned panels compare the 2030, 2035 and 2050 technology scenarios.
All 29 named regions and all four classifications retain their source shares;
the common ordering is the original 2035 hourly median-cost ordering.
Orange segments start at zero to support comparison across regions and years.
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
from matplotlib.patches import Patch
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_panel_alignment import require_matplotlib_panel_alignment

WIDTH_PT, HEIGHT_PT = 540, 424
FINAL_WIDTH_PT = 456.9
YEARS = (2030, 2035, 2050)
BENCHMARK = 2.0
INK, AXIS = "#263238", "#89969B"
# Category colors are identical to the main-text hydrogen classification maps.
COLORS = {2: "#DEAB67", 1: "#5E929F", 3: "#987BA8", 0: "#E5E8EA"}
STACK_ORDER = (2, 1, 3, 0)
CLASS_LABELS = {2: "Annual-average only", 1: "Both assessments",
                3: "Hourly only", 0: "Neither assessment"}
DISPLAY_NAMES = {
    "Africa_N": "North Africa", "Africa_S": "Southern Africa",
    "Africa_E": "East Africa", "Africa_W": "West Africa",
    "Europe_Eastern": "Eastern Europe", "Europe_Non_EU": "Other Europe",
    "South America_N": "N. South America",
    "South America_S": "S. South America",
    "Australia_NZ": "Australia / NZ", "Southeast Asia": "Southeast Asia",
}
SELECTED = {
    2030: {"South Asia", "India", "Central Asia", "Middle East", "China"},
    2035: {"China", "Africa_N", "EU-15", "Europe_Eastern", "EU-12", "South Korea"},
    2050: {"Canada", "Russia", "European FTA", "EU-15", "EU-12"},
}

mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial"],
    "font.size": 7.6, "axes.labelsize": 8,
    "xtick.labelsize": 7.2, "ytick.labelsize": 7.2,
    "legend.fontsize": 7.2, "legend.frameon": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "axes.linewidth": 0.55, "axes.edgecolor": AXIS,
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.major.size": 2.6, "xtick.major.width": 0.55,
    "ytick.major.size": 0, "ytick.major.width": 0.55,
    "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK,
    "savefig.facecolor": "white",
})


def load_data():
    source = HERE / "source_data/regional_classifications.csv"
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 270
    order = json.loads((HERE / "source_data/region_order.json").read_text(encoding="utf-8"))
    assert len(order) == 29 and len(set(order)) == 29
    candidates = [r for r in rows if float(r["benchmark_usd_kg"]) == BENCHMARK]
    assert len(candidates) == 90
    chosen = [r for r in candidates if r["region_name"] in order]
    assert len(chosen) == 87
    lookup = {(int(r["year"]), r["region_name"]): r for r in chosen}
    assert len(lookup) == 87
    data, summaries = {}, []
    for year in YEARS:
        group = [lookup[(year, region)] for region in order]
        shares = np.array([[float(row[f"cat{k}_pct"]) for k in STACK_ORDER] for row in group])
        counts = np.array([[int(row[f"cat{k}_n"]) for k in STACK_ORDER] for row in group])
        denominator = np.array([int(row["n"]) for row in group])
        assert np.all(np.isfinite(shares)) and np.all((shares >= 0) & (shares <= 100))
        assert np.all(denominator > 0)
        np.testing.assert_array_equal(counts.sum(axis=1), denominator)
        np.testing.assert_allclose(shares, 100 * counts / denominator[:, None], rtol=0, atol=1e-12)
        np.testing.assert_allclose(shares.sum(axis=1), 100, rtol=0, atol=1e-12)
        data[year] = shares
        summaries.append({"year": year, "named_regions": len(group),
                          "paired_grid_cells_in_named_regions": int(denominator.sum())})
    return source, rows, order, data, summaries


def main():
    source, rows, order, data, summaries = load_data()
    qa = HERE / "qa"
    fig = plt.figure(figsize=(WIDTH_PT / 72, HEIGHT_PT / 72), facecolor="white")
    fig.text(10 / WIDTH_PT, 411 / HEIGHT_PT, "Hydrogen cost benchmark: 2 USD/kg",
             fontsize=8, ha="left", va="center")
    axes, letters, annotations, annotation_records = [], [], [], []
    lefts, bottom, width, height = (62, 242, 422), 64, 110, 302

    for index, (year, left) in enumerate(zip(YEARS, lefts)):
        letter = "ABC"[index]
        ax = fig.add_axes([left / WIDTH_PT, bottom / HEIGHT_PT,
                           width / WIDTH_PT, height / HEIGHT_PT], label=letter)
        axes.append(ax)
        letters.append(fig.text((left - 52) / WIDTH_PT, 389 / HEIGHT_PT, letter,
                                fontsize=9.2, fontweight="bold", va="center"))
        fig.text((left - 38) / WIDTH_PT, 389 / HEIGHT_PT, str(year),
                 fontsize=8.4, fontweight="bold", va="center")
        ax.set_xlim(0, 100)
        ax.set_ylim(28.6, -0.6)
        ax.set_xticks([0, 50, 100])
        ax.set_yticks(np.arange(29))
        ax.set_yticklabels([DISPLAY_NAMES.get(name, name) for name in order])
        ax.tick_params(axis="x", pad=3.2)
        ax.tick_params(axis="y", length=0, pad=4)
        ax.spines["left"].set_visible(False)
        ax.grid(False)

        left_edge = np.zeros(29)
        for column, category in enumerate(STACK_ORDER):
            values = data[year][:, column]
            bars = ax.barh(np.arange(29), values, left=left_edge, height=0.80,
                           color=COLORS[category], edgecolor="none", linewidth=0, zorder=2)
            # Matplotlib derives widths by subtracting translated endpoints.
            np.testing.assert_allclose([bar.get_width() for bar in bars], values, rtol=0, atol=1e-12)
            np.testing.assert_array_equal([bar.get_x() for bar in bars], left_edge)
            left_edge = left_edge + values
        np.testing.assert_allclose(left_edge, 100, rtol=0, atol=1e-12)

        for row, region in enumerate(order):
            if region in SELECTED[year]:
                share = float(data[year][row, 0])
                label_font = 6.4 if year == 2050 and region == "Russia" else 7.2
                artist = ax.text(share / 2, row, f"{share:.1f}", fontsize=label_font,
                                 ha="center", va="center", color=INK, zorder=3)
                annotations.append((artist, width * share / 100))
                annotation_records.append({"panel": letter, "year": year, "region": region,
                                           "annual_average_only_share_percent": share,
                                           "display_value": f"{share:.1f}",
                                           "source_font_pt": label_font})

    fig.text(297 / WIDTH_PT, 37 / HEIGHT_PT, "Grid cells in region (%)",
             fontsize=8, ha="center", va="center")
    fig.legend(handles=[Patch(facecolor=COLORS[k], edgecolor="none", label=CLASS_LABELS[k])
                        for k in STACK_ORDER],
               loc="lower center", bbox_to_anchor=(0.5, 5 / HEIGHT_PT), ncol=4,
               handlelength=1.1, handletextpad=0.55, columnspacing=1.7,
               borderaxespad=0, fontsize=7.2)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for artist, available_width_pt in annotations:
        text_width_pt = artist.get_window_extent(renderer).width * 72 / fig.dpi
        assert text_width_pt <= available_width_pt - 0.8, (artist.get_text(), text_width_pt, available_width_pt)
    require_matplotlib_panel_alignment(
        fig, axes=axes, panel_ids=list("ABC"), row_groups=[list("ABC")], column_groups=[],
        require_panel_labels=False, tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True,
        json_out=qa / "panel_alignment.json", overlay_svg=qa / "panel_alignment.svg")
    anchors = [[text.get_position()[0] * WIDTH_PT, text.get_position()[1] * HEIGHT_PT] for text in letters]
    assert np.ptp([a[1] for a in anchors]) <= 1.5

    filename = HERE / "Figure_S15_Regional_Hydrogen_Classification"
    fig.savefig(filename.with_suffix(".pdf"))
    fig.savefig(filename.with_suffix(".svg"))
    fig.savefig(filename.with_suffix(".png"), dpi=300)
    buffer = BytesIO()
    fig.savefig(buffer, format="tiff", dpi=600)
    with Image.open(buffer) as image:
        rgb = BytesIO()
        image.convert("RGB").save(rgb, format="TIFF", compression="tiff_lzw", dpi=(600, 600))
        filename.with_suffix(".tiff").write_bytes(rgb.getvalue())
    plt.close(fig)
    (qa / "selected_annotations.json").write_text(json.dumps(annotation_records, indent=2), encoding="utf-8")
    (qa / "data_integrity.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_rows": len(rows), "rows_at_selected_benchmark": 90,
        "regional_rows_displayed": 87, "classified_segments_displayed": 348,
        "selection_rule": "benchmark 2 USD/kg; all 29 originally named regions; three technology scenarios",
        "other_benchmark_rows_not_displayed": 180,
        "unnamed_region_rows_not_displayed": 3,
        "unknown_region_handling": "excluded from regional panels as in original; retained in global analysis",
        "percentages": "exact original CSV shares; no recalculation or normalization",
        "region_order": order, "stack_order": [CLASS_LABELS[k] for k in STACK_ORDER],
        "colors": COLORS, "model_solves": 0,
        "source_dimensions_pt": [WIDTH_PT, HEIGHT_PT], "insert_width_pt": FINAL_WIDTH_PT,
        "panels": summaries, "annotation_count": len(annotation_records),
        "regional_label_layout": "All 29 region names repeated in every year panel",
    }, indent=2), encoding="utf-8")
    print("S15 exported: 29 regions x 3 scenarios; all four source classifications retained.")


if __name__ == "__main__":
    main()
