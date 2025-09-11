# CLAUDE.md

此文件为Claude Code (claude.ai/code)提供在此代码库中工作的指导。

## 项目概述

RWA-HUB是一个基于Solana区块链构建的去中心化实物资产（RWA）管理和交易平台。项目由Flask后端、Solana智能合约和用于资产代币化及交易的Web前端组成。

## 开发命令

### 启动应用程序
```bash
# 主应用程序 (运行在端口5000)
python app_wsgi.py

# 使用npm的替代方式
npm start
```

### 数据库操作
```bash
# 数据库迁移
flask db migrate -m "描述信息"
flask db upgrade

# 初始化分配设置
flask init-distribution
```

### 智能合约开发
```bash
# Hardhat命令
npx hardhat test
npx hardhat run scripts/deploy.js --network sepolia

# Solana/Anchor开发 (在program/或rwahub-contracts/目录中)
anchor build
anchor test
anchor deploy
```

### 测试
目前使用基本的Python测试设置：
```bash
python -m pytest tests/
```

## 架构概述

### 核心组件

**Flask应用程序 (`app/`)**
- 主应用程序工厂在 `app/__init__.py`
- 基于蓝图的路由系统在 `app/routes/`
- SQLAlchemy模型在 `app/models/`
- 区块链集成在 `app/blockchain/`
- 具有基于角色权限的管理系统

**智能合约**
- Solana程序在 `program/` 和 `rwahub-contracts/`
- 以太坊合约在 `contracts/` (遗留)
- 资产代币化和分红分配合约

**前端**
- 静态文件在 `app/static/`
- Jinja2模板在 `app/templates/`
- 多版本UI支持 (v6为当前版本)

### 关键配置

**环境变量**
- `DATABASE_URL`: PostgreSQL连接字符串
- `SECRET_KEY`: Flask会话加密
- `SOLANA_RPC_URL`: Solana网络端点
- `SOLANA_PROGRAM_ID`: 智能合约地址
- 通过 `SystemConfig` 管理的加密私钥

**安全特性**
- 通过 `app.utils.crypto_manager` 加密私钥存储
- 管理员基于角色的访问控制
- IP追踪中间件
- 使用Flask-Limiter限制访问频率

### 数据库模型

关键模型包括：
- `User`: 带有钱包地址的用户账户
- `Asset`: 带有代币化数据的房地产资产
- `Trade`: 交易记录
- `Commission`: 推荐和分配系统
- `Dividend`: 资产利润分配

### 区块链集成

**Solana集成**
- SPL代币创建用于资产代币化
- 基于USDC的支付处理
- 自动化交易监控
- 智能合约部署和交互

**支付流程**
1. 用户连接钱包 (MetaMask/Phantom)
2. 资产购买创建SPL代币
3. USDC支付在链上处理
4. 所有权记录在数据库中

## 开发指南

### 代码组织
- 遵循Flask蓝图模式进行路由
- 使用SQLAlchemy ORM进行数据库操作
- 实现适当的错误处理和日志记录
- 维护开发/生产环境的单独配置

### 安全实践
- 绝不提交私钥或密钥
- 对敏感数据使用加密存储
- 验证所有用户输入
- 实现适当的身份验证检查

### 测试策略
- 使用测试网测试区块链集成
- 在生产环境之前验证数据库迁移
- 测试不同提供商的钱包连接
- 验证管理员权限系统

## 常见问题

### 数据库连接
如果PostgreSQL连接失败，请检查：
- `DATABASE_URL` 环境变量
- PostgreSQL服务状态
- 数据库用户权限

### 区块链问题
对于Solana连接问题：
- 验证 `SOLANA_RPC_URL` 可访问性
- 检查程序部署状态
- 验证钱包私钥加密

### 静态文件
CSS/JS更改未生效：
- 在开发环境中禁用缓存 (`SEND_FILE_MAX_AGE_DEFAULT = 0`)
- 清除浏览器缓存
- 检查静态文件路由配置

## 服务器部署

**生产服务器详情**
- 服务器IP: 156.232.13.240
- 密码: Pr971V3j  
- 应用程序目录: `/root/RWA-HUB`
- 域名: rwa-hub.com
- 数据库: PostgreSQL
- 进程管理: PM2（应用运行在各自的虚拟环境下）

**部署流程**
标准部署流程为：本地测试 → git push → 服务器git pull → pm2 restart

**部署命令**
```bash
# 登录服务器（使用sshpass命令）
sshpass -p "Pr971V3j" ssh -o StrictHostKeyChecking=no root@156.232.13.240

# 检查应用程序状态
sshpass -p "Pr971V3j" ssh root@156.232.13.240 "pm2 status"

# 重启应用程序
sshpass -p "Pr971V3j" ssh root@156.232.13.240 "pm2 restart rwa-hub"

# 查看日志 (注意必须加--nostream)
sshpass -p "Pr971V3j" ssh root@156.232.13.240 "pm2 logs rwa-hub --lines 50 --nostream"

# 代码更新流程
sshpass -p "Pr971V3j" ssh root@156.232.13.240 "cd /root/RWA-HUB && git pull && pm2 restart rwa-hub"
```

