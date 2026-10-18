"""Signed absolute and relative hydrogen cost gaps on unchanged global maps.

Figure contract: annual-average cost underestimation varies spatially and its
absolute and relative magnitudes evolve differently across technology years.
A--C show paired hourly-minus-annual-average costs; D--F show the same gaps
divided by hourly costs. All grid-cell observations and the original basemap,
Plate Carree projection are retained, without aggregation. The display starts
at 60 degrees south to omit Antarctica while retaining every paired grid cell.
"""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import sys

import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Patch
import cartopy
import cartopy.crs as ccrs
import cartopy.feature as cf
from PIL import Image

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[2]
sys.path.insert(0, str(HERE))
from audit_panel_alignment import require_matplotlib_panel_alignment

SOURCE = PACKAGE / "02_main_figures/Fig2_Original_Maps_Revised_GHI_20260914/source_data/H2_paired_costs_all_locations.csv.gz"
WIDTH_PT, HEIGHT_PT = 528, 286
FINAL_WIDTH_PT = 456.9
MAP_EXTENT = (-180, 180, -60, 90)
YEARS = (2030, 2035, 2050)
INK, AXIS, LAND = "#263238", "#89969B", "#E6EAED"
DENOMINATORS = (228090, 228093, 228046)
SPECS = (
    {"field": "absolute", "title": "Absolute cost underestimation",
     "label": "Hourly − annual-average cost (USD/kg)",
     "bounds": (-0.2, 1.5), "ticks": (-0.2, 0, 0.5, 1.0, 1.5),
     "map_bottom": 189, "median_y": 181, "bar_bottom": 166},
    {"field": "relative", "title": "Relative cost underestimation",
     "label": "Cost underestimation (%)",
     "bounds": (-20, 45), "ticks": (-20, -10, 0, 10, 20, 30, 40, 45),
     "map_bottom": 60, "median_y": 52, "bar_bottom": 37},
)

mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial"],
    "font.size": 7.6, "axes.labelsize": 7.6,
    "xtick.labelsize": 7.2, "ytick.labelsize": 7.2,
    "legend.fontsize": 7.2, "legend.frameon": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "axes.linewidth": 0.55, "axes.edgecolor": AXIS,
    "xtick.major.size": 2.6, "xtick.major.width": 0.55,
    "ytick.major.size": 2.6, "ytick.major.width": 0.55,
    "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK,
    "savefig.facecolor": "white",
})


def signed_cmap(name, lower, upper):
    # The scalar domain remains linear; the pale zero is placed at its true
    # position in the asymmetric range. Warm shades retain negative values.
    zero = -lower / (upper - lower)
    anchors = [(0, "#C7A078"), (zero / 2, "#E9D7C5"), (zero, "#F7FAFC")]
    anchors.extend((zero + fraction * (1 - zero), color) for fraction, color in
                   ((0.2, "#D1E4ED"), (0.4, "#9BC1D1"), (0.6, "#5E929F"),
                    (0.8, "#277A89"), (1.0, "#174C63")))
    assert np.all(np.diff([position for position, _ in anchors]) > 0)
    return LinearSegmentedColormap.from_list(name, anchors, N=256)


def load_data():
    d = pd.read_csv(SOURCE, usecols=["year", "latitude", "longitude",
                                   "static_cost_per_kg", "hourly8760_cost_per_kg"])
    assert len(d) == 684229 and not d.duplicated(["year", "latitude", "longitude"]).any()
    assert set(d.year.unique()) == set(YEARS)
    assert np.isfinite(d.to_numpy()).all() and (d.hourly8760_cost_per_kg > 0).all()
    assert d.longitude.between(-180, 180).all() and d.latitude.between(-90, 90).all()
    assert d.latitude.between(MAP_EXTENT[2], MAP_EXTENT[3]).all()
    d["absolute"] = d.hourly8760_cost_per_kg - d.static_cost_per_kg
    d["relative"] = 100 * d.absolute / d.hourly8760_cost_per_kg
    reference = pd.read_csv(HERE / "source_data/global_hydrogen_statistics.csv").set_index("year")
    summary = []
    for year, n in zip(YEARS, DENOMINATORS):
        group = d[d.year == year]
        assert len(group) == n
        absolute = float(group.absolute.median())
        relative = float(group.relative.median())
        np.testing.assert_allclose(absolute, reference.loc[year, "absolute_median_usd_kg"], rtol=0, atol=1e-12)
        np.testing.assert_allclose(relative, reference.loc[year, "relative_median_percent"], rtol=0, atol=1e-12)
        assert int((group.absolute < 0).sum()) == int(reference.loc[year, "negative_gap_locations"])
        summary.append({"year": year, "paired_grid_cells": n,
                        "absolute_median_USD_per_kg": absolute,
                        "relative_median_percent": relative,
                        "negative_gap_grid_cells": int((group.absolute < 0).sum())})
    for spec in SPECS:
        lower, upper = spec["bounds"]
        assert d[spec["field"]].between(lower, upper).all()
    return d, summary


