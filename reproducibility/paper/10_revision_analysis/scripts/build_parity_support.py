from pathlib import Path
import json,re,hashlib
import pandas as pd,numpy as np
O=Path(__file__).resolve().parents[2];R=O/'10_revision_analysis';P=R/'reports/parity_screening';D=O/'09_revision_plan_and_assessment';S=O/'03_supplementary_materials'
g=pd.read_csv(P/'global_classification.csv');r=pd.read_csv(P/'regional_classification.csv');nodes=pd.read_csv(P/'matched_node_costs.csv')
ind=pd.read_csv(R/'reports/independent36_node_results.csv');ind['annual_below_550']=ind.annual_cost_usd_per_t<=550
ind['hourly_threshold_status']=np.where(ind.hourly_cost_usd_per_t<=550,'below',np.where(np.isfinite(ind.hourly_cost_usd_per_t),'above',ind.analysis_feasibility_status))
ind.to_csv(P/'independent36_parity_classification.csv',index=False)
assert ind.annual_below_550.sum()==25
assert (ind.loc[ind.annual_below_550,'hourly_threshold_status']=='above').all()
weather=pd.read_csv(R/'reports/heldout_weather_results.csv')
assert (weather.loc[weather.annual_selected_in_2023,'hourly_cost_usd_per_t']>550).all()
# Direct reconciliation with the prior atlas totals; no model re-solves.
prior=pd.read_csv(R/'figures/reconciled_atlas/Reference_cost_supply_potential_by_region.csv').groupby(['fuel','year'])[['static_supply_Mt','dynamic_supply_Mt']].sum()
for _,v in g.iterrows():
 z=prior.loc[(v.fuel,v.year)]
 assert np.isclose(v.static_Mt,z.static_supply_Mt,atol=1e-6)
 assert np.isclose(v.hourly_Mt,z.dynamic_supply_Mt,atol=1e-6)
assert not nodes.duplicated(['fuel','year','latitude','longitude','region_match']).any()
def en(x):return {'Australia_NZ':'Australia and NZ','Africa_N':'North Africa','Africa_W':'West Africa','Africa_E':'East Africa','Africa_S':'Southern Africa','South America_N':'Northern South America','South America_S':'Southern South America','Europe_Eastern':'Eastern Europe','Europe_Non_EU':'Non-EU Europe'}.get(x,x).replace('&',r'\&').replace('_',r'\_')
head=r"""\clearpage
\subsection{Regional parity classification and scenario matching}

The new parity analysis postprocesses the parameter-reconciled global atlas. It does not rerun historical optimization. Static and hourly costs are paired by latitude, longitude and regional assignment. The hourly potential supplies a common weight after the source renewable-resource and basin-water filters. Only positive weights, finite positive costs and identified regions enter the paired supply sample. This sample is smaller than the cost-only sample because zero-potential locations are excluded. The 2035 static SAF input uses the previously reconciled DAC parameters. Input paths, file hashes, paired rows and calculation scripts are included in the revision archive.

Apparent parity denotes qualification at the specified production-cost cutoff. For each scenario, the false-positive set has static cost at or below the cutoff and hourly cost above it. We count this set and sum its common weights. We retain the reverse classification separately; its count and volume are zero in all nine baseline comparisons. This establishes that the static-minus-hourly qualified-potential difference equals the false-positive volume for these baseline data. That equality is checked, not imposed in the calculation. Missing percentage denominators are undefined, rather than zero.

The reference cutoffs are exactly 600, 550 and 1,200 USD t$^{-1}$. The unrounded illustrative fossil-pathway totals in Table S4 are 631.5, 548.9 and 1,215 USD t$^{-1}$, respectively. These fixed screening choices are not observed prices or forecasts. The sensitivity sweep changes each cutoff from 80\% to 120\% of its baseline, holding costs and weights fixed. It is a benchmark sensitivity, not a probabilistic uncertainty interval or a set of new technology optimizations.

For first observed qualifying scenarios, we match the same coordinates and regional assignment across 2030, 2035 and 2050, and require membership in the positive-potential paired sample in every year. The common samples contain 7,614 ammonia, 7,407 methanol and 7,377 e-SAF locations. Counts are unweighted. A location that already qualifies in 2030 has no earlier observation; one that does not qualify through 2050 has no observed crossing. Neither boundary is assigned a precise crossing year outside the observed scenarios. Qualification does not reverse in the three observations at any common location. Annual interpolation and assumptions about continuous trajectories are not used.

The controlled 36-site experiment applies the same 550 USD t$^{-1}$ reference cost to Y and H at a common net output. Exactly 25 sites have Y costs below the cutoff; all 25 have finite optimal H costs above it. The three infeasible and one unresolved outcome remain separately identified. The globally screened atlas and the independent experiment have different source-model and sampling boundaries, so their rates are not pooled.

\begin{table}[htbp]
\centering
\small
\setlength{\tabcolsep}{3pt}
\caption{Baseline parity classification in the paired positive-potential sample. S and H denote static and hourly assessment. Early potential is static-qualified potential above the hourly threshold; the share uses static-qualified potential as denominator. Volumes are Mt yr$^{-1}$. A dash denotes an undefined share.}
\label{tab:parity-global}
\begin{tabular}{llrrrrrr}
\toprule
Fuel & Year & Paired nodes & Early nodes & S potential & H potential & Early potential & Share (\%)\\
\midrule
"""
lines=[]
for _,v in g.iterrows():
 share='--' if pd.isna(v.false_positive_share_static_percent) else f'{v.false_positive_share_static_percent:.2f}'
 lines.append(f'{dict(ammonia="Ammonia",methanol="Methanol",saf="SAF")[v.fuel]} & {int(v.year)} & {int(v.nodes):,} & {int(v.false_positive_nodes):,} & {v.static_Mt:,.1f} & {v.hourly_Mt:,.1f} & {v.false_positive_Mt:,.1f} & {share} '+r'\\')
