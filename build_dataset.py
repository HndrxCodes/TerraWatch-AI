"""Build the per-cell weekly dataset from the FIRMS CSV and region.geojson.

Usage (from the repo root):
  python scripts/build_dataset.py --firms data/raw/firms/<file>.csv --region config/region.geojson \
         [--regional data/features/regional_features.parquet] [--out data/features/cell_weekly.parquet]
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from terrawatch.ingestion.firms import load_firms
from terrawatch.preprocessing.spatial import load_polygons, build_grid
from terrawatch.features.labels import build_cell_dataset


def read_table(path):
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path, index_col=0, parse_dates=True)


def write_table(df, path):
    try:
        df.to_parquet(path, index=False)
        return path
    except ImportError:
        alt = str(path).rsplit(".", 1)[0] + ".csv"
        print("pyarrow not installed -> writing CSV instead (pip install pyarrow for Parquet)")
        df.to_csv(alt, index=False)
        return alt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--firms", required=True)
    ap.add_argument("--region", default="config/region.geojson")
    ap.add_argument("--regional", default=None, help="optional daily regional features exported from the notebook")
    ap.add_argument("--out", default="data/features/cell_weekly.parquet")
    a = ap.parse_args()

    det = load_firms(a.firms)
    polys = load_polygons(a.region)
    grid, spec = build_grid(polys)
    print(f"Detections kept: {len(det)} | grid cells kept: {len(grid)} (0.25 deg, >=20% inside province)")
    regional = read_table(a.regional) if a.regional else None

    D = build_cell_dataset(det, grid, spec, regional=regional)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    grid.to_csv("data/processed/grid_cells.csv", index=False)
    saved = write_table(D, a.out)
    print(f"Saved {len(D)} rows ({D.date.nunique()} weeks x {D.cell_id.nunique()} cells) -> {saved}")
    print(f"Positive rate Y: {D.y.mean():.3f}")
    print("Positive rate by year (sanity check: should peak in 2006, 2015, 2019):")
    print(D.groupby(D.date.dt.year).y.mean().round(3).to_string())


if __name__ == "__main__":
    main()
