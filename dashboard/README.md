# Dashboard (Phase 6)

A Streamlit web app that shows all project results and lets you type a review to get its sentiment.
It runs on the laptop with plain Python - no Spark or Java needed.

| Page | Shows |
|---|---|
| Overview | dataset numbers, star ratings, categories, trends, top words |
| Sentiment | **live "type a review" prediction**, model comparison, confusion matrix, strongest words |
| Fake reviews | warning-sign counts, suspicion scores, rating impact, explorer of suspicious reviews |
| Recommendations | pick a user -> what they rated + their top 10, ALS vs baseline metrics |
| Scalability | run time vs data size and cores (after Phase 5) |

## 1. Get the data (once, and again after re-running any notebook)

1. In Colab run `notebooks/06a_dashboard_export.ipynb` (after `04c_recommendation.ipynb`).
2. In Google Drive, open `amazon_reviews/`, right-click **`dashboard_data.zip`** -> **Download**.
3. Extract it here so the folder is `D:\PROJECTS\BIG_DATA_project\dashboard\dashboard_data\`.

## 2. Start the dashboard

Open a terminal in `D:\PROJECTS\BIG_DATA_project` and run:

```
.venv\Scripts\python -m streamlit run dashboard\app.py
```

It opens in your browser at http://localhost:8501. Stop it with `Ctrl + C`.

If `.venv` is missing (new computer), create it first:

```
python -m venv .venv
.venv\Scripts\python -m pip install -r dashboard\requirements.txt
```

## Files

| File | What |
|---|---|
| `app.py` | the dashboard |
| `sentiment_model.py` | runs the Spark-trained sentiment model with numpy (same cleaning as Phase 2) |
| `requirements.txt` | Python packages |
| `dashboard_data/` | results exported from Colab (not included - download the zip) |

The Sentiment page has a **"Check: does this laptop version match Spark?"** box. It compares the laptop's
predictions with Spark's for 20 reviews; it should say **same model**.
