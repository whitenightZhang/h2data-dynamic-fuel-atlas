"""Create the agreed Fig1 from its accompanying immutable source CSVs."""
from pathlib import Path
import sys, json, hashlib, inspect
import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.font_manager import findfont, FontProperties
import tifffile
from audit_panel_alignment import require_matplotlib_panel_alignment

ROOT = Path(__file__).resolve().parent
OUT = ROOT
BASE = "Figure_1_Parity_Clarity"
WIDTH_MM, HEIGHT_MM = 172, 166
BLUE = "#286879"
AMBER = "#CF8A30"
LIGHT_AMBER = "#F6E9D2"
CELL_AMBER = "#E8B873"
GRAY = "#899096"
PALE = "#ECEFF1"
INK = "#22282C"

mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial"],
    "font.size": 7.5, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": .65, "xtick.major.width": .65,
    "ytick.major.width": .65, "xtick.major.size": 2.5,
    "ytick.major.size": 2.5, "text.color": INK,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "savefig.facecolor": "white", "figure.facecolor": "white",
    "legend.frameon": False, "pdf.compression": 9,
})
font = findfont(FontProperties(family="Arial"), fallback_to_default=False)
assert Path(font).is_file()
points = pd.read_csv(ROOT / "source_data" / "A_methanol_2035_common_locations.csv")
common = pd.read_csv(ROOT / "source_data" / "B_common_locations_all_fuels.csv")
assert len(points) == 7407
assert np.isfinite(points[["static_usd_t", "hourly_usd_t"]].to_numpy()).all()
assert (points.potential_Mt > 0).all()
assert (points.threshold_usd_t == 550).all()
assert not points.duplicated(["latitude", "longitude", "region_match"]).any()
static_pass = points.static_usd_t <= 550
hourly_pass = points.hourly_usd_t <= 550
classes = {
    "Both below": static_pass & hourly_pass,
    "Static only": static_pass & ~hourly_pass,
    "Both above": ~static_pass & ~hourly_pass,
    "Hourly only": ~static_pass & hourly_pass,
}
counts = {name: int(mask.sum()) for name, mask in classes.items()}
assert counts == {"Both below": 365, "Static only": 4780, "Both above": 2262, "Hourly only": 0}
shares = {name: value / len(points) * 100 for name, value in counts.items()}
assert np.isclose(sum(shares.values()), 100)
fuels = ["ammonia", "methanol", "saf"]
titles = ["Green ammonia", "E-methanol", "E-SAF"]
benchmarks = [630, 550, 1215]
expected_n = [7614, 7407, 7377]
years = [2030, 2035, 2050, 9999]
grids = {}
for fuel, benchmark, expected in zip(fuels, benchmarks, expected_n):
    cohort = common[common.fuel == fuel].copy()
    assert len(cohort) == expected
    assert not cohort.duplicated(["latitude", "longitude", "region_match"]).any()
    for method in ["static", "hourly"]:
        costs = cohort[[f"{method}_{year}_usd_t" for year in years[:3]]].to_numpy()
        assert np.isfinite(costs).all()
        qualify = costs <= benchmark
        first = np.where(qualify.any(axis=1), np.array(years[:3])[qualify.argmax(axis=1)], 9999)
        np.testing.assert_array_equal(first, cohort[f"{method}_first_observed_year"])
        assert not np.any(np.diff(qualify.astype(int), axis=1) < 0)
    grid = pd.crosstab(cohort.static_first_observed_year, cohort.hourly_first_observed_year).reindex(index=years, columns=years, fill_value=0).to_numpy(dtype=int)
    assert grid.sum() == expected
    grids[fuel] = grid

