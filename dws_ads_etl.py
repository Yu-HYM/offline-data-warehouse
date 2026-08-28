#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWS 汇总层 + ADS 应用层加工脚本

直接从 MySQL 业务表读取数据，完成聚合计算后写入 HDFS。
模拟完整的数据仓库加工流程：业务库 → DWS → ADS

用法:
  python3 dws_ads_etl.py 2026-08-19
  python3 dws_ads_etl.py 2026-08-20
"""

import sys
import os
import subprocess
import pymysql
from datetime import datetime, timedelta
from collections import defaultdict

# ==================== 配置 ====================
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'mall',
    'charset': 'utf8mb4'
}

HDFS_BASE = '/warehouse/mall'
LOCAL_TMP = '/tmp/dws_ads_etl'


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


def write_to_hdfs(rows, table_name, dt, columns, layer='dws'):
    """将数据写入 HDFS"""
    if not rows:
        return
    
    local_file = f"{LOCAL_TMP}/{table_name}_{dt}.txt"
    os.makedirs(LOCAL_TMP, exist_ok=True)
    
    with open(local_file, 'w', encoding='utf-8') as f:
        for row in rows:
            vals = [str(row.get(col, '')) if row.get(col) is not None else '' for col in columns]
            f.write('\t'.join(vals) + '\n')
    
    file_size = os.path.getsize(local_file)
    
    if layer == 'dws':
        hdfs_path = f"{HDFS_BASE}/dws/{table_name}/dt={dt}"
    else:
        hdfs_path = f"{HDFS_BASE}/ads/{table_name}"
    
    hdfs_cmd(f'-mkdir -p {hdfs_path}')
    hdfs_cmd(f'-put -f {local_file} {hdfs_path}/')
    
    result = hdfs_cmd(f'-ls {hdfs_path}')
    print(f"  → {hdfs_path} ({file_size} bytes, {len(rows)} 行)")
    
    os.remove(local_file)


# ==================== DWS 加工 ====================

def process_dws_user_day_agg(dt):
    """用户每日汇总（按用户聚合订单数据）"""
    print(f"\n[DWS] 用户每日汇总 (dws_user_day_agg)")
    
    sql = f"""
    SELECT 
        o.user_id,
        u.nick_name as user_nick_name,
        u.user_level,
        CASE u.gender WHEN '男' THEN 1 WHEN '女' THEN 2 ELSE 0 END as gender,
        COUNT(DISTINCT o.id) as order_count,
        ROUND(SUM(o.total_amount), 2) as order_amount,
        ROUND(SUM(CASE WHEN p.id IS NOT NULL THEN o.total_amount ELSE 0 END), 2) as pay_amount,
        SUM(od.sku_num) as item_count
    FROM mall.order_info o
    JOIN mall.user_info u ON o.user_id = u.id
    JOIN mall.order_detail od ON o.id = od.order_id
    LEFT JOIN mall.payment_info p ON o.id = p.order_id AND p.pay_status = 1
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    GROUP BY o.user_id, u.nick_name, u.user_level, u.gender
    """
    
    rows = mysql_query(sql)
    print(f"  聚合用户数: {len(rows)}")
    
    if not rows:
        return 0
    
    cleaned = []
    for row in rows:
        user_id, nick_name, level, gender, order_count, order_amount, pay_amount, item_count = row
        cleaned.append({
            'user_id': user_id,
            'user_nick_name': nick_name or '',
            'user_level': level or '普通',
            'gender': gender if gender else 0,
            'order_count': order_count,
            'order_amount': order_amount,
            'pay_amount': pay_amount,
            'item_count': item_count,
            'is_active': 1
        })
    
    write_to_hdfs(cleaned, 'dws_user_day_agg', dt,
                  ['user_id', 'user_nick_name', 'user_level', 'gender',
                   'order_count', 'order_amount', 'pay_amount', 'item_count', 'is_active'],
                  'dws')
    
    return len(cleaned)


def process_dws_sku_day_agg(dt):
    """商品每日汇总"""
    print(f"\n[DWS] 商品每日汇总 (dws_sku_day_agg)")
    
    sql = f"""
    SELECT 
        s.id as sku_id,
        s.sku_name,
        c1.name as category1_name,
        c2.name as category2_name,
        c3.name as category3_name,
        SUM(od.sku_num) as sale_count,
        ROUND(SUM(od.sku_num * od.sku_price), 2) as sale_amount,
        COUNT(DISTINCT o.user_id) as order_user_count,
        COUNT(DISTINCT o.id) as order_count
    FROM mall.order_info o
    JOIN mall.order_detail od ON o.id = od.order_id
    JOIN mall.sku_info s ON od.sku_id = s.id
    LEFT JOIN mall.category3 c3 ON s.category3_id = c3.id
    LEFT JOIN mall.category2 c2 ON c3.category2_id = c2.id
    LEFT JOIN mall.category1 c1 ON c2.category1_id = c1.id
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    GROUP BY s.id, s.sku_name, c1.name, c2.name, c3.name
    """
    
    rows = mysql_query(sql)
    print(f"  聚合商品数: {len(rows)}")
    
    if not rows:
        return 0
    
    cleaned = []
    for row in rows:
        sku_id, sku_name, c1, c2, c3, sale_count, sale_amount, user_count, order_count = row
        cleaned.append({
            'sku_id': sku_id,
            'sku_name': sku_name or '',
            'category1_name': c1 or '未分类',
            'category2_name': c2 or '未分类',
            'category3_name': c3 or '未分类',
            'sale_count': sale_count,
            'sale_amount': sale_amount,
            'order_user_count': user_count,
            'order_count': order_count
        })
    
    write_to_hdfs(cleaned, 'dws_sku_day_agg', dt,
                  ['sku_id', 'sku_name', 'category1_name', 'category2_name', 'category3_name',
                   'sale_count', 'sale_amount', 'order_user_count', 'order_count'],
                  'dws')
    
    return len(cleaned)


def process_dws_order_day_agg(dt):
    """订单每日汇总（全局概览）"""
    print(f"\n[DWS] 订单每日汇总 (dws_order_day_agg)")
    
    sql = f"""
    SELECT 
        COUNT(DISTINCT o.id) as total_order_count,
        ROUND(SUM(o.total_amount), 2) as total_order_amount,
        ROUND(SUM(CASE WHEN p.id IS NOT NULL THEN o.total_amount ELSE 0 END), 2) as total_pay_amount,
        COUNT(DISTINCT CASE WHEN p.id IS NOT NULL THEN o.id END) as paid_order_count,
        COUNT(DISTINCT CASE WHEN o.status = 4 THEN o.id END) as cancelled_count,
        ROUND(AVG(o.total_amount), 2) as avg_order_amount
    FROM mall.order_info o
    LEFT JOIN mall.payment_info p ON o.id = p.order_id AND p.pay_status = 1
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    """
    
    row = mysql_query(sql)
    if not row or not row[0][0]:
        print(f"  无订单数据")
        return 0
    
    total_orders, total_amount, pay_amount, paid_orders, cancelled, avg_amount = row[0]
    pay_rate = round(paid_orders / total_orders, 4) if total_orders > 0 else 0
    
    # 新用户数
    new_user_sql = f"""
    SELECT COUNT(DISTINCT o.user_id) 
    FROM mall.order_info o
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
      AND o.user_id IN (SELECT id FROM mall.user_info WHERE DATE(create_time) = '{dt}')
    """
    new_users = mysql_query(new_user_sql)[0][0]
    
    cleaned = [{
        'total_order_count': total_orders,
        'total_order_amount': total_amount,
        'total_pay_amount': pay_amount,
        'paid_order_count': paid_orders,
        'cancelled_count': cancelled,
        'new_user_count': new_users,
        'avg_order_amount': avg_amount,
        'pay_rate': pay_rate
    }]
    
    write_to_hdfs(cleaned, 'dws_order_day_agg', dt,
                  ['total_order_count', 'total_order_amount', 'total_pay_amount',
                   'paid_order_count', 'cancelled_count', 'new_user_count',
                   'avg_order_amount', 'pay_rate'],
                  'dws')
    
    return 1


def process_dws_category_day_agg(dt):
    """分类每日汇总"""
    print(f"\n[DWS] 分类每日汇总 (dws_category_day_agg)")
    
    sql = f"""
    SELECT 
        c1.id as category1_id,
        c1.name as category1_name,
        c2.id as category2_id,
        c2.name as category2_name,
        SUM(od.sku_num) as sale_count,
        ROUND(SUM(od.sku_num * od.sku_price), 2) as sale_amount,
        COUNT(DISTINCT o.id) as order_count
    FROM mall.order_info o
    JOIN mall.order_detail od ON o.id = od.order_id
    JOIN mall.sku_info s ON od.sku_id = s.id
    JOIN mall.category3 c3 ON s.category3_id = c3.id
    JOIN mall.category2 c2 ON c3.category2_id = c2.id
    JOIN mall.category1 c1 ON c2.category1_id = c1.id
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    GROUP BY c1.id, c1.name, c2.id, c2.name
    """
    
    rows = mysql_query(sql)
    print(f"  聚合分类数: {len(rows)}")
    
    if not rows:
        return 0
    
    cleaned = []
    for row in rows:
        c1_id, c1_name, c2_id, c2_name, sale_count, sale_amount, order_count = row
        cleaned.append({
            'category1_id': c1_id,
            'category1_name': c1_name or '',
            'category2_id': c2_id,
            'category2_name': c2_name or '',
            'sale_count': sale_count,
            'sale_amount': sale_amount,
            'order_count': order_count
        })
    
    write_to_hdfs(cleaned, 'dws_category_day_agg', dt,
                  ['category1_id', 'category1_name', 'category2_id', 'category2_name',
                   'sale_count', 'sale_amount', 'order_count'],
                  'dws')
    
    return len(cleaned)


# ==================== ADS 加工 ====================

def process_ads_gmv_day(dt):
    """GMV 日报表"""
    print(f"\n[ADS] GMV 日报表 (ads_gmv_day)")
    
    # GMV 计算
    detail_sql = f"""
    SELECT 
        ROUND(SUM(o.total_amount), 2) as gmv,
        ROUND(SUM(CASE WHEN p.id IS NOT NULL THEN o.total_amount ELSE 0 END), 2) as pay_amount,
        COUNT(DISTINCT o.id) as order_count,
        COUNT(DISTINCT CASE WHEN p.id IS NOT NULL THEN o.id END) as pay_order_count,
        COUNT(DISTINCT o.user_id) as customer_count,
        ROUND(AVG(o.total_amount), 2) as avg_order_value
    FROM mall.order_info o
    LEFT JOIN mall.payment_info p ON o.id = p.order_id AND p.pay_status = 1
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    """
    
    row = mysql_query(detail_sql)
    if not row or not row[0][0]:
        print(f"  无数据")
        return 0
    
    gmv, pay_amount, order_count, pay_order_count, customer_count, avg_order_value = row[0]
    pay_rate = round(pay_order_count / order_count, 4) if order_count > 0 else 0
    
    # 新用户数
    new_user_sql = f"""
    SELECT COUNT(DISTINCT o.user_id) 
    FROM mall.order_info o
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
      AND o.user_id IN (SELECT id FROM mall.user_info WHERE DATE(create_time) = '{dt}')
    """
    new_users = mysql_query(new_user_sql)[0][0]
    
    cleaned = [{
        'dt': dt,
        'gmv': gmv,
        'pay_amount': pay_amount,
        'order_count': order_count,
        'pay_order_count': pay_order_count,
        'customer_count': customer_count,
        'new_user_count': new_users,
        'avg_order_value': avg_order_value,
        'pay_rate': pay_rate
    }]
    
    write_to_hdfs(cleaned, 'ads_gmv_day', dt,
                  ['dt', 'gmv', 'pay_amount', 'order_count', 'pay_order_count',
                   'customer_count', 'new_user_count', 'avg_order_value', 'pay_rate'],
                  'ads')
    
    # 打印摘要
    print(f"  GMV: ¥{gmv:,.2f}")
    print(f"  支付金额: ¥{pay_amount:,.2f}")
    print(f"  订单数: {order_count}")
    print(f"  支付率: {pay_rate:.2%}")
    
    return 1


def process_ads_user_dashboard(dt):
    """用户看板"""
    print(f"\n[ADS] 用户看板 (ads_user_dashboard)")
    
    # 总用户数
    total_users = mysql_query("SELECT COUNT(*) FROM mall.user_info")[0][0]
    
    # 活跃用户（当日有下单）
    active_sql = f"""
    SELECT COUNT(DISTINCT o.user_id)
    FROM mall.order_info o
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    """
    active_users = mysql_query(active_sql)[0][0]
    
    # 新增用户
    new_users = mysql_query(f"SELECT COUNT(*) FROM mall.user_info WHERE DATE(create_time) = '{dt}'")[0][0]
    
    # 付费用户
    paying_sql = f"""
    SELECT COUNT(DISTINCT o.user_id)
    FROM mall.order_info o
    JOIN mall.payment_info p ON o.id = p.order_id AND p.pay_status = 1
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    """
    paying_users = mysql_query(paying_sql)[0][0]
    
    # ARPU
    pay_amount_sql = f"""
    SELECT COALESCE(ROUND(SUM(CASE WHEN p.id IS NOT NULL THEN o.total_amount ELSE 0 END) / NULLIF({paying_users}, 0), 2), 0)
    FROM mall.order_info o
    LEFT JOIN mall.payment_info p ON o.id = p.order_id AND p.pay_status = 1
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    """
    arpu = mysql_query(pay_amount_sql)[0][0]
    
    # 性别比例和等级分布
    gender_sql = f"""
    SELECT 
        ROUND(SUM(CASE WHEN u.gender = '男' THEN 1 ELSE 0 END) / COUNT(*), 4) as male_ratio,
        ROUND(SUM(CASE WHEN u.gender = '女' THEN 1 ELSE 0 END) / COUNT(*), 4) as female_ratio,
        SUM(CASE WHEN u.user_level = '普通' THEN 1 ELSE 0 END) as normal_count,
        SUM(CASE WHEN u.user_level != '普通' THEN 1 ELSE 0 END) as vip_count
    FROM mall.order_info o
    JOIN mall.user_info u ON o.user_id = u.id
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    """
    gender_rows = mysql_query(gender_sql)
    if gender_rows and gender_rows[0][0]:
        male_ratio, female_ratio, normal_count, vip_count = gender_rows[0]
    else:
        male_ratio, female_ratio, normal_count, vip_count = 0, 0, 0, 0
    
    cleaned = [{
        'dt': dt,
        'total_users': total_users,
        'active_users': active_users,
        'new_users': new_users,
        'paying_users': paying_users,
        'arpu': arpu,
        'gender_male_ratio': male_ratio,
        'gender_female_ratio': female_ratio,
        'level_normal_count': normal_count,
        'level_vip_count': vip_count
    }]
    
    write_to_hdfs(cleaned, 'ads_user_dashboard', dt,
                  ['dt', 'total_users', 'active_users', 'new_users', 'paying_users',
                   'arpu', 'gender_male_ratio', 'gender_female_ratio',
                   'level_normal_count', 'level_vip_count'],
                  'ads')
    
    return 1


def process_ads_sku_sales_top(dt, top_n=10):
    """商品销售排行榜 TOP N"""
    print(f"\n[ADS] 商品销售排行榜 (ads_sku_sales_top)")
    
    sql = f"""
    SELECT 
        s.id as sku_id,
        s.sku_name,
        c1.name as category1_name,
        SUM(od.sku_num) as sale_count,
        ROUND(SUM(od.sku_num * od.sku_price), 2) as sale_amount,
        COUNT(DISTINCT o.id) as order_count
    FROM mall.order_info o
    JOIN mall.order_detail od ON o.id = od.order_id
    JOIN mall.sku_info s ON od.sku_id = s.id
    LEFT JOIN mall.category3 c3 ON s.category3_id = c3.id
    LEFT JOIN mall.category2 c2 ON c3.category2_id = c2.id
    LEFT JOIN mall.category1 c1 ON c2.category1_id = c1.id
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    GROUP BY s.id, s.sku_name, c1.name
    ORDER BY sale_amount DESC
    LIMIT {top_n}
    """
    
    rows = mysql_query(sql)
    print(f"  TOP {top_n} 商品数: {len(rows)}")
    
    if not rows:
        return 0
    
    cleaned = []
    for i, row in enumerate(rows, 1):
        sku_id, sku_name, c1, sale_count, sale_amount, order_count = row
        cleaned.append({
            'dt': dt,
            'rank_num': i,
            'sku_id': sku_id,
            'sku_name': sku_name or '',
            'category1_name': c1 or '',
            'sale_count': sale_count,
            'sale_amount': sale_amount,
            'order_count': order_count
        })
    
    write_to_hdfs(cleaned, 'ads_sku_sales_top', dt,
                  ['dt', 'rank_num', 'sku_id', 'sku_name', 'category1_name',
                   'sale_count', 'sale_amount', 'order_count'],
                  'ads')
    
    # 打印 TOP 3
    print(f"\n  TOP 3 商品:")
    for item in cleaned[:3]:
        print(f"    {item['rank_num']}. {item['sku_name'][:20]} - ¥{item['sale_amount']:,.2f}")
    
    return len(cleaned)


def process_ads_user_rfm(dt):
    """用户 RFM 分层"""
    print(f"\n[ADS] 用户 RFM 分层 (ads_user_rfm)")
    
    # 计算 RFM 指标（近30天）
    end_date = datetime.strptime(dt, '%Y-%m-%d')
    start_date = end_date - timedelta(days=30)
    start_str = start_date.strftime('%Y-%m-%d')
    
    sql = f"""
    SELECT 
        o.user_id,
        MAX(u.nick_name) as user_nick_name,
        DATEDIFF('{dt}', MAX(DATE(o.create_time))) as recency,
        COUNT(DISTINCT o.id) as frequency,
        ROUND(SUM(o.total_amount), 2) as monetary
    FROM mall.order_info o
    JOIN mall.user_info u ON o.user_id = u.id
    WHERE DATE(o.create_time) >= '{start_str}'
      AND DATE(o.create_time) <= '{dt}'
      AND o.total_amount > 0
    GROUP BY o.user_id
    """
    
    rows = mysql_query(sql)
    print(f"  计算 RFM 用户数: {len(rows)}")
    
    if not rows:
        return 0
    
    cleaned = []
    for row in rows:
        user_id, nick_name, recency, frequency, monetary = row
        
        # R 分数
        if recency <= 3:
            r_score = 5
        elif recency <= 7:
            r_score = 4
        elif recency <= 14:
            r_score = 3
        elif recency <= 21:
            r_score = 2
        else:
            r_score = 1
        
        # F 分数
        if frequency >= 20:
            f_score = 5
        elif frequency >= 10:
            f_score = 4
        elif frequency >= 5:
            f_score = 3
        elif frequency >= 2:
            f_score = 2
        else:
            f_score = 1
        
        # M 分数
        if monetary >= 1000:
            m_score = 5
        elif monetary >= 500:
            m_score = 4
        elif monetary >= 200:
            m_score = 3
        elif monetary >= 50:
            m_score = 2
        else:
            m_score = 1
        
        # RFM 分层
        if r_score >= 4 and f_score >= 3:
            rfm_level = '重要价值客户'
        elif r_score >= 4 and f_score <= 2:
            rfm_level = '重要发展客户'
        elif r_score <= 2 and f_score >= 3:
            rfm_level = '重要保持客户'
        elif r_score <= 2 and f_score <= 2:
            rfm_level = '重要挽留客户'
        elif r_score >= 3:
            rfm_level = '一般价值客户'
        else:
            rfm_level = '流失客户'
        
        cleaned.append({
            'user_id': user_id,
            'user_nick_name': nick_name or '',
            'recency': recency,
            'frequency': frequency,
            'monetary': monetary,
            'r_score': r_score,
            'f_score': f_score,
            'm_score': m_score,
            'rfm_level': rfm_level,
            'dt': dt
        })
    
    write_to_hdfs(cleaned, 'ads_user_rfm', dt,
                  ['user_id', 'user_nick_name', 'recency', 'frequency', 'monetary',
                   'r_score', 'f_score', 'm_score', 'rfm_level', 'dt'],
                  'ads')
    
    # 统计各分层用户数
    level_stats = defaultdict(int)
    for row in cleaned:
        level_stats[row['rfm_level']] += 1
    
    print(f"\n  RFM 分层统计:")
    for level, count in sorted(level_stats.items(), key=lambda x: -x[1]):
        print(f"    {level}: {count} 人")
    
    return len(cleaned)


# ==================== 主入口 ====================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 dws_ads_etl.py <dt>")
        print("示例: python3 dws_ads_etl.py 2026-08-20")
        sys.exit(1)
    
    dt = sys.argv[1]
    
    print(f"\n{'#'*60}")
    print(f"# DWS + ADS 数据加工")
    print(f"# 日期: {dt}")
    print(f"{'#'*60}")
    
    total = 0
    
    # DWS 层加工
    total += process_dws_user_day_agg(dt)
    total += process_dws_sku_day_agg(dt)
    total += process_dws_order_day_agg(dt)
    total += process_dws_category_day_agg(dt)
    
    # ADS 层加工
    total += process_ads_gmv_day(dt)
    total += process_ads_user_dashboard(dt)
    total += process_ads_sku_sales_top(dt)
    total += process_ads_user_rfm(dt)
    
    print(f"\n{'#'*60}")
    print(f"# DWS + ADS 加工完成")
    print(f"# 日期: {dt}")
    print(f"# 总行数: {total}")
    print(f"{'#'*60}")
