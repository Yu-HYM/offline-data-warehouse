#!/bin/bash
set -e
SRC_DIR=/mnt/e/简历项目/01-离线数仓项目/scheduler
DST_DIR=/opt/script/mall/scheduler
for f in scheduler_lib.sh run_pipeline.sh daily_scheduler.sh mail_alert.sh install_cron.sh README_scheduler.txt; do
  cp "$SRC_DIR/$f" "$DST_DIR/$f"
done
cd $DST_DIR
for f in *.sh *.txt; do
  test -f "$f" || continue
  if head -c 3 "$f" | grep -q $'\xef\xbb\xbf'; then
    tail -c +4 "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
  fi
  tr -d '\r' < "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
done
chmod +x $DST_DIR/*.sh
for f in scheduler_lib.sh run_pipeline.sh daily_scheduler.sh mail_alert.sh install_cron.sh; do
  file "$DST_DIR/$f"
done