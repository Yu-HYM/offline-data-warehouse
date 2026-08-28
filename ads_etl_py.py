#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADS 复杂指标 Python 加工脚本（阶段七）

针对 Hive 本地模式难以稳定处理的复杂 JOIN / 窗口函数指标，
改用 Python 从 MySQL 业务表直接计算，结果写入 HDFS，
再通过 Hive 临时外部表加载到 ADS ORC 内部表。

处理两类指标：
  1. ads_repurchase_rate  复购率（当日下单用户中累计下单天数>=2 的占比）
  2. ads_user_rfm         近30天 RFM 用户分层（R/F/M 三维5档 + 8类标签）

（ads_trade_stats 由 process_ads.py 通过 Hive 本地模式加工，本脚本不重复处理）

用法:
  python3 ads_etl_py.py 2026-08-19
  python3 ads_etl_py.py 2026-08-19 2026-08-20
"""

import sys
import os
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict

import pymysql


MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'mall',
    'charset': 'utf8mb4'
}

HDFS_BASE = '/warehouse/mall'
LOCAL_TMP = '/tmp/ads_etl_py'


def hdfs_cmd(args):
    cmd = f'source ~/.profile && hdfs dfs {args}'
    result = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, timeout=120)
    return result


def run_hive(sql_file):
    cmd = f'source ~/.profile && hive -f {sql_file} 2>&1 | grep -E "OK|FAILED|Time taken" | tail -10'
    result = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, timeout=300)
    print(f"  {result.stdout.strip()}")
    return result.returncode


def mysql_query(sql):
    conn = pymysql.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def write_hdfs_text(rows, table_name, dt):
    if not rows:
        print(f"  ⚠️  {table_name} 无数据，跳过")
        return
    os.makedirs(LOCAL_TMP, exist_ok=True)
    local_file = f"{LOCAL_TMP}/{table_name}_{dt}.txt"
    with open(local_file, 'w', encoding='utf-8') as f:
        for row in rows:
            f.write('\t'.join(str(v) for v in row) + '\n')
    size = os.path.getsize(local_file)
    hdfs_path = f"{HDFS_BASE}/ads_load/{table_name}/dt={dt}"
    hdfs_cmd(f'-rm -r -f {hdfs_path}')
    hdfs_cmd(f'-mkdir -p {hdfs_path}')
    hdfs_cmd(f'-put -f {local_file} {hdfs_path}/')
    print(f"  → {hdfs_path} ({size} bytes, {len(rows)} 行)")
    os.remove(local_file)


def ntile5(pairs):
    """pairs: [(key, value)] 按 value 升序分5档，value大→分高，返回 {key:score}"""
    n = len(pairs)
    if n == 0:
        return {}
    sorted_items = sorted(pairs, key=lambda x: x[1])
    result = {}
    for i, (k, _) in enumerate(sorted_items):
        result[k] = (i * 5) // n + 1
    return result


def process_repurchase(dt):
    print(f"\n[ADS-PY] 复购率 (ads_repurchase_rate) dt={dt}")
    today_sql = f"SELECT DISTINCT user_id FROM order_info WHERE DATE(create_time) = '{dt}' AND total_amount > 0"
    today_users = {r[0] for r in mysql_query(today_sql)}
    print(f"  当日下单用户数: {len(today_users)}")
    if not today_users:
        print("  ⚠️  无当日下单用户")
        return
    uids = ','.join(str(u) for u in today_users)
    hist_sql = f"SELECT user_id, COUNT(DISTINCT DATE(create_time)) AS cnt FROM order_info WHERE DATE(create_time) <= '{dt}' AND total_amount > 0 AND user_id IN ({uids}) GROUP BY user_id"
    hist_rows = mysql_query(hist_sql)
    repurchase = sum(1 for _, cnt in hist_rows if cnt >= 2)
    order_user_count = len(today_users)
    rate = round(repurchase / order_user_count, 4) if order_user_count else 0
    print(f"  复购用户数(累计下单天数>=2): {repurchase}")
    print(f"  复购率: {rate}")
    write_hdfs_text([(order_user_count, repurchase, rate)], 'ads_repurchase_rate', dt)
    load_to_orc('ads_repurchase_rate', dt)


def process_rfm(dt):
    print(f"\n[ADS-PY] RFM 用户分层 (ads_user_rfm) dt={dt}")
    start = (datetime.strptime(dt, '%Y-%m-%d') - timedelta(days=29)).strftime('%Y-%m-%d')
    sql = f"SELECT user_id, DATE(create_time) AS d, SUM(total_amount) AS amt FROM order_info WHERE DATE(create_time) BETWEEN '{start}' AND '{dt}' AND total_amount > 0 GROUP BY user_id, DATE(create_time)"
    rows = mysql_query(sql)
    print(f"  30天窗口明细行数: {len(rows)}")
    if not rows:
        print("  ⚠️  无数据")
        return
    user_days = defaultdict(set)
    user_amount = defaultdict(float)
    for uid, d, amt in rows:
        user_days[uid].add(d)
        user_amount[uid] += float(amt) if amt else 0
    dt_date = datetime.strptime(dt, '%Y-%m-%d').date()
    rfm = []
    for uid in user_days:
        last_day = max(user_days[uid])
        r_days = (dt_date - last_day).days
        f_count = len(user_days[uid])
        m_amount = round(user_amount[uid], 2)
        rfm.append((uid, r_days, f_count, m_amount))
    f_scores = ntile5([(x[0], x[2]) for x in rfm])
    m_scores = ntile5([(x[0], x[3]) for x in rfm])
    r_raw = ntile5([(x[0], x[1]) for x in rfm])
    r_scores = {k: (6 - v) for k, v in r_raw.items()}
    out_rows = []
    label_count = defaultdict(int)
    for uid, _, _, _ in rfm:
        rs = r_scores[uid]
        fs = f_scores[uid]
        ms = m_scores[uid]
        if rs >= 3 and fs >= 3 and ms >= 3:
            label = '重要价值用户'
        elif rs < 3 and fs >= 3 and ms >= 3:
            label = '重要保持用户'
        elif rs >= 3 and fs < 3 and ms >= 3:
            label = '重要发展用户'
        elif rs < 3 and fs < 3 and ms >= 3:
            label = '重要挽留用户'
        elif rs >= 3 and fs >= 3 and ms < 3:
            label = '一般价值用户'
        elif rs < 3 and fs >= 3 and ms < 3:
            label = '一般保持用户'
        elif rs >= 3 and fs < 3 and ms < 3:
            label = '一般发展用户'
        else:
            label = '一般挽留用户'
        label_count[label] += 1
        out_rows.append((uid, rs, fs, ms, label))
    print(f"  RFM 用户总数: {len(out_rows)}")
    for lab, c in sorted(label_count.items(), key=lambda x: -x[1]):
        print(f"    {lab}: {c}")
    write_hdfs_text(out_rows, 'ads_user_rfm', dt)
    load_to_orc('ads_user_rfm', dt)


def load_to_orc(table_name, dt):
    print(f"  [加载] {table_name} → ORC (dt={dt})")
    if table_name == 'ads_repurchase_rate':
        cols = "order_user_count BIGINT, repurchase_user_count BIGINT, repurchase_rate DECIMAL(10,4)"
        sel_cols = "order_user_count, repurchase_user_count, repurchase_rate"
    elif table_name == 'ads_user_rfm':
        cols = "user_id STRING, r_score INT, f_score INT, m_score INT, rfm_label STRING"
        sel_cols = "user_id, r_score, f_score, m_score, rfm_label"
    else:
        return
    hive_sql = f"""USE mall;
DROP TABLE IF EXISTS tmp_{table_name}_text;
CREATE EXTERNAL TABLE tmp_{table_name}_text( {cols} )
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ads_load/{table_name}/dt={dt}';
SET hive.exec.mode.local.auto=true;
SET hive.exec.mode.local.auto.inputbytes.max=128000000;
INSERT OVERWRITE TABLE {table_name} PARTITION (dt='{dt}')
SELECT {sel_cols} FROM tmp_{table_name}_text;
DROP TABLE IF EXISTS tmp_{table_name}_text;
"""
    sql_file = f"/tmp/load_ads_{table_name}_{dt}.sql"
    with open(sql_file, 'w') as f:
        f.write(hive_sql)
    run_hive(sql_file)
    if os.path.exists(sql_file):
        os.remove(sql_file)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 ads_etl_py.py <日期1> [日期2] ...")
        sys.exit(1)
    dates = sys.argv[1:]
    print("=" * 60)
    print("# ADS 复杂指标 Python 加工（repurchase + rfm）")
    print(f"# 日期: {', '.join(dates)}")
    print("=" * 60)
    for dt in dates:
        process_repurchase(dt)
        process_rfm(dt)
    print("\n" + "=" * 60)
    print("# ADS Python 加工完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
