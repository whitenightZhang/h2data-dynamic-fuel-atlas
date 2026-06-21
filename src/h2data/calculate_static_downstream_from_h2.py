#!/usr/bin/env python3
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
import os

import numpy as np


logger = logging.getLogger(__name__)

CHECKPOINT_INTERVAL = 100


def capital_recovery_factor(discount_rate, lifetime):
    return discount_rate / (1 - (1 + discount_rate) ** -lifetime)


def annualized_cost(capex, discount_rate, lifetime, om_rate=0.03):
    return capex * capital_recovery_factor(discount_rate, lifetime) + capex * om_rate


def parse_csv_list(value):
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_chunks(chunks_text):
    chunks = []
    for part in parse_csv_list(chunks_text):
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            step = 1 if end >= start else -1
            chunks.extend(range(start, end + step, step))
        else:
            chunks.append(int(part))
    return list(dict.fromkeys(chunks))


def h2_scenario_family(scenario):
    scenario = str(scenario)
    if "2050" in scenario:
        return "2050"
    if "2035" in scenario:
        return "2035"
    return "2030"


def discover_scenarios(input_dir, file_template, chunks):
    scenarios = set()
    for chunk_idx in chunks:
        offset = chunk_idx * 60
        prefix = file_template.format(offset=offset, scenario="").replace(".csv", "")
        if not os.path.isdir(input_dir):
            continue
        for filename in os.listdir(input_dir):
            if not filename.startswith(prefix) or not filename.endswith(".csv"):
                continue
            scenario = filename[len(prefix):-4]
            if scenario:
                scenarios.add(scenario)
    return sorted(scenarios)


def ammonia_params(family):
    params = {
        "target": 10e3,
        "hydrogen_ratio": 0.18,
        "electricity_ratio": 0.303,
        "synthesis_lifetime": 30,
        "storage_cost_param": 0.59,
        "storage_lifetime": 30,
        "discount_rate": 0.07,
    }
    if family == "2050":
        params["synthesis_cost"] = 5000
    elif family == "2035":
        params["synthesis_cost"] = 6500
    else:
        params["synthesis_cost"] = 8000
    return params


def methanol_params(family):
    params = {
        "target": 10e3,
        "hydrogen_ratio": 0.19,
        "co2_ratio": 1.4,
        "electricity_ratio": 0.7,
        "synthesis_lifetime": 30,
        "storage_cost_param": 0.056,
        "storage_lifetime": 30,
        "heat_pump_cop": 3.2,
        "heat_pump_lifetime": 20,
        "thermal_storage_cost": 30,
        "thermal_storage_lifetime": 30,
        "dac_lifetime": 30,
        "co2_compressor_cost": 365,
        "co2_compression_energy": 0.1,
        "co2_compressor_lifetime": 20,
        "co2_storage_cost": 24,
        "co2_storage_lifetime": 30,
        "discount_rate": 0.07,
    }
    if family == "2050":
        params.update({
            "synthesis_cost": 5200,
            "heat_pump_cost": 900,
            "dac_cost": 3000,
            "dac_elec_per_kg": 0.22,
            "dac_heat_per_kg": 1.0,
            "sorbent_cost": 0.009,
        })
    elif family == "2035":
        params.update({
            "synthesis_cost": 5700,
            "heat_pump_cost": 950,
            "dac_cost": 4000,
            "dac_elec_per_kg": 0.25,
            "dac_heat_per_kg": 1.0,
            "sorbent_cost": 0.012,
        })
    else:
        params.update({
            "synthesis_cost": 6500,
            "heat_pump_cost": 1000,
            "dac_cost": 7800,
            "dac_elec_per_kg": 0.31,
            "dac_heat_per_kg": 1.3,
            "sorbent_cost": 0.020,
        })
    return params


