#!/bin/bash
source /opt/module/superset_env/bin/activate
cp "/mnt/e/简历项目/01-离线数仓项目/verify_superset.py" /tmp/verify_superset.py
tr -d '\r' < /tmp/verify_superset.py > /tmp/v2.py && mv /tmp/v2.py /tmp/verify_superset.py
python3 /tmp/verify_superset.py