#!/usr/bin/env bash
# ==========================================================================
# 单天 DAG 调度入口：run_pipeline.sh <dt> [--skip-mock] [--force]
# DAG 拓扑：
#   mock_data -> ods_sync -> dwd_process -> dws_prepare -> dws_load_orc
#       -> ads_hive(trade_stats) + ads_py(repurchase+rfm) -> ads_to_mysql
# ==========================================================================
set -u
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/scheduler_lib.sh"

SCRIPT_MOCK="/opt/script/mall/mock/mock_data.py"
SCRIPT_BATCH_SYNC="/opt/script/mall/datax/batch_sync.py"
SCRIPT_DWD_ETL="/opt/script/mall/dwd/dwd_etl.py"
SCRIPT_PREPARE_DWS="/opt/script/mall/dws_orc/prepare_dws_data.py"
SCRIPT_LOAD_DWS="/opt/script/mall/dws_orc/load_dws.py"
SCRIPT_PROCESS_ADS="/opt/script/mall/ads/process_ads.py"
SCRIPT_ADS_PY="/opt/script/mall/ads/ads_etl_py.py"
SCRIPT_EXPORT_ADS="/opt/script/mall/ads/export_ads_to_mysql.py"

DT="${1:-}"
SKIP_MOCK=0
FORCE=0
shift $(( $# > 0 ? 1 : 0 ))
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-mock) SKIP_MOCK=1 ;;
    --force)     FORCE=1 ;;
    *) log_warn "unknown arg: $1" ;;
  esac
  shift
done

if [ -z "$DT" ]; then
  echo "Usage: $0 <YYYY-MM-DD> [--skip-mock] [--force]"
  exit 1
fi
validate_dt "$DT" || exit 1

PIPELINE_TASK="pipeline_mall_${DT//-/}"
MAX_RETRY=2

log_info "========== Offline DW DAG Start =========="
log_info "DT=$DT SKIP_MOCK=$SKIP_MOCK FORCE=$FORCE"

if ! acquire_lock "$PIPELINE_TASK" 30; then
  log_error "DAG $DT already running"
  exit 2
fi

if [ "$FORCE" -eq 1 ]; then
  log_warn "--force: clear state for $DT"
  find "$STATE_HOME/$DT" -type f 2>/dev/null -delete || true
fi

fail_exit() {
  local task="$1"; local msg="$2"
  log_error "DAG FAILED task=$task msg=$msg"
  send_alert "CRITICAL" "$DT" "$task" "$msg"
  write_state "pipeline" "$DT" "FAILED" "{\"failed_task\":\"${task}\"}"
  release_lock; exit 10
}

dag_step() {
  local task="$1"; shift
  local cmd="$*"
  if [ "$FORCE" -ne 1 ] && skip_if_success "$task" "$DT"; then
    return 0
  fi
  if ! run_with_retry "$task" "$DT" "$MAX_RETRY" "$cmd"; then
    fail_exit "$task" "retry=${MAX_RETRY} exhausted"
  fi
}

export JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64"
export HADOOP_HOME="/opt/module/hadoop-3.3.6"
export HIVE_HOME="/opt/module/apache-hive-3.1.3-bin"
export PATH="$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$HIVE_HOME/bin:$PATH"
export HADOOP_CLASSPATH="$($HADOOP_HOME/bin/hadoop classpath)"

pipeline_timer_start=$(date +%s)
write_state "pipeline" "$DT" "RUNNING"

# STEP1 mock
if [ "$SKIP_MOCK" -eq 0 ]; then
  dag_step "01_mock_data" "python3 '$SCRIPT_MOCK' day"
else
  write_state "01_mock_data" "$DT" "SKIPPED" "{}"
fi
# STEP2 ods
dag_step "02_ods_sync" "python3 '$SCRIPT_BATCH_SYNC' '$DT' '$DT'"
# STEP3 dwd
dag_step "03_dwd_etl" "python3 '$SCRIPT_DWD_ETL' '$DT'"
# STEP4 dws prepare
dag_step "04_dws_prepare" "python3 '$SCRIPT_PREPARE_DWS' '$DT'"
# STEP5 dws load orc
dag_step "05_dws_load_orc" "python3 '$SCRIPT_LOAD_DWS' '$DT'"
# STEP6 ads trade_stats
dag_step "06_ads_trade_stats" "python3 '$SCRIPT_PROCESS_ADS' '$DT'"
# STEP7 ads complex (repurchase + rfm)
dag_step "07_ads_complex_py" "python3 '$SCRIPT_ADS_PY' '$DT'"
# STEP8 ads -> mysql
dag_step "08_ads_export_mysql" "python3 '$SCRIPT_EXPORT_ADS' '$DT'"
# STEP9 verify
verify_rows() {
  local info
  info=$(python3 - "$DT" <<'PYEOF'
import pymysql, sys
dt = sys.argv[1]
conn = pymysql.connect(host='localhost', port=3306, user='root', password='123456', database='mall_ads', charset='utf8mb4')
cur = conn.cursor()
qs = [("ads_trade_stats", f"SELECT gmv,order_count FROM ads_trade_stats WHERE dt='{dt}'"),
      ("ads_repurchase_rate", f"SELECT order_user_count,repurchase_rate FROM ads_repurchase_rate WHERE dt='{dt}'"),
      ("ads_user_rfm", f"SELECT COUNT(*) FROM ads_user_rfm WHERE dt='{dt}'")]
out=[]
for t,q in qs:
    cur.execute(q)
    out.append(f"{t}:{cur.fetchall()}")
cur.close(); conn.close()
print(" | ".join(out))
PYEOF
)
  task_log "09_verify" "$DT" "INFO" "verify: $info"
}
verify_rows

dur_sec=$(( $(date +%s) - pipeline_timer_start ))
dur_fmt=$(printf "%02d:%02d:%02d" $((dur_sec/3600)) $(((dur_sec%3600)/60)) $((dur_sec%60)))
write_state "pipeline" "$DT" "SUCCESS" "{\"duration\":\"${dur_fmt}\"}"
log_info "========== DAG OK  duration=${dur_fmt} dt=${DT} =========="
release_lock
exit 0
