# RWA-HUB 资产管理平台

RWA-HUB 是一个基于 Web3 技术的资产管理平台，支持不动产和类不动产的数字化和通证化管理。

## 功能特点

- 资产管理：支持不动产和类不动产的创建、编辑、删除和查询
- 权限控制：基于区块链地址的角色权限管理系统
- 通证化：支持资产的通证化和分红管理
- 安全性：完整的安全机制和数据验证

## 技术栈

- 后端：Python Flask
- 数据库：SQLite（可扩展至其他数据库）
- Web3：支持以太坊网络
- 前端：HTML/CSS/JavaScript

## 安装说明

1. 克隆仓库：
```bash
git clone https://github.com/ronalzhang/RWA-HUB.git
cd RWA-HUB
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置信息
```

5. 初始化数据库：
```bash
flask db upgrade
```

6. 运行程序：
```bash
python run.py
```

## 开发环境

- Python 3.8+
- Flask 2.3.3
- SQLAlchemy 2.0.37
- Web3 6.10.0

## 部署说明

1. 生产环境配置：
   - 使用生产级别的 WSGI 服务器（如 Gunicorn）
   - 启用 HTTPS
   - 配置安全的密钥
   - 使用生产级别的数据库

2. 环境变量配置：
   - SECRET_KEY：应用密钥
   - FLASK_ENV：运行环境（development/production）
   - DATABASE_URL：数据库连接 URL
   - WEB3_PROVIDER_URI：Web3 提供者 URI

## 贡献指南

欢迎提交 Pull Request 和 Issue。在提交之前，请确保：

1. 代码符合 PEP 8 规范
2. 添加了必要的测试
3. 更新了文档

## 许可证

MIT License 