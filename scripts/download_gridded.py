"""Download IMERG daily + MERRA-2 monthly SUBSETS for the study box, one file per year (resumable).

Credentials: environment variables EARTHDATA_USERNAME / EARTHDATA_PASSWORD (Kaggle: Add-ons > Secrets).
First run a probe to verify variable names, units and shapes:   python scripts/download_gridded.py --probe
Then the full download:                                         python scripts/download_gridded.py
Outputs: data/raw/gpm/imerg_daily_<year>.nc and data/raw/merra2/gwetprof_monthly_<year>.nc
"""
import argparse, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from terrawatch.ingestion import gpm, merra2


def describe(da, label):
    v = da.values
    print(f"[{label}] dims={da.dims} shape={da.shape} | lat {float(da.lat.min()):.2f}..{float(da.lat.max()):.2f} "
          f"| lon {float(da.lon.min()):.2f}..{float(da.lon.max()):.2f}")
    print(f"[{label}] dates {str(da.time.values[0])[:10]} .. {str(da.time.values[-1])[:10]} | n={da.sizes['time']} "
          f"| NaN fraction {np.isnan(v).mean():.3f} | min/mean/max = {np.nanmin(v):.3f} / {np.nanmean(v):.3f} / {np.nanmax(v):.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=["imerg", "merra2", "both"], default="both")
    ap.add_argument("--start-year", type=int, default=2000)
    ap.add_argument("--end-year", type=int, default=2024)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--probe", action="store_true", help="tiny download to check variables, units and shapes")
    ap.add_argument("--out", default="data/raw")
    a = ap.parse_args()

    if a.probe:
        if a.what in ("imerg", "both"):
            describe(gpm.fetch_range("2015-09-01", "2015-09-03", workers=3), "IMERG daily (expect mm/day, 3 days)")
        if a.what in ("merra2", "both"):
            describe(merra2.fetch_range("2015-08-01", "2015-10-31", workers=3), "MERRA-2 GWETPROF monthly (expect 0-1, 3 months)")
        return

    for year in range(a.start_year, a.end_year + 1):
        jobs = []
        if a.what in ("imerg", "both"):
            jobs.append((Path(a.out) / "gpm" / f"imerg_daily_{year}.nc", gpm, f"{year}-01-01", f"{year}-12-31"))
        if a.what in ("merra2", "both"):
            jobs.append((Path(a.out) / "merra2" / f"gwetprof_monthly_{year}.nc", merra2, f"{year}-01-01", f"{year}-12-31"))
        for path, mod, t0, t1 in jobs:
            if path.exists():
                print(f"{year} {path.name}: exists, skipped", flush=True)
                continue
            t = time.time()
            da = mod.fetch_range(t0, t1, workers=a.workers)
            path.parent.mkdir(parents=True, exist_ok=True)
            da.to_dataset().to_netcdf(path, engine="h5netcdf")
            print(f"{year} {path.name}: {da.sizes['time']} time steps, NaN {float(da.isnull().mean()):.3f}, {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