def ftl_params(family):
    params = {
        "target": 10e3,
        "electricity_ratio": 0.3,
        "synthesis_lifetime": 25,
        "synthesis_om_rate": 0.06,
        "storage_cost_param": 0.056,
        "storage_lifetime": 30,
        "heat_pump_cop": 3.2,
        "heat_pump_lifetime": 20,
        "thermal_storage_cost": 30,
        "thermal_storage_lifetime": 30,
        "dac_lifetime": 30,
        "co2_compressor_cost": 365,
        "co2_compression_energy": 0.1,
        "co2_compressor_lifetime": 20,
        "co2_storage_cost": 24,
        "co2_storage_lifetime": 30,
        "discount_rate": 0.07,
    }
    if family == "2050":
        params.update({
            "synthesis_cost": 9400,
            "hydrogen_ratio": 0.48,
            "co2_ratio": 3.3,
            "heat_pump_cost": 900,
            "dac_cost": 3000,
            "dac_elec_per_kg": 0.22,
            "dac_heat_per_kg": 1.0,
            "sorbent_cost": 0.009,
        })
    elif family == "2035":
        params.update({
            "synthesis_cost": 9400,
            "hydrogen_ratio": 0.49,
            "co2_ratio": 3.6,
            "heat_pump_cost": 950,
            "dac_cost": 4000,
            "dac_elec_per_kg": 0.25,
            "dac_heat_per_kg": 1.0,
            "sorbent_cost": 0.001,
        })
    else:
        params.update({
            "synthesis_cost": 22000,
            "hydrogen_ratio": 0.51,
            "co2_ratio": 3.9,
            "heat_pump_cost": 1000,
            "dac_cost": 7800,
            "dac_elec_per_kg": 0.31,
            "dac_heat_per_kg": 1.3,
            "sorbent_cost": 0.020,
        })
    return params


def read_value(row, names, default=0.0):
    for name in names:
        if name in row and not np.isnan(row[name]):
            return float(row[name])
    return default


def source_values(row, source):
    if source == "wind":
        return {
            "lcoe": read_value(row, ["wind_LCOE_per_kWh"]),
            "lcoh": read_value(row, ["wind_LCOH_per_kg"]),
            "wind_capacity": read_value(row, ["wind_based_wind_capacity"]),
            "pv_capacity": read_value(row, ["wind_based_pv_capacity"]),
            "electrolyzer_ae": read_value(row, ["wind_based_electrolyzer_capacity_AE"]),
            "electrolyzer_pem": read_value(row, ["wind_based_electrolyzer_capacity_PEM"]),
        }
    if source == "pv":
        return {
            "lcoe": read_value(row, ["pv_LCOE_per_kWh"]),
            "lcoh": read_value(row, ["pv_LCOH_per_kg"]),
            "wind_capacity": read_value(row, ["pv_based_wind_capacity"]),
            "pv_capacity": read_value(row, ["pv_based_pv_capacity"]),
            "electrolyzer_ae": read_value(row, ["pv_based_electrolyzer_capacity_AE"]),
            "electrolyzer_pem": read_value(row, ["pv_based_electrolyzer_capacity_PEM"]),
        }
    return {
        "lcoe": read_value(row, ["LCOE_per_kWh", "levelized_Elec_cost_per_kWh", "levelized_elec_cost_per_kWh"]),
        "lcoh": read_value(row, ["LCOH_per_kg", "levelized_hydrogen_production_cost_per_kg", "levelized_H2_cost_per_kgH2"]),
        "wind_capacity": read_value(row, ["wind_capacity"]),
        "pv_capacity": read_value(row, ["pv_capacity"]),
        "electrolyzer_ae": read_value(row, ["electrolyzer_capacity_AE"]),
        "electrolyzer_pem": read_value(row, ["electrolyzer_capacity_PEM"]),
    }


def scale_h2_capacities(source, h2_required, h2_basis):
    scale = h2_required / h2_basis if h2_basis > 0 else 0.0
    return {
        "wind_capacity": source["wind_capacity"] * scale,
        "pv_capacity": source["pv_capacity"] * scale,
        "electrolyzer_capacity_AE": source["electrolyzer_ae"] * scale,
        "electrolyzer_capacity_PEM": source["electrolyzer_pem"] * scale,
    }


