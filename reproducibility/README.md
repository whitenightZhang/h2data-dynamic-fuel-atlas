# Representative-system data and workflows — v1.1.0

Companion examples for **Annual-average assessments overstate off-grid renewable fuel competitiveness**.

The data cover the three sites used in Fig. 6 and shared across the derived-fuel pathways. They include equipment configurations, paired annual-average/hourly costs, saved 8760-hour operation, 54 baseline/sensitivity cases and nine e-methanol weather-year cases for 2021, 2022 and 2023. Existing solution files and numerical results are retained unchanged.

Start with `examples/representative_sites.csv`, `examples/representative_costs.csv`, `FIGURE_SOURCE_MAP.csv`, `docs/DATA_DICTIONARY.md` and `docs/REPRODUCE.md`. The source maps cover the representative-system figures; historical folder numbers can differ from manuscript figure numbers.

Global cost and assessment-bias maps are available in the [interactive atlas](https://whitenightzhang.github.io/h2data-dynamic-fuel-atlas/). Complete global paired-cost, production-potential and competitiveness/carbon-price result tables are outside the scope of this example distribution.

`paper/10_revision_analysis/representative_unified_charge_20261017/runs/` contains the 54 saved fuel/site/scenario solutions. Weather-year inputs and nine model runs are in `paper/03_supplementary_materials/Figures/FigS11_Methanol_Weather_20261013/`. Original run bindings identify the model, parameters and hourly profiles. Figure-level capacity, hourly-dispatch and cost-component tables are retained for Fig. 6 and Supplementary Figs. S6–S11.

Model and historical analysis source code is retained. The supported inspection example reads the supplied representative data; global processing and original plotting scripts use their documented input and asset paths. `docs/data_sources.bib` contains the data and parameter references.
