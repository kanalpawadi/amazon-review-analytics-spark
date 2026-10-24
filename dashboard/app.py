"""
Amazon Review Analytics - dashboard (Phase 6).

Start:  streamlit run dashboard/app.py
Data:   dashboard/dashboard_data/  (unzipped from dashboard_data.zip made by 06a_dashboard_export.ipynb)
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sentiment_model import SentimentModel

DATA = Path(os.environ.get("DASHBOARD_DATA", Path(__file__).parent / "dashboard_data"))
SAMPLE = "1pct"

BLUE, ORANGE, AQUA, RED, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#9a9893"
SENT_COLORS = {"positive": BLUE, "neutral": GREY, "negative": RED}
CLASSES = ["negative", "neutral", "positive"]

st.set_page_config(page_title="Amazon Review Analytics", page_icon="📦", layout="wide")
CHART = {"displayModeBar": False}       # hide the Plotly toolbar (it covers chart titles)


# ------------------------------------------------------------------ helpers
@st.cache_data
def load(rel):
    path = DATA / rel
    return pd.read_csv(path) if path.exists() else None


@st.cache_resource
def load_model():
    path = DATA / "sentiment_model.npz"
    return SentimentModel(path) if path.exists() else None


def missing(what):
    st.info(f"No data yet for **{what}**. Run the matching notebook, then re-export with "
            "`06a_dashboard_export.ipynb` and unzip it into `dashboard/dashboard_data/`.")


def style(fig, height=340):
    fig.update_layout(template="simple_white", height=height, margin=dict(l=10, r=10, t=40, b=10),
                      font=dict(size=13), title_x=0, legend_title_text="",
                      hoverlabel=dict(bgcolor="white"))
    fig.update_yaxes(showgrid=True, gridcolor="#e6e5e0")
    return fig


def pct(x):
    return f"{x:.1f}%"


# ------------------------------------------------------------------ sidebar
st.sidebar.title("📦 Amazon Review Analytics")
st.sidebar.caption("Sentiment analysis, fake review detection and product recommendation "
                   "on Amazon Reviews 2023 (Electronics) with Apache Spark")
page = st.sidebar.radio("Section", ["Overview", "Sentiment", "Fake reviews", "Recommendations", "Scalability"])
st.sidebar.divider()
st.sidebar.caption("DKTE · Dept. of AI & Data Science · 2026-27")

if not DATA.exists():
    st.error(f"Data folder not found: `{DATA}`. Download `dashboard_data.zip` from Google Drive "
             "and extract it into the `dashboard` folder (see dashboard/README.md).")
    st.stop()


# ------------------------------------------------------------------ overview
if page == "Overview":
    st.title("Overview of the data")
    ov = load("eda/01_overview.csv")
    if ov is None:
        missing("the overview (03_eda.ipynb)")
    else:
        o = ov.iloc[0]
        c = st.columns(5)
        c[0].metric("Reviews (1% user sample)", f"{int(o['reviews']):,}")
        c[1].metric("Users", f"{int(o['users']):,}")
        c[2].metric("Products", f"{int(o['products']):,}")
        c[3].metric("Average rating", f"{o['avg_rating']:.2f} ★")
        c[4].metric("Verified purchases", pct(o["verified_pct"]))
        st.caption(f"Reviews from {o['first_review']} to {o['last_review']}. "
                   "Full category: 43.9 million ratings.")

    left, right = st.columns(2)
    ratings = load("eda/02_rating_distribution.csv")
    if ratings is not None:
        ratings["stars"] = ratings["rating"].astype(int).astype(str) + " ★"
        ratings["sentiment"] = ratings["rating"].map(lambda r: "positive" if r >= 4 else ("neutral" if r == 3 else "negative"))
        fig = px.bar(ratings, x="stars", y="pct", color="sentiment", color_discrete_map=SENT_COLORS,
                     text=ratings["pct"].map(pct), title="Star ratings (classes are imbalanced)",
                     labels={"pct": "share of reviews (%)", "stars": ""})
        fig.update_traces(textposition="outside", hovertemplate="%{x}: %{y:.1f}%<extra></extra>")
        left.plotly_chart(style(fig), use_container_width=True, config=CHART)

    cats = load("eda/07_categories.csv")
    if cats is not None:
        top = cats.head(12).iloc[::-1]
        fig = px.bar(top, x="reviews", y="main_category", orientation="h", title="Top categories by reviews",
                     hover_data={"avg_rating": ":.2f", "products": ":,"}, labels={"main_category": ""})
        fig.update_traces(marker_color=BLUE)
        right.plotly_chart(style(fig), use_container_width=True, config=CHART)

    yearly = load("eda/03_reviews_per_year.csv")
    if yearly is not None:
        left, right = st.columns(2)
        fig = px.bar(yearly, x="year", y="reviews", title="Reviews per year (2023 = Jan-Sep)")
        fig.update_traces(marker_color=BLUE, hovertemplate="%{x}: %{y:,} reviews<extra></extra>")
        left.plotly_chart(style(fig), use_container_width=True, config=CHART)
        big = yearly[yearly["reviews"] >= 100]
        fig = px.line(big, x="year", y="avg_rating", markers=True, title="Average rating per year (100+ reviews)",
                      labels={"avg_rating": "average stars"})
        fig.update_traces(line_color=BLUE, hovertemplate="%{x}: %{y:.2f} ★<extra></extra>")
        right.plotly_chart(style(fig), use_container_width=True, config=CHART)

    pos, neg = load("eda/12_top_words_positive.csv"), load("eda/12_top_words_negative.csv")
    if pos is not None and neg is not None:
        left, right = st.columns(2)
        for col, df, s in [(left, pos, "positive"), (right, neg, "negative")]:
            d = df.head(15).iloc[::-1]
            fig = px.bar(d, x="count", y="word", orientation="h", title=f"Top words in {s} reviews",
                         labels={"word": ""})
            fig.update_traces(marker_color=SENT_COLORS[s])
            col.plotly_chart(style(fig, 420), use_container_width=True, config=CHART)


# ------------------------------------------------------------------ sentiment
elif page == "Sentiment":
    st.title("Sentiment analysis")
    model = load_model()

    st.subheader("Try it: type a review")
    examples = {
        "Positive": ("Love it", "Works great, battery lasts all day and the sound is amazing."),
        "Negative": ("Waste of money", "Stopped working after two days. Do not buy, returning it."),
        "Mixed": ("It's okay", "Sound is good but the battery is not great and it feels cheap."),
    }
    pick = st.radio("Example", list(examples), horizontal=True, label_visibility="collapsed")
    title = st.text_input("Review title", examples[pick][0])
    text = st.text_area("Review text", examples[pick][1], height=90)
    if model is None:
        missing("the sentiment model (06a_dashboard_export.ipynb)")
    elif title or text:
        res = model.predict(title, text)
        probs = res["probabilities"]
        left, right = st.columns([2, 3])
        left.markdown(f"### Prediction: **{res['label'].upper()}**")
        fig = go.Figure(go.Bar(x=[probs[c] for c in CLASSES], y=CLASSES, orientation="h",
                               marker_color=[SENT_COLORS[c] for c in CLASSES],
                               text=[f"{probs[c]:.0%}" for c in CLASSES], textposition="outside",
                               hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
        fig.update_xaxes(range=[0, 1.1], tickformat=".0%")
        left.plotly_chart(style(fig, 220), use_container_width=True, config=CHART)
        terms = pd.DataFrame(res["top_terms"], columns=["word / word pair", "push towards prediction"])
        terms = terms[terms["push towards prediction"].abs() > 1e-6]
        right.markdown("**Words that pushed the model most**")
        right.dataframe(terms.round(3), hide_index=True, use_container_width=True)

    st.divider()
    comp = load(f"sentiment/model_comparison_{SAMPLE}.csv")
    if comp is None:
        missing("the model comparison (04a_sentiment.ipynb)")
    else:
        st.subheader("Model comparison (test set)")
        long = comp.melt(id_vars="model", value_vars=["accuracy", "macro_f1"], var_name="metric")
        long["metric"] = long["metric"].map({"accuracy": "Accuracy", "macro_f1": "Macro F1 (fair for imbalance)"})
        fig = px.bar(long, x="value", y="model", color="metric", barmode="group", orientation="h",
                     color_discrete_sequence=[GREY, BLUE], labels={"model": "", "value": ""},
                     title="The baseline has high accuracy but very low macro F1")
        fig.update_traces(hovertemplate="%{y}<br>%{x:.3f}<extra></extra>")
        fig.update_xaxes(range=[0, 1])
        st.plotly_chart(style(fig, 380), use_container_width=True, config=CHART)
        cols = ["model", "accuracy", "macro_f1", "f1_negative", "f1_neutral", "f1_positive", "train_seconds"]
        st.dataframe(comp[cols].round(3), hide_index=True, use_container_width=True)

    left, right = st.columns(2)
    cm = load(f"sentiment/confusion_matrix_best_{SAMPLE}.csv")
    if cm is not None:
        cm = cm.set_index(cm.columns[0]).loc[CLASSES, CLASSES]
        cm_pct = cm.div(cm.sum(axis=1), axis=0) * 100
        fig = px.imshow(cm_pct, text_auto=".1f", color_continuous_scale="Blues", zmin=0, zmax=100,
                        labels=dict(x="predicted", y="true", color="% of true class"),
                        title="Confusion matrix of the best model (row %)")
        left.plotly_chart(style(fig, 380), use_container_width=True, config=CHART)
    terms = {c: load(f"sentiment/top_terms_{c}_{SAMPLE}.csv") for c in CLASSES}
    if all(t is not None for t in terms.values()):
        c = right.selectbox("Strongest words for class", CLASSES, index=0)
        d = terms[c].iloc[::-1]
        fig = px.bar(d, x="weight", y="term", orientation="h", labels={"term": ""},
                     title=f"Words the model links to '{c}'")
        fig.update_traces(marker_color=SENT_COLORS[c])
        right.plotly_chart(style(fig, 330), use_container_width=True, config=CHART)

    check = load("sentiment_check.csv")
    if check is not None and model is not None:
        with st.expander("Check: does this laptop version match Spark?"):
            mine = np.array([[model.predict(r.title, r.text)["probabilities"][c] for c in CLASSES]
                             for r in check.fillna("").itertuples()])
            spark = check[["p_negative", "p_neutral", "p_positive"]].to_numpy()
            diff = np.abs(mine - spark).max()
            st.write(f"Largest probability difference over {len(check)} reviews: **{diff:.4f}** "
                     f"({'✅ same model' if diff < 0.01 else '⚠️ differs - check the export'})")


# ------------------------------------------------------------------ fake reviews
elif page == "Fake reviews":
    st.title("Fake review detection")
    st.caption("Flags are **suspicious**, not proven fake: there is no labelled ground truth.")
    prev = load(f"fake_reviews/signal_prevalence_{SAMPLE}.csv")
    dist = load(f"fake_reviews/score_distribution_{SAMPLE}.csv")
    if prev is None:
        missing("fake review results (04b_fake_reviews.ipynb)")
        st.stop()

    if dist is not None:
        flagged = dist[dist["score_bucket"].isin(["3-4", "4.5+"])]
        c = st.columns(3)
        c[0].metric("Suspicious reviews", f"{int(flagged['count'].sum()):,}")
        c[1].metric("Share of all reviews", pct(flagged["pct"].sum()))
        c[2].metric("Reviews checked", f"{int(dist['count'].sum()):,}")

    left, right = st.columns(2)
    d = prev.iloc[::-1]
    fig = px.bar(d, x="pct_of_all", y="signal", orientation="h", title="How often each warning sign appears",
                 hover_data={"reviews": ":,", "points": True, "pct_of_flagged": ":.1f"},
                 labels={"pct_of_all": "% of all reviews", "signal": ""})
    fig.update_traces(marker_color=BLUE)
    left.plotly_chart(style(fig, 380), use_container_width=True, config=CHART)
    if dist is not None:
        order = ["0", "0.5-1", "1.5-2.5", "3-4", "4.5+"]
        d = dist.set_index("score_bucket").reindex(order).reset_index()
        d["flagged"] = d["score_bucket"].isin(["3-4", "4.5+"]).map({True: "suspicious", False: "not flagged"})
        fig = px.bar(d, x="score_bucket", y="pct", color="flagged", title="Suspicion scores (flag at 3+)",
                     color_discrete_map={"suspicious": RED, "not flagged": GREY},
                     labels={"score_bucket": "suspicion score", "pct": "% of reviews"})
        right.plotly_chart(style(fig, 380), use_container_width=True, config=CHART)

    impact = load(f"fake_reviews/product_rating_impact_{SAMPLE}.csv")
    if impact is not None:
        st.subheader("How product ratings change without suspicious reviews")
        top = impact.reindex(impact["change"].abs().sort_values(ascending=False).index).head(12).iloc[::-1]
        top["name"] = top["product_title"].fillna(top["parent_asin"]).str.slice(0, 55)
        fig = go.Figure()
        for _, r in top.iterrows():
            fig.add_trace(go.Scatter(x=[r["avg_all"], r["avg_without_flagged"]], y=[r["name"]] * 2, mode="lines",
                                     line=dict(color="#e6e5e0", width=4), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=top["avg_all"], y=top["name"], mode="markers", name="all reviews",
                                 marker=dict(color=GREY, size=11), hovertemplate="all: %{x:.2f} ★<extra></extra>"))
        fig.add_trace(go.Scatter(x=top["avg_without_flagged"], y=top["name"], mode="markers",
                                 name="suspicious removed", marker=dict(color=BLUE, size=11),
                                 hovertemplate="without suspicious: %{x:.2f} ★<extra></extra>"))
        fig.update_xaxes(title="average stars")
        st.plotly_chart(style(fig, 460), use_container_width=True, config=CHART)
        moved = impact[impact["change"].abs() >= 0.1]
        st.caption(f"{len(moved):,} of {len(impact):,} products (10+ reviews) change by 0.1+ stars: "
                   f"{(impact['change'] <= -0.1).sum()} drop, {(impact['change'] >= 0.1).sum()} rise.")

    prof = load(f"fake_reviews/kmeans_cluster_profiles_{SAMPLE}.csv")
    if prof is not None:
        with st.expander("Reviewer groups found by KMeans"):
            st.dataframe(prof, hide_index=True, use_container_width=True)

    ex = load("suspicious_examples.csv")
    if ex is not None:
        st.subheader("Explore suspicious reviews")
        signals = [s for s in prev["signal"] if s in ex.columns]
        pick = st.multiselect("Must have these signals", signals, default=[])
        view = ex.copy()
        for s in pick:
            view = view[view[s]]
        st.write(f"{len(view):,} reviews")
        st.dataframe(view[["suspicion_score", "rating", "product_title", "title", "text", *signals]],
                     hide_index=True, use_container_width=True, height=380)


# ------------------------------------------------------------------ recommendations
elif page == "Recommendations":
    st.title("Product recommendation (ALS)")
    stats = load("recommendation/data_stats.csv")
    if stats is not None:
        s = stats.iloc[0]
        c = st.columns(4)
        c[0].metric("Ratings used", f"{int(s['ratings']):,}")
        c[1].metric("Users", f"{int(s['users']):,}")
        c[2].metric("Products", f"{int(s['products']):,}")
        c[3].metric("Ratings per user", f"{s['ratings_per_user']:.1f}")
        st.caption(f"Official 5-core Electronics split (leave-last-out), {s['user_fraction']:.0%} of users.")

    rec_users = load("recommendations.csv")
    hist = load("user_history.csv")
    if rec_users is None:
        missing("recommendations (04c_recommendation.ipynb)")
    else:
        st.subheader("Recommendations for a user")
        users = sorted(rec_users["user_id"].unique())
        user = st.selectbox("User", users, index=0)
        left, right = st.columns(2)
        if hist is not None:
            h = hist[hist["user_id"] == user][["date", "rating", "title", "main_category"]]
            left.markdown(f"**What they rated before** ({len(h)} products)")
            left.dataframe(h, hide_index=True, use_container_width=True, height=390)
        r = rec_users[rec_users["user_id"] == user].sort_values("rank")
        cols = [c for c in ["rank", "title", "main_category", "parent_asin"] if c in r.columns]
        right.markdown("**Top 10 recommended (implicit ALS)**")
        right.dataframe(r[cols], hide_index=True, use_container_width=True, height=390)

    st.divider()
    left, right = st.columns(2)
    ranking = load("recommendation/ranking_comparison.csv")
    if ranking is not None:
        hit = [c for c in ranking.columns if c.startswith("hit_rate")][0]
        ndcg = [c for c in ranking.columns if c.startswith("ndcg")][0]
        long = ranking.melt(id_vars="model", value_vars=[hit, ndcg], var_name="metric")
        fig = px.bar(long, x="model", y="value", color="metric", barmode="group",
                     color_discrete_sequence=[BLUE, AQUA], title="Top-10 quality on test users",
                     labels={"model": "", "value": ""})
        left.plotly_chart(style(fig, 360), use_container_width=True, config=CHART)
        left.dataframe(ranking.round(4), hide_index=True, use_container_width=True)
    rmse = load("recommendation/rmse_comparison.csv")
    if rmse is not None:
        fig = px.bar(rmse.iloc[::-1], x="test_rmse", y="model", orientation="h",
                     title="Rating prediction error (RMSE, lower is better)", labels={"model": "", "test_rmse": "RMSE"})
        fig.update_traces(marker_color=[ORANGE if "ALS" in m else GREY for m in rmse["model"].iloc[::-1]])
        right.plotly_chart(style(fig, 300), use_container_width=True, config=CHART)


# ------------------------------------------------------------------ scalability
elif page == "Scalability":
    st.title("Scalability")
    runs = load("scalability/scalability_runs.csv")
    if runs is None:
        st.info("Scalability tests run in **Phase 5** (Hadoop + Spark on WSL2). Their results will appear "
                "here as `dashboard_data/scalability/scalability_runs.csv` with columns "
                "`data_fraction, cores, step, seconds`.")
    else:
        step = st.selectbox("Pipeline step", sorted(runs["step"].unique()))
        d = runs[runs["step"] == step].copy()
        d["cores"] = d["cores"].astype(str) + " cores"
        fig = px.line(d.sort_values("data_fraction"), x="data_fraction", y="seconds", color="cores", markers=True,
                      title=f"Run time vs data size - {step}",
                      labels={"data_fraction": "share of data", "seconds": "seconds"},
                      color_discrete_sequence=[BLUE, ORANGE, AQUA])
        fig.update_xaxes(tickformat=".0%")
        st.plotly_chart(style(fig, 400), use_container_width=True, config=CHART)
        base = runs[runs["cores"] == runs["cores"].min()].set_index(["step", "data_fraction"])["seconds"]
        sp = runs.join(base.rename("base"), on=["step", "data_fraction"])
        sp["speed_up"] = (sp["base"] / sp["seconds"]).round(2)
        st.dataframe(sp[sp["step"] == step][["data_fraction", "cores", "seconds", "speed_up"]],
                     hide_index=True, use_container_width=True)
