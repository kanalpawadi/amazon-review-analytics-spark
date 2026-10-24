"""
Phase 5 - ingest Electronics into HDFS, Parquet and Hive (runs on the Dataproc cluster).

--mode full     (first time)  GCS raw JSON -> HDFS -> Parquet partitioned by year (HDFS) -> Hive tables,
                              plus a Parquet copy in the bucket (HDFS is deleted with the cluster)
--mode restore  (new cluster) every table saved in the bucket -> HDFS -> Hive tables (a few minutes)

Submitted by run_ingest.sh.
"""
import argparse

from pyspark.sql import SparkSession, functions as F, types as T

from common import HDFS, TABLES, Steps, copy_files, restore_table, save_json, save_table

parser = argparse.ArgumentParser()
parser.add_argument("--bucket", required=True)           # gs://<project>-amazon-reviews
parser.add_argument("--mode", choices=["full", "restore"], default="full")
args = parser.parse_args()

spark = SparkSession.builder.appName(f"ingest-{args.mode}").enableHiveSupport().getOrCreate()
spark.sparkContext.setLogLevel("WARN")
steps = Steps()
report = {"mode": args.mode}

REVIEW_SCHEMA = T.StructType([
    T.StructField("rating", T.DoubleType()), T.StructField("title", T.StringType()),
    T.StructField("text", T.StringType()), T.StructField("asin", T.StringType()),
    T.StructField("parent_asin", T.StringType()), T.StructField("user_id", T.StringType()),
    T.StructField("timestamp", T.LongType()), T.StructField("helpful_vote", T.IntegerType()),
    T.StructField("verified_purchase", T.BooleanType()),
])
META_SCHEMA = T.StructType([
    T.StructField("parent_asin", T.StringType()), T.StructField("title", T.StringType()),
    T.StructField("main_category", T.StringType()), T.StructField("average_rating", T.DoubleType()),
    T.StructField("rating_number", T.LongType()), T.StructField("price", T.StringType()),
    T.StructField("store", T.StringType()), T.StructField("categories", T.ArrayType(T.StringType())),
])

if args.mode == "full":
    with steps("copy raw files GCS -> HDFS"):
        copy_files(spark, f"{args.bucket}/raw", f"{HDFS}/raw")

    # A .gz file cannot be split, so ONE task has to read it. We read it once and write splittable,
    # columnar Parquet spread over many files - every later step then runs fully in parallel.
    with steps("reviews JSON -> Parquet partitioned by year -> Hive amazon.reviews_raw (+ bucket copy)"):
        reviews = (spark.read.schema(REVIEW_SCHEMA).json(f"{HDFS}/raw/Electronics.jsonl.gz")
                   .withColumn("year", F.year(F.from_unixtime(F.col("timestamp") / 1000)).cast("int")))
        save_table(spark, reviews, "reviews_raw", bucket=args.bucket)

    with steps("metadata JSON -> Parquet -> Hive amazon.products_raw (+ bucket copy)"):
        products = spark.read.schema(META_SCHEMA).json(f"{HDFS}/raw/meta_Electronics.jsonl.gz").repartition(16)
        save_table(spark, products, "products_raw", bucket=args.bucket)
else:
    restored = []
    for name in TABLES:
        with steps(f"restore {name}"):
            if restore_table(spark, name, args.bucket):
                restored.append(name)
    report["restored_tables"] = restored

with steps("check with Spark SQL"):
    report["reviews"] = spark.sql("SELECT COUNT(*) AS n FROM amazon.reviews_raw").first()["n"]
    report["products"] = spark.sql("SELECT COUNT(*) AS n FROM amazon.products_raw").first()["n"]
    report["year_partitions"] = spark.sql("SHOW PARTITIONS amazon.reviews_raw").count()
    spark.sql("""SELECT year, COUNT(*) AS reviews, ROUND(AVG(rating), 2) AS avg_rating
                 FROM amazon.reviews_raw GROUP BY year ORDER BY year""").show(40)
    spark.sql("SHOW TABLES IN amazon").show()

report["seconds"] = steps.times
print(report)
save_json(spark, f"{args.bucket}/results/full/ingest_report_{args.mode}.json", report)
spark.stop()
