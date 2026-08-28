#!/usr/bin/env bash
# WSL ?????? + ????2026-08-21?
source /etc/profile 2>/dev/null; source ~/.profile 2>/dev/null
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
export PATH="$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$PATH"

DT=2026-08-21
echo "=== [1/3] mall ??????? & ?? $DT ??? ==="
mysql -uroot -p123456 mall -N -B -e "SELECT MAX(DATE(create_time)) AS max_dt, SUM(DATE(create_time)='$DT') AS cnt_20260821 FROM order_info;" 2>/dev/null

echo
echo "=== [2/3] mock_data.py day -> ?? $DT ?? ==="
python3 /opt/script/mall/mock/mock_data.py day 2>&1 | tail -10

echo
echo "=== [3/3] ???? $DT ??? ==="
mysql -uroot -p123456 mall -N -B -e "SELECT COUNT(*) FROM order_info WHERE DATE(create_time)='$DT';" 2>/dev/null
