"""
Phase 5 - one scalability run: times 4 workloads on a share of the data.

The number of executors is fixed by run_scalability.sh (spark.executor.instances), so each run
measures one (data fraction, cores) combination. Every run writes one JSON file:
<bucket>/results/scalability/runs/frac_<f>_cores_<c>.json   (collected by collect_results.sh)

Workloads (each forces a full computation; 'noop' output = compute everything, write nothing):
  sql_aggregation    Spark SQL group-by over the clean reviews             (scan heavy)
  text_cleaning      Phase 2 cleaning + tokenizing on the raw reviews       (CPU heavy)
  sentiment_scoring  TF-IDF + Logistic Regression model on the clean reviews (ML inference)
  als_training       implicit ALS, 5 iterations, on the 5-core ratings      (iterative ML training)
"""
import argparse
import time

from pyspark.ml import PipelineModel
from pyspark.ml.recommendation import ALS
from pyspark.ml.feature import StringIndexer
from pyspark.sql import SparkSession, functions as F

from common import add_labels, clean_text, path_exists, save_json, tokenize

parser = argparse.ArgumentParser()
parser.add_argument("--bucket", required=True)
parser.add_argument("--fraction", type=float, required=True)
parser.add_argument("--cores", type=int, required=True, help="total executor cores (for the label only)")
args = parser.parse_args()

spark = SparkSession.builder.appName(f"scale-f{args.fraction}-c{args.cores}").enableHiveSupport().getOrCreate()
spark.sparkContext.setLogLevel("WARN")
spark.sparkContext.setCheckpointDir("hdfs:///tmp/als-checkpoints")


def pick(df):
    """The same users are always in the sample, so every step sees the same share of the data."""
    return df.filter(F.abs(F.hash("user_id")) % 1000 < int(args.fraction * 1000))


result = {"data_fraction": args.fraction, "cores": args.cores, "steps": {}, "rows": {}}


def run(name, fn):
    t0 = time.time()
    rows = fn()
    result["steps"][name] = round(time.time() - t0, 1)
    result["rows"][name] = rows
    print(f"{name:<18} {result['steps'][name]:>8}s  rows={rows:,}", flush=True)


def sql_aggregation():
    df = pick(spark.table("amazon.reviews_clean"))
    out = df.groupBy("year", "sentiment").agg(F.count("*").alias("n"), F.avg("word_count"), F.avg("helpful_vote")).collect()
    return int(sum(r["n"] for r in out))


# One pass each: summing the tokens / predictions forces the full computation and counts the rows.
def text_cleaning():
    df = pick(spark.table("amazon.reviews_raw")).withColumn("text_clean", clean_text(F.col("title"), F.col("text")))
    out = add_labels(tokenize(df))
    row = out.agg(F.count("*").alias("n"), F.sum(F.size("tokens")), F.sum("label")).first()
    return int(row["n"])


def sentiment_scoring():
    model = PipelineModel.load(f"{args.bucket}/models/sentiment_lr_full")
    df = pick(spark.table("amazon.reviews_clean")).filter(F.size("tokens") > 0)
    row = model.transform(df).agg(F.count("*").alias("n"), F.sum("prediction")).first()
    return int(row["n"])


def als_training():
    schema = "user_id STRING, parent_asin STRING, rating DOUBLE, timestamp LONG"
    r = pick(spark.read.csv(f"{args.bucket}/5core/Electronics.train.csv.gz", header=True, schema=schema)).repartition(48)
    r = StringIndexer(inputCol="user_id", outputCol="u").fit(r).transform(r)
    r = StringIndexer(inputCol="parent_asin", outputCol="i").fit(r).transform(r).withColumn("bought", F.lit(1.0)).cache()
    n = r.count()
    ALS(userCol="u", itemCol="i", ratingCol="bought", implicitPrefs=True, alpha=10.0, rank=10, maxIter=5,
        regParam=0.1, seed=42).fit(r)
    return n


run("sql_aggregation", sql_aggregation)
run("text_cleaning", text_cleaning)
if path_exists(spark, f"{args.bucket}/models/sentiment_lr_full"):
    run("sentiment_scoring", sentiment_scoring)
else:
    print("sentiment_scoring skipped: run jobs/sentiment.py first")
run("als_training", als_training)

save_json(spark, f"{args.bucket}/results/scalability/runs/frac_{args.fraction}_cores_{args.cores}.json", result)
spark.stop()
