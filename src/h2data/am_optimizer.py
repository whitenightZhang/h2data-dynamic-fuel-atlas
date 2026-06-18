import xarray as xr
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import Model, GRB

# =============================================================================
# 函数: 合成氨系统优化
# =============================================================================
def optimize_ammonia_system(
    wind_output,
    pv_output,
    target_ammonia_production,
    wind_cost,
    pv_cost,
    battery_energy_cost,
    battery_storage_cost,
    battery_charge_efficiency,
    battery_discharge_efficiency,
    battery_charge_penalty,
    battery_discharge_penalty,
    electrolyzer_cost_AE,
    electrolyzer_cost_PEM,
    electrolyzer_eff_AE,
    electrolyzer_eff_PEM,
    ammonia_synthesis_cost,
    hydrogen_storage_cost,
    hydrogen_storage_elec,
    hydrogen_charge_penalty,
    hydrogen_storage_efficiency,
    ammonia_storage_cost_param,
    discount_rate,
    battery_lifetime,
    wind_lifetime,
    pv_lifetime,
    electrolyzer_lifetime_AE,
    electrolyzer_lifetime_PEM,
    ammonia_synthesis_lifetime,
    hydrogen_storage_lifetime,
    ammonia_storage_lifetime,
    Flex_up,
    Flex_mid,
    Flex_down,
    surplus_penalty,
    aggregation_mode
):
    # —————— 年化成本与运维 ——————
    wind_om                = wind_cost * 0.03
    pv_om                  = pv_cost * 0.03
    battery_energy_om      = battery_energy_cost * 0.03
    battery_storage_om     = battery_storage_cost * 0.03
    electrolyzer_om_AE     = electrolyzer_cost_AE * 0.03
    electrolyzer_om_PEM    = electrolyzer_cost_PEM * 0.03
    ammonia_synthesis_om   = ammonia_synthesis_cost * 0.03
    hydrogen_storage_om    = hydrogen_storage_cost * 0.03
    ammonia_storage_om     = ammonia_storage_cost_param * 0.03

    wind_annual_cost           = wind_cost * discount_rate / (1 - (1+discount_rate)**-wind_lifetime)     + wind_om
    pv_annual_cost             = pv_cost   * discount_rate / (1 - (1+discount_rate)**-pv_lifetime)       + pv_om
    battery_energy_annual_cost = battery_energy_cost  * discount_rate / (1 - (1+discount_rate)**-battery_lifetime) + battery_energy_om
    battery_storage_annual_cost= battery_storage_cost * discount_rate / (1 - (1+discount_rate)**-battery_lifetime) + battery_storage_om
    electrolyzer_annual_cost_AE= electrolyzer_cost_AE  * discount_rate / (1 - (1+discount_rate)**-electrolyzer_lifetime_AE) + electrolyzer_om_AE
    electrolyzer_annual_cost_PEM=electrolyzer_cost_PEM * discount_rate / (1 - (1+discount_rate)**-electrolyzer_lifetime_PEM) + electrolyzer_om_PEM
    ammonia_synthesis_annual_cost=ammonia_synthesis_cost * discount_rate / (1 - (1+discount_rate)**-ammonia_synthesis_lifetime) + ammonia_synthesis_om
    hydrogen_storage_annual_cost= hydrogen_storage_cost * discount_rate / (1 - (1+discount_rate)**-hydrogen_storage_lifetime) + hydrogen_storage_om
    ammonia_storage_annual_cost = ammonia_storage_cost_param * discount_rate / (1 - (1+discount_rate)**-ammonia_storage_lifetime) + ammonia_storage_om

    # 逐小时需求
    hourly_ammonia_demand = target_ammonia_production / 8760
    ammonia_electricity_ratio = 0.303
    ammonia_hydrogen_ratio   = 0.18

    # —————— 建模 ——————
    time_steps = 8760
    model = Model("AmmoniaOptimization_SplitBattery_AEPem")
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', 1000)
    model.setParam('Method', 2); model.setParam('Crossover', 0)
    model.setParam('BarConvTol', 1e-6); model.setParam('Threads', 1)
    model.setParam('Presolve', 1); model.setParam('BarHomogeneous', 1)

    # 决策变量
    wind_capacity      = model.addVar(lb=0, name="wind_capacity")
    pv_capacity        = model.addVar(lb=0, name="pv_capacity")
    battery_energy_capacity= model.addVar(lb=0, name="battery_energy_capacity")
    battery_storage_capacity= model.addVar(lb=0, name="battery_storage_capacity")
    electrolyzer_capacity_AE= model.addVar(lb=0, name="electrolyzer_capacity_AE")
    electrolyzer_capacity_PEM=model.addVar(lb=0, name="electrolyzer_capacity_PEM")
    ammonia_synthesis_capacity=model.addVar(lb=0, name="ammonia_synthesis_capacity")
    hydrogen_storage_capacity =model.addVar(lb=0, name="hydrogen_storage_capacity")
    ammonia_storage_capacity  =model.addVar(lb=0, name="ammonia_storage_capacity")

    # 时步变量
    energy_balance           = model.addVars(time_steps, lb=0, name="energy_balance")
    battery_charge          = model.addVars(time_steps, lb=0, name="battery_charge")
    battery_discharge       = model.addVars(time_steps, lb=0, name="battery_discharge")
    electrolyzer_power_AE   = model.addVars(time_steps, lb=0, name="electrolyzer_power_AE")
    electrolyzer_power_PEM  = model.addVars(time_steps, lb=0, name="electrolyzer_power_PEM")
    ammonia_synthesis_power = model.addVars(time_steps, lb=0, name="ammonia_synthesis_power")
    surplus                 = model.addVars(time_steps, lb=0, name="surplus")
    hydrogen_storage_balance= model.addVars(time_steps, lb=0, name="hydrogen_storage_balance")
    hydrogen_charge         = model.addVars(time_steps, lb=0, name="hydrogen_charge")
    hydrogen_discharge      = model.addVars(time_steps, lb=0, name="hydrogen_discharge")
    ammonia_storage_balance = model.addVars(time_steps, lb=0, name="ammonia_storage_balance")
    ammonia_storage_charge  = model.addVars(time_steps, lb=0, name="ammonia_storage_charge")
    ammonia_storage_discharge=model.addVars(time_steps, lb=0, name="ammonia_storage_discharge")

    # 目标函数
    model.setObjective(
        wind_annual_cost * wind_capacity +
        pv_annual_cost * pv_capacity +
        battery_energy_annual_cost * battery_energy_capacity +
        battery_storage_annual_cost * battery_storage_capacity +
        electrolyzer_annual_cost_AE * electrolyzer_capacity_AE +
        electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM +
        ammonia_synthesis_annual_cost * ammonia_synthesis_capacity +
        hydrogen_storage_annual_cost * hydrogen_storage_capacity +
        ammonia_storage_annual_cost * ammonia_storage_capacity +
        surplus_penalty * gp.quicksum(surplus[t] for t in range(time_steps)) +
        battery_charge_penalty * gp.quicksum(battery_charge[t] for t in range(time_steps)) +
        battery_discharge_penalty * gp.quicksum(battery_discharge[t] for t in range(time_steps)) +
        hydrogen_charge_penalty * gp.quicksum(hydrogen_charge[t] for t in range(time_steps)),
        GRB.MINIMIZE
    )

