#!/bin/bash
WIN=/mnt/e/简历项目/01-离线数仓项目
f=/opt/script/mall/ads/export_ads_to_mysql.py
cp "$WIN/export_ads_to_mysql.py" "$f"
if head -c 3 "$f" | od -An -c | head -1 | grep -q ' 357 273 277'; then
  tail -c +4 "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
fi
tr -d '\r' < "$f" > "${f}.tmp" && mv "${f}.tmp" "$f"
chmod +x "$f"
file "$f"
head -3 "$f"