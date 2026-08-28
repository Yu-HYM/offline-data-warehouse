-- =============================================================
-- 阶段五：DWS + ADS Hive 外部表
-- =============================================================

USE mall;

-- 删除旧表
DROP TABLE IF EXISTS dws_user_day_agg;
DROP TABLE IF EXISTS dws_sku_day_agg;
DROP TABLE IF EXISTS dws_order_day_agg;
DROP TABLE IF EXISTS dws_category_day_agg;
DROP TABLE IF EXISTS ads_gmv_day;
DROP TABLE IF EXISTS ads_user_dashboard;
DROP TABLE IF EXISTS ads_sku_sales_top;
DROP TABLE IF EXISTS ads_user_rfm;

-- =============================================================
-- DWS 层外部表
-- =============================================================

-- 1. 用户每日汇总表
CREATE EXTERNAL TABLE IF NOT EXISTS dws_user_day_agg (
    user_id         BIGINT      COMMENT '用户ID',
    user_nick_name  STRING      COMMENT '用户昵称',
    user_level      STRING      COMMENT '用户等级',
    gender          INT         COMMENT '性别',
    order_count     INT         COMMENT '下单数',
    order_amount    DECIMAL(10,2) COMMENT '下单金额',
    pay_amount      DECIMAL(10,2) COMMENT '支付金额',
    item_count      INT         COMMENT '购买商品数',
    is_active       INT         COMMENT '是否活跃'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dws/dws_user_day_agg';

-- 2. 商品每日汇总表
CREATE EXTERNAL TABLE IF NOT EXISTS dws_sku_day_agg (
    sku_id          BIGINT      COMMENT '商品ID',
    sku_name        STRING      COMMENT '商品名称',
    category1_name  STRING      COMMENT '一级分类',
    category2_name  STRING      COMMENT '二级分类',
    category3_name  STRING      COMMENT '三级分类',
    sale_count      INT         COMMENT '销售数量',
    sale_amount     DECIMAL(10,2) COMMENT '销售金额',
    order_user_count INT        COMMENT '购买用户数',
    order_count     INT         COMMENT '订单数'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dws/dws_sku_day_agg';

-- 3. 订单每日汇总表
CREATE EXTERNAL TABLE IF NOT EXISTS dws_order_day_agg (
    total_order_count   INT         COMMENT '订单总数',
    total_order_amount  DECIMAL(12,2) COMMENT '订单总金额',
    total_pay_amount    DECIMAL(12,2) COMMENT '支付总金额',
    paid_order_count    INT         COMMENT '已支付订单数',
    cancelled_count     INT         COMMENT '已取消订单数',
    new_user_count      INT         COMMENT '新下单用户数',
    avg_order_amount    DECIMAL(10,2) COMMENT '客单价',
    pay_rate            DECIMAL(5,4) COMMENT '支付率'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dws/dws_order_day_agg';

-- 4. 分类每日汇总表
CREATE EXTERNAL TABLE IF NOT EXISTS dws_category_day_agg (
    category1_id    BIGINT      COMMENT '一级分类ID',
    category1_name  STRING      COMMENT '一级分类名称',
    category2_id    BIGINT      COMMENT '二级分类ID',
    category2_name  STRING      COMMENT '二级分类名称',
    sale_count      INT         COMMENT '销售数量',
    sale_amount     DECIMAL(12,2) COMMENT '销售金额',
    order_count     INT         COMMENT '订单数'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/dws/dws_category_day_agg';

-- =============================================================
-- ADS 层外部表
-- =============================================================

-- 1. GMV 日报表
CREATE EXTERNAL TABLE IF NOT EXISTS ads_gmv_day (
    dt              STRING      COMMENT '日期',
    gmv             DECIMAL(12,2) COMMENT 'GMV',
    pay_amount      DECIMAL(12,2) COMMENT '实际支付金额',
    order_count     INT         COMMENT '订单数',
    pay_order_count INT         COMMENT '支付订单数',
    customer_count  INT         COMMENT '下单用户数',
    new_user_count  INT         COMMENT '新下单用户数',
    avg_order_value DECIMAL(10,2) COMMENT '客单价',
    pay_rate        DECIMAL(5,4) COMMENT '支付率'
)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ads/ads_gmv_day';

-- 2. 用户看板
CREATE EXTERNAL TABLE IF NOT EXISTS ads_user_dashboard (
    dt                  STRING  COMMENT '日期',
    total_users         INT     COMMENT '总用户数',
    active_users        INT     COMMENT '活跃用户数',
    new_users           INT     COMMENT '新增用户数',
    paying_users        INT     COMMENT '付费用户数',
    arpu                DECIMAL(10,2) COMMENT 'ARPU',
    gender_male_ratio   DECIMAL(5,4) COMMENT '男性占比',
    gender_female_ratio DECIMAL(5,4) COMMENT '女性占比',
    level_normal_count  INT     COMMENT '普通用户数',
    level_vip_count     INT     COMMENT 'VIP用户数'
)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ads/ads_user_dashboard';

-- 3. 商品销售排行榜
CREATE EXTERNAL TABLE IF NOT EXISTS ads_sku_sales_top (
    dt              STRING      COMMENT '日期',
    rank_num        INT         COMMENT '排名',
    sku_id          BIGINT      COMMENT '商品ID',
    sku_name        STRING      COMMENT '商品名称',
    category1_name  STRING      COMMENT '一级分类',
    sale_count      INT         COMMENT '销售数量',
    sale_amount     DECIMAL(12,2) COMMENT '销售金额',
    order_count     INT         COMMENT '订单数'
)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ads/ads_sku_sales_top';

-- 4. 用户 RFM 分层表
CREATE EXTERNAL TABLE IF NOT EXISTS ads_user_rfm (
    user_id         BIGINT      COMMENT '用户ID',
    user_nick_name  STRING      COMMENT '用户昵称',
    recency         INT         COMMENT '最近下单天数',
    frequency       INT         COMMENT '下单次数',
    monetary        DECIMAL(12,2) COMMENT '消费金额',
    r_score         INT         COMMENT 'R分数',
    f_score         INT         COMMENT 'F分数',
    m_score         INT         COMMENT 'M分数',
    rfm_level       STRING      COMMENT 'RFM分层',
    dt              STRING      COMMENT '统计日期'
)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ads/ads_user_rfm';

-- 修复分区元数据
MSCK REPAIR TABLE dws_user_day_agg;
MSCK REPAIR TABLE dws_sku_day_agg;
MSCK REPAIR TABLE dws_order_day_agg;
MSCK REPAIR TABLE dws_category_day_agg;

-- 验证
SHOW PARTITIONS dws_user_day_agg;
SELECT * FROM ads_gmv_day;
