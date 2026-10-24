#!/usr/bin/env bash
# Everyday helper for the big data stack (run inside Ubuntu after setup_bigdata.sh).
#
#   ~/bigdata/bigdata.sh start      start HDFS (NameNode + DataNode)
#   ~/bigdata/bigdata.sh stop       stop HDFS
#   ~/bigdata/bigdata.sh status     show running Java services and HDFS space
#   ~/bigdata/bigdata.sh check      full test: HDFS write/read + Spark + a Hive table on HDFS
#   ~/bigdata/bigdata.sh download   download the Electronics files (7.8 GB, resumes if interrupted)
set -euo pipefail
# shellcheck disable=SC1091
source "$HOME/bigdata/env.sh"

say() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

start_hdfs() {
    if jps | grep -q NameNode; then echo "HDFS already running"; return; fi
    hdfs --daemon start namenode
    hdfs --daemon start datanode
    sleep 5
    hdfs dfsadmin -safemode wait > /dev/null
    hdfs dfs -mkdir -p /user/hive/warehouse /amazon
    echo "HDFS running - web UI: http://localhost:9870"
}

stop_hdfs() {
    hdfs --daemon stop datanode || true
    hdfs --daemon stop namenode || true
    echo "HDFS stopped"
}

case "${1:-}" in
  start)  start_hdfs ;;
  stop)   stop_hdfs ;;
  status)
    jps | grep -E "NameNode|DataNode" || echo "HDFS is not running (use: bigdata.sh start)"
    hdfs dfs -df -h / 2>/dev/null || true
    ;;
  check)
    say "Starting HDFS"
    start_hdfs
    say "HDFS write / read"
    echo "hello from hdfs $(date)" > /tmp/hdfs_check.txt
    hdfs dfs -put -f /tmp/hdfs_check.txt /tmp_check.txt
    hdfs dfs -cat /tmp_check.txt
    hdfs dfs -rm -skipTrash /tmp_check.txt > /dev/null
    say "Spark + Hive table stored on HDFS"
    python - <<'PY'
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("check").master("local[*]").enableHiveSupport().getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
spark.sql("CREATE DATABASE IF NOT EXISTS amazon")
spark.range(1000).selectExpr("id", "id % 5 + 1 AS rating").write.mode("overwrite").saveAsTable("amazon.check_table")
print(spark.sql("SELECT rating, COUNT(*) AS n FROM amazon.check_table GROUP BY rating ORDER BY rating").toPandas())
loc = spark.sql("DESCRIBE FORMATTED amazon.check_table").filter("col_name = 'Location'").first()["data_type"]
print("table stored at:", loc)
spark.sql("DROP TABLE amazon.check_table")
print("Spark", spark.version, "- Hive tables on HDFS work")
spark.stop()
PY
    say "All checks passed"
    ;;
  download)
    mkdir -p "$BIG/data"
    cd "$BIG/data"
    base=https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw
    wget -c -q --show-progress "$base/review_categories/Electronics.jsonl.gz"
    wget -c -q --show-progress "$base/meta_categories/meta_Electronics.jsonl.gz"
    ls -lh "$BIG/data"
    ;;
  *)
    sed -n '2,10p' "$0"
    ;;
esac
