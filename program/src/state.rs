use borsh::{BorshDeserialize, BorshSerialize};
use solana_program::{
    program_pack::{IsInitialized, Pack, Sealed},
    pubkey::Pubkey,
};
use anchor_lang::prelude::*;
use anchor_spl::token::Mint;

#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct Asset {
    pub is_initialized: bool,
    pub owner: Pubkey,
    pub name: String,
    pub symbol: String,
    pub total_supply: u64,
    pub decimals: u8,
    pub mint: Pubkey,
    pub price: u64,        // USDC价格，6位小数
    pub remaining_supply: u64,
    pub vault_bump: u8,    // PDA金库的bump种子
}

impl Sealed for Asset {}

impl IsInitialized for Asset {
    fn is_initialized(&self) -> bool {
        self.is_initialized
    }
}

impl Pack for Asset {
    const LEN: usize = 166; // 原165 + 1(vault_bump)

    fn pack_into_slice(&self, dst: &mut [u8]) {
        let data = self.try_to_vec().unwrap();
        dst[..data.len()].copy_from_slice(&data);
    }

    fn unpack_from_slice(src: &[u8]) -> Result<Self, solana_program::program_error::ProgramError> {
        let asset = Self::try_from_slice(src)?;
        Ok(asset)
    }
}

#[account]
pub struct DividendPool {
    pub asset_mint: Pubkey,
    pub total_amount: u64,
    pub token_price: u64,
    pub distributor: Pubkey,
    pub holders_count: u32,
    pub last_distribution: i64,
    pub distribution_interval: i64,
    pub transaction_hash: [u8; 32],
    pub details: Vec<u8>,
}

impl DividendPool {
    pub const LEN: usize = 32 + // asset_mint
        8 + // total_amount
        8 + // token_price
        32 + // distributor
        4 + // holders_count
        8 + // last_distribution
        8 + // distribution_interval
        32 + // transaction_hash
        4 + // details length
        1000; // details (max size)
}

#[account]
pub struct DividendRecord {
    pub holder: Pubkey,
    pub amount: u64,
    pub claimed: bool,
    pub last_claim_time: i64,
    pub transaction_hash: [u8; 32],
}

impl DividendRecord {
    pub const LEN: usize = 32 + // holder
        8 + // amount
        1 + // claimed
        8 + // last_claim_time
        32; // transaction_hash
} 