#!/usr/bin/env python3
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
import os

import numpy as np


logger = logging.getLogger(__name__)

CHECKPOINT_INTERVAL = 100

SCENARIOS = {
    "RegionRE_2030": {
        "cost_year": "2030ATB",
        "output_tag": "RegionRE_2030_StaticLCOE",
        "battery_energy_cost": 200,
        "battery_storage_cost": 200,
        "electrolyzer_cost_AE": 430,
        "electrolyzer_cost_PEM": 650,
        "hydrogen_storage_cost": 1750,
        "default_electrolyzer": "AE",
    },
    "RegionRE_LowAE": {
        "cost_year": "2035ATB",
        "output_tag": "RegionRE_LowAE_StaticLCOE",
        "battery_energy_cost": 100,
        "battery_storage_cost": 100,
        "electrolyzer_cost_AE": 250,
        "electrolyzer_cost_PEM": 500,
        "hydrogen_storage_cost": 1000,
        "default_electrolyzer": "AE",
    },
    "RegionRE_LowAE_2040": {
        "cost_year": "2040ATB",
        "output_tag": "RegionRE_LowAE_2040_StaticLCOE",
        "battery_energy_cost": 100,
        "battery_storage_cost": 100,
        "electrolyzer_cost_AE": 250,
        "electrolyzer_cost_PEM": 500,
        "hydrogen_storage_cost": 1000,
        "default_electrolyzer": "AE",
    },
    "RegionRE_LowAE_2050": {
        "cost_year": "2050ATB",
        "output_tag": "RegionRE_LowAE_2050_StaticLCOE",
        "battery_energy_cost": 50,
        "battery_storage_cost": 50,
        "electrolyzer_cost_AE": 250,
        "electrolyzer_cost_PEM": 350,
        "hydrogen_storage_cost": 800,
        "default_electrolyzer": "AE",
    },
}

RESULT_COLUMNS = [
    "orig_idx",
    "latitude",
    "longitude",
    "region",
    "wind_cost",
    "pv_cost",
    "wind_capacity",
    "pv_capacity",
    "battery_energy_capacity",
    "battery_storage_capacity",
    "hydrogen_storage_capacity",
    "electrolyzer_capacity_AE",
    "electrolyzer_capacity_PEM",
    "total_hydrogen_production_kg",
    "electrolyzer_utilization_hours_percent",
    "levelized_Elec_cost_per_kWh",
    "levelized_H2_cost_per_kgH2",
    "levelized_hydrogen_production_cost_per_kg",
    "LCOE_per_kWh",
    "LCOH_per_kg",
    "wind_LCOE_per_kWh",
    "pv_LCOE_per_kWh",
    "wind_LCOH_per_kg",
    "pv_LCOH_per_kg",
    "wind_based_wind_capacity",
    "wind_based_pv_capacity",
    "wind_based_electrolyzer_capacity_AE",
    "wind_based_electrolyzer_capacity_PEM",
    "pv_based_wind_capacity",
    "pv_based_pv_capacity",
    "pv_based_electrolyzer_capacity_AE",
    "pv_based_electrolyzer_capacity_PEM",
    "selected_RE_source",
]


def capital_recovery_factor(discount_rate, lifetime):
    return discount_rate / (1 - (1 + discount_rate) ** -lifetime)


def annualized_cost(capex, discount_rate, lifetime, om_rate=0.03):
    return capex * capital_recovery_factor(discount_rate, lifetime) + capex * om_rate


def clean_profile(values):
    values = np.asarray(values, dtype=float)
    values = np.where(np.isfinite(values), values, 0.0)
    return np.maximum(values, 0.0)


