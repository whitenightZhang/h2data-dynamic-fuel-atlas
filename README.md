# H2DATA Dynamic Fuel Atlas

Data and code for **Annual-average assessments overstate off-grid renewable fuel competitiveness**.

The [interactive atlas](https://whitenightzhang.github.io/h2data-dynamic-fuel-atlas/) contains the current 2030, 2035 and 2050 paired-cost results for hydrogen, green ammonia, e-methanol and e-SAF. The 2035 median annual-average cost biases are 26.2%, 19.0%, 17.1% and 14.8%, respectively.

## Contents

- `src/h2data/`: public optimization and annual-average screening code.
- `docs/`: live atlas and current web-ready JSONs.
- `reproducibility/`: current paired costs, potential weights, figure/table source maps, run-model exports, 54 representative cases and nine weather-year cases.
- `CITATION.cff`: title, authors and fixed-version citation metadata.

The actual model version for a recorded calculation is identified by its saved binding and source-file hash. The companion archive distinguishes historical run exports from the maintained public model functions.

## Minimal inspection

Install numpy and pandas, then run:

```console
python reproducibility/scripts/check_paper_statistics.py
python reproducibility/examples/representative_case.py
```

The default example checks a stored 8760-hour system. An optional new solve requires Gurobi and a valid license; see [reproduction instructions](reproducibility/docs/REPRODUCE.md). Full global raw weather and geospatial datasets are obtained from their original providers, not bundled here.

## Local atlas

```console
python -m http.server 8000 --directory docs --bind 127.0.0.1
```

Open http://127.0.0.1:8000. To regenerate current atlas data, run `python reproducibility/scripts/rebuild_web_atlas.py`.

## Version and citation

Use the fixed [v1.0.0 release](https://github.com/whitenightZhang/h2data-dynamic-fuel-atlas/releases/tag/v1.0.0) for this manuscript snapshot. This release is identified by its GitHub tag and target commit; no DOI archive is requested for this version.

See [data fields](reproducibility/docs/DATA_DICTIONARY.md), [figure sources](reproducibility/FIGURE_SOURCE_MAP.csv), [table sources](reproducibility/TABLE_SOURCE_MAP.csv), [version provenance](reproducibility/docs/VERSION_PROVENANCE.md) and [code availability](CODE_AVAILABILITY.md). Code and author-generated processed outputs retain the existing MIT license; third-party assets retain their providers' terms.
