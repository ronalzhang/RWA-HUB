-- 添加管理员用户
INSERT INTO admin_users (wallet_address, username, role, permissions, created_at, updated_at)
VALUES ('HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd', '测试管理员', 'super_admin', '["all"]', NOW(), NOW())
ON CONFLICT (wallet_address) DO NOTHING; 