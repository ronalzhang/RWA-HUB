# RWA-HUB 部署和重启指南

本文档提供了RWA-HUB项目的部署和重启指南，以确保应用程序的稳定运行。

## 文件结构

```
/root/RWA-HUB/            # 项目根目录
├── app/                  # 应用主目录
├── migrations/           # 数据库迁移脚本
│   └── scripts/          # 配置和其他脚本
├── scripts/              # 系统脚本
│   └── restart.sh        # 应用重启脚本
├── venv/                 # Python虚拟环境
├── logs/                 # 日志目录
│   ├── app.log           # 应用日志
│   └── app_restart.log   # 重启日志
└── run.py                # 应用入口文件
```

## 部署流程

### 1. 从GitHub克隆代码

```bash
git clone https://github.com/ronalzhang/RWA-HUB.git
cd RWA-HUB
```

### 2. 设置虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置数据库和环境变量

按照`.env.example`文件配置必要的环境变量，确保数据库连接正确。

### 4. 使用PM2管理应用

使用PM2启动应用：

```bash
pm2 start run.py --name rwa-hub --interpreter python
pm2 save
```

## 重启应用

### 方法1: 使用PM2重启

```bash
pm2 restart rwa-hub
```

### 方法2: 使用重启脚本（更安全）

```bash
cd /root/RWA-HUB
bash scripts/restart.sh
```

重启脚本会执行以下操作：
1. 停止所有运行中的应用进程
2. 检查并释放9000端口
3. 激活虚拟环境
4. 启动应用
5. 验证应用是否成功启动

## 故障排除

### 端口占用问题

如果9000端口被占用，可以使用以下命令来查找并终止占用端口的进程：

```bash
lsof -i :9000
kill -9 <PID>
```

### 多个Python进程

有时可能会出现多个Python进程同时运行的情况，可以使用以下命令终止所有Python进程：

```bash
pkill -9 python
```

然后重新启动应用：

```bash
pm2 start run.py --name rwa-hub --interpreter python
```

### 检查日志

查看应用日志：

```bash
tail -f logs/app.log
```

查看重启日志：

```bash
tail -f logs/app_restart.log
```

## 代码管理最佳实践

1. **避免直接在服务器上修改代码**：
   - 所有代码修改应在本地开发环境完成
   - 提交到Git仓库
   - 在服务器上拉取更新

2. **代码更新流程**：
   ```bash
   # 在服务器上
   cd /root/RWA-HUB
   git pull origin main
   pm2 restart rwa-hub
   ```

3. **配置更新**：
   - 所有配置更改应通过管理界面完成
   - 重要配置应记录在文档中

## 重要配置

确保以下配置已正确设置：

- `PURCHASE_CONTRACT_ADDRESS`: Solana交易合约地址
- `PLATFORM_FEE_BASIS_POINTS`: 平台费率基点
- 其他关键配置项

## 监控

定期检查应用状态：

```bash
pm2 status
```

检查系统资源使用情况：

```bash
htop
``` 