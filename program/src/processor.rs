use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    msg,
    program::{invoke, invoke_signed},
    program_error::ProgramError,
    program_pack::{IsInitialized, Pack},
    pubkey::Pubkey,
    sysvar::{rent::Rent, Sysvar},
    clock::Clock,
};
use spl_token::{
    instruction as token_instruction,
    state::{Account as TokenAccount, Mint},
};

use crate::{
    error::RwaHubError,
    instruction::RwaHubInstruction,
    state::{Asset, DividendPool},
};

pub fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction: RwaHubInstruction,
) -> ProgramResult {
    match instruction {
        RwaHubInstruction::InitializeAsset {
            name,
            symbol,
            total_supply,
            decimals,
        } => {
            process_initialize_asset(program_id, accounts, name, symbol, total_supply, decimals)
        }
        RwaHubInstruction::Buy { amount } => process_buy(program_id, accounts, amount),
        RwaHubInstruction::Dividend { amount } => process_dividend(program_id, accounts, amount),
    }
}

fn process_initialize_asset(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    name: String,
    symbol: String,
    total_supply: u64,
    decimals: u8,
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();

    let creator_info = next_account_info(account_info_iter)?;
    let asset_info = next_account_info(account_info_iter)?;
    let mint_info = next_account_info(account_info_iter)?;
    let system_program_info = next_account_info(account_info_iter)?;
    let token_program_info = next_account_info(account_info_iter)?;

    // 验证是否有签名
    if !creator_info.is_signer {
        return Err(RwaHubError::Unauthorized.into());
    }

    // 检查资产账户是否已初始化
    if asset_info.owner != program_id {
        // 创建资产账户
        let rent = Rent::get()?;
        let rent_lamports = rent.minimum_balance(Asset::LEN);

        invoke(
            &solana_program::system_instruction::create_account(
                creator_info.key,
                asset_info.key,
                rent_lamports,
                Asset::LEN as u64,
                program_id,
            ),
            &[creator_info.clone(), asset_info.clone()],
        )?;
    }

    // 检查铸币账户是否已初始化
    if *mint_info.owner != spl_token::id() {
        // 创建铸币账户
        let rent = Rent::get()?;
        let rent_lamports = rent.minimum_balance(Mint::LEN);

        invoke(
            &solana_program::system_instruction::create_account(
                creator_info.key,
                mint_info.key,
                rent_lamports,
                Mint::LEN as u64,
                &spl_token::id(),
            ),
            &[creator_info.clone(), mint_info.clone()],
        )?;

        // 初始化铸币账户
        invoke(
            &token_instruction::initialize_mint(
                &spl_token::id(),
                mint_info.key,
                creator_info.key,
                Some(creator_info.key),
                decimals,
            )?,
            &[mint_info.clone(), creator_info.clone()],
        )?;
    }

    // 创建资产
    let mut asset = Asset::unpack_unchecked(&asset_info.data.borrow())?;
    if asset.is_initialized() {
        return Err(RwaHubError::AssetAlreadyExists.into());
    }

    asset.is_initialized = true;
    asset.owner = *creator_info.key;
    asset.name = name;
    asset.symbol = symbol;
    asset.total_supply = total_supply;
    asset.decimals = decimals;
    asset.mint = *mint_info.key;
    asset.remaining_supply = total_supply;

    Asset::pack(asset, &mut asset_info.data.borrow_mut())?;

    msg!("Asset initialized: {}", symbol);
    Ok(())
}

