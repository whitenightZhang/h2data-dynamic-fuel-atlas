from pathlib import Path
import importlib.util, json, hashlib, glob
import numpy as np
import pandas as pd
O=Path('D:\\OneDrive\\00PhD\\Chapter3_paper\\One_Earth_Submission_Package_20260913'); R=O/'10_revision_analysis'; OUT=Path(__file__).resolve().parent/'source_data'
OUT.mkdir(exist_ok=True)
keys=['latitude','longitude','region_match','region_name']; cache=OUT/'matched_node_costs.csv'
if cache.exists(): nodes=pd.read_csv(cache)
else:
 spec=importlib.util.spec_from_file_location('atlas',R/'scripts/plot_atlas_potential_reconciled.py')
 atlas=importlib.util.module_from_spec(spec); spec.loader.exec_module(atlas)
 blocks=[]; sources=[]; results=atlas.load_all_results(); assert len(results)==9
 for (fuel,year),data in results.items():
  d=data['matched'].copy(); assert not d.duplicated(keys).any(),(fuel,year)
  factor=1000 if atlas.cost_limit_for_data(fuel,year,data['cost_col'])<10 else 1
  d['static_usd_t']=d.static_cost*factor; d['hourly_usd_t']=d.dynamic_cost*factor
  d['fuel']=fuel; d['year']=int(year); d['threshold_usd_t']=atlas.REFERENCE_COST_LIMITS_USD_PER_TON[fuel]
  blocks.append(d[keys+['fuel','year','static_usd_t','hourly_usd_t','potential_Mt','threshold_usd_t']])
  for p in [atlas.static_file_for(fuel,year),atlas.find_dynamic_file(fuel,year,sorted(glob.glob(str(Path(atlas.DATA_OUTPUT_DIR)/'*_withPotential.csv'))))]:
   p=Path(p); sources.append(dict(fuel=fuel,year=year,path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 nodes=pd.concat(blocks,ignore_index=True); nodes.to_csv(cache,index=False)
 (OUT/'source_manifest.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')
def classify(g,multiplier=1.):
 b=g.threshold_usd_t*multiplier; s=g.static_usd_t<=b; h=g.hourly_usd_t<=b; fp=s&~h; fn=~s&h; w=g.potential_Mt
 margin=g.loc[fp,'hourly_usd_t']-b[fp]; sw=float(w[s].sum()); hw=float(w[h].sum()); fw=float(w[fp].sum()); nw=float(w[fn].sum())
 assert np.isclose(sw-hw,fw-nw,atol=1e-6)
 return dict(nodes=len(g),static_pass_nodes=int(s.sum()),hourly_pass_nodes=int(h.sum()),false_positive_nodes=int(fp.sum()),false_negative_nodes=int(fn.sum()),static_Mt=sw,hourly_Mt=hw,false_positive_Mt=fw,false_negative_Mt=nw,false_positive_share_static_percent=100*fw/sw if sw else None,hourly_excess_median_usd_t=float(margin.median()) if len(margin) else None,hourly_excess_p10_usd_t=float(margin.quantile(.1)) if len(margin) else None,hourly_excess_p90_usd_t=float(margin.quantile(.9)) if len(margin) else None)
summary=pd.DataFrame([dict(fuel=f,year=int(y),**classify(g)) for (f,y),g in nodes.groupby(['fuel','year'])]); summary.to_csv(OUT/'global_classification.csv',index=False)
regional=pd.DataFrame([dict(fuel=f,year=int(y),region_name=r,**classify(g)) for (f,y,r),g in nodes.groupby(['fuel','year','region_name'])]); regional.to_csv(OUT/'regional_classification.csv',index=False)
sens=pd.DataFrame([dict(fuel=f,year=int(y),threshold_multiplier=m,**classify(g,m)) for (f,y),g in nodes.groupby(['fuel','year']) for m in [.8,.9,1.,1.1,1.2]]); sens.to_csv(OUT/'threshold_sensitivity.csv',index=False)
# Fixed coordinates and region across years; 9999 denotes no observed crossing by 2050.
cross=[]; checks=[]
for fuel,g in nodes.groupby('fuel'):
 w=g.pivot(index=keys,columns='year',values=['static_usd_t','hourly_usd_t']).dropna(); threshold=float(g.threshold_usd_t.iloc[0]); row=w.index.to_frame(index=False); row['fuel']=fuel
 for method,col in [('static','static_usd_t'),('hourly','hourly_usd_t')]:
  cost=w[col][[2030,2035,2050]].to_numpy(); passed=cost<=threshold
  row[method+'_first_observed_year']=np.where(passed[:,0],2030,np.where(passed[:,1],2035,np.where(passed[:,2],2050,9999)))
  row[method+'_observed_reversal']=np.any(np.diff(passed.astype(int),axis=1)<0,axis=1)
  for j,yr in enumerate([2030,2035,2050]): row[f'{method}_{yr}_usd_t']=cost[:,j]
 row['static_earlier_observed']=row.static_first_observed_year<row.hourly_first_observed_year; cross.append(row)
 checks.append(dict(fuel=fuel,common_nodes=len(row),per_year_nodes={str(int(y)):len(gy) for y,gy in g.groupby('year')},static_earlier_nodes=int(row.static_earlier_observed.sum()),static_reversals=int(row.static_observed_reversal.sum()),hourly_reversals=int(row.hourly_observed_reversal.sum())))
cross=pd.concat(cross,ignore_index=True); cross.to_csv(OUT/'common_node_first_observed_year.csv',index=False)
cross.groupby(['fuel','static_first_observed_year','hourly_first_observed_year']).size().reset_index(name='nodes').to_csv(OUT/'crossing_matrix.csv',index=False)
cross.groupby(['fuel','region_name']).agg(common_nodes=('static_earlier_observed','size'),static_earlier_nodes=('static_earlier_observed','sum')).reset_index().to_csv(OUT/'regional_first_observed.csv',index=False)
(OUT/'matching_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(summary.to_string(index=False)); print(json.dumps(checks,indent=2)); print(cross.groupby(['fuel','static_first_observed_year','hourly_first_observed_year']).size().to_string())
ind=pd.read_csv(R/'reports/independent36_node_results.csv'); print('INDEPENDENT COLUMNS',list(ind.columns))
print(regional[(regional.year==2035)&(regional.fuel=='methanol')].sort_values('false_positive_Mt',ascending=False).head(5).to_string(index=False))

