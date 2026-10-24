"""
Phase 5 - recommendation on the FULL official 5-core Electronics split (notebooks/04c ran on 20% of users).

Explicit ALS (rating prediction, RMSE vs baselines) + implicit ALS (top-10, HitRate/Precision/NDCG@10 vs
most-popular baseline), with the settings found in Colab. Results: <bucket>/results/full/recommend_*.csv
"""
import argparse

import pandas as pd
from pyspark import StorageLevel
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import StringIndexer
from pyspark.ml.recommendation import ALS
from pyspark.sql import SparkSession, Window, functions as F

from common import Steps, save_csv, save_json

parser = argparse.ArgumentParser()
parser.add_argument("--bucket", required=True)
parser.add_argument("--rank", type=int, default=30)
parser.add_argument("--reg", type=float, default=0.3)
parser.add_argument("--alpha", type=float, default=10.0, help="implicit ALS alpha (best value from Colab)")
parser.add_argument("--implicit-rank", type=int, default=20)
parser.add_argument("--eval-users", type=int, default=5000)
args = parser.parse_args()
OUT, SEED, K, EXTRA = f"{args.bucket}/results/full", 42, 10, 60

spark = SparkSession.builder.appName("recommend-full").enableHiveSupport().getOrCreate()
spark.sparkContext.setLogLevel("WARN")
spark.sparkContext.setCheckpointDir("hdfs:///tmp/als-checkpoints")
steps = Steps()

SCHEMA = "user_id STRING, parent_asin STRING, rating DOUBLE, timestamp LONG"
load = lambda s: spark.read.csv(f"{args.bucket}/5core/Electronics.{s}.csv.gz", header=True, schema=SCHEMA).repartition(48)

with steps("load + index the 5-core split"):
    train, valid, test = load("train"), load("valid"), load("test")
    all_ids = train.union(valid).union(test)
    ui = StringIndexer(inputCol="user_id", outputCol="u").fit(all_ids)
    ii = StringIndexer(inputCol="parent_asin", outputCol="i").fit(all_ids)
    idx = lambda d: (ii.transform(ui.transform(d)).withColumn("u", F.col("u").cast("int"))
                     .withColumn("i", F.col("i").cast("int")).persist(StorageLevel.MEMORY_AND_DISK))
    tv, test_i = idx(train.union(valid)), idx(test)
    stats = {"ratings": tv.count() + test_i.count(), "users": len(ui.labelsArray[0]), "products": len(ii.labelsArray[0])}
    stats["ratings_per_user"] = round(stats["ratings"] / stats["users"], 2)
    stats["density_pct"] = round(100 * stats["ratings"] / (stats["users"] * stats["products"]), 5)
    print(stats)

rmse = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
with steps(f"explicit ALS rank={args.rank} reg={args.reg}"):
    explicit = ALS(userCol="u", itemCol="i", ratingCol="rating", rank=args.rank, regParam=args.reg, maxIter=10,
                   nonnegative=True, coldStartStrategy="drop", seed=SEED).fit(tv)
    gmean = tv.agg(F.avg("rating")).first()[0]
    base = (test_i.join(tv.groupBy("i").agg(F.avg("rating").alias("item_avg")), "i", "left")
            .withColumn("global", F.lit(gmean)).withColumn("product", F.coalesce("item_avg", F.lit(gmean))))
    rmse_table = pd.DataFrame([
        {"model": "Baseline: global average", "test_rmse": rmse.setPredictionCol("global").evaluate(base)},
        {"model": "Baseline: product average", "test_rmse": rmse.setPredictionCol("product").evaluate(base)},
        {"model": f"Explicit ALS (rank {args.rank}, reg {args.reg})",
         "test_rmse": rmse.setPredictionCol("prediction").evaluate(explicit.transform(test_i))}]).round(4)
    save_csv(spark, f"{OUT}/recommend_rmse.csv", rmse_table)

with steps(f"implicit ALS alpha={args.alpha}"):
    implicit = ALS(userCol="u", itemCol="i", ratingCol="bought", implicitPrefs=True, alpha=args.alpha,
                   rank=args.implicit_rank, regParam=0.1, maxIter=10, nonnegative=True,
                   coldStartStrategy="drop", seed=SEED).fit(tv.withColumn("bought", F.lit(1.0)))

eval_users = test_i.select("u").distinct().orderBy(F.rand(SEED)).limit(args.eval_users).persist()
truth = test_i.join(eval_users, "u").select("u", F.col("i").alias("true_i"))
seen = tv.select("u", "i").distinct()


def top_k(cands):
    w = Window.partitionBy("u").orderBy("pos")
    return (cands.join(seen, ["u", "i"], "left_anti").withColumn("rank", F.row_number().over(w))
                 .filter(F.col("rank") <= K))


def model_recs(m):
    return top_k(m.recommendForUserSubset(eval_users, K + EXTRA)
                 .select("u", F.posexplode("recommendations").alias("pos", "rec"))
                 .select("u", F.col("rec.i").alias("i"), "pos"))


def metrics(recs, name):
    recs = recs.persist()
    hits = truth.join(recs.withColumnRenamed("i", "true_i"), ["u", "true_i"], "left")
    m = hits.agg(F.avg(F.col("rank").isNotNull().cast("double")).alias("hit"),
                 F.avg(F.when(F.col("rank").isNotNull(), 1 / F.log2(F.col("rank") + 1)).otherwise(0.0)).alias("ndcg")).first()
    return {"model": name, f"hit_rate@{K}": m["hit"], f"precision@{K}": m["hit"] / K, f"ndcg@{K}": m["ndcg"],
            "products_recommended": recs.select("i").distinct().count()}


with steps(f"top-{K} evaluation on {args.eval_users:,} users"):
    popular = (tv.groupBy("i").count().orderBy(F.desc("count")).limit(K + EXTRA)
               .withColumn("pos", F.row_number().over(Window.orderBy(F.desc("count")))).select("i", "pos"))
    ranking = pd.DataFrame([metrics(top_k(eval_users.crossJoin(popular)), "Baseline: most popular"),
                            metrics(model_recs(explicit), "Explicit ALS"),
                            metrics(model_recs(implicit), f"Implicit ALS (alpha {args.alpha:g})")])
    save_csv(spark, f"{OUT}/recommend_ranking.csv", ranking.round(5))

print(rmse_table.to_string(index=False))
print(ranking.round(4).to_string(index=False))
save_json(spark, f"{OUT}/recommend_report.json",
          {"data": stats, "settings": vars(args), "rmse": rmse_table.to_dict("records"),
           "ranking": ranking.to_dict("records"), "seconds": steps.times})
spark.stop()
