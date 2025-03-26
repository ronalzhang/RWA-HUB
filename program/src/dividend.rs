use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Transfer, Mint};
use anchor_spl::associated_token::AssociatedToken;

declare_id!("9AcvoQmz22KRcMhkLkeSkKs8W7ru6oae8GHcxrS83fKz");

#[program]
pub mod dividend {
    use super::*;

    pub fn initialize_dividend_pool(
        ctx: Context<InitializeDividendPool>,
        bump: u8,
    ) -> Result<()> {
        let pool = &mut ctx.accounts.pool;
        pool.authority = ctx.accounts.authority.key();
        pool.bump = bump;
        pool.total_dividends = 0;
        pool.last_distribution = 0;
        Ok(())
    }

    pub fn create_asset(
        ctx: Context<CreateAsset>,
        name: String,
        symbol: String,
        total_supply: u64,
        price: u64,  // 价格(USDC)
        decimals: u8,
    ) -> Result<()> {
        let asset = &mut ctx.accounts.asset;
        asset.name = name;
        asset.symbol = symbol;
        asset.total_supply = total_supply;
        asset.price = price;
        asset.decimals = decimals;
        asset.owner = ctx.accounts.owner.key();
        asset.mint = ctx.accounts.mint.key();
        asset.created_at = Clock::get()?.unix_timestamp;
        Ok(())
    }

    pub fn buy_asset(
        ctx: Context<BuyAsset>,
        amount: u64,
    ) -> Result<()> {
        // 计算购买金额
        let asset = &ctx.accounts.asset;
        let buy_amount = amount.checked_mul(asset.price).unwrap();
        
        // 从买家USDC账户转账到平台账户
        let transfer_ctx = CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.buyer_usdc_account.to_account_info(),
                to: ctx.accounts.platform_usdc_account.to_account_info(),
                authority: ctx.accounts.buyer.to_account_info(),
                token_program: ctx.accounts.token_program.to_account_info(),
            },
        );
        token::transfer(transfer_ctx, buy_amount)?;

        // 铸造代币给买家
        let mint_ctx = CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            token::MintTo {
                mint: ctx.accounts.mint.to_account_info(),
                to: ctx.accounts.buyer_token_account.to_account_info(),
                authority: ctx.accounts.asset.to_account_info(),
                token_program: ctx.accounts.token_program.to_account_info(),
            },
        );
        token::mint_to(mint_ctx, amount)?;

        Ok(())
    }

    pub fn transfer_dividend_to_platform(
        ctx: Context<TransferDividendToPlatform>,
        amount: u64,
    ) -> Result<()> {
        // 从发起人账户转账到平台PDA
        let transfer_ctx = CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.distributor_token_account.to_account_info(),
                to: ctx.accounts.platform_token_account.to_account_info(),
                authority: ctx.accounts.distributor.to_account_info(),
                token_program: ctx.accounts.token_program.to_account_info(),
            },
        );

        token::transfer(transfer_ctx, amount)?;

        // 更新分红池状态
        let pool = &mut ctx.accounts.pool;
        pool.total_dividends = pool.total_dividends.checked_add(amount).unwrap();
        pool.last_distribution = Clock::get()?.unix_timestamp;

        Ok(())
    }

    pub fn process_withdrawal(
        ctx: Context<ProcessWithdrawal>,
        amount: u64,
    ) -> Result<()> {
        // 从平台PDA转账到用户账户
        let seeds = &[
            b"pool".as_ref(),
            &[ctx.accounts.pool.bump],
        ];
        let signer = &[&seeds[..]];

        let transfer_ctx = CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            Transfer {
                from: ctx.accounts.platform_token_account.to_account_info(),
                to: ctx.accounts.user_token_account.to_account_info(),
                authority: ctx.accounts.pool.to_account_info(),
                token_program: ctx.accounts.token_program.to_account_info(),
            },
            signer,
        );

        token::transfer(transfer_ctx, amount)?;

        Ok(())
    }
}

#[derive(Accounts)]
#[instruction(bump: u8)]
pub struct InitializeDividendPool<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + 32 + 1 + 8 + 8,
        seeds = [b"pool"],
        bump
    )]
    pub pool: Account<'info, DividendPool>,
    
    #[account(mut)]
    pub authority: Signer<'info>,
    
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct CreateAsset<'info> {
    #[account(
        init,
        payer = owner,
        space = 8 + 32 + 32 + 4 + 32 + 8 + 8 + 1 + 8,
    )]
    pub asset: Account<'info, Asset>,
    
    #[account(mut)]
    pub owner: Signer<'info>,
    
    #[account(
        init,
        payer = owner,
        mint::decimals = decimals,
        mint::authority = asset,
        space = 82,
    )]
    pub mint: Account<'info, Mint>,
    
    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct BuyAsset<'info> {
    #[account(mut)]
    pub asset: Account<'info, Asset>,
    
    #[account(mut)]
    pub buyer: Signer<'info>,
    
    #[account(mut)]
    pub mint: Account<'info, Mint>,
    
    #[account(mut)]
    pub buyer_token_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub buyer_usdc_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub platform_usdc_account: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct TransferDividendToPlatform<'info> {
    #[account(mut)]
    pub pool: Account<'info, DividendPool>,
    
    #[account(mut)]
    pub distributor: Signer<'info>,
    
    #[account(mut)]
    pub distributor_token_account: Account<'info, TokenAccount>,
    
    #[account(mut)]
    pub platform_token_account: Account<'info, TokenAccount>,
    
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct ProcessWithdrawal<'info> {
    #[account(mut)]
    pub pool: Account<'info, DividendPool>,
    
    #[account(mut)]
    pub user: Signer<'info>,
    
    #[account(mut)]
    pub platform_token_account: Account<'info, TokenAccount>,
    
    #[account(
        init_if_needed,
        payer = user,
        associated_token::mint = usdc_mint,
        associated_token::authority = user,
        associated_token::token_program = token_program,
        associated_token::system_program = system_program,
        associated_token::rent = rent,
    )]
    pub user_token_account: Account<'info, TokenAccount>,
    
    pub usdc_mint: Account<'info, token::Mint>,
    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

#[account]
pub struct DividendPool {
    pub authority: Pubkey,
    pub bump: u8,
    pub total_dividends: u64,
    pub last_distribution: i64,
}

#[account]
pub struct Asset {
    pub name: String,
    pub symbol: String,
    pub total_supply: u64,
    pub price: u64,  // 价格(USDC)
    pub decimals: u8,
    pub owner: Pubkey,
    pub mint: Pubkey,
    pub created_at: i64,
} 