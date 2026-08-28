-- =============================================================
-- 阶段六：DWS 聚合宽表 - 数据加载
-- 直接从 MySQL 业务库聚合数据写入 Hive ORC 内部表
-- =============================================================

USE mall;

-- =============================================================
-- 1. 用户交易日粒度宽表
-- =============================================================

-- 2026-08-19 数据
INSERT OVERWRITE TABLE dws_trade_user_order_1d PARTITION (dt='2026-08-19')
SELECT 
    u.id AS user_id,
    u.nick_name AS user_nick_name,
    CASE u.user_level 
        WHEN 1 THEN '普通用户'
        WHEN 2 THEN '银牌用户'
        WHEN 3 THEN '金牌用户'
        ELSE '未知'
    END AS user_level,
    CASE u.gender 
        WHEN 0 THEN '女'
        WHEN 1 THEN '男'
        ELSE '未知'
    END AS gender,
    COUNT(DISTINCT o.id) AS order_count_1d,
    ROUND(SUM(o.total_amount), 2) AS order_amount_1d,
    ROUND(SUM(CASE WHEN p.pay_status = 1 THEN p.pay_amount ELSE 0 END), 2) AS pay_amount_1d,
    SUM(COALESCE(od.sku_num, 0)) AS order_sku_count_1d,
    COUNT(DISTINCT s.category3_id) AS category_count_1d,
    ROUND(SUM(o.total_amount) / COUNT(DISTINCT o.id), 2) AS avg_order_amount_1d
FROM user_info u
JOIN order_info o ON u.id = o.user_id
LEFT JOIN order_detail od ON o.id = od.order_id
LEFT JOIN sku_info s ON od.sku_id = s.id
LEFT JOIN payment_info p ON o.id = p.order_id AND p.pay_status = 1
WHERE DATE(o.create_time) = '2026-08-19'
  AND o.total_amount > 0
GROUP BY u.id, u.nick_name, u.user_level, u.gender;

-- 2026-08-20 数据
INSERT OVERWRITE TABLE dws_trade_user_order_1d PARTITION (dt='2026-08-20')
SELECT 
    u.id AS user_id,
    u.nick_name AS user_nick_name,
    CASE u.user_level 
        WHEN 1 THEN '普通用户'
        WHEN 2 THEN '银牌用户'
        WHEN 3 THEN '金牌用户'
        ELSE '未知'
    END AS user_level,
    CASE u.gender 
        WHEN 0 THEN '女'
        WHEN 1 THEN '男'
        ELSE '未知'
    END AS gender,
    COUNT(DISTINCT o.id) AS order_count_1d,
    ROUND(SUM(o.total_amount), 2) AS order_amount_1d,
    ROUND(SUM(CASE WHEN p.pay_status = 1 THEN p.pay_amount ELSE 0 END), 2) AS pay_amount_1d,
    SUM(COALESCE(od.sku_num, 0)) AS order_sku_count_1d,
    COUNT(DISTINCT s.category3_id) AS category_count_1d,
    ROUND(SUM(o.total_amount) / COUNT(DISTINCT o.id), 2) AS avg_order_amount_1d
FROM user_info u
JOIN order_info o ON u.id = o.user_id
LEFT JOIN order_detail od ON o.id = od.order_id
LEFT JOIN sku_info s ON od.sku_id = s.id
LEFT JOIN payment_info p ON o.id = p.order_id AND p.pay_status = 1
WHERE DATE(o.create_time) = '2026-08-20'
  AND o.total_amount > 0
GROUP BY u.id, u.nick_name, u.user_level, u.gender;

-- =============================================================
-- 2. 商品交易日粒度宽表
-- =============================================================

-- 2026-08-19 数据
INSERT OVERWRITE TABLE dws_trade_sku_order_1d PARTITION (dt='2026-08-19')
SELECT 
    s.id AS sku_id,
    s.sku_name,
    c1.name AS category1_name,
    c2.name AS category2_name,
    c3.name AS category3_name,
    COUNT(DISTINCT od.order_id) AS order_count_1d,
    SUM(od.sku_num) AS sale_count_1d,
    ROUND(SUM(od.sku_num * od.sku_price), 2) AS sale_amount_1d,
    COUNT(DISTINCT o.user_id) AS order_user_count_1d,
    ROUND(AVG(od.sku_price), 2) AS avg_price_1d
FROM order_info o
JOIN order_detail od ON o.id = od.order_id
JOIN sku_info s ON od.sku_id = s.id
LEFT JOIN category3 c3 ON s.category3_id = c3.id
LEFT JOIN category2 c2 ON c3.category2_id = c2.id
LEFT JOIN category1 c1 ON c2.category1_id = c1.id
WHERE DATE(o.create_time) = '2026-08-19'
  AND o.total_amount > 0
GROUP BY s.id, s.sku_name, c1.name, c2.name, c3.name;

-- 2026-08-20 数据
INSERT OVERWRITE TABLE dws_trade_sku_order_1d PARTITION (dt='2026-08-20')
SELECT 
    s.id AS sku_id,
    s.sku_name,
    c1.name AS category1_name,
    c2.name AS category2_name,
    c3.name AS category3_name,
    COUNT(DISTINCT od.order_id) AS order_count_1d,
    SUM(od.sku_num) AS sale_count_1d,
    ROUND(SUM(od.sku_num * od.sku_price), 2) AS sale_amount_1d,
    COUNT(DISTINCT o.user_id) AS order_user_count_1d,
    ROUND(AVG(od.sku_price), 2) AS avg_price_1d
FROM order_info o
JOIN order_detail od ON o.id = od.order_id
JOIN sku_info s ON od.sku_id = s.id
LEFT JOIN category3 c3 ON s.category3_id = c3.id
LEFT JOIN category2 c2 ON c3.category2_id = c2.id
LEFT JOIN category1 c1 ON c2.category1_id = c1.id
WHERE DATE(o.create_time) = '2026-08-20'
  AND o.total_amount > 0
GROUP BY s.id, s.sku_name, c1.name, c2.name, c3.name;

-- 验证
SELECT '用户宽表-2026-08-19' AS info, COUNT(*) FROM dws_trade_user_order_1d WHERE dt='2026-08-19'
UNION ALL
SELECT '用户宽表-2026-08-20', COUNT(*) FROM dws_trade_user_order_1d WHERE dt='2026-08-20'
UNION ALL
SELECT '商品宽表-2026-08-19', COUNT(*) FROM dws_trade_sku_order_1d WHERE dt='2026-08-19'
UNION ALL
SELECT '商品宽表-2026-08-20', COUNT(*) FROM dws_trade_sku_order_1d WHERE dt='2026-08-20';
