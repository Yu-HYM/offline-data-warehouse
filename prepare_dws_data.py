#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
准备 DWS 数据到 HDFS（给 Hive 外部表使用）
"""

import pymysql
import subprocess
import sys
import os
import shutil

MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'mall',
    'charset': 'utf8mb4'
}

HDFS_BASE = '/warehouse/mall/dws_load'
LOCAL_TMP = '/tmp/dws_load_data'


def run_cmd(cmd):
    """执行Shell命令"""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        executable='/bin/bash', timeout=30
    )
    return result.stdout.strip(), result.returncode


def mysql_query(sql):
    """执行MySQL查询"""
    conn = pymysql.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    cur.execute(sql)
    results = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return columns, results


def prepare_data(dt):
    """准备一天的数据到 HDFS"""
    
    # 清理
    if os.path.exists(LOCAL_TMP):
        shutil.rmtree(LOCAL_TMP, ignore_errors=True)
    
    # ==================== 1. 用户交易日宽表 ====================
    print(f"[准备] 用户交易日宽表 - {dt}")
    
    sql = f"""
    SELECT 
        u.id,
        u.nick_name,
        CASE u.user_level WHEN 1 THEN '普通用户' WHEN 2 THEN '银牌用户' WHEN 3 THEN '金牌用户' ELSE '未知' END,
        CASE u.gender WHEN 0 THEN '女' WHEN 1 THEN '男' ELSE '未知' END,
        COUNT(DISTINCT o.id),
        ROUND(SUM(o.total_amount), 2),
        ROUND(SUM(CASE WHEN p.pay_status = 1 THEN p.pay_amount ELSE 0 END), 2),
        SUM(COALESCE(od.sku_num, 0)),
        COUNT(DISTINCT s.category3_id),
        ROUND(SUM(o.total_amount) / COUNT(DISTINCT o.id), 2)
    FROM mall.user_info u
    JOIN mall.order_info o ON u.id = o.user_id
    LEFT JOIN mall.order_detail od ON o.id = od.order_id
    LEFT JOIN mall.sku_info s ON od.sku_id = s.id
    LEFT JOIN mall.payment_info p ON o.id = p.order_id AND p.pay_status = 1
    WHERE DATE(o.create_time) = '{dt}' AND o.total_amount > 0
    GROUP BY u.id, u.nick_name, u.user_level, u.gender
    """
    
    columns, user_results = mysql_query(sql)
    print(f"  用户数: {len(user_results)}")
    
    # 写本地文件
    local_dir = f"{LOCAL_TMP}/user/{dt}"
    os.makedirs(local_dir, exist_ok=True)
    
    with open(f"{local_dir}/data.txt", 'w', encoding='utf-8') as f:
        for row in user_results:
            line = '\t'.join([str(v) if v is not None else '\\N' for v in row])
            f.write(line + '\n')
    
    # 上传 HDFS
    hdfs_dir = f"{HDFS_BASE}/user/dt={dt}"
    run_cmd(f"source ~/.profile && hdfs dfs -rm -r -f '{hdfs_dir}' 2>/dev/null")
    run_cmd(f"source ~/.profile && hdfs dfs -mkdir -p '{hdfs_dir}'")
    run_cmd(f"source ~/.profile && hdfs dfs -put -f '{local_dir}/data.txt' '{hdfs_dir}/'")
    
    # ==================== 2. 商品交易日宽表 ====================
    print(f"[准备] 商品交易日宽表 - {dt}")
    
    sql = f"""
    SELECT 
        s.id,
        s.sku_name,
        c1.name,
        c2.name,
        c3.name,
        COUNT(DISTINCT od.order_id),
        SUM(od.sku_num),
        ROUND(SUM(od.sku_num * od.sku_price), 2),
        COUNT(DISTINCT o.user_id),
        ROUND(AVG(od.sku_price), 2)
    FROM mall.order_info o
    JOIN mall.order_detail od ON o.id = od.order_id
    JOIN mall.sku_info s ON od.sku_id = s.id
    LEFT JOIN mall.category3 c3 ON s.category3_id = c3.id
    LEFT JOIN mall.category2 c2 ON c3.category2_id = c2.id
    LEFT JOIN category1 c1 ON c2.category1_id = c1.id
    WHERE DATE(o.create_time) = '{dt}' AND o.total_amount > 0
    GROUP BY s.id, s.sku_name, c1.name, c2.name, c3.name
    """
    
    columns, sku_results = mysql_query(sql)
    print(f"  商品数: {len(sku_results)}")
    
    # 写本地文件
    local_dir = f"{LOCAL_TMP}/sku/{dt}"
    os.makedirs(local_dir, exist_ok=True)
    
    with open(f"{local_dir}/data.txt", 'w', encoding='utf-8') as f:
        for row in sku_results:
            line = '\t'.join([str(v) if v is not None else '\\N' for v in row])
            f.write(line + '\n')
    
    # 上传 HDFS
    hdfs_dir = f"{HDFS_BASE}/sku/dt={dt}"
    run_cmd(f"source ~/.profile && hdfs dfs -rm -r -f '{hdfs_dir}' 2>/dev/null")
    run_cmd(f"source ~/.profile && hdfs dfs -mkdir -p '{hdfs_dir}'")
    run_cmd(f"source ~/.profile && hdfs dfs -put -f '{local_dir}/data.txt' '{hdfs_dir}/'")
    
    # 清理
    shutil.rmtree(LOCAL_TMP, ignore_errors=True)
    print(f"  ✅ {dt} 数据准备完成")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 prepare_dws_data.py <日期> [日期2]")
        sys.exit(1)
    
    dates = sys.argv[1:]
    
    print("=" * 50)
    print("# 准备 DWS 数据到 HDFS")
    print(f"# 日期: {', '.join(dates)}")
    print("=" * 50)
    
    for dt in dates:
        prepare_data(dt)
    
    print("\n✅ 数据准备完成，请执行 load_dws_to_orc.sql 加载到 ORC 内部表")


if __name__ == "__main__":
    main()
