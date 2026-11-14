# TerraWatch AI

**Earth System Trend Detective for South Sumatra: rainfall trends, dry spells, and satellite-detected fire activity**

NASA Space Apps Challenge 2026 (Jakarta) · Challenge: *Be An Earth System Trend Detective!* · Solo project

> **Status:** hackathon prototype. Trend, anomaly, dry-spell, and fire-link results are computed from real NASA data. The 7-day prediction model is a design only. Items marked **TODO** still need to be filled in.

---

## 1. Problem

South Sumatra has large forest and peatland areas that are vulnerable to prolonged dry conditions and fire. The challenge asks four questions about an Earth system variable:

1. **What** is changing?
2. **Where** is it changing?
3. **How much** is it changing?
4. Are the changes **statistically significant**?

TerraWatch AI answers these for **rainfall** and then asks a follow-up question: *do dry periods line up with satellite-detected fire activity?*

## 2. Approach

```
Rainfall (GPM IMERG) -> Trend test -> Anomalies and dry spells -> Link to fire detections (FIRMS) -> Risk blueprint
```

| Step | Method |
|---|---|
| Trend | Mann-Kendall test and Sen's slope (annual, seasonal, dry-season series) |
| Anomaly | Robust z-score (median and MAD) against same-calendar-month baseline; months with z < -1.5 flagged as unusually dry |
| Dry spell | Consecutive days below a rainfall threshold (threshold is documented, not tuned to results) |
| Fire link | Spearman rank correlation between Aug-Oct rainfall / longest dry spell and Aug-Oct FIRMS detections (24 years). Correlation only, no causal claim |
| Prediction | 7-day probability of satellite-detected fire activity: **design only, not implemented** |

## 3. Data

| Dataset | Details |
|---|---|
| NASA GPM IMERG Final Run, Daily | Product `GPM_3IMERGDF` **V07**, variable: daily mean precipitation rate (combined microwave-IR), units **mm/day**, native resolution 0.1 degree |
| Access | NASA Giovanni, Time Series, Area-Averaged |
| Region | Bounding box `102.0, -4.9, 106.2, -1.6` (data box `102.05, -4.85, 106.15, -1.65`) |
| Period | 2000-01-01 to 2024-12-31 (9,132 days) |
| Quality checks | No missing days, no duplicates, no fill values (-9999.9) found |
| MERRA-2 soil moisture | `M2TMNXLND` V5.12.4, variable `GWETPROF` (profile soil moisture, dimensionless 0-1), monthly, native grid 0.5 x 0.625 degree, 2000-2024. This is a **model reanalysis**, not a direct satellite observation. Giovanni data box: 102.5 to 105.625 E, -4.5 to -2 N (smaller than the rainfall box because of the coarse grid) |
| NASA FIRMS | MODIS active fire detections, same bounding box, 2001-2024 (225,736 raw records). Filters: Terra satellite only (Aqua starts mid-2002, so combining both would inflate counts over time), confidence >= 30, type = 0 (presumed vegetation fire), duplicates removed. Product: MODIS Active Fire and Thermal Anomalies, standard-quality archive (MCD14ML) from NASA FIRMS. The `version` field in the downloaded file has two values, `6.03` and `61.03`, both without the `NRT` suffix, so no near-real-time records are included. Per the FIRMS attribute guide the number before the decimal is the processing collection, so the file combines Collection 6 and Collection 6.1 records. |

Reproduce the rainfall series with the Giovanni URL stored in the header of the CSV file.

**Limitations of the data**
- Values are an **area average** over the bounding box, which is rectangular and larger than the province. This answers "what", not "where".
- IMERG resolution is about 10 km. Averaging does not create finer detail.
- FIRMS records satellite detections, not every fire. No detection does not prove no fire.
- The FIRMS README lists known MODIS gaps: late June to early July 2001, some data missing in 2002, mid-August 2007, and 21-22 April 2009. 2002 and 2007 overlap the Aug-Oct window, so their detection counts may be underestimated.

## 4. Preliminary results (rainfall, real data)

