#!/bin/bash
source /opt/module/superset_env/bin/activate
export SUPERSET_CONFIG_PATH=/opt/module/superset_env/superset_config.py

echo "=== 补装 cachetools ==="
pip install cachetools -i https://mirrors.aliyun.com/pypi/simple/ 2>&1 | tail -1

echo "=== 杀旧进程 ==="
kill $(cat /tmp/superset.pid 2>/dev/null) 2>/dev/null
sleep 2

echo "=== 重启 Superset ==="
nohup superset run -p 8088 --host 0.0.0.0 --with-threads > /data/logs/superset/superset_web.log 2>&1 &
echo "NEW_PID=$!"
echo $! > /tmp/superset.pid

for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  sleep 5
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/login/)
  echo "try ${i}: HTTP ${code}"
  if [ "$code" = "200" ]; then
    echo "=== STARTED ==="
    break
  fi
done
tail -5 /data/logs/superset/superset_web.log