def calc_ammonia(row, source_name, source):
    params = ammonia_params(h2_scenario_family(row["scenario"]))
    target = params["target"]
    h2_required = target * params["hydrogen_ratio"]
    h2_basis = read_value(row, ["total_hydrogen_production_kg"], 10000.0)
    synthesis_capacity_kg_h = target / 8760.0
    synthesis_annual = annualized_cost(
        params["synthesis_cost"], params["discount_rate"], params["synthesis_lifetime"]
    )
    synthesis_cost = synthesis_annual * synthesis_capacity_kg_h
    direct_elec_kwh = target * params["electricity_ratio"]
    total_cost = h2_required * source["lcoh"] + direct_elec_kwh * source["lcoe"] + synthesis_cost
    caps = scale_h2_capacities(source, h2_required, h2_basis)
    return {
        **caps,
        "battery_energy_capacity": 0.0,
        "battery_storage_capacity": 0.0,
        "ammonia_synthesis_capacity": target / 1000.0,
        "hydrogen_storage_capacity": 0.0,
        "ammonia_storage_capacity": 0.0,
        "total_ammonia_production_kg": target,
        "total_hydrogen_production_kg": h2_required,
        "total_elec_generation_kwh": direct_elec_kwh,
        "direct_electricity_consumption_kwh": direct_elec_kwh,
        "electrolyzer_utilization_percent": 100.0,
        "ammonia_utilization_percent": 100.0,
        "levelized_elec_cost_per_kwh": source["lcoe"],
        "levelized_h2_cost_per_kg": source["lcoh"],
        "levelized_ammonia_cost_per_ton": total_cost / target * 1000.0,
        "static_h2_cost_component": h2_required * source["lcoh"],
        "static_electricity_cost_component": direct_elec_kwh * source["lcoe"],
        "static_synthesis_cost_component": synthesis_cost,
        "selected_RE_source": source_name,
    }


