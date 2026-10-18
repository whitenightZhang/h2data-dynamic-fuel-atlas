"""Exact unit normalization for a homogeneous continuous production LP."""
import math
REGULARIZERS=('surplus_penalty','battery_charge_penalty','battery_discharge_penalty','hydrogen_charge_penalty','methanol_charge_penalty')
def financial_case(source_params,node,target_t_per_year,reference_kg=10000.):
    if not math.isfinite(target_t_per_year) or target_t_per_year<=0:raise ValueError('Positive finite output required')
    scale=target_t_per_year*1000/reference_kg
    p=dict(source_params);p['target_methanol_production']=reference_kg
    p.update({k:0. for k in REGULARIZERS});p.update(wind_cost=node['wind_cost'],pv_cost=node['pv_cost'])
    n=dict(node)
    for key in ['wind_cap_kw','pv_cap_kw']:n[key]=node[key]/scale
    return p,n,scale
