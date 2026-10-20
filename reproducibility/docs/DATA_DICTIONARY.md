# Representative-system fields and units

## Sites and scenarios

`examples/representative_sites.csv` identifies the three Fig. 6 sites. W is wind-cluster, H is wind–solar complementary and S is solar-cluster. Latitude and longitude are in degrees. These sites are shared across green ammonia, e-methanol and e-SAF. Baseline technology assumptions are for 2035. The separate e-methanol weather comparison uses 2021, 2022 and 2023.

`examples/representative_costs.csv` contains the nine baseline fuel/site combinations. Annual-average and hourly costs are in USD/t fuel. Absolute underestimation is hourly minus annual-average cost; relative underestimation is 100 times this difference divided by hourly cost. The classification columns compare these site costs with the baseline fossil-reference costs. They describe the representative systems, not regional production-potential totals.

## Fossil-reference inputs

At a carbon price of 100 USD/tCO2, the reference costs are 630, 550 and 1215 USD/t for ammonia, e-methanol and e-SAF. Fossil emission factors are 3.90, 3.10 and 3.15 tCO2/t fuel. At carbon price p, reference = baseline + emission_factor * (p - 100). These are post-processing inputs; they do not alter the saved renewable-system optimization solutions.

## Configurations, operation and sensitivity cases

`paper/10_revision_analysis/representative_unified_charge_20261017/runs/<product>_<site>_<case>/` contains `solver.json` and `solution.npz`. Bindings record actual parameters, renewable CAPEX, model/profile hashes and case overrides. The NPZ arrays `names`, `values` and `objective_coefficients` preserve variable order. Their value/coefficient dot product gives the saved annual objective. Use the figure-level source tables for USD/t fuel and normalized equipment capacities.

The legacy model variable `battery_energy_capacity` denotes battery power in kW; `battery_storage_capacity` denotes energy in kWh. Exported `battery_power_kW` and `battery_energy_kWh` columns distinguish these explicitly. The hourly profiles have 8760 ordered values in `CF_wind_avg` and `CF_pv_avg`. Recorded representative cases use a battery charging coefficient of 0.002 USD/kWh.

`source_data/representative_summary.csv` contains ammonia and e-SAF baseline equipment capacities and fuel costs. E-methanol baseline results are in the Fig. 6 `source_data/site_summary.csv`. The accompanying `scenario_results.csv`, `storage_responses.csv` and `cost_changes.csv` record the equipment-cost and operating-constraint sensitivity results. Figure folders provide site summaries, hourly operation, selected-week data and cost-component tables for the three sites.

## Weather-year cases

`paper/03_supplementary_materials/Figures/FigS11_Methanol_Weather_20261013/` contains the nine site/year profiles, the model export, parameter inputs and `model_runs`. `weather_sensitivity_results.csv` summarizes the annual-average/hourly costs and operating results.

## Global visualization

Global maps are served by the interactive atlas. Its web data columns are `lat`, `lon`, `cost_8760`, `absolute_underestimate`, `underestimation_pct` and `region`. Hydrogen costs use USD/kg; derived-fuel costs use USD/t. The website's global visualization assets remain in the website branch directory and are excluded from downloadable source archives.
