#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWS 聚合宽表加工脚本（最终版）
直接从 MySQL 聚合数据，加载到 Hive ORC 内部表
使用 LOAD DATA 方式避免 MapReduce 超时问题
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
LOCAL_TMP = '/tmp/dws_load_tmp'


def run_cmd(cmd, timeout=60):
    """执行Shell命令"""
    try:
        result = subprocess.run(
            cmd, shell=True,
            capture_output=True, text=True,
            timeout=timeout,
            executable='/bin/bash'
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  命令执行超时 ({timeout}s)")
        return "", -1


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


def process_dws(dt):
    """处理一天的 DWS 数据"""
    
    # ==================== 1. 用户交易日宽表 ====================
    print(f"\n[DWS] 加工用户交易日宽表 - {dt}")
    
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
    print(f"  聚合用户数: {len(user_results)}")
    
    if user_results:
        # 写本地文件
        local_dir = f"{LOCAL_TMP}/user/{dt}"
        os.makedirs(local_dir, exist_ok=True)
        data_file = f"{local_dir}/data.txt"
        
        with open(data_file, 'w', encoding='utf-8') as f:
            for row in user_results:
                line = '\t'.join([str(v) if v is not None else '\\N' for v in row])
                f.write(line + '\n')
        
        # 上传 HDFS
        hdfs_dir = f"{HDFS_BASE}/user/{dt}"
        run_cmd(f"source ~/.profile && hdfs dfs -rm -r -f {hdfs_dir} 2>/dev/null")
        run_cmd(f"source ~/.profile && hdfs dfs -mkdir -p {hdfs_dir}")
        run_cmd(f"source ~/.profile && hdfs dfs -put -f {data_file} {hdfs_dir}/data.txt")
        
        # 用 Hive 加载
        print(f"  加载到 Hive 内部表...")
        load_sql = f"""
        USE mall;
        LOAD DATA INPATH '{hdfs_dir}/data.txt' 
        INTO TABLE dws_trade_user_order_1d PARTITION (dt='{dt}');
        """
        
        sql_file = f"{local_dir}/load.sql"
        with open(sql_file, 'w') as f:
            f.write(load_sql)
        
        stdout, code = run_cmd(f"source ~/.profile && hive -f {sql_file} 2>&1 | tail -3")
        print(f"  {stdout}")
    
    # ==================== 2. 商品交易日宽表 ====================
    print(f"\n[DWS] 加工商品交易日宽表 - {dt}")
    
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
    print(f"  聚合商品数: {len(sku_results)}")
    
    if sku_results:
        # 写本地文件
        local_dir = f"{LOCAL_TMP}/sku/{dt}"
        os.makedirs(local_dir, exist_ok=True)
        data_file = f"{local_dir}/data.txt"
        
        with open(data_file, 'w', encoding='utf-8') as f:
            for row in sku_results:
                line = '\t'.join([str(v) if v is not None else '\\N' for v in row])
                f.write(line + '\n')
        
        # 上传 HDFS
        hdfs_dir = f"{HDFS_BASE}/sku/{dt}"
        run_cmd(f"source ~/.profile && hdfs dfs -rm -r -f {hdfs_dir} 2>/dev/null")
        run_cmd(f"source ~/.profile && hdfs dfs -mkdir -p {hdfs_dir}")
        run_cmd(f"source ~/.profile && hdfs dfs -put -f {data_file} {hdfs_dir}/data.txt")
        
        # 用 Hive 加载
        print(f"  加载到 Hive 内部表...")
        load_sql = f"""
        USE mall;
        LOAD DATA INPATH '{hdfs_dir}/data.txt' 
        INTO TABLE dws_trade_sku_order_1d PARTITION (dt='{dt}');
        """
        
        sql_file = f"{local_dir}/load.sql"
        with open(sql_file, 'w') as f:
            f.write(load_sql)
        
        stdout, code = run_cmd(f"source ~/.profile && hive -f {sql_file} 2>&1 | tail -3")
        print(f"  {stdout}")
    
    # 清理本地临时文件
    if os.path.exists(LOCAL_TMP):
        shutil.rmtree(LOCAL_TMP, ignore_errors=True)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 dws_orc_etl.py <日期> [日期2]")
        sys.exit(1)
    
    dates = sys.argv[1:]
    
    print("=" * 60)
    print("# DWS 聚合宽表加工 (ORC 内部表)")
    print(f"# 日期: {', '.join(dates)}")
    print("=" * 60)
    
    for dt in dates:
        process_dws(dt)
    
    # 验证
    print(f"\n{'=' * 60}")
    print("# 验证数据")
    
    for dt in dates:
        stdout, _ = run_cmd(f"""source ~/.profile && hive -e "
            SELECT '用户-{dt}', COUNT(*) FROM mall.dws_trade_user_order_1d WHERE dt='{dt}'
            UNION ALL
            SELECT '商品-{dt}', COUNT(*) FROM mall.dws_trade_sku_order_1d WHERE dt='{dt}';
        " 2>&1 | grep -E '^{dt}|_{dt}'""")
        print(stdout)


if __name__ == "__main__":
    main()
