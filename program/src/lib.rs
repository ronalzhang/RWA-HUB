use solana_program::{
    account_info::AccountInfo,
    entrypoint,
    entrypoint::ProgramResult,
    msg,
    pubkey::Pubkey,
};

mod error;
mod instruction;
mod processor;
mod state;

use instruction::RwaHubInstruction;

entrypoint!(process_instruction);

pub fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    msg!("RWA-HUB: Processing instruction");
    
    let instruction = RwaHubInstruction::unpack(instruction_data)?;
    processor::process_instruction(program_id, accounts, instruction)
} 