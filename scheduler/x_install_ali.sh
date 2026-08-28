#!/bin/bash
source /opt/module/superset_env/bin/activate
export PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
echo "=== 用阿里源安装 superset ==="
pip install apache-superset pymysql cryptography 2>&1 | tail -8
echo "=== INSTALL_RC=$? ==="
which superset && superset --version 2>&1 | head -3