# Reconstruct the scatter quadrants from the methanol first-scenario matrix.
methanol_common = common[common.fuel.eq("methanol")]
matched = points.merge(methanol_common, on=["latitude", "longitude", "region_match"], validate="one_to_one")
assert len(matched) == len(points) == len(methanol_common)
np.testing.assert_array_equal(matched.static_usd_t, matched.static_2035_usd_t)
np.testing.assert_array_equal(matched.hourly_usd_t, matched.hourly_2035_usd_t)
grid_m = grids["methanol"]
assert counts["Both below"] == int(grid_m[:2,:2].sum())
assert counts["Static only"] == int(grid_m[:2,2:].sum())
assert counts["Both above"] == int(grid_m[2:,2:].sum())
assert counts["Hourly only"] == int(grid_m[2:,:2].sum())


# Per-scenario parity shares, calculated from costs rather than rounded matrix labels.
status_rows = []
for fuel, benchmark, n in zip(fuels, benchmarks, expected_n):
    cohort = common[common.fuel.eq(fuel)]
    for year in years[:3]:
        sp = cohort[f"static_{year}_usd_t"].le(benchmark)
        hp = cohort[f"hourly_{year}_usd_t"].le(benchmark)
        assert not (hp & ~sp).any()
        vals = [int((sp & hp).sum()), int((sp & ~hp).sum()), int((~sp & ~hp).sum())]
        assert sum(vals) == n
        idx = years.index(year)
        grid = grids[fuel]
        reconstructed = [int(grid[:idx+1,:idx+1].sum()), int(grid[:idx+1,idx+1:].sum()), int(grid[idx+1:,idx+1:].sum())]
        assert vals == reconstructed
        for category, number in zip(['Parity under both', 'Parity only under static', 'No parity under either'],vals):
            status_rows.append({'fuel':fuel,'scenario':year,'category':category,'locations':number,'denominator':n,'percent':number/n*100})
status = pd.DataFrame(status_rows)
status.to_csv(OUT/'source_data'/'B_parity_status_by_scenario.csv',index=False)
for category, count in zip(['Parity under both','Parity only under static','No parity under either'],[365,4780,2262]):
    r=status[status.fuel.eq('methanol') & status.scenario.eq(2035) & status.category.eq(category)].iloc[0]
    assert int(r.locations)==count

