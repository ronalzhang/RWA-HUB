import { CONTRACT_CONFIG } from '../config/api.js';

// 初始化Solana连接
export function initializeSolanaConnection() {
    try {
        return new window.solanaWeb3.Connection(
            CONTRACT_CONFIG.NETWORK.SOLANA_ENDPOINT,
            'confirmed'
        );
    } catch (error) {
        console.error('初始化Solana连接失败:', error);
        throw error;
    }
}

// 获取USDC代币账户
export async function getUSDCAccount(walletAddress) {
    try {
        const publicKey = new window.solanaWeb3.PublicKey(walletAddress);
        const tokenMint = new window.solanaWeb3.PublicKey(CONTRACT_CONFIG.USDC_CONTRACT_ADDRESS);
        
        const tokenAccount = await window.splToken.getAssociatedTokenAddress(
            tokenMint,
            publicKey
        );
        
        return tokenAccount;
    } catch (error) {
        console.error('获取USDC账户失败:', error);
        throw error;
    }
}

// 创建USDC代币账户
export async function createUSDCAccount(walletAddress) {
    try {
        const connection = initializeSolanaConnection();
        const publicKey = new window.solanaWeb3.PublicKey(walletAddress);
        const tokenMint = new window.solanaWeb3.PublicKey(CONTRACT_CONFIG.USDC_CONTRACT_ADDRESS);
        
        const transaction = new window.solanaWeb3.Transaction();
        
        // 创建关联代币账户的指令
        const createAccountInstruction = await window.splToken.createAssociatedTokenAccountInstruction(
            publicKey,
            tokenMint,
            publicKey
        );
        
        transaction.add(createAccountInstruction);
        
        // 获取最新的区块哈希
        const { blockhash } = await connection.getRecentBlockhash();
        transaction.recentBlockhash = blockhash;
        transaction.feePayer = publicKey;
        
        // 发送交易
        const signed = await window.solana.signTransaction(transaction);
        const signature = await connection.sendRawTransaction(signed.serialize());
        
        // 等待确认
        await connection.confirmTransaction(signature);
        
        return await getUSDCAccount(walletAddress);
    } catch (error) {
        console.error('创建USDC账户失败:', error);
        throw error;
    }
}

// 检查USDC余额
export async function checkSolanaUSDCBalance(walletAddress) {
    try {
        const connection = initializeSolanaConnection();
        const tokenAccount = await getUSDCAccount(walletAddress);
        
        const balance = await connection.getTokenAccountBalance(tokenAccount);
        return parseFloat(balance.value.uiAmount);
    } catch (error) {
        console.error('检查USDC余额失败:', error);
        throw error;
    }
}

// 计算平台费用
export function calculatePlatformFee(amount) {
    return amount * (CONTRACT_CONFIG.FEES.PLATFORM_FEE_PERCENT / 100);
}

// 转账USDC (修改后的版本，包含费用分配)
export async function transferUSDC(fromAddress, toAddress, amount) {
    try {
        const connection = initializeSolanaConnection();
        const fromPublicKey = new window.solanaWeb3.PublicKey(fromAddress);
        
        // 计算费用分配
        const platformFee = calculatePlatformFee(amount);
        const sellerAmount = amount - platformFee;
        
        // 创建交易
        const transaction = new window.solanaWeb3.Transaction();
        
        // 1. 转账平台费用
        const platformTransfer = await createTransferInstruction(
            fromAddress,
            CONTRACT_CONFIG.PLATFORM_WALLET,
            platformFee
        );
        transaction.add(platformTransfer);
        
        // 2. 转账给卖家
        const sellerTransfer = await createTransferInstruction(
            fromAddress,
            toAddress,
            sellerAmount
        );
        transaction.add(sellerTransfer);
        
        // 获取最新的区块哈希
        const { blockhash } = await connection.getRecentBlockhash();
        transaction.recentBlockhash = blockhash;
        transaction.feePayer = fromPublicKey;
        
        // 发送交易
        const signed = await window.solana.signTransaction(transaction);
        const signature = await connection.sendRawTransaction(signed.serialize());
        
        // 等待确认
        await connection.confirmTransaction(signature);
        
        return {
            signature,
            platformFee,
            sellerAmount
        };
    } catch (error) {
        console.error('USDC转账失败:', error);
        throw error;
    }
}

// 创建转账指令
async function createTransferInstruction(fromAddress, toAddress, amount) {
    const fromTokenAccount = await getUSDCAccount(fromAddress);
    const toTokenAccount = await getUSDCAccount(toAddress);
    const fromPublicKey = new window.solanaWeb3.PublicKey(fromAddress);
    
    return window.splToken.createTransferInstruction(
        fromTokenAccount,
        toTokenAccount,
        fromPublicKey,
        amount * Math.pow(10, 6) // USDC有6位小数
    );
}

// 监听交易状态
export function watchSolanaTransactionStatus(signature) {
    return new Promise((resolve, reject) => {
        const connection = initializeSolanaConnection();
        const checkStatus = async () => {
            try {
                const status = await connection.getSignatureStatus(signature);
                if (status.value !== null) {
                    if (status.value.err === null) {
                        resolve(status);
                    } else {
                        reject(new Error('交易失败'));
                    }
                } else {
                    setTimeout(checkStatus, 2000);
                }
            } catch (error) {
                reject(error);
            }
        };
        checkStatus();
    });
}

// 获取交易记录
export async function getSolanaTransactionHistory(walletAddress) {
    try {
        const connection = initializeSolanaConnection();
        const publicKey = new window.solanaWeb3.PublicKey(walletAddress);
        
        // 获取最近的交易签名
        const signatures = await connection.getSignaturesForAddress(publicKey, {
            limit: 10
        });
        
        // 获取交易详情
        const transactions = await Promise.all(
            signatures.map(async (sig) => {
                const tx = await connection.getTransaction(sig.signature);
                return {
                    signature: sig.signature,
                    timestamp: sig.blockTime,
                    ...tx
                };
            })
        );
        
        return transactions;
    } catch (error) {
        console.error('获取交易历史失败:', error);
        throw error;
    }
} 