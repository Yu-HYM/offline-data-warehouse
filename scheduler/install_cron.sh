#!/usr/bin/env bash
# ==========================================================================
# install_cron.sh  : 把每日调度装到 crontab（幂等，重复执行不会重复添加）
# ==========================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_LINE="30 0 * * * /bin/bash ${SCRIPT_DIR}/daily_scheduler.sh 1 >> /data/logs/scheduler/cron.log 2>&1"
mkdir -p /data/logs/scheduler

if crontab -l 2>/dev/null | grep -Fq "daily_scheduler.sh"; then
  echo "[install_cron] 已存在，跳过"
else
  ( crontab -l 2>/dev/null; echo "# Offline DW daily scheduler - T-1 at 00:30"; echo "$CRON_LINE" ) | crontab -
  echo "[install_cron] 已安装:"
  crontab -l | grep -E "daily_scheduler|Offline DW"
fi
