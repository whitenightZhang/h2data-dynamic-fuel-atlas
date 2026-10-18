"""Recompute representative-system sensitivities with a common charging cost.

The original optimizer functions and scenario overrides are retained. Only the
battery charging coefficient is changed. Main Fig. 6 solutions supply the
methanol reference, shared by equipment-cost and operating-constraint cases.
"""
from __future__ import annotations

import ast
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PKG = ROOT.parents[1]
SOURCE = Path("D:/OneDrive/POTSED")
CF = SOURCE / "00 Figures/Fig3.9_3.20_运行图/Input/median_points_cf_timeseries_RegionalRE_LowAE.csv"
FIG6 = PKG / "02_main_figures/Fig6_Cost_Gap_Decomposition_20260916/source_data"
OLD = PKG / "22_sensitivity_redesign_20260923/source_data"
SITES = [("W", "North America", 0, 61.5, -99.75),
         ("H", "Africa&Middle East", 1, 17.5, 18.25),
         ("S", "Europe", 2, 37.5, 34.75)]
CASES = {
    "Base": ("param", {}),
    "HighPEM": ("param", {"electrolyzer_cost_PEM": 650}),
    "HighBat": ("param", {"battery_energy_cost": 200}),
    "LowBat": ("param", {"battery_energy_cost": 50}),
    "HighFlex": ("flex", {"Flex_am_up": .2, "Flex_am_down": .4,
        "Flex_me_up": .2, "Flex_me_down": .4, "Flex_ftl_up": .2,
        "Flex_ftl_down": .4, "Flex_dac_up": .2, "Flex_dac_down": .4,
        "am_min_load": .05, "me_min_load": .05, "ftl_min_load": .05,
        "dac_min_load": .05}),
    "LowFlex": ("flex", {"Flex_am_up": .05, "Flex_am_down": .1,
        "Flex_me_up": .02, "Flex_me_down": .1, "Flex_ftl_up": .02,
        "Flex_ftl_down": .1, "Flex_dac_up": .02, "Flex_dac_down": .1,
        "am_min_load": .5, "me_min_load": .5, "ftl_min_load": .5,
        "dac_min_load": .5}),
}
CAPS = {"AE_kW": "electrolyzer_capacity_AE", "PEM_kW": "electrolyzer_capacity_PEM",
        "battery_power_kW": "battery_energy_capacity", "battery_energy_kWh": "battery_storage_capacity",
        "H2_storage_kg": "hydrogen_storage_capacity", "wind_kW": "wind_capacity", "pv_kW": "pv_capacity"}
