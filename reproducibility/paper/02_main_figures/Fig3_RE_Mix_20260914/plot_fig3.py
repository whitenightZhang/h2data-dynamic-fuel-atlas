"""Figure 3: wind-PV configurations and the limits of static cost assessment."""
from pathlib import Path
import json, inspect, hashlib
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.mlab import GaussianKDE
from matplotlib.font_manager import findfont, FontProperties
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
from cartopy.feature import ShapelyFeature
import fitz, tifffile
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT=Path(__file__).resolve().parent
BASE="Figure_3_RE_Mix_and_Cost_Bias"
W,H=528.6217651367188,505.0
SCENARIOS=["2030","LowAE","LowAE_2050"]
YEARS=[2030,2035,2050]
COLORS=["#5E8E9B","#C18473","#9387A5"]
INK="#22282C"
df=pd.read_csv(ROOT/"source_data/RE_mix_all_locations.csv.gz",
    dtype={"scenario":str},float_precision="round_trip",low_memory=False)
assert len(df)==684229 and not df.duplicated(["scenario","latitude","longitude"]).any()
numeric=df.select_dtypes(include=np.number)
assert np.isfinite(numeric).all().all()
assert df.static_pv_share.between(0,1).all() and df.hourly8760_pv_share.between(0,1).all()
assert np.allclose(df.delta_pv_share_pp,100*(df.hourly8760_pv_share-df.static_pv_share),atol=1e-9)
assert np.allclose(df.static_underestimate_percent,
    100*(df.hourly8760_cost_per_kg-df.static_cost_per_kg)/df.hourly8760_cost_per_kg,atol=1e-9)
groups=[df[df.scenario==s].copy() for s in SCENARIOS]
assert [len(g) for g in groups]==[228090,228093,228046]
gstats=[];hstats=[];istats=[]
classes=["Wind >25 pp","Wind 5-25 pp","Stable <=5 pp","PV 5-25 pp","PV >25 pp"]
for year,data in zip(YEARS,groups):
    delta=data.delta_pv_share_pp.to_numpy()
    changed=delta[np.abs(delta)>5]
    gstats.append({"year":year,"all_locations":len(data),"changed_locations":len(changed),
        "stable_share_percent":float((np.abs(delta)<=5).mean()*100),
        "changed_mean_pp":float(changed.mean()),"changed_median_pp":float(np.median(changed)),
        "changed_min_pp":float(changed.min()),"changed_max_pp":float(changed.max())})
    masks=[delta < -25,(delta>=-25)&(delta < -5),np.abs(delta)<=5,
        (delta>5)&(delta<=25),delta>25]
    assert sum(int(m.sum()) for m in masks)==len(data)
    for category,mask in zip(classes,masks):
        vals=data.static_underestimate_percent.to_numpy()[mask]
        q10,q25,median,q75,q90=np.quantile(vals,[.1,.25,.5,.75,.9])
        hstats.append({"year":year,"class":category,"locations":len(vals),
            "share_percent":float(mask.mean()*100),
            "q10":float(q10),"q25":float(q25),"median":float(median),
            "q75":float(q75),"q90":float(q90)})
    bins=pd.cut(data.hourly8760_pv_share*100,np.arange(0,105,5),
        labels=np.arange(2.5,100,5),include_lowest=True)
    grouped=data.groupby(bins,observed=True).static_underestimate_percent
    for center,vals in grouped:
        q25,median,q75=np.quantile(vals,[.25,.5,.75])
        istats.append({"year":year,"pv_share_bin_center_percent":float(center),
            "locations":len(vals),"q25":float(q25),"median":float(median),"q75":float(q75)})
for name,rows in [("G_configuration_change_summary.csv",gstats),
    ("H_cost_by_adjustment.csv",hstats),("I_cost_by_PV_share.csv",istats)]:
    pd.DataFrame(rows).to_csv(ROOT/"source_data"/name,index=False)

mpl.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial"],"font.size":7,
    "axes.labelsize":7,"xtick.labelsize":7,"ytick.labelsize":7,"axes.linewidth":.6,
    "xtick.major.width":.6,"ytick.major.width":.6,"xtick.major.size":2,"ytick.major.size":2,
    "text.color":INK,"axes.labelcolor":INK,"xtick.color":INK,"ytick.color":INK,
    "axes.spines.top":False,"axes.spines.right":False,"pdf.fonttype":42,"ps.fonttype":42,
    "svg.fonttype":"none","figure.facecolor":"white","savefig.facecolor":"white","legend.frameon":False})
