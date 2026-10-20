"""Full regional bubble matrix: color encodes hourly cost; size classes encode paired underestimation."""
from pathlib import Path
import sys,json,inspect
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.colorbar import ColorbarBase
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages
from scipy.stats import gaussian_kde
import fitz,tifffile
from audit_panel_alignment import require_matplotlib_panel_alignment
sys.stdout.reconfigure(encoding="utf-8")
R=Path(__file__).resolve().parent
BASE="Figure_5_SAF1215"
W,H=528.621765,494.
PRODS=["Ammonia","Methanol","FTL"];YEARS=[2030,2035,2050]
NAMES={"Ammonia":"Green ammonia","Methanol":"E-methanol","FTL":"E-SAF"}
REF={"Ammonia":630,"Methanol":550,"FTL":1215}
BLUE=np.array(mpl.colors.to_rgb("#286879"))*.75+.25
ORANGE=np.array(mpl.colors.to_rgb("#CF8A30"))*.75+.25
REFCOLOR="#7E898E"
XLIM={"Ammonia":(250,900),"Methanol":(400,1200),"FTL":(1100,2900)}
XTICKS={"Ammonia":[300,600,900],"Methanol":[400,800,1200],"FTL":[1200,2000,2800]}
YTICKS={"Ammonia":[200,600,1000],"Methanol":[400,800,1200,1600],"FTL":[1000,2000,3000,4000]}
mpl.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial"],"font.size":7,
 "axes.labelsize":7,"xtick.labelsize":7,"ytick.labelsize":7,"legend.fontsize":7,
 "pdf.fonttype":42,"ps.fonttype":42,"svg.fonttype":"none","axes.linewidth":.65,
 "axes.spines.top":False,"axes.spines.right":False,"savefig.facecolor":"white",
 "text.color":"#263137","axes.labelcolor":"#263137","axes.edgecolor":"#536167",
 "xtick.color":"#263137","ytick.color":"#263137"})
df=pd.read_csv(R/"source_data/matched_costs.csv.gz",float_precision="round_trip")
reg=pd.read_csv(R/"source_data/regional_summary.csv",float_precision="round_trip")
assert len(df)==162261 and len(reg)==261
assert np.isfinite(df[["hourly_cost","static_cost","underestimation_pct"]]).all().all()
assert np.allclose(df.underestimation_pct,100*(df.hourly_cost-df.static_cost)/df.hourly_cost)


LIMITS={"Ammonia":(250,1250),"Methanol":(400,1700),"FTL":(1000,4500)}
TICKS={"Ammonia":[250,750,1250],"Methanol":[400,1050,1700],"FTL":[1000,2750,4500]}
COST_CMAP=LinearSegmentedColormap.from_list("Hourly_cost",["#C0D5D8","#86AFB8","#4D8998","#195969"])
SIZE_EDGES=np.array([0,10,15,20,25,np.inf])
SIZE_LABELS=["<10", "10–<15", "15–<20", "20–<25", "≥25"]
SIZE_DIAMETERS_PT=np.array([2.3,4.2,6.3,8.6,10.5])
assert (reg.underestimation_pct>=0).all()
assert np.all(np.diff(SIZE_DIAMETERS_PT)>0)
assert np.all(np.diff(SIZE_EDGES)>0)
reg["size_class_index"]=pd.cut(reg.underestimation_pct,SIZE_EDGES,right=False,labels=False).astype(int)
assert reg.size_class_index.between(0,4).all()
check=df.groupby(["product","year","region_name"]).agg(hourly_median=("hourly_cost","median"),static_median=("static_cost","median"),underestimation_pct=("underestimation_pct","median"),nodes=("hourly_cost","size")).reset_index()
check=reg.merge(check,on=["product","year","region_name"],suffixes=("_provided","_recomputed"),validate="one_to_one")
differences={k:float((check[k+"_provided"]-check[k+"_recomputed"]).abs().max()) for k in ["hourly_median","static_median","underestimation_pct","nodes"]}
assert max(differences.values())<1e-9
regions=reg.loc[reg.year.eq(2050)&reg["product"].eq("Ammonia")].sort_values("hourly_median").region_label.tolist()
assert len(regions)==29 and len(set(regions))==29
fig=plt.figure(figsize=(W/72,H/72))
def axes_at(x,top,w,h):
 return fig.add_axes([x/W,1-(top+h)/H,w/W,h/H])
