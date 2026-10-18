"""Install recalculated data into the existing S6--S10 figure workflows."""
from pathlib import Path
import json
import shutil
import sys

import numpy as np
import pandas as pd

from run_unified import ROOT, PKG, SITES, GROUPS, sha

FIGURES = PKG / "03_supplementary_materials/Figures"
FOLDERS = ["FigS6_Ammonia_20261013", "FigS7_SAF_20261013",
           "FigS8_Methanol_Sensitivity_20261013", "FigS9_Ammonia_Sensitivity_20261013",
           "FigS10_SAF_Sensitivity_20261013"]
BACKUP = ROOT / "before"


def preserve():
    for name in FOLDERS:
        dest = BACKUP / name.split("_")[0]
        if not dest.exists():
            shutil.copytree(FIGURES / name, dest)
    for name in ["01_main_manuscript/Manuscript.tex", "03_supplementary_materials/Supplemental_Information.tex"]:
        dest = BACKUP / name
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PKG / name, dest)


def export_sensitivity():
    records = pd.read_csv(ROOT / "source_data/scenario_results.csv")
    storage = pd.read_csv(ROOT / "source_data/storage_responses.csv")
    costs = pd.read_csv(ROOT / "source_data/cost_changes.csv")
    assert len(records) == 54 and len(storage) == 162 and len(costs) == 216
    assert (records.battery_charge_penalty_USD_kWh == .002).all()
    assert records.groupby(["product", "site"]).baseline_LCOP_USD_t.nunique().eq(1).all()
    for (product, site, profile), frame in costs.groupby(["product", "site", "profile"]):
        r = records.loc[(records["product"] == product) & (records.site == site) & (records.profile == profile)].iloc[0]
        assert abs(frame.change_USD_t.sum() - r.LCOP_change_USD_t) < 1e-9
    main = pd.read_csv(PKG / "02_main_figures/Fig6_Cost_Gap_Decomposition_20260916/source_data/site_summary.csv").set_index("site")
    me = records.loc[(records["product"] == "methanol") & (records.profile == "Base")].set_index("site")
    for s in ["W", "H", "S"]:
        np.testing.assert_allclose(me.loc[s, "AE_kW"], main.loc[s, "electrolyzer_capacity_AE"], rtol=1e-12)
        np.testing.assert_allclose(me.loc[s, "PEM_kW"], main.loc[s, "electrolyzer_capacity_PEM"], rtol=1e-12)
        np.testing.assert_allclose(me.loc[s, "LCOP_USD_t"], main.loc[s, "hourly_cost_USD_per_t"], rtol=1e-12)
    provenance = json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))
    provenance.update({"calculation_directory": str(ROOT), "baseline": "One shared Base per fuel and site, used for all five perturbations; methanol Base is exactly main Fig.6.",
                       "scenario_results_sha256": sha(ROOT / "source_data/scenario_results.csv"),
                       "historical_raw_tables": "Preserved in the before snapshot; not used for the updated figures."})
    for name in FOLDERS[2:]:
        data = FIGURES / name / "source_data"
        for fn in ["scenario_results.csv", "storage_responses.csv", "cost_changes.csv"]:
            shutil.copy2(ROOT / "source_data" / fn, data / fn)
        (data / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
        shutil.copy2(ROOT / "param_parameters.json", data / "parameters.json")


def export_representatives():
    base_params = json.loads((ROOT / "param_parameters.json").read_text(encoding="utf-8"))
    group_map = {"wind_capacity": "Renewable power", "pv_capacity": "Renewable power",
                 **{v: k for k, vs in GROUPS.items() for v in vs}}
    report = []
    for product, folder in [("ammonia", FOLDERS[0]), ("ftl", FOLDERS[1])]:
        data = FIGURES / folder / "source_data"
        old_summary = pd.read_csv(BACKUP / folder.split("_")[0] / "source_data/site_summary.csv").set_index("site")
        old_costs = pd.read_csv(BACKUP / folder.split("_")[0] / "source_data/cost_decomposition.csv")
        params = dict(base_params, fuel_hydrogen_ratio=.18 if product == "ammonia" else .49,
                      fuel_electricity_ratio=.303 if product == "ammonia" else .3)
        (data / "parameters.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
        summaries, costs, checks = [], [], []
        prefix = "ammonia_synthesis_power" if product == "ammonia" else "FTL_synthesis_power"
        synth_capacity = "ammonia_synthesis_capacity" if product == "ammonia" else "FTL_capacity"
        for site, _, _, lat, lon in SITES:
            source = ROOT / "runs" / f"{product}_{site}_Base"
            z = np.load(source / "solution.npz")
            vals = dict(zip(z["names"].tolist(), z["values"].tolist()))
            obj = dict(zip(z["names"].tolist(), z["objective_coefficients"].tolist()))
            caps = {n: v for n, v in vals.items() if "[" not in n}
            series = sorted({n.split("[")[0] for n in vals if "[" in n})
            d = pd.DataFrame({"hour": range(8760), **{n: [vals[f"{n}[{t}]"] for t in range(8760)] for n in series}})
            cf = pd.read_csv(ROOT / f"capacity_factors_{site}.csv")
            d["wind_power"] = cf.CF_wind_avg * caps["wind_capacity"]
            d["pv_power"] = cf.CF_pv_avg * caps["pv_capacity"]
            d["fuel_synthesis_power"] = d[prefix]
            caps["fuel_synthesis_capacity"] = caps[synth_capacity]
            if product == "ammonia":
                for n in ["heat_pump_output", "dac_electricity", "co2_comp_elec"]:
                    d[n] = 0.
            q = float(d.fuel_synthesis_power.sum())
            rated = (caps["electrolyzer_capacity_AE"] * params["electrolyzer_eff_AE"]
                     + caps["electrolyzer_capacity_PEM"] * params["electrolyzer_eff_PEM"]) * .03
            h2 = (d.electrolyzer_power_AE * params["electrolyzer_eff_AE"] + d.electrolyzer_power_PEM * params["electrolyzer_eff_PEM"]) * .03
            demand = (d.electrolyzer_power_AE + d.electrolyzer_power_PEM
                      + d.fuel_synthesis_power * params["fuel_electricity_ratio"]
                      + d.hydrogen_charge * params["hydrogen_storage_elec"]
                      + d.heat_pump_output / params["heat_pump_cop"] + d.dac_electricity + d.co2_comp_elec)
            power_residual = d.wind_power + d.pv_power + d.battery_discharge - demand - d.battery_charge - d.surplus
            h2_residual = h2 + d.hydrogen_discharge - d.fuel_synthesis_power * params["fuel_hydrogen_ratio"] - d.hydrogen_charge
            assert power_residual.abs().max() < 1e-3 and h2_residual.min() > -1e-4
            terms = [{"variable": n, "value": vals[n], "objective_coefficient": coeff,
                      "group": group_map.get(n, "Other process"), "cost_USD_per_t": vals[n] * coeff / q * 1000}
                     for n, coeff in obj.items() if coeff != 0]
            td = pd.DataFrame(terms)
            td.to_csv(data / f"objective_terms_{site}.csv", index=False)
            hourly = td.groupby("group").cost_USD_per_t.sum()
            lcop = float(hourly.sum())
            for _, row in old_costs.loc[old_costs.site == site].iterrows():
                val = float(hourly.loc[row.component])
                costs.append(dict(site=site, component=row.component, hourly_USD_per_t=val,
                                  static_USD_per_t=row.static_USD_per_t, difference_USD_per_t=val-row.static_USD_per_t))
            re = caps["wind_capacity"] + caps["pv_capacity"]
            summaries.append(dict(site=site, latitude=lat, longitude=lon, **caps,
                hourly_cost_USD_per_t=lcop, static_cost_USD_per_t=old_summary.loc[site, "static_cost_USD_per_t"],
                total_fuel_kg=q, electrolyzer_FLH=float(h2.sum()/rated), synthesis_FLH=q/caps[synth_capacity],
                battery_energy_per_RE_kW_h=caps["battery_storage_capacity"]/re,
                h2_duration_h=caps["hydrogen_storage_capacity"]/rated))
            d.to_csv(data / f"hourly_{site}.csv", index=False)
            shutil.copy2(source / "solution.npz", data / f"solution_{site}.npz")
            shutil.copy2(source / "solver.json", data / f"solver_{site}.json")
            checks.append(dict(site=site, power_balance_max_abs_kW=float(power_residual.abs().max()),
                               hydrogen_balance_min_kg_h=float(h2_residual.min()),
                               battery_charge_penalty_USD_kWh=.002, solution_sha256=sha(source/"solution.npz")))
        pd.DataFrame(summaries).to_csv(data / "site_summary.csv", index=False)
        pd.DataFrame(costs).to_csv(data / "cost_decomposition.csv", index=False)
        (data / "data_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
        (data / "data_provenance.json").write_text(json.dumps({"calculation_directory": str(ROOT),
            "battery_charge_penalty_USD_kWh": .002, "shared_baseline_with_sensitivity": True,
            "other_model_settings": "Original representative and sensitivity model constraints retained."}, indent=2), encoding="utf-8")
        report += [dict(product=product, **row) for row in summaries]
    pd.DataFrame(report).to_csv(ROOT / "source_data/representative_summary.csv", index=False)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    preserve()
    export_sensitivity()
    export_representatives()
    print("S6--S10 data updated; all use charging coefficient 0.002 and shared reference solutions.")
