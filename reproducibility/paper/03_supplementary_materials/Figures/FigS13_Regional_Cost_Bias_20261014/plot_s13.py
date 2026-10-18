"""Regional production costs and assessment biases across fuels and years.

Quantitative grid: all 29 regional medians in each of nine fuel-year panels.
Numerical inputs and potential classes are retained; only display geometry,
typography, marker sizes and selected region annotations are revised.
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
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit_panel_alignment import require_matplotlib_panel_alignment

WIDTH_PT, HEIGHT_PT = 528, 486
FINAL_WIDTH_PT = 456.9
INK, GRAY = "#263238", "#89969B"
YEARS = (2030, 2035, 2050)
PRODUCTS = ("Ammonia", "Methanol", "FTL")
TITLES = ("Green ammonia", "e-Methanol", "e-SAF")
POINT_DIAMETERS = np.array([3.4, 4.4, 5.6, 7.0])
POTENTIAL_LABELS = ("<10", "10–<100", "100–<500", "≥500")
XLIMS = {
    2030: ((450, 1250), (700, 1750), (2000, 4700)),
    2035: ((350, 875), (500, 1150), (1300, 2900)),
    2050: ((250, 650), (400, 900), (900, 2100)),
}
XTICKS = {
    2030: ([500, 750, 1000], [800, 1200, 1600], [2500, 3500, 4500]),
    2035: ([400, 600, 800], [600, 800, 1000], [1500, 2000, 2500]),
    2050: ([300, 450, 600], [400, 600, 800], [1000, 1500, 2000]),
}

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size": 7.6,
    "axes.labelsize": 7.6,
    "xtick.labelsize": 7.2,
    "ytick.labelsize": 7.2,
    "legend.fontsize": 7.2,
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


def load_rows():
    source = HERE / "source_data/regional_values.csv"
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 261
    keys = {(r["year"], r["product"], r["region_name"]) for r in rows}
    assert len(keys) == len(rows)
    for row in rows:
        row["year"] = int(row["year"])
        for field in ("hourly_median", "static_median", "underestimation_pct", "potential_Mt_yr"):
            row[field] = float(row[field])
            assert np.isfinite(row[field])
        assert row["hourly_median"] > 0 and row["potential_Mt_yr"] >= 0
        row["display_size_class"] = int(np.digitize(row["potential_Mt_yr"], [10, 100, 500]))
        row["display_area_pt2"] = float(POINT_DIAMETERS[row["display_size_class"]] ** 2)
    return source, rows


def selected_labels(year, product):
    if year == 2030:
        return {"India": (0.44, 0.80), "China": (0.025, 0.16)}
    if year == 2035:
        return {"India": (0.58, 0.88), "Brazil": (0.49, 0.55), "China": (0.025, 0.16)}
    labels = {"China": (0.52, 0.38), "Central Asia": (0.60, 0.12)}
    if product == "Methanol":
        labels["South Asia"] = (0.32, 0.80)
    return labels


def main():
    source, rows = load_rows()
    qa = HERE / "qa"
    geo = json.loads((HERE / "source_data/geographic_groups.json").read_text(encoding="utf-8"))
    colors = geo["colors"]
    fig = plt.figure(figsize=(WIDTH_PT / 72, HEIGHT_PT / 72), facecolor="white")
    lefts, bottoms = (59, 217, 375), (323, 185, 47)
    panel_width, panel_height = 136, 98
    axes, letters, selected, panel_records = [], [], [], []

    for left, title in zip(lefts, TITLES):
        fig.text((left + panel_width / 2) / WIDTH_PT, 470 / HEIGHT_PT, title,
                 fontsize=8, fontweight="bold", ha="center", va="center")
    geo_handles = [Line2D([], [], marker="o", markersize=3.6, linestyle="none",
                         markerfacecolor=color, markeredgecolor="white", markeredgewidth=0.3,
                         label=group) for group, color in colors.items()]
    fig.legend(handles=geo_handles, loc="center", bbox_to_anchor=(0.5, 450 / HEIGHT_PT),
               ncol=7, handlelength=0.8, columnspacing=1.05, handletextpad=0.35, fontsize=7.2)

    for iy, (year, bottom) in enumerate(zip(YEARS, bottoms)):
        top = bottom + panel_height
        fig.text(4 / WIDTH_PT, (top + 11) / HEIGHT_PT, str(year),
                 fontsize=8, fontweight="bold", va="center")
        for ip, (product, left) in enumerate(zip(PRODUCTS, lefts)):
            panel = "ABCDEFGHI"[iy * 3 + ip]
            ax = fig.add_axes([left / WIDTH_PT, bottom / HEIGHT_PT,
                               panel_width / WIDTH_PT, panel_height / HEIGHT_PT], label=panel)
            axes.append(ax)
            letters.append(fig.text(left / WIDTH_PT, (top + 11) / HEIGHT_PT, panel,
                                    fontsize=9.2, fontweight="bold", va="center"))
            group = [r for r in rows if r["year"] == year and r["product"] == product]
            assert len(group) == 29 and sum(int(r["nodes"]) for r in group) == 18029
            assert {r["region_name"] for r in group} == {r["region_name"] for r in rows}
            xmin, xmax = XLIMS[year][ip]
            assert all(xmin <= r["hourly_median"] <= xmax and -3 <= r["underestimation_pct"] <= 40 for r in group)
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(-3, 40)
            ax.set_xticks(XTICKS[year][ip])
            ax.set_yticks([0, 10, 20, 30, 40])
            ax.tick_params(axis="both", pad=3)
            ax.grid(False)
            ax.axhline(0, color="#D2D9DC", linewidth=0.4, zorder=1)
            if ip == 0:
                ax.set_ylabel("Annual-average cost\nunderestimation (%)", labelpad=8,
                              fontsize=7.6, linespacing=1.2)
            else:
                ax.set_yticklabels([])
            ordered = sorted(group, key=lambda r: r["potential_Mt_yr"], reverse=True)
            scatter = ax.scatter([r["hourly_median"] for r in ordered],
                                [r["underestimation_pct"] for r in ordered],
                                s=[r["display_area_pt2"] for r in ordered],
                                c=[colors[r["geographic_group"]] for r in ordered],
                                edgecolor="white", linewidth=0.3, alpha=0.90, zorder=3)
            np.testing.assert_array_equal(scatter.get_offsets(),
                                          np.array([[r["hourly_median"], r["underestimation_pct"]] for r in ordered]))
            panel_records.append({"panel": panel, "year": year, "product": product,
                                  "regional_points": len(group), "matched_grid_cells": 18029})

            by_name = {r["region_label"]: r for r in group}
            for name, position in selected_labels(year, product).items():
                row = by_name[name]
                ax.scatter(row["hourly_median"], row["underestimation_pct"],
                           s=row["display_area_pt2"], facecolors="none", edgecolors=INK,
                           linewidths=0.45, zorder=4)
                elbow = name == "China" or year == 2050
                arrow = {"arrowstyle": "-", "color": GRAY, "lw": 0.5,
                         "shrinkA": 2, "shrinkB": np.sqrt(row["display_area_pt2"]) / 2 + 0.8}
                if elbow:
                    arrow["connectionstyle"] = "angle,angleA=0,angleB=90,rad=2"
                ax.annotate(name, xy=(row["hourly_median"], row["underestimation_pct"]),
                            xytext=position, textcoords="axes fraction", ha="left", va="center",
                            fontsize=7.2, color=INK, arrowprops=arrow, zorder=5)
                selected.append({"panel": panel, "region": name,
                                 "hourly_median": row["hourly_median"],
                                 "underestimation_pct": row["underestimation_pct"]})

    fig.text(285 / WIDTH_PT, 25 / HEIGHT_PT, "Hourly production cost (USD/t)",
             fontsize=8, ha="center", va="center")
    fig.text(38 / WIDTH_PT, 8 / HEIGHT_PT, "Production potential (Mt/yr)",
             fontsize=7.2, va="center")
    for left, diameter, label in zip((170, 239, 325, 421), POINT_DIAMETERS, POTENTIAL_LABELS):
        fig.add_artist(Line2D([left / WIDTH_PT], [8 / HEIGHT_PT], transform=fig.transFigure,
                             marker="o", markersize=diameter, markerfacecolor="#93A0A6",
                             markeredgecolor="white", markeredgewidth=0.3, linestyle="none"))
        fig.text((left + diameter / 2 + 4) / WIDTH_PT, 8 / HEIGHT_PT, label,
                 fontsize=7.2, va="center")

    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig, axes=axes, panel_ids=list("ABCDEFGHI"),
        row_groups=[list("ABC"), list("DEF"), list("GHI")],
        column_groups=[list("ADG"), list("BEH"), list("CFI")],
        json_out=qa / "panel_alignment.json", overlay_svg=qa / "panel_alignment.svg",
        tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True)
    anchors = {panel: [letter.get_position()[0] * WIDTH_PT,
                       letter.get_position()[1] * HEIGHT_PT]
               for panel, letter in zip("ABCDEFGHI", letters)}
    for group in ("ABC", "DEF", "GHI"):
        assert np.ptp([anchors[p][1] for p in group]) <= 1.5
    for group in ("ADG", "BEH", "CFI"):
        assert np.ptp([anchors[p][0] for p in group]) <= 1.5
    (qa / "panel_label_alignment.json").write_text(json.dumps(anchors, indent=2), encoding="utf-8")

    filename = HERE / "Figure_S13_Regional_Cost_Bias"
    fig.savefig(filename.with_suffix(".pdf"))
    fig.savefig(filename.with_suffix(".svg"))
    fig.savefig(filename.with_suffix(".png"), dpi=300)
    buffer = BytesIO()
    fig.savefig(buffer, format="tiff", dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    with Image.open(buffer) as image:
        rgb = BytesIO()
        image.convert("RGB").save(rgb, format="TIFF", compression="tiff_lzw", dpi=(600, 600))
        filename.with_suffix(".tiff").write_bytes(rgb.getvalue())
    plt.close(fig)
    (qa / "selected_labels.json").write_text(json.dumps(selected, indent=2), encoding="utf-8")
    (qa / "data_integrity.json").write_text(json.dumps({
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "rows_supplied": len(rows), "rows_displayed": len(rows), "exclusions": 0,
        "coordinates": "exact source regional medians", "potential_values": "unchanged",
        "potential_bins_Mt_per_year": [10, 100, 500],
        "point_diameters_pt": POINT_DIAMETERS.tolist(), "source_dimensions_pt": [WIDTH_PT, HEIGHT_PT],
        "insert_width_pt": FINAL_WIDTH_PT, "panels": panel_records, "model_solves": 0,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