def zero_result():
    return {
        "wind_capacity": 0.0,
        "pv_capacity": 0.0,
        "battery_energy_capacity": 0.0,
        "battery_storage_capacity": 0.0,
        "hydrogen_storage_capacity": 0.0,
        "electrolyzer_capacity_AE": 0.0,
        "electrolyzer_capacity_PEM": 0.0,
        "total_hydrogen_production_kg": 0.0,
        "electrolyzer_utilization_hours_percent": 0.0,
        "levelized_Elec_cost_per_kWh": 0.0,
        "levelized_H2_cost_per_kgH2": 0.0,
        "levelized_hydrogen_production_cost_per_kg": 0.0,
        "LCOE_per_kWh": 0.0,
        "LCOH_per_kg": 0.0,
        "wind_LCOE_per_kWh": 0.0,
        "pv_LCOE_per_kWh": 0.0,
        "wind_LCOH_per_kg": 0.0,
        "pv_LCOH_per_kg": 0.0,
        "wind_based_wind_capacity": 0.0,
        "wind_based_pv_capacity": 0.0,
        "wind_based_electrolyzer_capacity_AE": 0.0,
        "wind_based_electrolyzer_capacity_PEM": 0.0,
        "pv_based_wind_capacity": 0.0,
        "pv_based_pv_capacity": 0.0,
        "pv_based_electrolyzer_capacity_AE": 0.0,
        "pv_based_electrolyzer_capacity_PEM": 0.0,
        "selected_RE_source": "",
    }


