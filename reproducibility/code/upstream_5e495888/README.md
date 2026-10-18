# H2DATA Dynamic Fuel Atlas

This repository contains the code and static web atlas for an 8760-hour
assessment of renewable hydrogen-derived fuels. It supports renewable hydrogen,
green ammonia, e-methanol, and e-SAF cost and underestimation analysis.

## Repository Structure

```text
.
├── src/h2data/                 # Optimization and static-screening code
├── scripts/                    # Data-preparation utilities
├── docs/                       # GitHub Pages static website
├── docs/data/                  # Processed web-ready JSON extracts
├── data/                       # Raw-data notes and optional local inputs
├── examples/                   # Example command lines
├── CODE_AVAILABILITY.md        # Scope of released code and data
├── CITATION.cff                # Citation metadata
├── environment.yml             # Conda environment
├── requirements.txt            # Pip requirements
└── pyproject.toml              # Editable package metadata
```

## Installation

Create an environment:

```powershell
conda env create -f environment.yml
conda activate h2data
python -m pip install -e .
```

Or install with pip:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

The 8760-hour optimization functions require Gurobi and a valid Gurobi license.

## Main Code Components

- `h2_optimizer.py`: 8760-hour renewable hydrogen system optimization.
- `am_optimizer.py`: 8760-hour green ammonia system optimization.
- `me_optimizer.py`: 8760-hour e-methanol system optimization.
- `ftl_optimizer.py`: 8760-hour Fischer-Tropsch/e-SAF system optimization.
- `calculate_h2_chunk_static_lcoe.py`: static annual-average hydrogen screening
  by longitude chunk.
- `calculate_static_downstream_from_h2.py`: static downstream screening for
  ammonia, methanol, and FTL/e-SAF from precomputed hydrogen results.

## Static Screening Examples

```powershell
python -m h2data.calculate_h2_chunk_static_lcoe `
  --input-dir D:/path/to/input_data `
  --output-dir D:/path/to/static_h2_output `
  --chunks 0-23 `
  --scenario 2050 `
  --workers 4
```

```powershell
python -m h2data.calculate_static_downstream_from_h2 `
  --input-dir D:/path/to/static_h2_output `
  --output-dir D:/path/to/static_downstream_output `
  --scenarios auto `
  --products ammonia,methanol,ftl `
  --chunks 0-23 `
  --workers 4
```

## Web Atlas

The `docs/` folder is ready for GitHub Pages.

Local preview:

```powershell
python -m http.server 8765 --directory docs
```

Then open:

```text
http://127.0.0.1:8765/
```

For GitHub Pages, set:

- Source: deploy from a branch
- Branch: `main`
- Folder: `/docs`

No build step is required.

## Regenerating Web Data

The committed `docs/data/` files are compact processed extracts for the website.
To rebuild them from processed CSV tables:

```powershell
python scripts/prepare_web_data.py `
  --hydrogen-bias-csv D:/path/to/hydrogen_static_vs_8760_cost_bias_points.csv `
  --product-node-csv D:/path/to/Figure5_downstream_archetype_node_data.csv `
  --world-topojson D:/path/to/world-110m.json `
  --output-dir docs/data
```

The web data schema is:

```text
lat, lon, cost_8760, absolute_underestimate, underestimation_pct, region
```

## Scenario Names

Use year-based scenario names in commands and output files:

```text
2030, 2035, 2050
```

For example, `--scenario 2050` writes files such as
`hydrogen_results_0_2050.csv`.

## Data Policy

Large raw meteorological files, geospatial inputs, and intermediate optimization
outputs are not committed to this repository. See `data/README.md` and
`CODE_AVAILABILITY.md` for details.

## License

This repository is released under the MIT License.
