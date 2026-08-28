#!/bin/bash
set -x
echo "=== [1/3] 安装 python3.10-venv ==="
sudo apt install -y python3.10-venv 2>&1 | tail -2

echo "=== [2/3] 重建 venv ==="
sudo rm -rf /opt/module/superset_env
sudo mkdir -p /opt/module/superset_env
sudo chown -R $(whoami):$(whoami) /opt/module/superset_env
python3 -m venv /opt/module/superset_env
source /opt/module/superset_env/bin/activate
python -m pip install --upgrade pip wheel setuptools -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tail -2
pip --version

echo "=== [3/3] 安装 apache-superset ==="
pip install apache-superset pymysql cryptography -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tail -8
echo "=== INSTALL_RC=$? ==="
which superset && superset --version