#!/bin/bash
source /opt/module/superset_env/bin/activate
export SUPERSET_CONFIG_PATH=/opt/module/superset_env/superset_config.py
cp "/mnt/e/简历项目/01-离线数仓项目/setup_superset_datasource.py" /tmp/setup_superset.py
# 去 BOM 和 CR
if head -c 3 /tmp/setup_superset.py | od -An -c | head -1 | grep -q "357 273 277"; then
  tail -c +4 /tmp/setup_superset.py > /tmp/setup_superset.py.tmp && mv /tmp/setup_superset.py.tmp /tmp/setup_superset.py
fi
tr -d '\r' < /tmp/setup_superset.py > /tmp/setup_superset.py.tmp && mv /tmp/setup_superset.py.tmp /tmp/setup_superset.py
python3 /tmp/setup_superset.py 2>&1 | grep -vE "^(WARNING|INFO|DEBUG)" | tail -30