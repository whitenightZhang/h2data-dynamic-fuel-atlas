# Source data and recorded workflows — v1.0.0

Companion data/code for **Annual-average assessments overstate off-grid renewable fuel competitiveness**.

The archive contains paired annual-average/hourly costs, screened production-potential weights, threshold and carbon-price outputs, figure scripts, 54 recorded representative-system cases and nine weather-year cases. Numerical source files and actual run-model exports are copied unchanged from the 2026-10-18 author-review package. Notebook code is retained; saved notebook outputs are removed from the distribution.

Start with `FIGURE_SOURCE_MAP.csv`, `TABLE_SOURCE_MAP.csv`, `SOURCE_WORKFLOW_MAP.csv`, `docs/DATA_DICTIONARY.md` and `docs/REPRODUCE.md`. Original folder numbers can differ from the current paper's figure numbers; use the maps. `docs/data_sources.bib` retains the data and parameter source citations.

The manuscript and SI documents, rendered figures, third-party basemap shapefiles, original global raw data and solver logs remain outside this public distribution. Plotting scripts retain the original asset paths, so reproducing maps or panels based on an original figure PDF requires the corresponding excluded assets. The paired numerical data and verified statistics can be inspected without those assets. Recorded configuration/solution JSON/NPZ files and original model source identify the numerical run versions.

`code/upstream_5e495888/` preserves the earlier public-code snapshot; the models bound to actual recorded runs are in `paper/10_revision_analysis/` and the weather archive. The current release does not claim that all historical calculations were executed by one later public-code commit.

The public atlas in the repository's `docs/` directory is generated from these current paired costs. Source input hashes and file-level provenance are recorded in `source_provenance.json`; `FILE_MANIFEST.csv` and `checksums.sha256` identify the delivered files.
