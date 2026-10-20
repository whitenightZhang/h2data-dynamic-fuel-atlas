"""Conservative refinement of the original regional bars and nine cost-curve insets."""
from pathlib import Path
from io import BytesIO
import sys,json,hashlib
import numpy as np,pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator,StrMethodFormatter
from audit_panel_alignment import require_matplotlib_panel_alignment
sys.stdout.reconfigure(encoding="utf-8")
R=Path(__file__).resolve().parent
BASE="Figure_2_SAF1215"
W,H=528.621765,472.
L,MW=50.,364.
BLUE="#286879";ORANGE="#CF8A30";INK="#263137";GREY="#6C777D"
meta=json.loads((R/"source_data/original_plot_metadata.json").read_text(encoding="utf-8"))
stats=pd.read_csv(R/"source_data/region_potential.csv",float_precision="round_trip")
curves=pd.read_csv(R/"source_data/cost_ranked_curves.csv.gz",float_precision="round_trip")
regions=meta["region_order"]
assert len(stats)==261 and len(regions)==21
assert stats.static_underestimate_Mt.eq(0).all()
assert np.allclose(stats.static_supply_Mt,stats.dynamic_supply_Mt+stats.static_overestimate_Mt,atol=1e-9)
colors={}
for region,rgb in meta["original_colors"].items():
 rgb=np.array(rgb)
 # Mild desaturation retains the original region hue identities.
 colors[region]=tuple(.90*rgb+.10*np.mean(rgb))
mpl.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial"],"font.size":7,
 "axes.labelsize":7.5,"xtick.labelsize":7,"ytick.labelsize":7,"legend.fontsize":7,
 "axes.linewidth":.65,"axes.spines.top":False,"axes.spines.right":False,
 "axes.edgecolor":"#68777D","axes.labelcolor":INK,"text.color":INK,"xtick.color":INK,
 "ytick.color":INK,"pdf.fonttype":42,"ps.fonttype":42,"svg.fonttype":"none",
 "savefig.facecolor":"white","figure.facecolor":"white","pdf.compression":9})
fig=plt.figure(figsize=(W/72,H/72))
def txt(x,y,s,**kw):
 return fig.text(x/W,1-y/H,s,va=kw.pop("va","top"),**kw)
def at(x,y,w,h):
 return fig.add_axes([x/W,1-(y+h)/H,w/W,h/H])
def swatch(x,top,color,cap=False):
 fig.add_artist(Rectangle((x/W,1-(top+6)/H),9/W,6/H,transform=fig.transFigure,
  facecolor=color,edgecolor=GREY if cap else "none",linewidth=.45,linestyle=(0,(2,1.5))))
def rule(x,top,color,dash=False):
 fig.add_artist(Line2D([x/W,(x+13)/W],[1-top/H]*2,transform=fig.transFigure,
  color=color,lw=1.05,linestyle=(0,(3,2)) if dash else "-"))

