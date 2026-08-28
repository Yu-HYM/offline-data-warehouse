-- =============================================================
-- 阶段四：DWD 明细层建表
-- DWD 层职责：清洗脏数据 + 维度退化 + SCD 拉链
-- =============================================================

USE mall;

-- 1. 删除旧表
DROP TABLE IF EXISTS dim_user_full;
DROP TABLE IF EXISTS dim_sku_full;
DROP TABLE IF EXISTS fact_order_detail;
DROP TABLE IF EXISTS fact_payment_detail;

-- =============================================================
-- 2. 用户维度表（SCD2 拉链表）
-- =============================================================
CREATE TABLE IF NOT EXISTS dim_user_full (
    user_id         BIGINT      COMMENT '用户ID',
    login_name      STRING      COMMENT '登录名',
    nick_name       STRING      COMMENT '昵称',
    phone           STRING      COMMENT '手机号',
    gender          INT         COMMENT '性别',
    user_level      STRING      COMMENT '用户等级',
    create_time     TIMESTAMP   COMMENT '注册时间',
    start_date      STRING      COMMENT '拉链开始日期',
    end_date        STRING      COMMENT '拉链结束日期',
    is_current      INT         COMMENT '是否当前版本'
)
PARTITIONED BY (dt STRING)
STORED AS ORC;

-- =============================================================
-- 3. 商品维度表
-- =============================================================
CREATE TABLE IF NOT EXISTS dim_sku_full (
    sku_id          BIGINT      COMMENT '商品ID',
    sku_name        STRING      COMMENT '商品名称',
    category3_id    BIGINT      COMMENT '三级分类ID',
    category3_name  STRING      COMMENT '三级分类名称',
    category2_id    BIGINT      COMMENT '二级分类ID',
    category2_name  STRING      COMMENT '二级分类名称',
    category1_id    BIGINT      COMMENT '一级分类ID',
    category1_name  STRING      COMMENT '一级分类名称',
    price           DECIMAL(10,2) COMMENT '商品价格'
)
PARTITIONED BY (dt STRING)
STORED AS ORC;

-- =============================================================
-- 4. 订单明细事实表（宽表）
-- =============================================================
CREATE TABLE IF NOT EXISTS fact_order_detail (
    order_id        BIGINT      COMMENT '订单ID',
    order_detail_id BIGINT      COMMENT '订单明细ID',
    user_id         BIGINT      COMMENT '用户ID',
    user_nick_name  STRING      COMMENT '用户昵称',
    user_level      STRING      COMMENT '用户等级',
    gender          INT         COMMENT '性别',
    sku_id          BIGINT      COMMENT '商品ID',
    sku_name        STRING      COMMENT '商品名称',
    category1_name  STRING      COMMENT '一级分类',
    category2_name  STRING      COMMENT '二级分类',
    category3_name  STRING      COMMENT '三级分类',
    order_amount    DECIMAL(10,2) COMMENT '订单总额',
    sku_price       DECIMAL(10,2) COMMENT '商品单价',
    sku_num         INT         COMMENT '购买数量',
    item_amount     DECIMAL(10,2) COMMENT '明细金额',
    order_status    INT         COMMENT '订单状态',
    status_desc     STRING      COMMENT '状态描述',
    is_paid         INT         COMMENT '是否已支付',
    create_time     TIMESTAMP   COMMENT '创建时间'
)
PARTITIONED BY (dt STRING)
STORED AS ORC;

-- =============================================================
-- 5. 支付明细事实表（宽表）
-- =============================================================
CREATE TABLE IF NOT EXISTS fact_payment_detail (
    payment_id      BIGINT      COMMENT '支付ID',
    order_id        BIGINT      COMMENT '订单ID',
    user_id         BIGINT      COMMENT '用户ID',
    user_nick_name  STRING      COMMENT '用户昵称',
    pay_amount      DECIMAL(10,2) COMMENT '支付金额',
    pay_status      INT         COMMENT '支付状态',
    pay_status_desc STRING      COMMENT '状态描述',
    pay_channel     STRING      COMMENT '支付渠道',
    create_time     TIMESTAMP   COMMENT '支付时间'
)
PARTITIONED BY (dt STRING)
STORED AS ORC;

-- 6. 验证
DESC dim_user_full;
DESC fact_order_detail;