def text(x,top,s,**kw):
 return fig.text(x/W,1-top/H,s,va=kw.pop("va","top"),**kw)
labels={}
def header(letter,x,top,title):
 labels[letter]=text(x,top,letter,fontsize=9,fontweight="bold")
 text(x+14,top,title,fontsize=8.2,fontweight="bold")
header("A",4,9,"Regional hourly costs and annual-average cost underestimation")
MX,MT,MW,RH=112.,58.,243.,11.
ax=axes_at(MX,MT,MW,RH*29)
ax.set_xlim(0,9);ax.set_ylim(29,0);ax.axis("off")
axes={"A":ax}
# Guides are pale and remain behind every mark. Values are carried only by circles.
for ir,r in enumerate(regions):
 if ir%2==0:
  fig.add_artist(Rectangle((4/W,1-(MT+(ir+1)*RH)/H),(MX+MW-4)/W,RH/H,transform=fig.transFigure,facecolor="#F5F8F9",edgecolor="none",zorder=-1))
 text(MX-7,MT+(ir+.5)*RH,r,ha="right",va="center",fontsize=7)
for column in range(10):
 ax.axvline(column,color="#D6DFE2" if column in [0,3,6,9] else "#E7EDEF",lw=.5 if column in [0,3,6,9] else .3,zorder=0)
ax.axhline(0,color="#D6DFE2",lw=.5,zorder=0)
ax.axhline(29,color="#D6DFE2",lw=.5,zorder=0)
plotted=[]
for ip,p in enumerate(PRODS):
 cx=MX+(ip*3+1.5)*MW/9
 text(cx,29,NAMES[p],ha="center",fontsize=8,fontweight="bold")
 norm=Normalize(*LIMITS[p])
 for iy,y in enumerate(YEARS):
  text(MX+(ip*3+iy+.5)*MW/9,44,str(y),ha="center",fontsize=7)
  g=reg.loc[reg.year.eq(y)&reg["product"].eq(p)].set_index("region_label").loc[regions].reset_index()
  assert len(g)==29 and g.hourly_median.between(*LIMITS[p]).all()
  size_codes=g.size_class_index.to_numpy()
  areas=SIZE_DIAMETERS_PT[size_codes]**2
  colors=COST_CMAP(norm(g.hourly_median.to_numpy()))
  ax.scatter(np.full(29,ip*3+iy+.5),np.arange(29)+.5,s=areas,c=colors,edgecolors="none",linewidths=0,zorder=3)
  for ir,row in enumerate(g.itertuples()):
   plotted.append({"row":ir+1,"column":ip*3+iy+1,"region_name":row.region_name,"region_label":row.region_label,"product":p,"year":y,"hourly_median_usd_t":row.hourly_median,"median_paired_underestimation_pct":row.underestimation_pct,"nodes":int(row.nodes),"underestimation_size_class":SIZE_LABELS[size_codes[ir]],"size_class_index":int(size_codes[ir]),"marker_size_parameter_pt2":float(areas[ir]),"marker_disk_area_pt2":float(np.pi/4*areas[ir]),"marker_diameter_pt":float(np.sqrt(areas[ir])),"color_hex":mpl.colors.to_hex(colors[ir]),"cost_scale_min":LIMITS[p][0],"cost_scale_max":LIMITS[p][1]})
 cax=axes_at(MX+ip*MW/3+10.5,393,60,6)
 cb=ColorbarBase(cax,cmap=COST_CMAP,norm=norm,orientation="horizontal",ticks=TICKS[p])
 cb.outline.set_visible(False)
 cb.ax.tick_params(labelsize=7,length=2,width=.45,pad=3)
 cb.ax.xaxis.set_major_formatter(mpl.ticker.StrMethodFormatter("{x:,.0f}"))
