"""Source rasters -> per-cell tables. NumPy/pandas only (no xarray), so it can be unit-tested offline.

Two honest rules (spec 4.2 / 7.2):
  * IMERG (0.1 deg, finer than the cell): mean of the source pixels whose CENTER falls inside the cell.
  * MERRA-2 (0.625 x 0.5 deg, coarser than the cell): each cell takes the value of the source cell that
    contains its center. NO interpolation, so neighbouring cells share values. This does not add resolution.
"""
import numpy as np
import pandas as pd


def to_dates(t):
    """datetime64 or cftime-like times -> normalized pandas DatetimeIndex (IMERG files may use a julian calendar)."""
    t = np.asarray(t)
    try:
        return pd.DatetimeIndex(pd.to_datetime(t)).normalize()
    except (TypeError, ValueError):
        return pd.DatetimeIndex([f"{x.year:04d}-{x.month:02d}-{x.day:02d}" for x in t])


def cell_mean_from_pixels(values, lon, lat, grid, spec):
    """values (t, n_lat, n_lon) -> (t, n_cells) mean of valid pixels per cell (NaN if none), plus pixel counts."""
    values = np.asarray(values, float)
    ix = np.floor((np.asarray(lon) - spec.x0) / spec.res).astype(int)
    iy = np.floor((np.asarray(lat) - spec.y0) / spec.res).astype(int)
    in_box = (iy[:, None] >= 0) & (iy[:, None] < spec.ny) & (ix[None, :] >= 0) & (ix[None, :] < spec.nx)
    cid = np.where(in_box, iy[:, None] * spec.nx + ix[None, :], -1)
    col = pd.Series(np.arange(len(grid)), index=grid.cell_id.values).reindex(cid.ravel()).values   # NaN: not in grid
    sel = np.flatnonzero(~np.isnan(col))
    cols = col[sel].astype(int)
    v = values.reshape(values.shape[0], -1)[:, sel]
    ok = ~np.isnan(v)
    sums = np.zeros((values.shape[0], len(grid)))
    cnts = np.zeros_like(sums)
    np.add.at(sums, (slice(None), cols), np.where(ok, v, 0.0))
    np.add.at(cnts, (slice(None), cols), ok.astype(float))
    mean = np.where(cnts > 0, sums / np.maximum(cnts, 1), np.nan)
    return mean, np.bincount(cols, minlength=len(grid))


def nearest_cell_values(values, lon, lat, grid, max_dist=(0.5, 0.5), fill_missing=True):
    """values (t, n_lat, n_lon) on a COARSE grid -> (t, n_cells) by nearest source-cell center (no interpolation).
    max_dist = (lat, lon) in degrees: half a source cell. Fails loudly if the downloaded subset does not cover a cell.
    MERRA-2 land diagnostics are empty over open water: a coastal cell whose nearest source cell has no data in ANY
    month takes the nearest source cell that has data (warned, never silent), so the cell is not lost downstream."""
    import warnings
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    values = np.asarray(values, float)
    dj = np.abs(lat[:, None] - grid.lat.values[None, :])
    di = np.abs(lon[:, None] - grid.lon.values[None, :])
    j, i = dj.argmin(axis=0), di.argmin(axis=0)
    if (dj.min(axis=0) > max_dist[0] + 1e-9).any() or (di.min(axis=0) > max_dist[1] + 1e-9).any():
        raise ValueError("Source subset does not cover every grid cell: download with a larger padding.")
    out = values[:, j, i].copy()
    if fill_missing:
        has_data = ~np.isnan(values).all(axis=0)                       # (n_lat, n_lon)
        empty = np.flatnonzero(~has_data[j, i])
        for c in empty:
            d = (lat[:, None] - grid.lat.values[c]) ** 2 + (lon[None, :] - grid.lon.values[c]) ** 2
            d = np.where(has_data, d, np.inf)
            jj, ii = np.unravel_index(np.argmin(d), d.shape)
            out[:, c] = values[:, jj, ii]
        if len(empty):
            warnings.warn(f"{len(empty)} of {len(grid)} cells had an empty nearest source cell (open water); "
                          "they use the nearest source cell with data.")
    return out


def save_matrix(df, path):
    """Index = dates, columns = cell_id. Parquet needs string column names, so they are converted back on load."""
    out = df.copy()
    out.columns = [str(c) for c in out.columns]
    out.index.name = "date"
    out = out.reset_index()
    try:
        out.to_parquet(path, index=False)
        return str(path)
    except ImportError:
        alt = str(path).rsplit(".", 1)[0] + ".csv"
        out.to_csv(alt, index=False)
        return alt


def load_matrix(path):
    path = str(path)
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df.columns = [int(c) for c in df.columns]
    return df
