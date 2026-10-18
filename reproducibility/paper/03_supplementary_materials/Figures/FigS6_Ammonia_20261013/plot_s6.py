from pathlib import Path
from io import BytesIO
import json, sys, warnings
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
sys.stdout.reconfigure(encoding="utf-8")
ROOT=Path(__file__).parent; DATA=ROOT/"source_data"
sys.path.insert(0,str(ROOT))
from audit_panel_alignment import require_matplotlib_panel_alignment
mpl.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial","DejaVu Sans"],"font.size":7.2,
"axes.labelsize":7.2,"xtick.labelsize":7,"ytick.labelsize":7,"legend.fontsize":7.2,
"pdf.fonttype":42,"ps.fonttype":42,"svg.fonttype":"none","axes.linewidth":.5,
"axes.spines.top":False,"axes.spines.right":False,"xtick.major.size":2,"ytick.major.size":2,
"xtick.major.width":.5,"ytick.major.width":.5,"text.color":"#263238","axes.labelcolor":"#263238",
"xtick.color":"#263238","ytick.color":"#263238","legend.frameon":False,"savefig.facecolor":"white"})
# Final compact page: preserve plot sizes and fonts; remove repeated storage titles/ticks.
W,H=528,598
BLUE="#286879"; ORANGE="#CF8A30"; PURPLE="#826B98"; GRAY="#89969B"; PALE="#DCE2E4"; INK="#263238"
summary=pd.read_csv(DATA/"site_summary.csv").set_index("site")
costs=pd.read_csv(DATA/"cost_decomposition.csv")
params=json.loads((DATA/"parameters.json").read_text(encoding="utf-8"))
re_capacity=summary.wind_capacity+summary.pv_capacity
assert (re_capacity>0).all()
summary["battery_power_percent_RE"]=summary.battery_energy_capacity/re_capacity*100
summary["battery_energy_h_RE"]=summary.battery_storage_capacity/re_capacity
rated_h2=(summary.electrolyzer_capacity_AE*params["electrolyzer_eff_AE"]+summary.electrolyzer_capacity_PEM*params["electrolyzer_eff_PEM"])*3.6/120
summary["h2_storage_h_EL"]=summary.hydrogen_storage_capacity/rated_h2
np.testing.assert_allclose(summary.battery_energy_h_RE,summary.battery_energy_per_RE_kW_h,rtol=1e-12)
np.testing.assert_allclose(summary.h2_storage_h_EL,summary.h2_duration_h,rtol=1e-12)
summary[["wind_capacity","pv_capacity","battery_energy_capacity","battery_storage_capacity","hydrogen_storage_capacity","electrolyzer_capacity_AE","electrolyzer_capacity_PEM","battery_power_percent_RE","battery_energy_h_RE","h2_storage_h_EL"]].to_csv(DATA/"storage_power_energy_metrics.csv")
keys=["W","H","S"]; hourly={k:pd.read_csv(DATA/f"hourly_{k}.csv") for k in keys}
# Match the main figure's illustrative week; preserve all annual data.
def electric_load(d):
    return (d.electrolyzer_power_AE+d.electrolyzer_power_PEM
        +d.fuel_synthesis_power*params["fuel_electricity_ratio"]
        +d.hydrogen_charge*params["hydrogen_storage_elec"]
        +d.heat_pump_output/params["heat_pump_cop"]+d.dac_electricity+d.co2_comp_elec)
selection=json.loads((ROOT.parents[2]/"02_main_figures/Fig6_Cost_Gap_Decomposition_20260916/window_selection.json").read_text(encoding="utf-8"))
start=int(selection["start_hour"]);stop=start+168
assert selection["day_first"]==120 and selection["day_last"]==126
(ROOT/"window_selection.json").write_text(json.dumps(selection,indent=2),encoding="utf-8")
period_records=[]
for k in keys:
    for period,frame in [("selected_week",hourly[k].iloc[start:stop]),("full_year",hourly[k])]:
        re=frame.wind_power+frame.pv_power;load=electric_load(frame)
        period_records.append({"site":k,"period":period,"hours":len(frame),
            "curtailment_percent_RE":float(frame.surplus.clip(lower=0).sum()/re.sum()*100),
            "battery_supply_percent_process_load":float(frame.battery_discharge.clip(lower=0).sum()/load.sum()*100),
            "H2_supply_percent_synthesis_demand":float(frame.hydrogen_discharge.clip(lower=0).sum()/(frame.fuel_synthesis_power*params["fuel_hydrogen_ratio"]).sum()*100)})
