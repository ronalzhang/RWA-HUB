-- 修复服务器数据库表结构
-- 添加缺失的字段到 trades 和 assets 表

-- 开始事务
BEGIN;

-- 检查并添加 trades 表的缺失字段
DO $$
BEGIN
    -- 添加 error_message 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='error_message') THEN
        ALTER TABLE trades ADD COLUMN error_message TEXT;
        RAISE NOTICE '添加 trades.error_message 字段';
    ELSE
        RAISE NOTICE 'trades.error_message 字段已存在';
    END IF;
    
    -- 添加 confirmation_count 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='confirmation_count') THEN
        ALTER TABLE trades ADD COLUMN confirmation_count INTEGER DEFAULT 0;
        RAISE NOTICE '添加 trades.confirmation_count 字段';
    ELSE
        RAISE NOTICE 'trades.confirmation_count 字段已存在';
    END IF;
    
    -- 添加 estimated_completion_time 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='estimated_completion_time') THEN
        ALTER TABLE trades ADD COLUMN estimated_completion_time TIMESTAMP;
        RAISE NOTICE '添加 trades.estimated_completion_time 字段';
    ELSE
        RAISE NOTICE 'trades.estimated_completion_time 字段已存在';
    END IF;
    
    -- 添加 status_updated_at 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='status_updated_at') THEN
        ALTER TABLE trades ADD COLUMN status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE '添加 trades.status_updated_at 字段';
    ELSE
        RAISE NOTICE 'trades.status_updated_at 字段已存在';
    END IF;
    
    -- 添加 retry_count 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='retry_count') THEN
        ALTER TABLE trades ADD COLUMN retry_count INTEGER DEFAULT 0;
        RAISE NOTICE '添加 trades.retry_count 字段';
    ELSE
        RAISE NOTICE 'trades.retry_count 字段已存在';
    END IF;
    
    -- 添加 blockchain_network 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trades' AND column_name='blockchain_network') THEN
        ALTER TABLE trades ADD COLUMN blockchain_network VARCHAR(20) DEFAULT 'solana';
        RAISE NOTICE '添加 trades.blockchain_network 字段';
    ELSE
        RAISE NOTICE 'trades.blockchain_network 字段已存在';
    END IF;
END $$;

-- 检查并添加 assets 表的缺失字段
DO $$
BEGIN
    -- 添加 contract_address 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assets' AND column_name='contract_address') THEN
        ALTER TABLE assets ADD COLUMN contract_address VARCHAR(100);
        RAISE NOTICE '添加 assets.contract_address 字段';
    ELSE
        RAISE NOTICE 'assets.contract_address 字段已存在';
    END IF;
    
    -- 添加 vault_address 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assets' AND column_name='vault_address') THEN
        ALTER TABLE assets ADD COLUMN vault_address VARCHAR(100);
        RAISE NOTICE '添加 assets.vault_address 字段';
    ELSE
        RAISE NOTICE 'assets.vault_address 字段已存在';
    END IF;
    
    -- 添加 blockchain_data 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assets' AND column_name='blockchain_data') THEN
        ALTER TABLE assets ADD COLUMN blockchain_data TEXT;
        RAISE NOTICE '添加 assets.blockchain_data 字段';
    ELSE
        RAISE NOTICE 'assets.blockchain_data 字段已存在';
    END IF;
    
    -- 添加 error_message 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assets' AND column_name='error_message') THEN
        ALTER TABLE assets ADD COLUMN error_message TEXT;
        RAISE NOTICE '添加 assets.error_message 字段';
    ELSE
        RAISE NOTICE 'assets.error_message 字段已存在';
    END IF;
    
    -- 添加 approved_at 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assets' AND column_name='approved_at') THEN
        ALTER TABLE assets ADD COLUMN approved_at TIMESTAMP;
        RAISE NOTICE '添加 assets.approved_at 字段';
    ELSE
        RAISE NOTICE 'assets.approved_at 字段已存在';
    END IF;
    
    -- 添加 approved_by 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assets' AND column_name='approved_by') THEN
        ALTER TABLE assets ADD COLUMN approved_by VARCHAR(100);
        RAISE NOTICE '添加 assets.approved_by 字段';
    ELSE
        RAISE NOTICE 'assets.approved_by 字段已存在';
    END IF;
    
    -- 添加 deployment_in_progress 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assets' AND column_name='deployment_in_progress') THEN
        ALTER TABLE assets ADD COLUMN deployment_in_progress BOOLEAN DEFAULT FALSE;
        RAISE NOTICE '添加 assets.deployment_in_progress 字段';
    ELSE
        RAISE NOTICE 'assets.deployment_in_progress 字段已存在';
    END IF;
    
    -- 添加 deployment_started_at 字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='assets' AND column_name='deployment_started_at') THEN
        ALTER TABLE assets ADD COLUMN deployment_started_at TIMESTAMP;
        RAISE NOTICE '添加 assets.deployment_started_at 字段';
    ELSE
        RAISE NOTICE 'assets.deployment_started_at 字段已存在';
    END IF;
END $$;

-- 更新现有交易记录的 status_updated_at 字段
UPDATE trades 
SET status_updated_at = COALESCE(created_at, CURRENT_TIMESTAMP)
WHERE status_updated_at IS NULL;

-- 提交事务
COMMIT;

-- 验证修复结果
SELECT 'trades表字段检查:' as info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'trades' 
AND column_name IN ('error_message', 'confirmation_count', 'estimated_completion_time', 
                    'status_updated_at', 'retry_count', 'blockchain_network')
ORDER BY column_name;

SELECT 'assets表字段检查:' as info;
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'assets' 
AND column_name IN ('contract_address', 'vault_address', 'blockchain_data', 
                    'error_message', 'approved_at', 'approved_by', 
                    'deployment_in_progress', 'deployment_started_at')
ORDER BY column_name;

SELECT 'trades表记录统计:' as info;
SELECT 
    COUNT(*) as total_trades,
    COUNT(error_message) as with_error_message,
    COUNT(status_updated_at) as with_status_updated,
    COUNT(blockchain_network) as with_blockchain_network
FROM trades;

SELECT 'assets表记录统计:' as info;
SELECT 
    COUNT(*) as total_assets,
    COUNT(contract_address) as with_contract_address,
    COUNT(error_message) as with_error_message,
    COUNT(deployment_in_progress) as with_deployment_progress
FROM assets;
