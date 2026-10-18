from pathlib import Path
import pandas as pd,numpy as np,json,sys,re,subprocess,hashlib
sys.stdout.reconfigure(encoding='utf-8')
O=Path(r'D:\OneDrive\00PhD\Chapter3_paper\One_Earth_Submission_Package_20260913');R=O/'11_co2_boundary_correction_20260915';A=O/'10_revision_analysis'
paths=json.loads((R/'corrected_static_paths.json').read_text()); lookup={}
for tag,p in paths.items():
 f,y=tag.split('_'); cc='levelized_methanol_cost_per_ton' if f=='methanol' else 'levelized_FTL_cost_per_ton'
 d=pd.read_csv(p,usecols=['latitude','longitude',cc]);d=d[d[cc].gt(0)];assert not d.duplicated(['latitude','longitude']).any()
 lookup[f,int(y)]=d.set_index(['latitude','longitude'])[cc]
def fix(d,cost,fcol='fuel'):
 for (f,y),idx in d.groupby([fcol,'year']).groups.items():
  f={'Methanol':'methanol','FTL':'saf','ftl':'saf','Ammonia':'ammonia'}.get(f,f)
  if (f,int(y)) not in lookup:continue
  vals=lookup[f,int(y)].reindex(pd.MultiIndex.from_frame(d.loc[idx,['latitude','longitude']])).to_numpy();assert np.isfinite(vals).all();d.loc[idx,cost]=vals
 return d
# Route every active provider to the correction, preserving other datasets.
for filename,signature,expr,ret in [
 ('plot_atlas_potential_reconciled.py','def static_file_for(fuel_type, year):','fuel_type','str(p)'),
 ('plot_archetypes_reconciled.py','def static_file_for(fuel_type: str, year: str) -> Path | None:','fuel_type','p'),
 ('plot_saf_sensitivity_reconciled.py','def static_file_for_product(product: str, year: str = YEAR_TAG) -> Path | None:',"{'ftl':'saf'}.get(product,product)",'p')]:
 p=A/'scripts'/filename;t=p.read_text(encoding='utf-8-sig');new=signature+f"\n    from pathlib import Path\n    f = {expr}\n    p = Path(__file__).resolve().parents[2] / '11_co2_boundary_correction_20260915' / 'corrected_static' / f'{{f}}_{{year}}_static_storage_boundary.csv'\n    if p.exists(): return {ret}"
 assert signature in t;t=t.replace(signature,new,1);p.write_text(t,encoding='utf-8')
p=A/'scripts/plot_atlas_costs_reconciled.py';t=p.read_text(encoding='utf-8-sig');lines=t.splitlines();res=[]
for l in lines:
 res.append(l)
 if "if prod_name=='FTL' and year_str=='2035': static_path=" in l:
  res+= ["    from pathlib import Path", "    corrected = Path(__file__).resolve().parents[2] / '11_co2_boundary_correction_20260915/corrected_static' / f\"{{'Methanol':'methanol','FTL':'saf'}.get(prod_name,prod_name)}_{year_str}_static_storage_boundary.csv\"", "    if corrected.exists(): static_path = str(corrected)"]