pd.DataFrame(period_records).to_csv(DATA/"weekly_and_annual_operation_metrics.csv",index=False)
metric_limits={
    "battery_power":max(16.5,float(summary.battery_power_percent_RE.max())*1.3),
    "battery_energy":max(.72,float(summary.battery_energy_h_RE.max())*1.3),
    "h2_capacity":max(16.5,float(summary.h2_storage_h_EL.max())*1.3)}
bounds=[]
for k in keys:
    d=hourly[k].iloc[start:stop];s=summary.loc[k]
    elcap=s.electrolyzer_capacity_AE+s.electrolyzer_capacity_PEM
    rated=(s.electrolyzer_capacity_AE*params["electrolyzer_eff_AE"]+s.electrolyzer_capacity_PEM*params["electrolyzer_eff_PEM"])*.03
    bounds.append(((d.wind_power+d.pv_power).max()/elcap*100,d.battery_charge.max()/elcap*100,d.fuel_synthesis_power.max()*params["fuel_hydrogen_ratio"]/rated*100,d.hydrogen_charge.max()/rated*100))
bounds=np.asarray(bounds)
power_upper=max(250.,float(np.ceil(bounds[:,0].max()*1.05/50)*50))
power_lower=-max(40.,float(np.ceil(bounds[:,1].max()*1.05/25)*25))
h2_upper=max(100.,float(np.ceil(bounds[:,2].max()*1.05/25)*25))
h2_lower=-max(65.,float(np.ceil(bounds[:,3].max()*1.05/25)*25))
cost_span=max(1.,float(np.ptp(np.r_[costs.difference_USD_per_t.to_numpy(),0.])))
cost_low=min(0.,float(costs.difference_USD_per_t.min()))-.2*cost_span
cost_high=max(0.,float(costs.difference_USD_per_t.max()))+.25*cost_span
fig=plt.figure(figsize=(W/72,H/72))
axes=[]; ids=[]; rows=[]; columns=[]
X=[62,224,386]; WIDTH=126
def tx(x,y,text,size=7.2,ha="left",weight="normal",color=INK,**kw):
    return fig.text(x/W,y/H,text,fontsize=size,ha=ha,va="center",weight=weight,color=color,**kw)
def axis(i,y,h,ident,row):
    a=fig.add_axes([X[i]/W,y/H,WIDTH/W,h/H],label=ident)
    axes.append(a);ids.append(ident);rows.append(row);columns.append(i)
    return a
def panel(i,y,letter,label):
    tx(X[i],y,letter,10,weight="bold");tx(X[i]+13,y,label,8.5,weight="bold")
def clean_time(a,i):
    a.set_xlim(0,7);a.set_ylim(0,100);a.set_yticks([0,50,100])
    a.set_xticks([0,2,4,6,7]);a.tick_params(pad=2)
    a.grid(axis="y",color="#E9ECEE",linewidth=.4,zorder=0)
    if i: a.set_yticklabels([])
def legend_at(handles,labels,x,y,ncol,spacing=1.6):
    return fig.legend(handles,labels,loc="center",bbox_to_anchor=(x/W,y/H),ncol=ncol,
      handlelength=1.5,handletextpad=.45,columnspacing=spacing,borderpad=0)
