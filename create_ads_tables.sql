-- =============================================================
-- 阶段七：ADS 指标层建表（ORC 内部表）
-- =============================================================

USE mall;

-- 清理旧表
DROP TABLE IF EXISTS ads_trade_stats;
DROP TABLE IF EXISTS ads_repurchase_rate;
DROP TABLE IF EXISTS ads_user_rfm;

-- =============================================================
-- 1. 每日交易核心指标表
--    GMV、订单数、支付人数、客单价
-- =============================================================
CREATE TABLE IF NOT EXISTS ads_trade_stats(
    gmv             DECIMAL(16,2) COMMENT 'GMV 商品交易总额',
    order_count     BIGINT      COMMENT '订单数',
    pay_user_count  BIGINT      COMMENT '支付用户数',
    avg_pay_amount  DECIMAL(16,2) COMMENT '客单价'
)
PARTITIONED BY (dt STRING)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- =============================================================
-- 2. 复购率指标表
--    当日下单用户中，累计下单次数>=2 的占比
-- =============================================================
CREATE TABLE IF NOT EXISTS ads_repurchase_rate(
    order_user_count        BIGINT  COMMENT '当日下单用户数',
    repurchase_user_count   BIGINT  COMMENT '复购用户数(累计>=2次)',
    repurchase_rate         DECIMAL(10,4) COMMENT '复购率'
)
PARTITIONED BY (dt STRING)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- =============================================================
-- 3. RFM 用户分层表（近30天窗口）
--    R: 最近消费时间，F: 消费频次，M: 消费金额
-- =============================================================
CREATE TABLE IF NOT EXISTS ads_user_rfm(
    user_id     STRING  COMMENT '用户ID',
    r_score     INT     COMMENT 'R分数 1-5',
    f_score     INT     COMMENT 'F分数 1-5',
    m_score     INT     COMMENT 'M分数 1-5',
    rfm_label   STRING  COMMENT 'RFM标签'
)
PARTITIONED BY (dt STRING)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- 验证
SHOW TABLES LIKE 'ads_%';
