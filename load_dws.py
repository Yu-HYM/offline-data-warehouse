#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加载 DWS 数据到 Hive ORC 内部表
支持多天数据加载
"""

import subprocess
import sys
import os


def run_cmd(cmd, timeout=120):
    """执行Shell命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, executable='/bin/bash'
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  命令执行超时 ({timeout}s)")
        return "", -1


def load_dws(dt):
    """加载一天的 DWS 数据到 ORC 内部表"""
    
    # 构建 Hive SQL
    hive_sql = f"""
USE mall;

-- 清理旧临时表
DROP TABLE IF EXISTS tmp_user_dws_text;
DROP TABLE IF EXISTS tmp_sku_dws_text;

-- 1. 用户交易日宽表临时外部表
CREATE EXTERNAL TABLE tmp_user_dws_text(
    user_id STRING,
    user_nick_name STRING,
    user_level STRING,
    gender STRING,
    order_count_1d BIGINT,
    order_amount_1d DECIMAL(16,2),
    pay_amount_1d DECIMAL(16,2),
    order_sku_count_1d BIGINT,
    category_count_1d INT,
    avg_order_amount_1d DECIMAL(16,2)
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dws_load/user';

ALTER TABLE tmp_user_dws_text ADD IF NOT EXISTS PARTITION (dt='{dt}');

-- 2. 商品交易日宽表临时外部表
CREATE EXTERNAL TABLE tmp_sku_dws_text(
    sku_id STRING,
    sku_name STRING,
    category1_name STRING,
    category2_name STRING,
    category3_name STRING,
    order_count_1d BIGINT,
    sale_count_1d BIGINT,
    sale_amount_1d DECIMAL(16,2),
    order_user_count_1d BIGINT,
    avg_price_1d DECIMAL(16,2)
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dws_load/sku';

ALTER TABLE tmp_sku_dws_text ADD IF NOT EXISTS PARTITION (dt='{dt}');

-- 3. 设置优化参数
SET hive.exec.mode.local.auto=true;
SET hive.exec.mode.local.auto.inputbytes.max=128000000;

-- 4. 加载用户数据
INSERT OVERWRITE TABLE dws_trade_user_order_1d PARTITION (dt='{dt}')
SELECT user_id, user_nick_name, user_level, gender,
       order_count_1d, order_amount_1d, pay_amount_1d,
       order_sku_count_1d, category_count_1d, avg_order_amount_1d
FROM tmp_user_dws_text WHERE dt='{dt}';

-- 5. 加载商品数据
INSERT OVERWRITE TABLE dws_trade_sku_order_1d PARTITION (dt='{dt}')
SELECT sku_id, sku_name, category1_name, category2_name, category3_name,
       order_count_1d, sale_count_1d, sale_amount_1d,
       order_user_count_1d, avg_price_1d
FROM tmp_sku_dws_text WHERE dt='{dt}';

-- 6. 验证
SELECT '用户宽表' AS info, COUNT(*) FROM dws_trade_user_order_1d WHERE dt='{dt}';
SELECT '商品宽表' AS info, COUNT(*) FROM dws_trade_sku_order_1d WHERE dt='{dt}';

-- 7. 清理
DROP TABLE IF EXISTS tmp_user_dws_text;
DROP TABLE IF EXISTS tmp_sku_dws_text;
"""
    
    # 写入临时 SQL 文件
    sql_file = f"/tmp/load_dws_{dt}.sql"
    with open(sql_file, 'w') as f:
        f.write(hive_sql)
    
    # 执行 Hive
    print(f"\n[加载] {dt} 数据到 ORC 内部表...")
    stdout, code = run_cmd(f"source ~/.profile && hive -f {sql_file} 2>&1 | grep -E 'OK|FAILED|用户宽表|商品宽表'")
    print(f"  {stdout}")
    
    # 清理临时文件
    if os.path.exists(sql_file):
        os.remove(sql_file)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 load_dws.py <日期1> [日期2] ...")
        sys.exit(1)
    
    dates = sys.argv[1:]
    
    print("=" * 50)
    print("# 加载 DWS 数据到 Hive ORC 内部表")
    print(f"# 日期: {', '.join(dates)}")
    print("=" * 50)
    
    for dt in dates:
        load_dws(dt)
    
    print("\n✅ 全部完成")


if __name__ == "__main__":
    main()
