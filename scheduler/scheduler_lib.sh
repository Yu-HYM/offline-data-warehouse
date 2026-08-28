#!/usr/bin/env bash
# ==========================================================================
# 调度工具库 scheduler_lib.sh
# 功能：日志、重试、分布式锁、任务状态落盘、时间工具
# 用法：source /opt/script/mall/scheduler/scheduler_lib.sh
# ==========================================================================

# ---------- 基础配置 ----------
export SCHED_HOME="${SCHED_HOME:-/opt/script/mall/scheduler}"
export LOG_HOME="${LOG_HOME:-/data/logs/scheduler}"
export STATE_HOME="${STATE_HOME:-/data/scheduler/state}"
export LOCK_HOME="${LOCK_HOME:-/data/scheduler/lock}"

mkdir -p "$LOG_HOME" "$STATE_HOME" "$LOCK_HOME"

# ---------- 日志工具 ----------
log_info()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')][INFO] $*"; }
log_warn()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')][WARN] $*" 1>&2; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')][ERROR] $*" 1>&2; }

# 带任务名+dt的日志记录，同时落文件
task_log() {
  local task="$1"; local dt="$2"; local level="$3"; shift 3
  local log_dir="$LOG_HOME/$dt"
  mkdir -p "$log_dir"
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')][${level}][${task}] $*"
  case "$level" in
    INFO)  echo  "$msg" ;;
    WARN)  echo  "$msg" 1>&2 ;;
    ERROR) echo  "$msg" 1>&2 ;;
  esac
  echo "$msg" >> "$log_dir/${task}.log"
}

# ---------- 秒表 ----------
start_ts=""
timer_start() { start_ts=$(date +%s); }
timer_stop()  {
  local end_ts=$(date +%s)
  local diff=$((end_ts - start_ts))
  printf "%02d:%02d:%02d" $((diff/3600)) $(((diff%3600)/60)) $((diff%60))
}

# ---------- 分布式锁（WSL 单节点用 flock，多节点换 ZK/Redis） ----------
acquire_lock() {
  local lock_name="$1"
  local timeout_sec="${2:-600}"
  local lock_file="$LOCK_HOME/${lock_name}.lock"
  exec 9>>"$lock_file"
  if ! flock -w "$timeout_sec" 9; then
    log_error "获取锁失败: $lock_name (${timeout_sec}s 超时)"
    return 1
  fi
  log_info "获取锁成功: $lock_name"
  return 0
}
release_lock() {
  exec 9>&- 2>/dev/null || true
}

# ---------- 任务状态落盘（JSONL，可被监控读取） ----------
# state: NEW/RUNNING/SUCCESS/FAILED/SKIPPED/RETRY
write_state() {
  local task="$1"; local dt="$2"; local state="$3"
  local extra="${4:-{}}"
  local state_dir="$STATE_HOME/$dt"
  mkdir -p "$state_dir"
  local ts=$(date '+%Y-%m-%d %H:%M:%S')
  local line
  line=$(printf '{"ts":"%s","dt":"%s","task":"%s","state":"%s","extra":%s}' \
    "$ts" "$dt" "$task" "$state" "$extra")
  echo "$line" >> "$state_dir/${task}.state.jsonl"
  echo "$line" > "$state_dir/${task}.state.latest.json"
}

read_latest_state() {
  local task="$1"; local dt="$2"
  local latest="$STATE_HOME/$dt/${task}.state.latest.json"
  [ -f "$latest" ] && cat "$latest" || echo '{"state":"NEW"}'
}

is_task_success() {
  local task="$1"; local dt="$2"
  local s
  s=$(read_latest_state "$task" "$dt" | grep -oE '"state":"[^"]+"' | head -1 | cut -d'"' -f4)
  [ "$s" = "SUCCESS" ]
}

# ---------- 带重试的命令执行 ----------
# run_with_retry <task_name> <dt> <max_retry> <cmd...>
run_with_retry() {
  local task="$1"; local dt="$2"; local max_retry="$3"; shift 3
  local cmd="$*"
  local backoff=(10 30 60 120 300)
  local attempt=0
  write_state "$task" "$dt" "NEW" "{\"cmd\":\"${cmd//\"/\\\\\\\"}\"}"

  while [ $attempt -le "$max_retry" ]; do
    write_state "$task" "$dt" "RUNNING" "{\"attempt\":$((attempt+1))}"
    task_log "$task" "$dt" "INFO" "第 $((attempt+1)) 次执行: $cmd"
    timer_start
    local rc=0
    (eval "$cmd") 2>>"$LOG_HOME/$dt/${task}.log" >>"$LOG_HOME/$dt/${task}.log"
    rc=$?
    local dur
    dur=$(timer_stop)
    if [ $rc -eq 0 ]; then
      task_log "$task" "$dt" "INFO" "执行成功 耗时=${dur} rc=${rc}"
      write_state "$task" "$dt" "SUCCESS" "{\"attempt\":$((attempt+1)),\"duration\":\"${dur}\",\"rc\":$rc}"
      return 0
    fi
    task_log "$task" "$dt" "ERROR" "执行失败 耗时=${dur} rc=${rc} attempt=$((attempt+1))"
    if [ $attempt -lt "$max_retry" ]; then
      local sleep_sec="${backoff[$attempt]:-300}"
      write_state "$task" "$dt" "RETRY" "{\"attempt\":$((attempt+1)),\"rc\":$rc,\"sleep\":$sleep_sec}"
      task_log "$task" "$dt" "WARN" "等待 ${sleep_sec}s 后重试..."
      sleep "$sleep_sec"
    fi
    attempt=$((attempt + 1))
  done

  write_state "$task" "$dt" "FAILED" "{\"attempt\":${attempt},\"rc\":-1}"
  task_log "$task" "$dt" "ERROR" "达到最大重试次数 (${max_retry}) 仍失败"
  return 1
}

# ---------- 幂等跳过工具 ----------
skip_if_success() {
  local task="$1"; local dt="$2"
  if is_task_success "$task" "$dt"; then
    task_log "$task" "$dt" "INFO" "任务已成功，幂等跳过"
    write_state "$task" "$dt" "SKIPPED" "{\"reason\":\"idempotent\"}"
    return 0
  fi
  return 1
}

# ---------- 校验参数 ----------
validate_dt() {
  local dt="$1"
  if [[ ! "$dt" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    log_error "日期格式错误: $dt，需要 YYYY-MM-DD"
    return 1
  fi
  return 0
}

# ---------- 告警派发（默认 mail_alert.sh，未配置则只打日志） ----------
send_alert() {
  local level="$1"; local dt="$2"; local task="$3"; shift 3
  local msg="$*"
  local alert_script="$SCHED_HOME/mail_alert.sh"
  if [ -x "$alert_script" ]; then
    "$alert_script" "$level" "$dt" "$task" "$msg" >/dev/null 2>&1 || \
      log_warn "告警脚本执行失败，已降级为日志输出"
  else
    log_warn "告警脚本未配置/不可执行: $alert_script，仅打印日志"
  fi
  task_log "ALERT" "$dt" "ERROR" "[${level}] task=${task} msg=${msg}"
}
