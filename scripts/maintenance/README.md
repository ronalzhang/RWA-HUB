# 维护脚本

此目录包含用于系统维护和问题排查的实用脚本。

## 脚本说明

### trigger_cmd.py
触发特定资产的支付确认流程。直接执行脚本将处理预设的资产。

使用示例：
```bash
python -m scripts.maintenance.trigger_cmd
```

### trigger_payment.py
用于手动触发资产支付确认处理。需要在脚本中设置要处理的资产ID和交易哈希。

使用示例：
```bash
python -m scripts.maintenance.trigger_payment
```

### update_asset_status.py
用于手动更新资产状态，通常用于修复状态异常的资产。

使用示例：
```bash
python -m scripts.maintenance.update_asset_status
```

## 注意事项

1. 这些脚本仅供系统维护人员使用
2. 在使用前请确保了解其功能和影响
3. 不要在生产环境随意执行这些脚本
4. 如需修改，请遵循代码管理流程：本地修改 → 提交到仓库 → 服务器拉取 