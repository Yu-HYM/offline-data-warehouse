#!/bin/bash
source /opt/module/superset_env/bin/activate
export SUPERSET_CONFIG_PATH=/opt/module/superset_env/superset_config.py

# 后台启动 Superset Web 服务（8088 端口）
mkdir -p /data/logs/superset
nohup superset run -p 8088 --host 0.0.0.0 --with-threads > /data/logs/superset/superset_web.log 2>&1 &
echo "SUPerset PID=$!"
echo $! > /tmp/superset.pid

# 等待启动
for i in $(seq 1 12); do
  sleep 5
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/login/ | grep -q 200; then
    echo "=== Superset 已启动 (after $((i*5))s) ==="
    curl -s -o /dev/null -w "login page HTTP %{http_code}\n" http://localhost:8088/login/
    break
  fi
  echo "waiting... ${i}x5s"
done
tail -5 /data/logs/superset/superset_web.log