def main():
    d, summary = load_data()
    qa = HERE / "qa"
    basemap = []
    geo_root = Path(cartopy.config["data_dir"]) / "shapefiles/natural_earth/physical"
    for feature in ("land", "coastline"):
        path = geo_root / f"ne_110m_{feature}.shp"
        assert path.exists()
        basemap.append({"feature": feature, "resolution": "110m", "path": str(path),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    fig = plt.figure(figsize=(WIDTH_PT / 72, HEIGHT_PT / 72), facecolor="white")
    lefts, map_width, map_height = (12, 186, 360), 156, 65
    axes, bar_axes, letters, panels = [], [], [], []
    for left, year in zip(lefts, YEARS):
        fig.text((left + map_width / 2) / WIDTH_PT, 277 / HEIGHT_PT, str(year),
                 fontsize=8.4, fontweight="bold", ha="center", va="center")

    for row, spec in enumerate(SPECS):
        lower, upper = spec["bounds"]
        cmap = signed_cmap("cost_gap_" + spec["field"], lower, upper)
        norm = Normalize(vmin=lower, vmax=upper, clip=False)
        bottom = spec["map_bottom"]
        label_y = bottom + map_height + 8
        fig.text(26 / WIDTH_PT, label_y / HEIGHT_PT, spec["title"],
                 fontsize=8, fontweight="bold", va="center")

        for column, (left, year) in enumerate(zip(lefts, YEARS)):
            letter = "ABCDEF"[row * 3 + column]
            ax = fig.add_axes([left / WIDTH_PT, bottom / HEIGHT_PT,
                               map_width / WIDTH_PT, map_height / HEIGHT_PT],
                              projection=ccrs.PlateCarree(), label=letter)
            axes.append(ax)
            ax.set_extent(MAP_EXTENT, crs=ccrs.PlateCarree())
            ax.add_feature(cf.LAND.with_scale("110m"), facecolor=LAND,
                           edgecolor="none", zorder=0)
            group = d[d.year == year]
            lon = group.longitude.to_numpy()
            lat = group.latitude.to_numpy()
            values = group[spec["field"]].to_numpy()
            scatter = ax.scatter(lon, lat, c=values, s=0.32, cmap=cmap, norm=norm,
                                 marker="s", edgecolors="none", rasterized=True,
                                 transform=ccrs.PlateCarree(), zorder=1)
            np.testing.assert_array_equal(scatter.get_offsets(), np.column_stack((lon, lat)))
            np.testing.assert_array_equal(scatter.get_array(), values)
            ax.coastlines("110m", linewidth=0.22, color="#A1ADB3", zorder=2)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.spines["geo"].set_visible(False)
            letters.append(fig.text(left / WIDTH_PT, label_y / HEIGHT_PT, letter,
                                    fontsize=9.2, fontweight="bold", va="center"))
            record = summary[column]
            if row == 0:
                label = f"Median: {record['absolute_median_USD_per_kg']:.2f} USD/kg"
            else:
                label = f"Median: {record['relative_median_percent']:.1f}%"
            fig.text((left + map_width / 2) / WIDTH_PT, spec["median_y"] / HEIGHT_PT,
                     label, fontsize=7.6, ha="center", va="center")
            panels.append({"panel": letter, "year": year, "field": spec["field"],
                           "plotted_grid_cells": len(group), "median_label": label})

        cax = fig.add_axes([124 / WIDTH_PT, spec["bar_bottom"] / HEIGHT_PT,
                            280 / WIDTH_PT, 6 / HEIGHT_PT])
        bar_axes.append(cax)
        mappable = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
        colorbar = fig.colorbar(mappable, cax=cax, orientation="horizontal", ticks=spec["ticks"])
        colorbar.set_label(spec["label"], fontsize=7.6, labelpad=3)
        colorbar.ax.tick_params(labelsize=7.2, pad=2, length=2.6, width=0.55)
        colorbar.outline.set_linewidth(0.55)
        colorbar.outline.set_edgecolor(AXIS)

    fig.legend(handles=[Patch(facecolor=LAND, edgecolor="none", label="Land without paired estimates")],
               loc="center", bbox_to_anchor=(0.5, 8 / HEIGHT_PT),
               fontsize=7.2, handlelength=1.1, handletextpad=0.6)
    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig, axes=axes, panel_ids=list("ABCDEF"),
        row_groups=[list("ABC"), list("DEF")],
        column_groups=[list("AD"), list("BE"), list("CF")],
        require_panel_labels=False, tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True,
        json_out=qa / "panel_alignment.json", overlay_svg=qa / "panel_alignment.svg")
    anchors = [[text.get_position()[0] * WIDTH_PT, text.get_position()[1] * HEIGHT_PT] for text in letters]
    for ids in ((0, 1, 2), (3, 4, 5)):
        assert np.ptp([anchors[i][1] for i in ids]) <= 1.5
    for ids in ((0, 3), (1, 4), (2, 5)):
        assert np.ptp([anchors[i][0] for i in ids]) <= 1.5

    filename = HERE / "Figure_S16_Hydrogen_Cost_Underestimation"
    fig.savefig(filename.with_suffix(".pdf"), dpi=600)
    fig.savefig(filename.with_suffix(".svg"), dpi=600)
    fig.savefig(filename.with_suffix(".png"), dpi=300)
    buffer = BytesIO()
    fig.savefig(buffer, format="tiff", dpi=600)
    with Image.open(buffer) as image:
        rgb = BytesIO()
        image.convert("RGB").save(rgb, format="TIFF", compression="tiff_lzw", dpi=(600, 600))
        filename.with_suffix(".tiff").write_bytes(rgb.getvalue())
    plt.close(fig)

    report = {"input": str(SOURCE), "input_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              "source_rows": len(d), "rows_displayed_per_metric": len(d), "exclusions": 0,
              "model_solves": 0, "coordinates": "unchanged source longitude and latitude",
              "metrics": {"absolute": "hourly minus annual-average cost",
                          "relative": "100 * (hourly minus annual-average cost) / hourly cost"},
              "weights": "one per paired grid cell", "negative_values": "retained and shown in warm shades",
              "color_scales": [{"field": s["field"], "bounds": s["bounds"],
                                "normalization": "linear", "shared_across_years": True} for s in SPECS],
              "display_clipping": False, "smoothing": False, "aggregation": False,
              "projection": "PlateCarree", "extent": list(MAP_EXTENT),
              "geographic_crop": "Antarctica omitted; all paired grid cells retained",
              "basemap": basemap, "source_dimensions_pt": [WIDTH_PT, HEIGHT_PT],
              "insert_width_pt": FINAL_WIDTH_PT, "global_summaries": summary, "panels": panels}
    (qa / "data_integrity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (HERE / "source_data/provenance.json").write_text(json.dumps({
        "input": report["input"], "input_sha256": report["input_sha256"],
        "basemap": basemap, "source_rows": len(d),
        "display_extent": list(MAP_EXTENT),
        "figure_claim": "Absolute and relative hydrogen cost gaps have different spatial and scenario patterns.",
        "archetype": "quantitative grid; two outcomes by three technology scenarios",
    }, indent=2), encoding="utf-8")
    print("S16 exported: all 684,229 paired grid cells in each metric; signed values retained.")


if __name__ == "__main__":
    main()
