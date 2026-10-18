"""Fixed-output monetary comparisons; only validated feasible optima belong here."""
from math import isfinite

def decision_summary(c_a, c_b, c_c, target_t_per_year):
    vals = tuple(float(x) for x in (c_a, c_b, c_c, target_t_per_year))
    if not all(isfinite(x) for x in vals):
        raise ValueError('Comparison values must be finite')
    c_a, c_b, c_c, q = vals
    if q <= 0 or c_b <= 0 or c_c <= 0 or c_a < 0:
        raise ValueError('Positive output and reference costs are required')
    if c_b < c_c:
        raise ValueError('Replay cost below the claimed hourly optimum; inspect raw results')
    return {
        'budget_gap_usd_per_year': c_b-c_a,
        'budget_gap_usd_per_t': (c_b-c_a)/q,
        'budget_underestimate_fraction': (c_b-c_a)/c_b,
        'allocation_regret_usd_per_year': c_b-c_c,
        'allocation_regret_fraction': (c_b-c_c)/c_c,
    }
