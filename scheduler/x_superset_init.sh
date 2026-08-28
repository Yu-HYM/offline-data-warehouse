#!/bin/bash
set -e
source /opt/module/superset_env/bin/activate

# 生成 SECRET_KEY 并写配置
SECRET=$(openssl rand -base64 42)
cat > /opt/module/superset_env/superset_config.py <<EOF
# Superset 配置（阶段九）
import os

SECRET_KEY = "${SECRET}"
SQLALCHEMY_DATABASE_URI = "sqlite:////opt/module/superset_env/superset.db"

# 允许的 CSV 上传等基础配置
ENABLE_PROXY_FIX = True
TALISMAN_ENABLED = False

# 时区
DEFAULT_APP_THEME = "light"

# 关闭示例数据加载
LOAD_EXAMPLES = False
EOF

export SUPERSET_CONFIG_PATH=/opt/module/superset_env/superset_config.py
echo "=== [1/3] db upgrade（建元数据库表）==="
superset db upgrade 2>&1 | tail -5

echo
echo "=== [2/3] 创建 admin 账号 ==="
superset fab create-admin --username admin --firstname admin --lastname user --email admin@mall.com --password admin123 2>&1 | tail -3 || true

echo
echo "=== [3/3] superset init（角色权限）==="
superset init 2>&1 | tail -5
echo "=== INIT DONE ==="