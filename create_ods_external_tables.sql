-- =============================================================
-- 阶段三：ODS 贴源层 Hive 外部表
-- 基于 HDFS 数据创建 Hive 外部表，支持分区查询
-- =============================================================

-- 切换到 mall 数据库
USE mall;

-- 1. 删除旧表
DROP TABLE IF EXISTS user_info;
DROP TABLE IF EXISTS product_info;
DROP TABLE IF EXISTS order_info;
DROP TABLE IF EXISTS sku_info;
DROP TABLE IF EXISTS order_detail;
DROP TABLE IF EXISTS payment_info;
DROP TABLE IF EXISTS ods_event_log;

-- 2. 创建 ODS 外部表 - 用户信息（全量分区覆盖）
CREATE EXTERNAL TABLE IF NOT EXISTS user_info (
    id              BIGINT      COMMENT '用户ID',
    login_name      STRING      COMMENT '登录名',
    nick_name       STRING      COMMENT '昵称',
    phone           STRING      COMMENT '手机号',
    gender          STRING      COMMENT '性别',
    user_level      STRING      COMMENT '用户等级',
    create_time     STRING      COMMENT '创建时间',
    operate_time    STRING      COMMENT '操作时间'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ods/ods_user_info';

-- 3. 创建 ODS 外部表 - 商品信息
CREATE EXTERNAL TABLE IF NOT EXISTS sku_info (
    id              BIGINT      COMMENT '商品ID',
    sku_name        STRING      COMMENT '商品名称',
    category3_id    BIGINT      COMMENT '三级分类ID',
    price           DECIMAL(10,2) COMMENT '价格',
    create_time     STRING      COMMENT '创建时间',
    operate_time    STRING      COMMENT '操作时间'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ods/ods_sku_info';

-- 4. 创建 ODS 外部表 - 订单信息（增量分区）
CREATE EXTERNAL TABLE IF NOT EXISTS order_info (
    id              BIGINT      COMMENT '订单ID',
    user_id         BIGINT      COMMENT '用户ID',
    total_amount    DECIMAL(10,2) COMMENT '订单金额',
    status          INT         COMMENT '订单状态',
    create_time     STRING      COMMENT '创建时间',
    operate_time    STRING      COMMENT '操作时间'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ods/ods_order_info';

-- 5. 创建 ODS 外部表 - 订单明细
CREATE EXTERNAL TABLE IF NOT EXISTS order_detail (
    id              BIGINT      COMMENT '明细ID',
    order_id        BIGINT      COMMENT '订单ID',
    sku_id          BIGINT      COMMENT '商品ID',
    sku_num         INT         COMMENT '商品数量',
    sku_price       DECIMAL(10,2) COMMENT '商品单价',
    create_time     STRING      COMMENT '创建时间'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ods/ods_order_detail';

-- 6. 创建 ODS 外部表 - 支付信息
CREATE EXTERNAL TABLE IF NOT EXISTS payment_info (
    id              BIGINT      COMMENT '支付ID',
    order_id        BIGINT      COMMENT '订单ID',
    pay_amount      DECIMAL(10,2) COMMENT '支付金额',
    pay_status      INT         COMMENT '支付状态',
    create_time     STRING      COMMENT '创建时间',
    operate_time    STRING      COMMENT '操作时间'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY '\t'
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ods/ods_payment_info';

-- 7. 创建 ODS 外部表 - 埋点日志（JSON 格式）
CREATE EXTERNAL TABLE IF NOT EXISTS ods_event_log (
    event_id        STRING      COMMENT '事件ID',
    user_id         STRING      COMMENT '用户ID',
    action          STRING      COMMENT '行为类型',
    sku_id          STRING      COMMENT '商品ID',
    ts              STRING      COMMENT '时间戳'
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED
    FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/warehouse/mall/ods/ods_event_log';

-- 8. 修复分区元数据
MSCK REPAIR TABLE user_info;
MSCK REPAIR TABLE sku_info;
MSCK REPAIR TABLE order_info;
MSCK REPAIR TABLE order_detail;
MSCK REPAIR TABLE payment_info;
MSCK REPAIR TABLE ods_event_log;

-- 9. 验证表结构
DESC user_info;
DESC order_info;
