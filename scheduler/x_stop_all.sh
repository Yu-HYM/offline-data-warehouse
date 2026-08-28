#!/bin/bash
source /etc/profile 2>/dev/null
source ~/.profile 2>/dev/null
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

echo "=== [1/4] jps before stop ==="
jps

echo
echo "=== [2/4] 停止 Hive Metastore/Server2 ==="
# 找 RunJar 的 PID 精确 kill
HIVE_PID=$(jps | grep RunJar | awk "{print \$1}")
if [ -n "$HIVE_PID" ]; then
  echo "killing Hive RunJar PID=$HIVE_PID"
  kill "$HIVE_PID" 2>/dev/null
  sleep 3
  kill -9 "$HIVE_PID" 2>/dev/null
else
  echo "no Hive process"
fi

echo
echo "=== [3/4] 停止 HDFS (stop-dfs.sh) ==="
stop-dfs.sh 2>&1 | tail -8
sleep 2

echo
echo "=== [4/4] 停止 MySQL ==="
sudo service mysql stop 2>&1 | tail -3
sleep 2
mysqladmin -uroot -p123456 ping 2>&1 | tail -2

echo
echo "=== final jps ==="
jps
echo "=== cron 条目（保留，WSL 关闭后不自动触发）==="
crontab -l 2>/dev/null | grep -E "daily_scheduler|Offline" || echo "no cron"