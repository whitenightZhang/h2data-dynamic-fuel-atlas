"""Carbon-price sensitivity on the unchanged paired global fuel atlas."""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "15_SAF_reference_1215_20260917/source_data"
OUTPUT = HERE / "source_data"
BASELINES = {"ammonia": 600.0, "methanol": 550.0, "saf": 1215.0}
EMISSIONS = {"ammonia": 3.60, "methanol": 3.10, "saf": 3.15}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    nodes_path = SOURCE / "matched_node_costs.csv"
    nodes = pd.read_csv(nodes_path)
    numeric = nodes[["static_usd_t", "hourly_usd_t", "potential_Mt"]].to_numpy()
    assert np.isfinite(numeric).all() and (numeric > 0).all()
    assert not nodes.duplicated(["fuel", "year", "latitude", "longitude", "region_match", "region_name"]).any()
    reference = pd.read_csv(SOURCE / "global_classification.csv").set_index(["fuel", "year"])
    prices = np.arange(0, 201, 5, dtype=float)
    records = []
    for (fuel, year), group in nodes.groupby(["fuel", "year"]):
        assert np.all(group.threshold_usd_t == BASELINES[fuel])
        static = group.static_usd_t.to_numpy()
        hourly = group.hourly_usd_t.to_numpy()
        weight = group.potential_Mt.to_numpy()
        for price in prices:
            threshold = BASELINES[fuel] + EMISSIONS[fuel] * (price - 100)
            s = static <= threshold
            h = hourly <= threshold
            only_s = s & ~h
            only_h = h & ~s
            qs, qh = float(weight[s].sum()), float(weight[h].sum())
            false_s, false_h = float(weight[only_s].sum()), float(weight[only_h].sum())
            assert abs((qs - qh) - (false_s - false_h)) < 1e-6
            share = 100 * false_s / qs if qs > 0 else np.nan
            if price == 100:
                expected = reference.loc[(fuel, year)]
                np.testing.assert_allclose(
                    [qs, qh, false_s],
                    [expected.static_Mt, expected.hourly_Mt, expected.false_positive_Mt],
                    rtol=0, atol=1e-6,
                )
            records.append({
                "fuel": fuel, "technology_year": int(year),
                "carbon_price_USD_per_tCO2": price,
                "reference_cost_USD_per_t": threshold,
                "baseline_reference_cost_USD_per_t": BASELINES[fuel],
                "emission_factor_tCO2_per_t": EMISSIONS[fuel],
                "paired_grid_cells": len(group),
                "annual_average_qualified_potential_Mt_per_year": qs,
                "hourly_qualified_potential_Mt_per_year": qh,
                "annual_average_only_potential_Mt_per_year": false_s,
                "hourly_only_potential_Mt_per_year": false_h,
                "annual_average_qualified_cells": int(s.sum()),
                "hourly_qualified_cells": int(h.sum()),
                "annual_average_only_cells": int(only_s.sum()),
                "uncompetitive_share_of_annual_average_potential_percent": share,
            })
    results = pd.DataFrame(records)
    assert len(results) == 9 * 41
    results.to_csv(OUTPUT / "carbon_price_sensitivity_all_years.csv", index=False)
    selected = ((results.fuel == "ammonia") & (results.technology_year == 2030)
                | (results.fuel == "methanol") & (results.technology_year == 2035)
                | (results.fuel == "saf") & results.technology_year.isin([2035, 2050]))
    plot = results.loc[selected].copy()
    assert len(plot) == 4 * 41
    plot.to_csv(OUTPUT / "carbon_price_sensitivity_plot.csv", index=False)
    shutil.copy2(nodes_path, OUTPUT / "matched_node_costs.csv")
    (OUTPUT / "provenance.json").write_text(json.dumps({
        "source": str(nodes_path),
        "source_sha256": hashlib.sha256(nodes_path.read_bytes()).hexdigest(),
        "source_rows": len(nodes),
        "matched_grid_cells_and_weights": "unchanged",
        "carbon_prices_USD_per_tCO2": prices.tolist(),
        "baseline_carbon_price_USD_per_tCO2": 100,
        "reference_cost_formula": "b_f(p)=b_f(100)+epsilon_f*(p-100)",
        "baseline_reference_costs_USD_per_t": BASELINES,
        "emission_factors_tCO2_per_t": EMISSIONS,
        "share_definition": "100*sum(weights at annual-average-qualified and hourly-unqualified cells)/sum(weights at annual-average-qualified cells)",
        "zero_denominator": "undefined; CSV value is empty, not zero",
        "baseline_100_validation": "all nine fuel-year totals reproduce the published classifications",
        "model_solves": 0,
    }, indent=2), encoding="utf-8")
    print("369 carbon-price classifications; all nine baseline totals reproduced.")
    print(plot[plot.carbon_price_USD_per_tCO2.isin([0, 80, 100, 120, 200])][
        ["fuel", "technology_year", "carbon_price_USD_per_tCO2", "reference_cost_USD_per_t", "uncompetitive_share_of_annual_average_potential_percent"]
    ].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
