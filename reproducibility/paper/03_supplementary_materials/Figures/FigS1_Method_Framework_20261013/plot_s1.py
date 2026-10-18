"""S1: shared resources, independent hourly fuel systems and paired assessment.
Original map pixels and both original weather-curve paths are retained.
No weather series is generated or interpolated.
"""
from pathlib import Path
import hashlib, json, re, shutil
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, PathPatch, Rectangle
from matplotlib.path import Path as MplPath
from PIL import Image
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "source_data"
W, H = 528, 602
INK, MUTED, RULE = "#25363C", "#63757B", "#D9E1E3"
ELEC,H2,HEAT,CO2,FUEL,CURT = "#C28A2E","#28718A","#B86A55","#826B99","#5B8166","#7F8D93"
FILL = {ELEC:"#F7F0E2",H2:"#E9F2F5",HEAT:"#F8EDE8",CO2:"#F0EBF5",FUEL:"#EAF1EC",CURT:"#F0F3F4"}
WIND,SOLAR = "#1F3B5D","#E4572E"
mpl.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial","DejaVu Sans"],
    "font.size":7.4,"pdf.fonttype":42,"ps.fonttype":42,"svg.fonttype":"none",
    "savefig.facecolor":"white","text.color":INK,"axes.spines.top":False,"axes.spines.right":False})
fig = plt.figure(figsize=(W/72,H/72))
canvas = fig.add_axes([0,0,1,1],label="schematic_canvas")
canvas.set(xlim=(0,W),ylim=(H,0));canvas.axis("off")

def txt(x,y,text,size=7.4,ha="center",weight="normal",color=INK):
    return canvas.text(x,y,text,fontsize=size,ha=ha,va="center",fontweight=weight,
                       color=color,linespacing=1.16,zorder=6)

def device(x,y,w,h,text,color,size=7.4,storage=False):
    canvas.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0,rounding_size=2.4",
        facecolor="white" if storage else FILL[color],edgecolor=color if storage else "none",lw=.8,zorder=3))
    if not storage:
        canvas.add_patch(Rectangle((x,y+3),2,h-6,facecolor=color,edgecolor="none",zorder=4))
    txt(x+w/2+(0 if storage else 1),y+h/2,text,size=size)

def path(points):
    return MplPath(np.asarray(points,dtype=float),[MplPath.MOVETO]+[MplPath.LINETO]*(len(points)-1))

def edge(points,color,both=False,dashed=False,lw=1.05):
    canvas.add_patch(FancyArrowPatch(path=path(points),arrowstyle="<|-|>" if both else "-|>",
        mutation_scale=6.3,lw=lw,color=color,linestyle=(0,(2.5,2)) if dashed else "solid",
        zorder=2,capstyle="round",joinstyle="round"))

def line(points,color,lw=1.05,dashed=False):
    p=np.asarray(points,dtype=float)
    canvas.plot(p[:,0],p[:,1],color=color,lw=lw,ls=(0,(2.5,2)) if dashed else "solid",zorder=2)

def dot(x,y,color): canvas.plot(x,y,"o",color=color,ms=2.2,mec="none",zorder=4)

def heading(y,letter,label,note=""):
    txt(10,y,letter,size=9.2,ha="left",weight="bold")
    txt(24,y,label,size=8.5,ha="left",weight="bold")
    if note: txt(517,y,note,size=7.1,ha="right",color=MUTED)

def separator(y): line([(10,y),(518,y)],RULE,lw=.65)

