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
                        instruction: data.data.instruction,
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
                console.log('使用后端返回的区块哈希:', this.currentTrade.recentBlockhash);

                // 构建交易
                const transaction = new window.solanaWeb3.Transaction({
                    recentBlockhash: this.currentTrade.recentBlockhash,
                    feePayer: new window.solanaWeb3.PublicKey(this.currentTrade.feePayer)
                });

                // 添加指令
                const instruction = new window.solanaWeb3.TransactionInstruction({
                    keys: this.currentTrade.instruction.accounts.map(acc => ({
                        pubkey: new window.solanaWeb3.PublicKey(acc.pubkey),
                        isSigner: acc.is_signer,
                        isWritable: acc.is_writable
                    })),
                    programId: new window.solanaWeb3.PublicKey(this.currentTrade.instruction.program_id),
                    data: Buffer.from(this.currentTrade.instruction.data, 'hex')
                });

                transaction.add(instruction);
                console.log('构建的交易:', transaction);

                // 请求钱包签名
                this.showLoading('正在请求钱包签名...');
                const signedTransaction = await window.solana.signTransaction(transaction);
                console.log('交易已签名:', signedTransaction);

                // 发送交易
                this.showLoading('正在提交交易到区块链...');
                const txHash = await window.solanaConnection.sendRawTransaction(signedTransaction.serialize());
                console.log('交易已提交，哈希:', txHash);

                // 等待确认
                this.showLoading('正在等待交易确认...');
                const confirmation = await window.solanaConnection.confirmTransaction(txHash);
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
                    if (window.solanaWeb3) {
                        console.log('重新初始化Solana连接...');
                        const solanaEndpoint = 'https://api.mainnet-beta.solana.com';
                        window.solanaConnection = new window.solanaWeb3.Connection(solanaEndpoint, 'confirmed');
                        console.log('✅ Solana连接重新初始化成功');
                    } else {
                        console.error('Solana Web3.js 库未加载');
                        return 0;
                    }
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

                // 获取账户信息
                if (!window.solanaConnection) {
                    console.error('Solana连接未初始化，无法获取账户信息');
                    return 0;
                }
                const accountInfo = await window.solanaConnection.getAccountInfo(associatedTokenAddress);
                
                if (!accountInfo) {
                    console.log('USDC代币账户不存在，余额为0');
                    return 0;
                }

                // 解析代币账户数据
                if (!window.splToken?.AccountLayout) {
                    console.error('AccountLayout 不可用');
                    return 0;
                }

                const accountData = window.splToken.AccountLayout.decode(accountInfo.data);
                const balance = Number(accountData.amount) / Math.pow(10, 6); // USDC有6位小数
                
                console.log('USDC余额检查完成:', {
                    rawAmount: accountData.amount.toString(),
                    balance: balance,
                    decimals: 6
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

    // 动态加载SPL Token库
    async function loadSPLTokenLibrary() {
        return new Promise((resolve, reject) => {
            if (window.splToken) {
                console.log('SPL Token库已存在');
                resolve(true);
                return;
            }
            
            console.log('动态加载SPL Token库...');
            const script = document.createElement('script');
            script.src = '/static/js/contracts/spl-token.iife.min.js?v=' + Date.now();
            script.onload = function() {
                console.log('SPL Token库动态加载完成');
                // 等待一下让库初始化
                setTimeout(() => {
                    if (window.splToken) {
                        resolve(true);
                    } else {
                        reject(new Error('SPL Token库加载后仍不可用'));
                    }
                }, 500);
            };
            script.onerror = function() {
                reject(new Error('SPL Token库加载失败'));
            };
            document.head.appendChild(script);
        });
    }

    // 初始化Solana连接（如果未初始化）
    function ensureSolanaConnection() {
        if (!window.solanaConnection && window.solanaWeb3) {
            console.log('初始化Solana连接...');
            try {
                const solanaEndpoint = 'https://api.mainnet-beta.solana.com';
                window.solanaConnection = new window.solanaWeb3.Connection(solanaEndpoint, 'confirmed');
                console.log(`✅ Solana 连接已初始化: ${solanaEndpoint}`);
            } catch (error) {
                console.error('Solana连接初始化失败:', error);
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
            splTokenAccountLayout: !!(window.splToken && window.splToken.AccountLayout),
            solanaConnection: !!window.solanaConnection
        };
        
        console.log('库初始化检查:', checks);
        
        const allLoaded = Object.values(checks).every(check => check);
        if (!allLoaded) {
            console.warn('部分库未正确加载，可能影响购买功能');
            
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
                        
                        // SPL Token账户结构：
                        // - mint: 32 bytes (0-31)
                        // - owner: 32 bytes (32-63) 
                        // - amount: 8 bytes (64-71)
                        // - delegate: 32 bytes (72-103)
                        // - state: 1 byte (104)
                        // - isNative: 8 bytes (105-112)
                        // - delegatedAmount: 8 bytes (113-120)
                        // - closeAuthority: 32 bytes (121-152)
                        
                        const amount = data.slice(64, 72);
                        // 转换为BigInt然后转为字符串
                        const amountBigInt = new DataView(amount.buffer, amount.byteOffset).getBigUint64(0, true);
                        
                        return {
                            mint: data.slice(0, 32),
                            owner: data.slice(32, 64),
                            amount: amountBigInt,
                            delegate: data.slice(72, 104),
                            state: data[104],
                            isNative: data.slice(105, 113),
                            delegatedAmount: data.slice(113, 121),
                            closeAuthority: data.slice(121, 153)
                        };
                    }
                };
                console.log('✅ SPL Token AccountLayout已添加');
            }
        }
        
        return checks;
    }

    // 创建全局实例
    window.purchaseFlowManager = new UnifiedPurchaseFlowManager();

    // 全局购买函数
    window.initiatePurchase = async function(assetId, amount) {
        // 在购买前检查库状态
        const libStatus = checkLibrariesInitialization();
        
        // 如果SPL Token库未加载，尝试动态加载
        if (!libStatus.splToken || !libStatus.splTokenGetAssociatedTokenAddress) {
            console.log('SPL Token库未加载，尝试动态加载...');
            
            try {
                await loadSPLTokenLibrary();
                console.log('SPL Token库动态加载成功');
                
                // 重新检查库状态
                const newLibStatus = checkLibrariesInitialization();
                if (!newLibStatus.splToken || !newLibStatus.splTokenGetAssociatedTokenAddress) {
                    throw new Error('动态加载后SPL Token库仍不可用');
                }
            } catch (error) {
                console.error('动态加载SPL Token库失败:', error);
                // Display an error message to the user and stop the process.
                if (window.purchaseFlowManager && typeof window.purchaseFlowManager.showError === 'function') {
                    window.purchaseFlowManager.showError('初始化失败', '交易依赖库加载失败，请刷新页面或联系管理员。');
                } else {
                    alert('初始化失败: 交易依赖库加载失败，请刷新页面或联系管理员。');
                }
                return false; // Stop the purchase process
            }
        }
        
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
            setTimeout(async function() {
                const libStatus = checkLibrariesInitialization();
                // 如果SPL Token库未加载，尝试预加载
                if (!libStatus.splToken) {
                    console.log('预加载SPL Token库...');
                    try {
                        await loadSPLTokenLibrary();
                        console.log('SPL Token库预加载成功');
                        checkLibrariesInitialization(); // 重新检查
                    } catch (error) {
                        console.warn('SPL Token库预加载失败:', error);
                    }
                }
            }, 1000);
        });
    } else {
        bindPurchaseButton();
        // 延迟检查库状态，给其他脚本时间加载
        setTimeout(async function() {
            const libStatus = checkLibrariesInitialization();
            // 如果SPL Token库未加载，尝试预加载
            if (!libStatus.splToken) {
                console.log('预加载SPL Token库...');
                try {
                    await loadSPLTokenLibrary();
                    console.log('SPL Token库预加载成功');
                    checkLibrariesInitialization(); // 重新检查
                } catch (error) {
                    console.warn('SPL Token库预加载失败:', error);
                }
            }
        }, 1000);
    }

    console.log('✅ 统一购买处理器初始化完成');
}