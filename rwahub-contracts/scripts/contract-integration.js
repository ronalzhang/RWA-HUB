const anchor = require('@project-serum/anchor');
const { Connection, PublicKey, Keypair } = require('@solana/web3.js');
const { Token, TOKEN_PROGRAM_ID } = require('@solana/spl-token');

// 智能合约ID
const RWA_TRADE_PROGRAM_ID = new PublicKey('rwaHubTradeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX');
const RWA_DIVIDEND_PROGRAM_ID = new PublicKey('rwaHubDividendXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX');

// USDC代币ID（Solana主网）
const USDC_MINT = new PublicKey('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v');

// 平台手续费地址
const PLATFORM_FEE_ADDRESS = new PublicKey('EsfAFJFBa49RMc2UZNUjsWhGFZeA1uLgEkNPY5oYsDW4');

// 连接到Solana网络
const connection = new Connection('https://api.mainnet-beta.solana.com', 'confirmed');

/**
 * RWA-Hub智能合约交互类
 */
class RwaHubContracts {
  constructor(connection, wallet) {
    this.connection = connection;
    this.wallet = wallet;
    
    // 初始化Provider
    this.provider = new anchor.Provider(
      connection,
      wallet,
      { commitment: 'confirmed' }
    );
    
    // 加载交易合约
    this.tradeProgram = new anchor.Program(
      require('../target/idl/rwa_trade.json'), 
      RWA_TRADE_PROGRAM_ID,
      this.provider
    );
    
    // 加载分红合约
    this.dividendProgram = new anchor.Program(
      require('../target/idl/rwa_dividend.json'),
      RWA_DIVIDEND_PROGRAM_ID,
      this.provider
    );
  }
  
  /**
   * 初始化资产
   * @param {PublicKey} tokenMint 代币铸造地址
   * @param {number} price 代币价格（以USDC计价）
   * @param {number} totalSupply 总供应量
   * @param {number} platformFee 平台手续费（以千分比表示，例如35表示3.5%）
   * @returns {Promise<string>} 资产账户地址
   */
  async initializeAsset(tokenMint, price, totalSupply, platformFee = 35) {
    try {
      console.log(`初始化资产 - 代币: ${tokenMint.toString()}, 价格: ${price}, 供应量: ${totalSupply}`);
      
      // 创建资产账户
      const asset = anchor.web3.Keypair.generate();
      
      // 调用合约初始化资产
      const tx = await this.tradeProgram.rpc.initializeAsset(
        tokenMint,
        new anchor.BN(price),
        new anchor.BN(totalSupply),
        platformFee,
        {
          accounts: {
            owner: this.wallet.publicKey,
            asset: asset.publicKey,
            systemProgram: anchor.web3.SystemProgram.programId,
          },
          signers: [asset],
        }
      );
      
      console.log(`资产初始化成功 - 交易签名: ${tx}`);
      console.log(`资产账户地址: ${asset.publicKey.toString()}`);
      
      return asset.publicKey.toString();
    } catch (error) {
      console.error('初始化资产失败:', error);
      throw error;
    }
  }
  
  /**
   * 购买资产
   * @param {string} assetAddress 资产账户地址
   * @param {string} buyerAddress 买家地址
   * @param {number} amount 购买数量
   * @returns {Promise<string>} 交易签名
   */
  async buyAsset(assetAddress, buyerAddress, amount) {
    try {
      console.log(`购买资产 - 资产: ${assetAddress}, 买家: ${buyerAddress}, 数量: ${amount}`);
      
      const assetPublicKey = new PublicKey(assetAddress);
      const buyerPublicKey = new PublicKey(buyerAddress);
      
      // 获取资产信息
      const asset = await this.tradeProgram.account.asset.fetch(assetPublicKey);
      
      // 获取买家USDC账户
      const buyerTokenAccount = await this._findAssociatedTokenAccount(
        buyerPublicKey,
        USDC_MINT
      );
      
      // 获取卖家USDC账户（资产所有者）
      const sellerTokenAccount = await this._findAssociatedTokenAccount(
        asset.owner,
        USDC_MINT
      );
      
      // 获取平台手续费账户
      const platformFeeAccount = await this._findAssociatedTokenAccount(
        PLATFORM_FEE_ADDRESS,
        USDC_MINT
      );
      
      // 调用合约购买资产
      const tx = await this.tradeProgram.rpc.buyAsset(
        new anchor.BN(amount),
        {
          accounts: {
            buyer: buyerPublicKey,
            asset: assetPublicKey,
            buyerTokenAccount,
            sellerAccount: sellerTokenAccount,
            platformFeeAccount,
            tokenProgram: TOKEN_PROGRAM_ID,
            systemProgram: anchor.web3.SystemProgram.programId,
          },
        }
      );
      
      console.log(`资产购买成功 - 交易签名: ${tx}`);
      
      return tx;
    } catch (error) {
      console.error('购买资产失败:', error);
      throw error;
    }
  }
  
