"""Annual relaxation Y of net-delivery H.
Summed electricity/material rows and telescoped storage rows are retained.
Hourly capacity bounds are summed. Ramp, time-specific minimum loads, daily
availability and intra-year inventory paths are relaxed. Technology choices,
conversions, structural AE/battery coupling, endpoint convention, renewable
caps and objective coefficients are unchanged. Every feasible H dispatch
projects to Y through annual sums, capacities and terminal inventories.
"""
import gurobipy as gp
from gurobipy import GRB

CAPS={
'wind':('wind_cost','wind_lifetime'),
'pv':('pv_cost','pv_lifetime'),
'battery_energy':('battery_energy_cost','battery_lifetime'),
'battery_storage':('battery_storage_cost','battery_lifetime'),
'electrolyzer_AE':('electrolyzer_cost_AE','electrolyzer_lifetime_AE'),
'electrolyzer_PEM':('electrolyzer_cost_PEM','electrolyzer_lifetime_PEM'),
'methanol_synthesis':('methanol_synthesis_cost','methanol_synthesis_lifetime'),
'heat_pump':('heat_pump_cost','heat_pump_lifetime'),
' thermal_storage':('thermal_storage_cost','thermal_storage_lifetime'),
'hydrogen_storage':('hydrogen_storage_cost','hydrogen_storage_lifetime'),
'methanol_storage':('methanol_storage_cost_param','methanol_storage_lifetime'),
'dac':('dac_cost','dac_lifetime'),
'co2_compressor':('co2_compressor_cost','co2_compressor_lifetime'),
'co2_storage':('co2_storage_cost','co2_storage_lifetime')}
CAPS={k.strip():v for k,v in CAPS.items()}
def capname(k):
    if k.startswith('electrolyzer_'):return 'electrolyzer_capacity_'+k.split('_')[-1]
    return k+'_capacity'
FLOWS=['battery_charge','battery_discharge','electrolyzer_power_AE','electrolyzer_power_PEM','methanol_synthesis_power','surplus','hydrogen_charge','hydrogen_discharge','methanol_storage_charge','methanol_storage_discharge','dac_CO2','dac_electricity','dac_heat_input','heat_pump_output','thermal_charge','thermal_discharge','co2_comp_elec','co2_charge','co2_discharge','direct_co2','stored_co2','net_delivery','methanol_spill']
STOCKS={'energy_balance':'battery_storage','hydrogen_storage_balance':'hydrogen_storage','methanol_storage_balance':'methanol_storage','thermal_storage_level':'thermal_storage','co2_storage_level':'co2_storage'}

