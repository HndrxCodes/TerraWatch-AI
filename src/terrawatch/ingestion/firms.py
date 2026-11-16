"""Load and filter the FIRMS MODIS CSV exactly like notebook cell 8."""
import pandas as pd
from ..config import BBOX, CONF_MIN, SATELLITE, DATA_START, DATA_END


def load_firms(path, bbox=BBOX, satellite=SATELLITE, conf_min=CONF_MIN,
               start=DATA_START, end=DATA_END) -> pd.DataFrame:
    f = pd.read_csv(path)
    f.columns = [c.strip().lower() for c in f.columns]
    missing = {"latitude", "longitude", "acq_date"} - set(f.columns)
    if missing:
        raise ValueError(f"FIRMS file is missing columns: {sorted(missing)}")
    f["acq_date"] = pd.to_datetime(f["acq_date"])
    w, s, e, n = bbox
    f = f[f.longitude.between(w, e) & f.latitude.between(s, n)]
    if "satellite" in f.columns:
        f = f[f["satellite"].astype(str).str.contains(satellite, case=False)]
    if "confidence" in f.columns:                       # MODIS confidence is numeric 0-100
        f = f[pd.to_numeric(f["confidence"], errors="coerce") >= conf_min]
    if "type" in f.columns:                             # 0 = presumed vegetation fire
        f = f[f["type"] == 0]
    keys = [c for c in ("latitude", "longitude", "acq_date", "acq_time") if c in f.columns]
    f = f.drop_duplicates(keys)
    f = f[(f.acq_date >= start) & (f.acq_date <= end)]
    return f.reset_index(drop=True)
