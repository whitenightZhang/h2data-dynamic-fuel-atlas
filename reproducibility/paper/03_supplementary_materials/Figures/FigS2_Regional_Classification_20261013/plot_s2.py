"""S2 regional classification: source grid retained; display only is redesigned.
Categorical cell polygons remain EPSG:4326 inputs and are projected for display.
The Europe inset magnifies the same source classification. Numbering is a legend
lookup, separate from the original regional raster codes.
"""
from pathlib import Path
import csv,json,hashlib
import numpy as np
import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape,box
from shapely.ops import transform as transform_geometry
from pyproj import Transformer
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import cartopy.crs as ccrs
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"source_data"
W,H=528,430
INK,MUTED,UNCLASSIFIED="#263238","#6C767C","#E6E9EB"
mpl.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial","DejaVu Sans"],
    "font.size":7.4,"pdf.fonttype":42,"ps.fonttype":42,"svg.fonttype":"none",
    "axes.spines.top":False,"axes.spines.right":False,"savefig.facecolor":"white"})
# Display ID, source name, display name, geographic legend group, color.
REGIONS=[
(1,"Canada","Canada","Americas","#B49AC6"),
(2,"USA","USA","Americas","#D5C4E0"),
(3,"Mexico","Mexico","Americas","#987DAD"),
(4,"Central America","Central America","Americas","#4D9E8B"),
(5,"South America_N","Northern South America","Americas","#B8D5BC"),
(6,"South America_S","Southern South America","Americas","#73B5A6"),
(7,"Brazil","Brazil","Americas","#8DBB85"),
(8,"Argentina","Argentina","Americas","#D0DFC0"),
(9,"EU-15","EU-15","Europe","#648CBA"),
(10,"EU-12","EU-12","Europe","#B4C9E3"),
(11,"European FTA","European FTA","Europe","#557C95"),
(12,"Europe_Eastern","Eastern Europe","Europe","#D5E2EC"),
(13,"Europe_Non_EU","Non-EU Europe","Europe","#8296AF"),
(14,"Russia","Russia","Europe","#A5BBD0"),
(15,"Africa_N","North Africa","Africa and Middle East","#E0A44D"),
(16,"Africa_W","West Africa","Africa and Middle East","#F0D17D"),
(17,"Africa_E","East Africa","Africa and Middle East","#DDB581"),
(18,"Africa_S","Southern Africa","Africa and Middle East","#F1DCC0"),
(19,"South Africa","South Africa","Africa and Middle East","#C4A26B"),
(20,"Middle East","Middle East","Africa and Middle East","#F2E6AD"),
(21,"Central Asia","Central Asia","Asia and Oceania","#C87969"),
(22,"South Asia","South Asia","Asia and Oceania","#EBBBA9"),
(23,"Southeast Asia","Southeast Asia","Asia and Oceania","#B96469"),
(24,"China","China","Asia and Oceania","#D99491"),
(25,"India","India","Asia and Oceania","#ECD1C5"),
(26,"Japan","Japan","Asia and Oceania","#B95554"),
(27,"South Korea","South Korea","Asia and Oceania","#EDB6BA"),
(28,"Indonesia","Indonesia","Asia and Oceania","#CB8D75"),
(29,"Australia_NZ","Australia and New Zealand","Asia and Oceania","#65A5A7")]
assert len(REGIONS)==29 and len({r[1] for r in REGIONS})==29
with (DATA/"RegionMapping_filter.csv").open(encoding="utf-8-sig",newline="") as f:
    raw_mapping=list(csv.DictReader(f))
source_codes={r[1]:[int(x["region_code"]) for x in raw_mapping if x["region_name"]==r[1]] for r in REGIONS}
assert source_codes["Central America"]==[4,6] and source_codes["South Asia"]==[26,27]
assert set(source_codes)=={x["region_name"] for x in raw_mapping if x["region_name"] not in ["#N/A","Unknown"]}
with rasterio.open(DATA/"World_Region_025d.tif") as src:
    source=src.read(1);transform=src.transform;source_crs=str(src.crs)
assert source.shape==(720,1440) and source_crs=="EPSG:4326"
display=np.zeros_like(source,dtype=np.uint8)
for ident,name,_,_,_ in REGIONS:
    display[np.isin(source,source_codes[name])]=ident
named_mask=~np.isin(source,[9,255])
assert np.array_equal(display>0,named_mask)
cell_counts={str(i):int(np.count_nonzero(display==i)) for i,*_ in REGIONS}
geometries={i:[] for i,*_ in REGIONS}
for geo,value in shapes(display,mask=display>0,transform=transform,connectivity=4):
    geometries[int(value)].append(shape(geo))
