from __future__ import annotations
import numpy as np
import gurobipy as gp
from gurobipy import Model, GRB

def optimize_ammonia_system(wind_output, pv_output, target_ammonia_production, wind_cost, pv_cost, battery_energy_cost, battery_storage_cost, battery_charge_efficiency, battery_discharge_efficiency, battery_charge_penalty, battery_discharge_penalty, electrolyzer_cost_AE, electrolyzer_cost_PEM, electrolyzer_eff_AE, electrolyzer_eff_PEM, ammonia_synthesis_cost, hydrogen_storage_cost, hydrogen_storage_elec, hydrogen_charge_penalty, hydrogen_storage_efficiency, ammonia_storage_cost_param, discount_rate, battery_lifetime, wind_lifetime, pv_lifetime, electrolyzer_lifetime_AE, electrolyzer_lifetime_PEM, ammonia_synthesis_lifetime, hydrogen_storage_lifetime, ammonia_storage_lifetime, Flex_up, Flex_mid, Flex_down, Flex_am_up, Flex_am_down, am_min_load, surplus_penalty, aggregation_mode):
    wind_om = wind_cost * 0.03
    pv_om = pv_cost * 0.03
    battery_energy_om = battery_energy_cost * 0.03
    battery_storage_om = battery_storage_cost * 0.03
    electrolyzer_om_AE = electrolyzer_cost_AE * 0.03
    electrolyzer_om_PEM = electrolyzer_cost_PEM * 0.03
    ammonia_synthesis_om = ammonia_synthesis_cost * 0.03
    hydrogen_storage_om = hydrogen_storage_cost * 0.03
    ammonia_storage_om = ammonia_storage_cost_param * 0.03
    wind_annual_cost = wind_cost * discount_rate / (1 - (1 + discount_rate) ** (-wind_lifetime)) + wind_om
    pv_annual_cost = pv_cost * discount_rate / (1 - (1 + discount_rate) ** (-pv_lifetime)) + pv_om
    battery_energy_annual_cost = battery_energy_cost * discount_rate / (1 - (1 + discount_rate) ** (-battery_lifetime)) + battery_energy_om
    battery_storage_annual_cost = battery_storage_cost * discount_rate / (1 - (1 + discount_rate) ** (-battery_lifetime)) + battery_storage_om
    electrolyzer_annual_cost_AE = electrolyzer_cost_AE * discount_rate / (1 - (1 + discount_rate) ** (-electrolyzer_lifetime_AE)) + electrolyzer_om_AE
    electrolyzer_annual_cost_PEM = electrolyzer_cost_PEM * discount_rate / (1 - (1 + discount_rate) ** (-electrolyzer_lifetime_PEM)) + electrolyzer_om_PEM
    ammonia_synthesis_annual_cost = ammonia_synthesis_cost * discount_rate / (1 - (1 + discount_rate) ** (-ammonia_synthesis_lifetime)) + ammonia_synthesis_om
    hydrogen_storage_annual_cost = hydrogen_storage_cost * discount_rate / (1 - (1 + discount_rate) ** (-hydrogen_storage_lifetime)) + hydrogen_storage_om
    ammonia_storage_annual_cost = ammonia_storage_cost_param * discount_rate / (1 - (1 + discount_rate) ** (-ammonia_storage_lifetime)) + ammonia_storage_om
    hourly_ammonia_demand = target_ammonia_production / 8760
    ammonia_electricity_ratio = 0.303
    ammonia_hydrogen_ratio = 0.18
    time_steps = 8760
    model = Model('AmmoniaOptimization_SplitBattery_AEPem')
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', 1000)
    model.setParam('Method', 2)
    model.setParam('Crossover', 0)
    model.setParam('BarConvTol', 1e-06)
    model.setParam('Threads', 4)
    model.setParam('Presolve', 1)
    model.setParam('BarHomogeneous', 1)
    wind_capacity = model.addVar(lb=0, name='wind_capacity')
    pv_capacity = model.addVar(lb=0, name='pv_capacity')
    battery_energy_capacity = model.addVar(lb=0, name='battery_energy_capacity')
    battery_storage_capacity = model.addVar(lb=0, name='battery_storage_capacity')
    electrolyzer_capacity_AE = model.addVar(lb=0, name='electrolyzer_capacity_AE')
    electrolyzer_capacity_PEM = model.addVar(lb=0, name='electrolyzer_capacity_PEM')
    ammonia_synthesis_capacity = model.addVar(lb=0, name='ammonia_synthesis_capacity')
    hydrogen_storage_capacity = model.addVar(lb=0, name='hydrogen_storage_capacity')
    ammonia_storage_capacity = model.addVar(lb=0, name='ammonia_storage_capacity')
    energy_balance = model.addVars(time_steps, lb=0, name='energy_balance')
    battery_charge = model.addVars(time_steps, lb=0, name='battery_charge')
    battery_discharge = model.addVars(time_steps, lb=0, name='battery_discharge')
    electrolyzer_power_AE = model.addVars(time_steps, lb=0, name='electrolyzer_power_AE')
    electrolyzer_power_PEM = model.addVars(time_steps, lb=0, name='electrolyzer_power_PEM')
    ammonia_synthesis_power = model.addVars(time_steps, lb=0, name='ammonia_synthesis_power')
    surplus = model.addVars(time_steps, lb=0, name='surplus')
    hydrogen_storage_balance = model.addVars(time_steps, lb=0, name='hydrogen_storage_balance')
    hydrogen_charge = model.addVars(time_steps, lb=0, name='hydrogen_charge')
    hydrogen_discharge = model.addVars(time_steps, lb=0, name='hydrogen_discharge')
    ammonia_storage_balance = model.addVars(time_steps, lb=0, name='ammonia_storage_balance')
    ammonia_storage_charge = model.addVars(time_steps, lb=0, name='ammonia_storage_charge')
    ammonia_storage_discharge = model.addVars(time_steps, lb=0, name='ammonia_storage_discharge')
    model.setObjective(wind_annual_cost * wind_capacity + pv_annual_cost * pv_capacity + battery_energy_annual_cost * battery_energy_capacity + battery_storage_annual_cost * battery_storage_capacity + electrolyzer_annual_cost_AE * electrolyzer_capacity_AE + electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM + ammonia_synthesis_annual_cost * ammonia_synthesis_capacity + hydrogen_storage_annual_cost * hydrogen_storage_capacity + ammonia_storage_annual_cost * ammonia_storage_capacity + surplus_penalty * gp.quicksum((surplus[t] for t in range(time_steps))) + battery_charge_penalty * gp.quicksum((battery_charge[t] for t in range(time_steps))) + battery_discharge_penalty * gp.quicksum((battery_discharge[t] for t in range(time_steps))) + hydrogen_charge_penalty * gp.quicksum((hydrogen_charge[t] for t in range(time_steps))), GRB.MINIMIZE)
    for t in range(1, time_steps):
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t - 1] <= Flex_down * electrolyzer_capacity_AE, name=f'electrolyzer_AE_ramp_up_{t}')
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t - 1] >= -Flex_down * electrolyzer_capacity_AE, name=f'electrolyzer_AE_ramp_down_{t}')
        model.addConstr(ammonia_synthesis_power[t] - ammonia_synthesis_power[t - 1] <= Flex_am_up * ammonia_synthesis_capacity, name=f'ammonia_ramp_up_{t}')
        model.addConstr(ammonia_synthesis_power[t] - ammonia_synthesis_power[t - 1] >= -Flex_am_down * ammonia_synthesis_capacity, name=f'ammonia_ramp_down_{t}')
    start_index = 168
    if aggregation_mode == 'hourly':
        for t in range(start_index, time_steps):
            model.addConstr(ammonia_synthesis_power[t] + ammonia_storage_discharge[t] == hourly_ammonia_demand + ammonia_storage_charge[t], name=f'ammonia_balance_{t}')
    elif aggregation_mode == '3hourly':
        interval = 3
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(gp.quicksum((ammonia_synthesis_power[t] for t in range(t_start, t_end))) + gp.quicksum((ammonia_storage_discharge[t] for t in range(t_start, t_end))) == hourly_ammonia_demand * interval + gp.quicksum((ammonia_storage_charge[t] for t in range(t_start, t_end))), name=f'ammonia_balance_3hourly_{i}')
    elif aggregation_mode == 'daily':
        interval = 24
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(gp.quicksum((ammonia_synthesis_power[t] for t in range(t_start, t_end))) + gp.quicksum((ammonia_storage_discharge[t] for t in range(t_start, t_end))) >= 0.8 * hourly_ammonia_demand * interval + gp.quicksum((ammonia_storage_charge[t] for t in range(t_start, t_end))), name=f'ammonia_balance_daily_{i}')
    elif aggregation_mode == 'weekly':
        interval = 168
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(gp.quicksum((ammonia_synthesis_power[t] for t in range(t_start, t_end))) + gp.quicksum((ammonia_storage_discharge[t] for t in range(t_start, t_end))) == hourly_ammonia_demand * interval + gp.quicksum((ammonia_storage_charge[t] for t in range(t_start, t_end))), name=f'ammonia_balance_weekly_{i}')
    elif aggregation_mode == 'monthly':
        interval = 730
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(gp.quicksum((ammonia_synthesis_power[t] for t in range(t_start, t_end))) + gp.quicksum((ammonia_storage_discharge[t] for t in range(t_start, t_end))) == hourly_ammonia_demand * interval + gp.quicksum((ammonia_storage_charge[t] for t in range(t_start, t_end))), name=f'ammonia_balance_monthly_{i}')
    elif aggregation_mode == 'annual':
        model.addConstr(gp.quicksum((ammonia_synthesis_power[t] for t in range(start_index, time_steps))) + gp.quicksum((ammonia_storage_discharge[t] for t in range(start_index, time_steps))) == hourly_ammonia_demand * (time_steps - start_index) + gp.quicksum((ammonia_storage_charge[t] for t in range(start_index, time_steps))), name='ammonia_balance_annual')
    else:
        raise ValueError('Unsupported aggregation_mode value!')
    model.addConstr(gp.quicksum((ammonia_synthesis_power[t] for t in range(time_steps))) >= hourly_ammonia_demand * 8760, name='annual_ammonia_production_constraint')
    conversion_factor_AE = electrolyzer_eff_AE * 3.6 / 120
    conversion_factor_PEM = electrolyzer_eff_PEM * 3.6 / 120
    for t in range(time_steps):
        wind_power = wind_output[t] * wind_capacity
        pv_power = pv_output[t] * pv_capacity
        model.addConstr(energy_balance[t] <= battery_storage_capacity, name=f'energy_balance_limit_{t}')
        model.addConstr(battery_charge[t] + battery_discharge[t] <= battery_energy_capacity, name=f'battery_charge_discharge_limit_{t}')
        if t == 0:
            model.addConstr(energy_balance[t] == battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency, name=f'battery_balance_{t}')
        else:
            model.addConstr(energy_balance[t] == energy_balance[t - 1] + battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency, name=f'battery_balance_{t}')
        model.addConstr(hydrogen_storage_balance[t] <= hydrogen_storage_capacity, name=f'hydrogen_storage_capacity_limit_{t}')
        model.addConstr(hydrogen_charge[t] + hydrogen_discharge[t] <= hydrogen_storage_capacity, name=f'hydrogen_charge_limit_{t}')
        if t == 0:
            model.addConstr(hydrogen_storage_balance[t] == hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t], name=f'hydrogen_balance_{t}')
        else:
            model.addConstr(hydrogen_storage_balance[t] == hydrogen_storage_balance[t - 1] + hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t], name=f'hydrogen_balance_{t}')
        model.addConstr(ammonia_storage_balance[t] == (ammonia_storage_balance[t - 1] if t > 0 else ammonia_storage_charge[0]) + ammonia_storage_charge[t] - ammonia_storage_discharge[t], name=f'ammonia_storage_balance_{t}')
        model.addConstr(ammonia_storage_balance[t] <= ammonia_storage_capacity, name=f'ammonia_storage_capacity_limit_{t}')
        model.addConstr(ammonia_synthesis_power[t] + ammonia_storage_discharge[t] >= ammonia_storage_charge[t], name=f'ammonia_min_balance_{t}')
        model.addConstr(wind_power + pv_power + battery_discharge[t] == electrolyzer_power_AE[t] + electrolyzer_power_PEM[t] + battery_charge[t] + hydrogen_charge[t] * hydrogen_storage_elec + ammonia_synthesis_power[t] * ammonia_electricity_ratio + surplus[t], name=f'power_balance_{t}')
        model.addConstr(electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM + hydrogen_discharge[t] >= ammonia_synthesis_power[t] * ammonia_hydrogen_ratio + hydrogen_charge[t], name=f'hydrogen_PD_balance_{t}')
    model.addConstrs((electrolyzer_capacity_AE >= electrolyzer_power_AE[t] for t in range(time_steps)), name='electrolyzer_AE_capacity')
    model.addConstrs((electrolyzer_capacity_PEM >= electrolyzer_power_PEM[t] for t in range(time_steps)), name='electrolyzer_PEM_capacity')
    model.addConstrs((electrolyzer_power_AE[t] >= 0.1 * electrolyzer_capacity_AE for t in range(start_index, time_steps)), name='electrolyzer_AE_min')
    model.addConstrs((ammonia_synthesis_capacity >= ammonia_synthesis_power[t] for t in range(time_steps)), name='ammonia_capacity')
    model.addConstrs((ammonia_synthesis_power[t] >= am_min_load * ammonia_synthesis_capacity for t in range(start_index, time_steps)), name='ammonia_min')
    model.addConstr(battery_energy_capacity >= 0.5 * electrolyzer_capacity_AE, name='min_battery_for_AE')
    return model

