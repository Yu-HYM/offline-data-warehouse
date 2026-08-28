-- 检查 category 关联问题
SELECT s.id, s.sku_name, s.category3_id, c3.id as c3_id, c3.name as c3_name
FROM mall.sku_info s
LEFT JOIN mall.category3 c3 ON s.category3_id = c3.id
LIMIT 10;
