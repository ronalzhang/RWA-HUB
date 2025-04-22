# RWA-HUB 资产管理工具集

本文档介绍了RWA-HUB平台的三个命令行工具，用于资产的发行、查询和链上信息更新。这些工具可以方便地管理平台上的实物资产代币化业务。

## 环境要求

- Python 3.6+
- 安装依赖库: `pip install sqlalchemy psycopg2-binary python-dotenv`
- 设置环境变量或在`.env`文件中配置数据库连接

## 1. 发行资产 (issue_asset.py)

### 功能
发行新的资产，生成唯一的代币符号，并存储到数据库中。

### 使用方法
```bash
python issue_asset.py --name <资产名称> --type <资产类型> --blockchain <区块链> --issuer <发行人地址> [选项]
```

### 参数说明
- `--name, -n`: 资产名称（必填）
- `--type, -t`: 资产类型（必填），支持的类型:
  - real_estate: 不动产
  - art: 艺术品
  - commodity: 商品
  - fund: 基金
  - bond: 债券
  - stock: 股票
- `--description, -d`: 资产描述（可选）
- `--blockchain, -b`: 区块链平台（必填），支持的区块链:
  - ethereum: 以太坊
  - solana: Solana
  - binance: 币安智能链
  - polygon: Polygon
- `--issuer, -i`: 发行人区块链地址（必填）
- `--metadata-file, -m`: JSON格式的元数据文件路径（可选）
- `--metadata-json, -j`: 直接提供JSON格式的元数据（可选）

### 示例
```bash
# 发行一个不动产资产
python issue_asset.py --name "上海公寓A" --type real_estate --blockchain ethereum --issuer 0x123456789abcdef --description "位于上海市中心的高档公寓"

# 使用元数据文件
python issue_asset.py --name "数字艺术品" --type art --blockchain solana --issuer DL55SriT5kP57hVdLPGsHpYbg9BnJfXXXXXXXXX --metadata-file metadata.json
```

## 2. 查询资产 (query_asset.py)

### 功能
查询特定代币符号对应的资产详情及相关交易记录。

### 使用方法
```bash
python query_asset.py [代币符号]
```

### 参数说明
- `token_symbol`: 资产的代币符号，如不提供则使用默认值"RH-108235"

### 示例
```bash
# 查询指定代币
python query_asset.py RRE-245789

# 使用默认代币查询
python query_asset.py
```

### 输出内容
脚本输出包括:
- 资产基本信息：ID、名称、类型、代币符号等
- 资产元数据：发行人地址、创建日期等
- 资产特有信息：如不动产的位置、面积等
- 相关交易记录：包括交易ID、买卖双方地址、金额等

## 3. 更新资产链上信息 (update_asset_onchain.py)

### 功能
更新资产的链上信息，包括合约地址、交易哈希和状态，或列出系统中的资产。

### 使用方法
```bash
# 更新资产链上信息
python update_asset_onchain.py update --token <代币符号> --contract <合约地址> [选项]

# 列出资产
python update_asset_onchain.py list [--status <状态>]
```

### 子命令和参数

#### update 子命令
- `--token, -t`: 资产的代币符号（必填）
- `--contract, -c`: 合约地址（必填）
- `--tx-hash`: 部署交易的哈希值（可选）
- `--status`: 资产状态（可选，默认为"active"）
  - active: 活跃
  - inactive: 非活跃
  - pending: 待处理

#### list 子命令
- `--status`: 按状态筛选资产（可选）
  - active: 显示活跃资产
  - inactive: 显示非活跃资产
  - pending: 显示待处理资产

### 示例
```bash
# 更新资产的合约地址和状态
python update_asset_onchain.py update --token RRE-245789 --contract 0x7c1956dd3108725417631cc6d08dfa9ed92a72b9 --status active

# 更新资产的合约地址并记录交易哈希
python update_asset_onchain.py update --token RRE-245789 --contract 0x7c1956dd3108725417631cc6d08dfa9ed92a72b9 --tx-hash 0x12345...

# 列出所有活跃状态的资产
python update_asset_onchain.py list --status active

# 列出所有资产
python update_asset_onchain.py list
```

## 数据库配置

所有脚本都依赖于正确配置的数据库连接。可以通过以下方式设置:

1. 在工作目录创建`.env`文件并添加以下内容:
   ```
   DATABASE_URL=postgresql://用户名:密码@主机/数据库名
   ```

2. 或使用环境变量:
   ```bash
   export DATABASE_URL=postgresql://用户名:密码@主机/数据库名
   ```

如果未设置，则使用默认值: `postgresql://rwa_hub_user:password@localhost/rwa_hub`

## 注意事项

1. 这些脚本应当在RWA-HUB应用的工作目录下运行，以确保能够正确连接到数据库。
2. 确保数据库连接信息正确，脚本执行时会检查表结构并创建必要的表。
3. 对于资产类型和区块链平台，脚本仅支持预设的选项，请确保输入正确。
4. 元数据可以通过文件或直接的JSON字符串提供，便于扩展资产的附加信息。
5. 脚本包含地址格式验证，确保输入的区块链地址格式正确。 