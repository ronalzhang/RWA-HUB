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
