SELECT '用户' AS 表名, COUNT(*) AS 总行数, MIN(create_time) AS 最早时间, MAX(create_time) AS 最晚时间 FROM mall.user_info
UNION ALL
SELECT '商品', COUNT(*), MIN(create_time), MAX(create_time) FROM mall.sku_info
UNION ALL
SELECT '订单', COUNT(*), MIN(create_time), MAX(create_time) FROM mall.order_info
UNION ALL
SELECT '订单明细', COUNT(*), MIN(create_time), MAX(create_time) FROM mall.order_detail
UNION ALL
SELECT '支付', COUNT(*), MIN(create_time), MAX(create_time) FROM mall.payment_info;

-- 脏数据检查
SELECT '用户表空手机号' AS 检查项, COUNT(*) AS 数量 FROM mall.user_info WHERE phone IS NULL
UNION ALL
SELECT '用户表非法时间', COUNT(*) FROM mall.user_info WHERE create_time < '2020-01-01'
UNION ALL
SELECT '订单表负金额', COUNT(*) FROM mall.order_info WHERE total_amount < 0
UNION ALL
SELECT '订单表空用户ID', COUNT(*) FROM mall.order_info WHERE user_id IS NULL;
