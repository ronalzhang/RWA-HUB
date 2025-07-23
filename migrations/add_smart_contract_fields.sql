-- 添加智能合约相关字段到assets表
-- 执行时间: 2025-07-23
-- 用途: 支持智能合约集成功能

-- 添加智能合约相关字段
ALTER TABLE assets ADD COLUMN IF NOT EXISTS contract_address VARCHAR(64);
ALTER TABLE assets ADD COLUMN IF NOT EXISTS vault_address VARCHAR(64);
ALTER TABLE assets ADD COLUMN IF NOT EXISTS blockchain_data TEXT;

-- 添加注释
COMMENT ON COLUMN assets.contract_address IS '智能合约资产账户地址';
COMMENT ON COLUMN assets.vault_address IS '资产金库PDA地址';
COMMENT ON COLUMN assets.blockchain_data IS '智能合约数据（JSON格式）';

-- 验证字段已添加
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'assets' 
AND column_name IN ('contract_address', 'vault_address', 'blockchain_data');