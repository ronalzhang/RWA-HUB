# RWA-HUB 4.0

RWA-HUB是一个用于管理和交易实物资产(RWA)的去中心化平台，基于Solana区块链。

## 安全警告

**重要安全提示**：本项目曾经存在严重安全漏洞，导致资金损失。已采取以下措施进行修复：

1. 移除了所有硬编码的私钥和助记词
2. 改进了.gitignore文件，确保敏感文件不会被推送到公共仓库
3. 添加了明确的安全指南，防止未来发生类似问题

## 安全最佳实践

开发和部署本项目时，请遵循以下安全最佳实践：

1. **永远不要**在代码或配置文件中硬编码私钥、助记词或密码
2. **永远不要**将真实的私钥或助记词提交到版本控制系统
3. 使用`.env`文件存储敏感配置，并确保它被添加到`.gitignore`中
4. 部署前检查所有配置文件是否包含敏感信息
5. 定期审查代码中的安全漏洞
6. 使用安全的密钥管理系统和环境变量管理敏感信息

## 安装和配置

1. 克隆仓库
```bash
git clone https://github.com/yourusername/RWA-HUB_4.0.git
cd RWA-HUB_4.0
```

2. 创建虚拟环境并安装依赖
```bash
python -m venv venv
source venv/bin/activate  # 在Windows上使用 venv\Scripts\activate
pip install -r requirements.txt
```

3. 复制并配置环境变量
```bash
cp app/.env.example app/.env
# 编辑.env文件，填入您的配置，但不要使用真实的助记词或私钥
```

4. 初始化数据库
```bash
flask db upgrade
```

5. 运行应用
```bash
flask run
```

## 贡献代码

1. 创建分支
2. 提交更改
3. 发起Pull Request
4. 等待代码审查

请确保您的代码不包含任何敏感信息或安全漏洞。

## 功能特点

- 资产数字化：将实物资产转化为区块链上的数字通证
- 智能合约：基于 ERC20 标准的资产代币和交易市场
- 安全可靠：完整的测试用例和审计机制
- 交易管理：支持一级市场交易，二级市场开发中

## 技术栈

- 智能合约：Solidity, Hardhat
- 前端：HTML5, CSS3, JavaScript, Web3.js
- 后端：Python Flask
- 数据库：PostgreSQL
- 区块链：以太坊, Sepolia测试网

## 快速开始

1. 克隆项目
```bash
git clone https://github.com/your-username/RWA-HUB_4.0.git
cd RWA-HUB_4.0
```

2. 安装依赖
```bash
npm install
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置信息
```

4. 运行测试
```bash
npx hardhat test
```

5. 部署合约
```bash
npx hardhat run scripts/deploy.js --network sepolia
```

## 项目结构

```
RWA-HUB_4.0/
├── contracts/           # 智能合约
├── scripts/            # 部署和交互脚本
├── test/              # 测试文件
├── app/               # Web应用
└── docs/              # 文档
```

## 已部署合约

- 测试网：Sepolia
- RealEstateToken: `0x8e2cbB9C52f0404e4fe50C04c1999434de1cB281`
- RealEstateMarket: [待部署]

## 开发路线图

- [x] 智能合约开发
- [x] 合约测试
- [ ] 前端开发
- [ ] 后端开发
- [ ] 二级市场
- [ ] 积分系统

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证

MIT License

# RWA-HUB 4.0 钱包修复工具包

## 概述

本工具包旨在修复RWA-HUB 4.0版本中的钱包连接和API查询问题，主要包含以下修复组件：

1. **钱包状态修复脚本** (wallet_fix.js) - 修复钱包连接状态同步和UI更新问题
2. **钱包调试脚本** (wallet_debug.js) - 监控钱包状态变化和页面交互，辅助排查问题
3. **API修复** (api.py.fixed) - 修复用户资产查询API的问题
4. **运行脚本修复** (fixed_run.py) - 修复应用启动配置问题
5. **部署脚本** (deploy_fix.sh) - 自动部署所有修复到服务器
6. **检查脚本** (check_server.sh) - 验证服务器修复状态

## 文件说明

### 1. 钱包修复脚本 (app/static/js/wallet_fix.js)

主要功能：
- 修复钱包连接状态的初始化和同步问题
- 确保钱包状态在页面刷新后正确恢复
- 修复购买按钮状态更新问题
- 修复API请求中钱包地址参数缺失问题

### 2. 钱包调试脚本 (app/static/js/wallet_debug.js)

主要功能：
- 监控并记录钱包状态变化
- 监控购买按钮状态变化
- 捕获和记录API请求和错误
- 提供控制台调试命令

使用方法：
- 在浏览器控制台输入 `window.showWalletDebug()` 查看调试信息
- 调试日志会自动保存在控制台，便于排查问题

### 3. API修复 (app/routes/api.py.fixed)

修复内容：
- 优化用户资产查询API的实现
- 修复参数验证和错误处理问题
- 优化数据库查询逻辑

### 4. 运行脚本修复 (fixed_run.py)

修复内容：
- 改用waitress作为生产环境WSGI服务器
- 优化日志配置
- 增强数据库连接错误处理

### 5. 部署脚本 (deploy_fix.sh)

主要功能：
- 检查本地修复文件完整性
- 备份服务器上的原始文件
- 上传修复文件到服务器
- 确保HTML模板引用了修复脚本
- 重启Flask应用
- 验证部署成功

使用方法：
```bash
chmod +x deploy_fix.sh
./deploy_fix.sh
```

### 6. 检查脚本 (check_server.sh)

主要功能：
- 检查JavaScript修复文件是否存在并被正确引用
- 检查API修复状态
- 检查应用运行状态
- 监控服务器资源使用情况

使用方法：
```bash
chmod +x check_server.sh
./check_server.sh
```

## 部署流程

1. 确认所有修复文件已准备就绪：
   - `app/static/js/wallet_fix.js`
   - `app/static/js/wallet_debug.js`
   - `fixed_run.py`
   - `app/routes/api.py.fixed`

2. 执行部署脚本：
   ```bash
   ./deploy_fix.sh
   ```
   脚本会执行以下步骤：
   - 检查本地修复文件
   - 备份服务器文件
   - 上传修复文件
   - 更新HTML模板引用
   - 重启应用
   - 验证部署

3. 部署后验证：
   ```bash
   ./check_server.sh
   ```
   确认所有组件正常工作

## 问题排查

如果部署后仍有问题，可以：

1. 检查服务器应用日志：
   ```bash
   ssh -i vincent.pem root@47.236.39.134 "tail -n 50 /home/vincent/RWA-HUB_4.0/flask_app.log"
   ```

2. 检查浏览器控制台日志，特别关注钱包调试脚本输出的信息

3. 使用浏览器调试工具检查网络请求，特别是API请求的参数和响应

## 回滚操作

如果需要回滚，可以使用服务器上的备份文件：
```bash
ssh -i vincent.pem root@47.236.39.134
cd /home/vincent/backups/
# 列出可用备份
ls -l
# 选择要恢复的备份
cd 备份目录
# 恢复文件
cp static/js/wallet.js /home/vincent/RWA-HUB_4.0/app/static/js/
cp routes/api.py /home/vincent/RWA-HUB_4.0/app/routes/
cp templates/base.html /home/vincent/RWA-HUB_4.0/app/templates/
# 重启应用
cd /home/vincent/RWA-HUB_4.0
pkill -f 'python.*run.py'
nohup python3 run.py > flask_app.log 2>&1 &
```