fn process_buy(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();

    let buyer_info = next_account_info(account_info_iter)?;
    let buyer_token_account_info = next_account_info(account_info_iter)?;
    let seller_token_account_info = next_account_info(account_info_iter)?;
    let buyer_usdc_account_info = next_account_info(account_info_iter)?;
    let seller_usdc_account_info = next_account_info(account_info_iter)?;
    let token_program_info = next_account_info(account_info_iter)?;
    let asset_info = next_account_info(account_info_iter)?;

    // 验证是否有签名
    if !buyer_info.is_signer {
        return Err(RwaHubError::Unauthorized.into());
    }

    // 获取资产信息
    let mut asset = Asset::unpack(&asset_info.data.borrow())?;
    if !asset.is_initialized() {
        return Err(RwaHubError::AssetNotFound.into());
    }

    // 检查余量是否足够
    if asset.remaining_supply < amount {
        return Err(RwaHubError::InsufficientFunds.into());
    }

    // 计算总价
    let total_price = amount.checked_mul(asset.price)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    // 转移 USDC
    invoke(
        &token_instruction::transfer(
            &spl_token::id(),
            buyer_usdc_account_info.key,
            seller_usdc_account_info.key,
            buyer_info.key,
            &[],
            total_price,
        )?,
        &[
            buyer_usdc_account_info.clone(),
            seller_usdc_account_info.clone(),
            buyer_info.clone(),
            token_program_info.clone(),
        ],
    )?;

    // 转移代币
    invoke(
        &token_instruction::transfer(
            &spl_token::id(),
            seller_token_account_info.key,
            buyer_token_account_info.key,
            &asset.owner,
            &[],
            amount,
        )?,
        &[
            seller_token_account_info.clone(),
            buyer_token_account_info.clone(),
            buyer_info.clone(),
            token_program_info.clone(),
        ],
    )?;

    // 更新资产余量
    asset.remaining_supply = asset.remaining_supply.checked_sub(amount)
        .ok_or(ProgramError::ArithmeticOverflow)?;
    Asset::pack(asset, &mut asset_info.data.borrow_mut())?;

    msg!("Purchased {} tokens", amount);
    Ok(())
}

fn process_dividend(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();

    let owner_info = next_account_info(account_info_iter)?;
    let dividend_pool_info = next_account_info(account_info_iter)?;
    let owner_usdc_account_info = next_account_info(account_info_iter)?;
    let token_program_info = next_account_info(account_info_iter)?;
    let asset_info = next_account_info(account_info_iter)?;

    // 验证是否有签名
    if !owner_info.is_signer {
        return Err(RwaHubError::Unauthorized.into());
    }

    // 获取资产信息
    let asset = Asset::unpack(&asset_info.data.borrow())?;
    if !asset.is_initialized() {
        return Err(RwaHubError::AssetNotFound.into());
    }

    // 验证所有者
    if asset.owner != *owner_info.key {
        return Err(RwaHubError::Unauthorized.into());
    }

    // 获取分红池信息
    let mut dividend_pool = if dividend_pool_info.owner == program_id {
        DividendPool::unpack(&dividend_pool_info.data.borrow())?
    } else {
        // 创建分红池账户
        let rent = Rent::get()?;
        let rent_lamports = rent.minimum_balance(DividendPool::LEN);

        invoke(
            &solana_program::system_instruction::create_account(
                owner_info.key,
                dividend_pool_info.key,
                rent_lamports,
                DividendPool::LEN as u64,
                program_id,
            ),
            &[owner_info.clone(), dividend_pool_info.clone()],
        )?;

        let mut dividend_pool = DividendPool {
            is_initialized: true,
            asset: *asset_info.key,
            total_amount: 0,
            last_distribution: 0,
        };

        DividendPool::pack(dividend_pool, &mut dividend_pool_info.data.borrow_mut())?;
        dividend_pool
    };

    // 检查分红金额
    if amount == 0 {
        return Err(RwaHubError::InvalidDividendAmount.into());
    }

    // 获取时间戳
    let clock = Clock::get()?;
    let current_time = clock.unix_timestamp;

    // 更新分红池
    dividend_pool.total_amount = dividend_pool.total_amount.checked_add(amount)
        .ok_or(ProgramError::ArithmeticOverflow)?;
    dividend_pool.last_distribution = current_time;

    // 保存分红池信息
    DividendPool::pack(dividend_pool, &mut dividend_pool_info.data.borrow_mut())?;

    msg!("Dividend of {} USDC added to pool", amount);
    Ok(())
} 