panels=[];insets=[];bars=[];curve_checks=[];letters=[]
for k,(fuel,name,reference) in enumerate(zip(["ammonia","methanol","saf"],
 ["Green ammonia","E-methanol","E-SAF"],[630.,550.,1215.])):
 head=12.+136*k;top=33.+136*k
 letters.append(txt(L,head,"ABC"[k],fontsize=9,fontweight="bold"))
 txt(L+14,head,name,fontsize=9,fontweight="bold")
 txt(L+132,head+1,f"Reference: {reference:,.0f} USD/t",ha="left",fontsize=7.5,color=GREY)
 ax=at(L,top,MW,97.);ax.set_facecolor("none");panels.append(ax)
 sub=stats.loc[stats.fuel.eq(fuel)].copy()
 sub["plot_region"]=sub.region_label.where(sub.region_label.isin(regions[:-1]),"Other regions")
 group=sub.groupby(["year","plot_region"],as_index=False)[["dynamic_supply_Mt","static_supply_Mt","static_overestimate_Mt"]].sum()
 n=len(regions);bw=.82/n*.88
 offsets=np.linspace(-.41+bw/2,.41-bw/2,n)
 for j,region in enumerate(regions):
  s=group[group.plot_region.eq(region)].set_index("year").loc[[2030,2035,2050]]
  xs=np.arange(3)+offsets[j]
  hourly=s.dynamic_supply_Mt.to_numpy();extra=s.static_overestimate_Mt.to_numpy()
  ax.bar(xs,hourly,bw,color=colors[region],edgecolor="white",linewidth=.22,zorder=3)
  ax.bar(xs,extra,bw,bottom=hourly,color=(*colors[region],.36),edgecolor=GREY,
   linewidth=.42,linestyle=(0,(2.4,1.6)),zorder=4)
  for iy,year in enumerate([2030,2035,2050]):
   bars.append(dict(fuel=fuel,year=year,region=region,region_order=j+1,
    hourly_Mt=hourly[iy],static_only_Mt=extra[iy],static_Mt=hourly[iy]+extra[iy]))
 ax.set_xlim(-.56,2.56)
 ymax=float(group.static_supply_Mt.max())*1.70
 ax.set_ylim(0,ymax)
 ax.set_xticks([0,1,2],["2030","2035","2050"])
 ax.set_yticks([[0,500,1000,1500,2000],[0,500,1000,1500],[0,200,400,600]][k])
 ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
 ax.tick_params(direction="out",length=2.5,width=.65,pad=3)
 ax.set_ylabel("Cost-competitive potential\n(Mt/yr)",labelpad=5)
 for boundary in [.5,1.5]: ax.axvline(boundary,color="#D8E0E3",lw=.6,zorder=0)
 if k==2: ax.set_xlabel("Year",labelpad=4)
 for j,year in enumerate([2030,2035,2050]):
  right=L+(j+.98)/3.12*MW
  ix=right-66.
  iax=at(ix,top+7,66.,32.);insets.append(iax)
  assert len(curves[(curves.fuel==fuel)&(curves.year==year)])==2*meta["curve_node_counts"][f"{fuel}_{year}"]
  endpoint=[]
  for method,color,dash in [("dynamic",BLUE,False),("static",ORANGE,True)]:
   c=curves[(curves.fuel==fuel)&(curves.year==year)&(curves.method==method)].sort_values("cost")
   assert c.cost.is_monotonic_increasing and c.cumulative_Mt.is_monotonic_increasing
   assert np.allclose(c.potential_Mt.cumsum(),c.cumulative_Mt,rtol=0,atol=1e-7)
   endpoint.append(float(c.cumulative_Mt.iloc[-1]))
   # Each location's cost covers its cumulative-potential interval.
   step_x=np.r_[0.,c.cumulative_Mt.to_numpy()]
   step_y=np.r_[c.cost.iloc[0],c.cost.to_numpy()]
   cost_line,=iax.step(step_x,step_y,where="pre",color=color,lw=.9,
    linestyle=(0,(3,1.8)) if dash else "-",zorder=3)
   qualified=float(c.loc[c.cost<=reference,"potential_Mt"].sum())
   original=float(sub.loc[sub.year.eq(year),"dynamic_supply_Mt" if method=="dynamic" else "static_supply_Mt"].sum())
   assert abs(qualified-original)<1e-8
   path=cost_line.get_path().vertices
   below_reference=path[path[:,1]<=reference,0]
   drawn_qualified=float(below_reference.max()) if below_reference.size else 0.
   assert abs(drawn_qualified-qualified)<1e-7
   curve_checks.append(dict(fuel=fuel,year=year,method=method,nodes=len(c),endpoint_Mt=endpoint[-1],qualified_Mt=qualified))
  assert abs(endpoint[0]-endpoint[1])<1e-7
  lo,hi=meta["curve_windows"][f"{fuel}_{year}"]
  span=hi-lo
  lo=min(lo,reference-.06*span);hi=max(hi,reference+.06*span)
  iax.set_ylim(lo,hi);iax.set_xlim(0,max(endpoint)*1.02)
  iax.axhline(reference,color="#8A9498",lw=.6,linestyle=(0,(2.2,1.8)),zorder=1)
  iax.yaxis.set_major_locator(MaxNLocator(nbins=2,min_n_ticks=2))
  iax.xaxis.set_major_locator(MaxNLocator(nbins=2,min_n_ticks=2))
  iax.tick_params(labelsize=7,length=1.8,width=.5,pad=1)
  iax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
  iax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
  for spine in iax.spines.values(): spine.set_linewidth(.5)
  iax.text(0,1.10,str(year),transform=iax.transAxes,ha="left",va="bottom",fontsize=7,color=INK)
  if k==0 and j==0:
   iax.set_ylabel("Cost (USD/t)",fontsize=7,labelpad=1)
   iax.set_xlabel("Cumulative potential\n(Mt/yr)",fontsize=7,labelpad=1)
  iax.set_facecolor("white")

