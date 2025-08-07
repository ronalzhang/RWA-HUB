# RWA-HUB 部署指南

## 概述

本项目使用统一的 `deploy.sh` 脚本进行部署，通过配置文件管理敏感信息，确保安全性。

## 快速开始

### 1. 首次使用

```bash
# 运行部署脚本（首次运行会自动创建配置文件）
./deploy.sh
```

首次运行时，脚本会自动创建 `deploy.config` 配置文件模板。

### 2. 配置服务器信息

编辑 `deploy.config` 文件，填入你的服务器信息：

```bash
# RWA-HUB 部署配置文件

# 服务器配置
SERVER_HOST="your-server-ip"           # 服务器IP地址
SERVER_USER="root"                     # SSH用户名
SERVER_PASSWORD="your-password"        # SSH密码
SERVER_PATH="/root/RWA-HUB"           # 服务器上的项目路径

# GitHub仓库配置
GITHUB_REPO="https://github.com/ronalzhang/RWA-HUB.git"
GITHUB_BRANCH="main"                   # 部署分支

# 数据库配置
DB_TYPE="postgresql"                   # postgresql 或 sqlite
PG_HOST="localhost"
PG_DATABASE="rwa_hub"
PG_USER="rwa_hub_user"
PG_PASSWORD="password"

# 应用配置
APP_PORT="9000"                        # 应用端口
SERVICE_NAME="rwa-hub"                 # 系统服务名
PYTHON_ENV="venv"                      # Python虚拟环境目录
```

### 3. 执行部署

```bash
./deploy.sh
```

## 部署流程

脚本会自动执行以下步骤：

1. **验证配置** - 检查配置文件和必要工具
2. **提交代码** - 自动提交并推送到GitHub
3. **连接服务器** - 使用SSH连接到目标服务器
4. **更新代码** - 在服务器上拉取最新代码
5. **安装依赖** - 安装Python依赖包
6. **数据库迁移** - 执行数据库迁移和修复
7. **启动服务** - 启动应用服务
8. **验证部署** - 测试API连接

## 特殊功能

### 分享消息修复

部署脚本会自动修复分享消息管理模块：

- 检查并添加缺失的 `message_type` 字段
- 初始化默认的分享消息数据
- 支持 PostgreSQL 和 SQLite 数据库

### 数据库支持

- **PostgreSQL**: 生产环境推荐
- **SQLite**: 开发环境使用

### 安全特性

- 敏感信息通过配置文件管理，不会提交到仓库
- 自动备份数据库（PostgreSQL）
- 配置文件被 `.gitignore` 排除

## 部署后验证

部署完成后，可以通过以下方式验证：

### 1. 检查服务状态

```bash
curl -s http://your-server:9000/api/health
```

### 2. 访问管理后台

- 主页: `http://your-server:9000`
- 管理后台: `http://your-server:9000/admin`
- 分享消息管理: `http://your-server:9000/admin/v2/share-messages`
- 分销系统配置: `http://your-server:9000/admin/v2/commission`

### 3. 查看服务器日志

```bash
sshpass -p 'your-password' ssh root@your-server 'cd /root/RWA-HUB && tail -f app.log'
```

## 故障排除

### 常见问题

1. **sshpass 未安装**
   ```bash
   # macOS
   brew install sshpass
   
   # Ubuntu
   sudo apt-get install sshpass
   
   # CentOS
   sudo yum install sshpass
   ```

2. **SSH连接失败**
   - 检查服务器IP、用户名、密码是否正确
   - 确认服务器SSH服务正常运行
   - 检查防火墙设置

3. **数据库连接失败**
   - 检查数据库配置信息
   - 确认数据库服务正常运行
   - 验证数据库用户权限

4. **应用启动失败**
   - 查看服务器日志: `tail -f app.log`
   - 检查Python依赖是否完整安装
   - 确认端口是否被占用

### 手动操作

如果自动部署失败，可以手动执行：

```bash
# 登录服务器
ssh root@your-server

# 进入项目目录
cd /root/RWA-HUB

# 拉取最新代码
git pull origin main

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动应用
python app.py
```

## 配置文件安全

⚠️ **重要提醒**:

- `deploy.config` 文件包含敏感信息，已被 `.gitignore` 排除
- 不要将配置文件提交到版本控制系统
- 定期更新服务器密码和数据库密码
- 在生产环境中使用强密码

## 支持

如果遇到问题，请检查：

1. 配置文件是否正确填写
2. 服务器网络连接是否正常
3. 数据库服务是否运行
4. 应用日志中的错误信息

---

**注意**: 本部署脚本适用于 CentOS/Ubuntu 服务器，其他系统可能需要调整相关命令。