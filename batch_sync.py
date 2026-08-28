#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量同步脚本：一次性同步多天数据到 HDFS
用于初始化历史数据或批量补数
"""

import sys
import os
import subprocess
import pymysql
from datetime import datetime, timedelta

# ==================== 配置 ====================
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'mall',
    'charset': 'utf8mb4'
}

HDFS_BASE = '/warehouse/mall/ods'
LOCAL_TMP = '/tmp/etl_sync'

# 同步任务配置（对应 DataX job json）
SYNC_CONFIG = {
    'user_info': {
        'table': 'user_info',
        'columns': ['id', 'login_name', 'nick_name', 'phone', 'gender', 'user_level', 'create_time', 'operate_time'],
        'partition_key': 'operate_time',
        'hdfs_dir': 'ods_user_info',
    },
    'sku_info': {
        'table': 'sku_info',
        'columns': ['id', 'sku_name', 'category3_id', 'price', 'create_time', 'operate_time'],
        'hdfs_dir': 'ods_sku_info',
    },
    'order_info': {
        'table': 'order_info',
        'columns': ['id', 'user_id', 'total_amount', 'status', 'create_time', 'operate_time'],
        'partition_key': 'create_time',
        'hdfs_dir': 'ods_order_info',
    },
    'order_detail': {
        'table': 'order_detail',
        'columns': ['id', 'order_id', 'sku_id', 'sku_num', 'sku_price', 'create_time'],
        'partition_key': 'create_time',
        'hdfs_dir': 'ods_order_detail',
    },
    'payment_info': {
        'table': 'payment_info',
        'columns': ['id', 'order_id', 'pay_amount', 'pay_status', 'create_time', 'operate_time'],
        'partition_key': 'create_time',
        'hdfs_dir': 'ods_payment_info',
    }
}


def hdfs_cmd(args):
    cmd = f'source ~/.profile && hdfs dfs {args}'
    result = subprocess.run(
        ['bash', '-c', cmd],
        capture_output=True, text=True, timeout=120
    )
    return result


def mysql_query(sql):
    conn = pymysql.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def sync_table(table_name, dt, mode='incr'):
    """同步单表到 HDFS"""
    cfg = SYNC_CONFIG[table_name]
    table = cfg['table']
    columns = cfg['columns']
    hdfs_dir = cfg['hdfs_dir']
    col_str = ', '.join(columns)
    
    if mode == 'full':
        where_clause = ''
        sql = f"SELECT {col_str} FROM {table}"
    else:
        start_time = f"{dt} 00:00:00"
        end_time = f"{dt} 23:59:59"
        partition_key = cfg['partition_key']
        where_clause = f"{partition_key} >= '{start_time}' AND {partition_key} <= '{end_time}'"
        sql = f"SELECT {col_str} FROM {table} WHERE {where_clause}"
    
    rows = mysql_query(sql)
    if not rows:
        return 0
    
    # 写入本地临时文件
    local_file = f"{LOCAL_TMP}/{table}_{dt}.txt"
    os.makedirs(LOCAL_TMP, exist_ok=True)
    
    with open(local_file, 'w', encoding='utf-8') as f:
        for row in rows:
            vals = [str(v) if v is not None else '' for v in row]
            f.write('\t'.join(vals) + '\n')
    
    # 上传到 HDFS
    hdfs_path = f"{HDFS_BASE}/{hdfs_dir}/dt={dt}"
    hdfs_cmd(f'-mkdir -p {hdfs_path}')
    hdfs_cmd(f'-put -f {local_file} {hdfs_path}/')
    
    os.remove(local_file)
    return len(rows)


def sync_log(dt):
    """同步日志到 HDFS"""
    local_log = f"/opt/script/mall/mock/logs/{dt}.log"
    if not os.path.exists(local_log):
        return 0
    
    hdfs_path = f"{HDFS_BASE}/ods_event_log/dt={dt}"
    hdfs_cmd(f'-mkdir -p {hdfs_path}')
    hdfs_cmd(f'-put -f {local_log} {hdfs_path}/')
    
    with open(local_log, 'r') as f:
        return sum(1 for _ in f)


def batch_sync(start_date, end_date):
    """批量同步多天数据"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    total_days = (end - start).days + 1
    
    print(f"\n{'='*60}")
    print(f"[批量同步] {start_date} ~ {end_date} ({total_days} 天)")
    print(f"{'='*60}")
    
    summary = {}
    
    current = start
    day_idx = 0
    while current <= end:
        dt = current.strftime('%Y-%m-%d')
        day_idx += 1
        
        # 首日全量同步 user_info 和 sku_info
        if day_idx == 1:
            print(f"\n--- Day {day_idx}: {dt} (首日全量) ---")
            for table in ['user_info', 'sku_info']:
                count = sync_table(table, dt, mode='full')
                summary[f"{table}_full"] = count
                print(f"  {table} 全量: {count} 行")
        else:
            print(f"\n--- Day {day_idx}: {dt} (增量) ---")
        
        # 每日增量同步订单相关表
        for table in ['order_info', 'order_detail', 'payment_info']:
            count = sync_table(table, dt, mode='incr')
            key = f"{table}_{dt}"
            summary[key] = count
        
        # 增量同步 user_info (按 operate_time)
        user_count = sync_table('user_info', dt, mode='incr')
        summary[f"user_info_incr_{dt}"] = user_count
        
        # 日志
        log_count = sync_log(dt)
        summary[f"log_{dt}"] = log_count
        
        print(f"  user_info: {user_count} | order_info: {summary.get(f'order_info_{dt}', 0)} | logs: {log_count}")
        
        current += timedelta(days=1)
    
    # 打印汇总
    print(f"\n{'='*60}")
    print(f"[批量同步完成]")
    print(f"{'='*60}")
    
    total = 0
    for key, count in summary.items():
        if count > 0:
            print(f"  {key}: {count} 行")
            total += count
    
    print(f"\n  总计: {total} 行数据已同步到 HDFS")
    return summary


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 batch_sync.py <start_date> <end_date>")
        print("示例: python3 batch_sync.py 2026-07-21 2026-08-19")
        sys.exit(1)
    
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    
    batch_sync(start_date, end_date)