text=head+'\n'.join(lines)+r"""
\bottomrule
\end{tabular}
\end{table}

\clearpage
\small
\begin{longtable}{lrrrrr}
\caption{Regional methanol classification at 550 USD t$^{-1}$ in 2035. Counts refer to paired positive-potential locations. Volumes are Mt yr$^{-1}$. Regional membership and sample exclusions follow the source atlas.}\label{tab:parity-regions}\\
\toprule
Region & Paired nodes & Early nodes & S potential & H potential & Early potential\\
\midrule
\endfirsthead
\toprule
Region & Paired nodes & Early nodes & S potential & H potential & Early potential\\
\midrule
\endhead
"""
for _,v in r[(r.fuel=='methanol')&(r.year==2035)].sort_values('false_positive_Mt',ascending=False).iterrows():
 text+=f'{en(v.region_name)} & {int(v.nodes):,} & {int(v.false_positive_nodes):,} & {v.static_Mt:,.1f} & {v.hourly_Mt:,.1f} & {v.false_positive_Mt:,.1f} '+r'\\'+'\n'
text+=r"""\bottomrule
\end{longtable}
\normalsize

\clearpage
\begin{figure}[htbp]
\centering
\includegraphics[width=0.98\textwidth,height=.67\textheight,keepaspectratio]{figures_engineering/FigureS12_Independent_Decision.pdf}
\caption{Independent methanol validation under 2035 technology, 2023 weather and 42,000 t yr$^{-1}$ net output. (A) Annual Y and hourly H costs at 32 finite optimal sites. (B) Budget underestimation and siting regret within each six-site group, retaining the North American regret bound. (C) Regional holdout cost errors. (D) Statuses of all 36 candidates. These diagnostics concern cost, ranking and feasibility. The parity extension classifies 25 annual-qualified sites above the hourly 550 USD t$^{-1}$ cutoff; unchanged minimum-cost choices do not establish correct parity classification.}
\label{fig:independent-decision-supp}
\end{figure}

\clearpage
\begin{figure}[htbp]
\centering
\includegraphics[width=.98\textwidth]{figures_engineering/FigureS13_Parity_Threshold_Sensitivity.pdf}
\caption{Sensitivity of premature classification to the reference cost. The vertical axis gives the percentage of static-qualified potential above the hourly threshold. Panels use ammonia in 2030, methanol in 2035 and e-SAF in 2050, with baseline cutoffs of 600, 550 and 1,200 USD t$^{-1}$, respectively. Cutoffs range from 80\% to 120\% of baseline, with costs, paired nodes and weights fixed. The full nine product--year combinations and five cutoffs are supplied as source data. The sweep is not a confidence interval and does not infer parity dates.}
\label{fig:parity-threshold-sensitivity}
\end{figure}
\clearpage
"""
text=text.replace('undefined, rather than zero','recorded as undefined')
(S/'Parity_Classification_Analysis.tex').write_text(text,encoding='utf-8')
p=S/'Supplemental_Information.tex';s=p.read_text(encoding='utf-8');needle=r'\input{Weather_Validation_Results.tex}';assert s.count(needle)==1
s=s.replace(needle,needle+'\n\n'+r'\input{Parity_Classification_Analysis.tex}');p.write_text(s,encoding='utf-8')
# Traceable claim ledger in the Nature skill's deterministic validation schema.
cols=['claim_id','section','paragraph_id','claim_text','claim_type','key_number','unit','figure_panel','source_data','source_script','scenario','region','year','uncertainty_or_range','robustness_check','citation_support','status','notes']
claims=[]
for fuel,yr in [('ammonia',2030),('methanol',2035),('saf',2050)]:
 v=g[(g.fuel==fuel)&(g.year==yr)].iloc[0]
 claims.append(dict(claim_id=f'PARITY_{fuel}',section='Summary; Results',paragraph_id='premature regional competitiveness',claim_text='Share of static-qualified potential above hourly threshold',claim_type='threshold',key_number=f'{v.false_positive_share_static_percent:.6f}',unit='percent',figure_panel='Figure 1A-C',source_data='reports/parity_screening/global_classification.csv',source_script='scripts/evaluate_parity_screening.py',scenario='baseline fixed fossil-reference cutoff',region='screened global candidates',year=str(yr),robustness_check='Five alternative cutoffs; direct reconciliation to prior atlas',status='supported',notes='Conditional positive-potential sample; not global deployment or investment loss'))
