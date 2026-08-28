#!/bin/bash
echo "--- DNS ---"
nslookup pypi.tuna.tsinghua.edu.cn 2>&1 | tail -3
echo "--- HTTPS 清华源 ---"
curl -sI --max-time 10 https://pypi.tuna.tsinghua.edu.cn/simple/ 2>&1 | head -3
echo "--- HTTPS pypi.org ---"
curl -sI --max-time 10 https://pypi.org/simple/ 2>&1 | head -3
echo "--- pip 详细错误 ---"
/opt/module/superset_env/bin/pip download wheel -d /tmp/piptest -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir 2>&1 | tail -6