#!/usr/bin/env bash
source /etc/profile 2>/dev/null
source ~/.profile 2>/dev/null
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
P=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$P
LOG=/data/logs/scheduler/pipeline_2026-08-21.out
nohup /opt/script/mall/scheduler/run_pipeline.sh 2026-08-21 --skip-mock --force > $LOG 2>&1 &
echo "PID=$!"
echo $! > /tmp/pipeline.pid
sleep 5
echo "--- head of log ---"
head -20 $LOG
