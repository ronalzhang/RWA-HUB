## 分红机制设计

### 1. 智能合约设计
#### 1.1 核心功能
- 资产所有者可以发起分红
- 支持USDC作为分红货币
- 按持有代币比例自动分配
- 收取1.5%平台手续费
- 记录完整分红历史
- 平台手续费发送至管理员多签钱包地址

#### 1.2 分红限制
- 最小分红金额: 10000 USDC
- 建议分红金额范围(基于Gas费用占比考虑):
  | 持有人数 | 建议分红金额 | Gas费用占比 |
  |---------|------------|------------|
  | 10人以下 | ≥10000 USDC | 约0.3% |
  | 10-50人  | ≥15000 USDC | 约0.5% |
  | 50-100人 | ≥20000 USDC | 约1% |
  | 100-500人 | ≥50000 USDC | 约1.5% |
  | 500-1000人 | ≥100000 USDC | 约2% |

#### 1.3 Gas费用说明
- 基础操作消耗:
  - approve(): 约46,000 Gas
  - transferFrom(): 约65,000 Gas
  - 每位接收者transfer(): 约35,000 Gas
- 批量处理优化:
  - 每批次处理1000位持有人
  - 单批次Gas消耗: 约35,000,000 Gas (35,000 × 1000)
  - 单批次预估费用: 约2.1 ETH (以30 Gwei gas价格计算)
  - 建议在gas价格较低时执行大批量分红

### 2. 前端实现
#### 2.1 分红发起模块
- 位置: 项目详情页购买模块下方
- 访问控制: 仅项目发起地址可见
- 显示内容:
  - 当前持有人数量
  - 预估Gas费用
  - 平台手续费(1.5%)
  - 建议分红金额范围
  - 预计每代币分红金额
  - 发起分红按钮

#### 2.2 分红历史模块
- 位置: 分红发起模块下方
- 访问控制: 所有访问者可见(无需登录)
- 显示内容:
  - 分红日期(精确到日)
  - 分红总金额(包含所有费用)
- 样式: 与上方模块对齐

### 3. 智能合约接口
```solidity
interface IAssetDividend {
    struct DividendRecord {
        uint256 timestamp;
        uint256 totalAmount;      // 总分红金额(包含所有费用)
        uint256 actualAmount;     // 实际分配金额(内部记录)
        uint256 platformFee;      // 平台费用(内部记录)
        uint256 holdersCount;     // 持有人数(内部记录)
        uint256 gasUsed;         // gas消耗(内部记录)
    }

    // 平台费率 1.5%
    uint256 public constant PLATFORM_FEE_RATE = 150; // 基点(1/10000)
    // 管理员多签钱包地址
    address public adminMultiSigWallet;
    // 每批次处理数量
    uint256 public constant BATCH_SIZE = 1000;

    function distributeDividend(address tokenAddress, uint256 amount) external;
    function getDividendHistory(address tokenAddress) external view returns (DividendRecord[] memory);
    function setAdminMultiSigWallet(address _wallet) external;
}
```

### 4. 数据结构
```sql
CREATE TABLE dividend_records (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL,
    total_amount DECIMAL(20,6) NOT NULL,
    actual_amount DECIMAL(20,6) NOT NULL,
    platform_fee DECIMAL(20,6) NOT NULL,
    holders_count INTEGER NOT NULL,
    gas_used BIGINT NOT NULL,
    tx_hash VARCHAR(66) NOT NULL,
    created_at DATE NOT NULL DEFAULT CURRENT_DATE,
    FOREIGN KEY (asset_id) REFERENCES assets(id)
);
```

### 5. 优化建议
1. 根据持有人数量自动推荐最优分红金额
2. 提供Gas费用预估功能
3. 在gas价格低于25 Gwei时执行大批量分红
4. 考虑将多个小额分红合并执行以优化成本
5. 针对大批量分红(>1000人)提供分步执行选项

### 6. 注意事项
1. Gas费用会随ETH价格和网络拥堵情况波动
2. 建议在分红前检查网络Gas价格
3. 确保资产所有者钱包中有足够的ETH支付Gas费用
4. 平台手续费(1.5%)直接发送至管理员多签钱包
5. 大批量分红建议在gas价格较低时执行 