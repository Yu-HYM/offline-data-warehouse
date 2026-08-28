#!/usr/bin/env bash
# ==========================================================================
# 每日调度触发器 daily_scheduler.sh [offset_days=0]
# 作用：
#   1) 调 run_pipeline.sh <T-1> 跑昨日离线批处理
#   2) 捕获返回码并邮件告警
#   3) 记录全量 stdout/stderr
# 使用示例（cron）：
#   # 每天凌晨 00:30 跑 T-1 全量 DAG
#   30 0 * * * /opt/script/mall/scheduler/daily_scheduler.sh 1 >> /data/logs/scheduler/cron.log 2>&1
# ==========================================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/scheduler_lib.sh"

OFFSET="${1:-1}"  # 默认跑 T-1

# 目标日期（T - OFFSET）
DT=$(date -d "${OFFSET} day ago" '+%Y-%m-%d')
LOG_DIR="$LOG_HOME/$DT"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily_scheduler.log"

log_info "[daily_scheduler] 触发 dt=${DT} offset=${OFFSET}"
log_info "[daily_scheduler] 完整日志: ${LOG_FILE}"

"$SCRIPT_DIR/run_pipeline.sh" "$DT" >>"$LOG_FILE" 2>&1
rc=$?

if [ $rc -ne 0 ]; then
  log_error "[daily_scheduler] DAG 失败 rc=${rc} dt=${DT}"
  send_alert "CRITICAL" "$DT" "daily_scheduler" "DAG 执行失败 exit_code=${rc}，请查看日志 ${LOG_FILE}"
  exit $rc
fi
log_info "[daily_scheduler] DAG 成功 dt=${DT}"
exit 0
