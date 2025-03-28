use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use solana_program::program::invoke;
use solana_program::system_instruction;

declare_id!("rwaHubTradeXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX");

#[program]
pub mod rwa_trade {
    use super::*;

    /// 初始化资产
    pub fn initialize_asset(
        ctx: Context<InitializeAsset>,
        token_mint: Pubkey,
        price: u64,
        total_supply: u64,
        platform_fee: u8,
    ) -> Result<()> {
        let asset = &mut ctx.accounts.asset;
        let owner = &ctx.accounts.owner;

        // 验证平台手续费合理性
        require!(platform_fee <= 100, ErrorCode::InvalidFeeAmount);

        // 初始化资产信息
        asset.owner = owner.key();
        asset.token_mint = token_mint;
        asset.price = price;
        asset.total_supply = total_supply;
        asset.available_supply = total_supply;
        asset.platform_fee = platform_fee;
        asset.created_at = Clock::get()?.unix_timestamp;
        asset.updated_at = Clock::get()?.unix_timestamp;

        Ok(())
    }

    /// 购买资产
    pub fn buy_asset(ctx: Context<BuyAsset>, amount: u64) -> Result<()> {
        let asset = &mut ctx.accounts.asset;
        let buyer = &ctx.accounts.buyer;
        let platform_fee_account = &ctx.accounts.platform_fee_account;
        let seller_account = &ctx.accounts.seller_account;
        let buyer_token_account = &ctx.accounts.buyer_token_account;
        let token_program = &ctx.accounts.token_program;

        // 验证资产是否可购买
        require!(asset.available_supply >= amount, ErrorCode::InsufficientSupply);

        // 计算支付金额
        let total_amount = amount.checked_mul(asset.price).ok_or(ErrorCode::Overflow)?;

        // 计算平台手续费和卖家金额
        let platform_fee_amount = total_amount
            .checked_mul(asset.platform_fee as u64)
            .ok_or(ErrorCode::Overflow)?
            .checked_div(1000)
            .ok_or(ErrorCode::Overflow)?; // platform_fee 是千分比，例如35表示3.5%
        let seller_amount = total_amount.checked_sub(platform_fee_amount).ok_or(ErrorCode::Overflow)?;

        // 向平台转账手续费
        token::transfer(
            CpiContext::new(
                token_program.to_account_info(),
                Transfer {
                    from: buyer_token_account.to_account_info(),
                    to: platform_fee_account.to_account_info(),
                    authority: buyer.to_account_info(),
                },
            ),
            platform_fee_amount,
        )?;

        // 向卖家转账
        token::transfer(
            CpiContext::new(
                token_program.to_account_info(),
                Transfer {
                    from: buyer_token_account.to_account_info(),
                    to: seller_account.to_account_info(),
                    authority: buyer.to_account_info(),
                },
            ),
            seller_amount,
        )?;

        // 更新资产状态
        asset.available_supply = asset
            .available_supply
            .checked_sub(amount)
            .ok_or(ErrorCode::Overflow)?;
        asset.updated_at = Clock::get()?.unix_timestamp;

        // 记录交易信息可以在这里添加

        emit!(AssetPurchased {
            asset: asset.key(),
            buyer: buyer.key(),
            amount,
            total_amount,
            platform_fee_amount,
            seller_amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }

    /// 更新资产价格
    pub fn update_asset_price(ctx: Context<UpdateAsset>, new_price: u64) -> Result<()> {
        let asset = &mut ctx.accounts.asset;
        let owner = &ctx.accounts.owner;

        // 验证权限
        require!(asset.owner == owner.key(), ErrorCode::Unauthorized);

        // 更新价格
        asset.price = new_price;
        asset.updated_at = Clock::get()?.unix_timestamp;

        emit!(AssetPriceUpdated {
            asset: asset.key(),
            old_price: asset.price,
            new_price,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }

    /// 更新资产平台手续费
    pub fn update_asset_fee(ctx: Context<UpdateAsset>, new_fee: u8) -> Result<()> {
        let asset = &mut ctx.accounts.asset;
        let owner = &ctx.accounts.owner;

        // 验证权限
        require!(asset.owner == owner.key(), ErrorCode::Unauthorized);
        require!(new_fee <= 100, ErrorCode::InvalidFeeAmount);

        // 更新手续费
        let old_fee = asset.platform_fee;
        asset.platform_fee = new_fee;
        asset.updated_at = Clock::get()?.unix_timestamp;

        emit!(AssetFeeUpdated {
            asset: asset.key(),
            old_fee,
            new_fee,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }
}

/// 资产账户数据结构
#[account]
pub struct Asset {
    pub owner: Pubkey,           // 资产所有者
    pub token_mint: Pubkey,      // 代币铸造地址
    pub price: u64,              // 资产价格（USDC）
    pub total_supply: u64,       // 总供应量
    pub available_supply: u64,   // 可用供应量
    pub platform_fee: u8,        // 平台手续费比例（3.5% = 35，以千分比存储）
    pub created_at: i64,         // 创建时间
    pub updated_at: i64,         // 更新时间
    // 保留空间用于后续升级
    pub _reserved: [u8; 64],
}

/// 初始化资产账户
#[derive(Accounts)]
pub struct InitializeAsset<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,

    #[account(
        init, 
        payer = owner, 
        space = 8 + std::mem::size_of::<Asset>()
    )]
    pub asset: Account<'info, Asset>,

    pub system_program: Program<'info, System>,
}

/// 购买资产的账户
#[derive(Accounts)]
pub struct BuyAsset<'info> {
    #[account(mut)]
    pub buyer: Signer<'info>,
    
    #[account(mut)]
    pub asset: Account<'info, Asset>,
    
    #[account(mut)]
    pub buyer_token_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub seller_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub platform_fee_account: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

/// 更新资产信息的账户
#[derive(Accounts)]
pub struct UpdateAsset<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    
    #[account(mut)]
    pub asset: Account<'info, Asset>,
    
    pub system_program: Program<'info, System>,
}

/// 资产购买事件
#[event]
pub struct AssetPurchased {
    pub asset: Pubkey,
    pub buyer: Pubkey,
    pub amount: u64,
    pub total_amount: u64,
    pub platform_fee_amount: u64,
    pub seller_amount: u64,
    pub timestamp: i64,
}

/// 资产价格更新事件
#[event]
pub struct AssetPriceUpdated {
    pub asset: Pubkey,
    pub old_price: u64,
    pub new_price: u64,
    pub timestamp: i64,
}

/// 资产手续费更新事件
#[event]
pub struct AssetFeeUpdated {
    pub asset: Pubkey,
    pub old_fee: u8,
    pub new_fee: u8,
    pub timestamp: i64,
}

/// 错误码
#[error_code]
pub enum ErrorCode {
    #[msg("余额不足")]
    InsufficientBalance,
    #[msg("供应量不足")]
    InsufficientSupply,
    #[msg("未授权操作")]
    Unauthorized,
    #[msg("计算溢出")]
    Overflow,
    #[msg("无效的手续费金额")]
    InvalidFeeAmount,
} 