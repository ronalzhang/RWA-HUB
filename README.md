# RWA-HUB 4.0

RWA-HUB 是一个基于区块链的实物资产数字化平台，致力于将不动产和类不动产转化为数字通证，实现资产的流动性提升和价值管理。

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
