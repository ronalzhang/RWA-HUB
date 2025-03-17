use borsh::{BorshDeserialize, BorshSerialize};
use solana_program::program_error::ProgramError;

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