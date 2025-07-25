# RWA-HUB 数据迁移脚本

## 概述
这个目录包含了RWA-HUB系统的数据迁移脚本，用于初始化和更新系统的配置数据和分享消息数据。

## 迁移脚本列表

### 1. `migrate_share_message_types.py`
**用途**: 迁移系统配置和分享消息数据

**功能**:
- 初始化系统配置数据（管理员地址、费率设置等）
- 添加和更新分享消息数据
- 修复消息类型分类问题

**使用方法**:
```bash
# 在项目根目录执行
python scripts/migrate_share_message_types.py
```

**数据内容**:

#### 系统配置 (9条)
- `PLATFORM_FEE_ADDRESS`: 平台收款地址
- `ASSET_CREATION_FEE_ADDRESS`: 资产创建收款地址  
- `ASSET_CREATION_FEE_AMOUNT`: 资产创建费用(0.02 USDC)
- `PLATFORM_FEE_BASIS_POINTS`: 平台费率(350基点=3.5%)
- `PLATFORM_FEE_RATE`: 平台费率(0.035)
- `SOLANA_RPC_URL`: Solana RPC节点
- `SOLANA_USDC_MINT`: USDC Mint地址
- `SOLANA_PROGRAM_ID`: Solana程序ID
- `SOLANA_PRIVATE_KEY_ENCRYPTED`: 加密的Solana私钥(待管理员设置)

#### 分享消息 (8条)
**分享内容消息** (`share_content`) - 用于资产分享:
- 💎 投资真实世界资产，数字化时代的理财新选择！
- 🌟 RWA数字化投资平台，让传统资产焕发新活力！
- 💰 智能分佣系统，35%无限级收益分成！
- 🔐 区块链技术保障，资产透明可查！
- 📈 多元化投资组合，降低风险提升收益！
- 🎯 专业团队严选资产，深度尽调保驾护航！

**奖励计划消息** (`reward_plan`) - 用于推广分佣:
- 🚀 发现优质RWA资产！真实世界资产数字化投资新机遇
- 🏠 不动产投资新玩法！通过区块链技术参与投资

## 执行要求
- Python 3.7+
- 已配置的数据库连接
- Flask应用环境

## 注意事项
1. 脚本会自动检查现有数据，避免重复插入
2. 对于已存在的数据，会进行更新而不是重新创建
3. 所有操作都在事务中执行，失败时会自动回滚
4. 执行前请确保数据库连接正常

## 故障排除
如果迁移失败，请检查：
1. 数据库连接配置是否正确
2. 数据库用户是否有足够权限
3. 相关数据表是否已创建
4. Python依赖包是否完整安装