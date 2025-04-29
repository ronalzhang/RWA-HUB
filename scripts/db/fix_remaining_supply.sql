-- 1. 查询并显示当前状态
SELECT id, token_symbol, token_supply, remaining_supply, 
       CASE 
           WHEN remaining_supply = 0 AND token_supply > 0 THEN '需要修复'
           ELSE '正常'
       END AS status
FROM assets
WHERE id IN (1, 2, 4);

-- 2. 修复remaining_supply字段为初始token_supply值
-- 只有当remaining_supply为0且token_supply存在时才更新
UPDATE assets
SET remaining_supply = token_supply,
    updated_at = NOW()
WHERE id IN (1, 2, 4)
  AND remaining_supply = 0
  AND token_supply > 0;

-- 3. 确认修复后的状态
SELECT id, token_symbol, token_supply, remaining_supply
FROM assets
WHERE id IN (1, 2, 4); 