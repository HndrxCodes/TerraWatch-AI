"""Walk-forward evaluation for the cell-level model (same protocol as notebook cell 15).

For each test year Y: train ONLY on rows whose 7-day label window ended before Y began, predict Y.
Benchmarks that a cell-level model must beat:
  - "season only": same probability for every cell in a week (what the regional model effectively does)
  - "cell climatology": the cell's own historical frequency of Y=1 in that calendar month (shrunk to the
    regional monthly rate). Any spatial skill must come on top of this, otherwise the model only learned
    where fires usually happen.
  - "persistence (naive)": predict Y=1 if the cell had any detection in the last 7 days. If a model barely
    beats this, its skill is mostly "fire now -> fire next week", not early warning.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ..config import HORIZON, WF_YEARS

CLIM = "cell climatology (baseline)"
PERSIST = "persistence (naive)"


def rf_model(n_estimators=150, seed=0):
    return RandomForestClassifier(n_estimators=n_estimators, min_samples_leaf=5, class_weight="balanced_subsample",
                                  random_state=seed, n_jobs=-1)


def climatology_baseline(tr, te, shrink=5.0):
    """P(Y=1 | cell, month) from training rows, shrunk toward the regional monthly rate."""
    trm, tem = tr.date.dt.month, te.date.dt.month
    regional = tr.groupby(trm).y.mean()
    g = tr.groupby([tr.cell_id, trm]).y.agg(["sum", "count"])
    key = pd.MultiIndex.from_arrays([te.cell_id.values, tem.values])
    s = g["sum"].reindex(key).fillna(0).values
    c = g["count"].reindex(key).fillna(0).values
    pm = tem.map(regional).fillna(tr.y.mean()).values
    return (s + shrink * pm) / (c + shrink)


def walk_forward_cells(D, feature_sets, years=WF_YEARS, horizon=HORIZON, n_estimators=150):
    """Returns {name: DataFrame[date, cell_id, year, y, p]} pooled over all test years."""
    D = D.copy()
    D["year"] = D.date.dt.year
    pooled = {name: [] for name in list(feature_sets) + [CLIM, PERSIST]}
    for yr in years:
        te = D[D.year == yr]
        if te.empty:
            continue
        tr = D[D.date < te.date.min() - pd.Timedelta(days=horizon)]   # label window ends before test starts
        if tr.y.sum() == 0:
            continue
        base = {"date": te.date.values, "cell_id": te.cell_id.values, "year": yr, "y": te.y.values}
        for name, cols in feature_sets.items():
            m = rf_model(n_estimators).fit(tr[cols], tr.y)
            pooled[name].append(pd.DataFrame({**base, "p": m.predict_proba(te[cols])[:, 1]}))
        pooled[CLIM].append(pd.DataFrame({**base, "p": climatology_baseline(tr, te)}))
        pooled[PERSIST].append(pd.DataFrame({**base, "p": (te["log_fire_7d"].values > 0).astype(float)}))
    return {k: pd.concat(v, ignore_index=True) for k, v in pooled.items() if v}


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def platt_by_year(df):
    """Platt scaling where each year is calibrated with the OTHER years' out-of-sample predictions."""
    df = df.copy()
    df["pc"] = 0.0
    for yr in df.year.unique():
        oth, cur = df[df.year != yr], (df.year == yr).values
        pl = LogisticRegression().fit(_logit(oth.p.values).reshape(-1, 1), oth.y)
        df.loc[cur, "pc"] = pl.predict_proba(_logit(df.loc[cur, "p"].values).reshape(-1, 1))[:, 1]
    return df


def summarize(pooled):
    rows = []
    for name, d in pooled.items():
        d = platt_by_year(d)
        rows.append({"model": name, "PR-AUC": average_precision_score(d.y, d.p), "ROC-AUC": roc_auc_score(d.y, d.p),
                     "Brier(cal)": brier_score_loss(d.y, d.pc),
                     "Brier(base rate)": brier_score_loss(d.y, np.full(len(d), d.y.mean())),
                     "positive rate": d.y.mean(), "rows": len(d)})
    return pd.DataFrame(rows).round(3)


def year_bootstrap_gain(a, b, n=200, seed=1):
    """95% interval of PR-AUC(a) - PR-AUC(b), resampling YEARS (weeks and cells inside a year are dependent)."""
    ga, gb = dict(tuple(a.groupby("year"))), dict(tuple(b.groupby("year")))
    years, rng, diffs = np.array(sorted(ga)), np.random.default_rng(seed), []
    for _ in range(n):
        ys = rng.choice(years, len(years), replace=True)
        A, B = pd.concat([ga[y] for y in ys]), pd.concat([gb[y] for y in ys])
        if A.y.sum() == 0:
            continue
        diffs.append(average_precision_score(A.y, A.p) - average_precision_score(B.y, B.p))
    return np.percentile(diffs, [2.5, 50, 97.5])


def summarize_onset(pooled, D):
    """Skill on rows with NO detection in the cell during the last 7 days ("onset" weeks).
    Persistence cannot help there, so this isolates what the environment adds. Platt is skipped (PR/ROC only)."""
    quiet = D.loc[D.log_fire_7d == 0, ["date", "cell_id"]].assign(quiet=True)
    rows = []
    for name, d in pooled.items():
        d = d.merge(quiet, on=["date", "cell_id"], how="inner")
        if d.y.sum() == 0 or d.y.nunique() < 2:
            continue
        rows.append({"model": name, "PR-AUC (onset weeks)": average_precision_score(d.y, d.p),
                     "ROC-AUC (onset weeks)": roc_auc_score(d.y, d.p), "positive rate": d.y.mean(), "rows": len(d)})
    return pd.DataFrame(rows).round(3)
