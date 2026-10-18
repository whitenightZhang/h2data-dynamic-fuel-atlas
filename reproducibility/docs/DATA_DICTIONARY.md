# Data fields and units

## Spatial and scenario keys

`latitude`, `longitude`: cell centre in degrees, at 0.25-degree assessment resolution. `year` is the technology scenario (2030, 2035, 2050), not a multi-year weather average. The global assessment uses 2023 hourly weather; the separate nine-case weather test uses 2021, 2022 and 2023. `region`, `region_match`, `region_name` and `region_label` retain the source assignment keys and labels; do not replace them by row position. Wind, wind–solar complementary and solar groups use the current source assignments. Legacy site code H denotes the complementary site (C in some plot labels), alongside W and S.

## Paired global hydrogen costs

File: `paper/02_main_figures/Fig2_Original_Maps_Revised_GHI_20260914/source_data/H2_paired_costs_all_locations.csv.gz`.

| Field | Meaning |
|---|---|
| `static_cost_per_kg` | Annual-average hydrogen production cost, USD/kg H2 |
| `hourly8760_cost_per_kg` | 8760-hour hydrogen production cost, USD/kg H2 |
| `year`, `scenario` | Technology scenario; use latitude/longitude/year as the paired key |
| `region_name` | Original regional label; cells without assignments remain in global statistics |

Absolute bias is hourly minus annual-average cost. Relative bias is 100 times the difference divided by hourly cost. Medians use equal cell weights and retain negative differences. At benchmark b, annual-average-only qualification means annual-average cost <= b < hourly cost.

## Derived-fuel paired costs

File: `paper/02_main_figures/Fig5_SAF1215_20260917/source_data/matched_costs.csv.gz`.

`product` is Ammonia, Methanol or FTL (e-SAF). `hourly_cost` and `static_cost` are USD/t fuel. `underestimation_pct` is relative to hourly cost. Use product/year/latitude/longitude as the paired key; regional labels are supplied in the same row. This cost-comparison sample differs from the positive-potential sample used for competitive-potential aggregation.

## Competitive potential and carbon-price support

File: `paper/15_SAF_reference_1215_20260917/source_data/matched_node_costs.csv`.

| Field | Meaning |
|---|---|
| `fuel` | ammonia, methanol, saf |
| `static_usd_t`, `hourly_usd_t` | Paired production costs, USD/t fuel |
| `potential_Mt` | Screened production-potential weight, Mt/year, held common between assessments |
| `threshold_usd_t` | Baseline fossil-reference cost at 100 USD/tCO2 |
| `region_match`, `region_name` | Original regional assignment |

Baseline references are 600/550/1215 USD/t for ammonia/methanol/e-SAF; fossil emission factors are 3.60/3.10/3.15 tCO2/t fuel. At carbon price p, reference = baseline + factor*(p-100). Competitive potential sums positive weights at qualifying cells. Fuel pathways are alternative uses of resources; their totals are not additive. The first competitive year is the first tested technology scenario passing the reference, not an interpolated calendar-year prediction.

## Wind–PV shares

`paper/02_main_figures/Fig3_RE_Mix_20260914/source_data/RE_mix_all_locations.csv.gz` stores paired costs and wind/PV shares. `static_pv_share` and `hourly8760_pv_share` are fractions from 0 to 1; `delta_pv_share_pp` is 100 times hourly minus annual-average share. Percentage points and relative percentages are different quantities.

## Representative-system runs

`paper/10_revision_analysis/representative_unified_charge_20261017/runs/<product>_<site>_<case>/` contains `solver.json` and `solution.npz`. Bindings record actual parameters, renewable CAPEX, model/CF hashes and case overrides. NPZ arrays `names`, `values`, `objective_coefficients` retain the original variable order; dot(values, objective_coefficients) gives the saved annual objective. Production outputs are in the original model units; use exported `source_data` for plot-level USD/t and normalized capacities.

The legacy variable `battery_energy_capacity` denotes battery power (kW); `battery_storage_capacity` denotes energy (kWh). The exported `battery_power_kW` and `battery_energy_kWh` columns make the distinction explicit. These original variable names are not renamed in archived model code. Capacity-factor inputs contain 8760 ordered hours in `CF_wind_avg` and `CF_pv_avg`. Stored representative cases use a charging coefficient of 0.002 USD/kWh.

The weather archive contains site/year input NPZ files, the model export, parameters and `model_runs`. Source JSON files retain their historical origin paths. Table S6 electrolyzer full-load hours are included as recorded bin-level summaries in `paper/18_results_section3_revision_20260922/electrolyzer_utilization_source.csv`; the full global hourly dispatch arrays underlying those summaries are not included here.

## Web data

`web_atlas/docs/data/*_<year>.json` uses columns `lat`, `lon`, `cost_8760`, `absolute_underestimate`, `underestimation_pct`, `region`. Costs and absolute differences are USD/kg for H2 and USD/t for the other fuels. JSON point values are rounded for display; metadata medians are calculated before rounding. Source CSVs remain the numerical record for post-processing.
