SELECT '2026-08-20新增用户' AS 检查项, COUNT(*) AS 数量 FROM mall.user_info WHERE DATE(create_time) = '2026-08-20'
UNION ALL
SELECT '2026-08-20新增订单', COUNT(*) FROM mall.order_info WHERE DATE(create_time) = '2026-08-20'
UNION ALL
SELECT '2026-08-20变更用户', COUNT(*) FROM mall.user_info WHERE DATE(operate_time) = '2026-08-20' AND operate_time != create_time;

SELECT '总用户数' AS 统计项, COUNT(*) AS 总数 FROM mall.user_info
UNION ALL
SELECT '总商品数', COUNT(*) FROM mall.sku_info
UNION ALL
SELECT '总订单数', COUNT(*) FROM mall.order_info
UNION ALL
SELECT '总订单明细', COUNT(*) FROM mall.order_detail
UNION ALL
SELECT '总支付数', COUNT(*) FROM mall.payment_info;
