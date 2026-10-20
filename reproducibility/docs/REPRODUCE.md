# Running the representative examples

From the repository root, install numpy and pandas and run:

```console
python reproducibility/scripts/verify_files.py
python reproducibility/examples/representative_case.py
```

The first command verifies the files in this example distribution. The second inspects a saved 8760-hour e-methanol solution and checks its model/profile/solution hashes and annual objective. It does not run a new optimization or require a solver license.

To regenerate the nine-row paired-cost and classification table from the saved baseline exports:

```console
python reproducibility/scripts/export_representative_costs.py
```

To run a new optimization for that case, install gurobipy and provide a valid Gurobi license:

```console
python reproducibility/examples/representative_case.py --solve --output-dir NEW_REPRESENTATIVE_RUN
```

The output directory must be new. Case bindings and solver settings are retained in the corresponding `solver.json` files. The archive contains 54 fuel/site/scenario cases and nine weather-year cases at the same three sites; see `FIGURE_SOURCE_MAP.csv` for the figure-level exports.

Global production-cost maps are explored through the live atlas linked in the main README. To prepare web JSONs from separately supplied cost tables, see `scripts/prepare_web_data.py` at the repository root. Website visualization data are excluded from source-code archives. Original global-analysis notebooks and plotting sources retain their input paths; use the cited source providers for the global raw resource inputs.
