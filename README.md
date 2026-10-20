# H2DATA Dynamic Fuel Atlas

Code and representative-system examples for **Annual-average assessments overstate off-grid renewable fuel competitiveness**.

Explore global hydrogen, green-ammonia, e-methanol and e-SAF cost maps in the [interactive atlas](https://whitenightzhang.github.io/h2data-dynamic-fuel-atlas/). The downloadable examples focus on the three sites used in main-text Fig. 6: wind-cluster, wind–solar complementary and solar-cluster.

## Contents

- `src/h2data/`: optimization and annual-average assessment functions.
- `reproducibility/`: model inputs and saved configurations, hourly operation and sensitivity results at the three representative sites, including 54 fuel/site/scenario cases and nine weather-year cases.
- `docs/`: the live interactive atlas. Its global visualization data in `docs/data/` remain available to the website and are excluded from source-code download archives.
- `CITATION.cff`: authors and fixed-version citation metadata.

## Inspect the representative examples

Install numpy and pandas, then run from the repository root:

```console
python reproducibility/scripts/verify_files.py
python reproducibility/examples/representative_case.py
```

The example reads a saved 8760-hour solution. An optional new optimization requires Gurobi and a valid license; see [instructions](reproducibility/docs/REPRODUCE.md). `reproducibility/examples/representative_costs.csv` provides paired costs and fossil-reference classifications for the nine fuel/site baseline combinations.

## Version and sources

Use the fixed [v1.1.0 release](https://github.com/whitenightZhang/h2data-dynamic-fuel-atlas/releases/tag/v1.1.0) for this representative-example distribution. See [data fields](reproducibility/docs/DATA_DICTIONARY.md), [figure sources](reproducibility/FIGURE_SOURCE_MAP.csv), [version provenance](reproducibility/docs/VERSION_PROVENANCE.md) and [code availability](CODE_AVAILABILITY.md).

Global result maps are accessed through the atlas; the example archive contains representative-site results. Historical global-analysis and plotting source code is retained for use with separately supplied inputs. Raw weather and geospatial products are obtained from their cited providers. Code and author-generated outputs retain the MIT license; third-party inputs retain their providers' terms.
