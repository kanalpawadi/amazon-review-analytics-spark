"""
Phase 5 - clean ALL Electronics reviews (same rules as notebooks/02_cleaning.ipynb).

amazon.reviews_raw  -> amazon.reviews_clean  (HDFS, Hive, partitioned by year; copy in the bucket)
amazon.products_raw -> amazon.products_clean
Results: <bucket>/results/full/cleaning_log.csv and clean_report.json
"""
import argparse

import pandas as pd
from pyspark.sql import SparkSession, functions as F

from common import (Steps, add_labels, clean_text, review_id_col, save_csv, save_json, save_table, tokenize)

parser = argparse.ArgumentParser()
parser.add_argument("--bucket", required=True)
args = parser.parse_args()
OUT = f"{args.bucket}/results/full"

spark = SparkSession.builder.appName("clean-full").enableHiveSupport().getOrCreate()
spark.sparkContext.setLogLevel("WARN")
steps = Steps()
raw = spark.table("amazon.reviews_raw")

with steps("count raw + invalid rows (one pass)"):
    valid_cond = (F.col("user_id").isNotNull() & F.col("parent_asin").isNotNull()
                  & F.col("rating").isNotNull() & F.col("rating").between(1, 5))
    agg = raw.agg(F.count("*").alias("raw"), F.sum(valid_cond.cast("int")).alias("valid")).first()

# Spark is lazy: these lines only describe the work; it runs inside the next timed step
deduped = (raw.filter(valid_cond)
           .withColumn("text_hash", F.sha2(F.coalesce("text", F.lit("")), 256))
           .dropDuplicates(["user_id", "parent_asin", "text_hash"]).drop("text_hash"))

with steps("dedupe + clean text + tokens + labels -> amazon.reviews_clean (HDFS + bucket)"):
    clean = (deduped
             .withColumn("review_id", review_id_col())
             .withColumn("review_date", F.to_date(F.from_unixtime(F.col("timestamp") / 1000)))
             .withColumn("text_clean", clean_text(F.col("title"), F.col("text")))
             .filter(F.length("text_clean") > 0))
    clean = add_labels(tokenize(clean)).select(
        "review_id", "user_id", "parent_asin", "asin", "rating", "sentiment", "label",
        "title", "text", "text_clean", "tokens", "word_count",
        "verified_purchase", "helpful_vote", "timestamp", "review_date", "year")
    save_table(spark, clean, "reviews_clean", bucket=args.bucket)

with steps("products -> amazon.products_clean"):
    products = (spark.table("amazon.products_raw")
                .dropna(subset=["parent_asin"]).dropDuplicates(["parent_asin"])
                .select("parent_asin", F.col("title").alias("product_title"),
                        F.coalesce("main_category", F.lit("Unknown")).alias("main_category"),
                        "average_rating", "rating_number", F.col("price").cast("double").alias("price"),
                        "store", "categories"))
    save_table(spark, products, "products_clean", bucket=args.bucket)

with steps("count after each step"):
    n_dedup = deduped.count()
    n_final = spark.table("amazon.reviews_clean").count()
    n_products = spark.table("amazon.products_clean").count()

log = pd.DataFrame([
    ("1. Raw reviews", agg["raw"]),
    ("2-3. Valid user, product and rating 1-5", agg["valid"]),
    ("4. Remove exact duplicates (same user+product+text)", n_dedup),
    ("5. Drop reviews with no words after cleaning", n_final),
], columns=["step", "rows"])
log["removed"] = (log["rows"].shift(1) - log["rows"]).fillna(0).astype(int)
print(log.to_string(index=False))
save_csv(spark, f"{OUT}/cleaning_log.csv", log)

summary = spark.sql("""
    SELECT sentiment, COUNT(*) AS reviews, ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct,
           ROUND(AVG(word_count), 1) AS avg_words,
           ROUND(100 * AVG(CAST(verified_purchase AS INT)), 1) AS verified_pct
    FROM amazon.reviews_clean GROUP BY sentiment ORDER BY reviews DESC""").toPandas()
print(summary.to_string(index=False))
save_csv(spark, f"{OUT}/sentiment_split.csv", summary)
save_json(spark, f"{OUT}/clean_report.json",
          {"rows": log.to_dict("records"), "products": n_products, "seconds": steps.times})
spark.stop()
