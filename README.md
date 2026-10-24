# Amazon Review Analytics with Apache Spark and Explainable AI

**Live demo: https://kanalpawadi.github.io/amazon-review-analytics-spark/**

Sentiment analysis, fake review detection and product recommendation on **Amazon Reviews 2023 (Electronics, 43.9 M ratings)**
with **Apache Spark (PySpark, Spark SQL, MLlib), Hadoop HDFS and Hive**, and an explainable React web app.

Final-year project · Department of Artificial Intelligence and Data Science · DKTE, Shivaji University · 2026-27 ·
Guide: Prof. P. N. Koshti.

## Results (development sample)

| Module | Method | Result |
| --- | --- | --- |
| Data | 1% user sample, Spark cleaning, Parquet by year | 431,302 clean reviews, 182,702 users, 165,578 products |
| Sentiment | TF-IDF on words + word pairs, class-weighted Logistic Regression | **macro F1 0.705** (always-positive baseline 0.287), accuracy 0.871 |
| Fake reviews | 8 signals (MinHash LSH copies, star-text mismatch, rating deviation, bursts, ...) + KMeans | 2,022 flagged (0.47%); KMeans found a 287-reviewer copy-paste group |
| Recommendation | explicit + implicit ALS on the official 5-core split (5% of users) | implicit ALS HitRate@10 0.0063, most-popular baseline 0.014 |
| Scalability | 4 workloads, 25-100% of the sample, 1 vs 2 cores (Colab) | speed-up up to 1.57x |

Every prediction is explained: exact word contributions for sentiment (the model is linear), a point-by-point
breakdown for each flagged review, and "because you rated X" for each recommendation.

## Repository layout

| Folder | What |
| --- | --- |
| `notebooks/` | Google Colab notebooks, one per phase: sample, cleaning, EDA, sentiment, fake reviews, recommendation, scalability, export |
| `scripts/make_sample.py` | builds the 1% user sample by streaming the official files |
| `dataproc/` | full-scale pipeline for a Google Dataproc cluster (HDFS, Hive, Spark): ingest, clean, modules, scalability |
| `web/` | React + Vite web app with the explanations (static, free to host); `web/public/data` holds the exported results |
| `dashboard/` | Streamlit dashboard (backup UI) and the numpy version of the sentiment model |
| `scripts/wsl/` | optional local Hadoop/Spark setup for Ubuntu on WSL2 |

## Run the web app

```
cd web
npm install
npm run dev
```

Open http://localhost:5173. The public version is served by GitHub Pages from the `gh-pages` branch
(the contents of `web/dist` after `npm run build`).

## Rebuild the results

1. Run the notebooks in `notebooks/` in order on Google Colab (data is kept in Google Drive).
2. Run `06a_dashboard_export.ipynb` and download `dashboard_data.zip`.
3. `python web/scripts/build_data.py` (finds the zip in Downloads and writes `web/public/data`).

## Data and citation

Y. Hou, J. Li, Z. He, A. Yan, X. Chen and J. McAuley, "Bridging Language and Items for Retrieval and Recommendation,"
arXiv:2403.03952, 2024 (Amazon Reviews 2023, McAuley Lab, UC San Diego). Used for academic, non-commercial purposes.
