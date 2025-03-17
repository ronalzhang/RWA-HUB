-- 为trades表添加新字段
BEGIN;

-- 1. 添加tx_hash字段 (可为空)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS tx_hash VARCHAR(66);

-- 2. 添加status字段 (不可为空,默认pending)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending';

-- 3. 添加gas_used字段 (可为空)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS gas_used DECIMAL;

COMMIT;

-- 回滚脚本
-- BEGIN;
-- ALTER TABLE trades DROP COLUMN IF EXISTS gas_used;
-- ALTER TABLE trades DROP COLUMN IF EXISTS status;
-- ALTER TABLE trades DROP COLUMN IF EXISTS tx_hash;
-- COMMIT; 