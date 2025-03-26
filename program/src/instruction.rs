use borsh::{BorshDeserialize, BorshSerialize};
use solana_program::program_error::ProgramError;
use anchor_lang::prelude::*;
use anchor_spl::token::{Token, TokenAccount};

#[derive(BorshSerialize, BorshDeserialize, Debug, Clone)]
pub enum RwaHubInstruction {
    /// 初始化资产
    /// 
    /// Accounts expected:
    /// 0. `[signer]` 创建者
    /// 1. `[writable]` 资产账户
    /// 2. `[writable]` 代币铸造账户
    /// 3. `[]` 系统程序
    /// 4. `[]` 代币程序
    InitializeAsset {
        name: String,
        symbol: String,
        total_supply: u64,
        decimals: u8,
    },

    /// 购买资产代币
    /// 
    /// Accounts expected:
    /// 0. `[signer]` 买家
    /// 1. `[writable]` 买家代币账户
    /// 2. `[writable]` 卖家代币账户
    /// 3. `[writable]` 买家USDC账户
    /// 4. `[writable]` 卖家USDC账户
    /// 5. `[]` 代币程序
    Buy {
        amount: u64,
    },

    /// 分红
    /// 
    /// Accounts expected:
    /// 0. `[signer]` 资产所有者
    /// 1. `[writable]` 分红池账户
    /// 2. `[writable]` 所有者USDC账户
    /// 3. `[]` 代币程序
    Dividend {
        amount: u64,
    },
}

impl RwaHubInstruction {
    /// 解包指令数据
    pub fn unpack(input: &[u8]) -> Result<Self, ProgramError> {
        let (&tag, rest) = input.split_first().ok_or(ProgramError::InvalidInstructionData)?;
        Ok(match tag {
            0 => {
                let payload = Self::try_from_slice(rest)?;
                payload
            }
            _ => return Err(ProgramError::InvalidInstructionData),
        })
    }
}

#[derive(Accounts)]
pub struct CreateDividend<'info> {
    #[account(mut)]
    pub distributor: Signer<'info>,
    
    #[account(mut)]
    pub distributor_usdc_account: Account<'info, TokenAccount>,
    
    #[account(
        init,
        payer = distributor,
        space = 8 + DividendPool::LEN,
        seeds = [b"dividend_pool", asset_mint.key().as_ref()],
        bump
    )]
    pub dividend_pool: Account<'info, DividendPool>,
    
    #[account(mut)]
    pub platform_fee_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub asset: Account<'info, Asset>,
    
    pub asset_mint: Account<'info, Mint>,
    
    /// CHECK: 用于记录交易哈希
    pub transaction: UncheckedAccount<'info>,
    
    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct ClaimDividend<'info> {
    #[account(mut)]
    pub holder: Signer<'info>,
    
    #[account(mut)]
    pub holder_usdc_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub dividend_pool: Account<'info, DividendPool>,
    
    #[account(
        init_if_needed,
        payer = holder,
        space = 8 + DividendRecord::LEN,
        seeds = [b"dividend_record", dividend_pool.key().as_ref(), holder.key().as_ref()],
        bump
    )]
    pub dividend_record: Account<'info, DividendRecord>,
    
    /// CHECK: 用于记录交易哈希
    pub transaction: UncheckedAccount<'info>,
    
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct GetDividendInfo<'info> {
    pub dividend_pool: Account<'info, DividendPool>,
    pub dividend_record: Account<'info, DividendRecord>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct DividendDetails {
    pub amount: u64,
    pub platform_fee: u64,
    pub dividend_per_token: u64,
    pub holders: Vec<HolderInfo>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct HolderInfo {
    pub address: Pubkey,
    pub amount: u64,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct DividendInfo {
    pub total_amount: u64,
    pub token_price: u64,
    pub dividend_per_token: u64,
    pub claimed: bool,
    pub last_claim_time: i64,
    pub next_distribution: i64,
    pub details: DividendDetails,
}

#[derive(Accounts)]
pub struct TokenHolder {
    pub address: Pubkey,
    pub balance: u64,
} 