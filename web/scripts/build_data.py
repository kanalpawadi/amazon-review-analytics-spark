"""
Convert the exported results (dashboard/dashboard_data) into small JSON files for the React app.

    .venv\\Scripts\\python web\\scripts\\build_data.py
    .venv\\Scripts\\python web\\scripts\\build_data.py --src <other folder> --out web\\public\\data

The sentiment model is made smaller by dropping terms whose weights are tiny in all three classes.
The largest cut that keeps every check prediction within 0.01 of Spark's probabilities is used.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dashboard"))
from sentiment_model import SentimentModel  # noqa: E402  (same scorer as the Streamlit dashboard)

SIGNAL_TEXT = {
    "near_duplicate": "Almost the same text appears on other products",
    "text_rating_mismatch": "The star rating contradicts what the text says",
    "rating_deviation": "Rating is 3+ stars away from the product's average",
    "burst": "Part of a burst of extreme reviews within one week",
    "outlier_reviewer": "Reviewer behaves unlike every normal reviewer group",
    "one_sided_reviewer": "Reviewer gives only 5-star or only 1-star ratings",
    "short_generic": "Very short text with an extreme rating",
    "unverified": "Purchase not verified by Amazon (weak signal)",
}


def no_nan(obj):
    """Missing values (NaN) are not valid JSON - browsers refuse the whole file. Turn them into null."""
    if isinstance(obj, float) and obj != obj:
        return None
    if isinstance(obj, dict):
        return {k: no_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [no_nan(v) for v in obj]
    return obj


def read(src, rel):
    p = src / rel
    return pd.read_csv(p) if p.exists() else None


def records(df, cols=None, digits=4):
    if df is None:
        return None
    d = df[cols] if cols else df
    d = d.round(digits).replace({np.nan: None})
    return d.to_dict("records")


def cluster_name(p, max_reviews):
    """Plain-language name for a KMeans reviewer group from its average behaviour."""
    if p.get("share_duplicate", 0) >= 0.3:
        return "Copy-paste reviewers"
    if p.get("share_mismatch", 0) >= 0.15:
        return "Mixed-signal reviewers"
    if p.get("n_reviews", 0) >= max_reviews * 0.8 and p.get("n_reviews", 0) >= 8:
        return "Power reviewers"
    if p.get("avg_rating", 5) < 3:
        return "Harsh critics"
    if p.get("avg_rating", 0) >= 4.5:
        return "Enthusiastic buyers"
    return "Balanced reviewers"


def build_model(src, out):
    npz, check = src / "sentiment_model.npz", read(src, "sentiment_check.csv")
    if not npz.exists():
        return None
    full = SentimentModel(npz)
    data = np.load(npz)
    texts = [] if check is None else list(check.fillna("")[["title", "text"]].itertuples(index=False))
    spark_p = None if check is None else check[["p_negative", "p_neutral", "p_positive"]].to_numpy()
    reference = spark_p if spark_p is not None else np.array([list(full.predict(t, x)["probabilities"].values()) for t, x in texts])

    strength = np.abs(data["coef"]).max(axis=0)
    chosen, chosen_diff = 0.0, None
    for cut in [0.0, 0.005, 0.01, 0.02, 0.03, 0.05]:
        keep = strength >= cut
        m = SentimentModel.__new__(SentimentModel)
        m.terms = data["vocab"][keep].tolist()
        m.vocab = {t: i for i, t in enumerate(m.terms)}
        m.idf, m.coef, m.intercept = data["idf"][keep], data["coef"][:, keep], data["intercept"]
        m.stop_words = set(data["stop_words"].tolist())
        if len(texts):
            mine = np.array([list(m.predict(t, x)["probabilities"].values()) for t, x in texts])
            diff = float(np.abs(mine - reference).max())
        else:
            diff = 0.0
        if cut == 0.0 or diff < 0.01:          # the full model is always kept as the fallback
            chosen, chosen_diff, model = cut, diff, m
        if diff >= 0.01:
            break

    payload = {
        "classes": ["negative", "neutral", "positive"],
        "terms": model.terms,
        "idf": [round(float(v), 4) for v in model.idf],
        "coef": [[round(float(v), 4) for v in row] for row in model.coef],
        "intercept": [round(float(v), 4) for v in model.intercept],
        "stop_words": sorted(model.stop_words),
        "pruned_below": chosen,
        "terms_full": int(len(data["vocab"])),
        "max_prob_diff_vs_spark": None if chosen_diff is None else round(chosen_diff, 5),
    }
    (out / "model.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"model.json: {len(model.terms):,} of {len(data['vocab']):,} terms (cut {chosen}), "
          f"max diff vs Spark {chosen_diff}")
    return {"terms": len(model.terms), "terms_full": int(len(data["vocab"])), "max_diff": chosen_diff}


def extract_zip(zip_path, src):
    """Unzip dashboard_data.zip so that its files end up directly in src (handles the extra top folder)."""
    import shutil
    import zipfile
    if zip_path is None:
        found = sorted((Path.home() / "Downloads").glob("dashboard_data*.zip"), key=lambda p: p.stat().st_mtime)
        if not found:
            return
        zip_path = found[-1]
    print(f"extracting {zip_path} -> {src}")
    tmp = src.parent / "_unzip_tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmp)
    inner = tmp / "dashboard_data" if (tmp / "dashboard_data").is_dir() else tmp
    shutil.rmtree(src, ignore_errors=True)
    shutil.move(str(inner), str(src))
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "dashboard" / "dashboard_data"))
    ap.add_argument("--out", default=str(ROOT / "web" / "public" / "data"))
    ap.add_argument("--sample", default="1pct")
    ap.add_argument("--zip", help="dashboard_data.zip to extract first (default: newest one in Downloads)")
    a = ap.parse_args()
    src, out, S = Path(a.src), Path(a.out), a.sample
    if a.zip or not src.exists():
        extract_zip(Path(a.zip) if a.zip else None, src)
    if not src.exists() or not any(src.rglob("*.csv")):
        nested = src / "dashboard_data"
        hint = (f"\n  It looks unzipped one folder too deep - move the files from\n  {nested}\n  up into\n  {src}"
                if nested.exists() else
                "\n  1. Run notebooks/06a_dashboard_export.ipynb in Colab"
                "\n  2. Download amazon_reviews/dashboard_data.zip from Google Drive"
                f"\n  3. Extract it so that this folder exists: {src}")
        sys.exit(f"ERROR: no exported results found in {src}{hint}\nNothing was written.")
    out.mkdir(parents=True, exist_ok=True)
    write = lambda name, obj: (out / f"{name}.json").write_text(
        json.dumps(no_nan(obj), separators=(",", ":"), default=str, allow_nan=False), encoding="utf-8")

    # ---------------------------------------------------------------- overview / EDA
    ov = read(src, "eda/01_overview.csv")
    eda = {
        "overview": None if ov is None else records(ov)[0],
        "ratings": records(read(src, "eda/02_rating_distribution.csv")),
        "yearly": records(read(src, "eda/03_reviews_per_year.csv")),
        "categories": records(None if read(src, "eda/07_categories.csv") is None else read(src, "eda/07_categories.csv").head(12)),
        "verified": records(read(src, "eda/06_verified_summary.csv")),
        "top_words": {s: records(read(src, f"eda/12_top_words_{s}.csv")) for s in ["positive", "negative"]},
    }
    write("eda", eda)

    # ---------------------------------------------------------------- sentiment
    cm = read(src, f"sentiment/confusion_matrix_best_{S}.csv")
    sentiment = {
        "comparison": records(read(src, f"sentiment/model_comparison_{S}.csv")),
        "confusion": None if cm is None else cm.set_index(cm.columns[0]).astype(int).to_dict("index"),
        "top_terms": {c: records(read(src, f"sentiment/top_terms_{c}_{S}.csv")) for c in ["negative", "neutral", "positive"]},
        "check": records(read(src, "sentiment_check.csv")),
    }
    sentiment["model"] = build_model(src, out)
    write("sentiment", sentiment)

    # ---------------------------------------------------------------- fake reviews
    prev = read(src, f"fake_reviews/signal_prevalence_{S}.csv")
    prof = read(src, f"fake_reviews/kmeans_cluster_profiles_{S}.csv")
    names = {}
    if prof is not None:
        mx = prof["n_reviews"].max() if "n_reviews" in prof else 0
        prof["name"] = [cluster_name(r, mx) for r in prof.to_dict("records")]
        names = dict(zip(prof["cluster"], prof["name"]))
    ex = read(src, "suspicious_examples.csv")
    if ex is not None:
        ex = ex.head(300).copy()
        ex["cluster_name"] = ex["cluster"].map(names) if "cluster" in ex else None
    impact = read(src, f"fake_reviews/product_rating_impact_{S}.csv")
    fake = {
        "weights": None if prev is None else dict(zip(prev["signal"], prev["points"])),
        "signal_text": SIGNAL_TEXT,
        "threshold": 3.0,
        "prevalence": records(prev),
        "distribution": records(read(src, f"fake_reviews/score_distribution_{S}.csv")),
        "profiles": records(prof),
        "impact_summary": None if impact is None else {
            "products": int(len(impact)), "changed": int((impact["change"].abs() >= 0.1).sum()),
            "drop": int((impact["change"] <= -0.1).sum()), "rise": int((impact["change"] >= 0.1).sum())},
        "impact_top": records(None if impact is None else
                              impact.reindex(impact["change"].abs().sort_values(ascending=False).index).head(12)),
        "examples": records(ex, digits=3),
    }
    write("fake", fake)

    # ---------------------------------------------------------------- recommendations
    recs, hist, expl = read(src, "recommendations.csv"), read(src, "user_history.csv"), read(src, "rec_explanations.csv")
    users = []
    if recs is not None:
        pop = None if expl is None else expl.groupby("rec_asin")["rec_popularity"].max()
        p90 = None if pop is None or pop.empty else float(pop.quantile(0.9))
        for uid in list(recs["user_id"].drop_duplicates())[:300]:
            r = recs[recs["user_id"] == uid].sort_values("rank")
            items = []
            for row in r.to_dict("records"):
                because = []
                if expl is not None:
                    e = expl[(expl["user_id"] == uid) & (expl["rank"] == row["rank"])].sort_values("similarity", ascending=False)
                    because = [{"title": b.get("because_title") or b["because_asin"], "similarity": float(b["similarity"])}
                               for b in e.head(2).to_dict("records")]
                    popn = int(e["rec_popularity"].iloc[0]) if len(e) and not pd.isna(e["rec_popularity"].iloc[0]) else None
                else:
                    popn = None
                items.append({"rank": int(row["rank"]), "title": row.get("title") or row["parent_asin"],
                              "category": row.get("main_category"), "asin": row["parent_asin"],
                              "because": because, "popularity": popn,
                              "popular": None if popn is None or p90 is None else popn >= p90})
            h = [] if hist is None else records(hist[hist["user_id"] == uid][["date", "rating", "title", "main_category"]])
            users.append({"user_id": uid, "history": h, "recs": items})
    stats = read(src, "recommendation/data_stats.csv")
    write("recs", {
        "stats": None if stats is None else records(stats)[0],
        "rmse": records(read(src, "recommendation/rmse_comparison.csv")),
        "ranking": records(read(src, "recommendation/ranking_comparison.csv"), digits=5),
        "users": users,
    })

    # ---------------------------------------------------------------- scalability
    write("scalability", {"runs": records(read(src, "scalability/scalability_runs.csv"))})

    write("meta", {"built": date.today().isoformat(), "sample": S,
                   "available": {k: (out / f"{k}.json").exists() for k in ["eda", "sentiment", "fake", "recs", "scalability", "model"]}})
    for f in sorted(out.glob("*.json")):
        print(f"{f.name:<20} {f.stat().st_size / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