def optimize_methanol_system(wind_output, pv_output, target_methanol_production, wind_cost, pv_cost, battery_energy_cost, battery_storage_cost, battery_charge_efficiency, battery_discharge_efficiency, battery_charge_penalty, battery_discharge_penalty, electrolyzer_cost_AE, electrolyzer_cost_PEM, electrolyzer_eff_AE, electrolyzer_eff_PEM, methanol_synthesis_cost, hydrogen_storage_cost, hydrogen_storage_elec, hydrogen_charge_penalty, hydrogen_storage_efficiency, methanol_storage_cost_param, methanol_charge_penalty, discount_rate, battery_lifetime, wind_lifetime, pv_lifetime, electrolyzer_lifetime_AE, electrolyzer_lifetime_PEM, methanol_synthesis_lifetime, hydrogen_storage_lifetime, methanol_storage_lifetime, heat_pump_cost, heat_pump_cop, heat_pump_lifetime, thermal_storage_cost, thermal_storage_efficiency, thermal_storage_lifetime, dac_cost, dac_elec_per_kg, dac_heat_per_kg, dac_lifetime, sorbent_cost, co2_compressor_cost, co2_compression_energy, co2_compressor_lifetime, co2_storage_cost, co2_storage_lifetime, Flex_up, Flex_mid, Flex_down, Flex_me_up, Flex_me_down, Flex_dac_up, Flex_dac_down, me_min_load, dac_min_load, surplus_penalty, aggregation_mode):
    wind_om = wind_cost * 0.03
    pv_om = pv_cost * 0.03
    battery_energy_om = battery_energy_cost * 0.03
    battery_storage_om = battery_storage_cost * 0.03
    electrolyzer_om_AE = electrolyzer_cost_AE * 0.03
    electrolyzer_om_PEM = electrolyzer_cost_PEM * 0.03
    methanol_synthesis_om = methanol_synthesis_cost * 0.03
    hydrogen_storage_om = hydrogen_storage_cost * 0.03
    methanol_storage_om = methanol_storage_cost_param * 0.03
    heat_pump_om = heat_pump_cost * 0.03
    thermal_storage_om = thermal_storage_cost * 0.03
    dac_om = dac_cost * 0.03
    co2_compressor_om = co2_compressor_cost * 0.03
    co2_storage_om = co2_storage_cost * 0.03
    wind_annual_cost = wind_cost * discount_rate / (1 - (1 + discount_rate) ** (-wind_lifetime)) + wind_om
    pv_annual_cost = pv_cost * discount_rate / (1 - (1 + discount_rate) ** (-pv_lifetime)) + pv_om
    battery_energy_annual_cost = battery_energy_cost * discount_rate / (1 - (1 + discount_rate) ** (-battery_lifetime)) + battery_energy_om
    battery_storage_annual_cost = battery_storage_cost * discount_rate / (1 - (1 + discount_rate) ** (-battery_lifetime)) + battery_storage_om
    electrolyzer_annual_cost_AE = electrolyzer_cost_AE * discount_rate / (1 - (1 + discount_rate) ** (-electrolyzer_lifetime_AE)) + electrolyzer_om_AE
    electrolyzer_annual_cost_PEM = electrolyzer_cost_PEM * discount_rate / (1 - (1 + discount_rate) ** (-electrolyzer_lifetime_PEM)) + electrolyzer_om_PEM
    methanol_synthesis_annual_cost = methanol_synthesis_cost * discount_rate / (1 - (1 + discount_rate) ** (-methanol_synthesis_lifetime)) + methanol_synthesis_om
    hydrogen_storage_annual_cost = hydrogen_storage_cost * discount_rate / (1 - (1 + discount_rate) ** (-hydrogen_storage_lifetime)) + hydrogen_storage_om
    methanol_storage_annual_cost = methanol_storage_cost_param * discount_rate / (1 - (1 + discount_rate) ** (-methanol_storage_lifetime)) + methanol_storage_om
    heat_pump_annual_cost = heat_pump_cost * discount_rate / (1 - (1 + discount_rate) ** (-heat_pump_lifetime)) + heat_pump_om
    thermal_storage_annual_cost = thermal_storage_cost * discount_rate / (1 - (1 + discount_rate) ** (-thermal_storage_lifetime)) + thermal_storage_om
    dac_annual_cost = dac_cost * discount_rate / (1 - (1 + discount_rate) ** (-dac_lifetime)) + dac_om
    co2_compressor_annual_cost = co2_compressor_cost * discount_rate / (1 - (1 + discount_rate) ** (-co2_compressor_lifetime)) + co2_compressor_om
    co2_storage_annual_cost = co2_storage_cost * discount_rate / (1 - (1 + discount_rate) ** (-co2_storage_lifetime)) + co2_storage_om
    hourly_methanol_demand = target_methanol_production / 8760
    methanol_electricity_ratio = 0.7
    methanol_hydrogen_ratio = 0.19
    methanol_co2_ratio = 1.4
    time_steps = 8760
    model = Model('MethanolDACOptimization')
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', 1000)
    model.setParam('Method', 2)
    model.setParam('Crossover', 0)
    model.setParam('BarConvTol', 1e-06)
    model.setParam('Threads', 4)
    model.setParam('Presolve', 1)
    model.setParam('BarHomogeneous', 1)
    wind_capacity = model.addVar(lb=0, name='wind_capacity')
    pv_capacity = model.addVar(lb=0, name='pv_capacity')
    battery_energy_capacity = model.addVar(lb=0, name='battery_energy_capacity')
    battery_storage_capacity = model.addVar(lb=0, name='battery_storage_capacity')
    electrolyzer_capacity_AE = model.addVar(lb=0, name='electrolyzer_capacity_AE')
    electrolyzer_capacity_PEM = model.addVar(lb=0, name='electrolyzer_capacity_PEM')
    methanol_synthesis_capacity = model.addVar(lb=0, name='methanol_synthesis_capacity')
    heat_pump_capacity = model.addVar(lb=0, name='heat_pump_capacity')
    thermal_storage_capacity = model.addVar(lb=0, name='thermal_storage_capacity')
    methanol_storage_capacity = model.addVar(lb=0, name='methanol_storage_capacity')
    hydrogen_storage_capacity = model.addVar(lb=0, name='hydrogen_storage_capacity')
    dac_capacity = model.addVar(lb=0, name='dac_capacity')
    co2_compressor_capacity = model.addVar(lb=0, name='co2_compressor_capacity')
    co2_storage_capacity = model.addVar(lb=0, name='co2_storage_capacity')
    energy_balance = model.addVars(time_steps, lb=0, name='energy_balance')
    battery_charge = model.addVars(time_steps, lb=0, name='battery_charge')
    battery_discharge = model.addVars(time_steps, lb=0, name='battery_discharge')
    electrolyzer_power_AE = model.addVars(time_steps, lb=0, name='electrolyzer_power_AE')
    electrolyzer_power_PEM = model.addVars(time_steps, lb=0, name='electrolyzer_power_PEM')
    methanol_synthesis_power = model.addVars(time_steps, lb=0, name='methanol_synthesis_power')
    surplus = model.addVars(time_steps, lb=0, name='surplus')
    hydrogen_storage_balance = model.addVars(time_steps, lb=0, name='hydrogen_storage_balance')
    hydrogen_charge = model.addVars(time_steps, lb=0, name='hydrogen_charge')
    hydrogen_discharge = model.addVars(time_steps, lb=0, name='hydrogen_discharge')
    methanol_storage_balance = model.addVars(time_steps, lb=0, name='methanol_storage_balance')
    methanol_storage_charge = model.addVars(time_steps, lb=0, name='methanol_storage_charge')
    methanol_storage_discharge = model.addVars(time_steps, lb=0, name='methanol_storage_discharge')
    dac_CO2 = model.addVars(time_steps, lb=0, name='dac_CO2')
    dac_electricity = model.addVars(time_steps, lb=0, name='dac_electricity')
    dac_heat_input = model.addVars(time_steps, lb=0, name='dac_heat_input')
    heat_pump_output = model.addVars(time_steps, lb=0, name='heat_pump_output')
    thermal_charge = model.addVars(time_steps, lb=0, name='thermal_charge')
    thermal_discharge = model.addVars(time_steps, lb=0, name='thermal_discharge')
    thermal_storage_level = model.addVars(time_steps, lb=0, name='thermal_storage_level')
    co2_comp_elec = model.addVars(time_steps, lb=0, name='co2_comp_elec')
    co2_storage_level = model.addVars(time_steps, lb=0, name='co2_storage_level')
    co2_charge = model.addVars(time_steps, lb=0, name='co2_charge')
    co2_discharge = model.addVars(time_steps, lb=0, name='co2_discharge')
    direct_co2 = model.addVars(time_steps, lb=0, name='direct_co2')
    stored_co2 = model.addVars(time_steps, lb=0, name='stored_co2')
    conversion_factor_AE = electrolyzer_eff_AE * 3.6 / 120
    conversion_factor_PEM = electrolyzer_eff_PEM * 3.6 / 120
    model.setObjective(wind_annual_cost * wind_capacity + pv_annual_cost * pv_capacity + battery_energy_annual_cost * battery_energy_capacity + battery_storage_annual_cost * battery_storage_capacity + electrolyzer_annual_cost_AE * electrolyzer_capacity_AE + electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM + methanol_synthesis_annual_cost * methanol_synthesis_capacity + heat_pump_annual_cost * heat_pump_capacity + thermal_storage_annual_cost * thermal_storage_capacity + hydrogen_storage_annual_cost * hydrogen_storage_capacity + methanol_storage_annual_cost * methanol_storage_capacity + dac_annual_cost * dac_capacity + co2_compressor_annual_cost * co2_compressor_capacity + co2_storage_annual_cost * co2_storage_capacity + sorbent_cost * gp.quicksum((dac_CO2[t] for t in range(time_steps))) + surplus_penalty * gp.quicksum((surplus[t] for t in range(time_steps))) + battery_charge_penalty * gp.quicksum((battery_charge[t] for t in range(time_steps))) + battery_discharge_penalty * gp.quicksum((battery_discharge[t] for t in range(time_steps))) + hydrogen_charge_penalty * gp.quicksum((hydrogen_charge[t] for t in range(time_steps))) + methanol_charge_penalty * gp.quicksum((methanol_storage_charge[t] for t in range(time_steps))), GRB.MINIMIZE)
    for t in range(1, time_steps):
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t - 1] <= Flex_down * electrolyzer_capacity_AE)
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t - 1] >= -Flex_down * electrolyzer_capacity_AE)
        model.addConstr(methanol_synthesis_power[t] - methanol_synthesis_power[t - 1] <= Flex_me_up * methanol_synthesis_capacity)
        model.addConstr(methanol_synthesis_power[t] - methanol_synthesis_power[t - 1] >= -Flex_me_down * methanol_synthesis_capacity)
        model.addConstr(dac_CO2[t] - dac_CO2[t - 1] <= Flex_dac_up * dac_capacity)
        model.addConstr(dac_CO2[t] - dac_CO2[t - 1] >= -Flex_dac_down * dac_capacity)
    start_index = 168
    if aggregation_mode == 'hourly':
        for t in range(start_index, time_steps):
            model.addConstr(methanol_synthesis_power[t] + methanol_storage_discharge[t] >= hourly_methanol_demand + methanol_storage_charge[t], name=f'methanol_balance_hourly_{t}')
    elif aggregation_mode == '3hourly':
        interval = 3
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(gp.quicksum((methanol_synthesis_power[t] for t in range(t_start, t_end))) + gp.quicksum((methanol_storage_discharge[t] for t in range(t_start, t_end))) == hourly_methanol_demand * interval + gp.quicksum((methanol_storage_charge[t] for t in range(t_start, t_end))), name=f'methanol_balance_3hourly_{i}')
    elif aggregation_mode == 'daily':
        interval = 24
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(gp.quicksum((methanol_synthesis_power[t] for t in range(t_start, t_end))) + gp.quicksum((methanol_storage_discharge[t] for t in range(t_start, t_end))) >= 0.8 * hourly_methanol_demand * interval + gp.quicksum((methanol_storage_charge[t] for t in range(t_start, t_end))), name=f'methanol_balance_daily_{i}')
    elif aggregation_mode == 'weekly':
        interval = 168
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(gp.quicksum((methanol_synthesis_power[t] for t in range(t_start, t_end))) + gp.quicksum((methanol_storage_discharge[t] for t in range(t_start, t_end))) == hourly_methanol_demand * interval + gp.quicksum((methanol_storage_charge[t] for t in range(t_start, t_end))), name=f'methanol_balance_weekly_{i}')
    elif aggregation_mode == 'monthly':
        interval = 730
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(gp.quicksum((methanol_synthesis_power[t] for t in range(t_start, t_end))) + gp.quicksum((methanol_storage_discharge[t] for t in range(t_start, t_end))) == hourly_methanol_demand * interval + gp.quicksum((methanol_storage_charge[t] for t in range(t_start, t_end))), name=f'methanol_balance_monthly_{i}')
    elif aggregation_mode == 'annual':
        model.addConstr(gp.quicksum((methanol_synthesis_power[t] for t in range(start_index, time_steps))) + gp.quicksum((methanol_storage_discharge[t] for t in range(start_index, time_steps))) == hourly_methanol_demand * (time_steps - start_index) + gp.quicksum((methanol_storage_charge[t] for t in range(start_index, time_steps))), name='methanol_balance_annual')
    else:
        raise ValueError('Unsupported aggregation_mode value!')
    model.addConstr(gp.quicksum((methanol_synthesis_power[t] for t in range(time_steps))) >= hourly_methanol_demand * 8760, name='annual_methanol_production')
    model.addConstr(methanol_storage_balance[0] == methanol_storage_charge[0] - methanol_storage_discharge[0], name='methanol_storage_balance_0')
    for t in range(1, time_steps):
        model.addConstr(methanol_storage_balance[t] == methanol_storage_balance[t - 1] + methanol_storage_charge[t] - methanol_storage_discharge[t], name=f'methanol_storage_balance_{t}')
        model.addConstr(methanol_storage_balance[t] <= methanol_storage_capacity, name=f'methanol_storage_capacity_limit_{t}')
    conversion_factor_AE = electrolyzer_eff_AE * 3.6 / 120
    conversion_factor_PEM = electrolyzer_eff_PEM * 3.6 / 120
    for t in range(time_steps):
        wind_power = wind_output[t] * wind_capacity
        pv_power = pv_output[t] * pv_capacity
        model.addConstr(methanol_synthesis_power[t] + methanol_storage_discharge[t] >= methanol_storage_charge[t], name=f'methanol_min_balance_{t}')
        model.addConstr(energy_balance[t] <= battery_storage_capacity, name=f'energy_balance_limit_{t}')
        model.addConstr(battery_charge[t] + battery_discharge[t] <= battery_energy_capacity, name=f'battery_charge_discharge_limit_{t}')
        model.addConstr(hydrogen_storage_balance[t] <= hydrogen_storage_capacity, name=f'hydrogen_storage_capacity_limit_{t}')
        model.addConstr(hydrogen_charge[t] + hydrogen_discharge[t] <= hydrogen_storage_capacity, name=f'hydrogen_charge_limit_{t}')
        model.addConstr(wind_power + pv_power + battery_discharge[t] == electrolyzer_power_AE[t] + electrolyzer_power_PEM[t] + methanol_synthesis_power[t] * methanol_electricity_ratio + battery_charge[t] + hydrogen_charge[t] * hydrogen_storage_elec + heat_pump_output[t] / heat_pump_cop + dac_electricity[t] + surplus[t] + co2_comp_elec[t], name=f'power_balance_{t}')
        if t == 0:
            model.addConstr(energy_balance[t] == battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency, name=f'battery_balance_{t}')
        else:
            model.addConstr(energy_balance[t] == energy_balance[t - 1] + battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency, name=f'battery_balance_{t}')
        if t == 0:
            model.addConstr(hydrogen_storage_balance[t] == hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t], name=f'hydrogen_balance_{t}')
        else:
            model.addConstr(hydrogen_storage_balance[t] == hydrogen_storage_balance[t - 1] + hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t], name=f'hydrogen_balance_{t}')
        model.addConstr(electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM + hydrogen_discharge[t] >= methanol_synthesis_power[t] * methanol_hydrogen_ratio + hydrogen_charge[t], name=f'hydrogen_PD_balance_{t}')
        model.addConstr(dac_heat_input[t] == dac_CO2[t] * dac_heat_per_kg, name=f'dac_heat_consumption_{t}')
        model.addConstr(dac_electricity[t] == dac_CO2[t] * dac_elec_per_kg, name=f'dac_electricity_consumption_{t}')
        model.addConstr(dac_CO2[t] <= dac_capacity, name=f'dac_capacity_limit_{t}')
        model.addConstr(direct_co2[t] + stored_co2[t] == dac_CO2[t], name=f'co2_split_{t}')
        model.addConstr(stored_co2[t] <= co2_compressor_capacity, name=f'co2_compressor_capacity_limit_{t}')
        model.addConstr(co2_comp_elec[t] == stored_co2[t] * co2_compression_energy, name=f'co2_compression_energy_{t}')
        model.addConstr(co2_charge[t] == stored_co2[t], name=f'co2_charge_relation_{t}')
        model.addConstr(heat_pump_output[t] - thermal_charge[t] + thermal_discharge[t] >= dac_heat_input[t], name=f'heat_supply_balance_{t}')
        if t == 0:
            model.addConstr(co2_storage_level[t] == co2_charge[t] - co2_discharge[t], name='co2_storage_balance_0')
        else:
            model.addConstr(co2_storage_level[t] == co2_storage_level[t - 1] + co2_charge[t] - co2_discharge[t], name=f'co2_storage_balance_{t}')
        model.addConstr(co2_storage_level[t] <= co2_storage_capacity, name=f'co2_storage_level_limit_{t}')
        if t == 0:
            model.addConstr(thermal_storage_level[t] == thermal_charge[t] * thermal_storage_efficiency - thermal_discharge[t] / thermal_storage_efficiency, name='thermal_storage_balance_0')
        else:
            model.addConstr(thermal_storage_level[t] == thermal_storage_level[t - 1] + thermal_charge[t] * thermal_storage_efficiency - thermal_discharge[t] / thermal_storage_efficiency, name=f'thermal_storage_balance_{t}')
        model.addConstr(thermal_storage_level[t] <= thermal_storage_capacity, name=f'thermal_storage_level_limit_{t}')
    model.addConstrs((heat_pump_capacity >= heat_pump_output[t] for t in range(time_steps)), name='heat_pump_capacity_constraint')
    model.addConstrs((heat_pump_output[t] >= 0.25 * heat_pump_capacity for t in range(168, time_steps)), name='heat_pump_min_output')
    model.addConstrs((electrolyzer_capacity_AE >= electrolyzer_power_AE[t] for t in range(time_steps)), name='electrolyzer_AE_capacity_constraint')
    model.addConstrs((electrolyzer_capacity_PEM >= electrolyzer_power_PEM[t] for t in range(time_steps)), name='electrolyzer_PEM_capacity_constraint')
    model.addConstrs((electrolyzer_power_AE[t] >= 0.1 * electrolyzer_capacity_AE for t in range(168, time_steps)), name='electrolyzer_AE_min_power')
    model.addConstrs((dac_CO2[t] >= dac_min_load * dac_capacity for t in range(168, time_steps)), name='heat_pump_min_output')
    model.addConstrs((methanol_synthesis_power[t] >= me_min_load * methanol_synthesis_capacity for t in range(168, time_steps)), name='methanol_synthesis_min_output')
    model.addConstrs((methanol_synthesis_power[t] <= methanol_synthesis_capacity for t in range(time_steps)), name='methanol_synthesis_max_output')
    model.addConstrs((direct_co2[t] + co2_discharge[t] >= methanol_synthesis_power[t] * methanol_co2_ratio for t in range(time_steps)), name='co2_hourly_balance')
    model.addConstr(gp.quicksum((direct_co2[t] + co2_discharge[t] for t in range(time_steps))) >= target_methanol_production * methanol_co2_ratio, name='annual_co2_supply_constraint')
    model.addConstr(battery_energy_capacity >= 0.5 * electrolyzer_capacity_AE, name='min_battery_for_AE')
    return model

