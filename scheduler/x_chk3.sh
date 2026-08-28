#!/bin/bash
LOG=/data/logs/scheduler/2026-08-21/08_ads_export_mysql.log
echo "--- 08 task log: $LOG ---"
tail -60 $LOG 2>&1
echo
echo "--- pipeline process alive? ---"
if [ -f /tmp/pipeline.pid ]; then
  PID=$(cat /tmp/pipeline.pid)
  if kill -0 $PID 2>/dev/null; then
    echo "alive PID=$PID"
    sleep 30
    echo "=== wait another 30s done ==="
    tail -15 /data/logs/scheduler/pipeline_2026-08-21.out
  else
    echo "dead PID=$PID - check final log"
    tail -20 /data/logs/scheduler/pipeline_2026-08-21.out
  fi
else
  echo "no pid file"
fi