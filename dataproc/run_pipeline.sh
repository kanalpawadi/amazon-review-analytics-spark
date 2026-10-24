#!/usr/bin/env bash
# Full-scale pipeline on all Electronics reviews, one job after another.
#   bash run_pipeline.sh                  clean -> sentiment -> fake -> recommend
#   bash run_pipeline.sh fake recommend   only the named steps (e.g. after a failure)
#
# Rough times on the 8-vCPU cluster: clean 30-60 min, sentiment 40-70 min, fake 40-90 min
# (use FAKE_ARGS="--lsh off" to skip the near-duplicate search), recommend 30-60 min.
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

STEPS="${*:-clean sentiment fake recommend}"
FAKE_ARGS="${FAKE_ARGS:-}"
RECOMMEND_ARGS="${RECOMMEND_ARGS:-}"

submit() {   # submit <job.py> [job args...]
    local job="$1"; shift
    echo "==> $job   (started $(date +%H:%M))"
    gcloud dataproc jobs submit pyspark "jobs/$job" \
        --cluster="$CLUSTER" --region="$REGION" --py-files=jobs/common.py \
        --properties="spark.driver.memory=4g" \
        -- --bucket="$BUCKET" "$@"
}

for step in $STEPS; do
    case "$step" in
        clean)     submit clean.py ;;
        sentiment) submit sentiment.py ;;
        fake)      submit fake_reviews.py $FAKE_ARGS ;;
        recommend) submit recommend.py $RECOMMEND_ARGS ;;
        *) echo "unknown step: $step (use clean, sentiment, fake, recommend)"; exit 1 ;;
    esac
done
echo "==> Pipeline done. Results: $BUCKET/results/full/   Next: bash run_scalability.sh"