text(4,391,"Hourly cost\n(USD/t)",fontsize=7)
text(4,430,"Annual-average cost underestimation (%)",fontsize=7,va="center")
for xp,diameter,label in zip([19,77,145,216,292],SIZE_DIAMETERS_PT,SIZE_LABELS):
 fig.add_artist(Line2D([xp/W],[1-451/H],transform=fig.transFigure,marker="o",ms=diameter,mfc="#6A919C",mec="none",mew=0,ls="none"))
 text(xp+diameter/2+5,451,f"{label}%",fontsize=7,va="center")
distribution=[];kde_records=[]
for ip,p in enumerate(PRODS):
 x=414.;panel_top=9.+151*ip
 letter="BCD"[ip]
 header(letter,378,panel_top,NAMES[p])
 ax=axes_at(x,panel_top+42,104,92);axes[letter]=ax
 allp=df.loc[df["product"].eq(p)]
 lo=float(allp[["hourly_cost","static_cost"]].min().min())
 hi=float(allp[["hourly_cost","static_cost"]].max().max())
 bottom=np.floor(lo*.9/50)*50
 top=np.ceil(hi*1.06/50)*50
 ax.set_xlim(-.6,2.6);ax.set_ylim(bottom,top);ax.set_yticks(YTICKS[p])
 ax.set_xticks([0,1,2]);ax.set_xticklabels(YEARS)
 ax.set_ylabel("Production cost (USD/t)",labelpad=5)
 ax.tick_params(axis="both",length=2.5,pad=3,width=.65)
 ax.axhline(REF[p],color=REFCOLOR,ls=(0,(4,3)),lw=.75,zorder=0)
 ax.annotate("Fossil-reference\ncost",xy=(.98,REF[p]),
  xycoords=("axes fraction","data"),xytext=(0,14),textcoords="offset points",
  ha="right",va="bottom",fontsize=6.5,color="#5A696F",linespacing=1.1,zorder=6)
 for j,y in enumerate(YEARS):
  g=df.loc[df.year.eq(y)&df["product"].eq(p)]
  assert len(g)==18029
  curves=[]
  for method,column,color,side in [("Hourly","hourly_cost",BLUE,-1),("Static","static_cost",ORANGE,1)]:
   vals=g[column].to_numpy()
   assert vals.min()>=bottom and vals.max()<=top
   kde=gaussian_kde(vals,bw_method="scott")
   grid=np.linspace(vals.min(),vals.max(),512)
   density=kde(grid)
   curves.append((method,vals,color,side,grid,density,kde))
  peak=max(float(c[5].max()) for c in curves)
  for method,vals,color,side,grid,density,kde in curves:
   widths=.38*density/peak
   # Both halves share one density-to-width scale within the same year.
   ax.fill_betweenx(grid,j,j+side*widths,facecolor=color,edgecolor=color,lw=.65,zorder=2)
   q1,med,q3=np.percentile(vals,[25,50,75])
   xpos=j+side*.095
   ax.vlines(xpos,q1,q3,color="#3B4D56",lw=1,zorder=4)
   ax.plot(xpos,med,marker="o",ms=2.8,mfc="white",mec="#3B4D56",mew=.6,ls="none",zorder=5)
   distribution.append({"product":p,"year":y,"method":method,"nodes":len(vals),"q1":q1,"median":med,"q3":q3})
   kde_records.append({"product":p,"year":y,"method":method,"observations":len(vals),"bandwidth":"Scott","factor":float(kde.factor),"evaluation_positions":512,"minimum":float(vals.min()),"maximum":float(vals.max()),"common_width_normalization_within_year":True})