# A establishes the common meteorological, geospatial and technology inputs.
heading(12,"A","Resource and technology inputs")
txt(12,32,"Hourly meteorological data",size=7.9,ha="left",weight="bold")
txt(245,32,"ERA5 · 2023",size=7.4,ha="right",color=MUTED)
txt(288,32,"Geospatial inputs",size=7.9,ha="left",weight="bold")
line([(266,30),(266,147)],RULE,lw=.6)
svg=ET.parse(DATA/"original_hourly_meteorological_week.svg").getroot()
ns={"s":"http://www.w3.org/2000/svg"}
source_xlim=(39.644688,444.244688);source_ylim=(21.935625,182.719375)
cx,cy,cw,ch=31,58,205,60
def wx(x):return cx+(np.asarray(x)-source_xlim[0])/(source_xlim[1]-source_xlim[0])*cw
def wy(y):return cy+(np.asarray(y)-source_ylim[0])/(source_ylim[1]-source_ylim[0])*ch
weather_vertex_counts={}
for gid,color in [("line2d_16",WIND),("line2d_25",SOLAR)]:
    group=svg.find(f".//s:g[@id='{gid}']",ns)
    original_path=group.find("s:path",ns).get("d")
    tokens=re.findall(r"([ML])\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)",original_path)
    assert len(tokens)>50
    # SVG path vertices are retained exactly; they are not a complete hourly dataset.
    verts=np.asarray([(float(x),float(y)) for _,x,y in tokens])
    rendered=np.column_stack([wx(verts[:,0]),wy(verts[:,1])])
    canvas.add_patch(PathPatch(MplPath(rendered,[MplPath.MOVETO if c=="M" else MplPath.LINETO for c,_,_ in tokens]),
        facecolor="none",edgecolor=color,lw=.9,capstyle="round",joinstyle="round",zorder=2))
    weather_vertex_counts[gid]=len(tokens)
line([(cx,cy),(cx,cy+ch),(cx+cw,cy+ch),(cx+cw,cy)],RULE,lw=.6)
txt(12,46,"Wind speed (m/s)",size=6.8,ha="left",color=WIND)
txt(245,46,"Solar radiation (W/m²)",size=6.8,ha="right",color=SOLAR)
for value in (5,8,11):
    y=float(wy(169.458227-(value-5)*21.115019667))
    line([(cx-2,y),(cx,y)],WIND,lw=.6);txt(cx-4,y,str(value),size=6.7,ha="right",color=WIND)
for value in (0,500,1000):
    y=float(wy(175.411023-value*(175.411023-23.785457)/1000))
    line([(cx+cw,y),(cx+cw+2,y)],SOLAR,lw=.6);txt(cx+cw+4,y,str(value),size=6.7,ha="left",color=SOLAR)
for day,hour in zip(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],range(24,169,24)):
    x=cx+hour/168*cw
    line([(x,cy+ch),(x,cy+ch+2)],MUTED,lw=.6);txt(x,cy+ch+8,day,size=6.7)
txt(133,138,"Typical week",size=7.1,color=MUTED)
txt(133,149,"Additional input: air temperature",size=7.0,color=MUTED)

map_rects={}
for name,label,x,y in [
    ("land_use","Land use / cover",286,40),("slope","Slope",410,40),
    ("elevation","Elevation",286,100),("runoff","Annual runoff · 2021–2025",410,100)]:
    im=Image.open(DATA/f"map_{name}.jpg")
    # Crop only the old bitmap footer. Map values, colors and extent are unchanged.
    im=im.crop((0,0,im.width,im.height-28))
    map_w=43*im.width/im.height
    left=x+(105-map_w)/2
    canvas.imshow(im,extent=(left,left+map_w,y+43,y),aspect="auto",zorder=1)
    txt(x+52.5,y+50,label,size=7.0);map_rects[name]=(left,y,map_w,43)
canvas.add_patch(Rectangle((10,159),508,14,facecolor="#F3F6F6",edgecolor="none",zorder=0))
txt(17,166,"Optimization grid  0.25°",size=7.5,ha="left",weight="bold")
txt(510,166,"Technology assumptions  2030 / 2035 / 2050",size=7.5,ha="right")

# B describes alternative systems, not a co-production plant.
heading(186,"B","Hourly production systems","Four fuel pathways optimized separately")
device(18,207,56,26,"PV",ELEC)
device(18,249,56,26,"Onshore\nwind",ELEC)
line([(74,220),(96,220),(96,354)],ELEC)
edge([(74,262),(96,262)],ELEC)
dot(96,220,ELEC);dot(96,262,ELEC)
device(18,298,56,26,"Battery",ELEC,storage=True)
edge([(74,311),(96,311)],ELEC,both=True);dot(96,311,ELEC)
device(18,349,56,24,"Curtailment",CURT,size=7.0)
edge([(96,341),(46,341),(46,349)],CURT,dashed=True)
# Dedicated electricity branch above the conversion network supplies synthesis.
line([(96,220),(96,198),(378,198),(378,348)],ELEC)
device(136,209,73,40,"Electrolysis\nAE / PEM",H2,size=7.9)
edge([(96,229),(136,229)],ELEC);dot(96,229,ELEC)
line([(209,229),(348,229)],H2);line([(348,223),(348,407)],H2);dot(348,229,H2)
device(243,264,64,28,"Hydrogen\nstorage",H2,storage=True)
edge([(275,229),(275,264)],H2,both=True);dot(275,229,H2)

