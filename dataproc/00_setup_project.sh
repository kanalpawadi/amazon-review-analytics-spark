#!/usr/bin/env bash
# One-time project setup (run in Cloud Shell): turn on the APIs, create the storage bucket,
# and give the cluster's service account the roles Dataproc needs.
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

echo "Project: $PROJECT_ID   Region: $REGION   Bucket: $BUCKET"

echo "==> Enabling APIs (takes 1-2 minutes the first time)"
gcloud services enable dataproc.googleapis.com compute.googleapis.com storage.googleapis.com

echo "==> Creating bucket $BUCKET"
if gcloud storage buckets describe "$BUCKET" > /dev/null 2>&1; then
    echo "bucket already exists"
else
    gcloud storage buckets create "$BUCKET" --location="$REGION" --uniform-bucket-level-access
fi

echo "==> Giving the default compute service account the Dataproc worker + storage roles"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for role in roles/dataproc.worker roles/storage.objectAdmin; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA" \
        --role="$role" --condition=None --quiet > /dev/null
    echo "  $role -> $SA"
done

echo "==> Done. Next: bash 01_download_to_gcs.sh"
