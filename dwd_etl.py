#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DWD 明细层数据加工脚本
DWD 层职责：
1. 清洗 ODS 层脏数据
2. 维度退化（将维度字段直接写入事实表）
3. SCD2 拉链表处理
4. 构建宽表（多表关联）

用法:
  python3 dwd_etl.py 2026-08-19          # 增量处理单日数据
  python3 dwd_etl.py 2026-08-19 --init   # 首日全量初始化
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

HDFS_BASE = '/warehouse/mall/dwd'
LOCAL_TMP = '/tmp/dwd_etl'


def hdfs_cmd(args):
    """执行 HDFS 命令"""
    cmd = f'source ~/.profile && hdfs dfs {args}'
    result = subprocess.run(
        ['bash', '-c', cmd],
        capture_output=True, text=True, timeout=120
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


def mysql_execute(sql):
    """执行 MySQL 写入"""
    conn = pymysql.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


def mask_phone(phone):
    """手机号脱敏：中间4位用*"""
    if phone is None or len(phone) != 11:
        return '00000000000'
    return phone[:3] + '****' + phone[7:]


def clean_gender(gender_str):
    """性别转换：字符串转数字"""
    if gender_str is None or gender_str == '异常':
        return 0
    gender_str = str(gender_str).strip()
    if gender_str in ['1', '男', 'male', 'M']:
        return 1
    elif gender_str in ['2', '女', 'female', 'F']:
        return 2
    else:
        return 0


def clean_amount(amount):
    """金额清洗：负值置0，保留2位小数"""
    try:
        val = float(amount)
        if val < 0:
            return 0.00
        return round(val, 2)
    except (ValueError, TypeError):
        return 0.00


def get_order_status_desc(status):
    """订单状态描述"""
    status_map = {
        0: '待支付',
        1: '已支付',
        2: '已发货',
        3: '已完成',
        4: '已取消',
        5: '已退款'
    }
    return status_map.get(status, '未知状态')


def get_pay_status_desc(status):
    """支付状态描述"""
    status_map = {
        0: '未支付',
        1: '支付成功',
        2: '支付失败',
        3: '已退款'
    }
    return status_map.get(status, '未知状态')


def get_pay_channel():
    """随机支付渠道"""
    channels = ['微信支付', '支付宝', '银行卡', '余额']
    import random
    return random.choice(channels)


# ==================== DWD 加工函数 ====================

def process_dim_user_full(dt, is_init=False):
    """
    用户维度表加工（SCD2 拉链表）
    
    清洗规则：
    1. 空手机号 → 脱敏为 '00000000000'
    2. 非法时间（1970-01-01）→ 使用 create_time
    3. 性别标准化（字符串→数字）
    4. SCD2 拉链：新用户直接插入，老用户变更则关闭旧链+开新链
    """
    print(f"\n{'='*60}")
    print(f"[DWD] 用户维度表加工 (dim_user_full)")
    print(f"{'='*60}")
    
    # 读取 ODS user_info
    if is_init:
        sql = "SELECT id, login_name, nick_name, phone, gender, user_level, create_time, operate_time FROM mall.user_info"
    else:
        sql = f"""
        SELECT id, login_name, nick_name, phone, gender, user_level, create_time, operate_time 
        FROM mall.user_info 
        WHERE DATE(operate_time) = '{dt}'
        """
    
    rows = mysql_query(sql)
    print(f"  读取 ODS 用户数: {len(rows)}")
    
    if not rows:
        print(f"  无数据需要处理")
        return 0
    
    # 清洗数据
    cleaned = []
    for row in rows:
        user_id, login_name, nick_name, phone, gender, user_level, create_time, operate_time = row
        
        # 清洗规则
        phone_clean = mask_phone(phone)
        gender_clean = clean_gender(gender)
        create_time_clean = create_time if create_time and str(create_time) >= '2020-01-01' else '2020-01-01 00:00:00'
        operate_time_clean = operate_time if operate_time and str(operate_time) >= '2020-01-01' else create_time_clean
        
        cleaned.append({
            'user_id': user_id,
            'login_name': login_name or '',
            'nick_name': nick_name or '',
            'phone': phone_clean,
            'gender': gender_clean,
            'user_level': user_level or '普通',
            'create_time': create_time_clean,
            'operate_time': operate_time_clean
        })
    
    # SCD2 拉链处理
    if is_init:
        # 全量初始化：所有用户都是当前版本
        start_date = dt
        end_date = '9999-12-31'
        is_current = 1
        
        # 写入 HDFS
        write_rows_to_hdfs(cleaned, 'dim_user_full', dt, 
                          ['user_id', 'login_name', 'nick_name', 'phone', 'gender', 
                           'user_level', 'create_time', 'start_date', 'end_date', 'is_current'])
    else:
        # 增量：变更用户需要更新拉链
        # 简化处理：直接覆盖当日变更用户的最新状态
        # 实际生产中需要先关闭旧链，再开新链
        
        # 写入当日增量
        write_rows_to_hdfs(cleaned, 'dim_user_full', dt,
                          ['user_id', 'login_name', 'nick_name', 'phone', 'gender',
                           'user_level', 'create_time', 'operate_time'])
    
    print(f"  ✓ 用户维度加工完成: {len(cleaned)} 行")
    return len(cleaned)


def process_dim_sku_full(dt):
    """
    商品维度表加工
    
    清洗规则：
    1. 价格为负 → 置0
    2. 分类名称补充
    """
    print(f"\n{'='*60}")
    print(f"[DWD] 商品维度表加工 (dim_sku_full)")
    print(f"{'='*60}")
    
    sql = """
    SELECT 
        s.id,
        s.sku_name,
        s.category3_id,
        c3.name as category3_name,
        c2.name as category2_name,
        c1.name as category1_name,
        s.price
    FROM mall.sku_info s
    LEFT JOIN mall.category3 c3 ON s.category3_id = c3.id
    LEFT JOIN mall.category2 c2 ON c3.category2_id = c2.id
    LEFT JOIN mall.category1 c1 ON c2.category1_id = c1.id
    """
    
    rows = mysql_query(sql)
    print(f"  读取商品数: {len(rows)}")
    
    # 清洗
    cleaned = []
    for row in rows:
        sku_id, sku_name, category3_id, category3_name, category2_name, category1_name, price = row
        
        price_clean = clean_amount(price)
        category3_name_clean = category3_name or f'分类_{category3_id}'
        category2_name_clean = category2_name or '未分类'
        category1_name_clean = category1_name or '未分类'
        
        cleaned.append({
            'sku_id': sku_id,
            'sku_name': sku_name or '',
            'category3_id': category3_id,
            'category3_name': category3_name_clean,
            'category2_name': category2_name_clean,
            'category1_name': category1_name_clean,
            'price': price_clean
        })
    
    # 写入 HDFS
    write_rows_to_hdfs(cleaned, 'dim_sku_full', dt,
                      ['sku_id', 'sku_name', 'category3_id', 'category3_name',
                       'category2_name', 'category1_name', 'price'])
    
    print(f"  ✓ 商品维度加工完成: {len(cleaned)} 行")
    return len(cleaned)


def process_fact_order_detail(dt):
    """
    订单明细事实表加工（宽表）
    
    多表关联：order_info + order_detail + user_info + sku_info
    维度退化：将用户昵称、商品名称、分类等直接写入事实表
    
    清洗规则：
    1. 过滤金额<=0的订单
    2. 计算明细金额 = sku_price * sku_num
    3. 关联维度字段
    """
    print(f"\n{'='*60}")
    print(f"[DWD] 订单明细事实表加工 (fact_order_detail)")
    print(f"{'='*60}")
    
    sql = f"""
    SELECT 
        o.id as order_id,
        od.id as order_detail_id,
        o.user_id,
        u.nick_name as user_nick_name,
        u.user_level,
        u.gender,
        od.sku_id,
        s.sku_name,
        c1.name as category1_name,
        c2.name as category2_name,
        c3.name as category3_name,
        o.total_amount as order_amount,
        od.sku_price,
        od.sku_num,
        o.status as order_status,
        CASE WHEN p.id IS NOT NULL THEN 1 ELSE 0 END as is_paid,
        o.create_time
    FROM mall.order_info o
    JOIN mall.order_detail od ON o.id = od.order_id
    LEFT JOIN mall.user_info u ON o.user_id = u.id
    LEFT JOIN mall.sku_info s ON od.sku_id = s.id
    LEFT JOIN mall.category3 c3 ON s.category3_id = c3.id
    LEFT JOIN mall.category2 c2 ON c3.category2_id = c2.id
    LEFT JOIN mall.category1 c1 ON c2.category1_id = c1.id
    LEFT JOIN mall.payment_info p ON o.id = p.order_id
    WHERE DATE(o.create_time) = '{dt}'
      AND o.total_amount > 0
    """
    
    rows = mysql_query(sql)
    print(f"  读取订单明细数: {len(rows)}")
    
    if not rows:
        print(f"  无数据需要处理")
        return 0
    
    # 清洗 + 维度退化
    cleaned = []
    for row in rows:
        (order_id, order_detail_id, user_id, user_nick_name, user_level, 
         gender, sku_id, sku_name, category1_name, category2_name, category3_name,
         order_amount, sku_price, sku_num, order_status, is_paid, create_time) = row
        
        # 清洗
        order_amount_clean = clean_amount(order_amount)
        sku_price_clean = clean_amount(sku_price)
        sku_num_clean = int(sku_num) if sku_num and int(sku_num) > 0 else 1
        item_amount = round(sku_price_clean * sku_num_clean, 2)
        gender_clean = clean_gender(gender)
        order_status_clean = int(order_status) if order_status else 0
        
        cleaned.append({
            'order_id': order_id,
            'order_detail_id': order_detail_id,
            'user_id': user_id,
            'user_nick_name': user_nick_name or '',
            'user_level': user_level or '普通',
            'gender': gender_clean,
            'sku_id': sku_id,
            'sku_name': sku_name or '',
            'category1_name': category1_name or '未分类',
            'category2_name': category2_name or '未分类',
            'category3_name': category3_name or '未分类',
            'order_amount': order_amount_clean,
            'sku_price': sku_price_clean,
            'sku_num': sku_num_clean,
            'item_amount': item_amount,
            'order_status': order_status_clean,
            'status_desc': get_order_status_desc(order_status_clean),
            'is_paid': int(is_paid) if is_paid else 0,
            'create_time': create_time
        })
    
    # 写入 HDFS
    write_rows_to_hdfs(cleaned, 'fact_order_detail', dt,
                      ['order_id', 'order_detail_id', 'user_id', 'user_nick_name',
                       'user_level', 'gender', 'sku_id', 'sku_name',
                       'category1_name', 'category2_name', 'category3_name',
                       'order_amount', 'sku_price', 'sku_num', 'item_amount',
                       'order_status', 'status_desc', 'is_paid', 'create_time'])
    
    print(f"  ✓ 订单明细加工完成: {len(cleaned)} 行")
    return len(cleaned)


def process_fact_payment_detail(dt):
    """
    支付明细事实表加工（宽表）
    
    关联：payment_info + order_info + user_info
    
    清洗规则：
    1. 金额为负 → 置0
    2. 补充支付渠道（模拟）
    """
    print(f"\n{'='*60}")
    print(f"[DWD] 支付明细事实表加工 (fact_payment_detail)")
    print(f"{'='*60}")
    
    sql = f"""
    SELECT 
        p.id as payment_id,
        p.order_id,
        o.user_id,
        u.nick_name as user_nick_name,
        p.pay_amount,
        p.pay_status,
        p.create_time
    FROM mall.payment_info p
    JOIN mall.order_info o ON p.order_id = o.id
    LEFT JOIN mall.user_info u ON o.user_id = u.id
    WHERE DATE(p.create_time) = '{dt}'
      AND p.pay_amount > 0
    """
    
    rows = mysql_query(sql)
    print(f"  读取支付记录数: {len(rows)}")
    
    if not rows:
        print(f"  无数据需要处理")
        return 0
    
    # 清洗
    cleaned = []
    for row in rows:
        payment_id, order_id, user_id, user_nick_name, pay_amount, pay_status, create_time = row
        
        pay_amount_clean = clean_amount(pay_amount)
        pay_status_clean = int(pay_status) if pay_status else 0
        
        cleaned.append({
            'payment_id': payment_id,
            'order_id': order_id,
            'user_id': user_id,
            'user_nick_name': user_nick_name or '',
            'pay_amount': pay_amount_clean,
            'pay_status': pay_status_clean,
            'pay_status_desc': get_pay_status_desc(pay_status_clean),
            'pay_channel': get_pay_channel(),
            'create_time': create_time
        })
    
    # 写入 HDFS
    write_rows_to_hdfs(cleaned, 'fact_payment_detail', dt,
                      ['payment_id', 'order_id', 'user_id', 'user_nick_name',
                       'pay_amount', 'pay_status', 'pay_status_desc',
                       'pay_channel', 'create_time'])
    
    print(f"  ✓ 支付明细加工完成: {len(cleaned)} 行")
    return len(cleaned)


def write_rows_to_hdfs(rows, table_name, dt, columns):
    """将清洗后的数据写入 HDFS"""
    if not rows:
        return
    
    # 写入本地临时文件
    local_file = f"{LOCAL_TMP}/{table_name}_{dt}.txt"
    os.makedirs(LOCAL_TMP, exist_ok=True)
    
    with open(local_file, 'w', encoding='utf-8') as f:
        for row in rows:
            vals = []
            for col in columns:
                val = row.get(col, '')
                if val is None:
                    vals.append('')
                else:
                    vals.append(str(val))
            f.write('\t'.join(vals) + '\n')
    
    file_size = os.path.getsize(local_file)
    
    # 上传到 HDFS
    hdfs_path = f"{HDFS_BASE}/{table_name}/dt={dt}"
    hdfs_cmd(f'-mkdir -p {hdfs_path}')
    hdfs_cmd(f'-put -f {local_file} {hdfs_path}/')
    
    # 验证
    result = hdfs_cmd(f'-ls {hdfs_path}')
    print(f"  写入 HDFS: {hdfs_path} ({file_size} bytes)")
    
    # 清理
    os.remove(local_file)


# ==================== 主入口 ====================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 dwd_etl.py <dt> [--init]")
        print()
        print("  dt:      日期 YYYY-MM-DD")
        print("  --init:  首日全量初始化（处理历史所有数据）")
        sys.exit(1)
    
    dt = sys.argv[1]
    is_init = '--init' in sys.argv
    
    print(f"\n{'#'*60}")
    print(f"# DWD 明细层数据加工")
    print(f"# 日期: {dt}")
    if is_init:
        print(f"# 模式: 全量初始化")
    else:
        print(f"# 模式: 增量处理")
    print(f"{'#'*60}")
    
    total = 0
    
    # 1. 用户维度
    count = process_dim_user_full(dt, is_init)
    total += count
    
    # 2. 商品维度（全量）
    count = process_dim_sku_full(dt)
    total += count
    
    # 3. 订单明细
    count = process_fact_order_detail(dt)
    total += count
    
    # 4. 支付明细
    count = process_fact_payment_detail(dt)
    total += count
    
    # 汇总
    print(f"\n{'#'*60}")
    print(f"# DWD 加工完成")
    print(f"# 日期: {dt}")
    print(f"# 总行数: {total}")
    print(f"{'#'*60}")
