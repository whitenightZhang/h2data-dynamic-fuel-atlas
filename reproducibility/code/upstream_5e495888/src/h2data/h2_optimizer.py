import xarray as xr
import numpy as np
import pandas as pd
import random
import gurobipy as gp
from gurobipy import Model, GRB

def optimize_hydrogen_system(wind_output,
    pv_output,
    target_hydrogen_production,  # kg/年，即10吨/年
    wind_cost,                     # $/kW
    pv_cost,                       # $/kW
    battery_energy_cost,                  # $/kW
    battery_storage_cost,                  # $/kW
    battery_charge_efficiency,
    battery_discharge_efficiency,
    battery_charge_penalty,      # $/kWh
    battery_discharge_penalty,     # $/kWh
    electrolyzer_cost_AE,          # $/kW
    electrolyzer_cost_PEM,         # $/kW
    electrolyzer_eff_AE,              # 效率
    electrolyzer_eff_PEM,              # 效率
    hydrogen_storage_cost,        # $/kg
    hydrogen_charge_penalty,     # $/kgH2
    hydrogen_storage_efficiency,
    hydrogen_storage_elec,        # kWh/kg H2
    discount_rate,
    battery_lifetime,
    wind_lifetime,
    pv_lifetime,
    electrolyzer_lifetime_AE,
    electrolyzer_lifetime_PEM,
    hydrogen_storage_lifetime,                   
    Flex_mid,                    
    surplus_penalty,
    aggregation_mode        # 可选："hourly"、"3hourly"、"daily"、"weekly"、"monthly"、"annual"
):
    # ---------------------------
    # 1. 数据加载：读取光伏和风电输出曲线
    # ---------------------------

    # 注：CSV第一列为PV输出，第二列为风电输出
    pv_output   = pv_output   
    wind_output = wind_output   
    
    # ---------------------------
    # 2. 参数计算
    # ---------------------------
    # 2.1 运维费用（OM）：取设备成本的3%
    battery_energy_om = battery_energy_cost * 0.03 
    battery_storage_om = battery_storage_cost * 0.03 
    electrolyzer_om_AE = electrolyzer_cost_AE * 0.03
    electrolyzer_om_PEM = electrolyzer_cost_PEM * 0.03
    hydrogen_storage_om = hydrogen_storage_cost * 0.03

    # 2.2 年化成本计算
    wind_annual_cost = wind_cost * discount_rate / (1 - (1 + discount_rate) ** -wind_lifetime) + wind_cost * 0.03
    pv_annual_cost = pv_cost * discount_rate / (1 - (1 + discount_rate) ** -pv_lifetime) + pv_cost * 0.03
    battery_energy_annual_cost = battery_energy_cost * discount_rate / (1 - (1 + discount_rate) ** -battery_lifetime) + battery_energy_om
    battery_storage_annual_cost = battery_storage_cost * discount_rate / (1 - (1 + discount_rate) ** -battery_lifetime) + battery_storage_om
    electrolyzer_annual_cost_AE = electrolyzer_cost_AE * discount_rate / (1 - (1 + discount_rate) ** -electrolyzer_lifetime_AE) + electrolyzer_om_AE
    electrolyzer_annual_cost_PEM = electrolyzer_cost_PEM * discount_rate / (1 - (1 + discount_rate) ** -electrolyzer_lifetime_PEM) + electrolyzer_om_PEM
    hydrogen_storage_annual_cost = hydrogen_storage_cost * discount_rate / (1 - (1 + discount_rate) ** -hydrogen_storage_lifetime) + hydrogen_storage_om

    # 2.3 目标制氢参数
    hourly_hydrogen_demand = target_hydrogen_production / 8760

    # ---------------------------
    # 3. 模型构建与变量定义
    # ---------------------------
    model = Model("HydrogenProductionOptimization")
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', 100)
    model.setParam('MIPFocus', 1)
    model.setParam('MIPGap', 0.1)
    model.setParam('Method', 2)
    model.setParam('Crossover', 0)

    time_steps = 8760

    # 3.1 装机设备决策变量
    wind_capacity = model.addVar(lb=0, name="wind_capacity")
    pv_capacity   = model.addVar(lb=0, name="pv_capacity")
    battery_energy_capacity = model.addVar(lb=0, name="battery_energy_capacity")
    battery_storage_capacity = model.addVar(lb=0, name="battery_storage_capacity")
    hydrogen_storage_capacity = model.addVar(lb=0, name="hydrogen_storage_capacity")

    # 分别定义 AE 与 PEM 型电解槽装机决策变量
    electrolyzer_capacity_AE = model.addVar(lb=0, name="electrolyzer_capacity_AE")
    electrolyzer_capacity_PEM = model.addVar(lb=0, name="electrolyzer_capacity_PEM")

    # 3.2 时间步相关变量（共8760小时）
    # 电解槽出力变量
    electrolyzer_power_AE = model.addVars(time_steps, lb=0, name="electrolyzer_power_AE")
    electrolyzer_power_PEM = model.addVars(time_steps, lb=0, name="electrolyzer_power_PEM")

    # 电池储能相关变量
    energy_balance = model.addVars(time_steps, lb=0, name="energy_balance")
    battery_charge = model.addVars(time_steps, lb=0, name="battery_charge")
    battery_discharge = model.addVars(time_steps, lb=0, name="battery_discharge")

    # 多余电量变量（未利用电量）
    surplus = model.addVars(time_steps, lb=0, name="surplus")

    # 氢气存储相关变量
    hydrogen_storage_balance = model.addVars(time_steps, lb=0, name="hydrogen_storage_balance")
    hydrogen_charge = model.addVars(time_steps, lb=0, name="hydrogen_charge")
    hydrogen_discharge = model.addVars(time_steps, lb=0, name="hydrogen_discharge")

    # =============================================================================
    # 4. 目标函数
    # =============================================================================
    model.setObjective(
        wind_annual_cost * wind_capacity +
        pv_annual_cost * pv_capacity +
        battery_energy_annual_cost * battery_energy_capacity +
        battery_storage_annual_cost * battery_storage_capacity +
        electrolyzer_annual_cost_AE * electrolyzer_capacity_AE + 
        electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM +
        hydrogen_storage_annual_cost * hydrogen_storage_capacity +
        surplus_penalty * gp.quicksum(surplus[t] for t in range(time_steps)) +
        battery_charge_penalty * gp.quicksum(battery_charge[t] for t in range(time_steps)) +
        battery_discharge_penalty * gp.quicksum(battery_discharge[t] for t in range(time_steps)) +
        hydrogen_charge_penalty * gp.quicksum(hydrogen_charge[t] for t in range(time_steps)),
        GRB.MINIMIZE
    )

    # =============================================================================
    # 5. 约束条件
    # =============================================================================

    # 5.1 逐时设备灵活性约束（仅针对 AE 型电解槽，限制功率变化）
    for t in range(1, time_steps):
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t-1] <= Flex_mid * electrolyzer_capacity_AE,
                        name=f"electrolyzer_AE_ramp_up_{t}")
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t-1] >= -Flex_mid * electrolyzer_capacity_AE,
                        name=f"electrolyzer_AE_ramp_down_{t}")

    # 5.2 电力平衡约束（逐时）
    for t in range(time_steps):
        wind_power = wind_output[t] * wind_capacity
        pv_power = pv_output[t] * pv_capacity
        model.addConstr(
            wind_power + pv_power + battery_discharge[t] ==
            (electrolyzer_power_AE[t] + electrolyzer_power_PEM[t]) +
            battery_charge[t] + hydrogen_charge[t] * hydrogen_storage_elec + surplus[t],
            name=f"power_balance_{t}"
        )
        # 电池储能与充放电限制
        model.addConstr(energy_balance[t] <= battery_storage_capacity,
                        name=f"energy_balance_limit_{t}")
        model.addConstr(battery_charge[t] + battery_discharge[t] <= battery_energy_capacity,
                        name=f"battery_charge_discharge_limit_{t}")
        # 电池动态平衡
        if t == 0:
            model.addConstr(
                energy_balance[t] == battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency,
                name=f"battery_balance_{t}"
            )
        else:
            model.addConstr(
                energy_balance[t] == energy_balance[t-1] + battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency,
                name=f"battery_balance_{t}"
            )

    # 5.3 氢气供需平衡约束（支持不同时间聚合尺度）
    # 转换系数：电解槽产氢量 = 出力 * electrolyzer_eff * 3.6/120
    conversion_factor_AE = electrolyzer_eff_AE * 3.6 / 120
    conversion_factor_PEM = electrolyzer_eff_PEM * 3.6 / 120

    if aggregation_mode == "hourly":
        for t in range(168, time_steps):
            model.addConstr( 
                (electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM) + hydrogen_discharge[t] >=
                0.8 * hourly_hydrogen_demand + hydrogen_charge[t],
                name=f"hydrogen_balance_{t}"
            )
    elif aggregation_mode == "3hourly":
        interval = 3
        start_index = 168
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum((electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM) for t in range(t_start, t_end)) +
                gp.quicksum(hydrogen_discharge[t] for t in range(t_start, t_end))
                >= hourly_hydrogen_demand * interval +
                gp.quicksum(hydrogen_charge[t] for t in range(t_start, t_end)),
                name=f"hydrogen_balance_3hourly_{i}"
            )
    elif aggregation_mode == "daily":
        interval = 24
        start_index = 168
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum((electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM) for t in range(t_start, t_end)) +
                gp.quicksum(hydrogen_discharge[t] for t in range(t_start, t_end))
                >= 0.8 * hourly_hydrogen_demand * interval +
                gp.quicksum(hydrogen_charge[t] for t in range(t_start, t_end)),
                name=f"hydrogen_balance_daily_{i}"
            )
    elif aggregation_mode == "weekly":
        interval = 168  # 1周 = 168小时
        start_index = 168
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum((electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM) for t in range(t_start, t_end)) +
                gp.quicksum(hydrogen_discharge[t] for t in range(t_start, t_end))
                >= hourly_hydrogen_demand * interval +
                gp.quicksum(hydrogen_charge[t] for t in range(t_start, t_end)),
                name=f"hydrogen_balance_weekly_{i}"
            )
    elif aggregation_mode == "monthly":
        interval = 730
        start_index = 168
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum((electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM) for t in range(t_start, t_end)) +
                gp.quicksum(hydrogen_discharge[t] for t in range(t_start, t_end))
                >= hourly_hydrogen_demand * interval +
                gp.quicksum(hydrogen_charge[t] for t in range(t_start, t_end)),
                name=f"hydrogen_balance_monthly_{i}"
            )
    elif aggregation_mode == "annual":
        model.addConstr(
            gp.quicksum((electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM) for t in range(168, time_steps)) +
            gp.quicksum(hydrogen_discharge[t] for t in range(168, time_steps))
            >= hourly_hydrogen_demand * (time_steps - 168) +
            gp.quicksum(hydrogen_charge[t] for t in range(168, time_steps)),
            name="hydrogen_balance_annual"
        )
    else:
        raise ValueError("Unsupported aggregation_mode value!")

    # 附加：年生产总量约束
    model.addConstr(
        gp.quicksum((electrolyzer_power_AE[t] * conversion_factor_AE + electrolyzer_power_PEM[t] * conversion_factor_PEM) for t in range(time_steps)) >= hourly_hydrogen_demand * 8760,
        name="annual_hydrogen_production_constraint"
    )

    # 5.4 氢气储存动态平衡及容量限制
    model.addConstr(hydrogen_storage_balance[0] == hydrogen_charge[0] - hydrogen_discharge[0],
                    name="hydrogen_storage_balance_0")
    for t in range(1, time_steps):
        model.addConstr(
            hydrogen_storage_balance[t] == hydrogen_storage_balance[t-1] + hydrogen_charge[t] - hydrogen_discharge[t],
            name=f"hydrogen_storage_balance_{t}"
        )
        model.addConstr(hydrogen_storage_balance[t] <= hydrogen_storage_capacity,
                        name=f"hydrogen_storage_level_limit_{t}")
        model.addConstr(hydrogen_charge[t] + hydrogen_discharge[t] <= hydrogen_storage_capacity,
                        name=f"hydrogen_charge_limit_{t}")

    # 5.5 装机容量约束
    model.addConstrs((electrolyzer_capacity_AE >= electrolyzer_power_AE[t] for t in range(time_steps)),
                     name="electrolyzer_AE_capacity_constraint")
    model.addConstrs((electrolyzer_capacity_PEM >= electrolyzer_power_PEM[t] for t in range(time_steps)),
                     name="electrolyzer_PEM_capacity_constraint")
    model.addConstrs((electrolyzer_power_AE[t] >= 0.1 * electrolyzer_capacity_AE for t in range(168, time_steps)),
                     name="electrolyzer_AE_power_constraint")

    # 5.6 附加：要求AE型电解槽必须配备至少0.5倍（约10%）的储能电池
    model.addConstr(battery_energy_capacity >= 0.5 * electrolyzer_capacity_AE,
                    name="min_battery_for_AE")

    # ---------------------------
    # 6. 求解模型
    # ---------------------------
    model.optimize()

    # ---------------------------
    # 7. 结果输出（以字典形式返回）
    # ---------------------------
    if model.status == GRB.OPTIMAL:
        total_hydrogen_production = sum((electrolyzer_power_AE[t].x * conversion_factor_AE+ electrolyzer_power_PEM[t].x * conversion_factor_PEM)  for t in range(time_steps))
        hydrogen_production_kwh = sum((electrolyzer_power_AE[t].x * electrolyzer_eff_AE + electrolyzer_power_PEM[t].x * electrolyzer_eff_PEM) for t in range(time_steps))
        hydrogen_electricity_demand =  sum(electrolyzer_power_AE[t].x  + electrolyzer_power_PEM[t].x  for t in range(time_steps))
        electrolyzer_utilization_hours = hydrogen_production_kwh / ((electrolyzer_capacity_AE.x * electrolyzer_eff_AE + electrolyzer_capacity_PEM.x * electrolyzer_eff_PEM) * 8760) * 100
        hydrogen_storage_kwh = sum(hydrogen_charge[t].x * hydrogen_storage_elec for t in range(time_steps))
        total_Elec_generation = (sum(wind_output[t] for t in range(time_steps)) * wind_capacity.x +
                                 sum(pv_output[t] for t in range(time_steps)) * pv_capacity.x -
                                 sum(surplus[t].x for t in range(time_steps)))

        levelized_Elec_cost = (
            wind_annual_cost * wind_capacity.x +
            pv_annual_cost * pv_capacity.x +
            battery_energy_annual_cost * battery_energy_capacity.x +
            battery_storage_annual_cost * battery_storage_capacity.x +
            battery_charge_penalty * sum(battery_charge[t].x for t in range(time_steps)) +
            battery_discharge_penalty * sum(battery_discharge[t].x for t in range(time_steps))
        ) / total_Elec_generation

        levelized_H2_cost = (
            electrolyzer_annual_cost_AE * electrolyzer_capacity_AE.x +
            electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM.x +
            levelized_Elec_cost * hydrogen_electricity_demand +
            levelized_Elec_cost * hydrogen_storage_kwh +
            hydrogen_storage_annual_cost * hydrogen_storage_capacity.x
        ) / (hydrogen_production_kwh / 33.3)

        results = {
            "wind_capacity": wind_capacity.x,
            "pv_capacity": pv_capacity.x,
            "battery_energy_capacity": battery_energy_capacity.x,
            "battery_storage_capacity": battery_storage_capacity.x,
            "hydrogen_storage_capacity": hydrogen_storage_capacity.x,
            "electrolyzer_capacity_AE": electrolyzer_capacity_AE.x,
            "electrolyzer_capacity_PEM": electrolyzer_capacity_PEM.x,
            "total_hydrogen_production_kg": total_hydrogen_production,
            "electrolyzer_utilization_hours_percent": electrolyzer_utilization_hours,
            "levelized_Elec_cost_per_kWh": levelized_Elec_cost,
            "levelized_H2_cost_per_kgH2": levelized_H2_cost,
            "levelized_hydrogen_production_cost_per_kg": model.objVal / total_hydrogen_production
        }
    else:
        results = {
            "wind_capacity": 0,
            "pv_capacity": 0,
            "battery_energy_capacity": 0,
            "battery_storage_capacity": 0,
            "hydrogen_storage_capacity": 0,
            "electrolyzer_capacity_AE": 0,
            "electrolyzer_capacity_PEM": 0,
            "total_hydrogen_production_kg": 0,
            "electrolyzer_utilization_hours_percent": 0,
            "levelized_Elec_cost_per_kWh": 0,
            "levelized_H2_cost_per_kgH2": 0,
            "levelized_hydrogen_production_cost_per_kg": 0
        }

    env = model._env  
    model.dispose()  
    env.dispose()
    return results