def optimize_ftl_system(wind_output, pv_output, target_ftl_production, wind_cost, pv_cost, battery_energy_cost, battery_storage_cost, battery_charge_efficiency, battery_discharge_efficiency, battery_charge_penalty, battery_discharge_penalty, electrolyzer_cost_AE, electrolyzer_cost_PEM, electrolyzer_eff_AE, electrolyzer_eff_PEM, electrolyzer_lifetime_AE, electrolyzer_lifetime_PEM, ftl_synthesis_cost, ftl_synthesis_lifetime, ftl_hydrogen_ratio, ftl_co2_ratio, ftl_electricity_ratio, hydrogen_storage_cost, hydrogen_storage_elec, hydrogen_charge_penalty, hydrogen_storage_efficiency, hydrogen_storage_lifetime, ftl_storage_cost_param, ftl_storage_lifetime, ftl_charge_penalty, heat_pump_cost, heat_pump_cop, heat_pump_lifetime, thermal_storage_cost, thermal_storage_efficiency, thermal_storage_lifetime, dac_cost, dac_elec_per_kg, dac_heat_per_kg, dac_lifetime, sorbent_cost, co2_compressor_cost, co2_compression_energy, co2_compressor_lifetime, co2_storage_cost, co2_storage_lifetime, discount_rate, battery_lifetime, wind_lifetime, pv_lifetime, Flex_up, Flex_mid, Flex_down, Flex_ftl_up, Flex_ftl_down, Flex_dac_up, Flex_dac_down, ftl_min_load, dac_min_load, surplus_penalty, aggregation_mode):
    """FT Liquid + DAC 优化模型（复用用户提供脚本逻辑，封装为函数）

    参数说明：传入逐小时风/光容量因子数组（长度需=8760），以及各类成本、效率、寿命与灵活性参数。
    返回：包含容量配置、利用率、平准化成本等指标的结果字典；若不可行返回空字典。
    """
    time_steps = len(wind_output)
    assert len(pv_output) == time_steps, 'pv_output length must match wind_output'
    wind_om = wind_cost * 0.03
    pv_om = pv_cost * 0.03
    battery_energy_om = battery_energy_cost * 0.03
    battery_storage_om = battery_storage_cost * 0.03
    electrolyzer_om_AE = electrolyzer_cost_AE * 0.03
    electrolyzer_om_PEM = electrolyzer_cost_PEM * 0.03
    ftl_synthesis_om = ftl_synthesis_cost * 0.06
    hydrogen_storage_om = hydrogen_storage_cost * 0.03
    ftl_storage_om = ftl_storage_cost_param * 0.03
    heat_pump_om = heat_pump_cost * 0.03
    thermal_storage_om = thermal_storage_cost * 0.03
    dac_om = dac_cost * 0.03
    co2_compressor_om = co2_compressor_cost * 0.03
    co2_storage_om = co2_storage_cost * 0.03
    hourly_ftl_demand = target_ftl_production / 8760.0

    def crf(dr, life):
        return dr / (1 - (1 + dr) ** (-life))
    wind_annual_cost = wind_cost * crf(discount_rate, wind_lifetime) + wind_om
    pv_annual_cost = pv_cost * crf(discount_rate, pv_lifetime) + pv_om
    battery_energy_annual_cost = battery_energy_cost * crf(discount_rate, battery_lifetime) + battery_energy_om
    battery_storage_annual_cost = battery_storage_cost * crf(discount_rate, battery_lifetime) + battery_storage_om
    electrolyzer_annual_cost_AE = electrolyzer_cost_AE * crf(discount_rate, electrolyzer_lifetime_AE) + electrolyzer_om_AE
    electrolyzer_annual_cost_PEM = electrolyzer_cost_PEM * crf(discount_rate, electrolyzer_lifetime_PEM) + electrolyzer_om_PEM
    ftl_synthesis_annual_cost = ftl_synthesis_cost * crf(discount_rate, ftl_synthesis_lifetime) + ftl_synthesis_om
    hydrogen_storage_annual_cost = hydrogen_storage_cost * crf(discount_rate, hydrogen_storage_lifetime) + hydrogen_storage_om
    dac_annual_cost = dac_cost * crf(discount_rate, dac_lifetime) + dac_om
    co2_compressor_annual_cost = co2_compressor_cost * crf(discount_rate, co2_compressor_lifetime) + co2_compressor_om
    co2_storage_annual_cost = co2_storage_cost * crf(discount_rate, co2_storage_lifetime) + co2_storage_om
    heat_pump_annual_cost = heat_pump_cost * crf(discount_rate, heat_pump_lifetime) + heat_pump_om
    thermal_storage_annual_cost = thermal_storage_cost * crf(discount_rate, thermal_storage_lifetime) + thermal_storage_om
    ftl_storage_annual_cost = ftl_storage_cost_param * crf(discount_rate, ftl_storage_lifetime) + ftl_storage_om
    model = Model('HydrogenFTLOptimization')
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', 1000)
    model.setParam('Method', 2)
    model.setParam('Crossover', 0)
    model.setParam('BarConvTol', 1e-06)
    model.setParam('Threads', 4)
    model.setParam('Presolve', 1)
    model.setParam('BarHomogeneous', 1)
    wind_capacity = model.addVar(lb=0, name='wind_capacity')
    pv_capacity = model.addVar(lb=0, name='pv_capacity')
    battery_energy_capacity = model.addVar(lb=0, name='battery_energy_capacity')
    battery_storage_capacity = model.addVar(lb=0, name='battery_storage_capacity')
    electrolyzer_capacity_AE = model.addVar(lb=0, name='electrolyzer_capacity_AE')
    electrolyzer_capacity_PEM = model.addVar(lb=0, name='electrolyzer_capacity_PEM')
    ftl_synthesis_capacity = model.addVar(lb=0, name='FTL_capacity')
    heat_pump_capacity = model.addVar(lb=0, name='heat_pump_capacity')
    thermal_storage_capacity = model.addVar(lb=0, name='thermal_storage_capacity')
    ftl_storage_capacity = model.addVar(lb=0, name='FTL_storage_capacity')
    hydrogen_storage_capacity = model.addVar(lb=0, name='hydrogen_storage_capacity')
    dac_capacity = model.addVar(lb=0, name='dac_capacity')
    co2_compressor_capacity = model.addVar(lb=0, name='co2_compressor_capacity')
    co2_storage_capacity = model.addVar(lb=0, name='co2_storage_capacity')
    energy_balance = model.addVars(time_steps, lb=0, name='energy_balance')
    battery_charge = model.addVars(time_steps, lb=0, name='battery_charge')
    battery_discharge = model.addVars(time_steps, lb=0, name='battery_discharge')
    electrolyzer_power_AE = model.addVars(time_steps, lb=0, name='electrolyzer_power_AE')
    electrolyzer_power_PEM = model.addVars(time_steps, lb=0, name='electrolyzer_power_PEM')
    ftl_synthesis_power = model.addVars(time_steps, lb=0, name='FTL_synthesis_power')
    ftl_storage_balance = model.addVars(time_steps, lb=0, name='FTL_storage_balance')
    ftl_storage_charge = model.addVars(time_steps, lb=0, name='FTL_storage_charge')
    ftl_storage_discharge = model.addVars(time_steps, lb=0, name='FTL_storage_discharge')
    hydrogen_storage_balance = model.addVars(time_steps, lb=0, name='hydrogen_storage_balance')
    hydrogen_charge = model.addVars(time_steps, lb=0, name='hydrogen_charge')
    hydrogen_discharge = model.addVars(time_steps, lb=0, name='hydrogen_discharge')
    dac_CO2 = model.addVars(time_steps, lb=0, name='dac_CO2')
    dac_electricity = model.addVars(time_steps, lb=0, name='dac_electricity')
    dac_heat_input = model.addVars(time_steps, lb=0, name='dac_heat_input')
    heat_pump_output = model.addVars(time_steps, lb=0, name='heat_pump_output')
    thermal_charge = model.addVars(time_steps, lb=0, name='thermal_charge')
    thermal_discharge = model.addVars(time_steps, lb=0, name='thermal_discharge')
    thermal_storage_level = model.addVars(time_steps, lb=0, name='thermal_storage_level')
    co2_comp_elec = model.addVars(time_steps, lb=0, name='co2_comp_elec')
    co2_storage_level = model.addVars(time_steps, lb=0, name='co2_storage_level')
    co2_charge = model.addVars(time_steps, lb=0, name='co2_charge')
    co2_discharge = model.addVars(time_steps, lb=0, name='co2_discharge')
    direct_co2 = model.addVars(time_steps, lb=0, name='direct_co2')
    stored_co2 = model.addVars(time_steps, lb=0, name='stored_co2')
    surplus = model.addVars(time_steps, lb=0, name='surplus')
    model.setObjective(wind_annual_cost * wind_capacity + pv_annual_cost * pv_capacity + battery_energy_annual_cost * battery_energy_capacity + battery_storage_annual_cost * battery_storage_capacity + electrolyzer_annual_cost_AE * electrolyzer_capacity_AE + electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM + ftl_synthesis_annual_cost * ftl_synthesis_capacity + heat_pump_annual_cost * heat_pump_capacity + thermal_storage_annual_cost * thermal_storage_capacity + hydrogen_storage_annual_cost * hydrogen_storage_capacity + ftl_storage_annual_cost * ftl_storage_capacity + dac_annual_cost * dac_capacity + co2_compressor_annual_cost * co2_compressor_capacity + co2_storage_annual_cost * co2_storage_capacity + surplus_penalty * gp.quicksum((surplus[t] for t in range(time_steps))) + battery_charge_penalty * gp.quicksum((battery_charge[t] for t in range(time_steps))) + battery_discharge_penalty * gp.quicksum((battery_discharge[t] for t in range(time_steps))) + sorbent_cost * gp.quicksum((dac_CO2[t] for t in range(time_steps))) + hydrogen_charge_penalty * gp.quicksum((hydrogen_charge[t] for t in range(time_steps))) + ftl_charge_penalty * gp.quicksum((ftl_storage_charge[t] for t in range(time_steps))), GRB.MINIMIZE)
    for t in range(1, time_steps):
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t - 1] <= Flex_down * electrolyzer_capacity_AE, name=f'electrolyzer_AE_ramp_up_{t}')
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t - 1] >= -Flex_down * electrolyzer_capacity_AE, name=f'electrolyzer_AE_ramp_down_{t}')
        model.addConstr(ftl_synthesis_power[t] - ftl_synthesis_power[t - 1] <= Flex_ftl_up * ftl_synthesis_capacity, name=f'ftl_synthesis_ramp_up_{t}')
        model.addConstr(ftl_synthesis_power[t] - ftl_synthesis_power[t - 1] >= -Flex_ftl_down * ftl_synthesis_capacity, name=f'ftl_synthesis_ramp_down_{t}')
        model.addConstr(dac_CO2[t] - dac_CO2[t - 1] <= Flex_dac_up * dac_capacity, name=f'dac_ramp_up_{t}')
        model.addConstr(dac_CO2[t] - dac_CO2[t - 1] >= -Flex_dac_down * dac_capacity, name=f'dac_ramp_down_{t}')
    start_index = 168
    if aggregation_mode == 'hourly':
        for t in range(start_index, time_steps):
            model.addConstr(ftl_synthesis_power[t] + ftl_storage_discharge[t] >= hourly_ftl_demand + ftl_storage_charge[t], name=f'ftl_balance_hourly_{t}')
    elif aggregation_mode == '3hourly':
        interval = 3
        n = (time_steps - start_index) // interval
        for i in range(n):
            s = start_index + i * interval
            e = s + interval
            model.addConstr(gp.quicksum((ftl_synthesis_power[t] for t in range(s, e))) + gp.quicksum((ftl_storage_discharge[t] for t in range(s, e))) == hourly_ftl_demand * interval + gp.quicksum((ftl_storage_charge[t] for t in range(s, e))), name=f'ftl_balance_3hourly_{i}')
    elif aggregation_mode == 'daily':
        interval = 24
        n = (time_steps - start_index) // interval
        for i in range(n):
            s = start_index + i * interval
            e = s + interval
            model.addConstr(gp.quicksum((ftl_synthesis_power[t] for t in range(s, e))) + gp.quicksum((ftl_storage_discharge[t] for t in range(s, e))) >= 0.8 * hourly_ftl_demand * interval + gp.quicksum((ftl_storage_charge[t] for t in range(s, e))), name=f'ftl_balance_daily_{i}')
    elif aggregation_mode == 'weekly':
        interval = 168
        n = (time_steps - start_index) // interval
        for i in range(n):
            s = start_index + i * interval
            e = s + interval
            model.addConstr(gp.quicksum((ftl_synthesis_power[t] for t in range(s, e))) + gp.quicksum((ftl_storage_discharge[t] for t in range(s, e))) == hourly_ftl_demand * interval + gp.quicksum((ftl_storage_charge[t] for t in range(s, e))), name=f'ftl_balance_weekly_{i}')
    elif aggregation_mode == 'monthly':
        interval = 730
        n = (time_steps - start_index) // interval
        for i in range(n):
            s = start_index + i * interval
            e = s + interval
            model.addConstr(gp.quicksum((ftl_synthesis_power[t] for t in range(s, e))) + gp.quicksum((ftl_storage_discharge[t] for t in range(s, e))) == hourly_ftl_demand * interval + gp.quicksum((ftl_storage_charge[t] for t in range(s, e))), name=f'ftl_balance_monthly_{i}')
    elif aggregation_mode == 'annual':
        model.addConstr(gp.quicksum((ftl_synthesis_power[t] for t in range(start_index, time_steps))) + gp.quicksum((ftl_storage_discharge[t] for t in range(start_index, time_steps))) == hourly_ftl_demand * (time_steps - start_index) + gp.quicksum((ftl_storage_charge[t] for t in range(start_index, time_steps))), name='ftl_balance_annual')
    else:
        raise ValueError('Unsupported aggregation_mode')
    model.addConstr(gp.quicksum((ftl_synthesis_power[t] for t in range(time_steps))) >= target_ftl_production, name='annual_ftl_production_constraint')
    model.addConstr(ftl_storage_balance[0] == ftl_storage_charge[0] - ftl_storage_discharge[0], name='ftl_storage_balance_0')
    for t in range(1, time_steps):
        model.addConstr(ftl_storage_balance[t] == ftl_storage_balance[t - 1] + ftl_storage_charge[t] - ftl_storage_discharge[t], name=f'ftl_storage_balance_{t}')
        model.addConstr(ftl_storage_balance[t] <= ftl_storage_capacity, name=f'ftl_storage_capacity_limit_{t}')
    conversion_factor_AE = electrolyzer_eff_AE * 3.6 / 120
    conversion_factor_PEM = electrolyzer_eff_PEM * 3.6 / 120
    for t in range(time_steps):
        wind_power = wind_output[t] * wind_capacity
        pv_power = pv_output[t] * pv_capacity
        model.addConstr(ftl_synthesis_power[t] + ftl_storage_discharge[t] >= ftl_storage_charge[t], name=f'ftl_min_balance_{t}')
        model.addConstr(energy_balance[t] <= battery_storage_capacity, name=f'battery_storage_limit_{t}')
        model.addConstr(battery_charge[t] + battery_discharge[t] <= battery_energy_capacity, name=f'battery_power_limit_{t}')
        model.addConstr(hydrogen_storage_balance[t] <= hydrogen_storage_capacity, name=f'hydrogen_storage_limit_{t}')
        model.addConstr(hydrogen_charge[t] + hydrogen_discharge[t] <= hydrogen_storage_capacity, name=f'hydrogen_power_limit_{t}')
        model.addConstr(wind_power + pv_power + battery_discharge[t] == electrolyzer_power_AE[t] + electrolyzer_power_PEM[t] + ftl_synthesis_power[t] * ftl_electricity_ratio + battery_charge[t] + hydrogen_charge[t] * hydrogen_storage_elec + heat_pump_output[t] / heat_pump_cop + dac_electricity[t] + surplus[t] + co2_comp_elec[t], name=f'power_balance_{t}')
        if t == 0:
            model.addConstr(energy_balance[t] == battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency, name='battery_balance_0')
            model.addConstr(hydrogen_storage_balance[t] == hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t], name='hydrogen_balance_0')
            model.addConstr(thermal_storage_level[t] == thermal_charge[t] * thermal_storage_efficiency - thermal_discharge[t] / thermal_storage_efficiency, name='thermal_balance_0')
            model.addConstr(co2_storage_level[t] == co2_charge[t] - co2_discharge[t], name='co2_storage_balance_0')
        else:
            model.addConstr(energy_balance[t] == energy_balance[t - 1] + battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency, name=f'battery_balance_{t}')
            model.addConstr(hydrogen_storage_balance[t] == hydrogen_storage_balance[t - 1] + hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t], name=f'hydrogen_balance_{t}')
            model.addConstr(thermal_storage_level[t] == thermal_storage_level[t - 1] + thermal_charge[t] * thermal_storage_efficiency - thermal_discharge[t] / thermal_storage_efficiency, name=f'thermal_balance_{t}')
            model.addConstr(co2_storage_level[t] == co2_storage_level[t - 1] + co2_charge[t] - co2_discharge[t], name=f'co2_storage_balance_{t}')
        model.addConstr(electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM + hydrogen_discharge[t] >= ftl_synthesis_power[t] * ftl_hydrogen_ratio + hydrogen_charge[t], name=f'hydrogen_PD_balance_{t}')
        model.addConstr(dac_heat_input[t] == dac_CO2[t] * dac_heat_per_kg, name=f'dac_heat_requirement_{t}')
        model.addConstr(dac_electricity[t] == dac_CO2[t] * dac_elec_per_kg, name=f'dac_elec_requirement_{t}')
        model.addConstr(dac_CO2[t] <= dac_capacity, name=f'dac_capacity_limit_{t}')
        model.addConstr(direct_co2[t] + stored_co2[t] == dac_CO2[t], name=f'co2_split_{t}')
        model.addConstr(stored_co2[t] <= co2_compressor_capacity, name=f'co2_compressor_limit_{t}')
        model.addConstr(co2_comp_elec[t] == stored_co2[t] * co2_compression_energy, name=f'co2_compression_energy_{t}')
        model.addConstr(co2_charge[t] == stored_co2[t], name=f'co2_charge_relation_{t}')
        model.addConstr(heat_pump_output[t] - thermal_charge[t] + thermal_discharge[t] >= dac_heat_input[t], name=f'heat_supply_balance_{t}')
        model.addConstr(thermal_storage_level[t] <= thermal_storage_capacity, name=f'thermal_storage_limit_{t}')
        model.addConstr(co2_storage_level[t] <= co2_storage_capacity, name=f'co2_storage_limit_{t}')
    model.addConstrs((heat_pump_capacity >= heat_pump_output[t] for t in range(time_steps)), name='heat_pump_capacity')
    model.addConstrs((heat_pump_output[t] >= 0.25 * heat_pump_capacity for t in range(168, time_steps)), name='heat_pump_min_output')
    model.addConstrs((electrolyzer_capacity_AE >= electrolyzer_power_AE[t] for t in range(time_steps)), name='electrolyzer_AE_capacity')
    model.addConstrs((electrolyzer_capacity_PEM >= electrolyzer_power_PEM[t] for t in range(time_steps)), name='electrolyzer_PEM_capacity')
    model.addConstrs((electrolyzer_power_AE[t] >= 0.1 * electrolyzer_capacity_AE for t in range(168, time_steps)), name='electrolyzer_AE_min_power')
    model.addConstrs((dac_CO2[t] >= dac_min_load * dac_capacity for t in range(168, time_steps)), name='dac_min_output')
    model.addConstrs((ftl_synthesis_power[t] <= ftl_synthesis_capacity for t in range(time_steps)), name='ftl_synthesis_capacity')
    model.addConstrs((ftl_synthesis_power[t] >= ftl_min_load * ftl_synthesis_capacity for t in range(168, time_steps)), name='ftl_min_output')
    model.addConstrs((direct_co2[t] + co2_discharge[t] >= ftl_synthesis_power[t] * ftl_co2_ratio for t in range(time_steps)), name='co2_hourly_balance')
    model.addConstr(gp.quicksum((direct_co2[t] + co2_discharge[t] for t in range(time_steps))) >= target_ftl_production * ftl_co2_ratio, name='annual_co2_supply_constraint')
    model.addConstr(battery_energy_capacity >= 0.5 * electrolyzer_capacity_AE, name='min_battery_for_AE')
    return model