boundaries=gpd.read_file(DATA/"basemap/word-map-with-correct-china-serbia.shp")
assert str(boundaries.crs)=="EPSG:4326"
null_boundaries=int(boundaries.geometry.isna().sum())
valid_boundaries=boundaries.loc[boundaries.geometry.notna()&~boundaries.geometry.is_empty].geometry.tolist()

fig=plt.figure(figsize=(W/72,H/72))
pc=ccrs.PlateCarree()
world_projection=ccrs.EqualEarth(central_longitude=0)
# Full longitude is retained. Antarctica alone is outside the displayed latitude range.
world=fig.add_axes([8/W,(H-247)/H,512/W,237/H],projection=world_projection,label="world_overview")
world.set_global()
world.set_ylim(world_projection.transform_point(0,-59,pc)[1],world_projection.transform_point(0,85,pc)[1])
world.set_xlim(-17250000,17250000)
world.spines["geo"].set_visible(False)
world.set_facecolor("white")
europe=fig.add_axes([13/W,(H-282)/H,126/W,103/H],
    projection=ccrs.LambertConformal(central_longitude=12,central_latitude=53,standard_parallels=(43,63)),
    label="europe_detail")
europe.set_extent([-25,42,34,72],crs=pc)
europe.spines["geo"].set_edgecolor("#C4CCD1")
europe.spines["geo"].set_linewidth(.55)
europe.set_facecolor("white")

def draw_map(ax,detail=False):
    # Clip the actual vector paths to the visible geographic window before
    # export. This avoids retaining off-panel vector strokes behind the legend.
    geographic_window=box(-90,0,100,89) if detail else box(-180,-59,180,85)
    x0,x1=ax.get_xlim();y0,y1=ax.get_ylim()
    viewport=box(x0,y0,x1,y1)
    project=Transformer.from_crs("EPSG:4326",ax.projection.proj4_init,always_xy=True).transform
    def visible(g):
        clipped=g.intersection(geographic_window)
        if clipped.is_empty:return None
        projected=transform_geometry(project,clipped).intersection(viewport)
        return None if projected.is_empty else projected
    land=[q for g in valid_boundaries if (q:=visible(g)) is not None]
    ax.add_geometries(land,ax.projection,facecolor=UNCLASSIFIED,edgecolor="none",zorder=0)
    for ident,_,_,_,color in REGIONS:
        parts=[q for g in geometries[ident] if (q:=visible(g)) is not None]
        ax.add_geometries(parts,ax.projection,facecolor=color,edgecolor="none",zorder=1)
    borders=[q for g in valid_boundaries if (q:=visible(g.boundary)) is not None]
    ax.add_geometries(borders,ax.projection,facecolor="none",edgecolor="#69767C",
                     linewidth=.2 if not detail else .28,zorder=2)
draw_map(world);draw_map(europe,True)

label_records=[]
def label(ax,ident,anchor,textpos=None):
    x,y=anchor
    row,col=rasterio.transform.rowcol(transform,x,y)
    sampled=int(display[row,col])
    assert sampled==ident,(ident,anchor,sampled)
    point_text=textpos if textpos is not None else anchor
    color="white" if ident in [3,11,23,26] and textpos is None else INK
    options={"fontsize":7.4,"ha":"center","va":"center","weight":"bold","color":color,"zorder":6}
    if textpos is None:
        ax.text(*anchor,str(ident),transform=pc,**options)
    else:
        tr=pc._as_mpl_transform(ax)
        ax.annotate(str(ident),xy=anchor,xycoords=tr,xytext=textpos,textcoords=tr,
                    arrowprops={"arrowstyle":"-","lw":.7,"color":INK,"shrinkA":1,"shrinkB":0},**options)
    if textpos is not None: ax.plot(x,y,"o",transform=pc,ms=1.3,color=INK,mec="none",zorder=5)
    label_records.append({"display_id":ident,"panel":ax.get_label(),"source_anchor":anchor,"text_position":point_text})

for ident,anchor,textpos in [
(1,(-105,60),None),(2,(-95,39),None),(3,(-103,24),None),
(4,(-90.5,15),(-107,7)),(5,(-66,7),None),(6,(-66,-15),(-84,-13)),
(7,(-52,-10),None),(8,(-65,-36),None),(9,(3,46),None),
(14,(103,61),None),(15,(18,28),None),(16,(0,17),None),(17,(39,7.5),None),
(18,(24,-22),None),(19,(23,-30),None),(20,(42,24),None),
(21,(70,48),None),(22,(68,29),(63,16)),(23,(102,18),(129,21)),
(24,(104,35),None),(25,(79,23),None),(26,(140,38),(153,43)),
(27,(127.5,36.5),(151,29)),(28,(114,-3),(110,-14)),(29,(135,-25),None)]:
    label(world,ident,anchor,textpos)
for ident,anchor,textpos in [
(9,(3,47),None),(10,(19,52),None),(11,(8,62),(-8,66)),
(12,(28,53),(38,58)),(13,(35,39),None)]:
    label(europe,ident,anchor,textpos)
