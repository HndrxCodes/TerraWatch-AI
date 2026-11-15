# TerraWatch AI

**Earth System Trend Detective for South Sumatra: rainfall trends, dry spells, and satellite-detected fire activity**

NASA Space Apps Challenge 2026 (Jakarta) · Challenge: *Be An Earth System Trend Detective!* · Solo project

> **Status:** hackathon prototype. Trend, anomaly, dry-spell, and fire-link results are computed from real NASA data. Spatial fire maps and a region-level 7-day machine learning model are implemented and evaluated; a per-grid-cell prediction map and a dashboard are design only. Items marked **TODO** still need to be filled in.

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
| Prediction | Region-level 7-day classifier of *high* satellite-detected fire activity (Logistic Regression, Random Forest, XGBoost), chronological and leave-one-year-out evaluation. A per-grid-cell version is a design only |

## 3. Data

| Dataset | Details |
|---|---|
| NASA GPM IMERG Final Run, Daily | Product `GPM_3IMERGDF` **V07**, variable: daily mean precipitation rate (combined microwave-IR), units **mm/day**, native resolution 0.1 degree |
| Access | NASA Giovanni, Time Series, Area-Averaged |
| Region | Bounding box `102.0, -4.9, 106.2, -1.6` (data box `102.05, -4.85, 106.15, -1.65`) |
| Period | 2000-01-01 to 2024-12-31 (9,132 days) |
| Quality checks | No missing days, no duplicates, no fill values (-9999.9) found |
| MERRA-2 soil moisture | `M2TMNXLND` V5.12.4, variable `GWETPROF` (profile soil moisture, dimensionless 0-1), monthly, native grid 0.5 x 0.625 degree, 2000-2024. This is a **model reanalysis**, not a direct satellite observation. Giovanni data box: 102.5 to 105.625 E, -4.5 to -2 N (smaller than the rainfall box because of the coarse grid) |
| NOAA climate indices (non-NASA) | Dipole Mode Index (HadISST1.1, NOAA PSL) and Nino 3.4 anomaly (ERSSTv5, NOAA CPC), monthly 1999-2026. Used only in one experiment (no improvement, see section 6) |
| geoBoundaries (non-NASA) | gbOpen Indonesia ADM1 (simplified). South Sumatra polygon used to draw maps, to restrict fire detections to the province in a robustness check, and saved as `config/region.geojson` |
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

### Where: spatial fire patterns (FIRMS, 0.25 degree cells)

The rainfall and soil series are area averages, so the question *where* is answered with fire detections, which carry coordinates. Maps and per-cell tests use Terra detections with confidence >= 50 (2001-2024) unless stated.

