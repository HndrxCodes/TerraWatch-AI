"""Per-cell weekly dataset: target Y(i,t) and causal features (spec sections 10.2-10.4).

Y(i,t) = 1 if at least one qualifying FIRMS detection falls in cell i during days t+1 ... t+7.
Every feature uses detections up to and including day t only (same convention as notebook cell 11).
A zero means "no qualifying detection in the data", never "no fire".
"""
import numpy as np
import pandas as pd

from ..config import (DATA_START, DATA_END, ML_START, HORIZON, STRIDE, GAPS)
from ..preprocessing.spatial import assign_cells
from .env import build_env_arrays

SEASON = ["doy_sin", "doy_cos"]
CELL_STATIC = ["lat", "lon", "frac_inside"]
CELL_HISTORY = ["log_fire_7d", "log_fire_30d", "log_fire_90d", "log_fire_365d", "days_since_fire"]
DAYS_SINCE_CAP = 365


def daily_counts(det, grid, spec, start=DATA_START, end=DATA_END):
    """Dense (n_days, n_cells) matrix of detection counts. Column order follows grid.cell_id."""
    days = pd.date_range(start, end)
    cid = assign_cells(det, spec)
    col = pd.Series(np.arange(len(grid)), index=grid.cell_id.values).reindex(cid).values   # NaN if not in grid
    d_idx = (det.acq_date.values.astype("datetime64[D]") - np.datetime64(start)).astype(int)
    ok = ~np.isnan(col) & (d_idx >= 0) & (d_idx < len(days))
    M = np.zeros((len(days), len(grid)), np.int32)
    np.add.at(M, (d_idx[ok], col[ok].astype(int)), 1)
    return days, M


def trailing_sum(M, w):
    """out[t] = sum of M[t-w+1 .. t] (includes day t, never later days)."""
    c = np.cumsum(M, axis=0, dtype=np.int64)
    out = c.copy()
    out[w:] -= c[:-w]
    return out


def forward_sum(M, h):
    """out[t] = sum of M[t+1 .. t+h]; -1 where the window runs past the end of the record."""
    c = np.cumsum(M, axis=0, dtype=np.int64)
    out = np.full(M.shape, -1, np.int64)
    out[:-h] = c[h:] - c[:-h]
    return out


def days_since(M, cap=DAYS_SINCE_CAP):
    """Days since the last detection in each cell, up to and including day t, capped (also when no history)."""
    n, k = M.shape
    last = np.full(k, -10 ** 9, dtype=np.int64)
    out = np.empty((n, k), np.int32)
    for t in range(n):
        last[M[t] > 0] = t
        out[t] = np.minimum(t - last, cap)
    return out


def build_cell_dataset(det, grid, spec, regional=None, precip=None, sm_monthly=None, data_start=DATA_START,
                       ml_start=ML_START, end=DATA_END, horizon=HORIZON, stride=STRIDE, gaps=GAPS):
    """Long table: one row per (reference date, cell).

    regional: optional DataFrame indexed by date (e.g. notebook X[ENV]); each column is broadcast to all
    cells. It carries no per-cell information, so cell differences then come from fire history and position.
    precip / sm_monthly: optional GRIDDED rain (daily x cell_id) and soil wetness (monthly x cell_id) tables; they
    give true per-cell rain_*d, dry_run and sm_prev and take precedence over `regional` columns of the same name.
    """
    days, M = daily_counts(det, grid, spec, data_start, end)
    t0 = days.get_loc(pd.Timestamp(ml_start))
    t_idx = np.arange(t0, len(days) - horizon, stride)
    dates = days[t_idx]
    keep = np.ones(len(t_idx), bool)
    for a, b in gaps:                                   # same exclusion rule as notebook cell 11
        keep &= ~((dates >= pd.Timestamp(a) - pd.Timedelta(days=30)) & (dates <= pd.Timestamp(b)))
    t_idx = t_idx[keep]
    dates = days[t_idx]
    n_t, k = len(t_idx), len(grid)

    out = pd.DataFrame({
        "date": np.repeat(dates.values, k),
        "cell_id": np.tile(grid.cell_id.values, n_t),
        "lat": np.tile(grid.lat.values, n_t),
        "lon": np.tile(grid.lon.values, n_t),
        "frac_inside": np.tile(grid.frac_inside.values, n_t),
    })
    for w in (7, 30, 90, 365):
        out[f"log_fire_{w}d"] = np.log1p(trailing_sum(M, w)[t_idx]).ravel()
    out["days_since_fire"] = days_since(M)[t_idx].ravel()
    doy = np.repeat(dates.dayofyear.values, k)
    out["doy_sin"], out["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)

    out["fut7"] = forward_sum(M, horizon)[t_idx].ravel()          # target window, NEVER a feature
    out["y"] = (out["fut7"] >= 1).astype(int)

    added = []
    if precip is not None:
        if list(precip.columns) != list(grid.cell_id):
            raise ValueError("precip columns must equal grid.cell_id in the same order")
        for name, A in build_env_arrays(precip, sm_monthly, days).items():
            out[name] = np.asarray(A)[t_idx].ravel()
            added.append(name)

    if regional is not None:
        reg = regional.reindex(dates)
        for c in reg.columns:
            if c not in out.columns:
                out[c] = np.repeat(reg[c].values, k)
                added.append(c)
    if added:
        out = out.dropna(subset=added).reset_index(drop=True)
    return out
