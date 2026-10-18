# Running the supplied examples

From the repository root:

```console
cd reproducibility
python scripts/verify_files.py
python scripts/check_paper_statistics.py
python examples/representative_case.py
```

The statistics script checks headline cost/bias medians, the 2 USD/kg classification, equivalent carbon prices, the full archived 0–200 USD/tCO2 carbon-price scan and hydrogen-benchmark scan. The representative example inspects a stored 8760-hour solution and checks its model/CF/solution hashes and annual objective. Both run with numpy and pandas and require no optimization license.

An explicit new optimization requires gurobipy and a Gurobi license:

```console
python examples/representative_case.py --solve --output-dir NEW_REPRESENTATIVE_RUN
```

That optional solve is not part of release preparation. The recorded models contain solver settings; case-specific overrides and solution metadata are in solver.json. The recorded representative logs identified Gurobi 11.0.3. Current observed environment versions are in environment/packaging_runtime.json; they are not a substitute for the original per-run provenance.

To regenerate the repository's live atlas data from the included cost tables:

```console
python scripts/rebuild_web_atlas.py
```

This command writes ../docs/data. Serve the repository's docs/ directory locally to view the atlas; its original CDN library dependencies require an internet connection.

Original notebooks, plotting and historical full-workflow scripts retain their original local paths. They are source records, not a single portable global-run launcher. Numerical post-processing and the representative example above are the supported minimal entry points. Raw global resource inputs, basemap shapefiles and original rendered map panels are not bundled; their data sources are documented in the accompanying bibliography and notebooks. Table S6 full-load-hour values are provided as recorded group summaries, rather than complete global dispatch arrays.