- **Fire is concentrated in time and space.** The three most active years (2006, 2015, 2019) hold **42%** of all detections, and the top 10% of cells hold **37%**. With Aqua (2003-2024) the top three years (2006, 2012, 2015) hold 34% and the top 10% of cells 28%.
- **Per-cell trends in annual detections (Mann-Kendall, Sen's slope).** Terra: 35 of 155 tested cells are significant at p < 0.05 (about 8 expected by chance), 33 decreasing and 1 increasing (uncorrected). Aqua: 122 of 192 cells significant (about 10 expected), 111 remain after Benjamini-Hochberg false-discovery-rate control, all decreasing. Detections declined across most of the province in both satellites, strongest in parts of the central and western province. The cause is not established (policy, land use, sensor and overpass differences are all possible). Neighbouring cells are spatially correlated, so these counts overstate the number of independent trends.
- **Province-only check.** 33,724 of the 45,972 Terra detections in the study box (73%) fall inside South Sumatra. Restricting the fire-rainfall link to those detections gives Spearman rho = -0.91 (Aug-Oct rainfall) and +0.77 (longest dry spell), p < 0.001, n = 24, essentially unchanged.
- Maps use a plain grid without a basemap; the province outline comes from geoBoundaries.

Settings note: the headline fire-rainfall correlations in the table above use confidence >= 30; the soil, spatial, and machine learning results use confidence >= 50. For the fire-rainfall correlations, the two thresholds gave the same results.

## 6. Prediction model (7-day, region level)

**Task.** Given information available on day *t*, classify whether the next 7 days (t+1 to t+7) have *high* satellite-detected fire activity in the study box. "High" means a 7-day detection count at or above the 85th percentile of the training period (44 detections in the first run); the threshold never uses validation or test data.

**Design.**
- Inputs use data up to day *t* only: rainfall over the previous 7/30/60/90 days, consecutive dry days, soil wetness of the last *completed* month (MERRA-2), and season (sin/cos of day of year). Recent fire counts are used in a comparison variant.
- One prediction per week, 2003-2024. 2001-2002 are skipped because of FIRMS gaps, and windows around the known 2007 and 2009 gaps are excluded.
- Random Forest is the main model, compared with Logistic Regression and XGBoost; class weights handle imbalance; metrics are PR-AUC (a no-skill model scores the positive rate, about 0.12-0.15), ROC-AUC, Brier score, and calibration with Platt scaling.

**1. Walk-forward evaluation, 2010-2024 (main result).** For each year the model is trained only on earlier years (7-day gap) and then predicts that year.

| Inputs | PR-AUC | ROC-AUC |
|---|---|---|
| Season only | 0.37 | 0.87 |
| Season + rain + soil | **0.87** | 0.98 |
| Season + rain + soil + recent fires | 0.91 | 0.98 |

- The gain from rainfall and soil over season only is **+0.47 PR-AUC (95% interval from resampling years: +0.31 to +0.63)**.
- The result holds for other definitions of "high": PR-AUC 0.87 vs 0.52 (75th percentile) and 0.80 vs 0.35 (90th percentile).
- Calibration: Brier score 0.036 after calibration vs 0.105 for always predicting the base rate. Probabilities above 0.7 matched observed frequencies well (predicted 0.82 and 0.95, observed 0.89 and 0.90); middle bins contain few weeks and are noisy, so risk categories should be read as provisional.
- Per year the model is very good in the large fire years 2011, 2012, 2014, 2015, 2019, and 2023 (average precision 0.88-1.00) but weaker in the small years 2018 and 2024 (0.30 and 0.51, with only 3 and 5 high weeks).

**2. Other checks.** On the fixed 2022-2024 test period the model selected on validation reached PR-AUC 0.81 (season only: 0.32-0.43). A leave-one-year-out check over 22 years gave 0.86 vs 0.44 (gain +0.40, interval +0.26 to +0.52); this check can train on later years, so it measures skill across years, not forecasting.

**3. Early-warning view (episodes).** There were 13 episodes of high-activity weeks. A calibrated probability of at least 0.5 (threshold fixed in advance) raised an alarm for 11 of them (during the 4 weeks before the episode or while it lasted), with only 3 of 85 alarm weeks outside any episode window. However only 6 of 13 were flagged at or before their start (median lead time 0 weeks), and for the 6 large episodes (peak at least 300 detections per week) only 2. The biggest episodes of 2012 and 2015 were flagged 6 and 5 weeks **late**. The model is therefore a reliable monitor of dry conditions that favour intense fire activity, not yet an early-warning system.

**4. What did not help.** More rainfall features (change in rainfall, days since heavy rain, wet-day counts, anomalies against a monthly baseline): PR-AUC change +0.00 (interval -0.03 to +0.03), lead times unchanged. Indian Ocean Dipole and Nino 3.4 indices (lagged 2 months): PR-AUC change -0.02 and -0.01 (intervals include zero), lead times unchanged. June-July Dipole index vs Aug-Oct fires: rho = 0.31, p = 0.14. We kept the simpler model.

**5. Explanation (SHAP and permutation importance).** Rainfall over the previous 60, 90, 30, and 7 days dominates the model (mean absolute SHAP 0.12, 0.09, 0.08, 0.07), followed by consecutive dry days (0.05) and season (0.04 and 0.02); soil wetness adds almost nothing beyond rainfall (0.015, consistent with a soil-rain correlation of 0.76). Long dry spells push the score up. In September 2015 and September 2019 the 60- and 90-day rainfall pushed the score up the most (+0.14 and +0.11; +0.12 and +0.10), and in February 2022 it pushed it down (-0.13 and -0.10). SHAP describes how the model uses inputs; it does not show causes. It was computed on the final model, so these weeks are in the training data.

**Limits.**
- Only a few independent high-activity episodes exist, so differences between the top models are not reliable.
- The model recognises persistent dry conditions and does not predict the onset of large episodes weeks ahead.
- Region-level, area-average inputs: no spatial prediction is claimed. IMERG Final has a latency of months, so operational use would need the Early or Late product.
- Fire detections declined over time (section 5), which can shift the meaning of a fixed "high" threshold between early and late years.

**Design only (not implemented).** A per-grid-cell probability map (about 0.25 degree), MODIS vegetation indices, and a Streamlit dashboard.

## 7. Repository structure

```
terrawatch-ai/
├── README.md
├── data/
│   └── raw/                # Giovanni IMERG and MERRA-2 CSVs (FIRMS CSV is large: link to a public Kaggle dataset, TODO add link)
├── config/
│   └── region.geojson      # South Sumatra boundary (geoBoundaries)
├── notebooks/              # Notebook (Kaggle/Colab): trend, anomaly, dry spell, fire link
└── docs/                   # slides link, figures/ (fig_*.png), notes
```

## 8. Tools

Python (pandas, NumPy, SciPy, Matplotlib, scikit-learn, XGBoost, SHAP), Kaggle Notebooks, NASA Giovanni, NASA FIRMS, GitHub.

## 9. Use of AI

AI (Claude, by Anthropic) was used for ideation, project planning, and drafting code and documentation. The main data are NASA datasets (GPM IMERG, MERRA-2, FIRMS); the climate indices (NOAA) and the province boundary (geoBoundaries) are non-NASA sources. All numbers reported here were computed in the notebook from the downloaded data. The author reviews and takes responsibility for the content.

## 10. References

- Huffman, G.J., Stocker, E.F., Bolvin, D.T., Nelkin, E.J., Tan, J. *GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07 (GPM_3IMERGDF)*. Goddard Earth Sciences Data and Information Services Center (GES DISC). DOI: 10.5067/GPM/IMERGDF/DAY/07 (verify on the GES DISC product page).
- NASA Giovanni, GES DISC: https://giovanni.gsfc.nasa.gov/giovanni/
- NASA FIRMS (LANCE / ESDIS), MODIS Active Fire and Thermal Anomalies (MCD14ML standard archive): https://firms.modaps.eosdis.nasa.gov/ . Cited following the NASA Earthdata data-use policy: https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-policy
- Global Modeling and Assimilation Office (GMAO). *MERRA-2 tavgM_2d_lnd_Nx: 2d, Monthly mean, Time-averaged, Single-Level, Assimilation, Land Surface Diagnostics V5.12.4*. GES DISC. DOI: 10.5067/8S35XF81C28F (verify on the GES DISC product page).
- NASA Space Apps Challenge 2026, *Be An Earth System Trend Detective!*: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/
- Mann, H.B. (1945), Kendall, M.G. (1975), Sen, P.K. (1968): trend test and slope estimator.
- Hirsch, R.M., Slack, J.R., Smith, R.A. (1982): seasonal Kendall test.
- Rayner, N.A., et al. (2003). Global analyses of sea surface temperature, sea ice, and night marine air temperature since the late nineteenth century (HadISST1). *J. Geophys. Res.*, 108(D14), 4407. Dipole Mode Index time series from NOAA PSL: https://psl.noaa.gov/data/timeseries/month/DMI (non-NASA; verify citation on the PSL page).
- Huang, B., et al. (2017). Extended Reconstructed Sea Surface Temperature, Version 5 (ERSSTv5). *J. Climate*, 30, 8179-8205. Nino 3.4 anomalies from NOAA CPC (non-NASA; verify the file and citation on the CPC page).
- Runfola, D., et al. (2020). geoBoundaries: A global database of political administrative boundaries. *PLoS ONE*, 15(4), e0231866. Data: geoBoundaries gbOpen Indonesia ADM1, CC BY 4.0 (non-NASA; verify the license on the geoBoundaries page).

## 11. Author

Solo participant, NASA Space Apps Jakarta 2026.
