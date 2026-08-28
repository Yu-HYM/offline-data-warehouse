#!/bin/bash
echo "--- 系统依赖检查 ---"
dpkg -l 2>/dev/null | grep -E "python3-dev|default-libmysqlclient|build-essential|libssl-dev|pkg-config" | awk "{print \$2}" | head -10
echo "--- venv ---"
python3 -c "import venv; print('venv OK')" 2>&1
echo "--- 磁盘 ---"
df -h / | tail -1
echo "--- pip 源（国内加速）---"
pip3 config list 2>/dev/null || echo "no pip config"
cat ~/.pip/pip.conf 2>/dev/null || cat /etc/pip.conf 2>/dev/null || echo "no pip.conf"