Mean annual rainfall in the area average is about **2,880 mm/year**. Trend tests (Mann-Kendall, two-sided; Sen's slope):

| Series | Period | Mann-Kendall p | Sen's slope | Significant? |
|---|---|---|---|---|
| Annual total | 2000-2024 | 0.91 | +1.7 mm/yr (CI -29 to +25) | No |
| Monthly, seasonal Mann-Kendall | 2000-2024 | 0.87 | about +1.2 mm/yr | No |
| Dry season (Jun-Sep) total | 2000-2024 | 0.80 | +2.0 mm/yr (CI -9 to +15) | No |
| Aug-Oct total | 2000-2024 | 0.94 | -0.7 mm/yr (CI -17 to +17) | No |

**Interpretation:** no significant long-term monotonic trend in area-average rainfall. Instead, **year-to-year variability is large**. The driest Aug-Oct periods occurred in 2015, 2019, 2023, and 2006. The longest runs of area-average rainfall below 1 mm/day were 35 days (2006), 34 days (2019), and 22 days (2015).

These are preliminary numbers and should be re-run from the notebook in `notebooks/` before final submission. Absence of a trend in the regional average does not rule out local trends.

## 5. Fire link (real data)

After filtering, 54,896 Terra MODIS detections remain (confidence >= 30).

| Relationship (2001-2024, n = 24 years) | Spearman rho | p-value |
|---|---|---|
| Aug-Oct rainfall vs Aug-Oct fire detections | -0.92 | < 0.001 |
| Longest dry spell vs Aug-Oct fire detections | +0.78 | < 0.001 |

The years with the most Aug-Oct detections were **2015 (8,995), 2006 (6,558), and 2019 (4,671)**. These are also among the driest Aug-Oct periods and have the longest dry spells (22, 35, and 34 days).

**Robustness check:** with a stricter confidence filter (>= 50, 45,972 detections) the correlations are unchanged (-0.92 and +0.78) and the top three years are the same.

**Caveats**
- Correlation, not causation. Peatland condition, land clearing, and fire management also affect fire activity.
- Rainfall is not the whole story: 2023 had a very dry Aug-Oct but far fewer detections than 2015, 2006, or 2019.
- Aug-Oct was chosen from the seasonal rainfall cycle, not from the fire data.
- 24 yearly points, one rectangular area average, and satellite detections rather than all fires.

### Soil moisture (MERRA-2, monthly)
Annual mean soil wetness has no significant trend (Mann-Kendall p = 0.15, Sen's slope +0.0025 per year, 95% CI -0.0006 to +0.0053). The driest Aug-Oct periods by soil wetness were 2015, 2003, 2019, 2002, 2012, and 2006. Soil wetness and Aug-Oct fire detections are strongly negatively correlated (Spearman rho = -0.88, p < 0.001, n = 24; computed with the confidence >= 50 fire counts). Soil wetness and rainfall are themselves correlated (rho = 0.76), so this is **not independent evidence**: it supports the same dry-conditions picture. Soil moisture here is a model product on a coarse 0.5 x 0.625 degree grid.

## 6. Prediction blueprint (design only)

- **Blueprint (not implemented):** predict the probability of at least one FIRMS detection in a grid cell during the next 7 days.
  - Inputs only from information available at prediction time (lagged rainfall, soil moisture, vegetation, temperature) to avoid data leakage.
  - Chronological train/validation/test split, never random only.
  - Class imbalance handled with weights and precision-recall metrics; probabilities calibrated.
  - SHAP used to explain model behavior. It does not prove causation.

## 7. Repository structure

```
terrawatch-ai/
├── README.md
├── data/
│   └── raw/                # Giovanni IMERG CSV; FIRMS CSV (TODO)
├── notebooks/              # Notebook (Kaggle/Colab): trend, anomaly, dry spell, fire link
└── docs/                   # slides link, notes
```

## 8. Tools

Python (pandas, NumPy, SciPy, Matplotlib), Kaggle Notebooks, NASA Giovanni, NASA FIRMS, GitHub.

## 9. Use of AI

AI (Claude, by Anthropic) was used for ideation, project planning, and drafting code and documentation. All data come from NASA sources, and all numbers reported here were computed from the downloaded NASA data. The author reviews and takes responsibility for the content.

## 10. References

- Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J., Tan, J. *GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07 (GPM_3IMERGDF)*. Goddard Earth Sciences Data and Information Services Center (GES DISC). DOI: 10.5067/GPM/IMERGDF/DAY/07 (verify on the GES DISC product page).
- NASA Giovanni, GES DISC: https://giovanni.gsfc.nasa.gov/giovanni/
- NASA FIRMS (LANCE / ESDIS), MODIS Active Fire and Thermal Anomalies (MCD14ML standard archive): https://firms.modaps.eosdis.nasa.gov/ . Cited following the NASA Earthdata data-use policy: https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-policy
- Global Modeling and Assimilation Office (GMAO). *MERRA-2 tavgM_2d_lnd_Nx: 2d, Monthly mean, Time-averaged, Single-Level, Assimilation, Land Surface Diagnostics V5.12.4*. GES DISC. DOI: 10.5067/8S35XF81C28F (verify on the GES DISC product page).
- NASA Space Apps Challenge 2026, *Be An Earth System Trend Detective!*: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/
- Mann, H.B. (1945), Kendall, M.G. (1975), Sen, P.K. (1968): trend test and slope estimator.
- Hirsch, R.M., Slack, J.R., Smith, R.A. (1982): seasonal Kendall test.

## 11. Author

Solo participant, NASA Space Apps Jakarta 2026.
