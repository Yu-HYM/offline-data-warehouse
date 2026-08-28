#!/bin/bash
source /opt/module/superset_env/bin/activate
export SUPERSET_CONFIG_PATH=/opt/module/superset_env/superset_config.py
cp "/mnt/e/简历项目/01-离线数仓项目/setup_superset_datasource.py" /tmp/setup_superset.py
tr -d '\r' < /tmp/setup_superset.py > /tmp/s2.py && mv /tmp/s2.py /tmp/setup_superset.py
python3 /tmp/setup_superset.py 2>&1 | grep -E "^\[|已|===|访问|Error|Traceback" | head -25