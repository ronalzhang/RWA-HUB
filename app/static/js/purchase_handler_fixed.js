/**
 * 修复版购买处理器 - 使用模拟交易流程
 */

// 防止重复初始化
if (window.purchaseHandlerFixedInitialized) {
    console.warn('Fixed purchase handler already initialized, skipping...');
} else {
    window.purchaseHandlerFixedInitialized = true;

    // 购买流程管理器
    class FixedPurchaseFlowManager {
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

        // 步骤1：创建购买交易
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

                    // 步骤2：模拟签名和确认交易
                    return await this.simulateSignAndConfirmTransaction();
                } else {
                    throw new Error(data.message || '创建交易失败');
                }
            } catch (error) {
                console.error('创建购买交易失败:', error);
                this.showError('创建交易失败', error.message || '请稍后重试');
                return false;
            }
        }

        // 步骤2：模拟签名和确认交易
        async simulateSignAndConfirmTransaction() {
            if (!this.currentTrade) {
                this.showError('系统错误', '没有待处理的交易');
                return false;
            }

            console.log('开始模拟签名交易:', this.currentTrade);

            try {
                // 检查钱包连接
                if (!window.solana || !window.solana.isConnected) {
                    throw new Error('钱包未连接或不可用');
                }

                // 解析交易数据
                let transactionInfo;
                try {
                    const transactionDataStr = atob(this.currentTrade.transactionToSign);
                    transactionInfo = JSON.parse(transactionDataStr);
                    console.log('解析的交易信息:', transactionInfo);
                } catch (parseError) {
                    console.error('解析交易数据失败:', parseError);
                    throw new Error('无效的交易数据格式');
                }

                // 显示交易确认信息
                const confirmMessage = `
                    <div style="text-align: left;">
                        <h4>确认交易详情：</h4>
                        <p><strong>代币:</strong> ${transactionInfo.token_symbol}</p>
                        <p><strong>金额:</strong> ${transactionInfo.amount} USDC</p>
                        <p><strong>数量:</strong> ${this.currentTrade.amount} 个代币</p>
                        <p><strong>接收方:</strong> ${transactionInfo.to_address.substring(0, 12)}...</p>
                        <br>
                        <p style="color: #666; font-size: 14px;">
                            <i class="fas fa-info-circle"></i> 
                            这是一个模拟交易，用于演示购买流程
                        </p>
                    </div>
                `;

                // 使用SweetAlert显示确认对话框
                if (typeof Swal !== 'undefined') {
                    const result = await Swal.fire({
                        title: '确认购买交易',
                        html: confirmMessage,
                        icon: 'question',
                        showCancelButton: true,
                        confirmButtonText: '确认购买',
                        cancelButtonText: '取消',
                        confirmButtonColor: '#28a745',
                        cancelButtonColor: '#dc3545',
                        width: '500px'
                    });

                    if (!result.isConfirmed) {
                        throw new Error('User rejected the request.');
                    }
                } else {
                    const confirmed = confirm(`确认购买 ${this.currentTrade.amount} 个代币，金额 ${transactionInfo.amount} USDC？`);
                    if (!confirmed) {
                        throw new Error('User rejected the request.');
                    }
                }

                // 生成模拟交易哈希
                const txHash = 'sim_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                console.log('生成模拟交易哈希:', txHash);

                // 模拟交易处理延迟
                this.showLoading('正在处理交易...');
                await new Promise(resolve => setTimeout(resolve, 2000));

                // 确认交易
                return await this.confirmPurchase(txHash);

            } catch (error) {
                console.error('模拟签名交易失败:', error);
                if (error.message.includes('User rejected')) {
                    this.showError('交易取消', '您取消了交易');
                } else {
                    this.showError('交易失败', error.message || '处理交易时发生错误');
                }
                return false;
            }
        }

        // 步骤3：确认购买交易
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
                        `您已成功购买 ${this.currentTrade.amount} 个代币\n交易哈希: ${txHash}`,
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
    window.fixedPurchaseFlowManager = new FixedPurchaseFlowManager();

    // 初始化购买按钮事件监听器
    function initializeFixedPurchaseButton() {
        const buyButton = document.getElementById('buy-button');
        if (buyButton) {
            console.log('设置修复版购买按钮事件监听器');

            // 清除可能存在的事件监听器
            const newButton = buyButton.cloneNode(true);
            buyButton.parentNode.replaceChild(newButton, buyButton);

            newButton.addEventListener('click', function (event) {
                event.preventDefault();
                event.stopPropagation();

                console.log('修复版购买按钮被点击');

                // 检查钱包连接
                const walletAddress = window.fixedPurchaseFlowManager.getWalletAddress();
                console.log('钱包地址:', walletAddress);

                if (!walletAddress) {
                    window.fixedPurchaseFlowManager.showError('钱包未连接', '请先连接您的钱包再进行购买');
                    return;
                }

                // 获取购买数量
                const amountInput = document.getElementById('purchase-amount');
                const amount = parseInt(amountInput?.value || 0);
                console.log('购买数量:', amount);

                if (!amount || amount <= 0) {
                    window.fixedPurchaseFlowManager.showError('输入错误', '请输入有效的购买数量');
                    amountInput?.focus();
                    return;
                }

                // 获取资产ID
                const assetId = document.querySelector('meta[name="asset-id"]')?.content ||
                    document.querySelector('[data-asset-id]')?.getAttribute('data-asset-id') ||
                    window.ASSET_CONFIG?.id;
                console.log('资产ID:', assetId);

                if (!assetId) {
                    window.fixedPurchaseFlowManager.showError('系统错误', '无法获取资产信息');
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
                            window.fixedPurchaseFlowManager.initiatePurchase(parseInt(assetId), amount);
                        }
                    });
                } else {
                    const confirmed = confirm(`您确定要购买 ${amount} 个代币吗？`);
                    if (confirmed) {
                        window.fixedPurchaseFlowManager.initiatePurchase(parseInt(assetId), amount);
                    }
                }
            });

            console.log('修复版购买按钮事件监听器设置完成');
            return true;
        } else {
            console.warn('购买按钮不存在');
            return false;
        }
    }

    // DOM加载完成后初始化购买按钮
    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(function () {
            if (!initializeFixedPurchaseButton()) {
                // 如果首次初始化失败，重试几次
                let retryCount = 0;
                const retryInterval = setInterval(function () {
                    retryCount++;
                    console.log(`重试初始化修复版购买按钮 (${retryCount}/5)`);
                    if (initializeFixedPurchaseButton() || retryCount >= 5) {
                        clearInterval(retryInterval);
                    }
                }, 500);
            }
        }, 200);
    });

    // 也在window.load事件中尝试初始化，确保所有资源都已加载
    window.addEventListener('load', function () {
        setTimeout(function () {
            if (!document.getElementById('buy-button')?.onclick) {
                console.log('window.load事件中重新初始化修复版购买按钮');
                initializeFixedPurchaseButton();
            }
        }, 100);
    });

    console.log('修复版购买流程处理器已加载');
}