def create_model_for_product(prod_key: str, wind_output: np.ndarray, pv_output: np.ndarray, wind_cost: float, pv_cost: float, p: dict):
    prod_key = (prod_key or 'methanol').lower()
    if prod_key == 'methanol':
        return optimize_methanol_system(wind_output, pv_output, p['target_methanol_production'], wind_cost, pv_cost, p['battery_energy_cost'], p['battery_storage_cost'], p['battery_charge_efficiency'], p['battery_discharge_efficiency'], p['battery_charge_penalty'], p['battery_discharge_penalty'], p['electrolyzer_cost_AE'], p['electrolyzer_cost_PEM'], p['electrolyzer_eff_AE'], p['electrolyzer_eff_PEM'], p['methanol_synthesis_cost'], p['hydrogen_storage_cost'], p['hydrogen_storage_elec'], p['hydrogen_charge_penalty'], p['hydrogen_storage_efficiency'], p['methanol_storage_cost_param'], p['methanol_charge_penalty'], p['discount_rate'], p['battery_lifetime'], p['wind_lifetime'], p['pv_lifetime'], p['electrolyzer_lifetime_AE'], p['electrolyzer_lifetime_PEM'], p['methanol_synthesis_lifetime'], p['hydrogen_storage_lifetime'], p['methanol_storage_lifetime'], p['heat_pump_cost'], p['heat_pump_cop'], p['heat_pump_lifetime'], p['thermal_storage_cost'], p['thermal_storage_efficiency'], p['thermal_storage_lifetime'], p['dac_cost'], p['dac_elec_per_kg'], p['dac_heat_per_kg'], p['dac_lifetime'], p['sorbent_cost'], p['co2_compressor_cost'], p['co2_compression_energy'], p['co2_compressor_lifetime'], p['co2_storage_cost'], p['co2_storage_lifetime'], p['Flex_up'], p['Flex_mid'], p['Flex_down'], p['Flex_me_up'], p['Flex_me_down'], p['Flex_dac_up'], p['Flex_dac_down'], p['me_min_load'], p['dac_min_load'], p['surplus_penalty'], p['aggregation_mode'])
    if prod_key == 'ftl':
        return optimize_ftl_system(wind_output, pv_output, p['target_ftl_production'], wind_cost, pv_cost, p['battery_energy_cost'], p['battery_storage_cost'], p['battery_charge_efficiency'], p['battery_discharge_efficiency'], p['battery_charge_penalty'], p['battery_discharge_penalty'], p['electrolyzer_cost_AE'], p['electrolyzer_cost_PEM'], p['electrolyzer_eff_AE'], p['electrolyzer_eff_PEM'], p['electrolyzer_lifetime_AE'], p['electrolyzer_lifetime_PEM'], p['ftl_synthesis_cost'], p['ftl_synthesis_lifetime'], p['ftl_hydrogen_ratio'], p['ftl_co2_ratio'], p['ftl_electricity_ratio'], p['hydrogen_storage_cost'], p['hydrogen_storage_elec'], p['hydrogen_charge_penalty'], p['hydrogen_storage_efficiency'], p['hydrogen_storage_lifetime'], p['ftl_storage_cost_param'], p['ftl_storage_lifetime'], p['ftl_charge_penalty'], p['heat_pump_cost'], p['heat_pump_cop'], p['heat_pump_lifetime'], p['thermal_storage_cost'], p['thermal_storage_efficiency'], p['thermal_storage_lifetime'], p['dac_cost'], p['dac_elec_per_kg'], p['dac_heat_per_kg'], p['dac_lifetime'], p['sorbent_cost'], p['co2_compressor_cost'], p['co2_compression_energy'], p['co2_compressor_lifetime'], p['co2_storage_cost'], p['co2_storage_lifetime'], p['discount_rate'], p['battery_lifetime'], p['wind_lifetime'], p['pv_lifetime'], p['Flex_up'], p['Flex_mid'], p['Flex_down'], p['Flex_ftl_up'], p['Flex_ftl_down'], p['Flex_dac_up'], p['Flex_dac_down'], p['ftl_min_load'], p['dac_min_load'], p['surplus_penalty'], p['aggregation_mode'])
    if prod_key == 'ammonia':
        return optimize_ammonia_system(wind_output, pv_output, p['target_ammonia_production'], wind_cost, pv_cost, p['battery_energy_cost'], p['battery_storage_cost'], p['battery_charge_efficiency'], p['battery_discharge_efficiency'], p['battery_charge_penalty'], p['battery_discharge_penalty'], p['electrolyzer_cost_AE'], p['electrolyzer_cost_PEM'], p['electrolyzer_eff_AE'], p['electrolyzer_eff_PEM'], p['ammonia_synthesis_cost'], p['hydrogen_storage_cost'], p['hydrogen_storage_elec'], p['hydrogen_charge_penalty'], p['hydrogen_storage_efficiency'], p['ammonia_storage_cost_param'], p['discount_rate'], p['battery_lifetime'], p['wind_lifetime'], p['pv_lifetime'], p['electrolyzer_lifetime_AE'], p['electrolyzer_lifetime_PEM'], p['ammonia_synthesis_lifetime'], p['hydrogen_storage_lifetime'], p['ammonia_storage_lifetime'], p['Flex_up'], p['Flex_mid'], p['Flex_down'], p['Flex_am_up'], p['Flex_am_down'], p['am_min_load'], p['surplus_penalty'], p['aggregation_mode'])
    raise ValueError(f'Unsupported product: {prod_key}')
