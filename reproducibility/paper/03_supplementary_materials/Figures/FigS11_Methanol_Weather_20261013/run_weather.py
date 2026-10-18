"""Recalculate the Fig. 6 methanol sites using the unchanged main-text model."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import csv
import datetime
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DATA = HERE / "source_data"
RUNS = HERE / "model_runs"
FIG6 = ROOT / "02_main_figures/Fig6_Cost_Gap_Decomposition_20260916"
SOURCE = ROOT / "10_revision_analysis/src/h2data/me_optimizer.py"


def annualized(capex, lifetime, rate):
    return capex * (rate / (1 - (1 + rate) ** -lifetime) + 0.03)


def annual_average(p, wind_cf, pv_cf, wind_cost, pv_cost):
    """Main-text AE 4000-h and downstream 0.8 utilization accounting."""
    rate = p["discount_rate"]
    wind_lcoe = annualized(wind_cost, p["wind_lifetime"], rate) / wind_cf.sum()
    pv_lcoe = annualized(pv_cost, p["pv_lifetime"], rate) / pv_cf.sum()
    lcoe = min(wind_lcoe, pv_lcoe)
    q = p["target_methanol_production"]
    hydrogen = q * p["methanol_hydrogen_ratio"]
    carbon = q * p["methanol_co2_ratio"]
    hydrogen_electricity = 120 / (3.6 * p["electrolyzer_eff_AE"])
    ae_annual = annualized(p["electrolyzer_cost_AE"], p["electrolyzer_lifetime_AE"], rate)
    lcoh = hydrogen_electricity * (lcoe + ae_annual / 4000)
    utilization_hours = 8760 * 0.8
    heat = carbon * p["dac_heat_per_kg"]
    other_electricity = (q * p["methanol_electricity_ratio"]
                         + carbon * p["dac_elec_per_kg"]
                         + heat / p["heat_pump_cop"])
    components = {
        "hydrogen": hydrogen * lcoh,
        "process_electricity": other_electricity * lcoe,
        "synthesis": annualized(p["methanol_synthesis_cost"], p["methanol_synthesis_lifetime"], rate) * q / utilization_hours,
        "dac": annualized(p["dac_cost"], p["dac_lifetime"], rate) * carbon / utilization_hours,
        "heat_pump": annualized(p["heat_pump_cost"], p["heat_pump_lifetime"], rate) * heat / utilization_hours,
        "sorbent": carbon * p["sorbent_cost"],
    }
    return {
        "annual_average_cost_USD_per_t": sum(components.values()) / q * 1000,
        "selected_RE_source": "wind" if wind_lcoe <= pv_lcoe else "PV",
        "wind_LCOE_USD_per_kWh": wind_lcoe,
        "pv_LCOE_USD_per_kWh": pv_lcoe,
        "annual_average_components_USD_per_year": components,
    }


def prepare():
    DATA.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(exist_ok=True)
    # Expose the original model before its solve and reporting code. All model
    # construction statements, solver settings, constraints and costs are retained.
    tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "optimize_methanol_system")
    solve_index = next(i for i, n in enumerate(function.body)
                       if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                       and isinstance(n.value.func, ast.Attribute)
                       and n.value.func.attr == "optimize")
    prefix = function.body[:solve_index]
    expected_ast = ast.dump(ast.Module(body=prefix, type_ignores=[]))
    function.body = prefix + [ast.Return(value=ast.Name(id="model", ctx=ast.Load()))]
    ast.fix_missing_locations(tree)
    exposed = DATA / "main_model_exposed.py"
    exposed.write_text(ast.unparse(tree), encoding="utf-8")
    check = ast.parse(exposed.read_text(encoding="utf-8"))
    actual_function = next(n for n in check.body if isinstance(n, ast.FunctionDef) and n.name == function.name)
    assert ast.dump(ast.Module(body=actual_function.body[:-1], type_ignores=[])) == expected_ast
    spec = importlib.util.spec_from_file_location("weather_main_model", exposed)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provenance = {
        "model_source": str(SOURCE),
        "model_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "model_construction_ast_identical": True,
        "technology_year": 2035,
        "weather_years": [2021, 2022, 2023],
        "site_source": str(FIG6 / "source_data/site_summary.csv"),
        "annual_average_basis": "AE 4000 h, downstream utilization 0.8, no storage-branch CO2 compressor; verified against Fig. 6's corrected 2023 costs",
        "profiles": [],
    }
    return module.optimize_methanol_system, provenance


def main():
    build, provenance = prepare()
    params = json.loads((FIG6 / "source_data/parameters.json").read_text())
    static_reference = pd.read_csv(FIG6 / "source_data/original_static_rows.csv").set_index("site")
    hourly_reference = pd.read_csv(FIG6 / "source_data/site_summary.csv").set_index("site")
    cf_reference = pd.read_csv(FIG6 / "source_data/original_hourly_capacity_factors.csv")
    (DATA / "parameters.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
    sites = [("W", "Wind-cluster", 61.5, -99.75),
             ("H", "Wind-solar complementary", 17.5, 18.25),
             ("S", "Solar-cluster", 37.5, 34.75)]
    results = []
    for year in [2023, 2021, 2022]:
        for site, label, latitude, longitude in sites:
            out = RUNS / f"{site}_{year}"
            assert not out.exists(), f"Existing run requires inspection: {out}"
            out.mkdir()
            source = Path("E:/Workspace") / f"average_{year}_segment_{int((longitude % 360) / 15) * 60}.nc"
            with xr.open_dataset(source) as ds:
                point = ds.sel(latitude=latitude, longitude=longitude % 360)
                wind_cf = np.asarray(point.CF_wind_avg.values, dtype=float)
                pv_cf = np.asarray(point.CF_pv_avg.values, dtype=float)
                times = point.valid_time.values.astype("datetime64[h]")
            assert wind_cf.shape == pv_cf.shape == times.shape == (8760,)
            assert np.isfinite(wind_cf).all() and np.isfinite(pv_cf).all()
            assert ((wind_cf >= 0) & (wind_cf <= 1)).all()
            assert ((pv_cf >= 0) & (pv_cf <= 1)).all()
            assert np.all(np.diff(times.astype(np.int64)) == 1)
            assert np.all(times.astype("datetime64[Y]") == np.datetime64(str(year), "Y"))
            if year == 2023:
                ref = cf_reference[cf_reference.site == site].sort_values("hour")
                np.testing.assert_allclose(wind_cf, ref.CF_wind_avg, rtol=0, atol=1e-15)
                np.testing.assert_allclose(pv_cf, ref.CF_pv_avg, rtol=0, atol=1e-15)
            np.savez_compressed(DATA / f"profiles_{site}_{year}.npz", wind_cf=wind_cf, pv_cf=pv_cf, timestamps=times)
            provenance["profiles"].append({
                "site": site, "year": year, "source": str(source),
                "wind_sha256": hashlib.sha256(wind_cf.tobytes()).hexdigest(),
                "pv_sha256": hashlib.sha256(pv_cf.tobytes()).hexdigest(),
                "timestamps_sha256": hashlib.sha256(times.astype(np.int64).tobytes()).hexdigest(),
                "adjustments": "none",
            })
            row = static_reference.loc[site]
            wind_cost, pv_cost = float(row.wind_cost), float(row.pv_cost)
            static = annual_average(params, wind_cf, pv_cf, wind_cost, pv_cost)
            if year == 2023:
                assert abs(static["annual_average_cost_USD_per_t"] - hourly_reference.loc[site, "static_cost_USD_per_t"]) < 1e-5
            print(f"START {site} {year}; annual-average {static['annual_average_cost_USD_per_t']:.3f} USD/t", flush=True)
            model = build(**params, wind_output=wind_cf, pv_output=pv_cf, wind_cost=wind_cost, pv_cost=pv_cost)
            model.Params.LogFile = str(out / "solver.log")
            model.optimize()
            record = {"site": site, "group": label, "latitude": latitude, "longitude": longitude,
                      "weather_year": year, "technology_year": 2035, "solver_status": model.Status,
                      "runtime_s": model.Runtime, **static}
            (out / "summary.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
            assert model.Status == 2, f"Unresolved solve: {site}, {year}, status {model.Status}"
            assert model.ConstrVio < 1e-3, (site, year, model.ConstrVio)
            variables = model.getVars()
            names = np.array([v.VarName for v in variables])
            values = np.array([v.X for v in variables])
            objective_coefficients = np.array([v.Obj for v in variables])
            total_output = float(sum(v.X for v in variables if v.VarName.startswith("methanol_synthesis_power[")))
            assert abs(total_output - params["target_methanol_production"]) < 0.01
            hourly_cost = model.ObjVal / total_output * 1000
            assert abs(np.dot(values, objective_coefficients) - model.ObjVal) < 1e-5
            if year == 2023:
                assert abs(hourly_cost - hourly_reference.loc[site, "hourly_cost_USD_per_t"]) < 0.01
            np.savez_compressed(out / "solution.npz", names=names, values=values, objective_coefficients=objective_coefficients)
            record.update(hourly_cost_USD_per_t=hourly_cost, total_methanol_kg=total_output,
                          constraint_violation=model.ConstrVio, bound_violation=model.BoundVio,
                          underestimation_percent=100 * (hourly_cost - static["annual_average_cost_USD_per_t"]) / hourly_cost,
                          wind_mean_CF=float(wind_cf.mean()), pv_mean_CF=float(pv_cf.mean()),
                          wind_cost_USD_per_kW=wind_cost, pv_cost_USD_per_kW=pv_cost)
            capacities = {v.VarName: v.X for v in variables if "[" not in v.VarName}
            (out / "capacities.json").write_text(json.dumps(capacities, indent=2), encoding="utf-8")
            (out / "summary.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
            results.append({k: v for k, v in record.items() if not isinstance(v, dict)})
            pd.DataFrame(results).to_csv(DATA / "weather_sensitivity_results.csv", index=False)
            (DATA / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
            print(f"DONE {site} {year}: hourly {hourly_cost:.3f}; underestimation {record['underestimation_percent']:.3f}%", flush=True)
            model.dispose()
    assert len(results) == 9
    print("COMPLETE: nine optimal main-model weather cases.", flush=True)


if __name__ == "__main__":
    main()
