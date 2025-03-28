use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};
use solana_program::program::invoke;
use solana_program::system_instruction;

declare_id!("rwaHubDividendXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX");

#[program]
pub mod rwa_dividend {
    use super::*;

    /// 创建分红
    pub fn create_dividend(
        ctx: Context<CreateDividend>,
        total_amount: u64,
        deadline: i64,
        asset_token_mint: Pubkey,
        platform_fee: u8,
    ) -> Result<()> {
        let dividend = &mut ctx.accounts.dividend;
        let creator = &ctx.accounts.creator;
        let platform_fee_account = &ctx.accounts.platform_fee_account;
        let creator_token_account = &ctx.accounts.creator_token_account;
        let token_program = &ctx.accounts.token_program;

        // 验证平台手续费合理性
        require!(platform_fee <= 100, ErrorCode::InvalidFeeAmount);
        
        // 验证截止时间合理性
        require!(
            deadline > Clock::get()?.unix_timestamp,
            ErrorCode::InvalidDeadline
        );

        // 计算平台手续费金额
        let platform_fee_amount = total_amount
            .checked_mul(platform_fee as u64)
            .ok_or(ErrorCode::Overflow)?
            .checked_div(1000)
            .ok_or(ErrorCode::Overflow)?; // platform_fee 是千分比，例如35表示3.5%
        
        let dividend_amount = total_amount
            .checked_sub(platform_fee_amount)
            .ok_or(ErrorCode::Overflow)?;

        // 转账平台手续费
        token::transfer(
            CpiContext::new(
                token_program.to_account_info(),
                Transfer {
                    from: creator_token_account.to_account_info(),
                    to: platform_fee_account.to_account_info(),
                    authority: creator.to_account_info(),
                },
            ),
            platform_fee_amount,
        )?;

        // 初始化分红信息
        dividend.creator = creator.key();
        dividend.asset_token_mint = asset_token_mint;
        dividend.total_amount = dividend_amount;
        dividend.remaining_amount = dividend_amount;
        dividend.total_holders = 0; // 实际持有人数量需要另外查询和设置
        dividend.claimed_count = 0;
        dividend.platform_fee = platform_fee;
        dividend.created_at = Clock::get()?.unix_timestamp;
        dividend.deadline = deadline;
        dividend.is_active = true;
        
        // 记录转账到分红合约的金额，用于后续分配
        // 这里假设用户已经先将USDC转账到创建的分红合约中
        
        emit!(DividendCreated {
            dividend: dividend.key(),
            creator: creator.key(),
            asset_token_mint,
            total_amount,
            dividend_amount,
            platform_fee_amount,
            deadline,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }
    
    /// 设置总持有人数和分红金额
    pub fn set_holders_info(
        ctx: Context<UpdateDividend>,
        total_holders: u32,
        excluded_amount: u64,
    ) -> Result<()> {
        let dividend = &mut ctx.accounts.dividend;
        let admin = &ctx.accounts.admin;
        
        // 验证管理员权限
        // 实际应该检查是否为平台管理员
        
        // 更新持有人信息
        dividend.total_holders = total_holders;
        
        // 更新可分配的金额（排除发行者持有的未售出代币对应金额）
        if excluded_amount > 0 && excluded_amount < dividend.total_amount {
            dividend.distributable_amount = dividend.total_amount - excluded_amount;
        } else {
            dividend.distributable_amount = dividend.total_amount;
        }
        
        emit!(HoldersInfoUpdated {
            dividend: dividend.key(),
            total_holders,
            excluded_amount,
            distributable_amount: dividend.distributable_amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }

    /// 领取分红
    pub fn claim_dividend(ctx: Context<ClaimDividend>, amount: u64) -> Result<()> {
        let dividend = &mut ctx.accounts.dividend;
        let holder = &ctx.accounts.holder;
        let holder_token_account = &ctx.accounts.holder_token_account;
        let dividend_token_account = &ctx.accounts.dividend_token_account;
        let token_program = &ctx.accounts.token_program;

        // 验证分红是否激活
        require!(dividend.is_active, ErrorCode::DividendNotActive);
        
        // 验证分红是否过期
        require!(
            Clock::get()?.unix_timestamp <= dividend.deadline,
            ErrorCode::DividendExpired
        );

        // 验证剩余分红金额
        require!(
            dividend.remaining_amount >= amount,
            ErrorCode::InsufficientDividendBalance
        );

        // 验证领取金额合理性
        // 这里需要一个复杂的验证逻辑，确保每个持有者只能领取其应得的分红
        // 实际项目中应该根据持有比例来计算
        
        // 转账分红金额到持有者账户
        token::transfer(
            CpiContext::new(
                token_program.to_account_info(),
                Transfer {
                    from: dividend_token_account.to_account_info(),
                    to: holder_token_account.to_account_info(),
                    authority: dividend.to_account_info(),
                },
            ),
            amount,
        )?;

        // 更新分红状态
        dividend.remaining_amount = dividend
            .remaining_amount
            .checked_sub(amount)
            .ok_or(ErrorCode::Overflow)?;
        dividend.claimed_count = dividend
            .claimed_count
            .checked_add(1)
            .ok_or(ErrorCode::Overflow)?;

        // 记录领取记录
        // 在实际项目中，应该创建一个单独的账户来记录每个持有者的领取情况

        emit!(DividendClaimed {
            dividend: dividend.key(),
            holder: holder.key(),
            amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }

    /// 关闭分红
    pub fn close_dividend(ctx: Context<CloseDividend>) -> Result<()> {
        let dividend = &mut ctx.accounts.dividend;
        let creator = &ctx.accounts.creator;

        // 验证权限
        require!(dividend.creator == creator.key(), ErrorCode::Unauthorized);

        // 关闭分红
        dividend.is_active = false;

        emit!(DividendClosed {
            dividend: dividend.key(),
            remaining_amount: dividend.remaining_amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }
}

/// 分红账户数据结构
#[account]
pub struct Dividend {
    pub creator: Pubkey,         // 分红创建者
    pub asset_token_mint: Pubkey, // 资产代币铸造地址
    pub total_amount: u64,       // 总分红金额（已扣除平台手续费）
    pub distributable_amount: u64, // 可分配金额（排除未售出代币）
    pub remaining_amount: u64,   // 剩余分红金额
    pub total_holders: u32,      // 总持有人数量
    pub claimed_count: u32,      // 已领取人数
    pub platform_fee: u8,        // 平台手续费比例（3.5% = 35）
    pub created_at: i64,         // 创建时间
    pub deadline: i64,           // 截止时间
    pub is_active: bool,         // 是否激活
    // 保留空间用于后续升级
    pub _reserved: [u8; 64],
}

/// 创建分红的账户
#[derive(Accounts)]
pub struct CreateDividend<'info> {
    #[account(mut)]
    pub creator: Signer<'info>,

    #[account(
        init, 
        payer = creator, 
        space = 8 + std::mem::size_of::<Dividend>()
    )]
    pub dividend: Account<'info, Dividend>,
    
    #[account(mut)]
    pub creator_token_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub platform_fee_account: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

/// 更新分红信息的账户
#[derive(Accounts)]
pub struct UpdateDividend<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    
    #[account(mut)]
    pub dividend: Account<'info, Dividend>,
    
    pub system_program: Program<'info, System>,
}

/// 领取分红的账户
#[derive(Accounts)]
pub struct ClaimDividend<'info> {
    #[account(mut)]
    pub holder: Signer<'info>,
    
    #[account(mut)]
    pub dividend: Account<'info, Dividend>,
    
    #[account(mut)]
    pub holder_token_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub dividend_token_account: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

/// 关闭分红的账户
#[derive(Accounts)]
pub struct CloseDividend<'info> {
    #[account(mut)]
    pub creator: Signer<'info>,
    
    #[account(mut)]
    pub dividend: Account<'info, Dividend>,
    
    pub system_program: Program<'info, System>,
}

/// 分红创建事件
#[event]
pub struct DividendCreated {
    pub dividend: Pubkey,
    pub creator: Pubkey,
    pub asset_token_mint: Pubkey,
    pub total_amount: u64,
    pub dividend_amount: u64,
    pub platform_fee_amount: u64,
    pub deadline: i64,
    pub timestamp: i64,
}

/// 持有人信息更新事件
#[event]
pub struct HoldersInfoUpdated {
    pub dividend: Pubkey,
    pub total_holders: u32,
    pub excluded_amount: u64,
    pub distributable_amount: u64,
    pub timestamp: i64,
}

/// 分红领取事件
#[event]
pub struct DividendClaimed {
    pub dividend: Pubkey,
    pub holder: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

/// 分红关闭事件
#[event]
pub struct DividendClosed {
    pub dividend: Pubkey,
    pub remaining_amount: u64,
    pub timestamp: i64,
}

/// 错误码
#[error_code]
pub enum ErrorCode {
    #[msg("余额不足")]
    InsufficientBalance,
    #[msg("分红余额不足")]
    InsufficientDividendBalance,
    #[msg("未授权操作")]
    Unauthorized,
    #[msg("计算溢出")]
    Overflow,
    #[msg("无效的手续费金额")]
    InvalidFeeAmount,
    #[msg("无效的截止时间")]
    InvalidDeadline,
    #[msg("分红已过期")]
    DividendExpired,
    #[msg("分红未激活")]
    DividendNotActive,
    #[msg("已超过最大领取金额")]
    ExceedMaxClaimAmount,
} 