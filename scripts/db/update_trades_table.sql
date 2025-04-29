-- 为trades表添加缺少的列
BEGIN;

-- 1. 添加total字段 (可为空)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS total DOUBLE PRECISION;

-- 2. 添加fee字段 (可为空)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS fee DOUBLE PRECISION;

-- 3. 添加fee_rate字段 (可为空)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS fee_rate DOUBLE PRECISION;

-- 4. 添加tx_hash字段 (可为空,如不存在)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS tx_hash VARCHAR(100);

-- 5. 添加gas_used字段 (可为空,如不存在)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS gas_used DECIMAL;

-- 6. 添加confirmed_at字段 (可为空)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMP WITHOUT TIME ZONE;

-- 7. 修改trader_address长度为64以支持Solana地址
ALTER TABLE trades ALTER COLUMN trader_address TYPE VARCHAR(64);

COMMIT;

-- 回滚脚本
-- BEGIN;
-- ALTER TABLE trades DROP COLUMN IF EXISTS total;
-- ALTER TABLE trades DROP COLUMN IF EXISTS fee;
-- ALTER TABLE trades DROP COLUMN IF EXISTS fee_rate;
-- ALTER TABLE trades DROP COLUMN IF EXISTS confirmed_at;
-- COMMIT; 