#!/usr/bin/env bash
# Create the Hadoop / Spark / Hive cluster. It COSTS MONEY while it exists:
# delete it with  bash cluster_delete.sh  when you finish (it also self-deletes after 30 idle minutes).
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

echo "Creating $CLUSTER: 1 x $MASTER_TYPE master + $NUM_WORKERS x $WORKER_TYPE workers (image $IMAGE)"
gcloud dataproc clusters create "$CLUSTER" \
    --region="$REGION" --zone="$ZONE" \
    --image-version="$IMAGE" \
    --master-machine-type="$MASTER_TYPE" --master-boot-disk-size=50GB \
    --num-workers="$NUM_WORKERS" --worker-machine-type="$WORKER_TYPE" --worker-boot-disk-size=80GB \
    --max-idle="$MAX_IDLE" --max-age="$MAX_AGE" \
    --enable-component-gateway \
    --properties="dfs:dfs.replication=2,spark:spark.sql.shuffle.partitions=48"

echo
echo "Cluster ready. Web pages (HDFS NameNode, YARN, Spark History):"
echo "  Console -> Dataproc -> Clusters -> $CLUSTER -> Web Interfaces"
echo "Next: bash run_ingest.sh"
