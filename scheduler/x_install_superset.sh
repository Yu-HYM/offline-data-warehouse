#!/bin/bash
set -x
echo "=== [1/3] 安装系统依赖 ==="
sudo apt install -y default-libmysqlclient-dev pkg-config libffi-dev 2>&1 | tail -3

echo "=== [2/3] 创建 venv ==="
python3 -m venv /opt/module/superset_env
source /opt/module/superset_env/bin/activate
pip install --upgrade pip wheel setuptools -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tail -2

echo "=== [3/3] 安装 apache-superset（时间较长）==="
pip install apache-superset pymysql cryptography -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tail -10
echo "=== 安装结束 rc=$? ==="
superset --version