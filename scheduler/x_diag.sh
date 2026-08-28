#!/bin/bash
source /opt/module/superset_env/bin/activate
python3 - <<'PYEOF'
import requests, json
BASE = "http://localhost:8088"
s = requests.Session()
r = s.post(BASE + "/api/v1/security/login",
           json={"username": "admin", "password": "admin123", "provider": "db", "refresh": True})
access = r.json()["access_token"]
H = {"Authorization": "Bearer " + access}
r = s.get(BASE + "/api/v1/security/csrf_token/", headers=H)
token = r.json()["result"]

payload = {
    "queries": [{
        "datasource": {"id": 1, "type": "table"},
        "granularity": "dt",
        "groupby": ["dt"],
        "metrics": [{"expressionType": "SIMPLE",
                     "column": {"column_name": "gmv", "type": "NUMERIC"},
                     "aggregate": "SUM", "label": "GMV"}],
        "row_limit": 10,
        "time_range": "100 years : now",
    }]
}
H2 = dict(H)
H2["X-CSRFToken"] = token
H2["Referer"] = BASE + "/"
r = s.post(BASE + "/api/v1/chart/data", json=payload, headers=H2)
print("HTTP", r.status_code)
print("Content-Type:", r.headers.get("Content-Type"))
print("BODY[:800]:", r.text[:800])
PYEOF