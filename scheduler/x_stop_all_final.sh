#!/bin/bash
# 停止所有服务
echo "=== [1] 停止 Superset ==="
PIDS=$(ps aux | grep -E "superset run|/superset_env/bin/python" | grep -v grep | awk "{print \$2}")
if [ -n "$PIDS" ]; then
  echo "killing: $PIDS"
  kill $PIDS 2>/dev/null
  sleep 3
fi
ps aux | grep -E "superset" | grep -v grep | wc -l | xargs echo "剩余 superset 进程:"

echo
echo "=== [2] 停止 MySQL ==="
sudo service mysql stop 2>&1 | tail -1
sleep 2
if mysqladmin -uroot -p123456 ping 2>/dev/null; then
  echo "MySQL 仍在运行!"
else
  echo "MySQL 已停止"
fi

echo
echo "=== [3] Java 进程检查 ==="
jps 2>/dev/null || echo "无 Java 进程"

echo
echo "=== [4] 关键端口检查 ==="
ss -tlnp 2>/dev/null | grep -E ":8088|:3306|:9000|:9870|:8088" || echo "所有关键端口已释放 (8088/3306/9000)"