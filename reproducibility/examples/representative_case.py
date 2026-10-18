"""Inspect a stored 8760-hour case; --solve explicitly enables a new solve."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
REP=ROOT/'paper/10_revision_analysis/representative_unified_charge_20261017'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solve',action='store_true')
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args()
    run=REP/'runs/methanol_H_HighPEM'
    record=json.loads((run/'solver.json').read_text(encoding='utf-8'))
    binding=record['binding']
    assert digest(REP/'param_models.py')==binding['model_sha256']
    assert digest(REP/'capacity_factors_H.csv')==binding['capacity_factor_sha256']
    assert digest(run/'solution.npz')==record['solution_sha256']
    cf=pd.read_csv(REP/'capacity_factors_H.csv').sort_values('hour')
    assert len(cf)==8760 and cf.hour.tolist()==list(range(8760))
    with np.load(run/'solution.npz',allow_pickle=False) as arrays:
        values=arrays['values']
        assert np.isfinite(values).all()
        objective=float(np.dot(values,arrays['objective_coefficients']))
    np.testing.assert_allclose(objective,record['objective'],rtol=0,atol=1e-6)
    result=dict(status='PASS',mode='stored-solution inspection',case='methanol_H_HighPEM',
                hours=8760,objective=objective,stored_solver_status=record['status'],
                stored_constraint_violation=record['constraint_violation'],new_model_solves=0)
    if args.solve:
        if args.output_dir is None:
            parser.error('--solve requires a new --output-dir')
        out=args.output_dir.resolve()
        if out.exists():
            parser.error('--output-dir must not already exist')
        import gurobipy as gp
        spec=importlib.util.spec_from_file_location('archived_model',REP/'param_models.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        out.mkdir(parents=True)
        model=module.create_model_for_product(binding['product'],cf.CF_wind_avg.to_numpy(),
            cf.CF_pv_avg.to_numpy(),binding['wind_cost'],binding['pv_cost'],binding['parameters'])
        model.Params.OutputFlag=0
        model.Params.LogFile=str(out/'solve.log')
        for name,value in record.get('solver_tolerances',{}).items():
            model.setParam(name,value)
        model.optimize()
        if model.Status!=gp.GRB.OPTIMAL:
            raise RuntimeError(f'Gurobi status {model.Status}; see {out}/solve.log')
        variables=model.getVars()
        np.savez_compressed(out/'solution.npz',names=np.array([v.VarName for v in variables]),
            values=np.array([v.X for v in variables]),objective_coefficients=np.array([v.Obj for v in variables]))
        result=dict(status='PASS',mode='new optimization',case='methanol_H_HighPEM',hours=8760,
                    objective=model.ObjVal,stored_objective=objective,new_model_solves=1,
                    constraint_violation=model.ConstrVio)
        (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        model.dispose()
    print(json.dumps(result))

if __name__=='__main__':
    main()