def calc_carbon_product(row, product, source_name, source):
    params = methanol_params(h2_scenario_family(row["scenario"])) if product == "methanol" else ftl_params(h2_scenario_family(row["scenario"]))
    target = params["target"]
    h2_required = target * params["hydrogen_ratio"]
    co2_required = target * params["co2_ratio"]
    h2_basis = read_value(row, ["total_hydrogen_production_kg"], 10000.0)

    dr = params["discount_rate"]
    synthesis_om = params.get("synthesis_om_rate", 0.03)
    synthesis_annual = annualized_cost(
        params["synthesis_cost"], dr, params["synthesis_lifetime"], synthesis_om
    )
    dac_annual = annualized_cost(params["dac_cost"], dr, params["dac_lifetime"])
    compressor_annual = annualized_cost(
        params["co2_compressor_cost"], dr, params["co2_compressor_lifetime"]
    )
    heat_pump_annual = annualized_cost(params["heat_pump_cost"], dr, params["heat_pump_lifetime"])

    synthesis_capacity_kg_h = target / 8760.0
    dac_capacity_kg_h = co2_required / 8760.0
    compressor_capacity_kg_h = co2_required / 8760.0
    heat_required_kwh_th = co2_required * params["dac_heat_per_kg"]
    heat_pump_capacity_kw_th = heat_required_kwh_th / 8760.0

    direct_elec_kwh = target * params["electricity_ratio"]
    dac_elec_kwh = co2_required * params["dac_elec_per_kg"]
    compressor_elec_kwh = co2_required * params["co2_compression_energy"]
    heat_pump_elec_kwh = heat_required_kwh_th / params["heat_pump_cop"]
    total_direct_elec = direct_elec_kwh + dac_elec_kwh + compressor_elec_kwh + heat_pump_elec_kwh

    h2_cost = h2_required * source["lcoh"]
    elec_cost = total_direct_elec * source["lcoe"]
    synthesis_cost = synthesis_annual * synthesis_capacity_kg_h
    dac_capital_cost = dac_annual * dac_capacity_kg_h
    compressor_cost = compressor_annual * compressor_capacity_kg_h
    heat_pump_cost = heat_pump_annual * heat_pump_capacity_kw_th
    sorbent_cost = params["sorbent_cost"] * co2_required
    total_cost = (
        h2_cost + elec_cost + synthesis_cost + dac_capital_cost
        + compressor_cost + heat_pump_cost + sorbent_cost
    )

    caps = scale_h2_capacities(source, h2_required, h2_basis)
    common = {
        **caps,
        "battery_energy_capacity_kW": 0.0,
        "battery_storage_capacity_kWh": 0.0,
        "heat_pump_capacity_kW_th": heat_pump_capacity_kw_th,
        "thermal_storage_capacity_kWh_th": 0.0,
        "hydrogen_storage_capacity_kgH2": 0.0,
        "dac_capacity_kgCO2_per_h": dac_capacity_kg_h,
        "co2_compressor_capacity_kgCO2_per_h": compressor_capacity_kg_h,
        "co2_storage_capacity_kg": 0.0,
        "total_CO2_captured_kg": co2_required,
        "total_hydrogen_production_kg": h2_required,
        "electrolyzer_utilization_percent": 100.0,
        "dac_utilization_percent": 100.0,
        "levelized_dac_cost_per_tCO2": (dac_capital_cost + compressor_cost) / (co2_required / 1000.0),
        "levelized_elec_cost_per_kWh": source["lcoe"],
        "levelized_heat_cost_per_kWh_th": (
            heat_pump_cost + heat_pump_elec_kwh * source["lcoe"]
        ) / heat_required_kwh_th if heat_required_kwh_th > 0 else 0.0,
        "levelized_h2_cost_per_kg": source["lcoh"],
        "direct_electricity_consumption_kwh": direct_elec_kwh,
        "dac_electricity_consumption_kwh": dac_elec_kwh,
        "co2_compression_electricity_consumption_kwh": compressor_elec_kwh,
        "heat_pump_electricity_consumption_kwh": heat_pump_elec_kwh,
        "total_direct_electricity_consumption_kwh": total_direct_elec,
        "static_h2_cost_component": h2_cost,
        "static_electricity_cost_component": elec_cost,
        "static_synthesis_cost_component": synthesis_cost,
        "static_dac_cost_component": dac_capital_cost,
        "static_co2_compressor_cost_component": compressor_cost,
        "static_heat_pump_cost_component": heat_pump_cost,
        "static_sorbent_cost_component": sorbent_cost,
        "selected_RE_source": source_name,
    }
    if product == "methanol":
        return {
            "wind_capacity_kW": caps["wind_capacity"],
            "pv_capacity_kW": caps["pv_capacity"],
            "electrolyzer_capacity_AE_kW": caps["electrolyzer_capacity_AE"],
            "electrolyzer_capacity_PEM_kW": caps["electrolyzer_capacity_PEM"],
            **{k: v for k, v in common.items() if k not in caps},
            "methanol_synthesis_capacity_tpy": target / 1000.0,
            "methanol_storage_capacity_kg_per_h": 0.0,
            "total_methanol_production_kg": target,
            "methanol_utilization_percent": 100.0,
            "levelized_methanol_cost_per_ton": total_cost / target * 1000.0,
        }
    return {
        "wind_capacity_kW": caps["wind_capacity"],
        "pv_capacity_kW": caps["pv_capacity"],
        "electrolyzer_capacity_AE_kW": caps["electrolyzer_capacity_AE"],
        "electrolyzer_capacity_PEM_kW": caps["electrolyzer_capacity_PEM"],
        **{k: v for k, v in common.items() if k not in caps},
        "FTL_synthesis_capacity_tpy": target / 1000.0,
        "FTL_storage_capacity_kg_per_h": 0.0,
        "total_FTL_production_kg": target,
        "FTL_utilization_percent": 100.0,
        "levelized_FTL_cost_per_ton": total_cost / target * 1000.0,
        "objective_value": total_cost,
    }


