"""H: legacy hourly physics with explicit net delivery and source-bound resource caps.
All storage starts empty and may end nonempty. No free initial inventory.
The difference from H0 is documented by the removed and added row names.
"""
import gurobipy as gp

def adapt_hourly(b,node):
    m=b['model'];T=b['time_steps'];Q=b['target_methanol_production']
    remove=[c for c in m.getConstrs() if c.ConstrName.startswith(('methanol_balance_hourly_','methanol_balance_daily_','methanol_balance_3hourly_','methanol_balance_weekly_','methanol_balance_monthly_','methanol_min_balance_')) or c.ConstrName in ('methanol_balance_annual','annual_methanol_production')]
    b['removed_H0_rows']=[c.ConstrName for c in remove];m.remove(remove)
    d=m.addVars(T,lb=0,name='net_delivery');z=m.addVars(T,lb=0,name='methanol_spill')
    b['net_delivery']=d;b['methanol_spill']=z
    m.addConstrs((b['methanol_synthesis_power'][t]+b['methanol_storage_discharge'][t]==d[t]+b['methanol_storage_charge'][t]+z[t] for t in range(T)),name='net_product_balance')
    m.addConstr(gp.quicksum(d.values())==Q,name='annual_net_delivery')
    if b['aggregation_mode']!='daily':raise ValueError('Revision H currently specifies the source daily contract')
    for start in range(168,T,24):
        end=min(start+24,T)
        m.addConstr(gp.quicksum(d[t] for t in range(start,end))>=.8*Q/T*(end-start),name=f'daily_net_delivery_{start}')
    m.addConstr(b['methanol_storage_balance'][0]<=b['methanol_storage_capacity'],name='methanol_storage_capacity_limit_0')
    b['wind_capacity'].UB=node['wind_cap_kw'];b['pv_capacity'].UB=node['pv_cap_kw']
    # Higher precision than historical barrier termination; same linear model.
    m.Params.BarConvTol=1e-8
    m.update()
    return b
