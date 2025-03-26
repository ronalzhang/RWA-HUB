# RWA-HUB Solana智能合约规范文档

## 1. 合约概述

RWA-HUB项目使用Solana区块链上的智能合约来管理资产代币化、购买和分红功能。合约主要包含以下核心功能：

1. **资产初始化**：创建新的代币化资产，包括名称、符号、总供应量等信息
2. **资产购买**：用户使用USDC代币购买资产代币的交易逻辑
3. **分红管理**：资产持有者进行分红分配的功能

## 2. 合约代码结构

合约代码位于`program`目录，使用Rust语言和Solana BPF (Berkley Packet Filter)技术编写：

- `lib.rs`: 合约入口点，处理指令分发
- `instruction.rs`: 定义合约支持的指令类型
- `processor.rs`: 包含主要业务逻辑实现
- `state.rs`: 定义链上存储的数据结构
- `error.rs`: 自定义错误类型

## 3. 主要功能详解

### 3.1 资产初始化 (InitializeAsset)

此功能允许创建新的资产代币，步骤包括：
- 创建资产账户存储资产元数据
- 初始化SPL代币铸造账户
- 设置资产的基本信息（名称、符号、供应量等）
- 记录资产所有者（创建者）信息

### 3.2 资产购买 (Buy)

此功能允许用户购买资产代币，步骤包括：
- 验证买家身份和签名
- 检查资产剩余供应量是否足够
- 计算购买总价（代币数量 * 单价）
- 从买家USDC账户转账到卖家USDC账户
- 从卖家代币账户转账到买家代币账户
- 更新资产剩余供应量

### 3.3 分红管理 (Dividend)

#### 3.3.1 账户结构
```rust
// 分红池账户
pub struct DividendPool {
    pub asset_mint: Pubkey,        // 资产代币地址
    pub total_amount: u64,         // 分红总金额
    pub token_price: u64,          // 分红时的代币价格
    pub distributor: Pubkey,       // 分红发起人
    pub holders_count: u32,        // 接收分红的持有人数量
    pub last_distribution: i64,    // 上次分红时间
    pub distribution_interval: i64, // 分红间隔
    pub transaction_hash: [u8; 32], // 交易哈希
    pub details: Vec<u8>,          // 分红详情（JSON格式）
}

// 分红记录账户
pub struct DividendRecord {
    pub holder: Pubkey,            // 持有者地址
    pub amount: u64,               // 应得分红金额
    pub claimed: bool,             // 是否已领取
    pub last_claim_time: i64,      // 上次领取时间
    pub transaction_hash: [u8; 32], // 领取交易哈希
}
```

#### 3.3.2 分红流程

1. **创建分红**
```rust
pub fn create_dividend(
    ctx: Context<CreateDividend>,
    amount: u64,
    interval: i64
) -> Result<()> {
    // 验证调用者权限
    require!(
        ctx.accounts.distributor.key() == ctx.accounts.asset.creator ||
        is_admin(ctx.accounts.distributor.key()),
        ErrorCode::Unauthorized
    );
    
    // 计算平台手续费（3.5%）
    let platform_fee = (amount * 35) / 1000;
    let actual_amount = amount - platform_fee;
    
    // 从发起人USDC账户转账到分红池
    transfer_usdc(
        ctx.accounts.distributor_usdc_account,
        ctx.accounts.dividend_pool,
        actual_amount
    )?;
    
    // 转账平台手续费
    transfer_usdc(
        ctx.accounts.distributor_usdc_account,
        ctx.accounts.platform_fee_account,
        platform_fee
    )?;
    
    // 获取代币持有人信息（排除发行者未售出代币）
    let holders = get_token_holders(ctx.accounts.asset_mint)?;
    let circulating_supply = calculate_circulating_supply(
        holders,
        ctx.accounts.asset.creator
    )?;
    
    // 计算每个代币的分红金额
    let dividend_per_token = actual_amount / circulating_supply;
    
    // 更新分红池信息
    let pool = &mut ctx.accounts.dividend_pool;
    pool.total_amount = actual_amount;
    pool.token_price = get_token_price(ctx.accounts.asset_mint)?;
    pool.distributor = ctx.accounts.distributor.key();
    pool.holders_count = holders.len() as u32;
    pool.last_distribution = Clock::get()?.unix_timestamp;
    pool.distribution_interval = interval;
    pool.transaction_hash = ctx.accounts.transaction.signature;
    
    // 记录分红详情
    let details = DividendDetails {
        amount: actual_amount,
        platform_fee,
        dividend_per_token,
        holders: holders.iter().map(|h| HolderInfo {
            address: h.address,
            amount: h.balance * dividend_per_token
        }).collect()
    };
    pool.details = serde_json::to_vec(&details)?;
    
    Ok(())
}
```

2. **计算流通代币数量**
```rust
fn calculate_circulating_supply(
    holders: Vec<TokenHolder>,
    creator: Pubkey
) -> Result<u64> {
    let mut circulating_supply = 0;
    
    for holder in holders {
        if holder.address != creator {
            circulating_supply += holder.balance;
        }
    }
    
    require!(circulating_supply > 0, ErrorCode::NoCirculatingSupply);
    Ok(circulating_supply)
}
```

3. **领取分红**
```rust
pub fn claim_dividend(
    ctx: Context<ClaimDividend>
) -> Result<()> {
    let record = &mut ctx.accounts.dividend_record;
    require!(!record.claimed, ErrorCode::AlreadyClaimed);
    
    // 从分红池转账到持有者USDC账户
    transfer_usdc(
        ctx.accounts.dividend_pool,
        ctx.accounts.holder_usdc_account,
        record.amount
    )?;
    
    // 更新记录
    record.claimed = true;
    record.last_claim_time = Clock::get()?.unix_timestamp;
    record.transaction_hash = ctx.accounts.transaction.signature;
    
    Ok(())
}
```