GROUPS = {"Electrolyzers": ["electrolyzer_capacity_AE", "electrolyzer_capacity_PEM"],
          "Battery": ["battery_energy_capacity", "battery_storage_capacity"],
          "H2 storage": ["hydrogen_storage_capacity"]}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_inputs():
    ROOT.mkdir(parents=True, exist_ok=True)
    provenance = {"battery_charge_penalty_USD_kWh": .002, "cases": CASES,
                  "capacity_factor_sha256": sha(CF), "sources": {},
                  "scope": "Representative sites only; original physical constraints and other coefficients retained."}
    for kind, fn in [("param", "3.2 CAPEXUnCentainty.ipynb"), ("flex", "3.3 FlexUnCentainty.ipynb")]:
        path = SOURCE / fn
        nb = json.loads(path.read_text(encoding="utf-8"))
        functions, params = [], None
        for cell in nb["cells"]:
            if cell.get("cell_type") != "code":
                continue
            src = "".join(cell.get("source", []))
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name in {
                    "optimize_ammonia_system", "optimize_methanol_system", "optimize_ftl_system", "create_model_for_product"}:
                    if node.name.startswith("optimize_"):
                        # Defer the one original solve so logs and exports are handled here.
                        calls = [x for x in node.body if isinstance(x, ast.Expr)
                                 and isinstance(x.value, ast.Call)
                                 and isinstance(x.value.func, ast.Attribute)
                                 and x.value.func.attr == "optimize"]
                        assert len(calls) == 1
                        node.body.remove(calls[0])
                    functions.append(node)
                if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "params_base" for t in node.targets):
                    params = ast.literal_eval(node.value)
        assert len(functions) == 4 and params is not None
        assert params["battery_charge_penalty"] == 1e-5
        params["battery_charge_penalty"] = .002
        code = "from __future__ import annotations\nimport numpy as np\nimport gurobipy as gp\nfrom gurobipy import Model, GRB\n\n"
        code += ast.unparse(ast.Module(body=functions, type_ignores=[])) + "\n"
        (ROOT / f"{kind}_models.py").write_text(code, encoding="utf-8")
        (ROOT / f"{kind}_parameters.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
        provenance["sources"][kind] = {"notebook": str(path), "sha256": sha(path),
                                          "export_sha256": sha(ROOT / f"{kind}_models.py")}
    cf = pd.read_csv(CF)
    for site, _, _, lat, lon in SITES:
        f = cf.loc[np.isclose(cf.latitude, lat) & np.isclose(cf.longitude, lon)].sort_values("hour")
        assert len(f) == 8760 and f.hour.tolist() == list(range(8760))
        f.to_csv(ROOT / f"capacity_factors_{site}.csv", index=False)
    (ROOT / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")


def solve_one(job, solver_tolerances=None):
    import gurobipy as gp
    import importlib.util
    product, site, profile = job
    kind, overrides = CASES[profile]
    folder = ROOT / "runs" / f"{product}_{site}_{profile}"
    folder.mkdir(parents=True, exist_ok=True)
    params = json.loads((ROOT / f"{kind}_parameters.json").read_text(encoding="utf-8"))
    params.update(overrides)
    _, continent, cluster, lat, lon = next(x for x in SITES if x[0] == site)
    old = pd.read_csv(OLD / "raw/param" / f"{product}_{continent}_cluster{cluster}/param_sensitivity_summary.csv")
    old = old.loc[old.capex_profile == "Base"].iloc[0]
    wind_cost, pv_cost = float(old.wind_cost_input), float(old.pv_cost_input)
    binding = {"product": product, "site": site, "profile": profile,
               "parameters": params, "wind_cost": wind_cost, "pv_cost": pv_cost,
               "capacity_factor_sha256": sha(ROOT / f"capacity_factors_{site}.csv"),
               "model_sha256": sha(ROOT / f"{kind}_models.py")}
    record_path, solution_path = folder / "solver.json", folder / "solution.npz"
    if record_path.exists() and solution_path.exists():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        assert record["binding"] == binding and record["status"] == "OPTIMAL"
        if solver_tolerances is None or record.get("solver_tolerances") == solver_tolerances:
            return f"REUSED {product} {site} {profile}"
        before = ROOT / "before" / f"precision_{product}_{site}_{profile}"
        before.mkdir(parents=True, exist_ok=True)
        shutil.copy2(record_path, before / "solver.json")
        shutil.copy2(solution_path, before / "solution.npz")
    if product == "methanol" and profile == "Base":
        original = PKG / "10_revision_analysis/outputs" / f"H0_lat{lat}_lon{lon}"
        summary = json.loads((original / "summary.json").read_text(encoding="utf-8"))
        assert summary["status"] == "OPTIMAL"
        inputs = np.load(PKG / "10_revision_analysis/inputs" / f"lat{lat}_lon{lon}.npz")
        f = pd.read_csv(ROOT / f"capacity_factors_{site}.csv")
        np.testing.assert_allclose(inputs["wind_cf"], f.CF_wind_avg, atol=1e-12)
        np.testing.assert_allclose(inputs["pv_cf"], f.CF_pv_avg, atol=1e-12)
        shutil.copy2(original / "solution.npz", solution_path)
        record = {"binding": binding, "status": "OPTIMAL", "reused_main_Fig6": True,
                  "source": str(original), "runtime_seconds": summary["runtime_s"],
                  "constraint_violation": summary["max_constraint_violation"]}
    else:
        gp.setParam("OutputFlag", 0)
        spec = importlib.util.spec_from_file_location(f"models_{kind}", ROOT / f"{kind}_models.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        f = pd.read_csv(ROOT / f"capacity_factors_{site}.csv")
        m = mod.create_model_for_product(product, f.CF_wind_avg.to_numpy(), f.CF_pv_avg.to_numpy(), wind_cost, pv_cost, params)
        for key, value in (solver_tolerances or {}).items():
            m.setParam(key, value)
        m.setParam("LogFile", str(folder / "solve.log"))
        m.optimize()
        if m.Status != gp.GRB.OPTIMAL:
            raise RuntimeError(f"{job}: non-optimal solver status {m.Status}")
        assert m.ConstrVio < 1e-3, (job, m.ConstrVio)
        vs = m.getVars()
        np.savez_compressed(solution_path, names=np.array([v.VarName for v in vs]),
                            values=np.array([v.X for v in vs]),
                            objective_coefficients=np.array([v.Obj for v in vs]))
        record = {"binding": binding, "status": "OPTIMAL", "objective": m.ObjVal,
                  "runtime_seconds": m.Runtime, "constraint_violation": m.ConstrVio,
                  "reused_main_Fig6": False}
        if solver_tolerances:
            record["solver_tolerances"] = solver_tolerances
        m.dispose()
    z = np.load(solution_path)
    names, values, coeff = z["names"].tolist(), z["values"], z["objective_coefficients"]
    charge = [i for i, n in enumerate(names) if n.startswith("battery_charge[")]
    assert len(charge) == 8760 and np.all(coeff[charge] == .002)
    assert np.isfinite(values).all() and np.isfinite(coeff).all()
    record["solution_sha256"] = sha(solution_path)
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return f"DONE {product} {site} {profile} ({record['runtime_seconds']:.1f} s)"


def summarize():
    rows, components = [], []
    for product in ["methanol", "ammonia", "ftl"]:
        prefix = {"methanol": "methanol_synthesis_power", "ammonia": "ammonia_synthesis_power", "ftl": "FTL_synthesis_power"}[product]
        for site, continent, cluster, lat, lon in SITES:
            for profile, (kind, _) in CASES.items():
                folder = ROOT / "runs" / f"{product}_{site}_{profile}"
                record = json.loads((folder / "solver.json").read_text(encoding="utf-8"))
                z = np.load(folder / "solution.npz")
                vals, obj = dict(zip(z["names"].tolist(), z["values"])), dict(zip(z["names"].tolist(), z["objective_coefficients"]))
                quantity = sum(vals[f"{prefix}[{i}]"] for i in range(8760))
                cost = float(np.dot(z["values"], z["objective_coefficients"]))
                assert quantity > 0
                row = dict(product=product, site=site, node=f"{product}_{continent}_cluster{cluster}",
                           kind=kind, profile=profile, latitude=lat, longitude=lon,
                           annual_cost_USD=cost, output_t=quantity / 1000, LCOP_USD_t=cost / quantity * 1000,
                           battery_charge_penalty_USD_kWh=.002,
                           **{out: vals[name] for out, name in CAPS.items()})
                rows.append(row)
                sums = {}
                for group, names in GROUPS.items():
                    sums[group] = sum(vals[n] * obj[n] for n in names) / quantity * 1000
                sums["Other system"] = row["LCOP_USD_t"] - sum(sums.values())
                for group, value in sums.items():
                    components.append(dict(product=product, site=site, profile=profile, component=group, value_USD_t=value))
    frame = pd.DataFrame(rows)
    records, storage, costs = [], [], []
    for (product, site), group in frame.groupby(["product", "site"], sort=False):
        base = group.loc[group.profile == "Base"].iloc[0]
        for _, row in group.iterrows():
            meta = {k: row[k] for k in ["product", "site", "node", "kind", "profile"]}
            bel = base.AE_kW + base.PEM_kW
            records.append(dict(row, baseline_electrolysis_kW=bel,
                AE_pct_base_total=100 * row.AE_kW / bel, PEM_pct_base_total=100 * row.PEM_kW / bel,
                baseline_LCOP_USD_t=base.LCOP_USD_t, LCOP_change_USD_t=row.LCOP_USD_t - base.LCOP_USD_t,
                LCOP_change_pct=100 * (row.LCOP_USD_t / base.LCOP_USD_t - 1)))
            for label, field in [("Battery power", "battery_power_kW"), ("Battery energy", "battery_energy_kWh"), ("H2 storage", "H2_storage_kg")]:
                assert base[field] > .05
                storage.append(dict(**meta, metric=label, base=base[field], value=row[field], change_pct=100 * (row[field] / base[field] - 1)))
            for group_name in GROUPS.keys() | {"Other system"}:
                b = next(x["value_USD_t"] for x in components if x["product"] == product and x["site"] == site and x["profile"] == "Base" and x["component"] == group_name)
                v = next(x["value_USD_t"] for x in components if x["product"] == product and x["site"] == site and x["profile"] == row.profile and x["component"] == group_name)
                costs.append(dict(**meta, component=group_name, base_USD_t=b, value_USD_t=v, change_USD_t=v-b))
    data = ROOT / "source_data"
    data.mkdir(exist_ok=True)
    for name, items, count in [("scenario_results", records, 54), ("storage_responses", storage, 162), ("cost_changes", costs, 216)]:
        df = pd.DataFrame(items)
        assert len(df) == count and np.isfinite(df.select_dtypes("number")).all().all()
        df.to_csv(data / f"{name}.csv", index=False)
    print("ALL 54 CASES COMPLETE; ONE BASELINE PER FUEL AND SITE", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    prepare_inputs()
    jobs = [(p, s[0], c) for c in CASES for p in ["methanol", "ammonia", "ftl"] for s in SITES]
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(solve_one, job): job for job in jobs}
        for i, future in enumerate(as_completed(futures), 1):
            print(f"{i}/54 {future.result()}", flush=True)
    summarize()
