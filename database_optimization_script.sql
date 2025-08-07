-- RWA-HUB 5.0 数据库优化脚本
-- 执行前请备份数据库

-- ================================
-- 1. 性能优化索引
-- ================================

-- 资产表关键索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assets_status_active 
    ON assets (status, deleted_at) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assets_remaining_supply 
    ON assets (remaining_supply) WHERE remaining_supply > 0;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_assets_creator_status 
    ON assets (creator_address, status);

-- 交易表索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_asset_status 
    ON trades (asset_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_trader_created 
    ON trades (trader_address, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_tx_hash 
    ON trades (tx_hash) WHERE tx_hash IS NOT NULL;

-- 用户推荐表索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_referrals_referrer 
    ON user_referrals (referrer_address, status);

-- 佣金记录表索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_commission_records_recipient 
    ON commission_records (recipient_address, status);

-- ================================
-- 2. 数据一致性修复
-- ================================

-- 修复 remaining_supply 为 NULL 的问题
UPDATE assets 
SET remaining_supply = token_supply 
WHERE remaining_supply IS NULL AND token_supply IS NOT NULL;

-- 修复负的 remaining_supply
UPDATE assets 
SET remaining_supply = 0 
WHERE remaining_supply < 0;

-- 修复超出 token_supply 的 remaining_supply
UPDATE assets 
SET remaining_supply = token_supply 
WHERE remaining_supply > token_supply AND token_supply IS NOT NULL;

-- ================================
-- 3. 添加约束确保数据完整性
-- ================================

-- 资产表约束
ALTER TABLE assets 
ADD CONSTRAINT ck_remaining_supply_valid 
CHECK (remaining_supply >= 0 AND remaining_supply <= token_supply);

-- 交易表约束
ALTER TABLE trades 
ADD CONSTRAINT ck_trade_amount_positive 
CHECK (amount > 0);

-- ================================
-- 4. 清理冗余数据
-- ================================

-- 清理空的或无效的交易记录
DELETE FROM trades 
WHERE amount <= 0 OR price < 0;

-- 清理重复的佣金记录（保留最新的）
WITH duplicate_commissions AS (
    SELECT id, 
           ROW_NUMBER() OVER (
               PARTITION BY transaction_id, recipient_address, commission_type 
               ORDER BY created_at DESC
           ) as rn
    FROM commission_records
)
DELETE FROM commission_records 
WHERE id IN (
    SELECT id FROM duplicate_commissions WHERE rn > 1
);

-- ================================
-- 5. 统计信息更新
-- ================================

-- 更新表统计信息以优化查询计划
ANALYZE assets;
ANALYZE trades;
ANALYZE user_referrals;
ANALYZE commission_records;

-- ================================
-- 6. 创建视图简化查询
-- ================================

-- 活跃资产视图
CREATE OR REPLACE VIEW v_active_assets AS
SELECT 
    id, name, asset_type, location, token_symbol, token_price,
    remaining_supply, total_value, annual_revenue, status,
    created_at, creator_address
FROM assets 
WHERE status = 2 AND deleted_at IS NULL AND remaining_supply > 0;

-- 用户资产持仓汇总视图
CREATE OR REPLACE VIEW v_user_holdings AS
SELECT 
    h.user_id,
    a.id as asset_id,
    a.name as asset_name,
    a.token_symbol,
    h.amount,
    h.purchase_price,
    a.token_price as current_price,
    (h.amount * a.token_price) as current_value,
    (h.amount * (a.token_price - h.purchase_price)) as profit_loss
FROM holdings h
JOIN assets a ON h.asset_id = a.id
WHERE a.status = 2 AND a.deleted_at IS NULL;

-- 佣金统计视图  
CREATE OR REPLACE VIEW v_commission_summary AS
SELECT 
    recipient_address,
    commission_type,
    COUNT(*) as record_count,
    SUM(amount) as total_amount,
    SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) as paid_amount,
    SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END) as pending_amount
FROM commission_records
GROUP BY recipient_address, commission_type;

-- ================================
-- 执行完成提示
-- ================================
SELECT 'Database optimization completed successfully!' as status;