# =============================================================================
# 5. 约束条件
# =============================================================================
# 5.1 逐时灵活性
    for t in range(1, time_steps):
        model.addConstr(electrolyzer_power_AE[t]   - electrolyzer_power_AE[t-1]   <= Flex_down * electrolyzer_capacity_AE,
                        name=f"electrolyzer_AE_ramp_up_{t}")
        model.addConstr(electrolyzer_power_AE[t]   - electrolyzer_power_AE[t-1]   >= -Flex_down * electrolyzer_capacity_AE,
                        name=f"electrolyzer_AE_ramp_down_{t}")
        model.addConstr(ammonia_synthesis_power[t] - ammonia_synthesis_power[t-1] <= Flex_mid  * ammonia_synthesis_capacity,
                        name=f"ammonia_ramp_up_{t}")
        model.addConstr(ammonia_synthesis_power[t] - ammonia_synthesis_power[t-1] >= -Flex_down * ammonia_synthesis_capacity,
                        name=f"ammonia_ramp_down_{t}")

    # 5.2 合成氨供需平衡约束（含氨储存充放，支持不同时间聚合尺度）
    start_index = 168  # 避免初始不稳定阶段
    if aggregation_mode == "hourly":
        for t in range(start_index, time_steps):
            model.addConstr(
                ammonia_synthesis_power[t] + ammonia_storage_discharge[t] ==
                hourly_ammonia_demand + ammonia_storage_charge[t],
                name=f"ammonia_balance_{t}"
            )
    elif aggregation_mode == "3hourly":
        interval = 3
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum(ammonia_synthesis_power[t] for t in range(t_start, t_end)) +
                gp.quicksum(ammonia_storage_discharge[t] for t in range(t_start, t_end))
                ==
                hourly_ammonia_demand * interval +
                gp.quicksum(ammonia_storage_charge[t] for t in range(t_start, t_end)),
                name=f"ammonia_balance_3hourly_{i}"
            )
    elif aggregation_mode == "daily":
        interval = 24
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum(ammonia_synthesis_power[t] for t in range(t_start, t_end)) +
                gp.quicksum(ammonia_storage_discharge[t] for t in range(t_start, t_end))
                >=
                0.8 * hourly_ammonia_demand * interval +
                gp.quicksum(ammonia_storage_charge[t] for t in range(t_start, t_end)),
                name=f"ammonia_balance_daily_{i}"
            )
    elif aggregation_mode == "weekly":
        interval = 168  # 一周168小时
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum(ammonia_synthesis_power[t] for t in range(t_start, t_end)) +
                gp.quicksum(ammonia_storage_discharge[t] for t in range(t_start, t_end))
                ==
                hourly_ammonia_demand * interval +
                gp.quicksum(ammonia_storage_charge[t] for t in range(t_start, t_end)),
                name=f"ammonia_balance_weekly_{i}"
            )
    elif aggregation_mode == "monthly":
        # 近似每月730小时（可根据实际情况调整）
        interval = 730
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum(ammonia_synthesis_power[t] for t in range(t_start, t_end)) +
                gp.quicksum(ammonia_storage_discharge[t] for t in range(t_start, t_end))
                ==
                hourly_ammonia_demand * interval +
                gp.quicksum(ammonia_storage_charge[t] for t in range(t_start, t_end)),
                name=f"ammonia_balance_monthly_{i}"
            )
    elif aggregation_mode == "annual":
        model.addConstr(
            gp.quicksum(ammonia_synthesis_power[t] for t in range(start_index, time_steps)) +
            gp.quicksum(ammonia_storage_discharge[t] for t in range(start_index, time_steps))
            ==
            hourly_ammonia_demand * (time_steps - start_index) +
            gp.quicksum(ammonia_storage_charge[t] for t in range(start_index, time_steps)),
            name="ammonia_balance_annual"
        )
    else:
        raise ValueError("Unsupported aggregation_mode value!")

    # 附加：年度合成氨生产总量约束
    model.addConstr(
        gp.quicksum(ammonia_synthesis_power[t] for t in range(time_steps)) >= hourly_ammonia_demand * 8760,
        name="annual_ammonia_production_constraint"
    )

    # 5.3 电力与存储平衡
    conversion_factor_AE  = electrolyzer_eff_AE  * 3.6 / 120
    conversion_factor_PEM = electrolyzer_eff_PEM * 3.6 / 120

    for t in range(time_steps):
        wind_power = wind_output[t] * wind_capacity
        pv_power   = pv_output[t]   * pv_capacity

        # 电池储能约束
        model.addConstr(energy_balance[t] <= battery_storage_capacity,
                        name=f"energy_balance_limit_{t}")
        model.addConstr(battery_charge[t] + battery_discharge[t] <= battery_energy_capacity,
                        name=f"battery_charge_discharge_limit_{t}")

        # 动态电池平衡
        if t == 0:
            model.addConstr(
                energy_balance[t] == battery_charge[t] * battery_charge_efficiency
                                    - battery_discharge[t] / battery_discharge_efficiency,
                name=f"battery_balance_{t}" )
        else:
            model.addConstr(
                energy_balance[t] == energy_balance[t-1] +
                                    battery_charge[t] * battery_charge_efficiency
                                  - battery_discharge[t] / battery_discharge_efficiency,
                name=f"battery_balance_{t}" )

        # 氢气存储约束
        model.addConstr(hydrogen_storage_balance[t] <= hydrogen_storage_capacity,
                        name=f"hydrogen_storage_capacity_limit_{t}")
        model.addConstr(hydrogen_charge[t] + hydrogen_discharge[t] <= hydrogen_storage_capacity,
                        name=f"hydrogen_charge_limit_{t}")

        # 氢气存储动态平衡
        if t == 0:
            model.addConstr(
                hydrogen_storage_balance[t] == hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t],
                name=f"hydrogen_balance_{t}"
            )
        else:
            model.addConstr(
                hydrogen_storage_balance[t] == hydrogen_storage_balance[t-1] + hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t],
                name=f"hydrogen_balance_{t}"
            )

        # 氢气供需平衡：电解槽产氢（转换系数 3.6/120）加上氢气释放，
        # 需满足合成氨生产所需的氢气（按氢消耗比）加上充氢量

        # 氨储存平衡
        model.addConstr(ammonia_storage_balance[t] == (ammonia_storage_balance[t-1] if t>0 else ammonia_storage_charge[0])
                                  + ammonia_storage_charge[t] - ammonia_storage_discharge[t],
                        name=f"ammonia_storage_balance_{t}")
        model.addConstr(ammonia_storage_balance[t] <= ammonia_storage_capacity,
                        name=f"ammonia_storage_capacity_limit_{t}")

        # 氨储存：确保合成氨生产加上储存放出不少于储入量
        model.addConstr(
            ammonia_synthesis_power[t] + ammonia_storage_discharge[t] >= ammonia_storage_charge[t],
            name=f"ammonia_min_balance_{t}"
        )

        # 电力平衡
        model.addConstr(
            wind_power + pv_power + battery_discharge[t] ==
            electrolyzer_power_AE[t] + electrolyzer_power_PEM[t] +
            battery_charge[t] + hydrogen_charge[t] * hydrogen_storage_elec +
            ammonia_synthesis_power[t] * ammonia_electricity_ratio + surplus[t],
            name=f"power_balance_{t}" )

        # 氢气供需平衡
        model.addConstr(
            electrolyzer_power_AE[t] * conversion_factor_AE +
            electrolyzer_power_PEM[t] * conversion_factor_PEM +
            hydrogen_discharge[t] >=
            ammonia_synthesis_power[t] * ammonia_hydrogen_ratio + hydrogen_charge[t],
            name=f"hydrogen_PD_balance_{t}" )

    # 5.4 容量与最小运行
    model.addConstrs((electrolyzer_capacity_AE >= electrolyzer_power_AE[t] for t in range(time_steps)), name="electrolyzer_AE_capacity")
    model.addConstrs((electrolyzer_capacity_PEM >= electrolyzer_power_PEM[t] for t in range(time_steps)), name="electrolyzer_PEM_capacity")
    model.addConstrs((electrolyzer_power_AE[t] >= 0.1 * electrolyzer_capacity_AE for t in range(start_index, time_steps)), name="electrolyzer_AE_min")
    model.addConstrs((ammonia_synthesis_capacity >= ammonia_synthesis_power[t] for t in range(time_steps)), name="ammonia_capacity")
    model.addConstrs((ammonia_synthesis_power[t] >= 0.2 * ammonia_synthesis_capacity for t in range(start_index, time_steps)), name="ammonia_min")

    # AE电解需配备电池能量：
    model.addConstr(battery_energy_capacity >= 0.5 * electrolyzer_capacity_AE, name="min_battery_for_AE")


    model.optimize()

    # 返回结果
    if model.status == GRB.OPTIMAL:
        total_ammonia = sum(ammonia_synthesis_power[t].x for t in range(time_steps))
        total_hydrogen_production = sum((electrolyzer_power_AE[t].x * conversion_factor_AE + electrolyzer_power_PEM[t].x * conversion_factor_PEM) for t in range(time_steps))
        total_elec_consumed = sum(electrolyzer_power_AE[t].x + electrolyzer_power_PEM[t].x for t in range(time_steps))
        installed_elec_cap = electrolyzer_capacity_AE.x + electrolyzer_capacity_PEM.x
        electrolyzer_utilization = total_elec_consumed / (installed_elec_cap * 8760) * 100
        # 氢气储存所用电量（kWh）
        hydrogen_storage_kwh = sum(hydrogen_charge[t].x * hydrogen_storage_elec for t in range(time_steps))
        
        # 合成氨装置利用率（%）
        ammonia_utilization = total_ammonia / (ammonia_synthesis_capacity.x * 8760) * 100
        
        # 年度总发电（kWh）
        total_Elec_generation = (
            sum(wind_output[t] for t in range(time_steps)) * wind_capacity.x +
            sum(pv_output[t]   for t in range(time_steps)) * pv_capacity.x -
            sum(surplus[t].x    for t in range(time_steps))
        )
        
        # 平准化电价（$/kWh）
        levelized_Elec_cost = (
            wind_annual_cost * wind_capacity.x +
            pv_annual_cost   * pv_capacity.x +
            battery_energy_annual_cost  * battery_energy_capacity.x +
            battery_storage_annual_cost * battery_storage_capacity.x +
            battery_charge_penalty   * sum(battery_charge[t].x   for t in range(time_steps)) +
            battery_discharge_penalty* sum(battery_discharge[t].x for t in range(time_steps))
        ) / total_Elec_generation
        
        # 平准化制氢成本 ($/kgH2)
        levelized_H2_cost = (
            electrolyzer_annual_cost_AE  * electrolyzer_capacity_AE.x +
            electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM.x +
            levelized_Elec_cost * total_elec_consumed +
            levelized_Elec_cost * hydrogen_storage_kwh +
            hydrogen_storage_annual_cost * hydrogen_storage_capacity.x
        ) / total_hydrogen_production

        results = {
            "wind_capacity": wind_capacity.x,
            "pv_capacity": pv_capacity.x,
            "battery_energy_capacity": battery_energy_capacity.x,
            "battery_storage_capacity": battery_storage_capacity.x,
            "electrolyzer_capacity_AE": electrolyzer_capacity_AE.x,
            "electrolyzer_capacity_PEM": electrolyzer_capacity_PEM.x,
            "ammonia_synthesis_capacity": ammonia_synthesis_capacity.x * 8760 / 1000,
            "hydrogen_storage_capacity": hydrogen_storage_capacity.x,
            "ammonia_storage_capacity": ammonia_storage_capacity.x,
            "total_ammonia_production_kg": total_ammonia,
            "total_hydrogen_production_kg": total_hydrogen_production,
            "total_elec_generation_kwh": total_Elec_generation,
            "electrolyzer_utilization_percent": electrolyzer_utilization,
            "ammonia_utilization_percent": ammonia_utilization,
            "levelized_elec_cost_per_kwh": levelized_Elec_cost,
            "levelized_h2_cost_per_kg": levelized_H2_cost,
            "levelized_ammonia_cost_per_ton": model.objVal / total_ammonia * 1000
        }
    else:
        results = {k: 0 for k in [
            "wind_capacity","pv_capacity","battery_energy_capacity","battery_storage_capacity",
            "electrolyzer_capacity_AE","electrolyzer_capacity_PEM","ammonia_synthesis_capacity",
            "hydrogen_storage_capacity","ammonia_storage_capacity","total_ammonia_production_kg",
            "total_hydrogen_production_kg","total_elec_generation_kwh",
            "electrolyzer_utilization_percent","ammonia_utilization_percent",
            "levelized_elec_cost_per_kwh","levelized_h2_cost_per_kg",
            "levelized_ammonia_cost_per_ton"
        ]}

    env = model._env  
    model.dispose()  
    env.dispose()
    return results
