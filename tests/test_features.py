"""Leakage and label tests. SYNTHETIC data only (random detections), used to test code, never to claim results."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
import pandas as pd
from terrawatch.preprocessing.spatial import build_grid, assign_cells
from terrawatch.features.labels import build_cell_dataset, CELL_HISTORY

KW = dict(data_start="2001-01-01", ml_start="2002-01-01", end="2005-12-31", gaps=[("2004-03-01", "2004-03-10")])


def synthetic():
    square = [[np.array([[102.0, -3.0], [103.0, -3.0], [103.0, -2.0], [102.0, -2.0], [102.0, -3.0]])]]
    grid, spec = build_grid(square)
    rng = np.random.default_rng(0)
    n = 4000
    det = pd.DataFrame({"latitude": rng.uniform(-3.2, -1.8, n), "longitude": rng.uniform(101.8, 103.2, n),
                        "acq_date": pd.to_datetime("2001-01-01") + pd.to_timedelta(rng.integers(0, 1826, n), unit="D")})
    return det, grid, spec


def test_grid_has_16_cells():
    _, grid, _ = synthetic()
    assert len(grid) == 16 and grid.frac_inside.min() > 0.99


def test_label_matches_bruteforce():
    det, grid, spec = synthetic()
    D = build_cell_dataset(det, grid, spec, **KW)
    det = det.assign(cell_id=assign_cells(det, spec))
    for _, r in D.sample(300, random_state=1).iterrows():
        win = det[(det.cell_id == r.cell_id) & (det.acq_date > r.date) & (det.acq_date <= r.date + pd.Timedelta(days=7))]
        assert r.fut7 == len(win) and r.y == int(len(win) >= 1)


def test_features_ignore_the_future():
    det, grid, spec = synthetic()
    T = pd.Timestamp("2004-06-30")
    full = build_cell_dataset(det, grid, spec, **KW)
    cut = build_cell_dataset(det[det.acq_date <= T], grid, spec, **KW)
    m = full.merge(cut, on=["date", "cell_id"], suffixes=("", "_cut"))
    past = m[m.date <= T]
    for c in CELL_HISTORY + ["doy_sin", "doy_cos"]:
        assert np.allclose(past[c], past[c + "_cut"]), f"feature {c} changed when future detections were removed"
    early = m[m.date <= T - pd.Timedelta(days=7)]
    assert (early.y == early.y_cut).all()          # labels differ only inside the last 7 days before T


def test_gap_rows_dropped_and_caps():
    det, grid, spec = synthetic()
    D = build_cell_dataset(det, grid, spec, **KW)
    bad = (D.date >= pd.Timestamp("2004-03-01") - pd.Timedelta(days=30)) & (D.date <= pd.Timestamp("2004-03-10"))
    assert not bad.any()
    assert D.days_since_fire.between(0, 365).all() and (D.fut7 >= 0).all()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
