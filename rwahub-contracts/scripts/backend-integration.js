/**
 * RWA-HUB后端集成示例
 * 展示如何在Flask应用中集成Solana智能合约
 */

const anchor = require('@project-serum/anchor');
const { Keypair } = require('@solana/web3.js');
const { RwaHubContracts } = require('./contract-integration');
const fs = require('fs');
const path = require('path');

/**
 * 初始化RWA-Hub合约连接
 * 在Flask应用中调用此函数来初始化合约连接
 */
function initializeContracts() {
  try {
    // 加载服务钱包私钥
    const keyPath = path.resolve(process.env.HOME, '.config/solana/id.json');
    const secretKey = Uint8Array.from(JSON.parse(fs.readFileSync(keyPath, 'utf8')));
    const wallet = new anchor.Wallet(Keypair.fromSecretKey(secretKey));
    
    // 连接到Solana网络
    const connection = new anchor.web3.Connection(
      'https://api.mainnet-beta.solana.com',
      'confirmed'
    );
    
    // 创建合约实例
    const contracts = new RwaHubContracts(connection, wallet);
    console.log('RWA-Hub智能合约已初始化');
    
    return contracts;
  } catch (error) {
    console.error('初始化合约失败:', error);
    throw error;
  }
}

/**
 * Python <-> JavaScript交互示例
 * 
 * 在Python中可以使用以下方式调用：
 * ```python
 * import subprocess
 * import json
 * 
 * def init_asset(token_mint, price, total_supply):
 *     cmd = [
 *         "node", 
 *         "scripts/backend-integration.js", 
 *         "initAsset", 
 *         token_mint, 
 *         str(price), 
 *         str(total_supply)
 *     ]
 *     result = subprocess.run(cmd, capture_output=True, text=True)
 *     return json.loads(result.stdout)
 * 
 * def buy_asset(asset_address, buyer_address, amount):
 *     cmd = [
 *         "node", 
 *         "scripts/backend-integration.js", 
 *         "buyAsset", 
 *         asset_address, 
 *         buyer_address, 
 *         str(amount)
 *     ]
 *     result = subprocess.run(cmd, capture_output=True, text=True)
 *     return json.loads(result.stdout)
 * ```
 */

// 命令行参数处理
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  
  try {
    // 初始化合约
    const contracts = initializeContracts();
    
    let result = {};
    
    // 执行相应的命令
    switch (command) {
      case 'initAsset':
        result = await contracts.initializeAsset(
          new anchor.web3.PublicKey(args[1]), // token_mint
          parseInt(args[2]),                   // price
          parseInt(args[3]),                   // total_supply
          args[4] ? parseInt(args[4]) : 35     // platform_fee (optional)
        );
        break;
        
      case 'buyAsset':
        result = await contracts.buyAsset(
          args[1],                            // asset_address
          args[2],                            // buyer_address
          parseInt(args[3])                   // amount
        );
        break;
        
      case 'createDividend':
        result = await contracts.createDividend(
          args[1],                            // creator_address
          args[2],                            // asset_token_mint
          parseInt(args[3]),                  // total_amount
          args[4] ? parseInt(args[4]) : 30,   // deadline_days (optional)
          args[5] ? parseInt(args[5]) : 35    // platform_fee (optional)
        );
        break;
        
      case 'claimDividend':
        result = await contracts.claimDividend(
          args[1],                            // dividend_address
          args[2],                            // holder_address
          parseInt(args[3])                   // amount
        );
        break;
        
      default:
        throw new Error(`未知命令: ${command}`);
    }
    
    // 输出结果为JSON格式
    console.log(JSON.stringify(result));
    
  } catch (error) {
    // 输出错误信息
    console.error(JSON.stringify({
      error: true,
      message: error.message,
      stack: error.stack
    }));
    process.exit(1);
  }
}

// 执行主函数
main(); 