titles=["Wind-cluster","Wind–solar complementary","Solar-cluster"]
coords=["61.50°N, 99.75°W","17.50°N, 18.25°E","37.50°N, 34.75°E"]
flow_checks=[]
for i,k in enumerate(keys):
    s=summary.loc[k]; d=hourly[k]; window=d.iloc[start:stop].copy()
    tx(X[i]+WIDTH/2,578,titles[i],10.3,ha="center",weight="bold")
    panel(i,558,chr(65+i),"Configuration")
    a=axis(i,510,38,chr(65+i),"configuration")
    a.set_xlim(0,100);a.set_ylim(-.35,1.55);a.axis("off")
    for y,first,second,n1,n2 in [(1,s.wind_capacity,s.pv_capacity,"Wind","PV"),(0,s.electrolyzer_capacity_AE,s.electrolyzer_capacity_PEM,"AE","PEM")]:
        share=100*first/(first+second)
        a.barh(y,share,height=.54,color=BLUE,linewidth=0)
        a.barh(y,100-share,left=share,height=.54,color=ORANGE,linewidth=0)
        for pct,left,label,col in [(share,0,n1,"white"),(100-share,share,n2,INK)]:
            if pct>=10:
                segment_label=f"{label} {pct:.1f}%"
                prop=mpl.font_manager.FontProperties(family=mpl.rcParams["font.sans-serif"],size=7.2,weight="bold")
                renderer=fig.canvas.get_renderer()
                text_width=renderer.get_text_width_height_descent(segment_label,prop,False)[0]
                segment_width=a.get_window_extent().width*pct/100
                if text_width+2*fig.dpi/72>segment_width:
                    a.text(left,y+.50,segment_label,ha="left",va="center",
                        fontsize=7.2,color=BLUE,weight="bold")
                else:
                    a.text(left+pct/2,y,segment_label,ha="center",va="center",fontsize=7.2,color=col,weight="bold")
    # Three compact rows retain separate power and energy quantities and scales.
    storage_rows=[
      ("Battery power\n(% RE)",491,s.battery_power_percent_RE,16.5,PALE,GRAY,"battery_power","%"),
      ("Battery energy\n(h RE)",473,s.battery_energy_h_RE,.72,GRAY,"none","battery_energy"," h"),
      ("H2 storage\n(h EL)",455,s.h2_storage_h_EL,16.5,PURPLE,"none","h2_capacity"," h"),
    ]
    for label,axis_y,value,maximum,face,edge,metric,unit in storage_rows:
        maximum=metric_limits[metric]
        if i==0:
            tx(X[0]-8,axis_y+6,label,7.2,ha="right",linespacing=1.3)
        storage=axis(i,axis_y,12,chr(65+i)+"_"+metric,metric)
        storage.barh([0],[value],height=.64,color=face,edgecolor=edge,linewidth=.6 if edge!="none" else 0,zorder=3)
        storage.set_xlim(0,maximum); storage.set_ylim(-.5,.5)
        storage.set_xticks([]); storage.set_yticks([])
        for spine in storage.spines.values(): spine.set_visible(False)
        storage.text(value+maximum*.02,0,f"{value:.1f}{unit}",va="center",ha="left",fontsize=7.2)
        assert value>=0 and value<maximum*.9

    panel(i,438,chr(68+i),"Operation")
    # Model flow accounting shows what storage contributes, not just inventory.
    hours=np.arange(168)/24
    el_capacity=s.electrolyzer_capacity_AE+s.electrolyzer_capacity_PEM
    rated_h2_output=(s.electrolyzer_capacity_AE*params["electrolyzer_eff_AE"]+s.electrolyzer_capacity_PEM*params["electrolyzer_eff_PEM"])*3.6/120
    el_power=window.electrolyzer_power_AE+window.electrolyzer_power_PEM
    total_load=(el_power+window.fuel_synthesis_power*params["fuel_electricity_ratio"]
                +window.hydrogen_charge*params["hydrogen_storage_elec"]
                +window.heat_pump_output/params["heat_pump_cop"]+window.dac_electricity+window.co2_comp_elec)
    re_available=window.wind_power+window.pv_power
    power_residual=re_available+window.battery_discharge-total_load-window.battery_charge-window.surplus
    assert power_residual.abs().max()<5e-5
    direct_re_raw=total_load-window.battery_discharge
    battery_in=window.battery_charge.clip(lower=0)
    battery_out=window.battery_discharge.clip(lower=0)
    # This signed residual is no longer a plotted supply allocation.
    np.testing.assert_allclose(direct_re_raw,re_available-window.battery_charge-window.surplus,atol=5e-5,rtol=0)
    h2_produced=(window.electrolyzer_power_AE*params["electrolyzer_eff_AE"]+window.electrolyzer_power_PEM*params["electrolyzer_eff_PEM"])*3.6/120
    h2_need=window.fuel_synthesis_power*params["fuel_hydrogen_ratio"]
    h2_residual=h2_produced+window.hydrogen_discharge-h2_need-window.hydrogen_charge
    assert h2_residual.min()>-1e-5
    direct_h2_raw=h2_need-window.hydrogen_discharge
    assert direct_h2_raw.min()>-1e-5
    direct_h2=direct_h2_raw.clip(lower=0)
    h2_in=window.hydrogen_charge.clip(lower=0)
    h2_out=window.hydrogen_discharge.clip(lower=0)
    np.testing.assert_allclose(direct_h2_raw,h2_produced-window.hydrogen_charge-h2_residual,atol=1e-12,rtol=0)
    # Only negligible negative solver residuals are floored in the displayed derived flows.
    for col in ["battery_charge","battery_discharge","hydrogen_charge","hydrogen_discharge"]:
        assert window[col].min()>-5e-5
    bd=(battery_out/el_capacity*100).to_numpy(); bc=(battery_in/el_capacity*100).to_numpy()
    el=(el_power/el_capacity*100).to_numpy()
    hd=(h2_out/rated_h2_output*100).to_numpy(); hc=(h2_in/rated_h2_output*100).to_numpy()
    hdir=(direct_h2/rated_h2_output*100).to_numpy(); demand=(h2_need/rated_h2_output*100).to_numpy()
    battery_supply_share=float(battery_out.sum()/total_load.sum()*100)
    h2_supply_share=float(h2_out.sum()/h2_need.sum()*100)
    curtailment_share=float(window.surplus.clip(lower=0).sum()/re_available.sum()*100)
    tx(X[i],407,f"Curtailment {curtailment_share:.1f}%",7.2,color="#9B632B")
    tx(X[i],397,f"Battery supplies {battery_supply_share:.1f}%",7.2,color="#596B74")
    tx(X[i],306,f"Stored H2 supplies {h2_supply_share:.1f}%",7.2,color=PURPLE)
    gross=(re_available/el_capacity*100).to_numpy()
    curtailed=(window.surplus.clip(lower=0)/el_capacity*100).to_numpy()
    load_curve=(total_load/el_capacity*100).to_numpy()
    assert (re_available+window.battery_discharge-window.surplus).min()>-5e-5
    # Surplus is a bus-flow variable; tiny simultaneous battery cycling is retained.
    a=axis(i,328,63,chr(68+i)+"_power","power")
    a.fill_between(hours,0,gross,color=PALE,lw=0,zorder=1)
    a.fill_between(hours,gross-curtailed,gross,color="#EEDBC3",lw=0,zorder=2)
    # Independent zero-based battery areas, not a stack with renewable generation.
    a.fill_between(hours,0,bd,color=GRAY,lw=0,zorder=3)
    a.fill_between(hours,-bc,0,color=GRAY,alpha=.35,lw=0,zorder=2)
    a.axhline(100,color="#AEB9BE",lw=.45,ls=(0,(2,3)),zorder=2)
    a.plot(hours,el,color=BLUE,lw=1.05,zorder=5)
    a.axhline(0,color="#738086",lw=.5,zorder=3)
    a.set_xlim(0,7);a.set_ylim(power_lower,power_upper);a.set_yticks(np.arange(0,power_upper,100))
    a.set_xticks([0,2,4,6,7]);a.set_xticklabels([]);a.tick_params(axis="x",bottom=False)
    a.tick_params(pad=2)
    if i:a.set_yticklabels([])
    if i==0:a.set_ylabel("Power (% EL cap.)",labelpad=5)
    b=axis(i,247,54,chr(68+i)+"_hydrogen","hydrogen")
    b.fill_between(hours,0,hdir,color=PALE,lw=0,zorder=1)
    b.fill_between(hours,hdir,hdir+hd,color=PURPLE,lw=0,zorder=2)
    b.fill_between(hours,-hc,0,color=PURPLE,alpha=.30,lw=0,zorder=1)
    b.plot(hours,demand,color=ORANGE,lw=1.05,zorder=3)
    b.axhline(0,color="#738086",lw=.5,zorder=2)
    b.set_xlim(0,7);b.set_ylim(h2_lower,h2_upper);b.set_yticks(np.arange(-50,h2_upper+1,50))
    b.set_xticks([0,2,4,6,7]);b.tick_params(pad=2)
    if i:b.set_yticklabels([])
    if i==0:b.set_ylabel("H2 flow (% rated output)",labelpad=5)
    b.set_xlabel("Day within selected week",labelpad=3)
    flow_checks.append({"site":k,"start_hour":start,"end_hour_exclusive":stop,
       "power_balance_max_abs_kW":float(power_residual.abs().max()),
       "curtailment_percent_RE":curtailment_share,
       "minimum_net_RE_after_charging_and_curtailment_kW":float(direct_re_raw.min()),
       "minimum_H2_balance_residual_kg_h":float(h2_residual.min()),
       "positive_H2_balance_slack_kg":float(h2_residual.clip(lower=0).sum()),
       "H2_balance_slack_excluded_from_direct_supply":True,
       "battery_discharge_share_of_week_electric_load_percent":float(battery_out.sum()/total_load.sum()*100),
       "H2_discharge_share_of_week_synthesis_H2_demand_percent":float(h2_out.sum()/h2_need.sum()*100)})
    window["net_RE_after_charging_and_curtailment_kW"]=direct_re_raw
    window["total_process_electric_load_kW"]=total_load
    window["other_process_electric_load_kW"]=total_load-el_power
    window["curtailment_percent_EL_capacity"]=curtailed
    window["total_process_demand_percent_EL_capacity"]=load_curve
    window["direct_H2_use_kg_h"]=direct_h2
    window["H2_synthesis_demand_kg_h"]=h2_need
    window["H2_balance_residual_kg_h"]=h2_residual
    window["battery_discharge_percent_EL_capacity"]=bd
    window["battery_charge_percent_EL_capacity"]=bc
    window["direct_H2_percent_rated_output"]=hdir
    window["H2_discharge_percent_rated_output"]=hd
    window["H2_charge_percent_rated_output"]=hc
    window["H2_synthesis_demand_percent_rated_output"]=demand
    tx(X[i],214,f"Electrolysis: {s.electrolyzer_FLH:,.0f} h/yr",7.4,color=BLUE)
    tx(X[i],202,f"Synthesis: {s.synthesis_FLH:,.0f} h/yr",7.4,color="#936222")
    panel(i,188,chr(71+i),"Cost gap decomposition")
    tx(X[i]+WIDTH/2,173,f"{s.static_cost_USD_per_t:.1f}  →  {s.hourly_cost_USD_per_t:.1f} USD/t",8.3,ha="center",weight="bold")
    c=axis(i,66,94,chr(71+i),"cost");c.set_facecolor("none")
    order=["Renewable power","Electrolyzers","Battery","H2 storage","Other process"]
    cc=costs.loc[costs.site==k].set_index("component").loc[order]
    delta=cc.difference_USD_per_t.to_numpy(); ypos=np.arange(4,-1,-1)
    c.barh(ypos,delta,height=.55,color=[ORANGE if v>=0 else BLUE for v in delta],linewidth=0,zorder=3)
    c.axvline(0,color="#65747A",lw=.6,zorder=2)
    c.set_xlim(cost_low,cost_high);c.set_ylim(-.65,4.65);c.xaxis.set_major_locator(mpl.ticker.MaxNLocator(nbins=3));c.set_yticks(ypos)
    c.set_yticklabels(["RE power","Electrolyzers","Battery","H2 storage","Other process"] if i==0 else [])
    c.tick_params(axis="y",length=0,pad=4);c.tick_params(axis="x",pad=2)
    c.spines["left"].set_visible(False)
    for y,v in zip(ypos,delta):
        # Keep negative labels left of the bar, positive labels to the right.
        c.text(v+(.025*cost_span if v>=0 else -.025*cost_span),y,f"{v:+.1f}",ha="left" if v>=0 else "right",va="center",fontsize=7.2)
    gap=s.hourly_cost_USD_per_t-s.static_cost_USD_per_t
    tx(X[i]+WIDTH/2,38,f"Net cost gap  {gap:+.1f} USD/t",8,ha="center",weight="bold")
    window["site"]=k
    window["RE_percent_electrolyzer_capacity"]=(re_available/el_capacity*100).to_numpy()
    window["electrolysis_percent_rated"]=el
    window["H2_SOC_percent"]=(window.hydrogen_storage_balance/s.hydrogen_storage_capacity*100).to_numpy()
    window["battery_SOC_percent"]=(window.energy_balance/s.battery_storage_capacity*100).to_numpy()
    window["synthesis_percent_rated"]=(window.fuel_synthesis_power/s.fuel_synthesis_capacity*100).to_numpy()
    window.to_csv(DATA/f"plotted_week_{k}.csv",index=False)
