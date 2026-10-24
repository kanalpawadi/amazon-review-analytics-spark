# Web app (React) with explainable AI

A fast, static React site that shows every result of the project and **explains** each prediction.
No server is needed: the trained sentiment model runs in the visitor's browser, so the site can be
hosted **for free** on GitHub Pages, Netlify or Vercel.

| Page | Explainability (XAI) |
|---|---|
| Sentiment + XAI | Type a review: prediction, **words coloured by their influence**, exact "why A and not B" breakdown, **click a word to remove it** (what-if), strongest words per class |
| Fake reviews + XAI | Each flagged review: score bar vs threshold, **evidence with the review's own numbers**, signals that did *not* fire, reviewer group (KMeans) |
| Recommendations + XAI | Pick a user: history + top 10, each **"because you rated X (similarity 0.82)"** and popular / niche |
| Overview, Scalability, About | EDA charts, speed-up vs cores, pipeline, limitations, citation |

Built with Vite + React 18 + Recharts. Light and dark mode, works on phones.

---

## 1. Get the data (after the Colab notebooks)

1. Re-run `notebooks/04c_recommendation.ipynb` (adds the "because you rated" explanations).
2. Run `notebooks/06a_dashboard_export.ipynb` in Colab. In Google Drive open `amazon_reviews/`,
   right-click **`dashboard_data.zip` -> Download** (it goes to your Downloads folder - no need to unzip).
3. Convert it to the app's JSON files (run in `D:\PROJECTS\BIG_DATA_project`):

```
.venv\Scripts\python web\scripts\build_data.py
```

The script finds the newest `dashboard_data*.zip` in Downloads, extracts it to `dashboard/dashboard_data/`,
writes `web/public/data/*.json` and checks that the shrunken sentiment model still matches Spark.
If you downloaded a newer zip later, run it with `--zip C:\Users\Admin\Downloads\dashboard_data.zip`.

## 2. Run it on your laptop

```
cd web
npm install
npm run dev
```

Open http://localhost:5173.

## 3. Deploy for free

Build the site once:

```
cd web
npm run build
```

This creates `web/dist/`, a folder of plain files. Then pick **one** host:

- **Netlify (easiest, no account setup on GitHub needed):** sign in at app.netlify.com, choose
  *Add new site → Deploy manually* and drag the `web/dist` folder onto the page. You get a link
  like `amazon-review-analytics.netlify.app`.
- **GitHub Pages:** push the project to GitHub, then publish the `web/dist` folder
  (for example with the `gh-pages` branch). Links use `#/` routes, so no extra server settings are needed.
- **Vercel:** import the GitHub repository, set *Root directory* = `web`, build command `npm run build`,
  output `dist`.

Add the dataset citation (already on the About page) and keep the "for academic use" note when sharing.

## Files

| Path | What |
|---|---|
| `src/lib/sentiment.js` | the Spark model in JavaScript + the exact word attributions |
| `src/pages/*.jsx` | one file per page |
| `scripts/build_data.py` | CSV / model export -> `public/data/*.json` |
| `public/data/` | generated data (not edited by hand) |
