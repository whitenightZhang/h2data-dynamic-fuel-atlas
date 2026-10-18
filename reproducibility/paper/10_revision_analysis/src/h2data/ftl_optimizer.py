import numpy as np
import gurobipy as gp
from gurobipy import Model, GRB


def optimize_ftl_system(
    wind_output,
    pv_output,
    target_ftl_production,
    # 成本 / 参数输入（允许外部灵活指定）
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
    electrolyzer_lifetime_AE,
    electrolyzer_lifetime_PEM,
    ftl_synthesis_cost,
    ftl_synthesis_lifetime,
    ftl_hydrogen_ratio,
    ftl_co2_ratio,
    ftl_electricity_ratio,
    hydrogen_storage_cost,
    hydrogen_storage_elec,
    hydrogen_charge_penalty,
    hydrogen_storage_efficiency,
    hydrogen_storage_lifetime,
    ftl_storage_cost_param,
    ftl_storage_lifetime,
    ftl_charge_penalty,
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
    discount_rate,
    battery_lifetime,
    wind_lifetime,
    pv_lifetime,
    Flex_up,
    Flex_mid,
    Flex_down,
    surplus_penalty,
    aggregation_mode
):
    """FT Liquid + DAC 优化模型（复用用户提供脚本逻辑，封装为函数）

    参数说明：传入逐小时风/光容量因子数组（长度需=8760），以及各类成本、效率、寿命与灵活性参数。
    返回：包含容量配置、利用率、平准化成本等指标的结果字典；若不可行返回空字典。
    """
    time_steps = len(wind_output)
    assert len(pv_output) == time_steps, "pv_output length must match wind_output"

    # 年化 O&M（使用统一 3% 或指定 6% 的比率）
    wind_om = wind_cost * 0.03
    pv_om = pv_cost * 0.03
    battery_energy_om = battery_energy_cost * 0.03
    battery_storage_om = battery_storage_cost * 0.03
    electrolyzer_om_AE = electrolyzer_cost_AE * 0.03
    electrolyzer_om_PEM = electrolyzer_cost_PEM * 0.03
    ftl_synthesis_om = ftl_synthesis_cost * 0.06  # 按用户脚本示例
    hydrogen_storage_om = hydrogen_storage_cost * 0.03
    ftl_storage_om = ftl_storage_cost_param * 0.03
    heat_pump_om = heat_pump_cost * 0.03
    thermal_storage_om = thermal_storage_cost * 0.03
    dac_om = dac_cost * 0.03
    co2_compressor_om = co2_compressor_cost * 0.03
    co2_storage_om = co2_storage_cost * 0.03

    hourly_ftl_demand = target_ftl_production / 8760.0

    # 年化资本 + O&M
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

    model = Model("HydrogenFTLOptimization")
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', 1000)
    model.setParam('Method', 2)
    model.setParam('Crossover', 0)
    model.setParam('BarConvTol', 1e-6)
    model.setParam('Threads', 1)
    model.setParam('Presolve', 1)
    model.setParam('BarHomogeneous', 1)

    # 容量变量
    wind_capacity = model.addVar(lb=0, name="wind_capacity")
    pv_capacity = model.addVar(lb=0, name="pv_capacity")
    battery_energy_capacity = model.addVar(lb=0, name="battery_energy_capacity")
    battery_storage_capacity = model.addVar(lb=0, name="battery_storage_capacity")
    electrolyzer_capacity_AE = model.addVar(lb=0, name="electrolyzer_capacity_AE")
    electrolyzer_capacity_PEM = model.addVar(lb=0, name="electrolyzer_capacity_PEM")
    ftl_synthesis_capacity = model.addVar(lb=0, name="FTL_capacity")
    heat_pump_capacity = model.addVar(lb=0, name="heat_pump_capacity")
    thermal_storage_capacity = model.addVar(lb=0, name="thermal_storage_capacity")
    ftl_storage_capacity = model.addVar(lb=0, name="FTL_storage_capacity")
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
    ftl_synthesis_power = model.addVars(time_steps, lb=0, name="FTL_synthesis_power")
    ftl_storage_balance = model.addVars(time_steps, lb=0, name="FTL_storage_balance")
    ftl_storage_charge = model.addVars(time_steps, lb=0, name="FTL_storage_charge")
    ftl_storage_discharge = model.addVars(time_steps, lb=0, name="FTL_storage_discharge")
    hydrogen_storage_balance = model.addVars(time_steps, lb=0, name="hydrogen_storage_balance")
    hydrogen_charge = model.addVars(time_steps, lb=0, name="hydrogen_charge")
    hydrogen_discharge = model.addVars(time_steps, lb=0, name="hydrogen_discharge")
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
    surplus = model.addVars(time_steps, lb=0, name="surplus")

    # 目标函数
    model.setObjective(
        wind_annual_cost * wind_capacity +
        pv_annual_cost * pv_capacity +
        battery_energy_annual_cost * battery_energy_capacity +
        battery_storage_annual_cost * battery_storage_capacity +
        electrolyzer_annual_cost_AE * electrolyzer_capacity_AE +
        electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM +
        ftl_synthesis_annual_cost * ftl_synthesis_capacity +
        heat_pump_annual_cost * heat_pump_capacity +
        thermal_storage_annual_cost * thermal_storage_capacity +
        hydrogen_storage_annual_cost * hydrogen_storage_capacity +
        ftl_storage_annual_cost * ftl_storage_capacity +
        dac_annual_cost * dac_capacity +
        co2_compressor_annual_cost * co2_compressor_capacity +
        co2_storage_annual_cost * co2_storage_capacity +
        surplus_penalty * gp.quicksum(surplus[t] for t in range(time_steps)) +
        battery_charge_penalty * gp.quicksum(battery_charge[t] for t in range(time_steps)) +
        battery_discharge_penalty * gp.quicksum(battery_discharge[t] for t in range(time_steps)) +
        sorbent_cost * gp.quicksum(dac_CO2[t] for t in range(time_steps)) +
        hydrogen_charge_penalty * gp.quicksum(hydrogen_charge[t] for t in range(time_steps)) +
        ftl_charge_penalty * gp.quicksum(ftl_storage_charge[t] for t in range(time_steps)),
        GRB.MINIMIZE
    )

    # 爬坡约束
    for t in range(1, time_steps):
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t-1] <= Flex_down * electrolyzer_capacity_AE)
        model.addConstr(electrolyzer_power_AE[t] - electrolyzer_power_AE[t-1] >= -Flex_down * electrolyzer_capacity_AE)
        model.addConstr(ftl_synthesis_power[t] - ftl_synthesis_power[t-1] <= Flex_up * ftl_synthesis_capacity)
        model.addConstr(ftl_synthesis_power[t] - ftl_synthesis_power[t-1] >= -Flex_down * ftl_synthesis_capacity)
        model.addConstr(dac_CO2[t] - dac_CO2[t-1] <= Flex_up * dac_capacity)
        model.addConstr(dac_CO2[t] - dac_CO2[t-1] >= -Flex_down * dac_capacity)

    # FTL 供需聚合约束
    start_index = 168
    if aggregation_mode == "hourly":
        for t in range(start_index, time_steps):
            model.addConstr(ftl_synthesis_power[t] + ftl_storage_discharge[t] >= hourly_ftl_demand + ftl_storage_charge[t])
    elif aggregation_mode == "3hourly":
        interval = 3
        n = (time_steps - start_index) // interval
        for i in range(n):
            s = start_index + i * interval
            e = s + interval
            model.addConstr(
                gp.quicksum(ftl_synthesis_power[t] for t in range(s, e)) +
                gp.quicksum(ftl_storage_discharge[t] for t in range(s, e)) ==
                hourly_ftl_demand * interval +
                gp.quicksum(ftl_storage_charge[t] for t in range(s, e))
            )
    elif aggregation_mode == "daily":
        interval = 24
        n = (time_steps - start_index) // interval
        for i in range(n):
            s = start_index + i * interval
            e = s + interval
            model.addConstr(
                gp.quicksum(ftl_synthesis_power[t] for t in range(s, e)) +
                gp.quicksum(ftl_storage_discharge[t] for t in range(s, e)) >=
                0.8 * hourly_ftl_demand * interval +
                gp.quicksum(ftl_storage_charge[t] for t in range(s, e))
            )
    elif aggregation_mode == "weekly":
        interval = 168
        n = (time_steps - start_index) // interval
        for i in range(n):
            s = start_index + i * interval
            e = s + interval
            model.addConstr(
                gp.quicksum(ftl_synthesis_power[t] for t in range(s, e)) +
                gp.quicksum(ftl_storage_discharge[t] for t in range(s, e)) ==
                hourly_ftl_demand * interval +
                gp.quicksum(ftl_storage_charge[t] for t in range(s, e))
            )
    elif aggregation_mode == "monthly":
        interval = 730
        n = (time_steps - start_index) // interval
        for i in range(n):
            s = start_index + i * interval
            e = s + interval
            model.addConstr(
                gp.quicksum(ftl_synthesis_power[t] for t in range(s, e)) +
                gp.quicksum(ftl_storage_discharge[t] for t in range(s, e)) ==
                hourly_ftl_demand * interval +
                gp.quicksum(ftl_storage_charge[t] for t in range(s, e))
            )
    elif aggregation_mode == "annual":
        model.addConstr(
            gp.quicksum(ftl_synthesis_power[t] for t in range(start_index, time_steps)) +
            gp.quicksum(ftl_storage_discharge[t] for t in range(start_index, time_steps)) ==
            hourly_ftl_demand * (time_steps - start_index) +
            gp.quicksum(ftl_storage_charge[t] for t in range(start_index, time_steps))
        )
    else:
        raise ValueError("Unsupported aggregation_mode")

    # 年生产量约束
    model.addConstr(gp.quicksum(ftl_synthesis_power[t] for t in range(time_steps)) >= target_ftl_production)

    # 储存动态
    model.addConstr(ftl_storage_balance[0] == ftl_storage_charge[0] - ftl_storage_discharge[0])
    for t in range(1, time_steps):
        model.addConstr(ftl_storage_balance[t] == ftl_storage_balance[t-1] + ftl_storage_charge[t] - ftl_storage_discharge[t])
        model.addConstr(ftl_storage_balance[t] <= ftl_storage_capacity)

    conversion_factor_AE = electrolyzer_eff_AE * 3.6 / 120
    conversion_factor_PEM = electrolyzer_eff_PEM * 3.6 / 120

    for t in range(time_steps):
        wind_power = wind_output[t] * wind_capacity
        pv_power = pv_output[t] * pv_capacity

        model.addConstr(ftl_synthesis_power[t] + ftl_storage_discharge[t] >= ftl_storage_charge[t])
        model.addConstr(energy_balance[t] <= battery_storage_capacity)
        model.addConstr(battery_charge[t] + battery_discharge[t] <= battery_energy_capacity)
        model.addConstr(hydrogen_storage_balance[t] <= hydrogen_storage_capacity)
        model.addConstr(hydrogen_charge[t] + hydrogen_discharge[t] <= hydrogen_storage_capacity)

        model.addConstr(
            wind_power + pv_power + battery_discharge[t] ==
            (electrolyzer_power_AE[t] + electrolyzer_power_PEM[t]) +
            ftl_synthesis_power[t] * ftl_electricity_ratio +
            battery_charge[t] + hydrogen_charge[t] * hydrogen_storage_elec +
            (heat_pump_output[t] / heat_pump_cop) + dac_electricity[t] + surplus[t] + co2_comp_elec[t]
        )
        if t == 0:
            model.addConstr(energy_balance[t] == battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency)
            model.addConstr(hydrogen_storage_balance[t] == hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t])
            model.addConstr(thermal_storage_level[t] == thermal_charge[t] * thermal_storage_efficiency - thermal_discharge[t] / thermal_storage_efficiency)
            model.addConstr(co2_storage_level[t] == co2_charge[t] - co2_discharge[t])
        else:
            model.addConstr(energy_balance[t] == energy_balance[t-1] + battery_charge[t] * battery_charge_efficiency - battery_discharge[t] / battery_discharge_efficiency)
            model.addConstr(hydrogen_storage_balance[t] == hydrogen_storage_balance[t-1] + hydrogen_charge[t] * hydrogen_storage_efficiency - hydrogen_discharge[t])
            model.addConstr(thermal_storage_level[t] == thermal_storage_level[t-1] + thermal_charge[t] * thermal_storage_efficiency - thermal_discharge[t] / thermal_storage_efficiency)
            model.addConstr(co2_storage_level[t] == co2_storage_level[t-1] + co2_charge[t] - co2_discharge[t])

        model.addConstr(
            electrolyzer_power_AE[t] * conversion_factor_AE +
            electrolyzer_power_PEM[t] * conversion_factor_PEM + hydrogen_discharge[t] >=
            ftl_synthesis_power[t] * ftl_hydrogen_ratio + hydrogen_charge[t]
        )

        model.addConstr(dac_heat_input[t] == dac_CO2[t] * dac_heat_per_kg)
        model.addConstr(dac_electricity[t] == dac_CO2[t] * dac_elec_per_kg)
        model.addConstr(dac_CO2[t] <= dac_capacity)

        model.addConstr(direct_co2[t] + stored_co2[t] == dac_CO2[t])
        model.addConstr(stored_co2[t] <= co2_compressor_capacity)
        model.addConstr(co2_comp_elec[t] == stored_co2[t] * co2_compression_energy)
        model.addConstr(co2_charge[t] == stored_co2[t])

        model.addConstr(heat_pump_output[t] - thermal_charge[t] + thermal_discharge[t] >= dac_heat_input[t])
        model.addConstr(thermal_storage_level[t] <= thermal_storage_capacity)
        model.addConstr(co2_storage_level[t] <= co2_storage_capacity)

    # 设备容量/最小出力
    model.addConstrs((heat_pump_capacity >= heat_pump_output[t] for t in range(time_steps)))
    model.addConstrs((heat_pump_output[t] >= 0.25 * heat_pump_capacity for t in range(168, time_steps)))
    model.addConstrs((electrolyzer_capacity_AE >= electrolyzer_power_AE[t] for t in range(time_steps)))
    model.addConstrs((electrolyzer_capacity_PEM >= electrolyzer_power_PEM[t] for t in range(time_steps)))
    model.addConstrs((electrolyzer_power_AE[t] >= 0.1 * electrolyzer_capacity_AE for t in range(168, time_steps)))
    model.addConstrs((dac_CO2[t] >= 0.25 * dac_capacity for t in range(168, time_steps)))
    model.addConstrs((ftl_synthesis_power[t] <= ftl_synthesis_capacity for t in range(time_steps)))
    model.addConstrs(
        (ftl_synthesis_power[t] >= 0.25 * ftl_synthesis_capacity for t in range(168, time_steps)),
        name="ftl_min_output"
    )
    model.addConstrs((direct_co2[t] + co2_discharge[t] >= ftl_synthesis_power[t] * ftl_co2_ratio for t in range(time_steps)))
    model.addConstr(gp.quicksum(direct_co2[t] + co2_discharge[t] for t in range(time_steps)) >= target_ftl_production * ftl_co2_ratio)
    model.addConstr(battery_energy_capacity >= 0.5 * electrolyzer_capacity_AE)

    model.optimize()

    if model.status == GRB.OPTIMAL:
        total_ftl_production = sum(ftl_synthesis_power[t].x for t in range(time_steps))
        hydrogen_prod_kwh = sum(
            electrolyzer_power_AE[t].x * conversion_factor_AE +
            electrolyzer_power_PEM[t].x * conversion_factor_PEM for t in range(time_steps)
        )
        max_h2_kwh = (
            electrolyzer_capacity_AE.x * conversion_factor_AE +
            electrolyzer_capacity_PEM.x * conversion_factor_PEM
        ) * 8760
        electrolyzer_util_pct = hydrogen_prod_kwh / max_h2_kwh * 100 if max_h2_kwh > 0 else 0
        hydrogen_storage_kwh = sum(hydrogen_charge[t].x * hydrogen_storage_elec for t in range(time_steps))
        ftl_util_pct = target_ftl_production / (ftl_synthesis_capacity.x * 8760) * 100 if ftl_synthesis_capacity.x > 0 else 0
        total_CO2_captured = sum(dac_CO2[t].x for t in range(time_steps))
        total_elec_generation = (
            sum(wind_output[t] for t in range(time_steps)) * wind_capacity.x +
            sum(pv_output[t] for t in range(time_steps)) * pv_capacity.x -
            sum(surplus[t].x for t in range(time_steps))
        )
        total_elec_consumed = sum(electrolyzer_power_AE[t].x + electrolyzer_power_PEM[t].x for t in range(time_steps))
        total_hydrogen_production = sum(
            electrolyzer_power_AE[t].x * conversion_factor_AE +
            electrolyzer_power_PEM[t].x * conversion_factor_PEM for t in range(time_steps)
        )
        total_heat_generation = sum(heat_pump_output[t].x for t in range(time_steps))
        dac_util_pct = total_CO2_captured / (dac_capacity.x * 8760) * 100 if dac_capacity.x > 0 else 0
        levelized_dac_cost = (
            dac_annual_cost * dac_capacity.x +
            co2_compressor_annual_cost * co2_compressor_capacity.x +
            co2_storage_annual_cost * co2_storage_capacity.x
        ) / (total_CO2_captured / 1000) if total_CO2_captured > 0 else 0
        levelized_elec_cost = (
            wind_annual_cost * wind_capacity.x +
            pv_annual_cost * pv_capacity.x +
            battery_energy_annual_cost * battery_energy_capacity.x +
            battery_storage_annual_cost * battery_storage_capacity.x
        ) / total_elec_generation if total_elec_generation > 0 else 0
        levelized_heat_cost = (
            heat_pump_annual_cost * heat_pump_capacity.x +
            thermal_storage_annual_cost * thermal_storage_capacity.x +
            levelized_elec_cost * total_heat_generation / heat_pump_cop
        ) / total_heat_generation if total_heat_generation > 0 else 0
        levelized_h2_cost = (
            electrolyzer_annual_cost_AE * electrolyzer_capacity_AE.x +
            electrolyzer_annual_cost_PEM * electrolyzer_capacity_PEM.x +
            levelized_elec_cost * total_elec_consumed +
            levelized_elec_cost * hydrogen_storage_kwh +
            hydrogen_storage_annual_cost * hydrogen_storage_capacity.x
        ) / total_hydrogen_production if total_hydrogen_production > 0 else 0
        results = {
            'wind_capacity_kW': wind_capacity.x,
            'pv_capacity_kW': pv_capacity.x,
            'battery_energy_capacity_kW': battery_energy_capacity.x,
            'battery_storage_capacity_kWh': battery_storage_capacity.x,
            'electrolyzer_capacity_AE_kW': electrolyzer_capacity_AE.x,
            'electrolyzer_capacity_PEM_kW': electrolyzer_capacity_PEM.x,
            'heat_pump_capacity_kW_th': heat_pump_capacity.x,
            'thermal_storage_capacity_kWh_th': thermal_storage_capacity.x,
            'FTL_synthesis_capacity_tpy': ftl_synthesis_capacity.x * 8760 / 1000,
            'FTL_storage_capacity_kg_per_h': ftl_storage_capacity.x,
            'hydrogen_storage_capacity_kgH2': hydrogen_storage_capacity.x,
            'dac_capacity_kgCO2_per_h': dac_capacity.x,
            'co2_compressor_capacity_kgCO2_per_h': co2_compressor_capacity.x,
            'co2_storage_capacity_kg': co2_storage_capacity.x,
            'total_CO2_captured_kg': total_CO2_captured,
            'total_FTL_production_kg': total_ftl_production,
            'total_hydrogen_production_kg': total_hydrogen_production,
            'electrolyzer_utilization_percent': electrolyzer_util_pct,
            'FTL_utilization_percent': ftl_util_pct,
            'dac_utilization_percent': dac_util_pct,
            'levelized_dac_cost_per_tCO2': levelized_dac_cost,
            'levelized_elec_cost_per_kWh': levelized_elec_cost,
            'levelized_heat_cost_per_kWh_th': levelized_heat_cost,
            'levelized_h2_cost_per_kg': levelized_h2_cost,
            'levelized_FTL_cost_per_ton': (model.objVal / total_ftl_production * 1000) if total_ftl_production > 0 else 0,
            'objective_value': model.objVal,
        }
    else:
        results = {}

    env = model._env
    model.dispose()
    env.dispose()
    return results
