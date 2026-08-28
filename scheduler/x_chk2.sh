#!/bin/bash
LOG=/data/logs/scheduler/pipeline_2026-08-21.out
echo "--- tail 80 lines ---"
tail -80 $LOG
echo
echo "--- latest pipeline state ---"
cat /data/scheduler/state/2026-08-21/pipeline.state.latest.json 2>/dev/null
echo
echo "--- 08 state ---"
cat /data/scheduler/state/2026-08-21/08_ads_export_mysql.state.latest.json 2>/dev/null
echo
echo "--- 09 state ---"
ls /data/scheduler/state/2026-08-21/ | sort
echo
echo "--- latest 07 state ---"
cat /data/scheduler/state/2026-08-21/07_ads_complex_py.state.latest.json 2>/dev/null