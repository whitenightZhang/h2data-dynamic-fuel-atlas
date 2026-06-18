# Example Commands

Run commands from the repository root after installing the package in editable
mode:

```powershell
python -m pip install -e .
```

## Static Hydrogen Screening

```powershell
python -m h2data.calculate_h2_chunk_static_lcoe `
  --input-dir D:/path/to/input_data `
  --output-dir D:/path/to/static_h2_output `
  --chunks 0-23 `
  --scenario RegionRE_LowAE_2050 `
  --workers 4
```

## Static Downstream Screening

```powershell
python -m h2data.calculate_static_downstream_from_h2 `
  --input-dir D:/path/to/static_h2_output `
  --output-dir D:/path/to/static_downstream_output `
  --scenarios auto `
  --products ammonia,methanol,ftl `
  --chunks 0-23 `
  --workers 4
```

## Local Web Atlas

```powershell
python -m http.server 8765 --directory docs
```

Then open `http://127.0.0.1:8765/`.