p.write_text('\n'.join(res)+'\n',encoding='utf-8')
# Primary paired cohorts retain their membership and weights.
p=A/'reports/parity_screening/matched_node_costs.csv';old=pd.read_csv(p);d=fix(old.copy(),'static_usd_t');assert np.array_equal(old.hourly_usd_t,d.hourly_usd_t);d.to_csv(p,index=False)
subprocess.run([sys.executable,str(A/'scripts/evaluate_parity_screening.py')],check=True,stdout=(R/'parity_recalculation.log').open('w',encoding='utf-8'))
manifest=json.loads((A/'reports/parity_screening/source_manifest.json').read_text())
for x in manifest:
 tag=f"{x['fuel']}_{x['year']}"
 if tag in paths and 'static' in x['path'].lower():
  p=Path(paths[tag]);x.update(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(A/'reports/parity_screening/source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
# Fig 1.
f1=O/'02_main_figures/Fig1_Parity_Diagnostic_20260914';d[(d.fuel=='methanol')&(d.year==2035)].to_csv(f1/'source_data/B_methanol_2035_all_paired_locations.csv',index=False)
cross=pd.read_csv(A/'reports/parity_screening/common_node_first_observed_year.csv');cross.to_csv(f1/'source_data/C_common_locations_all_fuels.csv',index=False)
p=f1/'plot_fig1.py';t=p.read_text(encoding='utf-8-sig');t=re.sub(r'assert counts == \{[^\n]+\}',"assert sum(counts.values()) == len(b)  # Recomputed paired cohort",t) if False else t
# Replace old result fixture with corrected exact classification.
b=d[(d.fuel=='methanol')&(d.year==2035)];s=b.static_usd_t.le(550);h=b.hourly_usd_t.le(550)
for before,after in [('373',str(int((s&h).sum()))),('4544',str(int((s&~h).sum()))),('2792',str(int((~s&~h).sum())) )]:
 t=re.sub(r'(?<="Both below":)\s*373', ' '+str(int((s&h).sum())),t) if before=='373' else t
# Scoped literal dictionary is inspected below if style differs.
t=t.replace('"Static only":4544','"Static only":'+str(int((s&~h).sum()))).replace('"Both above":2792','"Both above":'+str(int((~s&~h).sum())))
t=t.replace('"Static only": 4544','"Static only": '+str(int((s&~h).sum()))).replace('"Both above": 2792','"Both above": '+str(int((~s&~h).sum())))
p.write_text(t,encoding='utf-8')
# Fig4 and supplementary Fig S14.
for root in [O/'02_main_figures/Fig4_Bubble_Matrix_Compact_20260915',O/'03_supplementary_materials/Figures/FigS14_Regional_Cost_Bias_All_Years_20260915']:
 p=root/'source_data/matched_costs.csv.gz';m=fix(pd.read_csv(p),'static_cost','product');m['underestimation_pct']=(m.hourly_cost-m.static_cost)/m.hourly_cost*100;m.to_csv(p,index=False,compression='gzip')
 p=root/'source_data/regional_summary.csv';r=pd.read_csv(p);g=m.groupby(['year','product','region_name']).agg(hourly_median=('hourly_cost','median'),static_median=('static_cost','median'),underestimation_pct=('underestimation_pct','median'),nodes=('latitude','size'))
 for c in g.columns:r[c]=g[c].reindex(pd.MultiIndex.from_frame(r[['year','product','region_name']])).to_numpy()
 assert r.notna().all().all();r.to_csv(p,index=False)
# Fig5: preserve region metadata, replace all classification totals; rebuild costs/ranks with identical paired weights.
f5=O/'02_main_figures/Fig5_Original_Layout_Refined_20260915';p=f5/'source_data/region_potential.csv';q=pd.read_csv(p)
g=pd.read_csv(A/'reports/parity_screening/regional_classification.csv').set_index(['fuel','year','region_name']);ix=pd.MultiIndex.from_frame(q[['fuel','year','region_name']])
for out,src in [('dynamic_supply_Mt','hourly_Mt'),('static_supply_Mt','static_Mt'),('static_overestimate_Mt','false_positive_Mt'),('static_underestimate_Mt','false_negative_Mt')]:q[out]=g[src].reindex(ix).to_numpy()
q['static_minus_8760_Mt']=q.static_supply_Mt-q.dynamic_supply_Mt;assert q.notna().all().all();q.to_csv(p,index=False)
blocks=[]
for (f,y),z in d.groupby(['fuel','year']):
 for method,c in [('dynamic','hourly_usd_t'),('static','static_usd_t')]:
  z=z.sort_values(c,kind='stable');blocks.append(pd.DataFrame(dict(cost=z[c].to_numpy(),cumulative_Mt=z.potential_Mt.cumsum().to_numpy(),potential_Mt=z.potential_Mt.to_numpy(),fuel=f,year=y,method=method)))
pd.concat(blocks,ignore_index=True).to_csv(f5/'source_data/cost_ranked_curves.csv.gz',index=False,compression='gzip')
# S4 cached archetypes and statistics.
p=A/'figures/reconciled_atlas/Fig5/Figure5_downstream_archetype_node_data.csv';z=fix(pd.read_csv(p),'cost_static_usd_t');z['underestimation_pct']=(z.cost_8760_usd_t-z.cost_static_usd_t)/z.cost_8760_usd_t*100;z.to_csv(p,index=False)
rows=[]
for keys,v in z.groupby(['fuel','product','year','archetype']):
 for c in ['cost_8760_usd_t','underestimation_pct']:
  x=v[c];rows.append(dict(zip(['fuel','product','year','archetype'],keys),metric=c,n=len(x),q25=x.quantile(.25),median=x.median(),q75=x.quantile(.75),mean=x.mean(),min=x.min(),max=x.max()))
pd.DataFrame(rows).to_csv(p.with_name('Figure5_downstream_archetype_summary_stats.csv'),index=False)
print(pd.read_csv(A/'reports/parity_screening/global_classification.csv').to_string(index=False))
print('Affected source tables and active providers updated.')
