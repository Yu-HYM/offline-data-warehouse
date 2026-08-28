#!/bin/bash
# 验证 Superset: Web存活 + 登录 + 看板列表 + 图表数据查询
BASE=http://localhost:8088

echo "=== [1] Web 存活 ==="
curl -s -o /dev/null -w "login page: HTTP %{http_code}\n" $BASE/login/

echo
echo "=== [2] 登录获取 session ==="
# 获取 CSRF token
TOKEN=$(curl -s -c /tmp/ss_cookie.txt $BASE/api/v1/security/csrf_token/ | grep -oE '"result":"[^"]+"' | cut -d'"' -f4)
echo "csrf_token=${TOKEN:0:20}..."

# 登录
LOGIN_RC=$(curl -s -b /tmp/ss_cookie.txt -c /tmp/ss_cookie.txt \
  -H "X-CSRFToken: $TOKEN" -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123","refresh":true,"provider":"db","events":["login"]}' \
  -w "%{http_code}" -o /tmp/login_resp.txt $BASE/api/v1/security/login)
echo "login: HTTP $LOGIN_RC"
grep -o '"access_token"' /tmp/login_resp.txt >/dev/null && echo "access_token 获取成功"

ACCESS=$(grep -oE '"access_token":"[^"]+"' /tmp/login_resp.txt | cut -d'"' -f4)

echo
echo "=== [3] 看板列表 ==="
curl -s -H "Authorization: Bearer $ACCESS" "$BASE/api/v1/dashboard/" | python3 -c "
import json,sys
d = json.load(sys.stdin)
for r in d.get('result', []):
    print('  dashboard:', r.get('dashboard_title'), '| slug:', r.get('slug'), '| url:', r.get('url'))
" 2>/dev/null || echo "(解析失败)"

echo
echo "=== [4] 图表列表 ==="
curl -s -H "Authorization: Bearer $ACCESS" "$BASE/api/v1/chart/" | python3 -c "
import json,sys
d = json.load(sys.stdin)
for r in d.get('result', []):
    print('  chart:', r.get('slice_name'), '| viz:', r.get('viz_type'))
" 2>/dev/null || echo "(解析失败)"

echo
echo "=== [5] 图表数据查询（GMV 趋势）==="
curl -s -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -X POST "$BASE/api/v1/chart/data" \
  -d '{
    "queries": [{
      "datasource": {"id": 1, "type": "table"},
      "granularity": "dt",
      "groupby": ["dt"],
      "metrics": [{"expressionType":"SIMPLE","column":{"column_name":"gmv","type":"NUMERIC"},"aggregate":"SUM","label":"GMV"}],
      "row_limit": 10,
      "time_range": "100 years : now"
    }]
  }' | python3 -c "
import json,sys
d = json.load(sys.stdin)
res = d.get('result', [])
if res:
    data = res[0].get('data', [])
    print('  查询成功, 返回 %d 行:' % len(data))
    for row in data:
        print('   ', row.get('dt'), '->', row.get('GMV'))
else:
    print('  失败:', json.dumps(d)[:300])
" 2>/dev/null || echo "(请求失败)"