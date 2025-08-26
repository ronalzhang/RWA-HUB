/**
 * 完整的资产购买流程处理器
 * 实现两步购买流程：1. 创建交易 2. 确认交易
 */

// 防止重复初始化
if (window.purchaseHandlerInitialized) {
    console.warn('Purchase handler already initialized, skipping...');
} else {
    window.purchaseHandlerInitialized = true;
    
    // 购买流程管理器
    class PurchaseFlowManager {
        constructor() {
            this.currentTrade = null;
            this.isProcessing = false;
        }

        // 获取钱包地址
        getWalletAddress() {
            return window.walletState?.address || 
                   localStorage.getItem('walletAddress') || 
                   (window.solana && window.solana.publicKey ? window.solana.publicKey.toString() : null);
        }

        // 显示错误信息
        showError(title, message) {
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

        // 显示成功信息
        showSuccess(title, message, callback = null) {
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

        // 第一步：创建购买交易
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
                    
                    // 进入第二步：签名交易
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

        // 第二步：签名并确认交易
        async signAndConfirmTransaction() {
            if (!this.currentTrade) {
                this.showError('系统错误', '没有待处理的交易');
                return false;
            }

            console.log('开始签名交易:', this.currentTrade);
            this.showLoading('请在钱包中确认交易...');

            try {
                // 检查钱包连接
                if (!window.solana || !window.solana.isConnected) {
                    throw new Error('钱包未连接或不可用');
                }

                // 构建交易对象
                const transaction = this.buildTransaction(this.currentTrade.transactionToSign);
                
                // 请求钱包签名
                const signedTransaction = await window.solana.signTransaction(transaction);
                console.log('交易签名成功');

                // 发送交易到区块链
                this.showLoading('正在提交交易到区块链...');
                const txHash = await this.sendTransaction(signedTransaction);
                console.log('交易已提交，哈希:', txHash);

                // 确认交易
                return await this.confirmPurchase(txHash);

            } catch (error) {
                console.error('签名或发送交易失败:', error);
                if (error.message.includes('User rejected')) {
                    this.showError('交易取消', '您取消了交易签名');
                } else {
                    this.showError('交易失败', error.message || '签名或发送交易时发生错误');
                }
                return false;
            }
        }

        // 构建交易对象
        buildTransaction(transactionData) {
            try {
                // 如果有简化的solanaWeb3对象，使用它
                if (window.solanaWeb3 && window.solanaWeb3.Transaction) {
                    return window.solanaWeb3.Transaction.from(Buffer.from(transactionData, 'base64'));
                }
                
                // 否则创建一个基本的交易对象
                return {
                    serialize: () => Buffer.from(transactionData, 'base64'),
                    _transactionData: transactionData
                };
            } catch (error) {
                console.error('构建交易对象失败:', error);
                throw new Error('无法构建交易对象');
            }
        }

        // 发送交易到区块链
        async sendTransaction(signedTransaction) {
            try {
                // 使用钱包的sendTransaction方法
                if (window.solana.sendTransaction) {
                    const signature = await window.solana.sendTransaction(signedTransaction);
                    return signature;
                }
                
                // 或者使用signAndSendTransaction
                if (window.solana.signAndSendTransaction) {
                    const signature = await window.solana.signAndSendTransaction(signedTransaction);
                    return signature;
                }
                
                throw new Error('钱包不支持发送交易');
            } catch (error) {
                console.error('发送交易失败:', error);
                throw error;
            }
        }

        // 第三步：确认购买交易
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
                            // 刷新页面显示最新状态
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

        // 启动完整购买流程
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

    // 创建全局购买流程管理器实例
    window.purchaseFlowManager = new PurchaseFlowManager();
    
    // 页面加载完成后初始化购买按钮
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() {
            const buyButton = document.getElementById('buy-button');
            if (buyButton) {
                console.log('设置购买按钮事件监听器');
                
                // 清除可能存在的旧事件监听器
                const newButton = buyButton.cloneNode(true);
                buyButton.parentNode.replaceChild(newButton, buyButton);
                
                newButton.addEventListener('click', function(event) {
                    event.preventDefault();
                    event.stopPropagation();
                    
                    console.log('购买按钮被点击');
                    
                    // 检查钱包连接
                    const walletAddress = window.purchaseFlowManager.getWalletAddress();
                    if (!walletAddress) {
                        window.purchaseFlowManager.showError('钱包未连接', '请先连接您的钱包再进行购买');
                        return;
                    }

                    // 获取购买数量
                    const amountInput = document.getElementById('purchase-amount');
                    const amount = parseInt(amountInput?.value || 0);
                    if (!amount || amount <= 0) {
                        window.purchaseFlowManager.showError('输入错误', '请输入有效的购买数量');
                        amountInput?.focus();
                        return;
                    }

                    // 获取资产ID
                    const assetId = document.querySelector('meta[name="asset-id"]')?.content || window.ASSET_CONFIG?.id;
                    if (!assetId) {
                        window.purchaseFlowManager.showError('系统错误', '无法获取资产信息');
                        return;
                    }

                    // 显示确认对话框
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
            } else {
                console.warn('购买按钮不存在');
            }
        }, 200);
    });
    
    console.log('完整购买流程处理器已加载');
}