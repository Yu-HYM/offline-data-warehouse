#!/usr/bin/env bash
source /etc/profile 2>/dev/null; source ~/.profile 2>/dev/null
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
export PATH="$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$PATH"

echo "--- 1) ???????? ---"
for p in \
  /opt/script/mall/dws_orc/prepare_dws_data.py \
  /opt/script/mall/dws_orc/load_dws.py \
  /opt/script/mall/ads/process_ads.py \
  /opt/script/mall/ads/ads_etl_py.py \
  /opt/script/mall/ads/export_ads_to_mysql.py \
  /opt/script/mall/datax/batch_sync.py \
  /opt/script/mall/scheduler/run_pipeline.sh; do
  [ -f "$p" ] && echo "OK   $p" || echo "MISS $p"
done

echo
echo "--- 2) Hive DWS/ADS ORC ?????? ---"
hive -S -e 'USE mall; SHOW TABLES LIKE "dws_trade%"; SHOW TABLES LIKE "ads%";' 2>&1
