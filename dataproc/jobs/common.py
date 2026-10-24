"""
Shared helpers for the Dataproc jobs (shipped to the cluster with --py-files).

The text cleaning here is the SAME as notebooks/02_cleaning.ipynb, so full-scale results are
comparable with the Colab sample results.
"""
import io
import json
import time

from pyspark.sql import functions as F

HDFS = "hdfs:///amazon"
KEEP_WORDS = {"not", "no", "nor", "against", "very", "too"}

# where each table lives (relative to HDFS / the bucket) and how it is partitioned
TABLES = {
    "reviews_raw": ("parquet/reviews_raw", ["year"]),
    "products_raw": ("parquet/products_raw", []),
    "reviews_clean": ("parquet/reviews_clean", ["year"]),
    "products_clean": ("parquet/products_clean", []),
    "sentiment_scores": ("parquet/sentiment_scores", []),
    "fake_scores": ("parquet/fake_scores", []),
}


# ------------------------------------------------------------------ text cleaning (Phase 2 rules)
def clean_text(title_col, text_col):
    c = F.concat_ws(" ", F.coalesce(title_col, F.lit("")), F.coalesce(text_col, F.lit("")))
    c = F.regexp_replace(c, r"<[^>]+>", " ")                 # HTML tags such as <br />
    c = F.regexp_replace(c, r"&#?[a-zA-Z0-9]+;", " ")        # HTML codes such as &#34;
    c = F.regexp_replace(c, r"https?://\S+|www\.\S+", " ")   # links
    c = F.lower(c)
    c = F.regexp_replace(c, r"n't\b", " not")                # don't -> do not
    c = F.regexp_replace(c, r"[^a-z ]", " ")                 # letters only
    c = F.regexp_replace(c, r"\s+", " ")
    return F.trim(c)


def tokenize(df):
    """text_clean -> tokens (stop words removed, negations kept) + word_count."""
    from pyspark.ml.feature import RegexTokenizer, StopWordsRemover
    stop = [w for w in StopWordsRemover.loadDefaultStopWords("english") if w not in KEEP_WORDS]
    tok = RegexTokenizer(inputCol="text_clean", outputCol="tokens_all", pattern=r"\s+", minTokenLength=2)
    rem = StopWordsRemover(inputCol="tokens_all", outputCol="tokens", stopWords=stop)
    return rem.transform(tok.transform(df)).drop("tokens_all").withColumn("word_count", F.size("tokens"))


def add_labels(df):
    return (df.withColumn("sentiment", F.when(F.col("rating") >= 4, "positive")
                                        .when(F.col("rating") == 3, "neutral").otherwise("negative"))
              .withColumn("label", F.when(F.col("rating") >= 4, 2.0)
                                    .when(F.col("rating") == 3, 1.0).otherwise(0.0)))


def review_id_col():
    return F.substring(F.sha2(F.concat_ws("|", "user_id", "parent_asin", F.col("timestamp").cast("string")), 256), 1, 16)


# ------------------------------------------------------------------ tables: HDFS + Hive + bucket copy
def save_table(spark, df, name, bucket=None, salt_buckets=8):
    """Write df as Parquet on HDFS, register it as Hive table amazon.<name>, optionally copy to the bucket."""
    rel, parts = TABLES[name]
    spark.sql("CREATE DATABASE IF NOT EXISTS amazon")
    spark.sql(f"DROP TABLE IF EXISTS amazon.{name}")
    if parts:
        # spread each partition value over a few tasks so one big year is not written by one task
        out = (df.withColumn("_salt", F.abs(F.hash(*df.columns[:2])) % salt_buckets)
                 .repartition(96, *parts, "_salt").drop("_salt"))
    else:
        out = df
    (out.write.mode("overwrite").format("parquet").partitionBy(*parts)
        .option("path", f"{HDFS}/{rel}").saveAsTable(f"amazon.{name}"))
    if bucket:
        copy_table_to_bucket(spark, name, bucket)


def copy_table_to_bucket(spark, name, bucket):
    rel, parts = TABLES[name]
    spark.table(f"amazon.{name}").write.mode("overwrite").partitionBy(*parts).parquet(f"{bucket}/{rel}")


def restore_table(spark, name, bucket):
    """Bucket Parquet -> HDFS -> Hive table (used on a fresh cluster). Returns False if not in the bucket."""
    rel, parts = TABLES[name]
    if not path_exists(spark, f"{bucket}/{rel}"):
        return False
    save_table(spark, spark.read.parquet(f"{bucket}/{rel}"), name)
    return True


# ------------------------------------------------------------------ files on HDFS / GCS
def _fs(spark, path):
    jvm = spark._jvm
    p = jvm.org.apache.hadoop.fs.Path(path)
    return p, p.getFileSystem(spark._jsc.hadoopConfiguration())


def path_exists(spark, path):
    p, fs = _fs(spark, path)
    return fs.exists(p)


def write_text(spark, path, text):
    p, fs = _fs(spark, path)
    stream = fs.create(p, True)
    stream.write(bytearray(text.encode("utf-8")))
    stream.close()


def save_json(spark, path, obj):
    write_text(spark, path, json.dumps(obj, indent=2, default=str))
    print("saved", path, flush=True)


def save_csv(spark, path, pdf):
    buf = io.StringIO()
    pdf.to_csv(buf, index=False)
    write_text(spark, path, buf.getvalue())
    print("saved", path, flush=True)


def copy_files(spark, src, dst):
    """Copy raw files (e.g. .gz) between GCS and HDFS with Hadoop FileUtil."""
    jvm, conf = spark._jvm, spark._jsc.hadoopConfiguration()
    s, sfs = _fs(spark, src)
    d, dfs = _fs(spark, dst)
    if dfs.exists(d):
        dfs.delete(d, True)
    jvm.org.apache.hadoop.fs.FileUtil.copy(sfs, s, dfs, d, False, True, conf)


# ------------------------------------------------------------------ timing
class Steps:
    """with steps('name'): ...  -> prints and records how long each step took."""
    def __init__(self):
        self.times = {}

    def __call__(self, name):
        steps = self

        class _T:
            def __enter__(self):
                self.t = time.time()
                print(f"--> {name}", flush=True)

            def __exit__(self, *exc):
                steps.times[name] = round(time.time() - self.t, 1)
                print(f"    {name}: {steps.times[name]}s", flush=True)
        return _T()


def confusion_metrics(pred_df, name, class_names=("negative", "neutral", "positive")):
    """Accuracy, macro F1 and per-class F1 from a Spark DataFrame with label + prediction."""
    import numpy as np
    rows = pred_df.groupBy("label", "prediction").count().collect()
    m = np.zeros((3, 3))
    for r in rows:
        m[int(r["label"]), int(r["prediction"])] = r["count"]
    tp = np.diag(m)
    prec = tp / np.maximum(m.sum(0), 1)
    rec = tp / np.maximum(m.sum(1), 1)
    f1 = 2 * prec * rec / np.maximum(prec + rec, 1e-12)
    out = {"model": name, "accuracy": tp.sum() / m.sum(), "macro_f1": f1.mean(),
           "weighted_f1": (f1 * m.sum(1)).sum() / m.sum()}
    for i, c in enumerate(class_names):
        out[f"f1_{c}"] = f1[i]
        out[f"recall_{c}"] = rec[i]
    return out, m
