-- 创建管理员相关表
-- 可以在PostgreSQL数据库中执行: psql -U username -d database_name -a -f create_admin_tables.sql

-- 管理员用户表
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(50),
    role VARCHAR(20) NOT NULL DEFAULT 'admin',
    permissions TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP
);

-- 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(80)
);

-- 佣金设置表
CREATE TABLE IF NOT EXISTS commission_settings (
    id SERIAL PRIMARY KEY,
    asset_type_id INTEGER,
    commission_rate FLOAT NOT NULL,
    min_amount FLOAT,
    max_amount FLOAT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    created_by VARCHAR(80)
);

-- 分销等级表
CREATE TABLE IF NOT EXISTS distribution_levels (
    id SERIAL PRIMARY KEY,
    level INTEGER UNIQUE NOT NULL,
    commission_rate FLOAT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- 用户推荐关系表
CREATE TABLE IF NOT EXISTS user_referrals (
    id SERIAL PRIMARY KEY,
    user_address VARCHAR(80) UNIQUE NOT NULL,
    referrer_address VARCHAR(80) NOT NULL,
    referral_level INTEGER DEFAULT 1,
    referral_code VARCHAR(20),
    joined_at TIMESTAMP DEFAULT NOW()
);

-- 佣金记录表
CREATE TABLE IF NOT EXISTS commission_records (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER,
    asset_id INTEGER,
    transaction_hash VARCHAR(100),
    recipient_address VARCHAR(80) NOT NULL,
    amount FLOAT NOT NULL,
    token_address VARCHAR(80),
    commission_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    payment_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- 管理员操作日志表
CREATE TABLE IF NOT EXISTS admin_operation_logs (
    id SERIAL PRIMARY KEY,
    admin_address VARCHAR(80) NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    target_table VARCHAR(50),
    target_id VARCHAR(50),
    operation_details TEXT,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 仪表盘统计数据表
CREATE TABLE IF NOT EXISTS dashboard_stats (
    id SERIAL PRIMARY KEY,
    stat_date DATE NOT NULL,
    stat_type VARCHAR(50) NOT NULL,
    stat_period VARCHAR(20) NOT NULL,
    stat_value FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    UNIQUE(stat_date, stat_type, stat_period)
);

-- 添加测试管理员
INSERT INTO admin_users (wallet_address, username, role, permissions, created_at, updated_at)
VALUES ('HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd', '测试管理员', 'super_admin', '["all"]', NOW(), NOW())
ON CONFLICT (wallet_address) DO NOTHING; 