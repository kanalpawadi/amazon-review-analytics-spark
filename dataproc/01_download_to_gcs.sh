#!/usr/bin/env bash
# Copy the dataset from UCSD straight into the bucket (run in Cloud Shell, no cluster needed).
# Files are streamed (download -> upload) so Cloud Shell's small disk is not used.
# Already-copied files are skipped, so it is safe to run again.
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

FILES=(
  "raw/review_categories/Electronics.jsonl.gz      raw/Electronics.jsonl.gz"
  "raw/meta_categories/meta_Electronics.jsonl.gz   raw/meta_Electronics.jsonl.gz"
  "benchmark/5core/last_out/Electronics.train.csv.gz  5core/Electronics.train.csv.gz"
  "benchmark/5core/last_out/Electronics.valid.csv.gz  5core/Electronics.valid.csv.gz"
  "benchmark/5core/last_out/Electronics.test.csv.gz   5core/Electronics.test.csv.gz"
)

for entry in "${FILES[@]}"; do
    read -r src dst <<< "$entry"
    if gcloud storage ls "$BUCKET/$dst" > /dev/null 2>&1; then
        echo "skip  $dst (already in bucket)"
        continue
    fi
    echo "copy  $src -> $BUCKET/$dst"
    start=$(date +%s)
    curl -sSfL "$DATA_URL/$src" | gcloud storage cp - "$BUCKET/$dst"
    echo "      done in $(( $(date +%s) - start ))s"
done

gcloud storage ls -l "$BUCKET/raw/" "$BUCKET/5core/"
echo "==> Next: bash cluster_create.sh"
