"""MERRA-2 M2TMNXLND V5.12.4 (monthly mean land surface diagnostics, 0.625 x 0.5 degree, dims (time, lat, lon)).
Variable GWETPROF = profile soil wetness (the same variable as the regional notebook cell 10).
MERRA-2 is a reanalysis (model + observations), not an observation and not a forecast."""
import numpy as np

from ..config import BBOX
from ..preprocessing.gridded import to_dates
from .earthdata import read_granules

MERRA2_LND_CONCEPT_ID = "C1276812856-GES_DISC"
VAR = "GWETPROF"


def _slice(coord, lo, hi):
    c = np.asarray(coord)
    return slice(lo, hi) if c[0] <= c[-1] else slice(hi, lo)


def read_granule(f, bbox=BBOX, pad=0.7, var=VAR):
    import xarray as xr
    w, s, e, n = bbox
    with xr.open_dataset(f, engine="h5netcdf") as ds:
        if var not in ds:
            raise KeyError(f"{var!r} not found in MERRA-2 file. Variables: {list(ds.data_vars)}")
        da = ds[var].sel(lon=_slice(ds["lon"].values, w - pad, e + pad), lat=_slice(ds["lat"].values, s - pad, n + pad))
        da = da.transpose("time", "lat", "lon").load()
    da = da.where(da < 1e10)                                # fill value -> NaN
    return da.assign_coords(time=to_dates(da["time"].values).to_period("M").to_timestamp())


def fetch_range(start, end, bbox=BBOX, workers=4):
    import xarray as xr
    parts = read_granules(MERRA2_LND_CONCEPT_ID, start, end, lambda f: read_granule(f, bbox), workers)
    da = xr.concat(parts, dim="time").sortby("time")
    da = da.isel(time=~da.get_index("time").duplicated())
    da.name = "gwetprof"
    da.attrs.update(source="MERRA-2 M2TMNXLND V5.12.4 (NASA GMAO / GES DISC)", bbox=str(bbox))
    return da