txt(431,120,"Region",fontsize=7.5,fontweight="bold")
for j,region in enumerate(regions):
 y=137+10.4*j
 swatch(431,y+1,colors[region])
 txt(444,y,region,fontsize=7)

swatch(43,437,"#87989D");txt(57,436,"Hourly cost-competitive potential",fontsize=7)
swatch(236,437,(.6,.65,.67,.36),cap=True);txt(250,436,"Annual-average-only potential",fontsize=7)
rule(43,456,BLUE);txt(61,452,"Hourly cost curve",fontsize=7)
rule(199,456,ORANGE,True);txt(217,452,"Annual-average cost curve",fontsize=7)
rule(351,456,"#8A9498",True);txt(369,452,"Reference cost",fontsize=7)
fig.canvas.draw()
require_matplotlib_panel_alignment(fig,axes=panels,panel_ids=["A","B","C"],
 column_groups=[["A","B","C"]],json_out=R/"qa/main_alignment.json",
 overlay_svg=R/"qa/main_alignment.svg",strict=True)
ids=[f"{r}{c}" for r in "ABC" for c in "123"]
require_matplotlib_panel_alignment(fig,axes=insets,panel_ids=ids,
 row_groups=[ids[0:3],ids[3:6],ids[6:9]],
 column_groups=[[ids[i],ids[i+3],ids[i+6]] for i in range(3)],
 json_out=R/"qa/inset_alignment.json",overlay_svg=R/"qa/inset_alignment.svg",strict=True)
assert np.ptp([t.get_position()[0] for t in letters])*W<1e-9
pd.DataFrame(bars).to_csv(R/"source_data/plotted_regional_bars.csv",index=False)
pd.DataFrame(curve_checks).to_csv(R/"source_data/plotted_curve_checks.csv",index=False)
fig.savefig(R/(BASE+".pdf"),metadata={"Title":"Regional cost-competitive production potential under annual-average and hourly assessments","Author":""})
fig.savefig(R/(BASE+".svg"))
fig.savefig(R/(BASE+".png"),dpi=300)
buffer=BytesIO()
fig.savefig(buffer,format="tiff",dpi=600,pil_kwargs={"compression":"tiff_lzw"})
(R/(BASE+".tiff")).write_bytes(buffer.getvalue())
plt.close(fig)
(R/"qa/data_checks.json").write_text(json.dumps(dict(status="PASS",regions_order_unchanged=regions,
 regional_bar_records=len(bars),source_regional_rows=len(stats),curve_observations=len(curves),
 original_source_difference=meta["source_difference"],all_curve_endpoint_checks_pass=True,
 all_below_reference_checks_pass=True,dimensions_pt=[W,H],minimum_font_pt=7),indent=2),encoding="utf-8")
print(json.dumps({"status":"rendered","bar_records":len(bars),"curve_observations":len(curves),"width_pt":W,"height_pt":H}))