assert Path(findfont(FontProperties(family="Arial"),fallback_to_default=False)).exists()
fig=plt.figure(figsize=(W/72,H/72),dpi=600)
def text(x,top,s,**kw):
    return fig.text(x/W,(H-top)/H,s,**kw)
def axpt(x,top,w,h,label,projection=None):
    kw={} if projection is None else {"projection":projection}
    return fig.add_axes([x/W,(H-top-h)/H,w/W,h/H],label=label,**kw)
labels={}
def title(letter,x,top,name):
    labels[letter]=text(x,top,letter,fontsize=7.8,fontweight="bold",va="top")
    text(x+12,top,name,fontsize=7.5,fontweight="bold",va="top")

crs=ccrs.PlateCarree()
world=ShapelyFeature(list(shpreader.Reader(str(ROOT/"source_data/basemap/world.shp")).geometries()),
    crs,facecolor="#F3F4F4",edgecolor="#778086",linewidth=.20)
cmap_share=LinearSegmentedColormap.from_list("Wind_PV",
    ["#4B8199","#8EA997","#D2C59C","#DCA356"],N=256)
cmap_delta=LinearSegmentedColormap.from_list("PV_share_change",
    ["#4B8199","#F7F7F7","#DCA356"],N=256)
delta_limit=float(max(10,np.ceil(np.quantile(np.abs(df.delta_pv_share_pp),.98)/5)*5))
norm_share=Normalize(0,100)
norm_delta=TwoSlopeNorm(vmin=-delta_limit,vcenter=0,vmax=delta_limit)
axes={}
for row,top in enumerate([22,174]):
    for i,(year,data) in enumerate(zip(YEARS,groups)):
        letter=chr(ord("A")+i+row*3);x=[30,201,372][i]
        ax=axpt(x,top,145,72.5,letter,crs);axes[letter]=ax
        ax.set_global();ax.add_feature(world,zorder=0)
        ax.spines["geo"].set_linewidth(.5);ax.spines["geo"].set_edgecolor("#687279")
        ax.set_xticks([-120,-60,0,60,120,180],crs=crs)
        ax.set_xticklabels(["120°W","60°W","0°","60°E","120°E","180°"],fontsize=7)
        ax.set_yticks([-60,-30,0,30,60,90],crs=crs)
        ax.set_yticklabels(["60°S","30°S","0°","30°N","60°N","90°N"],fontsize=7)
        ax.tick_params(pad=1.5,labelleft=i==0,length=2,width=.5)
        values=data.hourly8760_pv_share*100 if row==0 else data.delta_pv_share_pp
        ax.scatter(data.longitude,data.latitude,c=values,
            cmap=cmap_share if row==0 else cmap_delta,
            norm=norm_share if row==0 else norm_delta,s=.16,alpha=.92,
            linewidths=0,edgecolors="none",rasterized=True,transform=crs,zorder=2)
        title(letter,x,top-14,f"Hourly PV share, {year}" if row==0 else f"PV-share change, {year}")
# Shared colorbars distinguish capacity share from within-location share change.
for top,cmap,norm,name,ticks in [
    (124,cmap_share,norm_share,"Hourly PV share of wind + PV capacity (%)",[0,25,50,75,100]),
    (281,cmap_delta,norm_delta,"PV-share change: hourly − annual-average (pp)",[-55,-25,0,25,55])]:
    cax=axpt(65,top,400,6,"colorbar_"+str(top))
    cb=fig.colorbar(mpl.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,orientation="horizontal")
    cb.set_ticks(ticks);cb.ax.tick_params(labelsize=7,length=2,width=.5,pad=1.5)
    cb.outline.set_linewidth(.45)
    text(265,top-12,name,fontsize=7.5,ha="center",va="center")
text(65,144,"Wind only",fontsize=7,ha="left",va="top")
text(465,144,"PV only",fontsize=7,ha="right",va="top")
text(65,302,"Shift toward wind",fontsize=7,ha="left",va="top",color="#4B8199")
text(465,302,"Shift toward PV",fontsize=7,ha="right",va="top",color="#A16D2D")

for letter,x,name in [("G",30,"Changes outside ±5 pp"),("H",201,"Cost underestimation by adjustment"),
    ("I",372,"Cost underestimation by PV share")]:
    title(letter,x,328,name)
