use solana_program::program_error::ProgramError;
use thiserror::Error;

#[derive(Error, Debug, Copy, Clone)]
pub enum RwaHubError {
    #[error("无效的指令")]
    InvalidInstruction,

    #[error("无效的资产状态")]
    InvalidAssetState,

    #[error("余额不足")]
    InsufficientFunds,

    #[error("无权操作")]
    Unauthorized,

    #[error("资产已存在")]
    AssetAlreadyExists,

    #[error("资产不存在")]
    AssetNotFound,

    #[error("分红金额无效")]
    InvalidDividendAmount,
}

impl From<RwaHubError> for ProgramError {
    fn from(e: RwaHubError) -> Self {
        ProgramError::Custom(e as u32)
    }
} 