  /**
   * 创建分红
   * @param {string} creatorAddress 创建者地址
   * @param {string} assetTokenMint 资产代币铸造地址
   * @param {number} totalAmount 总分红金额
   * @param {number} deadlineDays 截止时间（天数）
   * @param {number} platformFee 平台手续费（以千分比表示，例如35表示3.5%）
   * @returns {Promise<string>} 分红账户地址
   */
  async createDividend(creatorAddress, assetTokenMint, totalAmount, deadlineDays = 30, platformFee = 35) {
    try {
      console.log(`创建分红 - 创建者: ${creatorAddress}, 资产: ${assetTokenMint}, 金额: ${totalAmount}`);
      
      const creatorPublicKey = new PublicKey(creatorAddress);
      const assetTokenMintPublicKey = new PublicKey(assetTokenMint);
      
      // 创建分红账户
      const dividend = anchor.web3.Keypair.generate();
      
      // 计算截止时间
      const currentTime = Math.floor(Date.now() / 1000);
      const deadline = currentTime + (deadlineDays * 24 * 60 * 60);
      
      // 获取创建者USDC账户
      const creatorTokenAccount = await this._findAssociatedTokenAccount(
        creatorPublicKey,
        USDC_MINT
      );
      
      // 获取平台手续费账户
      const platformFeeAccount = await this._findAssociatedTokenAccount(
        PLATFORM_FEE_ADDRESS,
        USDC_MINT
      );
      
      // 调用合约创建分红
      const tx = await this.dividendProgram.rpc.createDividend(
        new anchor.BN(totalAmount),
        new anchor.BN(deadline),
        assetTokenMintPublicKey,
        platformFee,
        {
          accounts: {
            creator: creatorPublicKey,
            dividend: dividend.publicKey,
            creatorTokenAccount,
            platformFeeAccount,
            tokenProgram: TOKEN_PROGRAM_ID,
            systemProgram: anchor.web3.SystemProgram.programId,
            rent: anchor.web3.SYSVAR_RENT_PUBKEY,
          },
          signers: [dividend],
        }
      );
      
      console.log(`分红创建成功 - 交易签名: ${tx}`);
      console.log(`分红账户地址: ${dividend.publicKey.toString()}`);
      
      return dividend.publicKey.toString();
    } catch (error) {
      console.error('创建分红失败:', error);
      throw error;
    }
  }
  
  /**
   * 领取分红
   * @param {string} dividendAddress 分红账户地址
   * @param {string} holderAddress 持有者地址
   * @param {number} amount 领取金额
   * @returns {Promise<string>} 交易签名
   */
  async claimDividend(dividendAddress, holderAddress, amount) {
    try {
      console.log(`领取分红 - 分红: ${dividendAddress}, 持有者: ${holderAddress}, 金额: ${amount}`);
      
      const dividendPublicKey = new PublicKey(dividendAddress);
      const holderPublicKey = new PublicKey(holderAddress);
      
      // 获取分红信息
      const dividend = await this.dividendProgram.account.dividend.fetch(dividendPublicKey);
      
      // 获取持有者USDC账户
      const holderTokenAccount = await this._findAssociatedTokenAccount(
        holderPublicKey,
        USDC_MINT
      );
      
      // 获取分红合约USDC账户
      const dividendTokenAccount = await this._findAssociatedTokenAccount(
        dividendPublicKey,
        USDC_MINT
      );
      
      // 调用合约领取分红
      const tx = await this.dividendProgram.rpc.claimDividend(
        new anchor.BN(amount),
        {
          accounts: {
            holder: holderPublicKey,
            dividend: dividendPublicKey,
            holderTokenAccount,
            dividendTokenAccount,
            tokenProgram: TOKEN_PROGRAM_ID,
            systemProgram: anchor.web3.SystemProgram.programId,
          },
        }
      );
      
      console.log(`分红领取成功 - 交易签名: ${tx}`);
      
      return tx;
    } catch (error) {
      console.error('领取分红失败:', error);
      throw error;
    }
  }
  
  /**
   * 内部方法：查找用户的Token账户
   * @private
   * @param {PublicKey} owner 用户地址
   * @param {PublicKey} mint 代币铸造地址
   * @returns {Promise<PublicKey>} Token账户地址
   */
  async _findAssociatedTokenAccount(owner, mint) {
    return Token.getAssociatedTokenAddress(
      anchor.web3.ASSOCIATED_TOKEN_PROGRAM_ID,
      TOKEN_PROGRAM_ID,
      mint,
      owner
    );
  }
}

module.exports = {
  RwaHubContracts,
  RWA_TRADE_PROGRAM_ID,
  RWA_DIVIDEND_PROGRAM_ID,
  USDC_MINT,
  PLATFORM_FEE_ADDRESS,
}; 