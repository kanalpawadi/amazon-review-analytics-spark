"""
Phase 5 - fake review detection on ALL reviews (same signals and points as notebooks/04b_fake_reviews.ipynb).

Needs amazon.reviews_clean, amazon.products_clean and amazon.sentiment_scores.
Writes amazon.fake_scores (HDFS + bucket) and <bucket>/results/full/fake_*.csv, fake_report.json.
"""
import argparse

import numpy as np
import pandas as pd
from pyspark import StorageLevel
from pyspark.ml import Pipeline
from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import HashingTF, MinHashLSH, StandardScaler, VectorAssembler
from pyspark.sql import SparkSession, Window, functions as F

from common import Steps, save_csv, save_json, save_table

parser = argparse.ArgumentParser()
parser.add_argument("--bucket", required=True)
parser.add_argument("--lsh", choices=["on", "off"], default="on", help="near-duplicate search (slowest part)")
parser.add_argument("--lsh-min-words", type=int, default=20)
parser.add_argument("--k", type=int, default=6, help="KMeans clusters (6 was chosen by silhouette in Colab)")
parser.add_argument("--min-product-reviews", type=int, default=50, help="products used for the rating-impact table")
args = parser.parse_args()
OUT, SEED, DAY = f"{args.bucket}/results/full", 42, 86400
WEIGHTS = {"near_duplicate": 3.0, "text_rating_mismatch": 2.0, "rating_deviation": 1.5, "burst": 1.5,
           "outlier_reviewer": 1.5, "one_sided_reviewer": 1.0, "short_generic": 1.0, "unverified": 0.5}
THRESHOLD = 3.0

spark = SparkSession.builder.appName("fake-reviews-full").enableHiveSupport().getOrCreate()
spark.sparkContext.setLogLevel("WARN")
steps = Steps()
report = {"lsh": args.lsh}

reviews = spark.table("amazon.reviews_clean")
base = (reviews
        .select("review_id", "user_id", "parent_asin", "rating", "word_count", "verified_purchase",
                "timestamp", "review_date", "tokens", F.sha2("text_clean", 256).alias("text_id"))
        .join(spark.table("amazon.products_clean").select("parent_asin", "average_rating"), "parent_asin", "left")
        .join(spark.table("amazon.sentiment_scores").select("review_id", "p_negative", "p_positive"), "review_id", "left"))

# ------------------------------------------------------------------ 1. copied text
with steps("exact copies on 2+ products"):
    exact = (base.filter(F.col("word_count") >= 5).groupBy("text_id")
             .agg(F.countDistinct("parent_asin").alias("products")).filter(F.col("products") >= 2)
             .select("text_id").persist(StorageLevel.MEMORY_AND_DISK))
    report["exact_copied_texts"] = exact.count()

dup_ids = exact
if args.lsh == "on":
    with steps(f"near-duplicates: MinHash + LSH banding ({args.lsh_min_words}+ words)"):
        BANDS, ROWS, MAX_BUCKET = 4, 3, 200
        texts = (base.filter(F.col("word_count") >= args.lsh_min_words).groupBy("text_id")
                 .agg(F.first("tokens").alias("tokens"), F.collect_set("parent_asin").alias("asins"))
                 .withColumn("uniq", F.array_distinct("tokens")))
        vecs = (HashingTF(inputCol="uniq", outputCol="vec", numFeatures=1 << 18, binary=True)
                .transform(texts).select("text_id", "asins", "uniq", "vec").persist(StorageLevel.MEMORY_AND_DISK))
        report["lsh_texts"] = vecs.count()
        mh = MinHashLSH(inputCol="vec", outputCol="hashes", numHashTables=BANDS * ROWS, seed=SEED).fit(vecs)
        flat = F.udf(lambda hs: [int(h[0]) for h in hs], "array<bigint>")
        keys = F.array(*[F.concat_ws("_", F.lit(b), *[F.col("h")[b * ROWS + r].cast("string") for r in range(ROWS)])
                         for b in range(BANDS)])
        buckets = (mh.transform(vecs).withColumn("h", flat("hashes"))
                   .select("text_id", F.explode(keys).alias("band"))
                   .withColumn("n", F.count("*").over(Window.partitionBy("band")))
                   .filter(F.col("n") <= MAX_BUCKET).select("text_id", "band"))
        cands = (buckets.alias("x").join(buckets.alias("y"), "band")
                 .filter(F.col("x.text_id") < F.col("y.text_id"))
                 .select(F.col("x.text_id").alias("a"), F.col("y.text_id").alias("b")).distinct())
        info = vecs.select("text_id", "asins", "uniq")
        pairs = (cands.join(info.toDF("a", "asins_a", "uniq_a"), "a").join(info.toDF("b", "asins_b", "uniq_b"), "b")
                 .withColumn("jaccard", F.size(F.array_intersect("uniq_a", "uniq_b")) / F.size(F.array_union("uniq_a", "uniq_b")))
                 .filter((F.col("jaccard") >= 0.8) & (F.size(F.array_union("asins_a", "asins_b")) >= 2))
                 .select("a", "b").persist(StorageLevel.MEMORY_AND_DISK))
        report["near_duplicate_pairs"] = pairs.count()
        dup_ids = (pairs.select(F.col("a").alias("text_id")).union(pairs.select(F.col("b").alias("text_id")))
                   .union(exact).distinct())

