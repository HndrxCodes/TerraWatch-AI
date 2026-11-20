"""Offline tests for gridded aggregation and per-cell env features. SYNTHETIC arrays only (code tests, not results)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from test_features import synthetic, KW
from terrawatch.preprocessing.gridded import cell_mean_from_pixels, nearest_cell_values, to_dates
from terrawatch.features.env import build_env_arrays, dry_run_days
from terrawatch.features.labels import build_cell_dataset


def test_pixel_mean_per_cell_and_nan():
    _, grid, spec = synthetic()                                    # 16 cells over lon 102-103, lat -3..-2
    lon = np.arange(101.95, 103.06, 0.1)
    lat = np.arange(-3.05, -1.94, 0.1)
    LON, LAT = np.meshgrid(lon, lat)
    cid = (np.floor((LAT - spec.y0) / spec.res) * spec.nx + np.floor((LON - spec.x0) / spec.res))
    vals = np.stack([cid, cid + 10.0])                             # 2 "days"; value = cell id (+10)
    vals[0, 3, 4] = np.nan                                          # one missing pixel must not bias the mean
    mean, npix = cell_mean_from_pixels(vals, lon, lat, grid, spec)
    assert np.allclose(mean[0], grid.cell_id.values) and np.allclose(mean[1], grid.cell_id.values + 10)
    assert npix.min() >= 4


def test_nearest_cell_has_no_interpolation():
    _, grid, _ = synthetic()
    lat = np.arange(-4.0, -1.0, 0.5)                                # MERRA-like coarse axes
    lon = 102.5 + 0.625 * np.arange(-2, 3)
    V = (lat[:, None] * 100 + lon[None, :])[None]
    out = nearest_cell_values(V, lon, lat, grid, max_dist=(0.25 + 0.5, 0.3125 + 0.5))[0]
    for c in range(len(grid)):
        j = np.abs(lat - grid.lat[c]).argmin(); i = np.abs(lon - grid.lon[c]).argmin()
        assert out[c] == V[0, j, i]
    try:
        nearest_cell_values(V, lon, lat + 10, grid)
        raise AssertionError("should fail when the subset does not cover the cells")
    except ValueError:
        pass


def test_to_dates_handles_cftime_like():
    class T:                                                        # stands in for a cftime julian date
        def __init__(self, y, m, d): self.year, self.month, self.day = y, m, d
    assert list(to_dates([T(2015, 9, 1), T(2015, 9, 2)])) == [pd.Timestamp("2015-09-01"), pd.Timestamp("2015-09-02")]


def _rain(days, k, seed=0):
    return pd.DataFrame(np.random.default_rng(seed).gamma(0.6, 6.0, (len(days), k)), index=days)


def test_dry_run_bruteforce_and_nan_resets():
    x = np.array([[5, 0, 0, np.nan, 0, 0, 0, 9, 0]], float).T
    assert dry_run_days(x).ravel().tolist() == [0, 1, 2, 0, 1, 2, 3, 0, 1]


def test_env_features_are_causal():
    days = pd.date_range("2001-01-01", "2005-12-31")
    k = 5
    P = _rain(days, k)
    sm = pd.DataFrame(np.random.default_rng(1).uniform(0.3, 0.9, (60, k)), index=pd.period_range("2001-01", periods=60, freq="M"))
    T = pd.Timestamp("2004-06-15")
    P2 = P.copy(); P2.loc[P2.index > T] += 50.0                     # change ONLY the future
    sm2 = sm.copy(); sm2.loc[sm2.index >= pd.Period("2004-06", "M")] += 0.5     # change the current and later months
    a, b = build_env_arrays(P, sm, days), build_env_arrays(P2, sm2, days)
    i = days.get_loc(T)
    for name in a:
        assert np.allclose(a[name][: i + 1], b[name][: i + 1], equal_nan=True), f"{name} leaks future information"
    # sm_prev on a day in June 2004 equals May 2004 exactly
    assert np.allclose(a["sm_prev"][i], sm.loc[pd.Period("2004-05", "M")].values)


def test_rolling_rain_matches_pandas_and_dataset_has_cell_variation():
    det, grid, spec = synthetic()
    days = pd.date_range("2001-01-01", "2005-12-31")
    P = _rain(days, len(grid)); P.columns = grid.cell_id.values
    sm = pd.DataFrame(np.random.default_rng(2).uniform(0.3, 0.9, (60, len(grid))),
                      index=pd.period_range("2001-01", periods=60, freq="M"), columns=grid.cell_id.values)
    D = build_cell_dataset(det, grid, spec, precip=P, sm_monthly=sm, **KW)
    assert not D[["rain_7d", "rain_30d", "rain_60d", "rain_90d", "dry_run", "sm_prev"]].isna().any().any()
    r = D.sample(50, random_state=0)
    for _, row in r.iterrows():
        assert np.isclose(row.rain_30d, P.loc[row.date - pd.Timedelta(days=29): row.date, row.cell_id].sum())
    assert D.groupby("date").rain_30d.std().mean() > 0              # cells differ at the same date (not broadcast)


def test_precip_column_order_is_checked():
    det, grid, spec = synthetic()
    days = pd.date_range("2001-01-01", "2005-12-31")
    P = _rain(days, len(grid)); P.columns = grid.cell_id.values[::-1]
    try:
        build_cell_dataset(det, grid, spec, precip=P, **KW)
        raise AssertionError("column order mismatch must raise")
    except ValueError:
        pass


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
