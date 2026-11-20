"""Raw IMERG/MERRA-2 subsets -> per-cell tables (data/processed/cell_precip_daily.parquet, cell_sm_monthly.parquet).

Usage: python scripts/aggregate_gridded.py --region config/region.geojson [--giovanni-csv <regional rain csv>]
The optional Giovanni check compares the plain pixel mean over the study box with your regional rain series
(same variable, same box): a large mismatch means a unit, orientation or date problem, so look at it before modelling.
"""
import argparse, glob, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
import pandas as pd
import xarray as xr
from terrawatch.config import BBOX
from terrawatch.preprocessing.spatial import load_polygons, build_grid
from terrawatch.preprocessing.gridded import (cell_mean_from_pixels, nearest_cell_values, to_dates, save_matrix)


def load_stack(pattern):
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No files match {pattern}")
    das = []
    for p in paths:
        with xr.open_dataset(p) as ds:
            das.append(ds[list(ds.data_vars)[0]].load())
    da = xr.concat(das, dim="time").sortby("time")
    return da.isel(time=~da.get_index("time").duplicated())


def giovanni_check(da, csv):
    w, s, e, n = BBOX
    sub = da.sel(lon=slice(w, e), lat=slice(s, n)) if da.lat[0] <= da.lat[-1] else da.sel(lon=slice(w, e), lat=slice(n, s))
    mine = pd.Series(np.nanmean(sub.values, axis=(1, 2)), index=to_dates(sub.time.values))
    raw = pd.read_csv(csv, skiprows=8, parse_dates=["time"])
    raw.columns = ["time", "p"]
    ref = raw.set_index("time")["p"].where(lambda x: x > -9998)
    j = pd.concat([mine.rename("gridded"), ref.rename("giovanni")], axis=1).dropna()
    print(f"[Giovanni check] {len(j)} common days | correlation {j.corr().iloc[0, 1]:.3f} | "
          f"mean difference {(j.gridded - j.giovanni).mean():+.3f} mm/day | max |difference| {(j.gridded - j.giovanni).abs().max():.2f} mm/day")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="config/region.geojson")
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--giovanni-csv", default=None)
    a = ap.parse_args()

    grid, spec = build_grid(load_polygons(a.region))
    Path(a.out).mkdir(parents=True, exist_ok=True)

    rain = load_stack(f"{a.raw}/gpm/imerg_daily_*.nc")
    dates = to_dates(rain.time.values)
    mean, npix = cell_mean_from_pixels(rain.values, rain.lon.values, rain.lat.values, grid, spec)
    P = pd.DataFrame(mean, index=dates, columns=grid.cell_id.values)
    print(f"IMERG: {len(P)} days {dates.min().date()}..{dates.max().date()} | cells {P.shape[1]} | "
          f"source pixels per cell {npix.min()}-{npix.max()} | NaN fraction {P.isna().mean().mean():.4f}")
    missing = pd.date_range(dates.min(), dates.max()).difference(dates)
    print(f"IMERG missing calendar days: {len(missing)}")
    print(f"Mean annual rain per cell: {P.mean().mean() * 365.25:.0f} mm/yr (range {P.mean().min() * 365.25:.0f}-{P.mean().max() * 365.25:.0f})")
    print("Saved:", save_matrix(P, Path(a.out) / "cell_precip_daily.parquet"))
    if a.giovanni_csv:
        giovanni_check(rain, a.giovanni_csv)

    sm_files = glob.glob(f"{a.raw}/merra2/gwetprof_monthly_*.nc")
    if sm_files:
        sm = load_stack(f"{a.raw}/merra2/gwetprof_monthly_*.nc")
        S = pd.DataFrame(nearest_cell_values(sm.values, sm.lon.values, sm.lat.values, grid),
                         index=to_dates(sm.time.values), columns=grid.cell_id.values)
        print(f"MERRA-2: {len(S)} months | {S.shape[1]} grid cells share {S.iloc[0].nunique()} distinct source values "
              f"(coarse source, no interpolation) | NaN {S.isna().mean().mean():.4f}")
        print("Saved:", save_matrix(S, Path(a.out) / "cell_sm_monthly.parquet"))
    grid.to_csv(Path(a.out) / "grid_cells.csv", index=False)


if __name__ == "__main__":
    main()
