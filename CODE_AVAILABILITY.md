# Data and code availability

Original optimization and annual-average assessment code is available under `src/h2data/`. The `reproducibility/` directory provides the three representative sites used in Fig. 6, their model/parameter bindings, 54 recorded fuel/site/scenario cases and nine weather-year cases. Figure-source maps cover Fig. 6 and Supplementary Figs. S6–S11.

Global production-cost and assessment-bias maps are available through the interactive atlas: https://whitenightzhang.github.io/h2data-dynamic-fuel-atlas/

The fixed example release is https://github.com/whitenightZhang/h2data-dynamic-fuel-atlas/releases/tag/v1.0.0. Download archives include code and representative-system data. Website visualization assets under `docs/data/` are retained on the public branch for GitHub Pages and excluded from source-code archives.

The default example inspects a saved solution without an optimization license. New optimization runs require Gurobi and a valid license. Inputs, variable definitions and reproduction instructions are provided in `reproducibility/docs/`. Original global data sources and their license terms are cited there. Historical global-analysis source code uses separately supplied inputs.