gax=axpt(38,361,128,112,"G");hax=axpt(216,361,128,112,"H");iax=axpt(394,361,128,112,"I")
axes.update(G=gax,H=hax,I=iax)
# Shared scenario colors for G-I, with distribution center definitions beside G.
fig.legend(handles=[Line2D([],[],marker="o",color=INK,ls="none",ms=3,label="Mean"),
    Line2D([],[],color=INK,lw=1.2,label="Median")],
    loc="center",bbox_to_anchor=(104/W,(H-347)/H),ncol=2,fontsize=7,
    handlelength=1.1,columnspacing=1.1,handletextpad=.5)
for x in [216,394]:
    for j,(year,color) in enumerate(zip(YEARS,COLORS)):
        xx=x+3+j*42
        style=["solid",(0,(4,2)),(0,(1.5,1.5))][j] if x==394 else "solid"
        marker=["o","s","^"][j] if x==394 else None
        fig.add_artist(Line2D([xx/W,(xx+8)/W],[(H-347)/H]*2,
            transform=fig.transFigure,color=color,lw=1.2,ls=style,
            marker=marker,markersize=2.3,markevery=[0]))
        text(xx+10,347,str(year),fontsize=7,va="center")
# G: condition on >5 pp change; preserve density on each side of the excluded band.
for i,(data,st,color) in enumerate(zip(groups,gstats,COLORS)):
    vals=data.delta_pv_share_pp.to_numpy()
    vals=vals[np.abs(vals)>5]
    kde=GaussianKDE(vals,bw_method="scott")
    grids=[np.linspace(vals.min(),-5,150),np.linspace(5,vals.max(),150)]
    densities=[kde.evaluate(grid) for grid in grids]
    peak=max(float(d.max()) for d in densities)
    for grid,density in zip(grids,densities):
        halfwidth=.32*density/peak
        gax.fill_betweenx(grid,i-halfwidth,i+halfwidth,color=color,alpha=.38,lw=0)
    gax.hlines(st["changed_median_pp"],i-.26,i+.26,color=INK,lw=1.0,zorder=3)
    gax.scatter([i],[st["changed_mean_pp"]],s=16,color=color,edgecolor="white",lw=.5,zorder=4)
    gax.text(i,91,f'{100-st["stable_share_percent"]:.1f}%',ha="center",va="center",fontsize=7)
gax.text(1,113,"Unstable share (>5 pp)",ha="center",va="center",fontsize=7,color="#58636A")
gax.axhline(0,color="#8E999F",lw=.55,ls=(0,(3,2)),zorder=0)
gax.set_xlim(-.55,2.55);gax.set_ylim(-105,122)
gax.set_xticks([0,1,2],[str(y) for y in YEARS]);gax.set_yticks([-100,-50,0,50])
gax.set_xlabel("Scenario",labelpad=4)
gax.set_ylabel("PV-share change (pp)",labelpad=4)
gax.spines["top"].set_visible(False);gax.spines["right"].set_visible(False)
# H: full five-class boxes, exact quartiles and 10th/90th percentile whiskers.
hax.axvspan(1.59,2.41,color="#EFF2F2",lw=0,zorder=0)
for j,(year,color,offset) in enumerate(zip(YEARS,COLORS,[-.2,0,.2])):
    rows=[r for r in hstats if r["year"]==year]
    boxes=[{"med":r["median"],"q1":r["q25"],"q3":r["q75"],
        "whislo":r["q10"],"whishi":r["q90"],"fliers":[]} for r in rows]
    face=tuple(.42*np.array(mpl.colors.to_rgb(color))+.58)
    hax.bxp(boxes,positions=np.arange(5)+offset,widths=.16,showfliers=False,
        patch_artist=True,manage_ticks=False,
        boxprops={"facecolor":face,"edgecolor":color,"linewidth":.6},
        whiskerprops={"color":color,"linewidth":.6},capprops={"color":color,"linewidth":.6},
        medianprops={"color":INK,"linewidth":.8})
hax.set_xlim(-.55,4.55)
hax.set_xticks(range(5),["Wind\n>25","Wind\n5–25","Stable\n≤5","PV\n5–25","PV\n>25"],fontsize=7)
hax.set_xlabel("PV-share adjustment (pp)",labelpad=4)
# I: all observations form a faint neutral cloud; no subsampling.
iax.scatter(df.hourly8760_pv_share*100,df.static_underestimate_percent,
    s=.10,color="#667279",alpha=.006,linewidths=0,rasterized=True,zorder=0)