def build(kind):
    fig = plt.figure(figsize=(WIDTH_MM/25.4, HEIGHT_MM/25.4),dpi=300)
    base=f"Figure_1_{kind}"
    def ax_mm(x,y,w,h,gid):
        return fig.add_axes([x/WIDTH_MM,y/HEIGHT_MM,w/WIDTH_MM,h/HEIGHT_MM],label=gid)
    def text_mm(x,y,text,**kw):
        return fig.text(x/WIDTH_MM,y/HEIGHT_MM,text,**kw)
    labels=[text_mm(7,163,'A',fontsize=11,fontweight='bold',va='top')]
    text_mm(21,162,'2035',fontsize=8.5,va='top')
    a=ax_mm(21,96,145,61,'A')
    a.add_patch(Rectangle((400,550),150,630,facecolor=LIGHT_AMBER,edgecolor='none',zorder=0))
    a.axvline(550,color='#69737A',lw=.75,ls=(0,(3,2)),zorder=1)
    a.axhline(550,color='#69737A',lw=.75,ls=(0,(3,2)),zorder=1)
    for name,color,marker,size,alpha in [('Both above',GRAY,'o',4,.40),('Static only',AMBER,'^',5,.43),('Both below',BLUE,'o',6,.66)]:
        sample=points.loc[classes[name]]
        a.scatter(sample.static_usd_t,sample.hourly_usd_t,s=size,marker=marker,facecolor=color,edgecolors='none',alpha=alpha,zorder=2)
    a.set_xlim(400,1000); a.set_ylim(400,1180)
    assert points.static_usd_t.between(*a.get_xlim()).all()
    assert points.hourly_usd_t.between(*a.get_ylim()).all()
    a.set_xticks([400,550,700,850,1000]); a.set_yticks([400,550,700,850,1000,1150])
    a.set_xlabel('E-methanol cost, annual-average (USD/t)',labelpad=4)
    a.set_ylabel('E-methanol cost, hourly (USD/t)',labelpad=4)
    a.text(412,1135,f"Cost-competitive only\nunder annual-average\n{shares['Static only']:.1f}%",fontsize=8,fontweight='bold',color='#8A571D',va='top',linespacing=1.25)
    a.text(705,1150,f"Not cost-competitive\nunder either\n{shares['Both above']:.1f}%",fontsize=7.5,color='#5F686E',va='top',linespacing=1.2)
    a.text(410,432,f"Cost-competitive\nunder both: {shares['Both below']:.1f}%",fontsize=7.1,color=BLUE,va='center')
    labels.append(text_mm(7,83,'B',fontsize=11,fontweight='bold',va='top'))
    facets=[]
    for xx,fuel,title,n,benchmark in zip([21,73,125],fuels,titles,expected_n,benchmarks):
        text_mm(xx+20.5,82,title,fontsize=8.5,fontweight='bold',ha='center',va='top')
        text_mm(xx+20.5,76.5,f'Reference cost: {benchmark:,} USD/t',fontsize=7.2,color='#69737A',ha='center',va='top')
        if kind=='Matrix_Refined':
            ax=ax_mm(xx,29,41,41,f'B_{fuel}')
            grid=grids[fuel]
            for si,sy in enumerate(years):
                for hi,hy in enumerate(years):
                    number=int(grid[si,hi])
                    if number==0: color,lc='#FFFFFF',INK
                    elif sy==hy==9999: color,lc='#C7CDD1',INK
                    elif sy==hy: color,lc=BLUE,'white'
                    elif sy<hy: color,lc=CELL_AMBER,'#442C0D'
                    else: raise AssertionError('Reverse parity category')
                    # Displayed x=static, y=hourly, both increasing from lower left.
                    ax.add_patch(Rectangle((si-.5,hi-.5),1,1,facecolor=color,edgecolor='#DFE3E6',lw=.55))
                    if number:
                        ax.text(si,hi,f'{number/n*100:.1f}%',ha='center',va='center',fontsize=7.4,color=lc)
            ax.set_xlim(-.5,3.5); ax.set_ylim(-.5,3.5)
            ticks=['2030','2035','2050','Not\nreached']
            ax.set_xticks(range(4),ticks); ax.set_yticks(range(4),ticks)
            ax.tick_params(length=0,pad=3,labelsize=7)
            for spine in ax.spines.values(): spine.set_visible(False)
        else:
            ax=ax_mm(xx,23,41,48,f'B_{fuel}')
            colors=[BLUE,CELL_AMBER,'#C7CDD1']
            label_colors=['white','#442C0D',INK]
            for xi,year in enumerate(years[:3]):
                rows=status[status.fuel.eq(fuel)&status.scenario.eq(year)]
                vals=rows['percent'].to_list()
                lower=0.
                tiny_top=[]
                for v,color,lc in zip(vals,colors,label_colors):
                    ax.bar(xi,v,bottom=lower,width=.78,color=color,edgecolor='none',zorder=2)
                    if v>=8:
                        ax.text(xi,lower+v/2,f'{v:.1f}%',ha='center',va='center',fontsize=7.1,color=lc,zorder=3)
                    elif v>0 and lower<.01:
                        ax.text(xi,-6,f'{v:.1f}%',ha='center',va='center',fontsize=7.0,color=BLUE if color==BLUE else '#8A571D')
                    elif v>0:
                        tiny_top.append((v,'#8A571D' if color==CELL_AMBER else '#5F686E'))
                    lower+=v
                assert np.isclose(lower,100)
                for j,(v,lc) in enumerate(tiny_top):
                    ax.text(xi,106+j*11,f'{v:.1f}%',ha='center',va='center',fontsize=7.0,color=lc)
            ax.set_xlim(-.62,2.62); ax.set_ylim(-10,125)
            ax.set_xticks(range(3),[str(y) for y in years[:3]])
            ax.set_yticks([0,50,100])
            ax.tick_params(axis='x',length=0,pad=3,labelsize=7)
            ax.tick_params(axis='y',length=2,pad=3,labelsize=7)
            ax.spines['left'].set_bounds(0,100)
            ax.spines['bottom'].set_visible(False)
            ax.grid(False)
        facets.append(ax)
    if kind=='Matrix_Refined':
        text_mm(4.2,49.5,'First cost-competitive year, hourly',rotation=90,rotation_mode='anchor',ha='center',va='center',fontsize=8)
        text_mm(93.5,16.5,'First cost-competitive year, annual-average',ha='center',va='center',fontsize=8)
        legends=[(7,BLUE,'Same first year'),(63,CELL_AMBER,'Earlier or only under annual-average'),(122,'#C7CDD1','Neither by 2050')]
    else:
        text_mm(5,47,'Locations (%)',rotation=90,rotation_mode='anchor',ha='center',va='center',fontsize=8)
        text_mm(93.5,14,'Scenario',ha='center',va='center',fontsize=8)
        legends=[(7,BLUE,'Parity under both'),(63,CELL_AMBER,'Parity only under static'),(122,'#C7CDD1','No parity under either')]
    for xx,color,label in legends:
        fig.patches.append(Rectangle((xx/WIDTH_MM,6/HEIGHT_MM),3/WIDTH_MM,2.5/HEIGHT_MM,transform=fig.transFigure,facecolor=color,edgecolor='none'))
        text_mm(xx+4.2,7.25,label,fontsize=7,va='center')
    fig.canvas.draw()
    alignment=require_matplotlib_panel_alignment(fig,axes=[a,*facets],panel_ids=['A','B_ammonia','B_methanol','B_saf'],row_groups=[['B_ammonia','B_methanol','B_saf']],column_groups=[],tolerance_pt=1.5,gutter_tolerance_pt=1.5,require_panel_labels=False,strict=True,json_out=OUT/f'{base}.alignment.json',overlay_svg=OUT/f'{base}.alignment.svg')
    assert np.isclose(a.get_position().x0,facets[0].get_position().x0)
    assert np.isclose(a.get_position().x1,facets[-1].get_position().x1)
    assert labels[0].get_position()[0]==labels[1].get_position()[0]
    fig.savefig(OUT/f'{base}.pdf',metadata={'Title':'Figure 1. Cost-competitive classifications under annual-average and hourly assessments','Author':''})
    fig.savefig(OUT/f'{base}.svg')
    fig.savefig(OUT/f'{base}.png',dpi=300)
    fig.set_dpi(1000); fig.canvas.draw()
    rgb=np.ascontiguousarray(np.asarray(fig.canvas.buffer_rgba())[:,:,:3])
    writer=getattr(tifffile.TiffWriter,'write',None) or tifffile.TiffWriter.save
    key='compression' if 'compression' in inspect.signature(writer).parameters else 'compress'
    tifffile.imwrite(OUT/f'{base}.tiff',rgb,photometric='rgb',resolution=(1000,1000),metadata=None,**{key:'deflate' if key=='compression' else 6})
    plt.close(fig)
    return {'variant':kind,'alignment':alignment.get('verdict'),'size_mm':[WIDTH_MM,HEIGHT_MM]}

outputs=[build('Matrix_Refined')]
meta={'outputs':outputs,'A_locations':len(points),'A_counts':counts,'A_unrounded_percent':shares,'B_common_cohort_counts':dict(zip(fuels,expected_n)),'percentage_precision':1,'percentages_computed_before_rounding':True,'same_methanol_sample_in_A_and_B':True,'annual_interpolation':False,'costs_changed':False,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'source_data').glob('*.csv')}}
(OUT/'data_checks.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print(json.dumps(meta,indent=2))
