# RWA-HUB 代码同步和部署管理规范

## 代码管理流程规则

### 三地代码同步原则
1. **GitHub仓库** - 作为代码的唯一真实来源 (Single Source of Truth)
2. **本地开发环境** - 用于开发和测试
3. **生产服务器** - 从GitHub拉取最新代码部署

### 标准工作流程
```
本地开发 → Git提交 → GitHub推送 → 服务器拉取 → 部署
```

## 当前代码状态同步

### 1. 提交本地修改到Git
```bash
# 添加所有修改的文件
git add .

# 提交修改
git commit -m "fix: 完整资产流程修复 - 图片显示、智能合约部署、购买支付API"

# 推送到GitHub
git push origin main
```

### 2. 服务器同步代码
```bash
# 连接服务器
ssh root@156.236.74.200

# 进入项目目录
cd /root/RWA-HUB

# 备份当前代码
cp -r . ../RWA-HUB-backup-$(date +%Y%m%d_%H%M%S)

# 拉取最新代码
git pull origin main

# 重启应用
pkill -f "python.*app.py"
sleep 2
nohup python app.py > logs/app.log 2>&1 &
```

## 标准化部署脚本

### 使用自动同步部署脚本
```bash
# 执行标准化部署
./sync_and_deploy.sh
```

## 代码管理规范 (重要!)

### ⚠️ 严格遵守的规则

1. **禁止直接scp文件到服务器**
   - ❌ 不要使用: `scp file.py root@server:/path/`
   - ✅ 正确流程: 本地修改 → Git提交 → 推送 → 服务器拉取

2. **所有修改必须通过Git管理**
   - 本地开发和测试
   - Git add & commit
   - Push to GitHub
   - 服务器 git pull

3. **三地代码必须保持同步**
   - GitHub仓库 (主要源)
   - 本地开发环境
   - 生产服务器

### 标准工作流程

#### 开发新功能
```bash
# 1. 本地开发
vim app/routes/api.py

# 2. 测试功能
python test_script.py

# 3. 提交代码
git add .
git commit -m "feat: 新功能描述"

# 4. 推送到GitHub
git push origin main

# 5. 部署到服务器
./sync_and_deploy.sh
```

#### 修复Bug
```bash
# 1. 本地修复
vim app/templates/assets/detail.html

# 2. 测试修复
python test_complete_asset_flow.py

# 3. 提交修复
git add .
git commit -m "fix: 修复问题描述"

# 4. 推送和部署
git push origin main
./sync_and_deploy.sh
```

#### 紧急修复
```bash
# 1. 快速修复
git add .
git commit -m "hotfix: 紧急修复描述"
git push origin main

# 2. 立即部署
./sync_and_deploy.sh
```

## 部署验证

### 自动验证脚本
```bash
# 运行完整验证
python final_verification.py
```

### 手动验证检查点
1. ✅ 网站访问: https://rwa-hub.com
2. ✅ 资产详情: https://rwa-hub.com/assets/RH-106046
3. ✅ API端点: /api/assets/list
4. ✅ 智能合约部署功能
5. ✅ 购买流程API

## 回滚机制

### 代码回滚
```bash
# 回滚到上一个提交
git reset --hard HEAD~1
git push -f origin main
./sync_and_deploy.sh
```

### 服务器备份恢复
```bash
# 查看备份
ssh root@156.236.74.200 "ls -la /root/RWA-HUB-backups/"

# 恢复备份
ssh root@156.236.74.200 "
cd /root
rm -rf RWA-HUB
cp -r RWA-HUB-backups/rwa-hub-backup-YYYYMMDD_HHMMSS RWA-HUB
cd RWA-HUB
nohup python app.py > logs/app.log 2>&1 &
"
```

## 监控和维护

### 日志监控
```bash
# 实时查看应用日志
ssh root@156.236.74.200 "tail -f /root/RWA-HUB/logs/app.log"

# 检查错误日志
ssh root@156.236.74.200 "grep ERROR /root/RWA-HUB/logs/app.log | tail -20"
```

### 进程监控
```bash
# 检查应用进程
ssh root@156.236.74.200 "ps aux | grep python | grep app.py"

# 检查端口占用
ssh root@156.236.74.200 "netstat -tlnp | grep :9000"
```

### 数据库维护
```bash
# 连接数据库
ssh root@156.236.74.200 "cd /root/RWA-HUB && source venv/bin/activate && python -c 'from app import create_app; app = create_app(); print(\"Database connected\")'"
```

## 最佳实践

### 提交消息规范
- `feat:` 新功能
- `fix:` Bug修复  
- `docs:` 文档更新
- `style:` 代码格式
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具

### 分支管理
- `main` - 生产分支
- `develop` - 开发分支
- `feature/*` - 功能分支
- `hotfix/*` - 紧急修复

### 代码审查
- 重要功能需要代码审查
- 使用GitHub Pull Request
- 测试通过后合并到main

## 当前部署状态

### ✅ 已完成的修复
- 图片显示路径问题
- 智能合约部署API
- 购买流程API完整实现
- 数据库类型匹配修复
- 前端完整流程脚本

### 📊 验证结果
- 网站访问: ✅ 正常
- 资产浏览: ✅ 图片显示正常
- API功能: ✅ 完整可用
- 智能合约: ✅ 部署功能正常
- 购买流程: ✅ 端到端可用

### 🎯 下一步
- 前端钱包集成测试
- 真实区块链交易集成
- 用户体验优化
- 性能监控和优化