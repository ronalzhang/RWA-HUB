# RWA-HUB Solana 程序

这是 RWA-HUB 的 Solana 智能合约，用于管理实体资产的通证化、交易和分红。

## 准备工作

1. 安装 Solana CLI 工具:
   ```bash
   sh -c "$(curl -sSfL https://release.solana.com/v1.17.0/install)"
   ```

2. 安装 Rust 和 Cargo:
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

3. 安装 Solana 程序依赖:
   ```bash
   rustup component add rustfmt
   rustup component add clippy
   ```

## 编译程序

```bash
cd program
cargo build-bpf
```

## 部署到 Devnet

1. 配置 Solana CLI 使用 devnet:
   ```bash
   solana config set --url https://api.devnet.solana.com
   ```

2. 创建一个部署钱包:
   ```bash
   solana-keygen new -o deployer.json
   ```

3. 获取测试 SOL:
   ```bash
   solana airdrop 2 $(solana-keygen pubkey deployer.json) --url https://api.devnet.solana.com
   ```

4. 部署程序:
   ```bash
   solana program deploy ./target/deploy/rwa_hub.so --keypair deployer.json
   ```

5. 程序部署成功后会显示程序 ID，请记录此 ID 并更新环境变量:
   ```
   Program Id: <YOUR_PROGRAM_ID>
   ```

## 更新环境变量

将程序 ID 添加到项目的 `.env` 文件中:

```
SOLANA_PROGRAM_ID=<YOUR_PROGRAM_ID>
SOLANA_RPC_URL=https://api.devnet.solana.com
```

## 测试程序

1. 创建资产:
   ```bash
   python -m tests.test_create_asset --asset-id 1 --name "测试资产" --symbol "TEST" --supply 1000
   ```

2. 购买资产:
   ```bash
   python -m tests.test_buy_asset --asset-id 1 --amount 10
   ```

3. 分红:
   ```bash
   python -m tests.test_dividend --asset-id 1 --amount 100
   ``` 