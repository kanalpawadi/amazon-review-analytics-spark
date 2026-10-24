#!/usr/bin/env bash
# Submit the ingestion job to the cluster, then query the new table with HIVE itself.
#   bash run_ingest.sh            first time: raw JSON -> HDFS -> Parquet -> Hive  (about 30-45 min)
#   bash run_ingest.sh restore    new cluster later: all saved tables from the bucket -> HDFS -> Hive
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh
MODE="${1:-full}"

gcloud dataproc jobs submit pyspark jobs/ingest.py \
    --cluster="$CLUSTER" --region="$REGION" --py-files=jobs/common.py \
    -- --bucket="$BUCKET" --mode="$MODE"

echo
echo "==> Same table, queried by the Hive engine (not Spark):"
gcloud dataproc jobs submit hive --cluster="$CLUSTER" --region="$REGION" --execute "
    SELECT verified_purchase, COUNT(*) AS reviews, ROUND(AVG(rating), 2) AS avg_rating
    FROM amazon.reviews_raw GROUP BY verified_purchase;"

echo
echo "==> HDFS contents (hdfs dfs -du -h, run as a Hadoop job):"
gcloud dataproc jobs submit hadoop --cluster="$CLUSTER" --region="$REGION" \
    --class=org.apache.hadoop.fs.FsShell -- -du -h /amazon /amazon/parquet
