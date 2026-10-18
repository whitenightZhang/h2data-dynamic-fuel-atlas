"""Correct the static SAF 2035 cost version, preserving source files and coordinates."""
from pathlib import Path
import ast,json,hashlib,numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1]
SRC=Path(r"D:\OneDrive\POTSED\DataOutput\Used_output")
static=SRC/'Output_combined_static_downstream/ftl/combined_RegionRE_LowAE_StaticLCOE_AE_fixed_caps_ftl_static_results_h2electrolyzer4000h_downstreamcf0.8.csv'
dynamic=SRC/'combined_RegionRE_LowAE_MidFTL_ftl_results.csv'
notebook=Path(r"D:\OneDrive\POTSED\3.3 FlexUnCentainty.ipynb")
param=None
for c in json.loads(notebook.read_text(encoding='utf-8'))['cells']:
 try:tree=ast.parse(''.join(c.get('source',[])))
 except SyntaxError:continue
 for n in ast.walk(tree):
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='params_base' for t in n.targets):
   try:v=ast.literal_eval(n.value)
   except Exception:continue
   if v.get('ftl_synthesis_cost')==15400:param=v
assert param is not None and param['sorbent_cost']==.012
out=ROOT/'inputs/reconciled_static';out.mkdir(exist_ok=True)
(out/'ftl_2035_notebook_parameter_binding.json').write_text(json.dumps({'path':str(notebook),'sha256':hashlib.sha256(notebook.read_bytes()).hexdigest(),'parameters':param},indent=2))
def af(life,om=.03):return .07/(1-1.07**(-life))+om
# Reconstruct all capital and sorbent terms from stored hourly capacities. Flow penalties remain as a residual.
terms={
 'wind_capacity_kW':(None,30,.03,'wind_cost'), 'pv_capacity_kW':(None,40,.03,'pv_cost'),
 'battery_energy_capacity_kW':(100,20,.03,None),'battery_storage_capacity_kWh':(100,20,.03,None),
 'electrolyzer_capacity_AE_kW':(250,25,.03,None),'electrolyzer_capacity_PEM_kW':(500,25,.03,None),
 'heat_pump_capacity_kW_th':(950,20,.03,None),'thermal_storage_capacity_kWh_th':(30,30,.03,None),
 'hydrogen_storage_capacity_kgH2':(500,30,.03,None),'FTL_storage_capacity_kg_per_h':(.056,30,.03,None),
 'dac_capacity_kgCO2_per_h':(4000,30,.03,None),'co2_compressor_capacity_kgCO2_per_h':(365,20,.03,None),'co2_storage_capacity_kg':(24,30,.03,None)}
residuals=[];alternative=[];valid_count=0
for df in pd.read_csv(dynamic,chunksize=50000):
 df=df.loc[(df.objective_value>0)&(df.total_FTL_production_kg>0)].copy()
 if df.empty:continue
 capital=np.zeros(len(df))
 for col,(cost,life,om,costcol) in terms.items():capital+=df[col].to_numpy()*(df[costcol].to_numpy() if costcol else cost)*af(life,om)
 syn=df.FTL_synthesis_capacity_tpy.to_numpy()*1000/8760*af(25,.06)
 financial=capital+syn*15400+df.total_CO2_captured_kg.to_numpy()*.012
 residuals.extend(((df.objective_value.to_numpy()-financial)/df.objective_value.to_numpy()).tolist())
 alternative.extend(((df.objective_value.to_numpy()-(capital+syn*9400+df.total_CO2_captured_kg.to_numpy()*.001))/df.objective_value.to_numpy()).tolist())
 valid_count+=len(df)