def static_lcoe_hydrogen_system(
    wind_output,
    pv_output,
    target_hydrogen_production,
    wind_cost,
    pv_cost,
    electrolyzer_cost_AE,
    electrolyzer_cost_PEM,
    electrolyzer_eff_AE,
    electrolyzer_eff_PEM,
    discount_rate,
    wind_lifetime,
    pv_lifetime,
    electrolyzer_lifetime_AE,
    electrolyzer_lifetime_PEM,
    re_source,
    electrolyzer,
):
    wind_output = clean_profile(wind_output)
    pv_output = clean_profile(pv_output)

    wind_full_load_hours = float(wind_output.sum())
    pv_full_load_hours = float(pv_output.sum())

    wind_annual_cost = annualized_cost(wind_cost, discount_rate, wind_lifetime)
    pv_annual_cost = annualized_cost(pv_cost, discount_rate, pv_lifetime)
    electrolyzer_annual_cost_AE = annualized_cost(
        electrolyzer_cost_AE, discount_rate, electrolyzer_lifetime_AE
    )
    electrolyzer_annual_cost_PEM = annualized_cost(
        electrolyzer_cost_PEM, discount_rate, electrolyzer_lifetime_PEM
    )

    wind_lcoe = wind_annual_cost / wind_full_load_hours if wind_full_load_hours > 0 else np.inf
    pv_lcoe = pv_annual_cost / pv_full_load_hours if pv_full_load_hours > 0 else np.inf

    technology_options = {
        "AE": {
            "efficiency": electrolyzer_eff_AE,
            "annual_cost": electrolyzer_annual_cost_AE,
        },
        "PEM": {
            "efficiency": electrolyzer_eff_PEM,
            "annual_cost": electrolyzer_annual_cost_PEM,
        },
    }

    if electrolyzer == "auto":
        raise ValueError("electrolyzer must be resolved before static calculation")

    if electrolyzer == "min-cost":
        selected_costs = {}
        for tech, params in technology_options.items():
            electricity_per_kg = 120.0 / (params["efficiency"] * 3.6)
            annual_electricity = target_hydrogen_production * electricity_per_kg
            electrolyzer_capacity_for_tech = annual_electricity / 8760.0

            def lcoh_for_source(source_lcoe, source_full_load_hours):
                if not np.isfinite(source_lcoe) or source_full_load_hours <= 0:
                    return np.inf
                return (
                    source_lcoe * annual_electricity
                    + params["annual_cost"] * electrolyzer_capacity_for_tech
                ) / target_hydrogen_production

            wind_cost_per_kg = lcoh_for_source(wind_lcoe, wind_full_load_hours)
            pv_cost_per_kg = lcoh_for_source(pv_lcoe, pv_full_load_hours)

            if re_source == "min-lcoe":
                selected_costs[tech] = wind_cost_per_kg if wind_lcoe <= pv_lcoe else pv_cost_per_kg
            elif re_source == "min-lcoh":
                selected_costs[tech] = min(wind_cost_per_kg, pv_cost_per_kg)
            elif re_source == "wind":
                selected_costs[tech] = wind_cost_per_kg
            elif re_source == "pv":
                selected_costs[tech] = pv_cost_per_kg
            else:
                raise ValueError(f"Unsupported re_source: {re_source}")

        electrolyzer = min(selected_costs, key=selected_costs.get)

    if electrolyzer not in technology_options:
        raise ValueError(f"Unsupported electrolyzer: {electrolyzer}")

    electrolyzer_efficiency = technology_options[electrolyzer]["efficiency"]
    electrolyzer_annual_cost = technology_options[electrolyzer]["annual_cost"]
    electricity_per_kg = 120.0 / (electrolyzer_efficiency * 3.6)
    annual_electricity_demand = target_hydrogen_production * electricity_per_kg
    electrolyzer_capacity = annual_electricity_demand / 8760.0

    def source_lcoh(source_lcoe, source_full_load_hours):
        if not np.isfinite(source_lcoe) or source_full_load_hours <= 0:
            return np.inf, 0.0
        renewable_capacity = annual_electricity_demand / source_full_load_hours
        annual_cost = (
            source_lcoe * annual_electricity_demand
            + electrolyzer_annual_cost * electrolyzer_capacity
        )
        return annual_cost / target_hydrogen_production, renewable_capacity

    wind_lcoh, wind_based_capacity = source_lcoh(wind_lcoe, wind_full_load_hours)
    pv_lcoh, pv_based_capacity = source_lcoh(pv_lcoe, pv_full_load_hours)
    wind_based_electrolyzer_capacity_AE = (
        electrolyzer_capacity if electrolyzer == "AE" and np.isfinite(wind_lcoh) else 0.0
    )
    wind_based_electrolyzer_capacity_PEM = (
        electrolyzer_capacity if electrolyzer == "PEM" and np.isfinite(wind_lcoh) else 0.0
    )
    pv_based_electrolyzer_capacity_AE = (
        electrolyzer_capacity if electrolyzer == "AE" and np.isfinite(pv_lcoh) else 0.0
    )
    pv_based_electrolyzer_capacity_PEM = (
        electrolyzer_capacity if electrolyzer == "PEM" and np.isfinite(pv_lcoh) else 0.0
    )

    if re_source == "min-lcoe":
        selected_source = "wind" if wind_lcoe <= pv_lcoe else "pv"
    elif re_source == "min-lcoh":
        selected_source = "wind" if wind_lcoh <= pv_lcoh else "pv"
    else:
        selected_source = re_source

    if selected_source == "wind":
        selected_lcoe = wind_lcoe
        selected_full_load_hours = wind_full_load_hours
        levelized_h2_cost = wind_lcoh
        selected_capacity = wind_based_capacity
    elif selected_source == "pv":
        selected_lcoe = pv_lcoe
        selected_full_load_hours = pv_full_load_hours
        levelized_h2_cost = pv_lcoh
        selected_capacity = pv_based_capacity
    else:
        raise ValueError(f"Unsupported re_source: {re_source}")

    if not np.isfinite(selected_lcoe) or selected_full_load_hours <= 0:
        return zero_result()

    wind_capacity = selected_capacity if selected_source == "wind" else 0.0
    pv_capacity = selected_capacity if selected_source == "pv" else 0.0
    electrolyzer_capacity_AE = electrolyzer_capacity if electrolyzer == "AE" else 0.0
    electrolyzer_capacity_PEM = electrolyzer_capacity if electrolyzer == "PEM" else 0.0

    return {
        "wind_capacity": wind_capacity,
        "pv_capacity": pv_capacity,
        "battery_energy_capacity": 0.0,
        "battery_storage_capacity": 0.0,
        "hydrogen_storage_capacity": 0.0,
        "electrolyzer_capacity_AE": electrolyzer_capacity_AE,
        "electrolyzer_capacity_PEM": electrolyzer_capacity_PEM,
        "total_hydrogen_production_kg": float(target_hydrogen_production),
        "electrolyzer_utilization_hours_percent": 100.0,
        "levelized_Elec_cost_per_kWh": selected_lcoe,
        "levelized_H2_cost_per_kgH2": levelized_h2_cost,
        "levelized_hydrogen_production_cost_per_kg": levelized_h2_cost,
        "LCOE_per_kWh": selected_lcoe,
        "LCOH_per_kg": levelized_h2_cost,
        "wind_LCOE_per_kWh": 0.0 if not np.isfinite(wind_lcoe) else wind_lcoe,
        "pv_LCOE_per_kWh": 0.0 if not np.isfinite(pv_lcoe) else pv_lcoe,
        "wind_LCOH_per_kg": 0.0 if not np.isfinite(wind_lcoh) else wind_lcoh,
        "pv_LCOH_per_kg": 0.0 if not np.isfinite(pv_lcoh) else pv_lcoh,
        "wind_based_wind_capacity": wind_based_capacity,
        "wind_based_pv_capacity": 0.0,
        "wind_based_electrolyzer_capacity_AE": wind_based_electrolyzer_capacity_AE,
        "wind_based_electrolyzer_capacity_PEM": wind_based_electrolyzer_capacity_PEM,
        "pv_based_wind_capacity": 0.0,
        "pv_based_pv_capacity": pv_based_capacity,
        "pv_based_electrolyzer_capacity_AE": pv_based_electrolyzer_capacity_AE,
        "pv_based_electrolyzer_capacity_PEM": pv_based_electrolyzer_capacity_PEM,
        "selected_RE_source": selected_source,
    }


