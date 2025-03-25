// Web3环境检查
export function checkWeb3Environment() {
    if (!window.ethereum) {
        throw new Error('请安装MetaMask或其他Web3钱包');
    }
    if (!window.web3) {
        throw new Error('Web3环境未初始化');
    }
    return true;
}

// 获取钱包地址
export async function getWalletAddress() {
    try {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        return accounts[0];
    } catch (error) {
        console.error('获取钱包地址失败:', error);
        throw new Error('获取钱包地址失败，请确保钱包已连接');
    }
}

// 初始化Web3环境
export async function initializeWeb3() {
    try {
        if (typeof window.ethereum !== 'undefined') {
            window.web3 = new Web3(window.ethereum);
            await window.ethereum.enable();
            return true;
        } else if (typeof window.web3 !== 'undefined') {
            window.web3 = new Web3(window.web3.currentProvider);
            return true;
        } else {
            throw new Error('未检测到Web3环境');
        }
    } catch (error) {
        console.error('初始化Web3失败:', error);
        throw error;
    }
}

// 获取网络ID
export async function getNetworkId() {
    try {
        return await window.web3.eth.net.getId();
    } catch (error) {
        console.error('获取网络ID失败:', error);
        throw error;
    }
}

// 检查网络是否正确
export async function checkNetwork() {
    try {
        const networkId = await getNetworkId();
        const requiredNetwork = CONTRACT_CONFIG.NETWORK.REQUIRED_NETWORK_ID;
        if (networkId !== requiredNetwork) {
            throw new Error(`请切换到正确的网络`);
        }
        return true;
    } catch (error) {
        console.error('检查网络失败:', error);
        throw error;
    }
}

// 增强的USDC余额检查
export async function checkUSDCBalance(address, usdcContract) {
    try {
        const balance = await usdcContract.methods.balanceOf(address).call();
        const decimals = await usdcContract.methods.decimals().call();
        return parseFloat(balance) / Math.pow(10, decimals);
    } catch (error) {
        console.error('检查USDC余额失败:', error);
        throw new Error('检查USDC余额失败: ' + error.message);
    }
}

// 增强的USDC授权
export async function approveUSDC(usdcContract, spenderAddress, amount, fromAddress) {
    try {
        const decimals = await usdcContract.methods.decimals().call();
        const rawAmount = (amount * Math.pow(10, decimals)).toString();
        
        // 检查现有授权
        const currentAllowance = await usdcContract.methods.allowance(fromAddress, spenderAddress).call();
        if (parseInt(currentAllowance) >= parseInt(rawAmount)) {
            console.log('已有足够的授权额度');
            return true;
        }
        
        // 发起新的授权
        const result = await usdcContract.methods
            .approve(spenderAddress, rawAmount)
            .send({ from: fromAddress });
            
        return result;
    } catch (error) {
        console.error('USDC授权失败:', error);
        throw new Error('USDC授权失败: ' + error.message);
    }
}

// 增强的交易执行
export async function executeTrade(tradeContract, tradeId, fromAddress) {
    try {
        // 估算gas
        const gasEstimate = await tradeContract.methods
            .executeTrade(tradeId)
            .estimateGas({ from: fromAddress });
            
        // 获取当前gas价格
        const gasPrice = await window.web3.eth.getGasPrice();
        
        // 执行交易
        const result = await tradeContract.methods
            .executeTrade(tradeId)
            .send({ 
                from: fromAddress,
                gas: Math.floor(gasEstimate * 1.2), // 增加20%的gas限制
                gasPrice: gasPrice
            });
            
        return result;
    } catch (error) {
        console.error('交易执行失败:', error);
        throw new Error('交易执行失败: ' + error.message);
    }
}

// 监听交易状态
export function watchTransactionStatus(txHash) {
    return new Promise((resolve, reject) => {
        const checkStatus = async () => {
            try {
                const receipt = await window.web3.eth.getTransactionReceipt(txHash);
                if (receipt) {
                    if (receipt.status) {
                        resolve(receipt);
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

// 更新交易状态
export async function updateTradeStatus(tradeId, status, txHash, walletAddress) {
    try {
        const response = await fetch(`/api/trades/${tradeId}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Eth-Address': walletAddress
            },
            body: JSON.stringify({
                status,
                tx_hash: txHash,
                wallet_address: walletAddress
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || '更新交易状态失败');
        }

        return await response.json();
    } catch (error) {
        console.error('更新交易状态失败:', error);
        throw error;
    }
}

// 计算平台费用
export function calculatePlatformFee(amount) {
    return amount * (CONTRACT_CONFIG.FEES.PLATFORM_FEE_PERCENT / 100);
}

// 计算实际支付金额
export function calculateActualPayment(amount) {
    const platformFee = calculatePlatformFee(amount);
    return amount - platformFee;
}

// 执行USDC转账（包含费用分配）
export async function transferUSDC(fromAddress, toAddress, amount) {
    try {
        const connection = initializeSolanaConnection();
        const fromPublicKey = new window.solanaWeb3.PublicKey(fromAddress);
        
        // 计算费用分配
        const platformFee = calculatePlatformFee(amount);
        const actualPayment = calculateActualPayment(amount);
        
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
            actualPayment
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
            actualPayment
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