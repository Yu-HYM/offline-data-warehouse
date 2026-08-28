-- =============================================================
-- 阶段四：DWD 数据验证
-- =============================================================

USE mall;

-- 1. HDFS DWD 目录检查
dfs -du -h /warehouse/mall/dwd/dim_user_full/*/;
dfs -du -h /warehouse/mall/dwd/fact_order_detail/*/;

-- 2. 分区检查
SHOW PARTITIONS dwd_dim_user_full;

-- 3. 抽样查询
SELECT * FROM dwd_dim_user_full WHERE dt='2026-08-19' LIMIT 3;
SELECT * FROM dwd_fact_order_detail WHERE dt='2026-08-20' LIMIT 3;
