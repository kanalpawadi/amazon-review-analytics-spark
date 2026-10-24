#!/usr/bin/env bash
# Shared settings for every Dataproc script. Edit here only.

PROJECT_ID="$(gcloud config get-value project 2>/dev/null)"
REGION="asia-south1"                 # Mumbai - closest to Maharashtra
ZONE="asia-south1-a"
BUCKET="gs://${PROJECT_ID}-amazon-reviews"
CLUSTER="amazon-cluster"
IMAGE="2.2-debian12"                 # Spark 3.5.3, Hadoop 3.3.6, Hive 3.1.3

# Cluster size. Free-trial accounts cannot raise quotas, so this stays at 8 vCPUs in total:
# 1 master + 3 workers, 2 vCPUs / 8 GB each. If creation fails with a CPUS quota error, set NUM_WORKERS=2.
MASTER_TYPE="n2-standard-2"
WORKER_TYPE="n2-standard-2"
NUM_WORKERS=3

# Safety: the cluster deletes itself after 30 idle minutes, and after 8 hours in any case.
MAX_IDLE="30m"
MAX_AGE="8h"

DATA_URL="https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023"

if [ -z "$PROJECT_ID" ]; then
    echo "No project selected. Run:  gcloud config set project YOUR_PROJECT_ID" >&2
    exit 1
fi
