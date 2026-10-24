#!/usr/bin/env bash
# Phase 5 - one-time setup of the big data stack inside Ubuntu (WSL2).
#
# Installs:  Java 17, Hadoop 3.3.6 (HDFS, pseudo-distributed, replication 1),
#            PySpark 3.5.3 with Hive support (metastore kept in ~/bigdata/metastore_db),
#            a Python virtual environment with pandas / pyarrow.
#
# Run inside Ubuntu:   bash /mnt/d/PROJECTS/BIG_DATA_project/scripts/wsl/setup_bigdata.sh
# Safe to run again: finished steps are skipped.
set -euo pipefail

BIG="$HOME/bigdata"
HADOOP_VERSION=3.3.6
HADOOP_HOME="$BIG/hadoop-$HADOOP_VERSION"
JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

say() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
mkdir -p "$BIG"/{downloads,hdfs/namenode,hdfs/datanode,spark-conf,spark-tmp,data,results}

say "1/6  Ubuntu packages (Java 17, Python venv) - asks for your Ubuntu password"
sudo apt-get update -qq
sudo apt-get install -y -qq openjdk-17-jdk-headless python3-venv python3-pip wget curl unzip > /dev/null
java -version 2>&1 | head -1

say "2/6  Hadoop $HADOOP_VERSION (about 700 MB download, resumes if interrupted)"
if [ ! -d "$HADOOP_HOME" ]; then
    cd "$BIG/downloads"
    TAR="hadoop-$HADOOP_VERSION.tar.gz"
    wget -c -q --show-progress "https://dlcdn.apache.org/hadoop/common/hadoop-$HADOOP_VERSION/$TAR" \
        || wget -c -q --show-progress "https://archive.apache.org/dist/hadoop/common/hadoop-$HADOOP_VERSION/$TAR"
    tar -xzf "$TAR" -C "$BIG"
    rm -f "$TAR"
fi
echo "Hadoop at $HADOOP_HOME"

say "3/6  Hadoop configuration (single node, replication 1)"
cat > "$HADOOP_HOME/etc/hadoop/core-site.xml" <<EOF
<?xml version="1.0"?>
<configuration>
  <property><name>fs.defaultFS</name><value>hdfs://localhost:9000</value></property>
  <property><name>hadoop.tmp.dir</name><value>$BIG/hdfs/tmp</value></property>
</configuration>
EOF
cat > "$HADOOP_HOME/etc/hadoop/hdfs-site.xml" <<EOF
<?xml version="1.0"?>
<configuration>
  <property><name>dfs.replication</name><value>1</value></property>
  <property><name>dfs.namenode.name.dir</name><value>file://$BIG/hdfs/namenode</value></property>
  <property><name>dfs.datanode.data.dir</name><value>file://$BIG/hdfs/datanode</value></property>
  <property><name>dfs.permissions.enabled</name><value>false</value></property>
</configuration>
EOF
grep -q "^export JAVA_HOME=$JAVA_HOME" "$HADOOP_HOME/etc/hadoop/hadoop-env.sh" \
    || echo "export JAVA_HOME=$JAVA_HOME" >> "$HADOOP_HOME/etc/hadoop/hadoop-env.sh"

say "4/6  Python environment with PySpark 3.5.3 (about 320 MB download)"
if [ ! -x "$BIG/venv/bin/python" ]; then
    python3 -m venv "$BIG/venv"
fi
"$BIG/venv/bin/pip" install -q --upgrade pip
"$BIG/venv/bin/pip" install -q "pyspark==3.5.3" "pandas>=2.0" "pyarrow>=14" "numpy>=1.24"
"$BIG/venv/bin/python" -c "import pyspark; print('pyspark', pyspark.__version__)"

say "5/6  Spark defaults (HDFS warehouse for Hive tables, fixed metastore location)"
cat > "$BIG/spark-conf/spark-defaults.conf" <<EOF
spark.sql.warehouse.dir                              hdfs://localhost:9000/user/hive/warehouse
spark.sql.catalogImplementation                      hive
spark.hadoop.javax.jdo.option.ConnectionURL          jdbc:derby:;databaseName=$BIG/metastore_db;create=true
spark.local.dir                                      $BIG/spark-tmp
spark.driver.memory                                  8g
spark.sql.shuffle.partitions                         32
spark.ui.showConsoleProgress                         true
EOF
cat > "$BIG/env.sh" <<EOF
# loaded by ~/.bashrc - big data environment
export JAVA_HOME=$JAVA_HOME
export HADOOP_HOME=$HADOOP_HOME
export HADOOP_CONF_DIR=\$HADOOP_HOME/etc/hadoop
export SPARK_CONF_DIR=$BIG/spark-conf
export PYSPARK_PYTHON=$BIG/venv/bin/python
export PATH=$BIG/venv/bin:\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin:\$PATH
export PROJECT=/mnt/d/PROJECTS/BIG_DATA_project
export BIG=$BIG
EOF
grep -q "bigdata/env.sh" "$HOME/.bashrc" || echo "source $BIG/env.sh" >> "$HOME/.bashrc"
# shellcheck disable=SC1091
source "$BIG/env.sh"

say "6/6  Format HDFS (only the first time)"
if [ ! -d "$BIG/hdfs/namenode/current" ]; then
    hdfs namenode -format -nonInteractive -force > "$BIG/hdfs/format.log" 2>&1
    echo "HDFS formatted"
else
    echo "HDFS already formatted - skipped"
fi

cp "$(dirname "$0")/bigdata.sh" "$BIG/bigdata.sh"
chmod +x "$BIG/bigdata.sh"

say "Setup finished. Next:  source ~/.bashrc  &&  ~/bigdata/bigdata.sh check"
