#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_superset.py - 验证 Superset 登录/看板/图表/数据查询"""
import json
import requests

BASE = "http://localhost:8088"
s = requests.Session()

# 1. 登录拿 JWT（该接口本身无需 CSRF）
r = s.post(
    BASE + "/api/v1/security/login",
    json={"username": "admin", "password": "admin123",
          "provider": "db", "refresh": True},
)
print("[1] login HTTP", r.status_code)
access = r.json()["access_token"]
H = {"Authorization": "Bearer " + access}
print("    access_token OK")

# 2. CSRF token（认证后获取，写操作需要）
r = s.get(BASE + "/api/v1/security/csrf_token/", headers=H)
token = r.json().get("result", "")
print("[2] CSRF token OK:", (token[:16] + "...") if token else "(empty)")

# 3. 看板列表
r = s.get(BASE + "/api/v1/dashboard/", headers=H)
for row in r.json()["result"]:
    print("[3] dashboard:", row["dashboard_title"], "| slug:", row["slug"], "| url:", row["url"])

# 4. 图表列表
r = s.get(BASE + "/api/v1/chart/", headers=H)
for row in r.json()["result"]:
    print("[4] chart:", row["slice_name"], "| viz:", row["viz_type"])

# 5. 图表数据查询 GMV
payload = {
    "datasource": {"id": 1, "type": "table"},
    "queries": [{
        "granularity": "dt",
        "groupby": ["dt"],
        "metrics": [{"expressionType": "SIMPLE",
                     "column": {"column_name": "gmv", "type": "NUMERIC"},
                     "aggregate": "SUM", "label": "GMV"}],
        "row_limit": 10,
        "time_range": "100 years ago : now",
    }]
}
H2 = dict(H)
H2["X-CSRFToken"] = token
H2["Referer"] = BASE + "/"
r = s.post(BASE + "/api/v1/chart/data", json=payload, headers=H2)
res = r.json().get("result", [])
if res:
    data = res[0].get("data", [])
    print("[5] GMV 查询成功，%d 行：" % len(data))
    for row in data:
        print("     ", row.get("dt"), "->", row.get("GMV"))
else:
    print("[5] 失败:", json.dumps(r.json())[:300])

# 6. RFM 分群查询
payload2 = {
    "datasource": {"id": 3, "type": "table"},
    "queries": [{
        "groupby": ["rfm_label"],
        "metrics": [{"expressionType": "SIMPLE",
                     "column": {"column_name": "user_id", "type": "TEXT"},
                     "aggregate": "COUNT_DISTINCT", "label": "用户数"}],
        "row_limit": 20,
    }]
}
r = s.post(BASE + "/api/v1/chart/data", json=payload2, headers=H2)
res = r.json().get("result", [])
if res:
    data = sorted(res[0].get("data", []), key=lambda x: -x["用户数"])
    print("[6] RFM 分群查询成功，%d 类：" % len(data))
    for row in data[:8]:
        print("     ", row.get("rfm_label"), "->", row.get("用户数"), "人")
else:
    print("[6] 失败:", json.dumps(r.json())[:300])