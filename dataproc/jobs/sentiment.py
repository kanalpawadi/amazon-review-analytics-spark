"""
Phase 5 - sentiment at full scale (same method as notebooks/04a_sentiment.ipynb).

1. Stratified sample of --train-size reviews -> 80/20 split, class weights
2. Words + word pairs -> CountVectorizer -> IDF; Logistic Regression and Naive Bayes vs the baseline
3. Save the model and score ALL reviews -> amazon.sentiment_scores (HDFS + bucket)
Results: <bucket>/results/full/sentiment_*.csv, sentiment_report.json; model: <bucket>/models/sentiment_lr_full
"""
import argparse

import numpy as np
import pandas as pd
from pyspark import StorageLevel
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.classification import LogisticRegression, NaiveBayes
from pyspark.ml.feature import IDF, CountVectorizer, NGram, SQLTransformer
from pyspark.ml.functions import vector_to_array
from pyspark.sql import SparkSession, functions as F

from common import Steps, confusion_metrics, save_csv, save_json, save_table

parser = argparse.ArgumentParser()
parser.add_argument("--bucket", required=True)
parser.add_argument("--train-size", type=int, default=2_000_000, help="reviews used for training (80%) + test (20%)")
parser.add_argument("--reg", type=float, default=0.1, help="regParam (best value from the Colab cross-validation)")
args = parser.parse_args()
OUT, SEED = f"{args.bucket}/results/full", 42
CLASSES = ["negative", "neutral", "positive"]

spark = SparkSession.builder.appName("sentiment-full").enableHiveSupport().getOrCreate()
spark.sparkContext.setLogLevel("WARN")
steps = Steps()

data = spark.table("amazon.reviews_clean").filter(F.size("tokens") > 0).select("review_id", "rating", "label", "tokens")

with steps("stratified sample + split"):
    total = data.count()
    frac = min(1.0, args.train_size / total)
    sample = data.sampleBy("label", {0.0: frac, 1.0: frac, 2.0: frac}, seed=SEED).persist(StorageLevel.MEMORY_AND_DISK)
    train = sample.sampleBy("label", {0.0: 0.8, 1.0: 0.8, 2.0: 0.8}, seed=SEED)
    test = sample.join(train.select("review_id"), "review_id", "left_anti")
    counts = {r["label"]: r["count"] for r in train.groupBy("label").count().collect()}
    weights = {k: sum(counts.values()) / (3 * v) for k, v in counts.items()}
    wmap = F.create_map(*[x for kv in weights.items() for x in (F.lit(kv[0]), F.lit(kv[1]))])
    train = train.withColumn("weight", wmap[F.col("label")]).persist(StorageLevel.MEMORY_AND_DISK)
    n_train, n_test = train.count(), test.count()
    print(f"all reviews {total:,}  train {n_train:,}  test {n_test:,}  weights {weights}")

with steps("fit features (words + word pairs, TF-IDF)"):
    feature_model = Pipeline(stages=[
        NGram(n=2, inputCol="tokens", outputCol="bigrams"),
        SQLTransformer(statement="SELECT *, concat(tokens, bigrams) AS terms FROM __THIS__"),
        CountVectorizer(inputCol="terms", outputCol="tf", vocabSize=100_000, minDF=5),
        IDF(inputCol="tf", outputCol="features", minDocFreq=5),
    ]).fit(train)
    train_f = feature_model.transform(train).select("label", "weight", "features").persist(StorageLevel.MEMORY_AND_DISK)
    test_f = feature_model.transform(test).select("label", "features").persist(StorageLevel.MEMORY_AND_DISK)
    train_f.count(); test_f.count()

results, models = [], {}
base, _ = confusion_metrics(test_f.withColumn("prediction", F.lit(2.0)), "Baseline: always positive")
results.append(base)
for name, est in [
    ("Logistic Regression (class weights)",
     LogisticRegression(featuresCol="features", labelCol="label", weightCol="weight", maxIter=100, regParam=args.reg)),
    ("Naive Bayes (class weights)",
     NaiveBayes(featuresCol="features", labelCol="label", weightCol="weight", modelType="multinomial")),
]:
    with steps(f"train {name}"):
        m = est.fit(train_f)
    row, cm = confusion_metrics(m.transform(test_f), name)
    row["train_seconds"] = steps.times[f"train {name}"]
    results.append(row)
    models[name] = (m, cm)
    print(f"{name}: accuracy {row['accuracy']:.3f}  macro F1 {row['macro_f1']:.3f}")

comparison = pd.DataFrame(results)
save_csv(spark, f"{OUT}/sentiment_model_comparison.csv", comparison.round(4))
lr_model, lr_cm = models["Logistic Regression (class weights)"]
save_csv(spark, f"{OUT}/sentiment_confusion_matrix.csv",
         pd.DataFrame(lr_cm.astype(int), index=CLASSES, columns=CLASSES).reset_index().rename(columns={"index": "true"}))

vocab = feature_model.stages[2].vocabulary
coef = lr_model.coefficientMatrix.toArray()
terms = pd.concat({c: pd.DataFrame({"term": [vocab[j] for j in np.argsort(coef[i])[::-1][:20]],
                                    "weight": np.sort(coef[i])[::-1][:20].round(3)})
                   for i, c in enumerate(CLASSES)}, axis=1)
terms.columns = [f"{a}_{b}" for a, b in terms.columns]
save_csv(spark, f"{OUT}/sentiment_top_terms.csv", terms)

with steps("save model"):
    scoring = PipelineModel(stages=feature_model.stages + [lr_model])
    scoring.write().overwrite().save(f"{args.bucket}/models/sentiment_lr_full")

with steps("score ALL reviews -> amazon.sentiment_scores (HDFS + bucket)"):
    scores = (scoring.transform(data)
              .withColumn("p", vector_to_array("probability"))
              .select("review_id", "rating", "label", F.col("prediction").alias("predicted_label"),
                      F.round(F.col("p")[0], 4).alias("p_negative"), F.round(F.col("p")[1], 4).alias("p_neutral"),
                      F.round(F.col("p")[2], 4).alias("p_positive")))
    save_table(spark, scores, "sentiment_scores", bucket=args.bucket)

with steps("agreement of predictions with star labels on all reviews"):
    full_row, _ = confusion_metrics(spark.table("amazon.sentiment_scores")
                                    .withColumnRenamed("predicted_label", "prediction"), "LR on ALL reviews")
    print(f"all reviews: accuracy {full_row['accuracy']:.3f}  macro F1 {full_row['macro_f1']:.3f}")

print(comparison.round(3).to_string(index=False))
save_json(spark, f"{OUT}/sentiment_report.json",
          {"reviews": total, "train": n_train, "test": n_test, "class_weights": weights,
           "regParam": args.reg, "vocabulary": len(vocab), "test_results": results,
           "all_reviews_result": full_row, "seconds": steps.times})
spark.stop()
