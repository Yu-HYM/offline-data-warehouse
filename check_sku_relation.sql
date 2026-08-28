-- 检查 order_detail 和 sku_info 的关联
SELECT MIN(sku_id) as min_sku, MAX(sku_id) as max_sku, COUNT(*) as cnt FROM mall.order_detail;
SELECT MIN(id) as min_id, MAX(id) as max_id, COUNT(*) as cnt FROM mall.sku_info;

-- 检查是否有关联不上的记录
SELECT od.sku_id, s.id
FROM mall.order_detail od
LEFT JOIN mall.sku_info s ON od.sku_id = s.id
WHERE s.id IS NULL
LIMIT 10;
