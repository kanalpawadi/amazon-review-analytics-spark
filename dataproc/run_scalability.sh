#!/usr/bin/env bash
# Scalability study: every (executors x data share) combination as its own Spark job.
# Each executor = 1 worker node = 2 cores, so 1/2/3 executors = 2/4/6 cores.
#
#   bash run_scalability.sh                         all 12 runs (about 2-3 hours)
#   bash run_scalability.sh "1 3" "0.1 1.0"         only some runs
#
# Needs: ingest + clean done on this cluster (run_pipeline.sh), and ideally the sentiment model.
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

EXECUTORS="${1:-1 2 3}"
FRACTIONS="${2:-0.1 0.25 0.5 1.0}"

for n in $EXECUTORS; do
    for f in $FRACTIONS; do
        cores=$(( n * 2 ))
        echo "==> data share $f with $n executor(s) = $cores cores   ($(date +%H:%M))"
        gcloud dataproc jobs submit pyspark jobs/scalability.py \
            --cluster="$CLUSTER" --region="$REGION" --py-files=jobs/common.py \
            --properties="spark.dynamicAllocation.enabled=false,spark.executor.instances=$n,spark.executor.cores=2,spark.executor.memory=3g" \
            -- --bucket="$BUCKET" --fraction="$f" --cores="$cores" \
            2>&1 | grep -E "^(sql_|text_|sentiment_|als_)|skipped|ERROR|Error" || true
    done
done
echo "==> All runs done. Next: bash collect_results.sh"