handles=[
 Line2D([0],[0],marker="o",ms=4,color=BLUE,ls="none",label="Hourly"),
 Line2D([0],[0],marker="o",ms=4,color=ORANGE,ls="none",label="Annual-average"),
 Line2D([0],[0],color=REFCOLOR,lw=.75,ls=(0,(4,3)),label="Fossil-reference cost")]
fig.legend(handles=handles,loc="center",bbox_to_anchor=(280/W,1-478/H),ncol=3,
 frameon=False,fontsize=7.5,handlelength=1.8,columnspacing=2.3,handletextpad=.7)

fig.canvas.draw()
require_matplotlib_panel_alignment(fig,axes=list(axes.values()),panel_ids=list(axes),
 row_groups=[],column_groups=[["B","C","D"]],
 tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=False,strict=True,
 json_out=R/"qa/panel_alignment.json",overlay_svg=R/"qa/panel_alignment.svg")
anchors={k:[v.get_position()[0]*W,H-v.get_position()[1]*H] for k,v in labels.items()}
assert max(anchors[k][0] for k in "BCD")-min(anchors[k][0] for k in "BCD")<.01
assert np.allclose(np.diff([anchors[k][1] for k in "BCD"]),151.)
(R/"qa/panel_anchors.json").write_text(json.dumps({"status":"PASS","anchors_pt":anchors,"column_groups":[["B","C","D"]],"A":"Left regional matrix spans the three supporting panels at right; only the right-column panels are equal-span comparable axes."},indent=2),encoding="utf-8")
for ext in ["pdf","svg"]:fig.savefig(R/(BASE+"."+ext),dpi=1000)
plt.close(fig)
doc=fitz.open(R/(BASE+".pdf"));page=doc[0]
page.get_pixmap(dpi=300,alpha=False).save(R/(BASE+".png"))
page.get_pixmap(dpi=300,alpha=False).save(R/"Fig4_preview.png")
page.get_pixmap(dpi=300,clip=fitz.Rect(0,0,362,460),alpha=False).save(R/"Panel_A_bubble_matrix.png")
pix=page.get_pixmap(dpi=1000,alpha=False)
rgb=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)
writer=getattr(tifffile.TiffWriter,"write",None) or tifffile.TiffWriter.save
key="compression" if "compression" in inspect.signature(writer).parameters else "compress"
tifffile.imwrite(R/(BASE+".tiff"),rgb,photometric="rgb",resolution=(1000,1000),metadata=None,**{key:"deflate" if key=="compression" else 6})
pd.DataFrame(plotted).to_csv(R/"source_data/plotted_bubble_matrix.csv",index=False,float_format="%.17g")
pd.DataFrame(distribution).to_csv(R/"source_data/plotted_distribution_statistics.csv",index=False,float_format="%.17g")
(R/"qa/kde_parameters.json").write_text(json.dumps(kde_records,indent=2),encoding="utf-8")
(R/"qa/data_integrity.json").write_text(json.dumps({"status":"PASS","paired_records":len(df),"regional_combinations":len(plotted),"regions":len(regions),"recomputed_aggregation_max_abs_errors":differences,"size_encoding":"Five ordered underestimation classes; circle areas do not encode continuous proportional values.","size_classes_pct":SIZE_LABELS,"class_counts":[int(reg.size_class_index.eq(i).sum()) for i in range(5)],"marker_diameters_pt":SIZE_DIAMETERS_PT.tolist(),"minimum_gap_pct":float(reg.underestimation_pct.min()),"minimum_circle_diameter_pt":float(SIZE_DIAMETERS_PT.min()),"width_pt":float(page.rect.width),"height_pt":float(page.rect.height),"tiff_dimensions":[pix.width,pix.height]},indent=2),encoding="utf-8")
print("Rendered",BASE,"with",len(plotted),"circles and unchanged full distributions.")
