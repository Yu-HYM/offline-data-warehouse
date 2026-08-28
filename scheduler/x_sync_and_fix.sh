#!/usr/bin/env bash
# sync + fix + run in WSL
set -e
WIN_S=/mnt/e/????/01-??????/scheduler
for f in scheduler_lib.sh run_pipeline.sh daily_scheduler.sh mail_alert.sh install_cron.sh; do
  d=/opt/script/mall/scheduler/$f
  cp "$WIN_S/$f" "$d"
done
# Strip any CR and chmod
cd /opt/script/mall/scheduler
for f in *.sh *.txt; do
  [ -f "$f" ] || continue
  if grep -q $'\r' "$f" 2>/dev/null; then
    sed -i "s/\r//" "$f"
  fi
done
chmod +x /opt/script/mall/scheduler/*.sh
# check format
echo "--- file formats ---"
for f in scheduler_lib.sh run_pipeline.sh daily_scheduler.sh mail_alert.sh install_cron.sh; do
  file "/opt/script/mall/scheduler/$f"
done