PRODUCT_CALCULATORS = {
    "ammonia": calc_ammonia,
    "methanol": lambda row, source_name, source: calc_carbon_product(row, "methanol", source_name, source),
    "ftl": lambda row, source_name, source: calc_carbon_product(row, "ftl", source_name, source),
    "saf": lambda row, source_name, source: calc_carbon_product(row, "ftl", source_name, source),
}


def product_output_prefix(product):
    if product == "ammonia":
        return "ammonia_results"
    if product == "methanol":
        return "methanol_results"
    return "ftl_results"


def prefixed_result(prefix, result):
    return {f"{prefix}_{key}": value for key, value in result.items()}


def build_entry(row, product, source_mode):
    selected_source_name = str(row.get("selected_RE_source", "selected") or "selected")
    sources = {
        "selected": source_values(row, "selected"),
        "wind": source_values(row, "wind"),
        "pv": source_values(row, "pv"),
    }
    if source_mode in {"selected", "all"}:
        source_name = selected_source_name
        source = sources["selected"]
    elif source_mode in {"wind", "pv"}:
        source_name = source_mode
        source = sources[source_mode]
    else:
        wind_cost = PRODUCT_CALCULATORS[product](row, "wind", sources["wind"])
        pv_cost = PRODUCT_CALCULATORS[product](row, "pv", sources["pv"])
        cost_key = {
            "ammonia": "levelized_ammonia_cost_per_ton",
            "methanol": "levelized_methanol_cost_per_ton",
            "ftl": "levelized_FTL_cost_per_ton",
            "saf": "levelized_FTL_cost_per_ton",
        }[product]
        if wind_cost[cost_key] <= pv_cost[cost_key]:
            source_name = "wind"
            source = sources["wind"]
        else:
            source_name = "pv"
            source = sources["pv"]

    result = PRODUCT_CALCULATORS[product](row, source_name, source)
    base = {
        "orig_idx": int(row["orig_idx"]),
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "region": row.get("region", 0),
        "wind_cost": row.get("wind_cost", 0),
        "pv_cost": row.get("pv_cost", 0),
        "hydrogen_scenario": row["scenario"],
        "hydrogen_selected_RE_source": selected_source_name,
        "hydrogen_LCOE_per_kWh": sources["selected"]["lcoe"],
        "hydrogen_LCOH_per_kg": sources["selected"]["lcoh"],
        "wind_LCOE_per_kWh": sources["wind"]["lcoe"],
        "pv_LCOE_per_kWh": sources["pv"]["lcoe"],
        "wind_LCOH_per_kg": sources["wind"]["lcoh"],
        "pv_LCOH_per_kg": sources["pv"]["lcoh"],
    }
    base.update(result)
    if source_mode == "all":
        for variant in ("wind", "pv"):
            variant_result = PRODUCT_CALCULATORS[product](row, variant, sources[variant])
            base.update(prefixed_result(f"{variant}_based", variant_result))
    return base


