#!/bin/bash
source /opt/module/superset_env/bin/activate
export SUPERSET_CONFIG_PATH=/opt/module/superset_env/superset_config.py

# 杀可能残留的进程
pkill -f "superset run" 2>/dev/null
sleep 2

# 用 setsid 完全脱离会话启动
mkdir -p /data/logs/superset
setsid nohup superset run -p 8088 --host 0.0.0.0 --with-threads > /data/logs/superset/superset_web.log 2>&1 < /dev/null &
disown
echo "started"

for i in $(seq 1 15); do
  sleep 4
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/login/)
  echo "try ${i}: HTTP ${code}"
  if [ "$code" = "200" ]; then
    echo "=== STARTED ==="
    break
  fi
done