legend_at([Patch(facecolor=PALE),Patch(facecolor="#EEDBC3"),Patch(facecolor=GRAY),
 Patch(facecolor=GRAY,alpha=.35),Line2D([],[],color=BLUE,lw=1.05)],
 ["RE generation","Curtailment","Battery discharge (+)","Battery charge (−)",
 "Electrolyzer demand"],287,422,5,.95)
legend_at([Patch(facecolor=PALE),Patch(facecolor=PURPLE),Patch(facecolor=PURPLE,alpha=.30),Line2D([],[],color=ORANGE,lw=1.05)],
 ["Direct H2 use","H2 discharge (+)","H2 charge (−)","Synthesis H2 demand"],287,315,4,.95)
(ROOT/"flow_accounting_checks.json").write_text(json.dumps(flow_checks,indent=2),encoding="utf-8")
pd.DataFrame(flow_checks)[["site","battery_discharge_share_of_week_electric_load_percent","H2_discharge_share_of_week_synthesis_H2_demand_percent"]].to_csv(DATA/"storage_supply_shares_selected_week.csv",index=False)
tx(281,18,"Component cost change (hourly − annual-average, USD/t)",7.5,ha="center")
fig.canvas.draw()
require_matplotlib_panel_alignment(fig,axes=axes,panel_ids=ids,row_groups=[[ids[j] for j,r in enumerate(rows) if r==row] for row in dict.fromkeys(rows)],column_groups=[[ids[j] for j,c in enumerate(columns) if c==col] for col in range(3)],
    exemptions=[{"panels":ids,"checks":["vertical-gutter"],"reason":"Different evidence sections reserve space for headings and annual metrics; the two aligned operating traces have a smaller internal gap. Every column uses identical vertical coordinates."}],
    json_out=ROOT/"panel_alignment.json",tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
stem=ROOT/"Figure_S6_Configuration_Operation_Cost"
fig.savefig(stem.with_suffix(".pdf"))
fig.savefig(stem.with_suffix(".svg"))
fig.savefig(stem.with_suffix(".png"),dpi=300)
buf=BytesIO();fig.savefig(buf,format="tiff",dpi=600,pil_kwargs={"compression":"tiff_lzw"})
stem.with_suffix(".tiff").write_bytes(buf.getvalue())
from matplotlib.transforms import Bbox
fig.savefig(ROOT/"Figure_S6_Operation_Detail.png",dpi=300,bbox_inches=Bbox.from_extents(6/72,193/72,520/72,448/72))
plt.close(fig)
print(json.dumps({"exports":str(stem),"window":selection,"width_mm":W/72*25.4,"height_mm":H/72*25.4}),flush=True)

