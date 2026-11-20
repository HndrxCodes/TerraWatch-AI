"""IMERG Final Daily V07 (GPM_3IMERGDF): daily mean precipitation rate in mm/day, 0.1 degree, dims (time, lon, lat).
Collection concept id from the GES DISC/CMR record of GPM_3IMERGDF V07 (IMERG V08 is a separate version: do not mix).
The variable name and orientation are checked at read time and fail loudly if they differ from what is assumed."""
import numpy as np

from ..config import BBOX
from ..preprocessing.gridded import to_dates
from .earthdata import read_granules

IMERG_CONCEPT_ID = "C2723754864-GES_DISC"
VAR = "precipitation"


def _slice(coord, lo, hi):
    c = np.asarray(coord)
    return slice(lo, hi) if c[0] <= c[-1] else slice(hi, lo)         # works for ascending or descending axes


def read_granule(f, bbox=BBOX, pad=0.1, var=VAR):
    import xarray as xr
    w, s, e, n = bbox
    with xr.open_dataset(f, engine="h5netcdf") as ds:
        if var not in ds:
            raise KeyError(f"{var!r} not found in IMERG file. Variables: {list(ds.data_vars)}")
        da = ds[var].sel(lon=_slice(ds["lon"].values, w - pad, e + pad), lat=_slice(ds["lat"].values, s - pad, n + pad))
        da = da.transpose("time", "lat", "lon").load()
    da = da.where(da >= 0)                                  # fill values -> NaN, never zero
    return da.assign_coords(time=to_dates(da["time"].values))


def fetch_range(start, end, bbox=BBOX, workers=8):
    import xarray as xr
    parts = read_granules(IMERG_CONCEPT_ID, start, end, lambda f: read_granule(f, bbox), workers)
    da = xr.concat(parts, dim="time").sortby("time")
    da = da.isel(time=~da.get_index("time").duplicated())
    da.name = "precip_mm_day"
    da.attrs.update(units="mm/day", source="GPM_3IMERGDF V07 (NASA GES DISC)", bbox=str(bbox))
    return da
