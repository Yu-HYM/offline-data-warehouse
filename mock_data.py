#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商离线数仓 - 业务数据生成器（造数器）
用法:
  python3 mock_data.py init 2026-08-19   # 初始化30天历史数据
  python3 mock_data.py day 2026-08-20   # 增量生成单日数据
"""

import sys
import random
import json
import os
import pymysql
from datetime import datetime, timedelta

# ==================== 数据库连接 ====================
conn = pymysql.connect(
    host="localhost",
    user="root",
    password="123456",
    database="mall",
    charset="utf8mb4"
)
cur = conn.cursor()

# ==================== 工具函数 ====================

def rand_dt(day: str) -> str:
    """生成指定日期的随机时间"""
    return f"{day} {random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"


def maybe_dirty(v, max_len=None):
    """约 5% 概率注入脏数据：
    - 2% 返回 None（空值）
    - 1.5% 返回负值或非法时间
    """
    r = random.random()
    if r < 0.02:
        return None
    if r < 0.035:
        if isinstance(v, (int, float)):
            return -abs(v)
        if max_len:
            return "异常"  # 短脏值
        return "1970-01-01 00:00:00"
    return v


# ==================== 数据生成函数 ====================

def gen_users(day: str, n: int):
    """生成用户数据"""
    for _ in range(n):
        uid = random.randint(100000, 999999)
        phone = f"1{random.randint(3000000000, 8999999999)}"
        login_name = f"user_{uid}"
        nick_name = f"用户{uid}"
        gender = random.choice([0, 1])
        user_level = random.choice([1, 2, 3])
        create_time = rand_dt(day)
        
        cur.execute(
            "INSERT INTO user_info (login_name, nick_name, phone, gender, user_level, create_time, operate_time) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                maybe_dirty(login_name),
                maybe_dirty(nick_name),
                maybe_dirty(phone, max_len=11),
                gender,
                user_level,
                maybe_dirty(create_time),
                maybe_dirty(create_time),
            ),
        )


def gen_skus(n: int):
    """生成商品SKU数据（仅初始化时调用一次）"""
    for _ in range(n):
        sku_name = f"商品{random.randint(1000, 9999)}"
        category3_id = random.randint(1, 5)
        price = round(random.uniform(10, 5000), 2)
        
        cur.execute(
            "INSERT INTO sku_info (sku_name, category3_id, price, create_time, operate_time) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                maybe_dirty(sku_name),
                category3_id,
                maybe_dirty(price),
                "2026-01-01 00:00:00",
                "2026-01-01 00:00:00",
            ),
        )


def gen_orders(day: str, order_n: int, user_ids: list):
    """生成订单数据（含订单明细和支付记录）"""
    for _ in range(order_n):
        uid = random.choice(user_ids)
        amount = round(random.uniform(20, 3000), 2)
        status = random.choices([1, 2], [8, 2])[0]  # 80%已支付，20%已取消
        ct = rand_dt(day)

        # 订单主表
        cur.execute(
            "INSERT INTO order_info (user_id, total_amount, status, create_time, operate_time) "
            "VALUES (%s, %s, %s, %s, %s)",
            (uid, maybe_dirty(amount), status, maybe_dirty(ct), maybe_dirty(ct)),
        )
        oid = cur.lastrowid

        # 订单明细（1~4件商品）
        for _ in range(random.randint(1, 4)):
            sku_id = random.randint(1, 200)
            sku_num = random.randint(1, 3)
            sku_price = round(random.uniform(10, 2000), 2)
            cur.execute(
                "INSERT INTO order_detail (order_id, sku_id, sku_num, sku_price, create_time) "
                "VALUES (%s, %s, %s, %s, %s)",
                (oid, sku_id, sku_num, sku_price, maybe_dirty(ct)),
            )

        # 支付记录（85%的订单有支付记录）
        if random.random() < 0.85 and status == 1:
            cur.execute(
                "INSERT INTO payment_info (order_id, pay_amount, pay_status, create_time, operate_time) "
                "VALUES (%s, %s, 1, %s, %s)",
                (oid, amount, ct, ct),
            )


def gen_log(day: str, n: int):
    """生成用户行为埋点日志（JSON格式，写入文件）"""
    log_dir = f"/opt/script/mall/mock/logs"
    os.makedirs(log_dir, exist_ok=True)
    log_path = f"{log_dir}/{day}.log"

    actions = ["page_view", "click", "cart_add", "favor", "buy"]

    with open(log_path, "a", encoding="utf-8") as f:
        for _ in range(n):
            ev = {
                "event_id": random.randint(10**8, 10**9),
                "user_id": random.randint(1, 2000),
                "action": random.choices(actions, [4, 3, 2, 1, 2])[0],
                "sku_id": random.randint(1, 200),
                "ts": rand_dt(day),
            }
            # 5% 概率某个字段为 None（埋点脏数据）
            if random.random() < 0.05:
                ev[random.choice(["user_id", "ts", "action"])] = None
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def user_change(day: str, user_ids: list):
    """随机修改5个老用户手机号，用于驱动 SCD2 拉链表"""
    for uid in random.sample(user_ids, min(5, len(user_ids))):
        new_phone = f"1{random.randint(3000000000, 8999999999)}"
        operate_time = rand_dt(day)
        cur.execute(
            "UPDATE user_info SET phone=%s, operate_time=%s WHERE id=%s",
            (new_phone, operate_time, uid),
        )


# ==================== 主入口 ====================

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "init"

    if mode == "init":
        day0 = sys.argv[2]
        print(f"[初始化] 从 {day0} 开始生成 30 天历史数据...")

        # 商品只生成一次
        gen_skus(200)
        print(f"  ✓ 商品数据: 200 条")

        # 30 天循环
        for i in range(30):
            d = (datetime.strptime(day0, "%Y-%m-%d") - timedelta(days=29 - i)).strftime("%Y-%m-%d")
            gen_users(d, random.randint(20, 60))
            cur.execute("SELECT id FROM user_info WHERE create_time < %s", (d + " 23:59:59",))
            user_ids = [r[0] for r in cur.fetchall()]
            gen_orders(d, random.randint(100, 300), user_ids)
            gen_log(d, 5000)
            
            if (i + 1) % 5 == 0:
                print(f"  ... 已生成 {i + 1}/30 天")

        conn.commit()
        print(f"[完成] 30 天历史数据生成完毕")

    elif mode == "day":
        d = sys.argv[2]
        print(f"[增量] 生成 {d} 当日数据...")

        # 新增用户
        gen_users(d, random.randint(10, 30))

        # 获取所有用户
        cur.execute("SELECT id FROM user_info")
        ids = [r[0] for r in cur.fetchall()]

        # 老用户信息变更（驱动 SCD2）
        user_change(d, ids)

        # 新增订单
        gen_orders(d, random.randint(80, 200), ids)

        # 行为日志
        gen_log(d, 5000)

        conn.commit()
        print(f"[完成] {d} 当日增量数据生成完毕")

    else:
        print("用法:")
        print("  python3 mock_data.py init 2026-08-19   # 初始化30天历史数据")
        print("  python3 mock_data.py day 2026-08-20   # 增量生成单日数据")
        sys.exit(1)

    conn.close()
    print("mock done:", mode)
