from pathlib import Path
import json,hashlib,zipfile,sys,shutil
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
R=Path(__file__).parent;O=R.parent;A=O/"10_revision_analysis"
INPUT=R/"corrected_static";INPUT.mkdir(exist_ok=True)
USED=Path(r"D:\OneDrive\POTSED\DataOutput\Used_output")
# Archive current deliverables and source tables before the authorized correction.
backup=R/"before_correction.zip"
roots=[O/"01_main_manuscript",O/"03_supplementary_materials",
O/"02_main_figures/Fig1_Parity_Diagnostic_20260914",
O/"02_main_figures/Fig4_Bubble_Matrix_Compact_20260915",
O/"02_main_figures/Fig5_Original_Layout_Refined_20260915",
O/"02_main_figures/Fig6_Configuration_Operation_Cost_20260915",
A/"reports/parity_screening",A/"scripts",A/"figures/reconciled_atlas",
O/"04_cover_letter_and_metadata",O/"08_ready_to_upload/Author_Review_20260914"]
if not backup.exists():
    with zipfile.ZipFile(backup,"w",zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        for base in roots:
            for p in base.rglob("*"):
                if p.is_file() and p.suffix.lower() in (".tex",".bib",".pdf",".py",".csv",".gz",".json",".md",".txt") and not any(t in p.parts for t in ("__pycache__","previous_text_storage","integration_backup")):
                    z.write(p,p.relative_to(O))
        for name in ["calculate_static_downstream_from_h2.py"]:
            p=A/"src/h2data"/name;z.write(p,p.relative_to(O))
        for p in (O/"02_main_figures").glob("*.pdf"):z.write(p,p.relative_to(O))
        p=O/"02_main_figures/CURRENT_FIGURE_REVIEW.md";z.write(p,p.relative_to(O))
contract="""# CO2 storage-compression correction

User authorized correction of the model-boundary mismatch and all affected figures and numerical text.
The independent CO2 compressor in the archived hourly model and the controlled annual relaxation acts on stored_CO2 only. The conventional static model has no CO2 storage but incorrectly charged this component on all CO2 throughput. The cited methanol-system source (Fasihi and Breyer 2024, section 2.1) explicitly includes fresh/recycle gas compression within the methanol synthesis package and treats storage conditioning separately.

Chosen correction: preserve the common aggregate synthesis block and the storage-branch compressor definition; remove the dedicated storage-compressor capital and electricity charge from the no-storage static baseline for methanol and SAF in 2030/2035/2050. Record this as the stated aggregate boundary for SAF, not evidence of a pressure-resolved SAF validation. All other parameters, including the prior 2035 SAF reconciliation, remain fixed.

Exact static correction per tonne: old cost - compressor annual cost/output - compression electricity*selected LCOE/output. Recompute all annual totals and derived DAC costs. Recompute paired node gaps, regional medians, supply rankings, cutoff classifications, first observed scenarios, sensitivity gaps, and Fig6 accounting. Do not shift total costs without recomputing their component/energy fields.

Affected current figures: Fig1, Fig4, Fig5, Fig6, S4, S7, S9, S13 and S14. Hydrogen/ammonia-only graphics and controlled H/Y decisions retain their data. Keep figure designs and the approved storage bars. Synchronize main manuscript, supplementary equations/tables, legends and review PDFs. Preserve before/after data with hashes.

Additional Fig6 consistency repair: use the already saved H0 solutions and global parameter binding, whose battery-charge regularizer is 0.002 rather than the plotting cache's 0.00001. This restores the three reference costs and prevents mixing a changed objective with the atlas. No new global optimization is needed for the storage-free static correction.

Validation: component and energy closure, matched-cohort preservation, classification identities, shared-input hashes, appropriate figure export checks, and manuscript/SI compilation. No unrelated model redesign or statistical tests.
"""
(R/"CORRECTION_PLAN.md").write_text(contract,encoding="utf-8")
manifest={};reports=[]
for product,sub,costcol,masscol in [("methanol","methanol","levelized_methanol_cost_per_ton","total_methanol_production_kg"),("saf","ftl","levelized_FTL_cost_per_ton","total_FTL_production_kg")]:
    for year,tag in [(2030,"RegionRE_2030"),(2035,"RegionRE_LowAE"),(2050,"RegionRE_LowAE_2050")]:
        src=(A/"inputs/reconciled_static/saf_2035_static_matched_parameters.csv" if product=="saf" and year==2035 else USED/f"Output_combined_static_downstream/{sub}/combined_{tag}_StaticLCOE_AE_fixed_caps_{sub}_static_results_h2electrolyzer4000h_downstreamcf0.8.csv")
        df=pd.read_csv(src,low_memory=False);valid=(df[costcol]>0)&(df[masscol]>0)
        old=df.loc[valid,costcol].copy();q=df.loc[valid,masscol]
        components=[c for c in df if c.startswith("static_") and c.endswith("_cost_component")]
        assert np.allclose(df.loc[valid,components].sum(axis=1)/q*1000,old,rtol=1e-8)
        comp=df.loc[valid,"static_co2_compressor_cost_component"].copy()
        elec=df.loc[valid,"co2_compression_electricity_consumption_kwh"].copy()
        lcoe=df.loc[valid,"levelized_elec_cost_per_kWh"]
        removed_e=elec*lcoe
        df.loc[valid,"static_electricity_cost_component"]-=removed_e
        df.loc[valid,"total_direct_electricity_consumption_kwh"]-=elec
        df.loc[valid,"static_co2_compressor_cost_component"]=0.
        df.loc[valid,"co2_compression_electricity_consumption_kwh"]=0.
        df.loc[valid,"co2_compressor_capacity_kgCO2_per_h"]=0.
        df.loc[valid,"levelized_dac_cost_per_tCO2"]-=comp/df.loc[valid,"total_CO2_captured_kg"]*1000
        df.loc[valid,"objective_value"]=df.loc[valid,components].sum(axis=1)
        df.loc[valid,costcol]=df.loc[valid,"objective_value"]/q*1000
        df.loc[valid,"correction_removed_compressor_usd_t"]=comp/q*1000
        df.loc[valid,"correction_removed_electricity_usd_t"]=removed_e/q*1000
        assert np.allclose(old-df.loc[valid,costcol],(comp+removed_e)/q*1000,atol=1e-8)
        assert (df.loc[valid,"co2_storage_capacity_kg"].abs()<1e-10).all()
        demandcols=["direct_electricity_consumption_kwh","dac_electricity_consumption_kwh","co2_compression_electricity_consumption_kwh","heat_pump_electricity_consumption_kwh"]
        assert np.allclose(df.loc[valid,demandcols].sum(axis=1),df.loc[valid,"total_direct_electricity_consumption_kwh"])
        dest=INPUT/f"{product}_{year}_static_storage_boundary.csv";df.to_csv(dest,index=False)
        report={"product":product,"year":year,"source":str(src),"source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),"corrected":str(dest),"corrected_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),"rows":len(df),"valid_rows":int(valid.sum()),"capital_removed_usd_t":list(np.quantile(comp/q*1000,[0,.5,1])),"electricity_removed_usd_t":list(np.quantile(removed_e/q*1000,[0,.5,1])),"total_removed_usd_t":list(np.quantile(old-df.loc[valid,costcol],[0,.5,1]))}
        reports.append(report);manifest[f"{product}_{year}"]=str(dest)
        print(json.dumps(report),flush=True)
(R/"static_correction_report.json").write_text(json.dumps(reports,indent=2),encoding="utf-8")
(R/"corrected_static_paths.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
src=A/"src/h2data/calculate_static_downstream_from_h2.py"
code=src.read_text(encoding="utf-8-sig")
assert "compressor_capacity_kg_h = co2_required / 8760.0" in code
code=code.replace("compressor_capacity_kg_h = co2_required / 8760.0","# Dedicated CO2 compression serves storage in the hourly model; static has no storage.\n    compressor_capacity_kg_h = 0.0")
code=code.replace('compressor_elec_kwh = co2_required * params["co2_compression_energy"]','compressor_elec_kwh = 0.0')
src.write_text(code,encoding="utf-8")
print("STATIC_CORRECTION_READY",flush=True)

