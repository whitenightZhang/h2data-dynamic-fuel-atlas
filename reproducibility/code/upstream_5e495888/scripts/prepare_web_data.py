from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

import pandas as pd


REPO_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_DIR / "docs" / "data"

YEARS = [2030, 2035, 2050]
SCENARIO_TO_YEAR = {
    "2030": 2030,
    "2035": 2035,
    "2050": 2050,
}

POINT_SCHEMA = [
    "lat",
    "lon",
    "cost_8760",
    "absolute_underestimate",
    "underestimation_pct",
    "region",
]

PRODUCTS = {
    "hydrogen": {
        "label": "Hydrogen",
        "cost_unit": "USD kg-1 H2",
        "cost_kind": "hydrogen",
        "bias_unit": "USD kg-1 H2",
    },
    "ammonia": {
        "label": "Green ammonia",
        "cost_unit": "USD t-1 NH3",
        "cost_kind": "fuel",
        "bias_unit": "USD t-1 NH3",
    },
    "methanol": {
        "label": "e-Methanol",
        "cost_unit": "USD t-1 MeOH",
        "cost_kind": "fuel",
        "bias_unit": "USD t-1 MeOH",
    },
    "saf": {
        "label": "e-SAF",
        "cost_unit": "USD t-1 fuel",
        "cost_kind": "fuel",
        "bias_unit": "USD t-1 fuel",
    },
}


def n(value, digits: int = 4):
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return round(v, digits)


def s(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


def dump_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def read_csv(path: Path, usecols: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, usecols=usecols, low_memory=False)


def summarize_numeric(df: pd.DataFrame, cost_col: str, bias_col: str) -> dict:
    cost = pd.to_numeric(df[cost_col], errors="coerce")
    bias = pd.to_numeric(df[bias_col], errors="coerce")
    return {
        "count": int(len(df)),
        "cost_min": n(cost.min()),
        "cost_p10": n(cost.quantile(0.10)),
        "cost_median": n(cost.median()),
        "cost_p90": n(cost.quantile(0.90)),
        "cost_max": n(cost.max()),
        "bias_pct_median": n(bias.median(), 3),
        "bias_pct_p90": n(bias.quantile(0.90), 3),
    }


def build_hydrogen_files(metadata: dict, h2_bias_path: Path, data_dir: Path) -> None:
    source = read_csv(
        h2_bias_path,
        [
            "latitude",
            "longitude",
            "scenario",
            "hourly8760_cost_per_kg",
            "absolute_underestimate_per_kg",
            "relative_underestimate_percent",
            "region_name",
        ],
    )
    source["year"] = source["scenario"].map(SCENARIO_TO_YEAR)
    source = source.dropna(subset=["year"]).copy()
    source["year"] = source["year"].astype(int)
    source["cost_8760"] = pd.to_numeric(source["hourly8760_cost_per_kg"], errors="coerce")
    source["absolute_underestimate"] = pd.to_numeric(source["absolute_underestimate_per_kg"], errors="coerce")
    source["underestimation_pct"] = pd.to_numeric(source["relative_underestimate_percent"], errors="coerce")

    metadata["products"]["hydrogen"]["files"] = {}
    for year in YEARS:
        part = source[source["year"].eq(year)].copy()
        rows = [
            [
                n(r.latitude, 4),
                n(r.longitude, 4),
                n(r.cost_8760, 4),
                n(r.absolute_underestimate, 4),
                n(r.underestimation_pct, 3),
                s(r.region_name),
            ]
            for r in part.itertuples(index=False)
        ]
        file_name = f"hydrogen_{year}.json"
        dump_json(data_dir / file_name, {"product": "hydrogen", "year": year, "columns": POINT_SCHEMA, "rows": rows})
        metadata["products"]["hydrogen"]["files"][str(year)] = file_name
        metadata["products"]["hydrogen"]["summary"][str(year)] = summarize_numeric(part, "cost_8760", "underestimation_pct")


def build_product_files(metadata: dict, product_node_path: Path, data_dir: Path) -> None:
    source = read_csv(
        product_node_path,
        [
            "latitude",
            "longitude",
            "cost_8760_usd_t",
            "cost_static_usd_t",
            "fuel",
            "year",
            "underestimation_pct",
            "region_name",
        ],
    )
    source["year"] = pd.to_numeric(source["year"], errors="coerce").astype(int)
    source["cost_8760"] = pd.to_numeric(source["cost_8760_usd_t"], errors="coerce")
    source["absolute_underestimate"] = source["cost_8760"] - pd.to_numeric(source["cost_static_usd_t"], errors="coerce")
    source["underestimation_pct"] = pd.to_numeric(source["underestimation_pct"], errors="coerce")

    for fuel in ["ammonia", "methanol", "saf"]:
        metadata["products"][fuel]["files"] = {}
        for year in YEARS:
            part = source[source["fuel"].eq(fuel) & source["year"].eq(year)].copy()
            rows = [
                [
                    n(r.latitude, 4),
                    n(r.longitude, 4),
                    n(r.cost_8760, 4),
                    n(r.absolute_underestimate, 4),
                    n(r.underestimation_pct, 3),
                    s(r.region_name),
                ]
                for r in part.itertuples(index=False)
            ]
            file_name = f"{fuel}_{year}.json"
            dump_json(data_dir / file_name, {"product": fuel, "year": year, "columns": POINT_SCHEMA, "rows": rows})
            metadata["products"][fuel]["files"][str(year)] = file_name
            metadata["products"][fuel]["summary"][str(year)] = summarize_numeric(part, "cost_8760", "underestimation_pct")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build compact JSON files for the H2DATA GitHub Pages atlas."
    )
    parser.add_argument(
        "--hydrogen-bias-csv",
        type=Path,
        required=True,
        help="Processed hydrogen cost-bias point table.",
    )
    parser.add_argument(
        "--product-node-csv",
        type=Path,
        required=True,
        help="Processed downstream product node table.",
    )
    parser.add_argument(
        "--world-topojson",
        type=Path,
        default=None,
        help="Optional world-110m TopoJSON basemap file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Output directory for web-ready JSON files.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    data_dir = args.output_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "title": "8760-hour dynamic fuel atlas",
        "description": "Web-ready extracts for 8760-hour dynamic model cost and static-reference underestimation.",
        "years": YEARS,
        "products": {key: {**value, "summary": {}} for key, value in PRODUCTS.items()},
        "schemas": {
            "hydrogen": POINT_SCHEMA,
            "product": POINT_SCHEMA,
        },
        "sources": [
            "hydrogen_static_vs_8760_cost_bias_points",
            "Figure5_downstream_node_cost_bias",
        ],
    }

    build_hydrogen_files(metadata, args.hydrogen_bias_csv, data_dir)
    build_product_files(metadata, args.product_node_csv, data_dir)

    if args.world_topojson and args.world_topojson.exists():
        shutil.copy2(args.world_topojson, data_dir / "world-110m.json")
        metadata["world_map"] = "world-110m.json"

    dump_json(data_dir / "metadata.json", metadata)
    print(f"Wrote cost-and-bias-only web data to {data_dir}")


if __name__ == "__main__":
    main()
