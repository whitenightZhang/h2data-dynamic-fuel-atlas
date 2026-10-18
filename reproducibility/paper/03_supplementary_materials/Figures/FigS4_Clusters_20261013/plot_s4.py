"""S4: original ammonia clusters and representative sites, plus K diagnostic.

Figure contract: locate the three production-system groups and their shared
representative sites, then show the existing evidence for selecting K = 3.
Panel A is a hero map using the approved S2 boundaries and Equal Earth
projection; panel B is the archived silhouette diagnostic in the lower-left
ocean area. Membership, sites
and diagnostic values are reused without recomputing optimization or k-means.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from shapely.ops import transform as transform_geometry
from pyproj import Transformer
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "source_data"
QA = ROOT / "qa"
W, H = 528, 318
INK, MUTED = "#26343B", "#6E7B82"
NAMES = {0: "Wind-cluster", 1: "Wind–solar complementary", 2: "Solar-cluster"}
COLORS = {0: "#0072B2", 1: "#009E73", 2: "#E69F00"}
LETTERS = {0: "W", 1: "C", 2: "S"}
mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 7.8, "pdf.fonttype": 42, "ps.fonttype": 42,
    "svg.fonttype": "none", "axes.spines.top": False,
    "axes.spines.right": False, "axes.linewidth": 0.55,
    "savefig.facecolor": "white",
})

nodes = pd.read_csv(DATA / "ammonia_2035_cluster_assignments.csv")
sites = pd.read_csv(DATA / "representative_sites.csv")
diagnostic = pd.read_csv(DATA / "silhouette_scores.csv")
assert len(nodes) == 18016 and set(nodes.cluster_label) == {0, 1, 2}
assert not nodes.duplicated(["latitude", "longitude"]).any()
assert nodes.latitude.between(-59, 85).all()
assert nodes.longitude.between(-180, 180).all()
assert len(sites) == 3 and set(sites.cluster_label) == {0, 1, 2}
site_check = sites.merge(nodes, on=["latitude", "longitude"], suffixes=("_site", "_grid"),
                         how="left", validate="one_to_one")
assert site_check.cluster_label_site.eq(site_check.cluster_label_grid).all()
assert diagnostic.K.tolist() == list(range(2, 13))
assert np.isfinite(diagnostic["Silhouette score"]).all()
best = diagnostic.loc[diagnostic["Silhouette score"].idxmax()]
assert int(best.K) == 3

boundary = gpd.read_file(DATA / "basemap/word-map-with-correct-china-serbia.shp")
assert str(boundary.crs) == "EPSG:4326"
valid = boundary.loc[boundary.geometry.notna() & ~boundary.geometry.is_empty].geometry.tolist()

fig = plt.figure(figsize=(W / 72, H / 72))
pc = ccrs.PlateCarree()
projection = ccrs.EqualEarth(central_longitude=0)
xlim = (-17250000, 17250000)
ylim = (projection.transform_point(0, -59, pc)[1],
        projection.transform_point(0, 85, pc)[1])
left, width, map_bottom = 42, 478, 67
map_height = width * (ylim[1] - ylim[0]) / (xlim[1] - xlim[0])
world = fig.add_axes([left / W, map_bottom / H, width / W, map_height / H],
                     projection=projection, label="A")
world.set_xlim(*xlim)
world.set_ylim(*ylim)
world.spines["geo"].set_visible(False)
world.set_facecolor("white")

geographic_window = box(-180, -59, 180, 85)
viewport = box(xlim[0], ylim[0], xlim[1], ylim[1])
project = Transformer.from_crs("EPSG:4326", projection.proj4_init, always_xy=True).transform


def visible_geometry(g):
    clipped = g.intersection(geographic_window)
    if clipped.is_empty:
        return None
    projected = transform_geometry(project, clipped).intersection(viewport)
    return None if projected.is_empty else projected


land = [p for g in valid if (p := visible_geometry(g)) is not None]
borders = [p for g in valid if (p := visible_geometry(g.boundary)) is not None]
world.add_geometries(land, projection, facecolor="#EFF1F2", edgecolor="none", zorder=0)
world.add_geometries(borders, projection, facecolor="none", edgecolor="#9AA7AD",
                     linewidth=0.23, zorder=1)
for c in NAMES:
    group = nodes.loc[nodes.cluster_label.eq(c)]
    world.scatter(group.longitude, group.latitude, transform=pc, s=0.30,
                  marker="s", color=COLORS[c], edgecolors="none", linewidths=0,
                  rasterized=True, zorder=2)

offsets = {0: (-9, -8), 1: (-11, -2), 2: (-5, -18)}
for row in sites.to_dict("records"):
    c = int(row["cluster_label"])
    world.scatter([row["longitude"]], [row["latitude"]], transform=pc,
                  marker="*", s=92, facecolor="white", edgecolor=INK,
                  linewidth=0.85, zorder=5)
    world.annotate(LETTERS[c], xy=(row["longitude"], row["latitude"]),
                   xycoords=pc._as_mpl_transform(world), xytext=offsets[c],
                   textcoords="offset points", ha="center", va="center",
                   fontsize=8.8, weight="bold", color=INK, zorder=6,
                   arrowprops=({"arrowstyle": "-", "color": MUTED, "linewidth": 0.55,
                                "shrinkA": 3, "shrinkB": 5} if c == 2 else None))

map_title_y = map_bottom + map_height + 15
fig.text(8 / W, map_title_y / H, "A", fontsize=10.2, weight="bold", color=INK, va="center")
fig.text(23 / W, map_title_y / H, "Green-ammonia production systems, 2035",
         fontsize=9, weight="bold", color=INK, va="center")

# Comparable legend columns stay below the map. The map and its inset have
# intentionally different dimensions and are not comparable plot-area grids.
legend_axes = []
for j in range(4):
    ax = fig.add_axes([(11 + 126 * j) / W, 36 / H, 121 / W, 12 / H], label=f"L{j+1}")
    ax.set_xlim(0, 121)
    ax.set_ylim(0, 12)
    ax.axis("off")
    if j < 3:
        ax.plot(4, 6, marker="s", markersize=4.1, linestyle="none",
                 color=COLORS[j], markeredgewidth=0)
        ax.text(12, 6, NAMES[j], fontsize=7.4, va="center", color=INK)
    else:
        ax.plot(4, 6, marker="*", markersize=8.0, linestyle="none",
                 markerfacecolor="white", markeredgecolor=INK, markeredgewidth=0.65)
        ax.text(17, 6, "Representative site", fontsize=7.4, va="center", color=INK)
    legend_axes.append(ax)

diag = fig.add_axes([52 / W, 89 / H, 111 / W, 73 / H], label="B", zorder=10)
diag.plot(diagnostic.K, diagnostic["Silhouette score"], color="#70868E", linewidth=1.15,
           marker="o", markersize=3.3, markeredgewidth=0, zorder=2)
diag.scatter([best.K], [best["Silhouette score"]], s=32, color="#315F70",
             edgecolor="white", linewidth=0.5, zorder=3)
diag.text(4.2, 0.637, f"K = 3 ({best['Silhouette score']:.3f})",
          fontsize=7.2, weight="bold", color="#315F70", va="center")
diag.set_xlim(1.75, 12.25)
diag.set_ylim(0.30, 0.66)
diag.set_xticks([2, 3, 6, 9, 12])
diag.set_yticks([0.3, 0.4, 0.5, 0.6])
diag.set_xlabel("Clusters, K", fontsize=7.4, color=INK, labelpad=4)
diag.set_ylabel("Silhouette score", fontsize=7.4, color=INK, labelpad=4)
diag.tick_params(labelsize=7.2, width=0.5, length=2.3, pad=2.5, colors=INK)
diag.grid(False)
diag.spines["left"].set_color("#7B878D")
diag.spines["bottom"].set_color("#7B878D")
inset_label = fig.text(52 / W, 173 / H, "B", fontsize=9.2, weight="bold", color=INK, va="center")

fig.canvas.draw()
projected_nodes = projection.transform_points(pc, nodes.longitude.to_numpy(), nodes.latitude.to_numpy())
screen_nodes = world.transData.transform(projected_nodes[:, :2])
inset_bounds = [diag.get_tightbbox(fig.canvas.get_renderer()).padded(2),
                inset_label.get_window_extent(fig.canvas.get_renderer()).padded(2)]
hidden = np.zeros(len(nodes), dtype=bool)
for bounds in inset_bounds:
    hidden |= ((screen_nodes[:, 0] >= bounds.x0) & (screen_nodes[:, 0] <= bounds.x1) &
               (screen_nodes[:, 1] >= bounds.y0) & (screen_nodes[:, 1] <= bounds.y1))
assert not hidden.any(), ("Diagnostic inset obscures classified grid cells", int(hidden.sum()))

require_matplotlib_panel_alignment(fig, axes=legend_axes, panel_ids=["L1", "L2", "L3", "L4"],
                                   row_groups=[["L1", "L2", "L3", "L4"]],
                                   column_groups=[],
                                   json_out=QA / "panel_alignment.json",
                                   overlay_svg=QA / "panel_alignment.svg",
                                   tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True)
prefix = ROOT / "Figure_S4_Clusters_and_Representative_Sites"
fig.savefig(str(prefix) + ".pdf", dpi=600)
fig.savefig(str(prefix) + ".svg", dpi=600)
fig.savefig(str(prefix) + ".png", dpi=600)
plt.close(fig)
(QA / "data_and_display_checks.json").write_text(json.dumps({
    "figure": "S4", "scenario": "green ammonia, 2035",
    "map_grid_cells": len(nodes),
    "cluster_counts": {str(c): int(nodes.cluster_label.eq(c).sum()) for c in NAMES},
    "all_cluster_members_displayed": True,
    "map_projection": "Equal Earth; same viewport and source boundaries as S2",
    "latitude_range": [-59, 85], "null_source_boundary_rows": int(boundary.geometry.isna().sum()),
    "representative_sites": sites.to_dict("records"),
    "diagnostic_points": len(diagnostic), "selected_K": int(best.K),
    "diagnostic_layout": "Inset in the lower-left ocean area",
    "classified_grid_cells_obscured_by_inset": int(hidden.sum()),
    "alignment_scope": "Four equal legend columns; main map and inset intentionally differ in dimensions",
    "maximum_silhouette": float(best["Silhouette score"]),
    "classification_or_model_results_changed": False,
    "country_geometry_changes": False, "map_point_layer_rasterized": True,
    "source_size_pt": [W, H], "SI_include_width": "0.95 textwidth",
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"pdf": str(prefix) + ".pdf", "map_grid_cells": len(nodes),
                  "maximum_silhouette": float(best["Silhouette score"])}))