txt(133,309,"Carbon supply · e-methanol and e-SAF",size=7.1,ha="left",color=MUTED)
device(133,330,60,29,"Heat pump",HEAT)
device(235,330,61,29,"Low-temp\nDAC",CO2)
line([(96,319),(265.5,319)],ELEC)
edge([(163,319),(163,330)],ELEC);edge([(265.5,319),(265.5,330)],ELEC)
dot(96,319,ELEC);dot(163,319,ELEC)
edge([(193,344.5),(235,344.5)],HEAT)
device(133,379,60,25,"Thermal\nstorage",HEAT,storage=True)
edge([(214,344.5),(214,391.5),(193,391.5)],HEAT,both=True);dot(214,344.5,HEAT)
# CO2 compression only charges the buffer; direct DAC supply bypasses it.
device(229,379,62,25,"CO2\ncompression",CO2,size=7.0)
device(308,379,34,25,"CO2\nbuffer",CO2,storage=True)
line([(296,344.5),(363,344.5)],CO2)
edge([(303,344.5),(303,369),(260,369),(260,379)],CO2);dot(303,344.5,CO2)
edge([(291,391.5),(308,391.5)],CO2);edge([(342,391.5),(363,391.5)],CO2)
line([(363,217),(363,391.5)],CO2);dot(363,344.5,CO2);dot(363,391.5,CO2)
edge([(96,354),(96,414),(260,414),(260,404)],ELEC)

for center,label,output,store_y in [
    (223,"e-SAF synthesis\nand upgrading","e-SAF",244),
    (281,"Methanol\nsynthesis","e-methanol",307),
    (342,"Ammonia\nsynthesis","Green\nammonia",368)]:
    height=32 if center==223 else 26
    device(390,center-height/2,62,height,label,FUEL,size=7.0)
    edge([(348,center),(390,center)],H2);dot(348,center,H2)
    edge([(378,center+6),(390,center+6)],ELEC);dot(378,center+6,ELEC)
    if center<300:
        edge([(363,center-6),(390,center-6)],CO2);dot(363,center-6,CO2)
    edge([(452,center),(471,center)],FUEL)
    txt(476,center,output,size=7.4,ha="left",weight="bold",color=FUEL)
    device(393,store_y,59,18,"Fuel storage",FUEL,size=7.0,storage=True)
    line([(462,center),(462,store_y+9)],FUEL)
    edge([(452,store_y+9),(462,store_y+9)],FUEL,both=True);dot(462,center,FUEL)
edge([(348,407),(463,407)],H2)
txt(469,407,"Renewable\nhydrogen",size=7.2,ha="left",weight="bold",color=H2)

for x,color,label in [(14,ELEC,"Electricity"),(105,H2,"Hydrogen"),(196,HEAT,"Heat"),
    (260,CO2,"CO2"),(322,FUEL,"Fuel"),(385,CURT,"Curtailed power")]:
    edge([(x,433),(x+12,433)],color,dashed=color==CURT)
    txt(x+17,433,label,size=7.2,ha="left")
separator(446)

# C defines the annual comparator without storage or hourly dispatch.
heading(459,"C","Annual-average assessment","No storage")
device(14,482,88,31,"Wind or PV\nLower LCOE",ELEC,size=7.6)
device(133,474,81,24,"AE → LCOH\n4,000 h/yr",H2,size=7.2)
device(133,506,81,24,"DAC → LCOC\nCF = 0.8",CO2,size=7.2)
device(264,488,77,31,"Fuel synthesis\nCF = 0.8",FUEL,size=7.6)
device(388,488,127,31,"Annual-average\nproduction costs",CURT,size=7.8)
line([(102,497.5),(116,497.5)],ELEC)
edge([(116,497.5),(116,486),(133,486)],ELEC)
edge([(116,497.5),(116,518),(133,518)],ELEC)
edge([(116,497.5),(116,536),(302.5,536),(302.5,519)],ELEC)
edge([(214,486),(238,486),(238,497),(264,497)],H2)
edge([(214,518),(246,518),(246,510),(264,510)],CO2)
edge([(341,503.5),(388,503.5)],FUEL)
edge([(214,486),(371,486),(371,493),(388,493)],H2)