def regional_cost_path_from_args(path_arg):
    if path_arg:
        return path_arg

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.abspath(os.path.join(script_dir, ".."))
    default_path = os.path.join(project_dir, "RegionalCost.csv")
    if os.path.exists(default_path):
        return default_path

    cwd_path = os.path.abspath("RegionalCost.csv")
    if os.path.exists(cwd_path):
        return cwd_path

    return default_path


def load_regional_cost_maps(regional_cost_path, cost_year):
    import pandas as pd

    regional_cost_df = pd.read_csv(regional_cost_path)
    wind_df = regional_cost_df[
        (regional_cost_df["Type"] == "Onshore Wind")
        & (regional_cost_df["Cost Type 1"] == "Total installed cost")
    ]
    pv_df = regional_cost_df[
        (regional_cost_df["Type"] == "Solar PV")
        & (regional_cost_df["Cost Type 1"] == "Total installed cost")
    ]
    return (
        wind_df.set_index("region_code")[cost_year].to_dict(),
        pv_df.set_index("region_code")[cost_year].to_dict(),
    )


def parse_chunks(chunks_text):
    chunks = []
    for part in chunks_text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            step = 1 if end >= start else -1
            chunks.extend(range(start, end + step, step))
        else:
            chunks.append(int(part))
    return list(dict.fromkeys(chunks))


