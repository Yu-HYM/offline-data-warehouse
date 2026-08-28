-- =============================================================
-- 阶段六：DWS 聚合宽表（内部表，ORC 格式）
-- =============================================================

USE mall;

-- 删除旧表
DROP TABLE IF EXISTS dws_trade_user_order_1d;
DROP TABLE IF EXISTS dws_trade_sku_order_1d;

-- =============================================================
-- 1. 用户交易日粒度宽表
-- 每行代表一个用户在某一天的交易汇总
-- =============================================================
CREATE TABLE IF NOT EXISTS dws_trade_user_order_1d(
    user_id            STRING      COMMENT '用户ID',
    user_nick_name     STRING      COMMENT '用户昵称（维度退化）',
    user_level         STRING      COMMENT '用户等级（维度退化）',
    gender             STRING      COMMENT '性别（维度退化）',
    order_count_1d     BIGINT      COMMENT '当日下单数',
    order_amount_1d    DECIMAL(16,2) COMMENT '当日下单金额',
    pay_amount_1d      DECIMAL(16,2) COMMENT '当日支付金额',
    order_sku_count_1d BIGINT      COMMENT '当日购买商品件数',
    category_count_1d  INT         COMMENT '当日购买品类数',
    avg_order_amount_1d DECIMAL(16,2) COMMENT '当日客单价'
)
PARTITIONED BY (dt STRING)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- =============================================================
-- 2. 商品交易日粒度宽表
-- 每行代表一个商品在某一天的交易汇总
-- =============================================================
CREATE TABLE IF NOT EXISTS dws_trade_sku_order_1d(
    sku_id             STRING      COMMENT '商品ID',
    sku_name           STRING      COMMENT '商品名称（维度退化）',
    category1_name     STRING      COMMENT '一级分类（维度退化）',
    category2_name     STRING      COMMENT '二级分类（维度退化）',
    category3_name     STRING      COMMENT '三级分类（维度退化）',
    order_count_1d     BIGINT      COMMENT '当日订单数',
    sale_count_1d      BIGINT      COMMENT '当日销售数量',
    sale_amount_1d     DECIMAL(16,2) COMMENT '当日销售金额',
    order_user_count_1d BIGINT     COMMENT '当日购买用户数',
    avg_price_1d       DECIMAL(16,2) COMMENT '当日平均售价'
)
PARTITIONED BY (dt STRING)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 验证表结构
DESC FORMATTED dws_trade_user_order_1d;
DESC FORMATTED dws_trade_sku_order_1d;
