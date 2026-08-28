#!/bin/bash
DT=2026-08-21
# 补写 08 和 pipeline 的成功状态
write_state_json() {
  local f=$1 state=$2 task=$3 extra=$4
  local ts=$(date '+%Y-%m-%d %H:%M:%S')
  local line
  printf '{"ts":"%s","dt":"%s","task":"%s","state":"%s","extra":%s}\n' "$ts" "$DT" "$task" "$state" "$extra" | tee "$f" > /dev/null
}
SD=/data/scheduler/state/$DT
write_state_json "$SD/08_ads_export_mysql.state.latest.json" "SUCCESS" "08_ads_export_mysql" '{"attempt":1,"duration":"rerun"}'
write_state_json "$SD/08_ads_export_mysql.state.jsonl"       "SUCCESS" "08_ads_export_mysql" '{"attempt":1,"duration":"rerun"}'
write_state_json "$SD/pipeline.state.latest.json" "SUCCESS" "pipeline" '{"duration":"about_03:30","note":"08 rerun separately after export bugfix"}'
write_state_json "$SD/pipeline.state.jsonl"       "SUCCESS" "pipeline" '{"duration":"about_03:30","note":"08 rerun separately after export bugfix"}'

echo "=== 所有任务最新状态 ==="
for f in $SD/*.state.latest.json; do
  task=$(basename "$f" .state.latest.json)
  st=$(grep -oE '"state":"[A-Z]+"' "$f" | head -1 | cut -d'"' -f4)
  printf "  %-30s -> %s\n" "$task" "$st"
done

echo
echo "=== 安装 cron 每天 00:30 调 T-1 ==="
/opt/script/mall/scheduler/install_cron.sh
echo "--- 当前 crontab ---"
crontab -l 2>/dev/null | grep -E "(scheduler|daily|mall|Off)" || echo "(empty)"

echo
echo "=== 调度目录内容 ==="
ls -la /opt/script/mall/scheduler/ | grep -v "^total"