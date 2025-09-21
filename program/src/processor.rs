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
            price,
        } => {
            process_initialize_asset(program_id, accounts, name, symbol, total_supply, decimals, price)
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
    price: u64,
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();

    let creator_info = next_account_info(account_info_iter)?;
    let asset_info = next_account_info(account_info_iter)?;
    let mint_info = next_account_info(account_info_iter)?;
    let system_program_info = next_account_info(account_info_iter)?;
    let token_program_info = next_account_info(account_info_iter)?;
    let associated_token_program_info = next_account_info(account_info_iter)?;
    let rent_sysvar_info = next_account_info(account_info_iter)?;

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

    // 派生资产金库PDA
    let (asset_vault_pda_key, vault_bump) = Pubkey::find_program_address(
        &[b"asset_vault", mint_info.key.as_ref()],
        program_id
    );

    // 创建资产金库的代币账户（ATA）
    invoke(
        &spl_associated_token_account::instruction::create_associated_token_account(
            creator_info.key,
            &asset_vault_pda_key,
            mint_info.key,
            token_program_info.key,
        ),
        &[
            creator_info.clone(),
            asset_info.clone(),
            creator_info.clone(),
            mint_info.clone(),
            system_program_info.clone(),
            token_program_info.clone(),
            rent_sysvar_info.clone(),
            associated_token_program_info.clone(),
        ],
    )?;

    // 铸造代币到资产金库的ATA
    invoke(
        &token_instruction::mint_to(
            &spl_token::id(),
            mint_info.key,
            asset_info.key,
            creator_info.key,
            &[],
            total_supply,
        )?,
        &[
            mint_info.clone(),
            asset_info.clone(),
            creator_info.clone(),
            token_program_info.clone(),
        ],
    )?;

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
    asset.price = price;
    asset.vault_bump = vault_bump;

    Asset::pack(asset, &mut asset_info.data.borrow_mut())?;

    msg!("Asset initialized with PDA vault: {}", symbol);
    Ok(())
}

fn process_buy(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    amount: u64,
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();

    // 解析账户
    let buyer_main_wallet_info = next_account_info(account_info_iter)?;
    let buyer_asset_ata_info = next_account_info(account_info_iter)?;
    let asset_vault_ata_info = next_account_info(account_info_iter)?;
    let buyer_usdc_ata_info = next_account_info(account_info_iter)?;
    let asset_account_info = next_account_info(account_info_iter)?;
    let platform_main_wallet_info = next_account_info(account_info_iter)?;
    let usdc_mint_info = next_account_info(account_info_iter)?;
    let token_program_info = next_account_info(account_info_iter)?;
    let associated_token_program_info = next_account_info(account_info_iter)?;
    let system_program_info = next_account_info(account_info_iter)?;
    let rent_sysvar_info = next_account_info(account_info_iter)?;

    // 验证买家签名
    if !buyer_main_wallet_info.is_signer {
        return Err(RwaHubError::Unauthorized.into());
    }

    // 获取并验证资产数据
    let mut asset_data = Asset::unpack(&asset_account_info.data.borrow())?;
    if !asset_data.is_initialized() {
        return Err(RwaHubError::AssetNotFound.into());
    }

    // 检查剩余供应量是否足够
    if asset_data.remaining_supply < amount {
        return Err(RwaHubError::InsufficientFunds.into());
    }

    // 计算付款金额
    let total_price = amount.checked_mul(asset_data.price)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    // 计算平台手续费(3.5%)和资产发起人收款(96.5%)
    let platform_fee = total_price.checked_mul(35)
        .ok_or(ProgramError::ArithmeticOverflow)?
        .checked_div(1000)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    let creator_amount = total_price.checked_sub(platform_fee)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    // 1. 处理平台手续费支付
    
    // 派生平台的USDC ATA
    let platform_usdc_ata = spl_associated_token_account::get_associated_token_address(
        platform_main_wallet_info.key,
        usdc_mint_info.key
    );
    
    // 转USDC给平台(3.5%手续费)
    // 前端在调用之前应该确保平台ATA已经存在
    invoke(
        &token_instruction::transfer(
            token_program_info.key,
            buyer_usdc_ata_info.key,
            &platform_usdc_ata,
            buyer_main_wallet_info.key,
            &[],
            platform_fee,
        )?,
        &[
            buyer_usdc_ata_info.clone(),
            buyer_main_wallet_info.clone(),
            token_program_info.clone(),
        ],
    )?;

    // 2. 处理资产发起人收款
    
    // 派生资产发起人的USDC ATA
    let creator_usdc_ata = spl_associated_token_account::get_associated_token_address(
        &asset_data.owner,
        usdc_mint_info.key
    );
    
    // 转USDC给资产发起人(96.5%)
    // 前端在调用之前应该确保发起人ATA已经存在
    invoke(
        &token_instruction::transfer(
            token_program_info.key,
            buyer_usdc_ata_info.key,
            &creator_usdc_ata,
            buyer_main_wallet_info.key,
            &[],
            creator_amount,
        )?,
        &[
            buyer_usdc_ata_info.clone(),
            buyer_main_wallet_info.clone(),
            token_program_info.clone(),
        ],
    )?;

    // 3. 处理资产代币转移
    
    // 前端在调用之前应该确保买家ATA已经存在
    
    // 派生资产金库PDA用于签名
    let vault_seeds = &[
        b"asset_vault", 
        asset_data.mint.as_ref(),
        &[asset_data.vault_bump]
    ];
    
    // 派生资产金库PDA密钥
    let asset_vault_pda_key = 
        Pubkey::create_program_address(vault_seeds, program_id)?;
    
    // 从金库ATA转移资产代币到买家ATA (使用PDA签名)
    invoke_signed(
        &token_instruction::transfer(
            token_program_info.key,
            asset_vault_ata_info.key,
            buyer_asset_ata_info.key,
            &asset_vault_pda_key,
            &[],
            amount,
        )?,
        &[
            asset_vault_ata_info.clone(),
            buyer_asset_ata_info.clone(),
            token_program_info.clone(),
        ],
        &[vault_seeds],
    )?;

    // 4. 更新资产状态中的剩余供应量
    asset_data.remaining_supply = asset_data.remaining_supply.checked_sub(amount)
        .ok_or(ProgramError::ArithmeticOverflow)?;
    Asset::pack(asset_data, &mut asset_account_info.data.borrow_mut())?;

    msg!("Asset purchase successful: {} tokens, total price {} USDC", amount, total_price);
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