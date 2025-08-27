/**
 * Complete asset purchase flow handler
 * Implements two-step purchase flow: 1. Create transaction 2. Confirm transaction
 */

// Prevent duplicate initialization
if (window.purchaseHandlerInitialized) {
    console.warn('Purchase handler already initialized, skipping...');
} else {
    window.purchaseHandlerInitialized = true;

    // Purchase flow manager
    class PurchaseFlowManager {
        constructor() {
            this.currentTrade = null;
            this.isProcessing = false;
        }

        // Get wallet address
        getWalletAddress() {
            return window.walletState?.address ||
                localStorage.getItem('walletAddress') ||
                (window.solana && window.solana.publicKey ? window.solana.publicKey.toString() : null);
        }

        // Show error message
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

        // Show loading state
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

        // Step 1: Create purchase transaction
        async createPurchase(assetId, amount) {
            console.log(`开始创建购买交易: 资产ID=${assetId}, 数量=${amount}`);

            const walletAddress = this.getWalletAddress();
            if (!walletAddress) {
                this.showError('钱包未连接', '请先连接您的钱包再进行购买');
                return false;
            }

            this.showLoading('正在创建购买交易...');

            try {
                const response = await fetch('/api/v2/trades/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Wallet-Address': walletAddress
                    },
                    body: JSON.stringify({
                        asset_id: assetId,
                        amount: amount
                    })
                });

                const data = await response.json();
                console.log('创建交易API响应:', data);

                if (data.success) {
                    this.currentTrade = {
                        id: data.trade_id,
                        assetId: assetId,
                        amount: amount,
                        transactionToSign: data.transaction_to_sign
                    };

                    // Step 2: Sign transaction
                    return await this.signAndConfirmTransaction();
                } else {
                    throw new Error(data.message || '创建交易失败');
                }
            } catch (error) {
                console.error('创建购买交易失败:', error);
                this.showError('创建交易失败', error.message || '请稍后重试');
                return false;
            }
        }

        // Step 2: Sign and send the transaction, then confirm with the backend
        async signAndConfirmTransaction() {
            if (!this.currentTrade || !this.currentTrade.transactionToSign) {
                this.showError('系统错误', '没有待处理的交易或交易数据');
                return false;
            }

            console.log('开始签名并发送真实交易:', this.currentTrade);
            this.showLoading('请在钱包中确认交易...');

            try {
                if (!window.solana || !window.solana.isConnected) {
                    throw new Error('钱包未连接或不可用');
                }

                // 1. Decode the base64 transaction data from the backend
                const serializedTransaction = Uint8Array.from(atob(this.currentTrade.transactionToSign), c => c.charCodeAt(0));

                // 2. Reconstruct the transaction object using the solanaWeb3.js library
                if (!window.solanaWeb3 || !window.solanaWeb3.Transaction) {
                    console.error('Solana Web3 library (solanaWeb3.js) not found on window object.');
                    throw new Error('客户端库缺失，无法处理交易。');
                }
                const transaction = window.solanaWeb3.Transaction.from(serializedTransaction);
                console.log('成功反序列化交易，准备请求钱包签名...');

                // 3. Sign and send the transaction using the wallet adapter.
                // This method prompts the user, signs, sends the transaction, and returns the transaction signature (txHash).
                const txHash = await window.solana.signAndSendTransaction(transaction);
                console.log('交易已签名并发送，交易哈希:', txHash);

                if (!txHash) {
                    throw new Error('未能获取交易哈希，交易可能已失败。');
                }
                
                this.showLoading('正在链上确认交易...');

                // 4. Confirm the purchase on the backend with the real txHash
                return await this.confirmPurchase(txHash);

            } catch (error) {
                console.error('签名或发送交易失败:', error);
                // Check for user rejection, which can have different error codes or messages
                if (error.message && (error.message.includes('User rejected') || error.code === 4001)) {
                    this.showError('交易已取消', '您在钱包中拒绝了交易请求。');
                } else {
                    this.showError('交易失败', error.message || '签名或发送交易时发生未知错误。');
                }
                return false;
            }
        }

        // NOTE: The functions `buildTransaction` and `sendTransaction` have been removed 
        // as they contained simulation logic and are no longer needed with the new 
        // `signAndSendTransaction` flow.

        // Step 3: Confirm purchase transaction
        async confirmPurchase(txHash) {
            console.log(`开始确认购买交易: 交易ID=${this.currentTrade.id}, 哈希=${txHash}`);

            this.showLoading('正在确认交易...');

            try {
                const walletAddress = this.getWalletAddress();
                const response = await fetch('/api/v2/trades/confirm', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Wallet-Address': walletAddress
                    },
                    body: JSON.stringify({
                        trade_id: this.currentTrade.id,
                        tx_hash: txHash
                    })
                });

                const data = await response.json();
                console.log('确认交易API响应:', data);

                if (data.success) {
                    this.showSuccess(
                        '购买成功！',
                        `您已成功购买 ${this.currentTrade.amount} 个代币`,
                        () => {
                            // Refresh page to show latest status
                            window.location.reload();
                        }
                    );
                    this.currentTrade = null;
                    return true;
                } else {
                    throw new Error(data.message || '确认交易失败');
                }
            } catch (error) {
                console.error('确认购买交易失败:', error);
                this.showError('确认交易失败', error.message || '请稍后重试');
                return false;
            }
        }

        // Start complete purchase flow
        async initiatePurchase(assetId, amount) {
            if (this.isProcessing) {
                console.warn('购买流程正在进行中，请勿重复操作');
                return;
            }

            this.isProcessing = true;
            try {
                await this.createPurchase(assetId, amount);
            } finally {
                this.isProcessing = false;
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