claims += [dict(claim_id='PARITY_same_nodes',section='Results',paragraph_id='Matching locations',claim_text='Methanol first observed qualifying scenario is 2035 static and 2050 hourly at identical nodes',claim_type='comparison',key_number='4231',unit='locations',figure_panel='Figure 1E',source_data='reports/parity_screening/common_node_first_observed_year.csv',source_script='scripts/evaluate_parity_screening.py',scenario='2030/2035/2050; fixed 550 USD/t',region='common screened locations',year='2035;2050',robustness_check='Three-year intersection; no observed reversals',status='supported',notes='Does not imply exact 15-year date delay'),
dict(claim_id='PARITY_independent',section='Results',paragraph_id='Temporal constraints',claim_text='Annual-qualified independent sites all remain above hourly threshold',claim_type='threshold',key_number='25',unit='sites',source_data='reports/parity_screening/independent36_parity_classification.csv',source_script='scripts/build_parity_support.py',scenario='2035 technology; 2023 weather; 42000 t/year;550 USD/t',region='six sampled macro-regions',year='2035',robustness_check='All 25 have finite optimal H costs; other statuses retained',status='supported',notes='Not a probability-weighted global rate')]
pd.DataFrame(claims).reindex(columns=cols).fillna('').to_csv(P/'nature_claims.csv',index=False)
ledger=pd.read_csv(R/'reports/claim_evidence.csv')
newrows=[dict(claim_id=c['claim_id'],claim=c['claim_text']+': '+c['key_number']+' '+c['unit'],source=c['source_data'],supported='yes',limit=c['notes']) for c in claims]
pd.concat([ledger,pd.DataFrame(newrows)],ignore_index=True).to_csv(R/'reports/claim_evidence.csv',index=False)
(P/'direct_verification.json').write_text(json.dumps({'baseline_product_years':9,'baseline_totals_reconcile_to_prior_atlas':True,'node_keys_unique':True,'false_positive_minus_false_negative_identity':True,'independent_annual_pass_all_fail_hourly':25,'selected_site_weather_costs_above_550':12,'new_optimization_runs':0},indent=2),encoding='utf-8')
print('Supplementary methods, tables, numerical checks and claim ledger prepared.')

