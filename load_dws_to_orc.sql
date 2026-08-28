-- =============================================================
-- 阶段六：DWS 聚合宽表 - 加载数据到 ORC 内部表（简化版）
-- =============================================================

USE mall;

-- 清理旧的临时表
DROP TABLE IF EXISTS tmp_user_dws_text;
DROP TABLE IF EXISTS tmp_sku_dws_text;

-- 1. 创建用户交易日宽表临时外部表
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
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dws_load/user';

-- 手动添加分区
ALTER TABLE tmp_user_dws_text ADD IF NOT EXISTS PARTITION (dt='2026-08-20');

-- 2. 创建商品交易日宽表临时外部表
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
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dws_load/sku';

-- 手动添加分区
ALTER TABLE tmp_sku_dws_text ADD IF NOT EXISTS PARTITION (dt='2026-08-20');

-- 3. 设置优化参数
SET hive.exec.mode.local.auto=true;
SET hive.exec.mode.local.auto.inputbytes.max=128000000;

-- 4. 加载用户数据到 ORC 内部表
INSERT OVERWRITE TABLE dws_trade_user_order_1d PARTITION (dt='2026-08-20')
SELECT 
    user_id,
    user_nick_name,
    user_level,
    gender,
    order_count_1d,
    order_amount_1d,
    pay_amount_1d,
    order_sku_count_1d,
    category_count_1d,
    avg_order_amount_1d
FROM tmp_user_dws_text
WHERE dt='2026-08-20';

-- 5. 加载商品数据到 ORC 内部表
INSERT OVERWRITE TABLE dws_trade_sku_order_1d PARTITION (dt='2026-08-20')
SELECT 
    sku_id,
    sku_name,
    category1_name,
    category2_name,
    category3_name,
    order_count_1d,
    sale_count_1d,
    sale_amount_1d,
    order_user_count_1d,
    avg_price_1d
FROM tmp_sku_dws_text
WHERE dt='2026-08-20';

-- 6. 验证结果
SELECT '用户宽表' AS info, COUNT(*) AS cnt 
FROM dws_trade_user_order_1d WHERE dt='2026-08-20';

SELECT '商品宽表' AS info, COUNT(*) AS cnt 
FROM dws_trade_sku_order_1d WHERE dt='2026-08-20';

-- 7. 清理临时表
DROP TABLE IF EXISTS tmp_user_dws_text;
DROP TABLE IF EXISTS tmp_sku_dws_text;
