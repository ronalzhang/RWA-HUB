use borsh::{BorshDeserialize, BorshSerialize};
use solana_program::{
    program_pack::{IsInitialized, Pack, Sealed},
    pubkey::Pubkey,
};

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
}

impl Sealed for Asset {}

impl IsInitialized for Asset {
    fn is_initialized(&self) -> bool {
        self.is_initialized
    }
}

impl Pack for Asset {
    const LEN: usize = 165; // 计算所有字段的总长度

    fn pack_into_slice(&self, dst: &mut [u8]) {
        let data = self.try_to_vec().unwrap();
        dst[..data.len()].copy_from_slice(&data);
    }

    fn unpack_from_slice(src: &[u8]) -> Result<Self, solana_program::program_error::ProgramError> {
        let asset = Self::try_from_slice(src)?;
        Ok(asset)
    }
}

#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct DividendPool {
    pub is_initialized: bool,
    pub asset: Pubkey,
    pub total_amount: u64,
    pub last_distribution: i64,
}

impl Sealed for DividendPool {}

impl IsInitialized for DividendPool {
    fn is_initialized(&self) -> bool {
        self.is_initialized
    }
}

impl Pack for DividendPool {
    const LEN: usize = 50; // 计算所有字段的总长度

    fn pack_into_slice(&self, dst: &mut [u8]) {
        let data = self.try_to_vec().unwrap();
        dst[..data.len()].copy_from_slice(&data);
    }

    fn unpack_from_slice(src: &[u8]) -> Result<Self, solana_program::program_error::ProgramError> {
        let pool = Self::try_from_slice(src)?;
        Ok(pool)
    }
} 