def build_annual(p,node,wind_cf,pv_cf):
    T=len(wind_cf)
    if len(pv_cf)!=T:raise ValueError('Profile lengths differ')
    m=gp.Model('Methanol_annual_relaxation_Y');m.Params.OutputFlag=0;m.Params.Threads=1;m.Params.FeasibilityTol=1e-8;m.Params.OptimalityTol=1e-8
    k={key:m.addVar(lb=0,name=capname(key)) for key in CAPS}
    k['wind'].UB=node['wind_cap_kw'];k['pv'].UB=node['pv_cap_kw']
    f={key:m.addVar(lb=0,name=key) for key in FLOWS}
    e={key:m.addVar(lb=0,name='terminal_'+key) for key in STOCKS}
    annual={key:p[c]*(p['discount_rate']/(1-(1+p['discount_rate'])**(-p[life]))+.03) for key,(c,life) in CAPS.items()}
    penalties={'surplus':p['surplus_penalty'],'battery_charge':p['battery_charge_penalty'],'battery_discharge':p['battery_discharge_penalty'],'hydrogen_charge':p['hydrogen_charge_penalty'],'methanol_storage_charge':p['methanol_charge_penalty']}
    m.setObjective(gp.quicksum(annual[key]*v for key,v in k.items())+p['sorbent_cost']*f['dac_CO2']+gp.quicksum(c*f[key] for key,c in penalties.items()),GRB.MINIMIZE)
    m.addConstr(sum(wind_cf)*k['wind']+sum(pv_cf)*k['pv']+f['battery_discharge']==f['electrolyzer_power_AE']+f['electrolyzer_power_PEM']+p['methanol_electricity_ratio']*f['methanol_synthesis_power']+f['battery_charge']+p['hydrogen_storage_elec']*f['hydrogen_charge']+f['heat_pump_output']/p['heat_pump_cop']+f['dac_electricity']+f['surplus']+f['co2_comp_elec'],name='annual_power_balance')
    m.addConstr(e['energy_balance']==p['battery_charge_efficiency']*f['battery_charge']-f['battery_discharge']/p['battery_discharge_efficiency'],name='telescoped_battery_balance')
    m.addConstr(f['battery_charge']+f['battery_discharge']<=T*k['battery_energy'],name='annual_battery_rate')
    m.addConstr(e['hydrogen_storage_balance']==p['hydrogen_storage_efficiency']*f['hydrogen_charge']-f['hydrogen_discharge'],name='telescoped_hydrogen_balance')
    m.addConstr(f['hydrogen_charge']+f['hydrogen_discharge']<=T*k['hydrogen_storage'],name='annual_hydrogen_rate')
    m.addConstr(p['electrolyzer_eff_AE']*.03*f['electrolyzer_power_AE']+p['electrolyzer_eff_PEM']*.03*f['electrolyzer_power_PEM']+f['hydrogen_discharge']>=p['methanol_hydrogen_ratio']*f['methanol_synthesis_power']+f['hydrogen_charge'],name='annual_hydrogen_supply')
    m.addConstr(e['methanol_storage_balance']==f['methanol_storage_charge']-f['methanol_storage_discharge'],name='telescoped_product_storage')
    m.addConstr(f['methanol_synthesis_power']+f['methanol_storage_discharge']==f['net_delivery']+f['methanol_storage_charge']+f['methanol_spill'],name='annual_product_balance')
    m.addConstr(f['net_delivery']==p['target_methanol_production'],name='annual_net_delivery')
    m.addConstr(f['dac_heat_input']==p['dac_heat_per_kg']*f['dac_CO2'],name='annual_DAC_heat')
    m.addConstr(f['dac_electricity']==p['dac_elec_per_kg']*f['dac_CO2'],name='annual_DAC_electricity')
    m.addConstr(f['direct_co2']+f['stored_co2']==f['dac_CO2'],name='annual_CO2_split')
    m.addConstr(f['co2_comp_elec']==p['co2_compression_energy']*f['stored_co2'],name='annual_compressor_electricity')
    m.addConstr(f['co2_charge']==f['stored_co2'],name='annual_CO2_charge')
    m.addConstr(e['co2_storage_level']==f['co2_charge']-f['co2_discharge'],name='telescoped_CO2_storage')
    m.addConstr(f['direct_co2']+f['co2_discharge']>=p['methanol_co2_ratio']*f['methanol_synthesis_power'],name='annual_CO2_supply')
    m.addConstr(f['direct_co2']+f['co2_discharge']>=p['target_methanol_production']*p['methanol_co2_ratio'],name='annual_CO2_target')
    m.addConstr(f['heat_pump_output']-f['thermal_charge']+f['thermal_discharge']>=f['dac_heat_input'],name='annual_heat_supply')
    m.addConstr(e['thermal_storage_level']==p['thermal_storage_efficiency']*f['thermal_charge']-f['thermal_discharge']/p['thermal_storage_efficiency'],name='telescoped_thermal_storage')
    for flow,cap in [('electrolyzer_power_AE','electrolyzer_AE'),('electrolyzer_power_PEM','electrolyzer_PEM'),('methanol_synthesis_power','methanol_synthesis'),('dac_CO2','dac'),('heat_pump_output','heat_pump'),('stored_co2','co2_compressor')]:
        m.addConstr(f[flow]<=T*k[cap],name='annual_capacity_'+flow)
    for stock,cap in STOCKS.items():m.addConstr(e[stock]<=k[cap],name='terminal_capacity_'+stock)
    m.addConstr(k['battery_energy']>=.5*k['electrolyzer_AE'],name='min_battery_for_AE')
    m.update()
    return {'model':m,'capacity':k,'flows':f,'terminal':e,'annual_cost_coefficients':annual,'penalty_coefficients':penalties}

def projected_solution(bundle,solution):
    """Map a saved H solution to Y and check every annual row without a re-solve."""
    vals=dict(zip(solution['names'].tolist(),solution['values'].tolist()));m=bundle['model']
    mapped={}
    for v in m.getVars():
        name=v.VarName
        if name.startswith('terminal_'):mapped[name]=vals[name[9:]+'[8759]']
        elif name in FLOWS:mapped[name]=sum(val for key,val in vals.items() if key.startswith(name+'['))
        else:mapped[name]=vals[name]
    checks=[]
    for row in m.getConstrs():
        expr=m.getRow(row);lhs=sum(expr.getCoeff(i)*mapped[expr.getVar(i).VarName] for i in range(expr.size()));rhs=row.RHS
        violation=abs(lhs-rhs) if row.Sense=='=' else max(0,lhs-rhs) if row.Sense=='<' else max(0,rhs-lhs)
        # Normalize by equation activity for physically different units/scales.
        activity=max(1,abs(rhs),sum(abs(expr.getCoeff(i)*mapped[expr.getVar(i).VarName]) for i in range(expr.size())))
        checks.append({'row':row.ConstrName,'absolute_residual':violation,'scaled_residual':violation/activity})
    projected_obj=sum(v.Obj*mapped[v.VarName] for v in m.getVars())
    return {'projected_objective':projected_obj,'max_scaled_row_violation':max(x['scaled_residual'] for x in checks),'rows':checks,'mapped':mapped}
