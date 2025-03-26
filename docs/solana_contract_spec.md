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

此功能允许资产所有者创建分红：
- 验证分红发起者是否为资产所有者
- 创建/更新分红池账户
- 从所有者USDC账户转账到分红池
- 记录分红总金额和时间戳

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

## 8. 注意事项

1. 在生产环境中，应确保使用安全的私钥管理方式
2. 定期更新Solana工具链以获取安全更新
3. 在主网部署前进行全面的测试和审计
4. 确保所有交易包含适当的费用以防止交易失败 