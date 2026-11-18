"""Walk-forward comparison: season only vs cell climatology vs cell history (+ regional env if present).

Usage: python scripts/evaluate_cell_baseline.py --data data/features/cell_weekly.parquet
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd
from terrawatch.features.labels import SEASON, CELL_STATIC, CELL_HISTORY
from terrawatch.evaluation.validation import (walk_forward_cells, summarize, summarize_onset,
                                              year_bootstrap_gain, CLIM, PERSIST)

REGIONAL_ENV = ["rain_7d", "rain_30d", "rain_60d", "rain_90d", "dry_run", "sm_prev"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/features/cell_weekly.parquet")
    ap.add_argument("--trees", type=int, default=150)
    a = ap.parse_args()
    D = pd.read_parquet(a.data) if a.data.endswith(".parquet") else pd.read_csv(a.data, parse_dates=["date"])

    sets = {"season only": SEASON, "cell history": SEASON + CELL_STATIC + CELL_HISTORY}
    env = [c for c in REGIONAL_ENV if c in D.columns]
    if env:
        sets["no fire history (season + position + env)"] = SEASON + CELL_STATIC + env
        sets["cell history + regional env"] = SEASON + CELL_STATIC + CELL_HISTORY + env
    else:
        print("No regional env columns found: run build_dataset.py with --regional to add rain/soil features.")

    pooled = walk_forward_cells(D, sets, n_estimators=a.trees)
    print("\nWALK-FORWARD (train on past only). No-skill PR-AUC = positive rate.")
    print(summarize(pooled).to_string(index=False))
    pairs = [("cell history", CLIM), ("cell history", "season only"), ("cell history", PERSIST)]
    if env:
        pairs += [("cell history + regional env", "cell history"),
                  ("cell history + regional env", PERSIST),
                  ("no fire history (season + position + env)", CLIM)]
    for new, old in pairs:
        lo, mid, hi = year_bootstrap_gain(pooled[new], pooled[old])
        print(f"PR-AUC gain of '{new}' over '{old}': {mid:+.3f} (95% year-bootstrap {lo:+.3f} to {hi:+.3f})")
    print("\nONSET WEEKS ONLY (no detection in the cell during the previous 7 days; persistence has no signal here)")
    print(summarize_onset(pooled, D).to_string(index=False))
    print("\nNote: Platt calibration is fitted on the other test years' out-of-sample predictions.")


if __name__ == "__main__":
    main()
