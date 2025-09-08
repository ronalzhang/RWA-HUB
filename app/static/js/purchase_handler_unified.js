/**
 * 统一的资产购买处理器
 * 整合了原有的功能，使用正确的V3 API
 */

// 防止重复初始化
if (window.purchaseHandlerInitialized) {
    console.warn('Purchase handler already initialized, skipping...');
} else {
    window.purchaseHandlerInitialized = true;

    // 统一的购买流程管理器
    class UnifiedPurchaseFlowManager {
        constructor() {
            this.currentTrade = null;
            this.isProcessing = false;
            this.retryAttempts = 0;
            this.maxRetries = 3;
            this.retryDelay = 2000;
            
            // 错误代码映射
            this.errorCodes = {
                'CONFIGURATION_ERROR': {
                    title: '配置错误',
                    message: '系统配置不完整，请联系管理员',
                    retryable: false
                },
                'BLOCKCHAIN_CONNECTION_ERROR': {
                    title: '区块链连接失败',
                    message: '无法连接到区块链网络，请稍后重试',
                    retryable: true
                },
                'TRANSACTION_CREATION_ERROR': {
                    title: '交易创建失败',
                    message: '创建交易时发生错误，请重试',
                    retryable: true
                },
                'VALIDATION_ERROR': {
                    title: '数据验证失败',
                    message: '输入数据不符合要求，请检查后重试',
                    retryable: false
                },
                'INSUFFICIENT_BALANCE': {
                    title: '余额不足',
                    message: '您的钱包余额不足以完成此交易',
                    retryable: false
                },
                'WALLET_CONNECTION_ERROR': {
                    title: '钱包连接错误',
                    message: '钱包连接异常，请重新连接钱包',
                    retryable: false
                },
                'TRANSACTION_TIMEOUT': {
                    title: '交易超时',
                    message: '交易处理超时，请稍后重试',
                    retryable: true
                },
                'NETWORK_ERROR': {
                    title: '网络错误',
                    message: '网络连接不稳定，请检查网络后重试',
                    retryable: true
                },
                'USER_REJECTED': {
                    title: '交易已取消',
                    message: '您在钱包中拒绝了交易请求',
                    retryable: false
                }
            };
        }

        // 获取钱包地址
        getWalletAddress() {
            return window.walletState?.address ||
                localStorage.getItem('walletAddress') ||
                (window.solana && window.solana.publicKey ? window.solana.publicKey.toString() : null);
        }

        // 显示错误消息
        showError(title, message) {
            console.error(`Error: ${title} - ${message}`);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: title,
                    text: message,
                    icon: 'error',
                    confirmButtonText: '确定'
                });
            } else {
                alert(`${title}: ${message}`);
            }
        }

        // 显示成功消息
        showSuccess(title, message, callback = null) {
            console.log(`Success: ${title} - ${message}`);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: title,
                    text: message,
                    icon: 'success',
                    confirmButtonText: '确定'
                }).then(() => {
                    if (callback) callback();
                });
            } else {
                alert(`${title}: ${message}`);
                if (callback) callback();
            }
        }

        // 显示加载状态
        showLoading(message) {
            console.log(`Loading: ${message}`);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: '处理中...',
                    text: message,
                    icon: 'info',
                    allowOutsideClick: false,
                    showConfirmButton: false,
                    didOpen: () => {
                        Swal.showLoading();
                    }
                });
            }
        }

        // 处理错误
        handleError(error, context = '') {
            console.error(`[${context}] Error:`, error);
            
            let errorCode = error.error_code || 'UNKNOWN_ERROR';
            let errorInfo = this.errorCodes[errorCode];
            
            if (!errorInfo) {
                errorInfo = {
                    title: '未知错误',
                    message: error.message || '发生了未知错误',
                    retryable: false
                };
            }
            
            // 如果可以重试且未达到最大重试次数
            if (errorInfo.retryable && this.retryAttempts < this.maxRetries && this.currentTrade) {
                this.retryTransaction();
            } else {
                this.showError(errorInfo.title, errorInfo.message);
            }
        }

        // 重试交易
        async retryTransaction() {
            if (this.retryAttempts >= this.maxRetries) {
                this.showError('重试次数已达上限', '请稍后再试或联系客服');
                return;
            }
            
            this.retryAttempts++;
            const delay = this.retryDelay * Math.pow(2, this.retryAttempts - 1);
            
            console.log(`[Retry] 第 ${this.retryAttempts} 次重试，延迟 ${delay}ms`);
            this.showLoading(`正在重试... (${this.retryAttempts}/${this.maxRetries})`);
            
            setTimeout(async () => {
                try {
                    if (this.currentTrade) {
                        await this.signAndConfirmTransaction();
                    }
                } catch (error) {
                    this.handleError(error, 'Transaction Retry');
                }
            }, delay);
        }

        // 重置重试状态
        resetRetryState() {
            this.retryAttempts = 0;
        }

        // 步骤1: 创建购买交易
        async createPurchase(assetId, amount) {
            console.log(`开始创建购买交易: 资产ID=${assetId}, 数量=${amount}`);

            const walletAddress = this.getWalletAddress();
            if (!walletAddress) {
                this.showError('钱包未连接', '请先连接您的钱包再进行购买');
                return false;
            }

            this.showLoading('正在创建购买交易...');

            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 30000);

                const response = await fetch('/api/trades/v3/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        asset_id: assetId,
                        amount: amount,
                        wallet_address: walletAddress
                    }),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('创建交易API响应:', data);

                if (data.success) {
                    this.currentTrade = {
                        id: data.data.id,
                        transactionId: data.data.transaction_id,
                        assetId: assetId,
                        amount: amount,
                        totalCost: data.data.total_cost,
                        instructions: data.data.instructions,
                        recentBlockhash: data.data.recent_blockhash,
                        feePayer: data.data.fee_payer
                    };

                    this.resetRetryState();
                    return await this.signAndConfirmTransaction();
                } else {
                    throw {
                        error_code: data.error_code || 'TRANSACTION_CREATION_ERROR',
                        message: data.message || '创建交易失败'
                    };
                }
            } catch (error) {
                console.error('创建购买交易失败:', error);
                
                if (error.name === 'AbortError') {
                    this.handleError({
                        error_code: 'TRANSACTION_TIMEOUT',
                        message: '请求超时，请检查网络连接后重试'
                    }, 'Create Purchase Timeout');
                } else {
                    this.handleError(error, 'Create Purchase');
                }
                return false;
            }
        }

        // 步骤2: 签名和确认交易
        async signAndConfirmTransaction() {
            if (!this.currentTrade) {
                this.showError('系统错误', '没有待处理的交易');
                return false;
            }

            console.log('开始签名和确认交易:', this.currentTrade);

            try {
                // 检查钱包连接
                if (!window.solana || !window.solana.isConnected) {
                    throw {
                        error_code: 'WALLET_CONNECTION_ERROR',
                        message: '钱包未连接或不可用，请重新连接钱包'
                    };
                }

                // 检查USDC余额
                this.showLoading('正在检查USDC余额...');
                const balance = await this.checkUSDCBalance();
                const requiredAmount = this.currentTrade.totalCost; // 使用后端计算的总价
                
                console.log('USDC余额检查:', {
                    balance: balance,
                    requiredAmount: requiredAmount,
                    tokenAmount: this.currentTrade.amount,
                    totalCost: this.currentTrade.totalCost,
                    walletAddress: this.getWalletAddress()
                });

                if (balance < requiredAmount) {
                    throw {
                        error_code: 'INSUFFICIENT_BALANCE',
                        message: `USDC余额不足。需要: ${requiredAmount} USDC，当前: ${balance} USDC`
                    };
                }

                console.log('✅ USDC余额充足，继续交易');

                

                // 使用后端返回的区块哈希
                this.showLoading('正在构建交易...');
                // 获取最新的区块哈希以避免"Blockhash not found"错误
                this.showLoading('正在获取最新区块信息...');
                console.log('原始后端区块哈希:', this.currentTrade.recentBlockhash);
                
                // 获取最新的区块哈希
                const latestBlockhash = await window.solanaConnection.getLatestBlockhash();
                console.log('获取最新区块哈希:', latestBlockhash.blockhash);

                // 构建交易
                this.showLoading('正在构建交易...');
                const transaction = new window.solanaWeb3.Transaction({
                    recentBlockhash: latestBlockhash.blockhash,
                    feePayer: new window.solanaWeb3.PublicKey(this.currentTrade.feePayer)
                });

                // 不预先添加ComputeBudget指令，让钱包自动处理
                console.log('跳过ComputeBudget指令预添加，让钱包自动管理');

                // 添加多个指令
                console.log('后端返回的指令数据:', this.currentTrade.instructions);
                
                // 处理多个指令（用于分润转账）
                this.currentTrade.instructions.forEach((instrData, index) => {
                    const instruction = new window.solanaWeb3.TransactionInstruction({
                        keys: instrData.accounts.map(acc => ({
                            pubkey: new window.solanaWeb3.PublicKey(acc.pubkey),
                            isSigner: acc.is_signer,
                            isWritable: acc.is_writable
                        })),
                        programId: new window.solanaWeb3.PublicKey(instrData.program_id),
                        data: new Uint8Array(Buffer.from(instrData.data, 'hex'))
                    });

                    console.log(`创建的指令${index}详情:`, {
                        programId: instruction.programId.toString(),
                        accounts: instruction.keys.map(key => ({
                            pubkey: key.pubkey.toString(),
                            isSigner: key.isSigner,
                            isWritable: key.isWritable
                        })),
                        dataLength: instruction.data.length,
                        dataHex: instrData.data
                    });

                    transaction.add(instruction);
                });
                console.log('构建的交易:', transaction);

                // 请求钱包签名
                this.showLoading('正在请求钱包签名...');
                let signedTransaction = await window.solana.signTransaction(transaction);
                console.log('交易已签名:', signedTransaction);

                // 发送交易（带重试机制）
                this.showLoading('正在提交交易到区块链...');
                let txHash;
                let retryCount = 0;
                const maxRetries = 3;

                while (retryCount < maxRetries) {
                    try {
                        txHash = await window.solanaConnection.sendRawTransaction(
                            signedTransaction.serialize(),
                            {
                                skipPreflight: false,
                                preflightCommitment: 'confirmed'
                            }
                        );
                        console.log('交易已提交，哈希:', txHash);
                        break;
                    } catch (error) {
                        retryCount++;
                        console.log(`交易提交失败，重试 ${retryCount}/${maxRetries}:`, error.message);

                        if (retryCount >= maxRetries) {
                            throw error;
                        }

                        // 如果是区块哈希相关错误，重新获取最新区块哈希
                        if (error.message.includes('Blockhash not found') || error.message.includes('blockhash')) {
                            console.log('检测到区块哈希过期，重新获取...');
                            const newBlockhash = await window.solanaConnection.getLatestBlockhash();
                            transaction.recentBlockhash = newBlockhash.blockhash;

                            // 重新签名交易并完全替换签名的交易对象
                            signedTransaction = await window.solana.signTransaction(transaction);
                            console.log('区块哈希已更新并重新签名:', {
                                oldBlockhash: newBlockhash.blockhash,
                                newBlockhash: transaction.recentBlockhash,
                                hasSignature: signedTransaction.signatures.length > 0
                            });
                        }

                        // 等待1秒后重试
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }

                // 等待确认（使用最新的区块高度信息）
                this.showLoading('正在等待交易确认...');
                const confirmation = await window.solanaConnection.confirmTransaction({
                    signature: txHash,
                    blockhash: latestBlockhash.blockhash,
                    lastValidBlockHeight: latestBlockhash.lastValidBlockHeight
                });
                console.log('交易确认结果:', confirmation);

                if (confirmation.value.err) {
                    throw new Error(`交易失败: ${JSON.stringify(confirmation.value.err)}`);
                }

                // 确认购买
                return await this.confirmPurchase(txHash);

            } catch (error) {
                console.error('签名和确认交易失败:', error);
                
                if (error.message && error.message.includes('User rejected')) {
                    this.handleError({
                        error_code: 'USER_REJECTED',
                        message: '您在钱包中拒绝了交易请求'
                    }, 'Sign Transaction');
                } else {
                    this.handleError(error, 'Sign and Confirm Transaction');
                }
                return false;
            }
        }

        // 步骤3: 确认购买
        async confirmPurchase(txHash) {
            console.log(`开始确认购买交易: 交易ID=${this.currentTrade.id}, 哈希=${txHash}`);

            this.showLoading('正在确认交易...');

            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 45000);

                const response = await fetch('/api/trades/v3/confirm', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        trade_id: this.currentTrade.id,
                        tx_hash: txHash
                    }),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('确认交易API响应:', data);

                if (data.success) {
                    this.resetRetryState();
                    this.showSuccess(
                        '购买成功！',
                        `您已成功购买 ${this.currentTrade.amount} 个代币\\n交易哈希: ${txHash.substring(0, 8)}...`,
                        () => {
                            window.location.reload();
                        }
                    );
                    this.currentTrade = null;
                    return true;
                } else {
                    throw {
                        error_code: data.error_code || 'TRANSACTION_CONFIRMATION_ERROR',
                        message: data.message || '确认交易失败'
                    };
                }
            } catch (error) {
                console.error('确认购买交易失败:', error);
                
                if (error.name === 'AbortError') {
                    this.handleError({
                        error_code: 'TRANSACTION_TIMEOUT',
                        message: '交易确认超时，但交易可能已成功，请检查您的钱包'
                    }, 'Confirm Purchase Timeout');
                } else {
                    this.handleError(error, 'Confirm Purchase');
                }
                return false;
            }
        }

        // 检查USDC余额
        async checkUSDCBalance() {
            try {
                const walletAddress = this.getWalletAddress();
                if (!walletAddress) {
                    console.log('钱包地址不存在');
                    return 0;
                }

                // 确保Solana连接已初始化
                if (!window.solanaConnection) {
                    ensureSolanaConnection();
                }

                // 检查必要的库是否加载
                if (!window.solanaWeb3) {
                    console.error('Solana Web3.js 库未加载');
                    return 0;
                }

                // USDC代币地址 (mainnet)
                const USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
                const walletPubkey = new window.solanaWeb3.PublicKey(walletAddress);
                const usdcMint = new window.solanaWeb3.PublicKey(USDC_MINT);

                console.log('开始检查USDC余额:', {
                    walletAddress,
                    usdcMint: USDC_MINT,
                    splTokenAvailable: !!window.splToken,
                    getAssociatedTokenAddressAvailable: !!window.splToken?.getAssociatedTokenAddress,
                    connectionAvailable: !!window.solanaConnection
                });

                // 获取关联代币账户地址
                let associatedTokenAddress;
                if (window.splToken?.getAssociatedTokenAddress) {
                    associatedTokenAddress = await window.splToken.getAssociatedTokenAddress(
                        usdcMint,
                        walletPubkey
                    );
                } else {
                    console.error('getAssociatedTokenAddress 函数不可用');
                    return 0;
                }

                console.log('关联代币账户地址:', associatedTokenAddress.toString());

                // 获取账户信息（带重试机制）
                if (!window.solanaConnection) {
                    console.error('Solana连接未初始化，无法获取账户信息');
                    return 0;
                }
                
                let accountInfo = null;
                let lastError = null;
                
                for (let attempt = 0; attempt < 3; attempt++) {
                    try {
                        accountInfo = await window.solanaConnection.getAccountInfo(associatedTokenAddress);
                        console.log(`✅ 第${attempt + 1}次尝试获取账户信息成功`);
                        break;
                    } catch (error) {
                        lastError = error;
                        console.warn(`第${attempt + 1}次获取账户信息失败:`, error.message);
                        
                        if (attempt < 2) {
                            // 重新初始化连接并重试
                            console.log('重新初始化Solana连接...');
                            ensureSolanaConnection();
                            await new Promise(resolve => setTimeout(resolve, 1000)); // 等待1秒
                        }
                    }
                }
                
                if (!accountInfo && lastError) {
                    throw lastError;
                }
                
                if (!accountInfo) {
                    console.log('USDC代币账户不存在，余额为0');
                    return 0;
                }

                // 解析代币账户数据
                let balance = 0;
                
                try {
                    if (window.splToken?.AccountLayout) {
                        console.log('使用SPL Token AccountLayout解码');
                        const accountData = window.splToken.AccountLayout.decode(accountInfo.data);
                        balance = Number(accountData.amount) / Math.pow(10, 6);
                    } else {
                        console.log('AccountLayout不可用，使用手动解码');
                        // 手动解码SPL Token账户数据
                        const data = accountInfo.data;
                        if (data.length >= 72) {
                            // amount字段在偏移量64处，为8字节的little-endian数字
                            const view = new DataView(data.buffer, data.byteOffset + 64, 8);
                            const rawAmount = view.getBigUint64(0, true); // little-endian
                            balance = Number(rawAmount) / Math.pow(10, 6);
                            console.log('手动解码成功:', {
                                rawAmount: rawAmount.toString(),
                                balance: balance
                            });
                        } else {
                            console.error('账户数据长度不足:', data.length);
                            return 0;
                        }
                    }
                } catch (decodeError) {
                    console.error('解码账户数据失败:', decodeError);
                    console.log('尝试备用解码方法...');
                    
                    // 备用解码方法
                    const data = accountInfo.data;
                    if (data && data.length >= 72) {
                        try {
                            // 直接从buffer读取
                            const buffer = data instanceof Uint8Array ? data : new Uint8Array(data);
                            const view = new DataView(buffer.buffer, buffer.byteOffset + 64, 8);
                            const rawAmount = view.getBigUint64(0, true);
                            balance = Number(rawAmount) / Math.pow(10, 6);
                            console.log('备用解码成功:', balance);
                        } catch (backupError) {
                            console.error('备用解码也失败:', backupError);
                            return 0;
                        }
                    } else {
                        console.error('数据无效，无法解码');
                        return 0;
                    }
                }
                
                console.log('USDC余额检查完成:', {
                    balance: balance,
                    decimals: 6,
                    walletAddress: walletAddress
                });
                
                return balance;
            } catch (error) {
                console.error('检查USDC余额失败:', error);
                console.error('错误详情:', {
                    message: error.message,
                    stack: error.stack,
                    splTokenAvailable: !!window.splToken,
                    solanaWeb3Available: !!window.solanaWeb3,
                    connectionAvailable: !!window.solanaConnection
                });
                return 0;
            }
        }

        // 启动完整购买流程
        async initiatePurchase(assetId, amount) {
            if (this.isProcessing) {
                console.warn('购买流程正在进行中，请勿重复操作');
                this.showError('操作进行中', '请等待当前操作完成');
                return;
            }

            this.resetRetryState();
            this.isProcessing = true;
            
            console.log('[Purchase Flow] 开始购买流程:', {
                assetId: assetId,
                amount: amount,
                timestamp: new Date().toISOString(),
                walletAddress: this.getWalletAddress()
            });

            try {
                const result = await this.createPurchase(assetId, amount);
                console.log('[Purchase Flow] 购买流程完成，结果:', result);
                return result;
            } catch (error) {
                console.error('[Purchase Flow] 购买流程异常:', error);
                this.handleError(error, 'Purchase Flow');
                return false;
            } finally {
                this.isProcessing = false;
            }
        }
    }

    

    // 初始化Solana连接（如果未初始化）
    function ensureSolanaConnection() {
        if (!window.solanaConnection && window.solanaWeb3) {
            console.log('初始化Solana连接...');
            
            // RPC端点配置（主要和备用）
            const rpcEndpoints = [
                'https://mainnet.helius-rpc.com/?api-key=edbb3e74-772d-4c65-a430-5c89f7ad02ea',
                'https://api.mainnet-beta.solana.com',
                'https://solana-api.projectserum.com'
            ];
            
            for (let i = 0; i < rpcEndpoints.length; i++) {
                try {
                    const endpoint = rpcEndpoints[i];
                    window.solanaConnection = new window.solanaWeb3.Connection(endpoint, 'confirmed');
                    console.log(`✅ Solana连接已初始化: ${endpoint}`);
                    break;
                } catch (error) {
                    console.error(`RPC端点 ${rpcEndpoints[i]} 连接失败:`, error);
                    if (i === rpcEndpoints.length - 1) {
                        console.error('❌ 所有RPC端点连接失败');
                        throw new Error('无法连接到Solana网络');
                    }
                }
            }
        }
    }

    // 检查库初始化状态
    function checkLibrariesInitialization() {
        // 确保Solana连接已初始化
        ensureSolanaConnection();
        
        const checks = {
            solanaWeb3: !!window.solanaWeb3,
            splToken: !!window.splToken,
            splTokenGetAssociatedTokenAddress: !!(window.splToken && window.splToken.getAssociatedTokenAddress),
            splTokenAccountLayout: !!(window.splToken && (window.splToken.AccountLayout || window.splToken.TOKEN_PROGRAM_ID || window.splToken.createAccount)),
            solanaConnection: !!window.solanaConnection
        };
        
        console.log('库初始化检查:', checks);
        
        const allLoaded = Object.values(checks).every(check => check);
        if (!allLoaded) {
            // 只有真正关键的库缺失时才显示警告
            const criticalMissing = !checks.solanaWeb3 || !checks.splToken || !checks.solanaConnection;
            if (criticalMissing) {
                console.warn('部分库未正确加载，可能影响购买功能');
            } else {
                console.log('所有必要的Solana库已正确加载');
            }
            
            // 如果SPL Token库中缺少AccountLayout，尝试手动添加
            if (window.splToken && !window.splToken.AccountLayout) {
                console.log('尝试添加SPL Token AccountLayout...');
                // AccountLayout是一个简单的数据结构，我们可以提供一个基本实现
                window.splToken.AccountLayout = {
                    decode: function(data) {
                        // 简化的SPL Token账户数据解析
                        if (data.length < 165) {
                            throw new Error('Invalid account data length');
                        }
                        return {
                            mint: data.slice(0, 32),
                            owner: data.slice(32, 64),
                            amount: data.slice(64, 72),
                            delegateOption: data[72],
                            delegate: data.slice(73, 105),
                            state: data[105],
                            isNativeOption: data[106],
                            isNative: data.slice(107, 115),
                            delegatedAmount: data.slice(115, 123),
                            closeAuthorityOption: data[123],
                            closeAuthority: data.slice(124, 156)
                        };
                    }
                };
                console.log('SPL Token AccountLayout已添加');
            }
        }
        
        return checks;
    }

    // 创建全局实例
    window.purchaseFlowManager = new UnifiedPurchaseFlowManager();

    // 全局购买函数
    window.initiatePurchase = async function(assetId, amount) {
        // 在购买前检查库状态
        checkLibrariesInitialization();
        return window.purchaseFlowManager.initiatePurchase(assetId, amount);
    };

    // 绑定购买按钮事件
    function bindPurchaseButton() {
        const buyButton = document.getElementById('buy-button');
        if (buyButton && !buyButton.hasAttribute('data-event-bound')) {
            buyButton.setAttribute('data-event-bound', 'true');
            buyButton.addEventListener('click', function(e) {
                e.preventDefault();
                
                console.log('购买按钮被点击');
                
                // 获取资产ID和购买数量
                const assetId = parseInt(this.getAttribute('data-asset-id'));
                const amountInput = document.getElementById('purchase-amount');
                const amount = parseInt(amountInput ? amountInput.value : 1);
                
                console.log('购买参数:', { assetId, amount });
                
                if (!assetId || !amount || amount <= 0) {
                    alert('请输入有效的购买数量');
                    return;
                }
                
                // 调用购买流程
                window.initiatePurchase(assetId, amount);
            });
            
            console.log('✅ 购买按钮事件已绑定');
        }
    }

    // DOM加载完成后绑定事件
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            bindPurchaseButton();
            // 延迟检查库状态，给其他脚本时间加载
            setTimeout(checkLibrariesInitialization, 1000);
        });
    } else {
        bindPurchaseButton();
        // 延迟检查库状态，给其他脚本时间加载
        setTimeout(checkLibrariesInitialization, 1000);
    }

    console.log('✅ 统一购买处理器初始化完成');
}