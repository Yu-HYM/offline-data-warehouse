-- =============================================================
-- 阶段四：DWD Hive 外部表创建（仅建表）
-- =============================================================

USE mall;

-- 1. 删除旧表
DROP TABLE IF EXISTS dwd_dim_user_full;
DROP TABLE IF EXISTS dwd_dim_sku_full;
DROP TABLE IF EXISTS dwd_fact_order_detail;
DROP TABLE IF EXISTS dwd_fact_payment_detail;

-- 2. 用户维度表
CREATE EXTERNAL TABLE IF NOT EXISTS dwd_dim_user_full (
    user_id         BIGINT,
    login_name      STRING,
    nick_name       STRING,
    phone           STRING,
    gender          INT,
    user_level      STRING,
    create_time     STRING,
    start_date      STRING,
    end_date        STRING,
    is_current      INT
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dwd/dim_user_full';

-- 3. 商品维度表
CREATE EXTERNAL TABLE IF NOT EXISTS dwd_dim_sku_full (
    sku_id          BIGINT,
    sku_name        STRING,
    category3_id    BIGINT,
    category3_name  STRING,
    category2_name  STRING,
    category1_name  STRING,
    price           DECIMAL(10,2)
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dwd/dim_sku_full';

-- 4. 订单明细事实表
CREATE EXTERNAL TABLE IF NOT EXISTS dwd_fact_order_detail (
    order_id        BIGINT,
    order_detail_id BIGINT,
    user_id         BIGINT,
    user_nick_name  STRING,
    user_level      STRING,
    gender          INT,
    sku_id          BIGINT,
    sku_name        STRING,
    category1_name  STRING,
    category2_name  STRING,
    category3_name  STRING,
    order_amount    DECIMAL(10,2),
    sku_price       DECIMAL(10,2),
    sku_num         INT,
    item_amount     DECIMAL(10,2),
    order_status    INT,
    status_desc     STRING,
    is_paid         INT,
    create_time     STRING
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dwd/fact_order_detail';

-- 5. 支付明细事实表
CREATE EXTERNAL TABLE IF NOT EXISTS dwd_fact_payment_detail (
    payment_id      BIGINT,
    order_id        BIGINT,
    user_id         BIGINT,
    user_nick_name  STRING,
    pay_amount      DECIMAL(10,2),
    pay_status      INT,
    pay_status_desc STRING,
    pay_channel     STRING,
    create_time     STRING
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dwd/fact_payment_detail';

-- 6. 修复分区
MSCK REPAIR TABLE dwd_dim_user_full;
MSCK REPAIR TABLE dwd_dim_sku_full;
MSCK REPAIR TABLE dwd_fact_order_detail;
MSCK REPAIR TABLE dwd_fact_payment_detail;
