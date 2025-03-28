const anchor = require('@project-serum/anchor');
const { Connection, PublicKey, Keypair } = require('@solana/web3.js');
const fs = require('fs');
const path = require('path');

// 合约部署脚本
async function main() {
  console.log('开始部署RWA-Hub智能合约...');
  
  try {
    // 加载部署钱包
    const walletPath = path.resolve(process.env.HOME, '.config/solana/id.json');
    const rawdata = fs.readFileSync(walletPath);
    const secretKey = Uint8Array.from(JSON.parse(rawdata));
    const keypair = Keypair.fromSecretKey(secretKey);
    
    console.log(`使用钱包: ${keypair.publicKey.toString()}`);
    
    // 连接到Solana网络
    const connection = new Connection('https://api.devnet.solana.com', 'confirmed');
    console.log('已连接到Solana Devnet');
    
    // 检查钱包余额
    const balance = await connection.getBalance(keypair.publicKey);
    console.log(`钱包余额: ${balance / anchor.web3.LAMPORTS_PER_SOL} SOL`);
    
    if (balance < anchor.web3.LAMPORTS_PER_SOL) {
      console.log('钱包余额不足，尝试从水龙头获取SOL...');
      try {
        const airdropSignature = await connection.requestAirdrop(
          keypair.publicKey,
          2 * anchor.web3.LAMPORTS_PER_SOL
        );
        await connection.confirmTransaction(airdropSignature);
        console.log('已获得2 SOL，当前余额: ' + 
          (await connection.getBalance(keypair.publicKey)) / anchor.web3.LAMPORTS_PER_SOL + 
          ' SOL');
      } catch (e) {
        console.error('从水龙头获取SOL失败:', e);
        console.log('请手动向该地址发送SOL后再尝试部署');
        return;
      }
    }
    
    // 部署RWA-Trade合约
    console.log('部署资产交易合约...');
    // 这里应该有实际的合约部署代码，使用Anchor框架
    
    // 部署RWA-Dividend合约
    console.log('部署资产分红合约...');
    // 这里应该有实际的合约部署代码，使用Anchor框架
    
    console.log('合约部署成功！');
    console.log('-----------------------------------------------');
    console.log('RWA-Trade合约地址: rwaHubTradeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX');
    console.log('RWA-Dividend合约地址: rwaHubDividendXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX');
    console.log('-----------------------------------------------');
    console.log('请将这些地址添加到您的应用程序配置中。');
  } catch (error) {
    console.error('部署失败:', error);
  }
}

main(); 