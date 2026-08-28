USE mall;

-- 1. 分区检查
SELECT '分区数量' AS 检查项, COUNT(*) AS 数量 FROM (
    SHOW PARTITIONS user_info
) t;

-- 2. 各表数据量统计
SELECT '用户表(dt=0819)' AS 表名, COUNT(*) AS 数据量 FROM user_info WHERE dt='2026-08-19'
UNION ALL
SELECT '用户表(dt=0820)', COUNT(*) FROM user_info WHERE dt='2026-08-20'
UNION ALL
SELECT '商品表', COUNT(*) FROM sku_info WHERE dt='2026-08-19'
UNION ALL
SELECT '订单表(dt=0819)', COUNT(*) FROM order_info WHERE dt='2026-08-19'
UNION ALL
SELECT '订单表(dt=0820)', COUNT(*) FROM order_info WHERE dt='2026-08-20'
UNION ALL
SELECT '订单明细表(dt=0819)', COUNT(*) FROM order_detail WHERE dt='2026-08-19'
UNION ALL
SELECT '订单明细表(dt=0820)', COUNT(*) FROM order_detail WHERE dt='2026-08-20'
UNION ALL
SELECT '支付表(dt=0819)', COUNT(*) FROM payment_info WHERE dt='2026-08-19'
UNION ALL
SELECT '支付表(dt=0820)', COUNT(*) FROM payment_info WHERE dt='2026-08-20';

-- 3. 抽样查看订单数据
SELECT id, user_id, total_amount, status, dt FROM order_info WHERE dt='2026-08-20' LIMIT 5;

-- 4. 验证 HDFS 数据总量
dfs -du -h /warehouse/mall/ods/ods_user_info;
dfs -du -h /warehouse/mall/ods/ods_order_info;
