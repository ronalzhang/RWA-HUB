# 常见问题FAQ

## 🚨 导入错误

### 问题：ImportError: cannot import name 'admin_required'
```python
# 解决方案：在__init__.py中正确导出
from .auth import admin_required, api_admin_required
```

### 问题：模块循环导入
```python
# 解决方案：调整导入顺序或使用延迟导入
def function():
    from .module import something  # 延迟导入
```

## 🔄 路由冲突

### 问题：AssertionError: View function mapping is overwriting
```python
# 解决方案：检查重复路由，临时禁用冲突蓝图
# app/routes/__init__.py
# app.register_blueprint(admin_solana_bp)  # 临时注释
```

### 问题：蓝图注册失败
```python
# 解决方案：确保正确的导入顺序
from .admin import admin_bp, admin_api_bp  # 先导入
app.register_blueprint(admin_bp)  # 后注册
```

## 📁 文件结构

### 问题：模块找不到
```bash
# 检查目录结构
app/routes/admin/
├── __init__.py  # 必须存在
├── auth.py     
└── assets.py   
```

### 问题：函数导出失败
```python
# __init__.py中必须导出常用函数
from .auth import admin_required
from .utils import is_admin
```

## 🔧 部署问题

### 问题：服务器重启失败
```bash
# 检查语法错误
python -m py_compile app/routes/admin/*.py

# 重启应用
pm2 restart all
pm2 logs --lines 50
```

### 问题：功能失效
```bash
# 检查数据库连接
python -c "from app import db; print(db.engine)"

# 检查路由注册
curl -I http://localhost:5000/admin/v2/assets
```

## 💾 数据库问题

### 问题：软删除不生效
```python
# 确保正确的状态值
ASSET_STATUS_DELETED = 4
asset.status = ASSET_STATUS_DELETED
db.session.commit()
```

### 问题：查询排除已删除
```python
# 正确的查询条件
query = Asset.query.filter(Asset.status != 4)
```

## 🛠️ 快速修复命令

```bash
# 检查应用状态
pm2 status

# 查看错误日志
pm2 logs app --lines 20

# 重启应用
pm2 restart app

# 检查端口占用
lsof -i :5000

# 检查Python语法
python -m py_compile filename.py
``` 