def calculate_chunk(config, chunk_idx):
    import pandas as pd
    import xarray as xr

    scenario = SCENARIOS[config["scenario"]]
    electrolyzer = config["electrolyzer"]
    if electrolyzer == "auto":
        electrolyzer = scenario["default_electrolyzer"]

    regional_cost_path = regional_cost_path_from_args(config["regional_cost_csv"])
    wind_cost_map, pv_cost_map = load_regional_cost_maps(regional_cost_path, scenario["cost_year"])

    offset = chunk_idx * 60
    ds_path = os.path.join(config["input_dir"], f"average_2023_segment_{offset}.nc")
    coords_path = os.path.join(
        config["input_dir"],
        "NoWater_valid_coords_with_region",
        f"NoWater_valid_coords_with_region_{offset}.csv",
    )

    data = xr.open_dataset(ds_path)
    valid_coords_df = pd.read_csv(coords_path)
    valid_coords_df = valid_coords_df.reset_index().rename(columns={"index": "orig_idx"})
    total_points = len(valid_coords_df)

    os.makedirs(config["output_dir"], exist_ok=True)
    output_tag = config["output_tag"] or scenario["output_tag"]
    out_csv = os.path.join(config["output_dir"], f"hydrogen_results_{offset}_{output_tag}.csv")

    if os.path.exists(out_csv):
        existing_df = pd.read_csv(out_csv)
        processed = set(existing_df["orig_idx"].tolist())
        logger.info(
            "Chunk %s: loaded checkpoint with %s points, skipping processed.",
            chunk_idx,
            len(existing_df),
        )
    else:
        existing_df = pd.DataFrame(columns=RESULT_COLUMNS)
        processed = set()

    todo_df = valid_coords_df[~valid_coords_df["orig_idx"].isin(processed)]
    if todo_df.empty:
        logger.info("Chunk %s: all points already processed, exiting.", chunk_idx)
        data.close()
        return out_csv

    logger.info(
        "Chunk %s: static LCOE calculation: scenario=%s, cost_year=%s, re_source=%s, electrolyzer=%s",
        chunk_idx,
        config["scenario"],
        scenario["cost_year"],
        config["re_source"],
        electrolyzer,
    )

    results_list = []
    for idx, row in enumerate(todo_df.itertuples(index=False), start=1):
        orig_idx = row.orig_idx
        lat_idx = int(row.latitude_index)
        lon_idx = int(row.longitude_index)
        region_code = int(row.Region) if not isinstance(row.Region, int) else row.Region
        print(
            f"Chunk {chunk_idx}: Processing [{idx}/{len(todo_df)}] orig_idx={orig_idx}, "
            f"region={region_code}, lat={lat_idx}, lon={lon_idx}",
            flush=True,
        )

        wind_out = data["CF_wind_avg"][:, lat_idx, lon_idx].values
        pv_out = data["CF_pv_avg"][:, lat_idx, lon_idx].values

        wind_cost_i = wind_cost_map.get(region_code, 800)
        pv_cost_i = pv_cost_map.get(region_code, 250)

        res = static_lcoe_hydrogen_system(
            wind_out,
            pv_out,
            target_hydrogen_production=config["target_hydrogen_production"],
            wind_cost=wind_cost_i,
            pv_cost=pv_cost_i,
            electrolyzer_cost_AE=scenario["electrolyzer_cost_AE"],
            electrolyzer_cost_PEM=scenario["electrolyzer_cost_PEM"],
            electrolyzer_eff_AE=config["electrolyzer_eff_AE"],
            electrolyzer_eff_PEM=config["electrolyzer_eff_PEM"],
            discount_rate=config["discount_rate"],
            wind_lifetime=config["wind_lifetime"],
            pv_lifetime=config["pv_lifetime"],
            electrolyzer_lifetime_AE=config["electrolyzer_lifetime_AE"],
            electrolyzer_lifetime_PEM=config["electrolyzer_lifetime_PEM"],
            re_source=config["re_source"],
            electrolyzer=electrolyzer,
        )

        entry = {
            "orig_idx": orig_idx,
            "latitude": lat_idx,
            "longitude": lon_idx,
            "region": region_code,
            "wind_cost": wind_cost_i,
            "pv_cost": pv_cost_i,
        }
        entry.update(res)
        results_list.append(entry)
        print(
            "Chunk {}: Completed orig_idx={}: cost_per_kg={:.2f} USD/kg".format(
                chunk_idx, orig_idx, res["levelized_hydrogen_production_cost_per_kg"]
            ),
            flush=True,
        )

        if idx % CHECKPOINT_INTERVAL == 0:
            checkpoint_df = pd.concat([existing_df, pd.DataFrame(results_list)], ignore_index=True)
            checkpoint_df = checkpoint_df.reindex(columns=RESULT_COLUMNS)
            checkpoint_df.to_csv(out_csv, index=False)
            logger.info("Chunk %s: checkpoint saved after %s total points.", chunk_idx, len(checkpoint_df))
            existing_df = checkpoint_df
            results_list = []

    final_df = pd.concat([existing_df, pd.DataFrame(results_list)], ignore_index=True)
    final_df = final_df.reindex(columns=RESULT_COLUMNS)
    final_df.to_csv(out_csv, index=False)
    logger.info(
        "Chunk %s: final results saved to %s (%s/%s points)",
        chunk_idx,
        out_csv,
        len(final_df),
        total_points,
    )
    data.close()
    return out_csv


