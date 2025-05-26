# 服务器支付配置测试指令

## 在服务器上运行测试的步骤

### 1. 连接到服务器并切换到项目目录
```bash
cd /root/RWA-HUB
```

### 2. 拉取最新代码
```bash
git pull origin main
```

### 3. 激活Python虚拟环境
```bash
source venv/bin/activate
```

### 4. 安装requests库（如果还没有安装）
```bash
pip install requests
```

### 5. 运行测试脚本
```bash
python3 test_server_payment_config.py
```

## 测试脚本功能说明

这个测试脚本会：

1. **测试生产环境API** - 检查 https://rwa-hub.com/api/service/config/payment_settings
2. **测试数据库配置** - 检查SystemConfig表中的配置
3. **测试本地API** - 检查服务器本地的API响应
4. **自动更新配置** - 如果配置不正确，会自动更新为正确的地址

## 期望的测试结果

测试脚本应该显示：
- 平台收款地址: `EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4`
- 资产创建收款地址: `EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4`
- 资产创建费用: `0.02 USDC`

## 如果测试失败

如果测试显示配置不匹配，脚本会自动尝试更新数据库配置。更新后需要：

1. **重启应用服务**
```bash
# 使用PM2重启（如果使用PM2）
pm2 restart rwa-hub

# 或者使用重启脚本
bash scripts/restart.sh
```

2. **再次运行测试确认**
```bash
python3 test_server_payment_config.py
```

## 故障排除

### 如果API返回404或500错误
1. 检查服务器是否正常运行：`pm2 status` 或 `ps aux | grep python`
2. 检查日志：`tail -f logs/app_restart.log`
3. 重启服务：`bash scripts/restart.sh`

### 如果数据库连接失败
1. 检查数据库服务状态
2. 检查.env文件中的数据库配置
3. 确认数据库权限

### 如果配置更新失败
1. 检查数据库写入权限
2. 手动通过管理后台更新配置
3. 检查SystemConfig模型是否正确

## 联系信息

如果遇到问题，请提供：
1. 测试脚本的完整输出
2. 服务器日志文件内容
3. 错误发生的具体时间 