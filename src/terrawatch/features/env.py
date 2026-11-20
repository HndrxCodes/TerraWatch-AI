"""Per-cell environmental features from gridded rain and soil wetness. Same names and definitions as the
regional notebook features (cell 11), so the evaluation scripts need no changes.
Every value at day t uses data up to and including day t (rain) or the last COMPLETED month (soil)."""
import numpy as np
import pandas as pd

from ..config import DRY_MM

RAIN_WINDOWS = (7, 30, 60, 90)


def dry_run_days(values, dry_mm=DRY_MM):
    """Consecutive days ending at t with rain < dry_mm. Missing rain counts as 'not dry' (resets the run),
    exactly as in the notebook (NaN < x is False)."""
    dry = np.asarray(values, float) < dry_mm
    out = np.zeros(dry.shape, np.int32)
    run = np.zeros(dry.shape[1], np.int32)
    for t in range(dry.shape[0]):
        run = np.where(dry[t], run + 1, 0)
        out[t] = run
    return out


def build_env_arrays(precip, sm_monthly, days):
    """precip: DataFrame (daily dates x cell_id, mm/day). sm_monthly: DataFrame (monthly PeriodIndex x cell_id) or None.
    Returns {feature: array (len(days), n_cells)} aligned with `days`."""
    P = precip.reindex(days)
    out = {f"rain_{w}d": P.rolling(w).sum().values for w in RAIN_WINDOWS}   # NaN if any day in the window is missing
    out["dry_run"] = dry_run_days(P.values)
    if sm_monthly is not None:
        sm = sm_monthly.copy()
        if not isinstance(sm.index, pd.PeriodIndex):
            sm.index = pd.PeriodIndex(sm.index, freq="M")
        sm = sm[list(precip.columns)]
        out["sm_prev"] = sm.reindex(days.to_period("M") - 1).values        # last completed month only
    return out
