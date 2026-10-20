"""Export the nine representative fuel/site cost comparisons; no optimization."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "paper/10_revision_analysis/representative_unified_charge_20261017/source_data/representative_summary.csv"
METHANOL = ROOT / "paper/02_main_figures/Fig6_Cost_Gap_Decomposition_20260916/source_data/site_summary.csv"
REFERENCES = {"ammonia": 630.0, "methanol": 550.0, "ftl": 1215.0}
EMISSIONS = {"ammonia": 3.90, "methanol": 3.10, "ftl": 3.15}


def main():
    fuels = pd.read_csv(BASELINE)
    methanol = pd.read_csv(METHANOL)
    assert len(fuels) == 6 and set(fuels["product"]) == {"ammonia", "ftl"}
    assert len(methanol) == 3 and set(methanol.year) == {2035}
    methanol["product"] = "methanol"
    columns = ["product", "site", "latitude", "longitude", "hourly_cost_USD_per_t", "static_cost_USD_per_t"]
    costs = pd.concat([fuels[columns], methanol[columns]], ignore_index=True)
    assert len(costs) == 9 and not costs.duplicated(["product", "site"]).any()
    assert costs[columns[2:]].notna().all().all()
    costs["technology_year"] = 2035
    costs["underestimation_percent"] = 100 * (costs.hourly_cost_USD_per_t - costs.static_cost_USD_per_t) / costs.hourly_cost_USD_per_t
    costs["reference_cost_USD_per_t"] = costs["product"].map(REFERENCES)
    costs["fossil_emission_factor_tCO2_per_t"] = costs["product"].map(EMISSIONS)
    costs["annual_average_below_reference"] = costs.static_cost_USD_per_t <= costs.reference_cost_USD_per_t
    costs["hourly_below_reference"] = costs.hourly_cost_USD_per_t <= costs.reference_cost_USD_per_t
    costs.to_csv(ROOT / "examples/representative_costs.csv", index=False)
    sites = costs[["site", "latitude", "longitude"]].drop_duplicates().sort_values("site")
    assert len(sites) == 3
    sites["group"] = sites.site.map({"W": "Wind-cluster", "H": "Wind-solar complementary", "S": "Solar-cluster"})
    sites.to_csv(ROOT / "examples/representative_sites.csv", index=False)
    print("Exported nine fuel/site comparisons at the three Fig. 6 sites.")


if __name__ == "__main__":
    main()