4. **查询分红信息**
```rust
pub fn get_dividend_info(
    ctx: Context<GetDividendInfo>
) -> Result<DividendInfo> {
    let pool = &ctx.accounts.dividend_pool;
    let record = &ctx.accounts.dividend_record;
    
    Ok(DividendInfo {
        total_amount: pool.total_amount,
        token_price: pool.token_price,
        dividend_per_token: pool.total_amount / pool.holders_count as u64,
        claimed: record.claimed,
        last_claim_time: record.last_claim_time,
        next_distribution: pool.last_distribution + pool.distribution_interval,
        details: serde_json::from_slice(&pool.details)?,
    })
}
```

#### 3.3.3 错误处理
```rust
#[error_code]
pub enum DividendError {
    #[msg("Unauthorized: Only asset creator or admin can create dividend")]
    Unauthorized,
    
    #[msg("No circulating supply available")]
    NoCirculatingSupply,
    
    #[msg("Dividend already claimed")]
    AlreadyClaimed,
    
    #[msg("Too early to trigger next dividend")]
    TooEarly,
    
    #[msg("Invalid dividend amount")]
    InvalidAmount,
    
    #[msg("Insufficient USDC balance")]
    InsufficientBalance,
}
```

## 4. 合约部署信息

### 4.1 部署地址

- **程序ID**：9AcvoQmz22KRcMhkLkeSkKs8W7ru6oae8GHcxrS83fKz
- **部署网络**：Solana Devnet (https://api.devnet.solana.com)
- **部署者地址**：EHzbrDvbzYj5QbYkcjWeaoXKNcgjayPgQRo9Et9C28jx

### 4.2 USDC代币配置

Solana Devnet上的USDC代币地址为：`EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`

### 4.3 平台地址

平台收款地址（用于收取手续费）：`HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd`

## 5. 部署步骤

1. **准备开发环境**:
   ```bash
   # 安装Rust和Solana工具链
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   curl -sSf https://raw.githubusercontent.com/solana-labs/solana/v1.17.0/install/solana-install-init.sh | sh
   
   # 安装Solana BPF工具
   cargo install cargo-build-bpf cargo-test-bpf
   ```

2. **编译合约**:
   ```bash
   cd program
   cargo build-bpf
   ```

3. **部署合约**:
   ```bash
   solana program deploy --keypair deployer-keypair.json \
     --program-id program-keypair.json \
     target/deploy/rwa_hub.so
   ```

## 6. 服务器配置

需要在服务器的`.env`文件中添加以下配置项：

```
# Solana网络配置
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_PROGRAM_ID=9AcvoQmz22KRcMhkLkeSkKs8W7ru6oae8GHcxrS83fKz
SOLANA_USDC_MINT=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
PLATFORM_FEE_ADDRESS=HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd

# Solana钱包配置（用于后端操作）
SOLANA_PRIVATE_KEY=<管理员私钥，请保密>
```

## 7. 合约调用示例

### 7.1 初始化资产
```javascript
// 创建资产示例代码
const transaction = new web3.Transaction();
transaction.add(
  program.instruction.initializeAsset(
    "Real Estate Token",
    "RET",
    new BN(1000000),
    6,
    {
      accounts: {
        creator: wallet.publicKey,
        assetAccount: assetPDA,
        mint: mintAccount,
        systemProgram: web3.SystemProgram.programId,
        tokenProgram: TOKEN_PROGRAM_ID,
      },
    }
  )
);
```

### 7.2 购买资产
```javascript
// 购买资产示例代码
const transaction = new web3.Transaction();
transaction.add(
  program.instruction.buy(
    new BN(100), // 购买数量
    {
      accounts: {
        buyer: wallet.publicKey,
        buyerTokenAccount: buyerTokenAccount,
        sellerTokenAccount: sellerTokenAccount,
        buyerUsdcAccount: buyerUsdcAccount,
        sellerUsdcAccount: sellerUsdcAccount,
        tokenProgram: TOKEN_PROGRAM_ID,
        asset: assetPDA,
      },
    }
  )
);
```

### 7.3 分红操作
```javascript
// 创建分红示例
const transaction = new web3.Transaction();
transaction.add(
  program.instruction.createDividend(
    new BN(1000000), // 分红金额（USDC）
    new BN(86400),   // 分红间隔（24小时）
    {
      accounts: {
        distributor: wallet.publicKey,
        distributorUsdcAccount: distributorUsdcAccount,
        dividendPool: dividendPoolPDA,
        platformFeeAccount: platformFeeAccount,
        asset: assetPDA,
        assetMint: assetMint,
        transaction: transaction.publicKey,
      },
    }
  )
);

// 领取分红示例
const transaction = new web3.Transaction();
transaction.add(
  program.instruction.claimDividend(
    {
      accounts: {
        holder: wallet.publicKey,
        holderUsdcAccount: holderUsdcAccount,
        dividendPool: dividendPoolPDA,
        dividendRecord: dividendRecordPDA,
        transaction: transaction.publicKey,
      },
    }
  )
);
```

## 8. 注意事项

1. 在生产环境中，应确保使用安全的私钥管理方式
2. 定期更新Solana工具链以获取安全更新
3. 在主网部署前进行全面的测试和审计
4. 确保所有交易包含适当的费用以防止交易失败
5. 分红相关注意事项：
   - 确保分红池账户有足够的SOL支付租金
   - 分红计算时注意处理精度问题
   - 实现分红查询接口，方便用户查看应得分红
   - 添加分红事件日志，便于前端展示分红历史
   - 考虑添加紧急暂停机制，以应对可能的漏洞 