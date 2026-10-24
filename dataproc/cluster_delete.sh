#!/usr/bin/env bash
# Delete the cluster to stop all charges. Data in the bucket (gs://...) is kept.
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

gcloud dataproc clusters delete "$CLUSTER" --region="$REGION" --quiet
echo "Cluster deleted. Running clusters now:"
gcloud dataproc clusters list --region="$REGION"
