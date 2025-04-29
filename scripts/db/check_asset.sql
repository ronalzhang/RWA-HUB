-- 查询资产记录
SELECT id, token_symbol, token_supply, remaining_supply 
FROM assets 
WHERE id = 1;

-- 查询资产1的交易统计
SELECT 
    COUNT(*) as transaction_count,
    SUM(CASE WHEN type = 'buy' AND status = 'completed' THEN amount ELSE 0 END) as total_bought
FROM trades
WHERE asset_id = 1;

-- 查询资产1的最近交易记录
SELECT id, type, status, amount, created_at
FROM trades
WHERE asset_id = 1
ORDER BY created_at DESC
LIMIT 10;

-- 查询所有资产的供应量信息
SELECT id, token_symbol, token_supply, remaining_supply
FROM assets
ORDER BY id; 