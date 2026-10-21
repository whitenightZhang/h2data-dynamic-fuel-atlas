# H2DATA Dynamic Fuel Atlas

Code and representative-site results for **Annual-average assessments overstate off-grid renewable fuel competitiveness**.

Explore global hydrogen, green-ammonia, e-methanol and e-SAF cost maps in the [interactive atlas](https://whitenightzhang.github.io/h2data-dynamic-fuel-atlas/).

## Contents

- `src/h2data/`: optimization and annual-average assessment functions.
- `reproducibility/`: computational results for the representative sites discussed in the main text.
- `docs/`: the interactive atlas.
- `CITATION.cff`: citation metadata.

## Inspect the representative examples

Install numpy and pandas, then run from the repository root:

```console
python reproducibility/scripts/verify_files.py
python reproducibility/examples/representative_case.py
```

The example reads a saved 8760-hour solution. An optional new optimization requires Gurobi and a valid license; see [instructions](reproducibility/docs/REPRODUCE.md).

## Version and sources

The [v1.0.0 release](https://github.com/whitenightZhang/h2data-dynamic-fuel-atlas/releases/tag/v1.0.0) includes computational results for the representative sites discussed in the main text. See [data fields](reproducibility/docs/DATA_DICTIONARY.md), [figure sources](reproducibility/FIGURE_SOURCE_MAP.csv), [version provenance](reproducibility/docs/VERSION_PROVENANCE.md) and [code availability](CODE_AVAILABILITY.md).

Raw weather and geospatial products are obtained from their cited providers. Code and author-generated outputs retain the MIT license; third-party inputs retain their providers' terms.