fig.text(13/W,1-284/H,"Europe detail",fontsize=7.8,fontweight="bold",color=INK,va="center")

# Four aligned legend columns make numbering and geographic families explicit.
legend_axes=[]
groups=["Americas","Europe","Africa and Middle East","Asia and Oceania"]
for j,group in enumerate(groups):
    ax=fig.add_axes([(10+131*j)/W,(H-424)/H,115/W,122/H],label=f"legend_{j+1}")
    ax.set(xlim=(0,115),ylim=(122,0));ax.axis("off");legend_axes.append(ax)
    ax.text(0,5,group,fontsize=7.6,fontweight="bold",ha="left",va="center",color=INK)
    for row,(ident,name,display_name,_,color) in enumerate([r for r in REGIONS if r[3]==group]):
        y=22+11.7*row
        ax.text(0,y,f"{ident:02d}",fontsize=7.2,ha="left",va="center",color=INK)
        ax.add_patch(Rectangle((13,y-3.6),7.2,7.2,facecolor=color,edgecolor="none"))
        ax.text(25,y,display_name,fontsize=7.2,ha="left",va="center",color=INK)
fig.lines.append(plt.Line2D([10/W,518/W],[1-291/H,1-291/H],transform=fig.transFigure,color="#DDE2E5",lw=.6))
fig.canvas.draw()
rr,cc=np.where(display>0)
lon=-180+(cc+.5)*.25;lat=90-(rr+.5)*.25
projected=world_projection.transform_points(pc,lon,lat)
screen=world.transData.transform(projected[:,:2])
inset_box=europe.get_window_extent()
visible_lat=(lat>=-59)&(lat<=85)
inset_covers_named_cells=int(np.count_nonzero(visible_lat&(screen[:,0]>inset_box.x0)&
    (screen[:,0]<inset_box.x1)&(screen[:,1]>inset_box.y0)&(screen[:,1]<inset_box.y1)))
assert inset_covers_named_cells==0,("Europe inset overlaps named source cells",inset_covers_named_cells)
# Main and inset are intentionally different spatial scales. The comparable
# legend columns provide the repeated geometry that needs alignment.
require_matplotlib_panel_alignment(fig,axes=legend_axes,panel_ids=[f"L{i+1}" for i in range(4)],
    row_groups=[["L1","L2","L3","L4"]],column_groups=[],require_panel_labels=False,
    tolerance_pt=1.5,gutter_tolerance_pt=1.5,json_out=ROOT/"qa/panel_alignment.json",
    overlay_svg=ROOT/"qa/panel_alignment.svg",strict=True)
stem=ROOT/"Figure_S2_Regional_Classification_Astra"
fig.savefig(stem.with_suffix(".pdf"),dpi=600)
fig.savefig(stem.with_suffix(".svg"),dpi=600)
fig.savefig(stem.with_suffix(".png"),dpi=300)
plt.close(fig)
with (DATA/"display_region_mapping.csv").open("w",encoding="utf8",newline="") as f:
    writer=csv.writer(f);writer.writerow(["display_id","source_region_name","display_name","legend_group","raster_codes","color","source_cell_count"])
    for ident,name,display_name,group,color in REGIONS:
        writer.writerow([ident,name,display_name,group,";".join(map(str,source_codes[name])),color,cell_counts[str(ident)]])
(ROOT/"qa/source_and_display_checks.json").write_text(json.dumps({
    "figure":"S2","source_grid_crs":source_crs,"source_grid_shape":list(source.shape),"grid_resolution_degrees":.25,
    "source_extent":[-180,180,-90,90],"display_latitudes":[-59,85],"projection":"Equal Earth; Europe inset Lambert conformal",
    "named_analysis_regions":29,"source_named_cell_count":int(named_mask.sum()),"display_named_cell_count":int((display>0).sum()),
    "display_only_merges":{"Central America":[4,6],"South Asia":[26,27]},
    "neutral_states":{"9":"#N/A in source mapping","255":"Unknown in source mapping, principally ocean; approved land boundary underlay is light grey","ocean":"white"},
    "country_boundary_null_geometries_omitted":null_boundaries,"country_geometry_changes":False,
    "classification_and_model_results_changed":False,"main_map_named_cells_hidden_by_inset":inset_covers_named_cells,"source_cell_counts_by_display_id":cell_counts,
    "label_source_anchors_verified":label_records,
    "source_sha256":{str(p.relative_to(DATA)):hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.rglob("*") if p.is_file() and p.name!="display_region_mapping.csv"},
    "figure_width_pt":W,"figure_height_pt":H,"legend_alignment":"Four equal physical columns; overview and inset intentionally differ in scale"},
    ensure_ascii=False,indent=2),encoding="utf8")
print("Exported S2 with all 29 source-defined analysis regions.")