## 服务器状态监控

**应用健康检查**
```bash
# 检查应用是否在线和重启次数
pm2 info rwa-hub

# 监控CPU和内存使用
pm2 monit

# 检查应用错误日志
pm2 logs rwa-hub --err --lines 50
```

**注意事项**
- 服务器上运行多个应用，操作时需特别小心不要影响其他应用
- RWA-HUB应用ID为15，确保操作时使用正确的进程ID
- 如果应用频繁重启（重启次数>10），需要检查错误日志找出根本原因
- /admin/dashboard 路由出现500错误，需要优先修复

## 项目改进建议

1. **错误处理优化**: 修复admin dashboard的500错误
2. **日志系统**: 减少重复的日志输出，提高日志质量
3. **性能监控**: 实现应用性能监控和告警系统
4. **测试完善**: 添加更完整的自动化测试套件

## 代码开发规则

### 🚀 基础开发流程规则

1. **代码修改流程**：代码只在本地修改，修改好后提交到GitHub仓库，再从服务器拉取更新。不能在服务器上修改代码和配置。

2. **运行环境分工**：本地只用于修复代码，运行应用并检查运行情况的事情全部要在服务器上进行。

3. **问题修复原则**：
   - 遇到任何问题，分析问题的根本原因，精确修改问题代码
   - 不要用新建代码文件的方式替换、掩盖原本问题，是要解决原有问题
   - **最小改动原则**：只修改必要的逻辑，避免不必要的重构
   - **保留原有架构**：不重新设计系统架构，在现有基础上修复
   - **修复而非重写**：在原有代码基础上修复问题，而不是创建新的实现
   - **避免重复实现**：检查现有功能，移除重复的代码逻辑

4. **文档和说明规则**：
   - 每次修复完成问题后，不要生成说明文件、文档
   - 只需简单总结一下本次的修复思路和方式方法即可
   - 不要每次修复问题都创建一个说明或总结文档
   - 时刻保持系统目录的干净、清爽

5. **验证和测试**：
   - 修复完成任何问题后，首先要验证一下是否真正修复完成了本次修复任务
   - 然后再让用户测试和验收
   - 所有应用都是生产环境，不需要任何模拟代码和硬编码

6. **代码质量检查**：
   - 每次修复完问题检查一下本次修复的功能有没有新增或者残留的重复代码冲突的问题
   - 时刻确保代码库干净整洁，只保留一套正确可用的代码

### ⚡ Python语法和结构规则

- **缩进一致性**：所有字典定义必须保持一致的缩进，避免混合空格和制表符
- **循环结构**：for循环内的代码块必须正确缩进，cursor.execute等数据库操作必须在循环内部
- **语法检查**：修改代码前必须先进行语法检查：`python -m py_compile 文件名`
- **嵌套结构**：复杂的嵌套结构（字典、列表、函数调用）必须使用一致的缩进风格

### 🔧 配置管理和同步规则

- **三端同步**：前后端配置修改必须同时更新数据库配置表和JavaScript配置对象
- **默认值一致性**：配置项的默认值必须在前端、后端、数据库三处保持一致
- **参数同步添加**：新增配置参数时必须在HTML表单、JavaScript处理、后端API三处同步添加
- **数据库统一**：统一使用PostgreSQL，禁止混用SQLite或其他数据库

### 🗄️ 数据库操作规则

- **异常处理**：所有数据库查询必须包含异常处理，避免因表不存在导致系统崩溃
- **冲突预防**：INSERT语句必须使用`ON CONFLICT DO NOTHING`或`ON DUPLICATE KEY UPDATE`防止主键冲突
- **表结构检查**：配置更新操作必须先检查表结构存在性，再执行更新

### 🚢 部署和版本控制规则

- **紧急修复**：语法错误修复必须立即提交，避免阻塞其他功能开发
- **部署流程**：服务器部署流程为：本地测试 → git push → 服务器git pull → pm2 restart
- **配置测试**：配置文件修改必须在本地测试通过后再推送到生产环境
- **完整性验证**：关键功能修复后必须验证前端显示和后端逻辑的完整性

### 🎨 UI/UX开发规则

- **样式复用优先**：优先修复和增强现有CSS样式类，避免创建重复的专用样式
- **功能验证**：HTML结构已存在时，应检查现有样式类的适用性，避免过度设计
- **响应式考虑**：UI改进必须考虑移动端兼容性和响应式布局