def process_product_chunk(config, product, scenario, chunk_idx):
    import pandas as pd

    offset = chunk_idx * 60
    input_path = os.path.join(
        config["input_dir"],
        config["input_template"].format(offset=offset, scenario=scenario),
    )
    if not os.path.exists(input_path):
        logger.warning("Missing input file: %s", input_path)
        return None

    output_dir = os.path.join(config["output_dir"], product)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(
        output_dir,
        config["output_template"].format(
            product_prefix=product_output_prefix(product),
            offset=offset,
            scenario=scenario,
        ),
    )

    h2_df = pd.read_csv(input_path)
    h2_df["scenario"] = scenario
    cost_col = config["h2_cost_column"]
    if cost_col in h2_df.columns:
        h2_df = h2_df[pd.to_numeric(h2_df[cost_col], errors="coerce") > 0].copy()

    if os.path.exists(output_path) and not config["overwrite"]:
        existing_df = pd.read_csv(output_path)
        processed = set(existing_df["orig_idx"].tolist()) if "orig_idx" in existing_df.columns else set()
        logger.info("%s chunk %s %s: loaded %s rows", product, chunk_idx, scenario, len(existing_df))
    else:
        existing_df = pd.DataFrame()
        processed = set()

    todo_df = h2_df[~h2_df["orig_idx"].isin(processed)]
    if todo_df.empty:
        logger.info("%s chunk %s %s: all points processed", product, chunk_idx, scenario)
        return output_path

    results = []
    for idx, row in enumerate(todo_df.to_dict("records"), start=1):
        entry = build_entry(row, product, config["source_mode"])
        results.append(entry)
        if idx % CHECKPOINT_INTERVAL == 0:
            checkpoint_df = pd.concat([existing_df, pd.DataFrame(results)], ignore_index=True)
            checkpoint_df.to_csv(output_path, index=False)
            existing_df = checkpoint_df
            results = []
            logger.info("%s chunk %s %s: checkpoint %s rows", product, chunk_idx, scenario, len(existing_df))

    final_df = pd.concat([existing_df, pd.DataFrame(results)], ignore_index=True)
    final_df.to_csv(output_path, index=False)
    logger.info("%s chunk %s %s: saved %s rows to %s", product, chunk_idx, scenario, len(final_df), output_path)
    return output_path


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="Static ammonia, methanol, and FTL/SAF assessment from precomputed H2 LCOE/LCOH chunk files."
    )
    parser.add_argument("--input-dir", default="/p/tmp/qianzhiz/GreenH2/Output_static")
    parser.add_argument("--output-dir", default="/p/tmp/qianzhiz/GreenH2/Output_static_downstream")
    parser.add_argument("--input-template", default="hydrogen_results_{offset}_{scenario}.csv")
    parser.add_argument("--output-template", default="{product_prefix}_{offset}_{scenario}_Static.csv")
    parser.add_argument("--scenarios", default="auto")
    parser.add_argument("--products", default="ammonia,methanol,ftl")
    parser.add_argument("--chunks", default="0-23")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--source-mode", choices=["selected", "wind", "pv", "min-product-cost", "all"], default="all")
    parser.add_argument("--h2-cost-column", default="levelized_hydrogen_production_cost_per_kg")
    parser.add_argument("--overwrite", action="store_true", help="忽略已有 checkpoint，重新写出完整结果")
    args = parser.parse_args()

    chunks = parse_chunks(args.chunks)
    if args.scenarios.strip().lower() == "auto":
        scenarios = discover_scenarios(args.input_dir, args.input_template, chunks)
        if not scenarios:
            raise SystemExit(f"No hydrogen scenarios discovered in {args.input_dir}")
        logger.info("Discovered scenarios: %s", ", ".join(scenarios))
    else:
        scenarios = parse_csv_list(args.scenarios)

    products = parse_csv_list(args.products)
    invalid_products = [product for product in products if product not in PRODUCT_CALCULATORS]
    if invalid_products:
        raise SystemExit(f"Unsupported products: {', '.join(invalid_products)}")

    config = vars(args).copy()
    tasks = [(product, scenario, chunk_idx) for product in products for scenario in scenarios for chunk_idx in chunks]
    workers = max(1, min(args.workers, len(tasks)))

    if workers == 1:
        for product, scenario, chunk_idx in tasks:
            process_product_chunk(config, product, scenario, chunk_idx)
        return

    failures = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_task = {
            executor.submit(process_product_chunk, config, product, scenario, chunk_idx): (product, scenario, chunk_idx)
            for product, scenario, chunk_idx in tasks
        }
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                future.result()
            except Exception as exc:
                failures.append((task, exc))
                logger.exception("Failed task: %s", task)

    if failures:
        failed = ", ".join(f"{p}:{s}:chunk{c}" for (p, s, c), _ in failures)
        raise SystemExit(f"Failed tasks: {failed}")


if __name__ == "__main__":
    main()
