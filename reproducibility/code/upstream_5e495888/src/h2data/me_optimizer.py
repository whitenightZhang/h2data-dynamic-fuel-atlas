import numpy as np
import gurobipy as gp
from gurobipy import Model, GRB


def optimize_methanol_system(
    wind_output,
    pv_output,
    target_methanol_production,
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
    methanol_synthesis_cost,
    methanol_electricity_ratio,
    methanol_hydrogen_ratio,
    methanol_co2_ratio,
    hydrogen_storage_cost,
    hydrogen_storage_elec,
    hydrogen_charge_penalty,
    hydrogen_storage_efficiency,
    methanol_storage_cost_param,
    methanol_charge_penalty,
    discount_rate,
    battery_lifetime,
    wind_lifetime,
    pv_lifetime,
    electrolyzer_lifetime_AE,
    electrolyzer_lifetime_PEM,
    methanol_synthesis_lifetime,
    hydrogen_storage_lifetime,
    methanol_storage_lifetime,
    heat_pump_cost,
    heat_pump_cop,
    heat_pump_lifetime,
    thermal_storage_cost,
    thermal_storage_efficiency,
    thermal_storage_lifetime,
    dac_cost,
    dac_elec_per_kg,
    dac_heat_per_kg,
    dac_lifetime,
    sorbent_cost,
    co2_compressor_cost,
    co2_compression_energy,
    co2_compressor_lifetime,
    co2_storage_cost,
    co2_storage_lifetime,
    Flex_up,
    Flex_mid,
    Flex_down,
    surplus_penalty,
    aggregation_mode
):
    # 年化运维成本
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

    # 年化成本
    wind_annual_cost = wind_cost * discount_rate / (1 - (1+discount_rate)**-wind_lifetime) + wind_om
    pv_annual_cost = pv_cost * discount_rate / (1 - (1+discount_rate)**-pv_lifetime) + pv_om
    battery_energy_annual_cost = battery_energy_cost * discount_rate / (1 - (1+discount_rate)**-battery_lifetime) + battery_energy_om
    battery_storage_annual_cost = battery_storage_cost * discount_rate / (1 - (1+discount_rate)**-battery_lifetime) + battery_storage_om
    electrolyzer_annual_cost_AE = electrolyzer_cost_AE * discount_rate / (1 - (1+discount_rate)**-electrolyzer_lifetime_AE) + electrolyzer_om_AE
    electrolyzer_annual_cost_PEM = electrolyzer_cost_PEM * discount_rate / (1 - (1+discount_rate)**-electrolyzer_lifetime_PEM) + electrolyzer_om_PEM
    methanol_synthesis_annual_cost = methanol_synthesis_cost * discount_rate / (1 - (1+discount_rate)**-methanol_synthesis_lifetime) + methanol_synthesis_om
    hydrogen_storage_annual_cost = hydrogen_storage_cost * discount_rate / (1 - (1+discount_rate)**-hydrogen_storage_lifetime) + hydrogen_storage_om
    methanol_storage_annual_cost = methanol_storage_cost_param * discount_rate / (1 - (1+discount_rate)**-methanol_storage_lifetime) + methanol_storage_om
    heat_pump_annual_cost = heat_pump_cost * discount_rate / (1 - (1+discount_rate)**-heat_pump_lifetime) + heat_pump_om
    thermal_storage_annual_cost = thermal_storage_cost * discount_rate / (1 - (1+discount_rate)**-thermal_storage_lifetime) + thermal_storage_om
    dac_annual_cost = dac_cost * discount_rate / (1 - (1+discount_rate)**-dac_lifetime) + dac_om
    co2_compressor_annual_cost = co2_compressor_cost * discount_rate / (1 - (1+discount_rate)**-co2_compressor_lifetime) + co2_compressor_om
    co2_storage_annual_cost = co2_storage_cost * discount_rate / (1 - (1+discount_rate)**-co2_storage_lifetime) + co2_storage_om

    hourly_methanol_demand = target_methanol_production / 8760

    time_steps = 8760
    model = Model("MethanolDACOptimization")
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', 1000)
    model.setParam('Method', 2)
    model.setParam('Crossover', 0)
    model.setParam('BarConvTol', 1e-6)
    model.setParam('Threads', 1)
    model.setParam('Presolve', 1)
    model.setParam('BarHomogeneous', 1)

    # 决策变量
    wind_capacity = model.addVar(lb=0, name="wind_capacity")
    pv_capacity = model.addVar(lb=0, name="pv_capacity")
    battery_energy_capacity = model.addVar(lb=0, name="battery_energy_capacity")
    battery_storage_capacity = model.addVar(lb=0, name="battery_storage_capacity")
    electrolyzer_capacity_AE = model.addVar(lb=0, name="electrolyzer_capacity_AE")
    electrolyzer_capacity_PEM = model.addVar(lb=0, name="electrolyzer_capacity_PEM")
    methanol_synthesis_capacity = model.addVar(lb=0, name="methanol_synthesis_capacity")
    heat_pump_capacity = model.addVar(lb=0, name="heat_pump_capacity")
    thermal_storage_capacity = model.addVar(lb=0, name="thermal_storage_capacity")
    methanol_storage_capacity = model.addVar(lb=0, name="methanol_storage_capacity")
    hydrogen_storage_capacity = model.addVar(lb=0, name="hydrogen_storage_capacity")
    dac_capacity = model.addVar(lb=0, name="dac_capacity")
    co2_compressor_capacity = model.addVar(lb=0, name="co2_compressor_capacity")
    co2_storage_capacity = model.addVar(lb=0, name="co2_storage_capacity")

    # 时序变量
    energy_balance = model.addVars(time_steps, lb=0, name="energy_balance")
    battery_charge = model.addVars(time_steps, lb=0, name="battery_charge")
    battery_discharge = model.addVars(time_steps, lb=0, name="battery_discharge")
    electrolyzer_power_AE = model.addVars(time_steps, lb=0, name="electrolyzer_power_AE")
    electrolyzer_power_PEM = model.addVars(time_steps, lb=0, name="electrolyzer_power_PEM")
    methanol_synthesis_power = model.addVars(time_steps, lb=0, name="methanol_synthesis_power")
    surplus = model.addVars(time_steps, lb=0, name="surplus")
    hydrogen_storage_balance = model.addVars(time_steps, lb=0, name="hydrogen_storage_balance")
    hydrogen_charge = model.addVars(time_steps, lb=0, name="hydrogen_charge")
    hydrogen_discharge = model.addVars(time_steps, lb=0, name="hydrogen_discharge")
    methanol_storage_balance = model.addVars(time_steps, lb=0, name="methanol_storage_balance")
    methanol_storage_charge = model.addVars(time_steps, lb=0, name="methanol_storage_charge")
    methanol_storage_discharge = model.addVars(time_steps, lb=0, name="methanol_storage_discharge")
    dac_CO2 = model.addVars(time_steps, lb=0, name="dac_CO2")
    dac_electricity = model.addVars(time_steps, lb=0, name="dac_electricity")
    dac_heat_input = model.addVars(time_steps, lb=0, name="dac_heat_input")
    heat_pump_output = model.addVars(time_steps, lb=0, name="heat_pump_output")
    thermal_charge = model.addVars(time_steps, lb=0, name="thermal_charge")
    thermal_discharge = model.addVars(time_steps, lb=0, name="thermal_discharge")
    thermal_storage_level = model.addVars(time_steps, lb=0, name="thermal_storage_level")
    co2_comp_elec = model.addVars(time_steps, lb=0, name="co2_comp_elec")
    co2_storage_level = model.addVars(time_steps, lb=0, name="co2_storage_level")
    co2_charge = model.addVars(time_steps, lb=0, name="co2_charge")
    co2_discharge = model.addVars(time_steps, lb=0, name="co2_discharge")
    direct_co2 = model.addVars(time_steps, lb=0, name="direct_co2")
    stored_co2 = model.addVars(time_steps, lb=0, name="stored_co2")

    # 计算转换系数
    conversion_factor_AE = electrolyzer_eff_AE * 3.6 / 120
    conversion_factor_PEM = electrolyzer_eff_PEM * 3.6 / 120

    # 目标函数
    model.setObjective(
        wind_annual_cost * wind_capacity +
        pv_annual_cost * pv_capacity +
        battery_energy_annual_cost * battery_energy_capacity +
        battery_storage_annual_cost * battery_storage_capacity +
        electrolyzer_annual_cost_AE * electrolyzer_capacity_AE +
        electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM +
        methanol_synthesis_annual_cost * methanol_synthesis_capacity +
        heat_pump_annual_cost * heat_pump_capacity +
        thermal_storage_annual_cost * thermal_storage_capacity +
        hydrogen_storage_annual_cost * hydrogen_storage_capacity +
        methanol_storage_annual_cost * methanol_storage_capacity +
        dac_annual_cost * dac_capacity +
        co2_compressor_annual_cost * co2_compressor_capacity +
        co2_storage_annual_cost * co2_storage_capacity +
        surplus_penalty * gp.quicksum(surplus[t] for t in range(time_steps)) +
        battery_charge_penalty * gp.quicksum(battery_charge[t] for t in range(time_steps)) +
        battery_discharge_penalty * gp.quicksum(battery_discharge[t] for t in range(time_steps)) +
        sorbent_cost * gp.quicksum(dac_CO2[t] for t in range(time_steps)) +
        hydrogen_charge_penalty * gp.quicksum(hydrogen_charge[t] for t in range(time_steps)) +
        methanol_charge_penalty * gp.quicksum(methanol_storage_charge[t] for t in range(time_steps)),
        GRB.MINIMIZE
    )

    # 添加约束
    for t in range(1, time_steps):
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t-1] <= Flex_down * electrolyzer_capacity_AE)
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t-1] >= -Flex_down * electrolyzer_capacity_AE)
        model.addConstr(methanol_synthesis_power[t] - methanol_synthesis_power[t-1] <= Flex_up * methanol_synthesis_capacity)
        model.addConstr(methanol_synthesis_power[t] - methanol_synthesis_power[t-1] >= -Flex_down * methanol_synthesis_capacity)
        model.addConstr(dac_CO2[t] - dac_CO2[t-1] <= Flex_up * dac_capacity)
        model.addConstr(dac_CO2[t] - dac_CO2[t-1] >= -Flex_down * dac_capacity)

    # 5.2 甲醇供需平衡约束（含储存充放，支持多种聚合尺度）
    start_index = 168  # 避开初始不稳定阶段
    if aggregation_mode == "hourly":
        for t in range(start_index, time_steps):
            model.addConstr(
                methanol_synthesis_power[t] + methanol_storage_discharge[t] >=
                hourly_methanol_demand + methanol_storage_charge[t],
                name=f"methanol_balance_hourly_{t}"
            )
    elif aggregation_mode == "3hourly":
        interval = 3
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum(methanol_synthesis_power[t] for t in range(t_start, t_end)) +
                gp.quicksum(methanol_storage_discharge[t] for t in range(t_start, t_end))
                ==
                hourly_methanol_demand * interval +
                gp.quicksum(methanol_storage_charge[t] for t in range(t_start, t_end)),
                name=f"methanol_balance_3hourly_{i}"
            )
    elif aggregation_mode == "daily":
        interval = 24
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum(methanol_synthesis_power[t] for t in range(t_start, t_end)) +
                gp.quicksum(methanol_storage_discharge[t] for t in range(t_start, t_end))
                >=
                0.8 * hourly_methanol_demand * interval +
                gp.quicksum(methanol_storage_charge[t] for t in range(t_start, t_end)),
                name=f"methanol_balance_daily_{i}"
            )
    elif aggregation_mode == "weekly":
        interval = 168
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum(methanol_synthesis_power[t] for t in range(t_start, t_end)) +
                gp.quicksum(methanol_storage_discharge[t] for t in range(t_start, t_end))
                ==
                hourly_methanol_demand * interval +
                gp.quicksum(methanol_storage_charge[t] for t in range(t_start, t_end)),
                name=f"methanol_balance_weekly_{i}"
            )
    elif aggregation_mode == "monthly":
        interval = 730
        n_intervals = (time_steps - start_index) // interval
        for i in range(n_intervals):
            t_start = start_index + i * interval
            t_end = t_start + interval
            model.addConstr(
                gp.quicksum(methanol_synthesis_power[t] for t in range(t_start, t_end)) +
                gp.quicksum(methanol_storage_discharge[t] for t in range(t_start, t_end))
                ==
                hourly_methanol_demand * interval +
                gp.quicksum(methanol_storage_charge[t] for t in range(t_start, t_end)),
                name=f"methanol_balance_monthly_{i}"
            )
    elif aggregation_mode == "annual":
        model.addConstr(
            gp.quicksum(methanol_synthesis_power[t] for t in range(start_index, time_steps)) +
            gp.quicksum(methanol_storage_discharge[t] for t in range(start_index, time_steps))
            ==
            hourly_methanol_demand * (time_steps - start_index) +
            gp.quicksum(methanol_storage_charge[t] for t in range(start_index, time_steps)),
            name="methanol_balance_annual"
        )
    else:
        raise ValueError("Unsupported aggregation_mode value!")

    # 附加：年生产总量约束
    model.addConstr(
        gp.quicksum(methanol_synthesis_power[t] for t in range(time_steps)) >= hourly_methanol_demand * 8760,
        name="annual_methanol_production"
    )

    # 5.3 甲醇储存动态与容量约束
    model.addConstr(methanol_storage_balance[0] ==
                    methanol_storage_charge[0] - methanol_storage_discharge[0],
                    name="methanol_storage_balance_0")
    for t in range(1, time_steps):
        model.addConstr(
            methanol_storage_balance[t] == methanol_storage_balance[t-1] + methanol_storage_charge[t] - methanol_storage_discharge[t],
            name=f"methanol_storage_balance_{t}"
        )
        model.addConstr(methanol_storage_balance[t] <= methanol_storage_capacity,
                        name=f"methanol_storage_capacity_limit_{t}")

    # 5.4 能量平衡与储能动态约束
    conversion_factor_AE  = electrolyzer_eff_AE  * 3.6 / 120
    conversion_factor_PEM = electrolyzer_eff_PEM * 3.6 / 120

    for t in range(time_steps):
        # 计算当期风电与光伏发电
        wind_power = wind_output[t] * wind_capacity
        pv_power = pv_output[t] * pv_capacity
        
        # 甲醇储存：要求合成功率与储存放出至少满足充入量
        model.addConstr(methanol_synthesis_power[t] + methanol_storage_discharge[t] >=
                        methanol_storage_charge[t],
                        name=f"methanol_min_balance_{t}")
                        
        # 电池储能及充放电限额
        model.addConstr(energy_balance[t] <= battery_storage_capacity,
                        name=f"energy_balance_limit_{t}")
        model.addConstr(battery_charge[t] + battery_discharge[t] <= battery_energy_capacity,
                        name=f"battery_charge_discharge_limit_{t}")
        # 氢气存储上限
        model.addConstr(hydrogen_storage_balance[t] <= hydrogen_storage_capacity,
                        name=f"hydrogen_storage_capacity_limit_{t}")
        model.addConstr(hydrogen_charge[t] + hydrogen_discharge[t] <= hydrogen_storage_capacity,
                        name=f"hydrogen_charge_limit_{t}")
        
        # 电力平衡（含电解槽、甲醇合成、储能、热泵、DAC与CO2压缩电耗等）
        model.addConstr(
            wind_power + pv_power + battery_discharge[t] ==
            (electrolyzer_power_AE[t] + electrolyzer_power_PEM[t]) +
            methanol_synthesis_power[t] * methanol_electricity_ratio +
            battery_charge[t] + hydrogen_charge[t] * hydrogen_storage_elec +
            (heat_pump_output[t] / heat_pump_cop) + dac_electricity[t] + surplus[t] + co2_comp_elec[t],
            name=f"power_balance_{t}"
        )
        # 电池动态平衡
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
        # 氢气供需平衡：电解槽产氢需满足甲醇合成及储氢要求
        model.addConstr(
            electrolyzer_power_AE[t] * conversion_factor_AE +
            electrolyzer_power_PEM[t] * conversion_factor_PEM + hydrogen_discharge[t] >=
            methanol_synthesis_power[t] * methanol_hydrogen_ratio + hydrogen_charge[t],
            name=f"hydrogen_PD_balance_{t}"
        )
        # DAC部分：热、电耗与捕集CO2量关系
        model.addConstr(dac_heat_input[t] == dac_CO2[t] * dac_heat_per_kg,
                        name=f"dac_heat_consumption_{t}")
        model.addConstr(dac_electricity[t] == dac_CO2[t] * dac_elec_per_kg,
                        name=f"dac_electricity_consumption_{t}")
        model.addConstr(dac_CO2[t] <= dac_capacity,
                        name=f"dac_capacity_limit_{t}")
        
        # CO2分流：直接供给与进入储存
        model.addConstr(direct_co2[t] + stored_co2[t] == dac_CO2[t],
                        name=f"co2_split_{t}")
        model.addConstr(stored_co2[t] <= co2_compressor_capacity,
                        name=f"co2_compressor_capacity_limit_{t}")
        model.addConstr(co2_comp_elec[t] == stored_co2[t] * co2_compression_energy,
                        name=f"co2_compression_energy_{t}")
        model.addConstr(co2_charge[t] == stored_co2[t],
                        name=f"co2_charge_relation_{t}")
        
        # 热泵与热储热平衡
        model.addConstr(
            heat_pump_output[t] - thermal_charge[t] + thermal_discharge[t] >= dac_heat_input[t],
            name=f"heat_supply_balance_{t}"
        )
        # CO2储存动态及容量约束
        if t == 0:
            model.addConstr(
                co2_storage_level[t] == co2_charge[t] - co2_discharge[t],
                name="co2_storage_balance_0"
            )
        else:
            model.addConstr(
                co2_storage_level[t] == co2_storage_level[t-1] + co2_charge[t] - co2_discharge[t],
                name=f"co2_storage_balance_{t}"
            )
        model.addConstr(co2_storage_level[t] <= co2_storage_capacity,
                        name=f"co2_storage_level_limit_{t}")
        
        # 储热系统动态及容量约束
        if t == 0:
            model.addConstr(
                thermal_storage_level[t] == thermal_charge[t] * thermal_storage_efficiency - thermal_discharge[t] / thermal_storage_efficiency,
                name="thermal_storage_balance_0"
            )
        else:
            model.addConstr(
                thermal_storage_level[t] == thermal_storage_level[t-1] + thermal_charge[t] * thermal_storage_efficiency - thermal_discharge[t] / thermal_storage_efficiency,
                name=f"thermal_storage_balance_{t}"
            )
        model.addConstr(thermal_storage_level[t] <= thermal_storage_capacity,
                        name=f"thermal_storage_level_limit_{t}")

    # 5.5 装机容量与最小运行约束
    model.addConstrs((heat_pump_capacity >= heat_pump_output[t] for t in range(time_steps)),
                    name="heat_pump_capacity_constraint")
    model.addConstrs((heat_pump_output[t] >= 0.25 * heat_pump_capacity for t in range(168, time_steps)),
                    name="heat_pump_min_output")
    model.addConstrs((electrolyzer_capacity_AE >= electrolyzer_power_AE[t] for t in range(time_steps)),
                    name="electrolyzer_AE_capacity_constraint")
    model.addConstrs((electrolyzer_capacity_PEM >= electrolyzer_power_PEM[t] for t in range(time_steps)),
                    name="electrolyzer_PEM_capacity_constraint")
    model.addConstrs((electrolyzer_power_AE[t] >= 0.1 * electrolyzer_capacity_AE for t in range(168, time_steps)),
                    name="electrolyzer_AE_min_power")
    model.addConstrs((dac_CO2[t] >= 0.25 * dac_capacity for t in range(168, time_steps)),
                    name="heat_pump_min_output")
    model.addConstrs((methanol_synthesis_power[t] >= 0.25 * methanol_synthesis_capacity for t in range(168, time_steps)),
                    name="methanol_synthesis_min_output")
    model.addConstrs((methanol_synthesis_power[t] <= methanol_synthesis_capacity for t in range(time_steps)),
                    name="methanol_synthesis_max_output")

    # 5.6 每小时CO2供需平衡约束：直接供给加储存放出需满足当期甲醇CO2需求

    model.addConstrs((direct_co2[t] + co2_discharge[t] >= methanol_synthesis_power[t] * methanol_co2_ratio for t in range(time_steps)),
            name="co2_hourly_balance")

    # 5.7 年度CO2供给约束
    model.addConstr(gp.quicksum(direct_co2[t] + co2_discharge[t] for t in range(time_steps)) >= target_methanol_production * methanol_co2_ratio,
                    name="annual_co2_supply_constraint")

    # 5.8 新增：AE型电解槽必须配备至少10%（此处0.5倍）储能电池
    model.addConstr(battery_energy_capacity >= 0.5 * electrolyzer_capacity_AE,
                    name="min_battery_for_AE")

    model.optimize()

    if model.status == GRB.OPTIMAL:
        total_methanol_production = sum(methanol_synthesis_power[t].x for t in range(time_steps))
        hydrogen_production_kwh = sum(electrolyzer_power_AE[t].x * conversion_factor_AE + electrolyzer_power_PEM[t].x * conversion_factor_PEM for t in range(time_steps)) 
        max_h2_kwh = (
        electrolyzer_capacity_AE.x * conversion_factor_AE +
        electrolyzer_capacity_PEM.x * conversion_factor_PEM
        ) * 8760
        electrolyzer_utilization_hours = hydrogen_production_kwh / max_h2_kwh * 100
        hydrogen_storage_kwh = sum(hydrogen_charge[t].x * hydrogen_storage_elec for t in range(time_steps))
        methanol_utilization_hours = target_methanol_production / (methanol_synthesis_capacity.x * 8760) * 100
        total_CO2_captured = sum(dac_CO2[t].x for t in range(time_steps))

        total_Elec_generation = (sum(wind_output[t] for t in range(time_steps)) * wind_capacity.x +
                                sum(pv_output[t] for t in range(time_steps)) * pv_capacity.x -
                                sum(surplus[t].x for t in range(time_steps)))

        # 年累计电解耗电（kWh）
        total_elec_consumed = sum(
            electrolyzer_power_AE[t].x +
            electrolyzer_power_PEM[t].x
            for t in range(time_steps)
        )

        total_hydrogen_production = sum(
            electrolyzer_power_AE[t].x * conversion_factor_AE +
            electrolyzer_power_PEM[t].x * conversion_factor_PEM
            for t in range(time_steps)
        )
        # 氢气储存所用电量（kWh）
        hydrogen_storage_kwh = sum(hydrogen_charge[t].x * hydrogen_storage_elec for t in range(time_steps))

        total_Heat_generation = sum(heat_pump_output[t].x for t in range(time_steps))

        dac_utilization_hours = total_CO2_captured / (dac_capacity.x * 8760) * 100
        levelized_dac_cost = (dac_annual_cost * dac_capacity.x +
                            co2_compressor_annual_cost * co2_compressor_capacity.x +
                            co2_storage_annual_cost * co2_storage_capacity.x) / (total_CO2_captured / 1000)

        levelized_Elec_cost = (wind_annual_cost * wind_capacity.x +
                            pv_annual_cost * pv_capacity.x +
                            battery_energy_annual_cost * battery_energy_capacity.x +
                            battery_storage_annual_cost * battery_storage_capacity.x) / (total_Elec_generation)

        levelized_Heat_cost = (heat_pump_annual_cost * heat_pump_capacity.x +
                            thermal_storage_annual_cost * thermal_storage_capacity.x +
                            levelized_Elec_cost * total_Heat_generation / heat_pump_cop) / (total_Heat_generation)

        levelized_H2_cost = (
            electrolyzer_annual_cost_AE  * electrolyzer_capacity_AE.x +
            electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM.x +
            levelized_Elec_cost * total_elec_consumed +
            levelized_Elec_cost * hydrogen_storage_kwh +
            hydrogen_storage_annual_cost * hydrogen_storage_capacity.x
        ) / total_hydrogen_production

        # 计算指标
        results = {
            "wind_capacity_kW":                    wind_capacity.x,
            "pv_capacity_kW":                      pv_capacity.x,
            "battery_energy_capacity_kW":          battery_energy_capacity.x,
            "battery_storage_capacity_kWh":        battery_storage_capacity.x,
            "electrolyzer_capacity_AE_kW":         electrolyzer_capacity_AE.x,
            "electrolyzer_capacity_PEM_kW":        electrolyzer_capacity_PEM.x,
            "heat_pump_capacity_kW_th":            heat_pump_capacity.x,
            "thermal_storage_capacity_kWh_th":     thermal_storage_capacity.x,
            "methanol_synthesis_capacity_tpy":     methanol_synthesis_capacity.x * 8760 / 1000,
            "methanol_storage_capacity_kg_per_h":  methanol_storage_capacity.x,
            "hydrogen_storage_capacity_kgH2":      hydrogen_storage_capacity.x,
            "dac_capacity_kgCO2_per_h":            dac_capacity.x,
            "co2_compressor_capacity_kgCO2_per_h": co2_compressor_capacity.x,
            "co2_storage_capacity_kg":             co2_storage_capacity.x,
            "total_CO2_captured_kg":               total_CO2_captured,
            "total_methanol_production_kg":        total_methanol_production,
            "total_hydrogen_production_kg":        total_hydrogen_production,
            "electrolyzer_utilization_percent":    electrolyzer_utilization_hours,
            "methanol_utilization_percent":        methanol_utilization_hours,
            "dac_utilization_percent":             dac_utilization_hours,
            "levelized_dac_cost_per_tCO2":         levelized_dac_cost,
            "levelized_elec_cost_per_kWh":         levelized_Elec_cost,
            "levelized_heat_cost_per_kWh_th":      levelized_Heat_cost,
            "levelized_h2_cost_per_kg":            levelized_H2_cost,
            "levelized_methanol_cost_per_ton":     model.objVal / total_methanol_production * 1000
        }
    else:
        results = { }

    env = model._env
    model.dispose()
    env.dispose()
    return results
