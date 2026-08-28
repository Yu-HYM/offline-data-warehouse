-- =============================================================
-- ODS 贴源层 Hive 外部表验证
-- 验证 HDFS 数据可被 Hive 正确读取
-- =============================================================

-- 1. 查看 ODS 库
SHOW DATABASES;

-- 2. 查询 user_info (HDFS)
SELECT * FROM mall.user_info LIMIT 5;

-- 3. 查询 sku_info
SELECT * FROM mall.sku_info LIMIT 5;

-- 4. 查询 order_info 最近几天
SELECT id, user_id, total_amount, status, create_time 
FROM mall.order_info 
WHERE create_time >= '2026-08-19' 
LIMIT 10;

-- 5. 查询 HDFS 中按天分区的数据量
-- Hive 外部表直接指向 HDFS 路径，按 dt 分区
-- 可以用 HDFS 命令查看: hdfs dfs -du -s /warehouse/mall/ods/ods_order_info/*

-- 6. 统计各 ODS 表数据量
SELECT '用户' AS 表名, COUNT(*) AS 数据量 FROM mall.user_info
UNION ALL
SELECT '商品', COUNT(*) FROM mall.sku_info
UNION ALL
SELECT '订单', COUNT(*) FROM mall.order_info;