def build_parser():
    parser = argparse.ArgumentParser(
        description="Calculate static LCOE-based H2 cost for one or more longitude chunks"
    )
    parser.add_argument("--chunk", type=int, default=None, help="Chunk index (0-based) 对应 60° 段")
    parser.add_argument(
        "--chunks",
        type=str,
        default=None,
        help="多个 chunk，例如 0-23 或 0,1,2,5-8；设置后可并行运行",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="并行进程数；每个进程计算一个 chunk",
    )
    parser.add_argument("--input-dir", type=str, default="/path/to/data", help="输入数据根目录")
    parser.add_argument("--output-dir", type=str, default="/path/to/output", help="输出结果根目录")
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default="RegionRE_LowAE_2050",
        help="成本和输出命名情景",
    )
    parser.add_argument(
        "--regional-cost-csv",
        type=str,
        default=None,
        help="RegionalCost.csv 路径；默认使用 GreenH2/RegionalCost.csv",
    )
    parser.add_argument(
        "--target-hydrogen-production",
        type=float,
        default=10000.0,
        help="年制氢量目标，单位 kg/年",
    )
    parser.add_argument(
        "--re-source",
        choices=["min-lcoh", "min-lcoe", "wind", "pv"],
        default="min-lcoh",
        help="静态计算采用的可再生电源；min-lcoh 表示逐点选择风/光中 LCOH 更低者",
    )
    parser.add_argument(
        "--electrolyzer",
        choices=["auto", "AE", "PEM", "min-cost"],
        default="auto",
        help="静态计算采用的电解槽；auto 使用情景默认技术；当前所有情景默认 AE",
    )
    parser.add_argument("--discount-rate", type=float, default=0.07)
    parser.add_argument("--wind-lifetime", type=float, default=30)
    parser.add_argument("--pv-lifetime", type=float, default=40)
    parser.add_argument("--electrolyzer-lifetime-AE", type=float, default=25)
    parser.add_argument("--electrolyzer-lifetime-PEM", type=float, default=25)
    parser.add_argument("--electrolyzer-eff-AE", type=float, default=0.65)
    parser.add_argument("--electrolyzer-eff-PEM", type=float, default=0.7)
    parser.add_argument(
        "--output-tag",
        type=str,
        default=None,
        help="自定义输出文件标签；默认由 scenario 生成",
    )
    return parser


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = build_parser()
    args = parser.parse_args()

    if args.chunks:
        chunks = parse_chunks(args.chunks)
    elif args.chunk is not None:
        chunks = [args.chunk]
    else:
        parser.error("必须指定 --chunk 或 --chunks")

    if not chunks:
        parser.error("--chunks 没有解析出任何 chunk")

    workers = max(1, min(args.workers, len(chunks)))
    config = vars(args).copy()

    if workers == 1 or len(chunks) == 1:
        for chunk_idx in chunks:
            calculate_chunk(config, chunk_idx)
        return

    logger.info("Running %s chunks with %s worker processes.", len(chunks), workers)
    failures = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_chunk = {
            executor.submit(calculate_chunk, config, chunk_idx): chunk_idx for chunk_idx in chunks
        }
        for future in as_completed(future_to_chunk):
            chunk_idx = future_to_chunk[future]
            try:
                out_csv = future.result()
                logger.info("Chunk %s finished: %s", chunk_idx, out_csv)
            except Exception as exc:
                failures.append((chunk_idx, exc))
                logger.exception("Chunk %s failed.", chunk_idx)

    if failures:
        failed_chunks = ", ".join(str(chunk_idx) for chunk_idx, _ in failures)
        raise SystemExit(f"Failed chunks: {failed_chunks}")


if __name__ == "__main__":
    main()
