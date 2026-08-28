#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线数仓 ETL 同步工具（替代 DataX）
支持 MySQL → HDFS 的全量/增量同步

用法:
  python3 etl_sync.py sync user_info full 2026-08-19
  python3 etl_sync.py sync order_info incr 2026-08-20
  python3 etl_sync.py sync sku_info full 2026-08-19
  python3 etl_sync.py log 2026-08-20
"""

import sys
import os
import subprocess
import pymysql
from datetime import datetime

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
        'mode': 'full'  # 首日全量
    },
    'sku_info': {
        'table': 'sku_info',
        'columns': ['id', 'sku_name', 'category3_id', 'price', 'create_time', 'operate_time'],
        'hdfs_dir': 'ods_sku_info',
        'mode': 'full'  # 全量覆盖
    },
    'order_info': {
        'table': 'order_info',
        'columns': ['id', 'user_id', 'total_amount', 'status', 'create_time', 'operate_time'],
        'partition_key': 'create_time',
        'hdfs_dir': 'ods_order_info',
        'mode': 'incr'  # 增量
    },
    'order_detail': {
        'table': 'order_detail',
        'columns': ['id', 'order_id', 'sku_id', 'sku_num', 'sku_price', 'create_time'],
        'partition_key': 'create_time',
        'hdfs_dir': 'ods_order_detail',
        'mode': 'incr'
    },
    'payment_info': {
        'table': 'payment_info',
        'columns': ['id', 'order_id', 'pay_amount', 'pay_status', 'create_time', 'operate_time'],
        'partition_key': 'create_time',
        'hdfs_dir': 'ods_payment_info',
        'mode': 'incr'
    }
}

# ==================== 工具函数 ====================

def hdfs_cmd(args):
    """执行 HDFS 命令"""
    cmd = f'source ~/.profile && hdfs dfs {args}'
    result = subprocess.run(
        ['bash', '-c', cmd],
        capture_output=True, text=True, timeout=60
    )
    return result


def mysql_query(sql):
    """执行 MySQL 查询"""
    conn = pymysql.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def mysql_count(table, where_clause=''):
    """获取表行数"""
    sql = f"SELECT COUNT(*) FROM {table}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    rows = mysql_query(sql)
    return rows[0][0] if rows else 0


# ==================== 同步函数 ====================

def sync_full(table_name, dt):
    """全量同步：读取全表数据写入 HDFS"""
    cfg = SYNC_CONFIG[table_name]
    table = cfg['table']
    columns = cfg['columns']
    hdfs_dir = cfg['hdfs_dir']
    
    print(f"\n{'='*60}")
    print(f"[全量同步] {table} → HDFS")
    print(f"{'='*60}")
    
    # 构建查询
    col_str = ', '.join(columns)
    count = mysql_count(table)
    print(f"  MySQL 源表行数: {count}")
    
    # 读取数据
    rows = mysql_query(f"SELECT {col_str} FROM {table}")
    print(f"  读取到 {len(rows)} 行数据")
    
    # 写入本地临时文件（Tab 分隔）
    local_file = f"{LOCAL_TMP}/{table}_{dt}.txt"
    os.makedirs(LOCAL_TMP, exist_ok=True)
    
    with open(local_file, 'w', encoding='utf-8') as f:
        for row in rows:
            vals = []
            for v in row:
                if v is None:
                    vals.append('')
                else:
                    vals.append(str(v))
            f.write('\t'.join(vals) + '\n')
    
    file_size = os.path.getsize(local_file)
    print(f"  写入本地文件: {local_file} ({file_size} bytes)")
    
    # 上传到 HDFS
    hdfs_path = f"{HDFS_BASE}/{hdfs_dir}/dt={dt}"
    print(f"  上传 HDFS 路径: {hdfs_path}")
    
    hdfs_cmd(f'-mkdir -p {hdfs_path}')
    hdfs_cmd(f'-put -f {local_file} {hdfs_path}/')
    
    # 验证
    result = hdfs_cmd(f'-ls {hdfs_path}')
    print(f"  HDFS 目录内容:")
    for line in result.stdout.strip().split('\n')[-3:]:
        print(f"    {line}")
    
    # 清理本地文件
    os.remove(local_file)
    print(f"  ✓ {table} 全量同步完成")
    
    return len(rows)


def sync_incr(table_name, dt, start_time=None, end_time=None):
    """增量同步：按时间条件筛选数据"""
    cfg = SYNC_CONFIG[table_name]
    table = cfg['table']
    columns = cfg['columns']
    partition_key = cfg['partition_key']
    hdfs_dir = cfg['hdfs_dir']
    
    # 默认时间范围：当天 00:00:00 ~ 次日 00:00:00
    if not start_time:
        start_time = f"{dt} 00:00:00"
    if not end_time:
        end_time = f"{dt} 23:59:59"
    
    print(f"\n{'='*60}")
    print(f"[增量同步] {table} → HDFS")
    print(f"  时间范围: {start_time} ~ {end_time}")
    print(f"{'='*60}")
    
    # 构建带条件的查询
    col_str = ', '.join(columns)
    where_clause = f"{partition_key} >= '{start_time}' AND {partition_key} <= '{end_time}'"
    count = mysql_count(table, where_clause)
    print(f"  符合条件行数: {count}")
    
    if count == 0:
        print(f"  ⚠ 无数据需要同步")
        return 0
    
    # 读取数据
    rows = mysql_query(
        f"SELECT {col_str} FROM {table} WHERE {where_clause}"
    )
    print(f"  读取到 {len(rows)} 行数据")
    
    # 写入本地临时文件
    local_file = f"{LOCAL_TMP}/{table}_{dt}.txt"
    os.makedirs(LOCAL_TMP, exist_ok=True)
    
    with open(local_file, 'w', encoding='utf-8') as f:
        for row in rows:
            vals = []
            for v in row:
                if v is None:
                    vals.append('')
                else:
                    vals.append(str(v))
            f.write('\t'.join(vals) + '\n')
    
    file_size = os.path.getsize(local_file)
    print(f"  写入本地文件: {local_file} ({file_size} bytes)")
    
    # 上传到 HDFS
    hdfs_path = f"{HDFS_BASE}/{hdfs_dir}/dt={dt}"
    print(f"  上传 HDFS 路径: {hdfs_path}")
    
    hdfs_cmd(f'-mkdir -p {hdfs_path}')
    hdfs_cmd(f'-put -f {local_file} {hdfs_path}/')
    
    # 验证
    result = hdfs_cmd(f'-ls {hdfs_path}')
    print(f"  HDFS 目录内容:")
    for line in result.stdout.strip().split('\n')[-3:]:
        print(f"    {line}")
    
    # 清理
    os.remove(local_file)
    print(f"  ✓ {table} 增量同步完成")
    
    return len(rows)


def sync_log(dt):
    """埋点日志入 HDFS"""
    print(f"\n{'='*60}")
    print(f"[日志同步] {dt}.log → HDFS")
    print(f"{'='*60}")
    
    local_log = f"/opt/script/mall/mock/logs/{dt}.log"
    if not os.path.exists(local_log):
        print(f"  ⚠ 本地日志不存在: {local_log}")
        return 0
    
    # 统计行数
    with open(local_log, 'r') as f:
        lines = sum(1 for _ in f)
    print(f"  本地日志行数: {lines}")
    
    # 上传到 HDFS
    hdfs_path = f"{HDFS_BASE}/ods_event_log/dt={dt}"
    print(f"  上传 HDFS 路径: {hdfs_path}")
    
    hdfs_cmd(f'-mkdir -p {hdfs_path}')
    hdfs_cmd(f'-put -f {local_log} {hdfs_path}/')
    
    # 验证
    result = hdfs_cmd(f'-ls {hdfs_path}')
    print(f"  HDFS 目录内容:")
    for line in result.stdout.strip().split('\n')[-3:]:
        print(f"    {line}")
    
    print(f"  ✓ {dt} 日志同步完成")
    return lines


# ==================== 主入口 ====================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 etl_sync.py sync <table> <mode> <dt>")
        print("  python3 etl_sync.py log <dt>")
        print()
        print("  table: user_info | sku_info | order_info | order_detail | payment_info")
        print("  mode:  full (全量) | incr (增量)")
        print("  dt:    日期 YYYY-MM-DD")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "sync":
        if len(sys.argv) < 5:
            print("参数不足: etl_sync.py sync <table> <mode> <dt>")
            sys.exit(1)
        
        table = sys.argv[2]
        mode = sys.argv[3]
        dt = sys.argv[4]
        
        if table not in SYNC_CONFIG:
            print(f"未知表: {table}")
            print(f"可选: {list(SYNC_CONFIG.keys())}")
            sys.exit(1)
        
        if mode == "full":
            count = sync_full(table, dt)
        elif mode == "incr":
            count = sync_incr(table, dt)
        else:
            print(f"未知模式: {mode}")
            sys.exit(1)
        
        print(f"\n[汇总] {table} {mode} 同步 {count} 行")
    
    elif action == "log":
        if len(sys.argv) < 3:
            print("参数不足: etl_sync.py log <dt>")
            sys.exit(1)
        
        dt = sys.argv[2]
        count = sync_log(dt)
        print(f"\n[汇总] 日志同步 {count} 行")
    
    else:
        print(f"未知操作: {action}")
        sys.exit(1)