dup_ids = dup_ids.withColumn("near_duplicate", F.lit(True))

# ------------------------------------------------------------------ 2. review-level signals
w_near = Window.partitionBy("parent_asin").orderBy("ts").rangeBetween(-3 * DAY, 3 * DAY)
w_prod = Window.partitionBy("parent_asin")
signals = (base.drop("tokens")
    .join(dup_ids, "text_id", "left")
    .withColumn("ts", (F.col("timestamp") / 1000).cast("long"))
    .withColumn("week_reviews", F.count("*").over(w_near))
    .withColumn("week_avg", F.avg("rating").over(w_near))
    .withColumn("product_reviews", F.count("*").over(w_prod))
    .withColumn("near_duplicate", F.coalesce("near_duplicate", F.lit(False)))
    .withColumn("text_rating_mismatch", ((F.col("rating") >= 4) & (F.col("p_negative") >= 0.8)) |
                                        ((F.col("rating") <= 2) & (F.col("p_positive") >= 0.8)))
    .withColumn("rating_deviation", F.abs(F.col("rating") - F.col("average_rating")) >= 3)
    .withColumn("burst", (F.col("week_reviews") >= 3) & (F.col("week_reviews") / F.col("product_reviews") >= 0.5)
                         & ((F.col("week_avg") >= 4.5) | (F.col("week_avg") <= 1.5)))
    .withColumn("short_generic", (F.col("word_count") <= 3) & F.col("rating").isin(1.0, 5.0))
    .withColumn("unverified", ~F.col("verified_purchase"))
    .na.fill(False, ["text_rating_mismatch", "rating_deviation", "burst", "short_generic", "unverified"])
    .drop("ts", "week_reviews", "week_avg", "text_id"))

with steps("review-level signals (window functions over all reviews)"):
    signals = signals.persist(StorageLevel.DISK_ONLY)
    report["reviews"] = signals.count()

# ------------------------------------------------------------------ 3. reviewer-level signals
FEATURES = ["log_n_reviews", "avg_rating", "rating_std", "share_5_star", "share_1_star", "share_verified",
            "avg_words", "avg_deviation", "share_duplicate", "share_mismatch", "log_reviews_per_day"]
with steps(f"reviewer features + KMeans (k={args.k})"):
    users = (signals.groupBy("user_id").agg(
                F.count("*").alias("n_reviews"), F.avg("rating").alias("avg_rating"),
                F.stddev_pop("rating").alias("rating_std"),
                F.avg((F.col("rating") == 5).cast("double")).alias("share_5_star"),
                F.avg((F.col("rating") == 1).cast("double")).alias("share_1_star"),
                F.avg(F.col("verified_purchase").cast("double")).alias("share_verified"),
                F.avg("word_count").alias("avg_words"),
                F.avg(F.abs(F.col("rating") - F.col("average_rating"))).alias("avg_deviation"),
                F.avg(F.col("near_duplicate").cast("double")).alias("share_duplicate"),
                F.avg(F.col("text_rating_mismatch").cast("double")).alias("share_mismatch"),
                F.countDistinct("review_date").alias("active_days"))
             .filter(F.col("n_reviews") >= 3)
             .withColumn("reviews_per_active_day", F.col("n_reviews") / F.col("active_days"))
             .withColumn("log_n_reviews", F.log1p("n_reviews"))
             .withColumn("log_reviews_per_day", F.log1p("reviews_per_active_day"))
             .na.fill(0.0).persist(StorageLevel.MEMORY_AND_DISK))
    report["reviewers_3plus"] = users.count()
    scaled = Pipeline(stages=[VectorAssembler(inputCols=FEATURES, outputCol="raw"),
                              StandardScaler(inputCol="raw", outputCol="features", withMean=True, withStd=True)]
                      ).fit(users).transform(users)
    km = KMeans(k=args.k, seed=SEED, featuresCol="features").fit(scaled)
    centers = [np.asarray(c) for c in km.clusterCenters()]
    dist = F.udf(lambda v, c: float(np.linalg.norm(v.toArray() - centers[c])), "double")
    clustered = (km.transform(scaled).withColumn("distance", dist("features", "prediction"))
                 .withColumnRenamed("prediction", "cluster").drop("raw", "features")
                 .persist(StorageLevel.MEMORY_AND_DISK))
    cutoff = clustered.approxQuantile("distance", [0.99], 0.001)[0]
    profiles = (clustered.groupBy("cluster").agg(F.count("*").alias("reviewers"),
                *[F.round(F.avg(c), 2).alias(c) for c in ["n_reviews", "avg_rating", "rating_std", "share_5_star",
                  "share_1_star", "share_verified", "avg_words", "avg_deviation", "share_duplicate",
                  "share_mismatch", "reviews_per_active_day"]]).orderBy("cluster").toPandas())
    save_csv(spark, f"{OUT}/fake_cluster_profiles.csv", profiles)
    user_flags = clustered.select(
        "user_id", "cluster", (F.col("distance") > cutoff).alias("outlier_reviewer"),
        ((F.col("n_reviews") >= 5) & ((F.col("share_5_star") == 1) | (F.col("share_1_star") == 1))).alias("one_sided_reviewer"))

