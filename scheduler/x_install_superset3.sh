#!/bin/bash
set -x
source /opt/module/superset_env/bin/activate
pip install --upgrade pip wheel setuptools 2>&1 | tail -2
pip --version

echo "=== 安装 apache-superset（官方源，时间较长 5-15 分钟）==="
pip install apache-superset pymysql cryptography 2>&1 | tail -6
echo "=== INSTALL DONE ==="
which superset
superset --version 2>&1 | head -3