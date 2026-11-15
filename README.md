TerraWatch AI

An Earth System Trend Detective for South Sumatra, Indonesia

TerraWatch AI is an environmental data science project designed to investigate long-term changes, environmental variability, and potential relationships between rainfall, soil moisture, and fire activity across South Sumatra, Indonesia.

By combining satellite-derived Earth observation datasets, statistical trend analysis, and machine learning, the project explores four central questions:

- What is changing?
- Where is it changing?
- By how much?
- Are the observed changes statistically significant?

Rather than relying solely on conventional trend analysis, TerraWatch AI also investigates interannual variability, extreme dry spells, and environmental patterns that may be relevant to regional early-warning systems.

---

Project Overview

Attribute| Description
Project| TerraWatch AI
Domain| Environmental Data Science
Study Area| South Sumatra, Indonesia
Temporal Coverage| 2000–2024 (rainfall analysis)
Data Sources| NASA GPM IMERG, MERRA-2, NASA FIRMS
Methods| Statistical Analysis, Machine Learning, Explainable AI
Status| Research Prototype

Data Sources

TerraWatch AI integrates three major Earth observation datasets:

1. NASA GPM IMERG — Precipitation

Satellite-based precipitation estimates used to investigate rainfall patterns, long-term trends, anomalies, and extreme dry periods.

2. NASA MERRA-2 — Soil Moisture

A global atmospheric reanalysis dataset used to investigate soil moisture conditions and their environmental variability.

3. NASA FIRMS — Active Fire Detections

MODIS active fire observations used to examine fire activity and its potential relationships with rainfall and dry conditions.

For detailed dataset information and acquisition notes, see ""data/README.md"" (data/README.md).

Official data portals:

- "NASA GPM" (https://gpm.nasa.gov/data)
- "NASA GES DISC – MERRA-2" (https://disc.gsfc.nasa.gov/)
- "NASA FIRMS" (https://firms.modaps.eosdis.nasa.gov/)

Methodology

The analytical workflow combines several complementary approaches.

1. Statistical Trend Analysis

- Mann-Kendall trend test.
- Sen's slope estimator.
- Rainfall anomaly analysis.
- Interannual variability assessment.
- Extreme dry-spell analysis.

2. Environmental Relationship Analysis

- Rainfall and soil moisture variability.
- Rainfall and fire activity relationships.
- Temporal and spatial pattern exploration.

3. Machine Learning

- Predictive modeling and model evaluation.
- Walk-forward validation.
- Leave-One-Year-Out (LOYO) evaluation.
- Performance and generalization assessment.

4. Explainable AI

- SHAP feature importance.
- Model interpretation.
- Identification of influential environmental variables.

Key Research Findings

The rainfall analysis indicates that long-term precipitation trends are not statistically significant under the applied Mann-Kendall test, despite substantial year-to-year variability.

The analysis also identifies extreme dry periods, including a documented dry spell reaching 35 consecutive days.

These findings highlight an important distinction: the absence of a statistically significant long-term trend does not mean that environmental variability or extreme conditions are absent.

Further analysis investigates soil moisture conditions, fire activity, and the potential contribution of environmental variables to observed patterns.

Note: Statistical associations and predictive relationships should not automatically be interpreted as causal relationships.

---

Visualization Gallery

The following figures summarize eight major analytical outputs of TerraWatch AI.

1. Rainfall Trend Analysis

"Rainfall Trend" (results/figures/fig_trend.png)

2. Rainfall Anomaly Analysis

"Rainfall Anomaly" (results/figures/fig_anomaly.png)

3. Extreme Dry-Spell Analysis

"Dry Spell Analysis" (results/figures/fig_dryspell.png)

4. Rainfall and Fire Relationship

"Fire Relationship" (results/figures/fig_fire_link.png)

5. Machine Learning Results

"Machine Learning" (results/figures/fig_ml.png)

6. Leave-One-Year-Out Evaluation

"LOYO Evaluation" (results/figures/fig_loyo.png)

7. SHAP Feature Importance

"SHAP Summary" (results/figures/fig_shap_summary.png)

8. Provincial Fire Density

"Fire Density" (results/figures/fig_fire_density_province.png)

---

Repository Structure

TerraWatch-AI/
│
├── notebooks/
│   └── *.ipynb
│
├── data/
│   └── README.md
│
├── results/
│   └── figures/
│       ├── fig_trend.png
│       ├── fig_anomaly.png
│       ├── fig_dryspell.png
│       ├── fig_fire_link.png
│       ├── fig_ml.png
│       ├── fig_loyo.png
│       ├── fig_shap_summary.png
│       └── fig_fire_density_province.png
│
├── .gitignore
├── requirements.txt
├── README.md
└── LICENSE

Reproducibility

The analysis is documented in the Jupyter notebooks available in the ""notebooks/"" (notebooks/) directory.

To reproduce the analysis:

1. Clone the repository

git clone https://github.com/HndrxCodes/TerraWatch-AI.git
cd TerraWatch-AI

2. Install dependencies

pip install -r requirements.txt

3. Obtain the required datasets

Follow the instructions in ""data/README.md"" (data/README.md) and obtain the original datasets from their official providers.

4. Run the notebooks

Open the notebooks using Jupyter Notebook, JupyterLab, or Google Colab. If using Kaggle, attach the required datasets and adjust input paths to the Kaggle environment.

Reproduction requires compatible dataset versions, file paths, preprocessing steps, and execution environments.

Limitations

- Satellite-derived observations have spatial and temporal resolution limitations.
- Reanalysis products are estimates and may not perfectly represent local ground conditions.
- Active fire detections do not directly represent total burned area.
- Statistical relationships do not establish causality.
- Machine learning performance must be interpreted in the context of the validation strategy and available observations.

Project Vision

TerraWatch AI aims to demonstrate how open Earth observation data, statistical reasoning, and explainable machine learning can be combined to better understand regional environmental dynamics.

The long-term vision is to develop a more comprehensive environmental monitoring and early-warning framework for South Sumatra.

---

Author

HndrxCodes

GitHub: "@HndrxCodes" (https://github.com/HndrxCodes)

---

TerraWatch AI — Understanding environmental changes through data, statistics, and artificial intelligence.
