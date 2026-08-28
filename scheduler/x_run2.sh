#!/bin/bash
source /etc/profile 2>/dev/null
source ~/.profile 2>/dev/null
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=/opt/module/hadoop-3.3.6
export HIVE_HOME=/opt/module/apache-hive-3.1.3-bin
P=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$P
LOG=/data/logs/scheduler/pipeline_2026-08-21.out
rm -f "$LOG" /tmp/pipeline.pid
echo "Starting DAG for 2026-08-21..."
nohup /opt/script/mall/scheduler/run_pipeline.sh 2026-08-21 --skip-mock --force > "$LOG" 2>&1 &
PID=$!
echo $PID > /tmp/pipeline.pid
echo "Pipeline PID=$PID, log=$LOG"
for round in 1 2 3 4 5 6; do
  sleep 20
  if ! kill -0 $PID 2>/dev/null; then
    echo "===== round ${round}: process $PID exited ====="
    tail -40 $LOG
    break
  fi
  echo "===== round ${round}: still running (PID $PID) ====="
  tail -10 $LOG
done
echo "--- final state files ---"
ls /data/scheduler/state/2026-08-21/ 2>/dev/null || true