# ------------------------------------------------------------------ 4. score
with steps("suspicion score -> amazon.fake_scores (HDFS + bucket)"):
    scored = (signals.join(user_flags, "user_id", "left")
              .na.fill(False, ["outlier_reviewer", "one_sided_reviewer"])
              .withColumn("suspicion_score", sum(F.col(s).cast("double") * w for s, w in WEIGHTS.items()))
              .withColumn("signals_count", sum(F.col(s).cast("int") for s in WEIGHTS))
              .withColumn("suspicious", F.col("suspicion_score") >= THRESHOLD)
              .select("review_id", "user_id", "parent_asin", "rating", *WEIGHTS,
                      "suspicion_score", "signals_count", "suspicious", "cluster"))
    save_table(spark, scored, "fake_scores", bucket=args.bucket)

fake = spark.table("amazon.fake_scores")
with steps("summary tables"):
    # one pass: how often each signal fires, overall and among flagged reviews
    row = fake.agg(F.count("*").alias("n"), F.sum(F.col("suspicious").cast("int")).alias("flagged"),
                   *[F.sum(F.col(s).cast("int")).alias(s) for s in WEIGHTS],
                   *[F.sum((F.col(s) & F.col("suspicious")).cast("int")).alias(f"{s}_f") for s in WEIGHTS]).first()
    n, flagged = row["n"], row["flagged"]
    prevalence = pd.DataFrame([{"signal": s, "points": w, "reviews": row[s],
                                "pct_of_all": round(100 * row[s] / n, 2),
                                "pct_of_flagged": round(100 * row[f"{s}_f"] / max(flagged, 1), 1)}
                               for s, w in WEIGHTS.items()])
    save_csv(spark, f"{OUT}/fake_signal_prevalence.csv", prevalence)
    report.update({"flagged": flagged, "flagged_pct": round(100 * flagged / n, 3)})

    impact = (fake.groupBy("parent_asin").agg(
                  F.count("*").alias("reviews"), F.sum(F.col("suspicious").cast("int")).alias("flagged"),
                  F.avg("rating").alias("avg_all"),
                  F.avg(F.when(~F.col("suspicious"), F.col("rating"))).alias("avg_without_flagged"))
              .filter(F.col("reviews") >= args.min_product_reviews)
              .withColumn("change", F.col("avg_without_flagged") - F.col("avg_all"))
              .join(spark.table("amazon.products_clean").select("parent_asin", "product_title"), "parent_asin", "left"))
    imp = impact.agg(F.count("*").alias("products"),
                     F.sum((F.abs("change") >= 0.1).cast("int")).alias("changed_0_1"),
                     F.sum((F.col("change") <= -0.1).cast("int")).alias("inflated"),
                     F.sum((F.col("change") >= 0.1).cast("int")).alias("deflated")).first().asDict()
    report["impact"] = imp
    top_impact = impact.orderBy(F.desc(F.abs("change"))).limit(50).toPandas()
    save_csv(spark, f"{OUT}/fake_product_rating_impact_top50.csv", top_impact)

print(prevalence.to_string(index=False))
print(profiles.to_string(index=False))
print(report)
report["seconds"] = steps.times
save_json(spark, f"{OUT}/fake_report.json", report)
spark.stop()