for year,color,style,marker in zip(YEARS,COLORS,["solid",(0,(4,2)),(0,(1.5,1.5))],["o","s","^"]):
    prof=pd.DataFrame([r for r in istats if r["year"]==year])
    x=prof.pv_share_bin_center_percent.to_numpy()
    iax.fill_between(x,prof.q25.to_numpy(),prof.q75.to_numpy(),color=color,alpha=.15,lw=0,zorder=1)
    iax.plot(x,prof["median"].to_numpy(),color=color,lw=1.2,ls=style,
        marker=marker,markersize=2.4,markevery=4,zorder=3)
iax.set_xlim(0,100);iax.set_xticks([0,25,50,75,100])
iax.set_xlabel("Hourly PV share (%)",labelpad=4)
for ax in [hax,iax]:
    ax.set_ylim(-20,45);ax.set_yticks([-20,0,20,40])
    ax.set_ylabel("Cost underestimation (%)",labelpad=4)
    ax.axhline(0,color="#B7BFC3",lw=.45,zorder=0)
    ax.spines["top"].set_visible(False);ax.spines["right"].set_visible(False)
fig.canvas.draw()
require_matplotlib_panel_alignment(fig,axes=list(axes.values()),
    panel_ids=list(axes),row_groups=[["A","B","C"],["D","E","F"],["G","H","I"]],
    column_groups=[["A","D"],["B","E"],["C","F"]],
    tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=False,strict=True,
    json_out=ROOT/(BASE+".alignment.json"),overlay_svg=ROOT/(BASE+".alignment.svg"))
anchors={k:[v.get_position()[0]*W,H-v.get_position()[1]*H] for k,v in labels.items()}
for col in ["ADG","BEH","CFI"]:
    assert max(anchors[k][0] for k in col)-min(anchors[k][0] for k in col)<.01
(ROOT/(BASE+".panel_anchors.json")).write_text(json.dumps({"status":"PASS","anchors_pt_from_top":anchors,
    "layout_note":"Bottom statistical axes use extra left margin for y-axis labels; equal widths/heights/gutters are checked within their own row."},indent=2),encoding="utf-8")
for ext in ["pdf","svg"]:
    fig.savefig(ROOT/(BASE+"."+ext),dpi=600)
plt.close(fig)
doc=fitz.open(ROOT/(BASE+".pdf"));page=doc[0]
page.get_pixmap(dpi=300,alpha=False).save(ROOT/(BASE+".png"))
pix=page.get_pixmap(dpi=1000,alpha=False)
rgb=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)
writer=getattr(tifffile.TiffWriter,"write",None) or tifffile.TiffWriter.save
key="compression" if "compression" in inspect.signature(writer).parameters else "compress"
tifffile.imwrite(ROOT/(BASE+".tiff"),rgb,photometric="rgb",resolution=(1000,1000),metadata=None,
    **{key:"deflate" if key=="compression" else 6})
checks={"source_rows":len(df),"scenario_rows":dict(zip(YEARS,[len(g) for g in groups])),
    "G":gstats,"H_2035_stable_median":next(r["median"] for r in hstats if r["year"]==2035 and "Stable" in r["class"]),
    "no_random_subsampling":True,"G_condition":"Absolute PV-share change >5 pp; displayed unstable share denominator is all matched locations",
    "G_kernel":"Gaussian Scott bandwidth; evaluated separately outside the excluded [-5,5] pp interval, same peak normalization",
    "H_whiskers":"10th and 90th percentiles; all observations enter statistics",
    "I_bins":"5 percentage-point PV-share bins, include 0 and 100; medians and interquartile ranges",
    "I_bin_counts_sum":sum(r["locations"] for r in istats),
    "map_delta_color_limit_pp":delta_limit,
    "map_delta_saturated_share_percent":float((df.delta_pv_share_pp.abs()>delta_limit).mean()*100),
    "visible_negative_cost_differences":True,
    "palette":dict(zip(YEARS,COLORS))}
assert checks["I_bin_counts_sum"]==len(df)
(ROOT/"data_checks.json").write_text(json.dumps(checks,indent=2),encoding="utf-8")
print(json.dumps({"pdf":str(ROOT/(BASE+".pdf")),"stable_percent":[r["stable_share_percent"] for r in gstats],
    "changed_mean_pp":[r["changed_mean_pp"] for r in gstats],"H_2035_stable_median":checks["H_2035_stable_median"]}))
