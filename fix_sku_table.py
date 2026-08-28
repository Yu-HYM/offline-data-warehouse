#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 sku_info 表 ID 不匹配问题
重新生成 200 条商品数据，id 从 1 开始
"""

import pymysql
import random
from datetime import datetime

MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'mall',
    'charset': 'utf8mb4'
}

# 商品名称模板
prefixes = ['智能', '高端', '经典', '时尚', '豪华', '便携', '专业', '入门', '旗舰', '精选']
suffixes = ['手机', '电脑', '平板', '冰箱', '洗衣机', '空调', '电视', '热水器', '电饭煲', '电风扇',
            '吸尘器', '豆浆机', '电水壶', '油烟机', '燃气灶', '微波炉', '烤箱', '净水器', 'T恤', '衬衫',
            '裤装', '外套', '西装', '连衣裙', '上衣', '女裤', '女鞋', '女包', '跑步鞋', '篮球鞋',
            '休闲鞋', '帆布鞋', '坚果', '饼干', '糖果', '蜜饯', '肉干', '蔬菜', '水果', '海鲜',
            '粮油', '调味', '精华液', '面膜', '面霜', '口红', '粉底液', '洗发水', '沐浴露', '牙膏']

def main():
    conn = pymysql.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    
    # 删除旧数据
    cur.execute("DELETE FROM mall.sku_info")
    cur.execute("ALTER TABLE mall.sku_info AUTO_INCREMENT = 1")
    
    # 生成 200 条商品
    batch = []
    for i in range(1, 201):
        prefix = prefixes[i % len(prefixes)]
        suffix = suffixes[i % len(suffixes)]
        name = f"{prefix}{suffix}{i:04d}"
        
        # category3_id 在 1-50 范围内
        category3_id = (i % 50) + 1
        
        # 价格 10-10000
        price = round(random.uniform(10, 10000), 2)
        
        create_time = f"2026-07-21 {random.randint(8,20):02d}:{random.randint(0,59):02d}:00"
        operate_time = create_time
        
        batch.append((i, name, category3_id, price, create_time, operate_time))
        
        if len(batch) >= 100:
            cur.executemany(
                "INSERT INTO mall.sku_info (id, sku_name, category3_id, price, create_time, operate_time) VALUES (%s, %s, %s, %s, %s, %s)",
                batch
            )
            batch = []
    
    if batch:
        cur.executemany(
            "INSERT INTO mall.sku_info (id, sku_name, category3_id, price, create_time, operate_time) VALUES (%s, %s, %s, %s, %s, %s)",
            batch
        )
    
    conn.commit()
    
    # 验证
    cur.execute("SELECT COUNT(*) FROM mall.sku_info")
    count = cur.fetchone()[0]
    
    cur.execute("SELECT MIN(id), MAX(id) FROM mall.sku_info")
    min_id, max_id = cur.fetchone()
    
    print(f"✅ sku_info 表修复完成")
    print(f"   商品总数: {count}")
    print(f"   ID 范围: {min_id} ~ {max_id}")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
