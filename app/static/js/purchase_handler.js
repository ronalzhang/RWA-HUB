/**
 * Complete asset purchase flow handler
 * Implements two-step purchase flow: 1. Create transaction 2. Confirm transaction
 */

// Prevent duplicate initialization
if (window.purchaseHandlerInitialized) {
    console.warn('Purchase handler already initialized, skipping...');
} else {
    window.purchaseHandlerInitialized = true;

    // Purchase flow manager (V3 Refactored)
    class PurchaseFlowManager {
        constructor() {
            this.currentTrade = null;
            this.isProcessing = false;
            this.retryAttempts = 0;
            this.maxRetries = 3;
            this.retryDelay = 2000; // 2 seconds
            
            // Enhanced error codes mapping
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
                'SERIALIZATION_ERROR': {
                    title: '交易序列化失败',
                    message: '交易数据处理失败，请重试',
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
                'ASSET_NOT_AVAILABLE': {
                    title: '资产不可用',
                    message: '该资产当前不可购买或已售完',
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
                },
                'TRANSACTION_CONFIRMATION_ERROR': {
                    title: '交易确认失败',
                    message: '交易确认过程中发生错误，请稍后重试',
                    retryable: true
                }
            };
        }

        // Get wallet address
        getWalletAddress() {
            return window.walletState?.address ||
                localStorage.getItem('walletAddress') ||
                (window.solana && window.solana.publicKey ? window.solana.publicKey.toString() : null);
        }

        // Enhanced error handling with detailed logging and user-friendly messages
        handleError(error, context = '') {
            // Log detailed error information for debugging
            const errorDetails = {
                context: context,
                timestamp: new Date().toISOString(),
                error: error,
                currentTrade: this.currentTrade,
                retryAttempts: this.retryAttempts,
                userAgent: navigator.userAgent,
                url: window.location.href
            };
            
            console.error(`[Purchase Flow Error] ${context}:`, errorDetails);
            
            // Parse error response
            let errorInfo = this.parseErrorResponse(error);
            
            // Use global error handler if available, otherwise fallback to local handling
            if (window.errorHandler && window.showPurchaseError) {
                window.showPurchaseError(error, {
                    showRetryButton: errorInfo.retryable && this.retryAttempts < this.maxRetries,
                    retryCallback: () => this.retryTransaction(),
                    maxRetries: this.maxRetries,
                    currentRetry: this.retryAttempts
                });
            } else {
                // Fallback to local error handling
                const errorConfig = this.errorCodes[errorInfo.code] || {
                    title: '操作失败',
                    message: errorInfo.message || '发生未知错误，请稍后重试',
                    retryable: true
                };
                
                this.showError(errorConfig.title, errorConfig.message, errorInfo.code, errorConfig.retryable);
            }
            
            return errorInfo;
        }

        // Parse error response from backend
        parseErrorResponse(error) {
            let errorInfo = {
                code: 'UNKNOWN_ERROR',
                message: '未知错误',
                details: null,
                retryable: true
            };
            
            try {
                if (error && typeof error === 'object') {
                    // Handle fetch response errors
                    if (error.response && error.response.data) {
                        const data = error.response.data;
                        errorInfo.code = data.error_code || 'API_ERROR';
                        errorInfo.message = data.message || '服务器响应错误';
                        errorInfo.details = data.details || null;
                    }
                    // Handle direct error objects
                    else if (error.error_code) {
                        errorInfo.code = error.error_code;
                        errorInfo.message = error.message || '操作失败';
                        errorInfo.details = error.details || null;
                    }
                    // Handle JavaScript errors
                    else if (error.message) {
                        errorInfo.message = error.message;
                        
                        // Classify common error types
                        if (error.message.includes('fetch')) {
                            errorInfo.code = 'NETWORK_ERROR';
                        } else if (error.message.includes('timeout')) {
                            errorInfo.code = 'TRANSACTION_TIMEOUT';
                        } else if (error.message.includes('rejected') || error.message.includes('User rejected')) {
                            errorInfo.code = 'USER_REJECTED';
                            errorInfo.retryable = false;
                        } else if (error.message.includes('insufficient')) {
                            errorInfo.code = 'INSUFFICIENT_BALANCE';
                            errorInfo.retryable = false;
                        }
                    }
                } else if (typeof error === 'string') {
                    errorInfo.message = error;
                }
            } catch (parseError) {
                console.error('Error parsing error response:', parseError);
            }
            
            return errorInfo;
        }

        // Show error message with retry option
        showError(title, message, errorCode = null, retryable = false) {
            console.error(`Error: ${title} - ${message} (Code: ${errorCode})`);
            
            if (typeof Swal !== 'undefined') {
                const swalConfig = {
                    title: title,
                    text: message,
                    icon: 'error',
                    confirmButtonText: '确定'
                };
                
                // Add retry button for retryable errors
                if (retryable && this.retryAttempts < this.maxRetries && this.currentTrade) {
                    swalConfig.showCancelButton = true;
                    swalConfig.cancelButtonText = '重试';
                    swalConfig.confirmButtonText = '取消';
                }
                
                Swal.fire(swalConfig).then((result) => {
                    if (retryable && result.dismiss === Swal.DismissReason.cancel && this.currentTrade) {
                        this.retryTransaction();
                    }
                });
            } else {
                const userMessage = `${title}: ${message}`;
                if (retryable && this.retryAttempts < this.maxRetries && this.currentTrade) {
                    const retry = confirm(`${userMessage}\n\n是否重试？`);
                    if (retry) {
                        this.retryTransaction();
                    }
                } else {
                    alert(userMessage);
                }
            }
        }

        // Show success message
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

        // Show loading state with progress information
        showLoading(message, step = null, totalSteps = null) {
            const progressText = step && totalSteps ? ` (${step}/${totalSteps})` : '';
            const fullMessage = `${message}${progressText}`;
            
            console.log(`Loading: ${fullMessage}`);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: '处理中...',
                    text: fullMessage,
                    icon: 'info',
                    allowOutsideClick: false,
                    showConfirmButton: false,
                    didOpen: () => {
                        Swal.showLoading();
                    }
                });
            }
        }

        // Retry transaction with exponential backoff
        async retryTransaction() {
            if (this.retryAttempts >= this.maxRetries) {
                this.showError('重试次数已达上限', '请稍后再试或联系客服');
                return;
            }
            
            this.retryAttempts++;
            const delay = this.retryDelay * Math.pow(2, this.retryAttempts - 1); // Exponential backoff
            
            console.log(`[Retry] 第 ${this.retryAttempts} 次重试，延迟 ${delay}ms`);
            this.showLoading(`正在重试... (${this.retryAttempts}/${this.maxRetries})`, this.retryAttempts, this.maxRetries);
            
            setTimeout(async () => {
                try {
                    if (this.currentTrade && this.currentTrade.transactionToSign) {
                        // Retry signing and confirming transaction
                        await this.signAndConfirmTransaction();
                    } else if (this.currentTrade) {
                        // Retry creating transaction
                        await this.createPurchase(this.currentTrade.assetId, this.currentTrade.amount);
                    }
                } catch (error) {
                    this.handleError(error, 'Transaction Retry');
                }
            }, delay);
        }

        // Reset retry state
        resetRetryState() {
            this.retryAttempts = 0;
        }

        // Step 1: Create purchase transaction (V3) with enhanced error handling
        async createPurchase(assetId, amount) {
            console.log(`[V3] 开始创建购买交易: 资产ID=${assetId}, 数量=${amount}, 重试次数=${this.retryAttempts}`);

            const walletAddress = this.getWalletAddress();
            if (!walletAddress) {
                this.handleError({
                    error_code: 'WALLET_CONNECTION_ERROR',
                    message: '请先连接您的钱包再进行购买'
                }, 'Wallet Validation');
                return false;
            }

            this.showLoading('正在向服务器请求交易...', 1, 3);

            try {
                // Add timeout to fetch request
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

                const response = await fetch('/api/trades/v3/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        asset_id: assetId,
                        amount: amount,
                        wallet_address: walletAddress
                    }),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                // Check if response is ok
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('[V3] 创建交易API响应:', data);

                if (data.success) {
                    this.currentTrade = {
                        id: data.trade_id,
                        assetId: assetId,
                        amount: amount,
                        transactionToSign: data.transaction
                    };

                    // Reset retry state on success
                    this.resetRetryState();

                    // Step 2: Sign transaction
                    return await this.signAndConfirmTransaction();
                } else {
                    // Handle backend error response
                    const errorInfo = {
                        error_code: data.error_code || 'TRANSACTION_CREATION_ERROR',
                        message: data.message || '创建交易失败',
                        details: data.details || null
                    };
                    throw errorInfo;
                }
            } catch (error) {
                console.error('[V3] 创建购买交易失败:', error);
                
                // Handle specific error types
                if (error.name === 'AbortError') {
                    this.handleError({
                        error_code: 'TRANSACTION_TIMEOUT',
                        message: '请求超时，请检查网络连接后重试'
                    }, 'Create Purchase Timeout');
                } else if (error.message && error.message.includes('fetch')) {
                    this.handleError({
                        error_code: 'NETWORK_ERROR',
                        message: '网络连接失败，请检查网络后重试'
                    }, 'Create Purchase Network Error');
                } else {
                    this.handleError(error, 'Create Purchase');
                }
                return false;
            }
        }

        // Step 2: Sign and send the transaction, then confirm with the backend (V3) with enhanced error handling
        async signAndConfirmTransaction() {
            if (!this.currentTrade || !this.currentTrade.transactionToSign) {
                this.handleError({
                    error_code: 'VALIDATION_ERROR',
                    message: '没有待处理的交易或交易数据'
                }, 'Transaction Validation');
                return false;
            }

            console.log('[V3] 开始签名并发送真实交易:', this.currentTrade);
            this.showLoading('请在钱包中确认交易...', 2, 3);

            try {
                // Validate wallet connection
                if (!window.solana || !window.solana.isConnected) {
                    throw {
                        error_code: 'WALLET_CONNECTION_ERROR',
                        message: '钱包未连接或不可用，请重新连接钱包'
                    };
                }

                // Validate Solana Web3 library
                if (!window.solanaWeb3 || !window.solanaWeb3.Transaction) {
                    console.error('Solana Web3 library (solanaWeb3.js) not found on window object.');
                    throw {
                        error_code: 'CONFIGURATION_ERROR',
                        message: '客户端库缺失，请刷新页面重试'
                    };
                }

                // 1. Decode the base64 transaction data from the backend
                let serializedTransaction;
                try {
                    serializedTransaction = Uint8Array.from(atob(this.currentTrade.transactionToSign), c => c.charCodeAt(0));
                } catch (decodeError) {
                    console.error('Transaction decode error:', decodeError);
                    throw {
                        error_code: 'SERIALIZATION_ERROR',
                        message: '交易数据格式错误，请重新创建交易'
                    };
                }

                // 2. Reconstruct the transaction object
                let transaction;
                try {
                    transaction = window.solanaWeb3.Transaction.from(serializedTransaction);
                    console.log('[V3] 成功反序列化交易，准备请求钱包签名...');
                } catch (reconstructError) {
                    console.error('Transaction reconstruction error:', reconstructError);
                    throw {
                        error_code: 'SERIALIZATION_ERROR',
                        message: '交易重构失败，请重新创建交易'
                    };
                }

                // 3. Sign and send the transaction using the wallet adapter
                let txHash;
                try {
                    txHash = await window.solana.signAndSendTransaction(transaction);
                    console.log('[V3] 交易已签名并发送，交易哈希:', txHash);
                } catch (walletError) {
                    console.error('Wallet signing error:', walletError);
                    
                    // Handle user rejection
                    if (walletError.message && (walletError.message.includes('User rejected') || walletError.code === 4001)) {
                        throw {
                            error_code: 'USER_REJECTED',
                            message: '您在钱包中拒绝了交易请求'
                        };
                    }
                    // Handle insufficient balance
                    else if (walletError.message && walletError.message.includes('insufficient')) {
                        throw {
                            error_code: 'INSUFFICIENT_BALANCE',
                            message: '钱包余额不足以完成此交易'
                        };
                    }
                    // Handle other wallet errors
                    else {
                        throw {
                            error_code: 'WALLET_CONNECTION_ERROR',
                            message: walletError.message || '钱包签名失败，请重试'
                        };
                    }
                }

                if (!txHash) {
                    throw {
                        error_code: 'TRANSACTION_CREATION_ERROR',
                        message: '未能获取交易哈希，交易可能已失败'
                    };
                }
                
                this.showLoading('正在链上确认交易...', 3, 3);

                // 4. Confirm the purchase on the backend with the real txHash
                return await this.confirmPurchase(txHash);

            } catch (error) {
                console.error('[V3] 签名或发送交易失败:', error);
                this.handleError(error, 'Sign and Send Transaction');
                return false;
            }
        }

        // Step 3: Confirm purchase transaction (V3) with enhanced error handling
        async confirmPurchase(txHash) {
            console.log(`[V3] 开始确认购买交易: 交易ID=${this.currentTrade.id}, 哈希=${txHash}`);

            this.showLoading('正在向服务器确认交易...');

            try {
                // Add timeout to confirmation request
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 45000); // 45 second timeout for confirmation

                const response = await fetch('/api/trades/v3/confirm', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        trade_id: this.currentTrade.id,
                        tx_hash: txHash
                    }),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                // Check if response is ok
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('[V3] 确认交易API响应:', data);

                if (data.success) {
                    // Reset retry state on success
                    this.resetRetryState();
                    
                    this.showSuccess(
                        '购买成功！',
                        `您已成功购买 ${this.currentTrade.amount} 个代币\n交易哈希: ${txHash.substring(0, 8)}...`,
                        () => {
                            window.location.reload();
                        }
                    );
                    this.currentTrade = null;
                    return true;
                } else {
                    // Handle backend error response
                    const errorInfo = {
                        error_code: data.error_code || 'TRANSACTION_CONFIRMATION_ERROR',
                        message: data.message || '确认交易失败',
                        details: data.details || null
                    };
                    throw errorInfo;
                }
            } catch (error) {
                console.error('[V3] 确认购买交易失败:', error);
                
                // Handle specific error types
                if (error.name === 'AbortError') {
                    this.handleError({
                        error_code: 'TRANSACTION_TIMEOUT',
                        message: '交易确认超时，但交易可能已成功，请检查您的钱包'
                    }, 'Confirm Purchase Timeout');
                } else if (error.message && error.message.includes('fetch')) {
                    this.handleError({
                        error_code: 'NETWORK_ERROR',
                        message: '网络连接失败，交易可能已成功，请检查您的钱包'
                    }, 'Confirm Purchase Network Error');
                } else {
                    this.handleError(error, 'Confirm Purchase');
                }
                return false;
            }
        }

        // Start complete purchase flow with enhanced error handling
        async initiatePurchase(assetId, amount) {
            if (this.isProcessing) {
                console.warn('购买流程正在进行中，请勿重复操作');
                this.showError('操作进行中', '请等待当前操作完成');
                return;
            }

            // Reset retry state for new purchase
            this.resetRetryState();
            this.isProcessing = true;
            
            // Log purchase initiation for debugging
            console.log('[Purchase Flow] 开始购买流程:', {
                assetId: assetId,
                amount: amount,
                timestamp: new Date().toISOString(),
                walletAddress: this.getWalletAddress(),
                userAgent: navigator.userAgent
            });

            try {
                const result = await this.createPurchase(assetId, amount);
                
                if (result) {
                    console.log('[Purchase Flow] 购买流程成功完成');
                } else {
                    console.log('[Purchase Flow] 购买流程失败');
                }
                
                return result;
            } catch (error) {
                console.error('[Purchase Flow] 购买流程异常:', error);
                this.handleError(error, 'Purchase Flow');
                return false;
            } finally {
                this.isProcessing = false;
            }
        }

        // Add method to check transaction status
        async checkTransactionStatus(txHash) {
            try {
                const response = await fetch(`/api/trades/status/${txHash}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    return data;
                } else {
                    console.warn('无法检查交易状态');
                    return null;
                }
            } catch (error) {
                console.error('检查交易状态失败:', error);
                return null;
            }
        }
    }

    // Create global purchase flow manager instance
    window.purchaseFlowManager = new PurchaseFlowManager();

    // Initialize purchase button event listener
    function initializePurchaseButton() {
        const buyButton = document.getElementById('buy-button');
        if (buyButton) {
            console.log('设置购买按钮事件监听器');

            // Clear possible existing event listeners
            const newButton = buyButton.cloneNode(true);
            buyButton.parentNode.replaceChild(newButton, buyButton);

            newButton.addEventListener('click', function (event) {
                event.preventDefault();
                event.stopPropagation();

                console.log('购买按钮被点击');
                console.log('事件详情:', {
                    type: event.type,
                    target: event.target.id,
                    timestamp: new Date().toISOString()
                });

                // Check wallet connection
                const walletAddress = window.purchaseFlowManager.getWalletAddress();
                console.log('钱包地址:', walletAddress);
                console.log('钱包状态检查:', {
                    'window.walletState': window.walletState,
                    'localStorage.walletAddress': localStorage.getItem('walletAddress'),
                    'localStorage.eth_address': localStorage.getItem('eth_address'),
                    'window.solana': !!window.solana
                });

                if (!walletAddress) {
                    window.purchaseFlowManager.showError('钱包未连接', '请先连接您的钱包再进行购买');
                    return;
                }

                // Get purchase amount
                const amountInput = document.getElementById('purchase-amount');
                const amount = parseInt(amountInput?.value || 0);
                console.log('购买数量详情:', {
                    inputExists: !!amountInput,
                    inputValue: amountInput?.value,
                    parsedAmount: amount,
                    inputMin: amountInput?.min,
                    inputMax: amountInput?.max
                });

                if (!amount || amount <= 0) {
                    window.purchaseFlowManager.showError('输入错误', '请输入有效的购买数量');
                    amountInput?.focus();
                    return;
                }

                // Get asset ID
                const assetId = document.querySelector('meta[name="asset-id"]')?.content ||
                    document.querySelector('[data-asset-id]')?.getAttribute('data-asset-id') ||
                    window.ASSET_CONFIG?.id;
                console.log('资产ID获取详情:', {
                    metaTag: document.querySelector('meta[name="asset-id"]')?.content,
                    dataAttribute: document.querySelector('[data-asset-id]')?.getAttribute('data-asset-id'),
                    windowConfig: window.ASSET_CONFIG?.id,
                    finalAssetId: assetId
                });

                if (!assetId) {
                    window.purchaseFlowManager.showError('系统错误', '无法获取资产信息');
                    return;
                }

                // Show confirmation dialog
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        title: '确认购买',
                        text: `您确定要购买 ${amount} 个代币吗？`,
                        icon: 'question',
                        showCancelButton: true,
                        confirmButtonText: '确认',
                        cancelButtonText: '取消'
                    }).then((result) => {
                        if (result.isConfirmed) {
                            window.purchaseFlowManager.initiatePurchase(parseInt(assetId), amount);
                        }
                    });
                } else {
                    const confirmed = confirm(`您确定要购买 ${amount} 个代币吗？`);
                    if (confirmed) {
                        window.purchaseFlowManager.initiatePurchase(parseInt(assetId), amount);
                    }
                }
            });

            console.log('购买按钮事件监听器设置完成');
            return true;
        } else {
            console.warn('购买按钮不存在');
            return false;
        }
    }

    // Initialize purchase button after DOM is loaded
    document.addEventListener('DOMContentLoaded', function () {
        // Only proceed if the buy button exists on the page.
        if (!document.getElementById('buy-button')) {
            console.log('购买按钮不存在，购买处理器不执行初始化。');
            return;
        }

        setTimeout(function () {
            if (!initializePurchaseButton()) {
                // If first initialization fails, retry a few times
                let retryCount = 0;
                const retryInterval = setInterval(function () {
                    retryCount++;
                    console.log(`重试初始化购买按钮 (${retryCount}/5)`);
                    if (initializePurchaseButton() || retryCount >= 5) {
                        clearInterval(retryInterval);
                    }
                }, 500);
            }
        }, 200);
    });

    // Also try to initialize on window.load event to ensure all resources are loaded
    window.addEventListener('load', function () {
        setTimeout(function () {
            if (!document.getElementById('buy-button')?.onclick) {
                console.log('window.load事件中重新初始化购买按钮');
                initializePurchaseButton();
            }
        }, 100);
    });

    console.log('完整购买流程处理器已加载');
}