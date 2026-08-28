#!/bin/bash
CRON_LINE='30 0 * * * /bin/bash /opt/script/mall/scheduler/daily_scheduler.sh 1 >> /data/logs/scheduler/cron.log 2>&1'
if crontab -l 2>/dev/null | grep -q "daily_scheduler.sh"; then
  echo "已存在 cron 条目"
else
  ( crontab -l 2>/dev/null
    echo "# Offline DW daily scheduler - T-1 at 00:30"
    echo "$CRON_LINE" ) | crontab -
fi
echo "--- 当前 crontab 列表 ---"
crontab -l