# D links both methods to the same cells and potential weights.
heading(551,"D","Assessment workflow")
stage_rects={}
for i,(title,description) in enumerate([
    ("Resource processing","Hourly profiles\nDevelopable capacity"),
    ("Fuel-specific optimization","Global H2 screening\nDerived-fuel candidates"),
    ("Production potential","Capacity scaling\nBasin water screening"),
    ("Cost-competitive potential","Paired costs · same grid cells\nCommon potential weights")]):
    x=10+i*131
    txt(x,569,title,size=7.25,ha="left",weight="bold")
    txt(x,585,description,size=7.0,ha="left",color=MUTED)
    if i<3:
        arrow_start=x+(96.87,104.52,95.25)[i]
        edge([(arrow_start,579),(arrow_start+11,579)],CURT,lw=.85)
    stage_rects[f"D{i+1}"]=(x,562,115,34)

# Compare the four source-map areas and four workflow stages at final size.
panel_rects={**{f"map_{k}":v for k,v in map_rects.items()},**stage_rects}
panel_axes=[]
for name,(x,top,w,h) in panel_rects.items():
    ax=fig.add_axes([x/W,1-(top+h)/H,w/W,h/H],label=name,zorder=-1)
    ax.axis("off");ax.patch.set_visible(False);panel_axes.append(ax)
fig.canvas.draw()
require_matplotlib_panel_alignment(fig,axes=panel_axes,panel_ids=list(panel_rects),
    row_groups=[["map_land_use","map_slope"],["map_elevation","map_runoff"],["D1","D2","D3","D4"]],
    column_groups=[["map_land_use","map_elevation"],["map_slope","map_runoff"]],
    require_panel_labels=False,tolerance_pt=1.5,gutter_tolerance_pt=1.5,
    json_out=ROOT/"qa/panel_alignment.json",overlay_svg=ROOT/"qa/panel_alignment.svg",strict=True)
stem=ROOT/"Figure_S1_Method_Framework_Astra"
fig.savefig(stem.with_suffix(".pdf"),dpi=600)
fig.savefig(stem.with_suffix(".svg"),dpi=600)
fig.savefig(stem.with_suffix(".png"),dpi=300)
plt.close(fig)
shutil.copy2(stem.with_suffix(".pdf"),ROOT.parents[1]/"figures_engineering/FigureS15_Method_Framework.pdf")
(ROOT/"qa/content_checks.json").write_text(json.dumps({
    "figure":"S1","weather_year":2023,"runoff_period":"2021–2025",
    "technology_years":[2030,2035,2050],"grid_resolution_degrees":.25,
    "annual_AE_full_load_hours":4000,"annual_DAC_synthesis_capacity_factor":.8,
    "annual_storage":False,"independent_fuel_optimizations":True,
    "weather_original_sha256":hashlib.sha256((DATA/"original_hourly_meteorological_week.svg").read_bytes()).hexdigest(),
    "weather_path_vertices":weather_vertex_counts,
    "weather_reuse":"Every original curve-path vertex retained; editable axes relabelled; no new observations or smoothing",
    "storage_supply_connections":["battery to electricity bus","H2 storage to hydrogen bus","CO2 buffer to synthesis","thermal storage to DAC heat supply","fuel storage to output"],
    "CO2_storage_compression_branch":"DAC to compression to buffer; direct DAC feed bypasses compression; compressor has electricity input",
    "geospatial_thumbnail_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob("map_*.jpg")},
    "geospatial_thumbnail_display":"Original map artwork; old raster footers cropped and replaced by editable vector labels",
    "width_mm":W/72*25.4,"height_mm":H/72*25.4,"model_and_results_changed":False},
    indent=2,ensure_ascii=False),encoding="utf8")
print("Exported S1 with restored original meteorological curves.")