residuals=np.array(residuals);alternative=np.array(alternative)
assert np.min(residuals)>-1e-5, np.min(residuals)
# The stored objective also includes flow regularizers; aggregated output cannot reconstruct them exactly.
assert np.max(np.abs(residuals)) < np.min(alternative), 'Parameter alternatives are not separated by the cost reconstruction'
corrected=out/'saf_2035_static_matched_parameters.csv'
counts={'total_source_rows':0,'valid_corrected_rows':0};diffs=[];stale_objective_diffs=[];first=True
for df in pd.read_csv(static,chunksize=50000,low_memory=False):
 counts['total_source_rows']+=len(df)
 df=df.loc[(df.levelized_FTL_cost_per_ton>0)&(df.total_FTL_production_kg>0)].copy()
 if df.empty:continue
 q=df.total_FTL_production_kg
 assert np.allclose(df.FTL_utilization_percent,80,atol=1e-7)
 assert np.allclose(df.dac_utilization_percent,80,atol=1e-7)
 assert np.allclose(df.static_synthesis_cost_component,q/(8760*.8)*9400*af(25,.06),rtol=1e-8)
 assert np.allclose(df.static_sorbent_cost_component,df.total_CO2_captured_kg*.001,rtol=1e-8)
 old=df.levelized_FTL_cost_per_ton.copy()
 component_cols=[c for c in df if c.startswith('static_') and c.endswith('_cost_component')]
 old_total=df[component_cols].sum(axis=1)
 assert np.allclose(old_total/q*1000,old,rtol=1e-8)
 stale_objective_diffs.extend(((old_total-df.objective_value)/q*1000).tolist())
 new_synth=df.static_synthesis_cost_component*(15400/9400)
 new_sorbent=df.total_CO2_captured_kg*.012
 delta=(new_synth-df.static_synthesis_cost_component)+(new_sorbent-df.static_sorbent_cost_component)
 df['static_synthesis_cost_component']=new_synth;df['static_sorbent_cost_component']=new_sorbent
 df['objective_value']=old_total+delta
 df['levelized_FTL_cost_per_ton']=df.objective_value/q*1000
 # Source DAC-levelized cost includes only DAC capital and compressor; sorbent correction does not alter that field.
 component_cols=[c for c in df if c.startswith('static_') and c.endswith('_cost_component')]
 assert np.allclose(df[component_cols].sum(axis=1),df.objective_value,rtol=1e-8)
 diffs.extend((df.levelized_FTL_cost_per_ton-old).tolist());counts['valid_corrected_rows']+=len(df)
 df.to_csv(corrected,index=False,mode='w' if first else 'a',header=first);first=False
report={'source_static':str(static),'source_static_sha256':hashlib.sha256(static.read_bytes()).hexdigest(),'source_hourly':str(dynamic),'source_hourly_sha256':hashlib.sha256(dynamic.read_bytes()).hexdigest(),'source_hourly_valid_rows':valid_count,'hourly_binding_limit':'Corroboration from manuscript and source notebook plus stored capacity reconstruction, not exact batch replication. The original 2035 batch file is a one-byte placeholder. Flow regularizers are not separately stored in the aggregated CSV.','hourly_financial_reconstruction_relative_residual_quantiles':dict(zip(['min','median','max'],np.quantile(residuals,[0,.5,1]))),'alternative_9400_0001_relative_residual_quantiles':dict(zip(['min','median','max'],np.quantile(alternative,[0,.5,1]))),'old_synthesis_capex_usd_per_kg_h':9400,'matched_synthesis_capex_usd_per_kg_h':15400,'old_sorbent_usd_per_kg_co2':.001,'matched_sorbent_usd_per_kg_co2':.012,'downstream_utilization_fraction':.8,'electrolyzer_full_load_hours':4000,'delta_usd_per_t_quantiles':dict(zip(['min','median','max'],np.quantile(diffs,[0,.5,1]))),'original_objective_shortfall_usd_per_t_quantiles':dict(zip(['min','median','max'],np.quantile(stale_objective_diffs,[0,.5,1]))),'corrected_path':str(corrected),'corrected_sha256':hashlib.sha256(corrected.read_bytes()).hexdigest(),'scope':'Only positive-cost positive-output static rows retained. No upstream files or hourly results changed. Parameter consistency does not make conventional static S a pure chronology ablation.',**counts}
(ROOT/'reports/static_saf2035_reconciliation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
