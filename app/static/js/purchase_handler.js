/**
 * 统一的购买处理器 - 资产详情页面
 * 避免重复事件监听器和冲突
 */

// 防止重复初始化
if (window.purchaseHandlerInitialized) {
    console.warn('Purchase handler already initialized, skipping...');
} else {
    window.purchaseHandlerInitialized = true;
    
    // 等待DOM和其他脚本加载完成
    function initializePurchaseHandler() {
        console.log('初始化购买处理器...');
        
        const buyButton = document.getElementById('buy-button');
        if (!buyButton) {
            console.warn('购买按钮不存在，可能是资产未部署或页面结构不同');
            return;
        }

        // 清除可能存在的旧事件监听器
        const newButton = buyButton.cloneNode(true);
        buyButton.parentNode.replaceChild(newButton, buyButton);
        
        // 添加新的事件监听器
        newButton.addEventListener('click', handlePurchaseClick);
        console.log('购买按钮事件监听器已设置');
    }

    // 购买按钮点击处理函数
    function handlePurchaseClick(event) {
        event.preventDefault();
        event.stopPropagation();
        
        console.log('购买按钮被点击');
        
        // 检查钱包连接状态
        const walletConnected = checkWalletConnection();
        if (!walletConnected) {
            return;
        }

        // 获取购买参数
        const purchaseParams = getPurchaseParams();
        if (!purchaseParams) {
            return;
        }

        // 显示确认对话框
        showPurchaseConfirmation(purchaseParams);
    }

    // 检查钱包连接
    function checkWalletConnection() {
        // 多种方式检查钱包连接状态
        const walletAddress = getWalletAddress();
        
        if (!walletAddress) {
            showError('请先连接您的钱包再进行购买');
            // 尝试触发钱包连接
            if (typeof window.connectWallet === 'function') {
                window.connectWallet();
            }
            return false;
        }
        
        console.log('钱包已连接:', walletAddress);
        return true;
    }

    // 获取钱包地址的统一方法
    function getWalletAddress() {
        // 按优先级检查各种钱包状态
        if (window.walletState && window.walletState.address) {
            return window.walletState.address;
        }
        
        if (localStorage.getItem('walletAddress')) {
            return localStorage.getItem('walletAddress');
        }
        
        if (sessionStorage.getItem('walletAddress')) {
            return sessionStorage.getItem('walletAddress');
        }
        
        // 检查Phantom钱包
        if (window.solana && window.solana.publicKey) {
            return window.solana.publicKey.toString();
        }
        
        // 检查以太坊钱包
        if (window.ethereum && window.ethereum.selectedAddress) {
            return window.ethereum.selectedAddress;
        }
        
        return null;
    }

    // 获取购买参数
    function getPurchaseParams() {
        const amountInput = document.getElementById('purchase-amount');
        const amount = parseInt(amountInput?.value || 0);
        
        if (!amount || amount <= 0) {
            showError('请输入有效的购买数量');
            amountInput?.focus();
            return null;
        }

        // 获取资产信息
        const assetId = document.querySelector('meta[name="asset-id"]')?.content || window.ASSET_CONFIG?.id;
        if (!assetId) {
            showError('资产信息错误，请刷新页面重试');
            return null;
        }

        // 检查剩余供应量
        const remainingSupply = window.ASSET_CONFIG?.remainingSupply || 
                               parseInt(document.querySelector('[data-field="remaining_supply"]')?.textContent?.replace(/,/g, '') || '0');
        
        if (amount > remainingSupply) {
            showError(`购买数量不能超过剩余供应量 (${remainingSupply.toLocaleString()})`);
            amountInput?.focus();
            return null;
        }

        // 计算总价
        const tokenPrice = window.ASSET_CONFIG?.tokenPrice || 
                          parseFloat(document.querySelector('[data-token-price]')?.dataset.tokenPrice || '0');
        const totalPrice = amount * tokenPrice;

        return {
            assetId: parseInt(assetId),
            amount: amount,
            tokenPrice: tokenPrice,
            totalPrice: totalPrice,
            remainingSupply: remainingSupply
        };
    }

    // 显示购买确认对话框
    function showPurchaseConfirmation(params) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: '确认购买',
                html: `
                    <div class="text-start">
                        <p><strong>购买数量:</strong> ${params.amount.toLocaleString()} 个代币</p>
                        <p><strong>单价:</strong> ${params.tokenPrice} USDC</p>
                        <p><strong>总价:</strong> ${params.totalPrice.toFixed(2)} USDC</p>
                        <hr>
                        <p class="text-muted small">请确认您的钱包中有足够的USDC余额</p>
                    </div>
                `,
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: '确认购买',
                cancelButtonText: '取消',
                confirmButtonColor: '#007bff',
                cancelButtonColor: '#6c757d'
            }).then((result) => {
                if (result.isConfirmed) {
                    executePurchase(params);
                }
            });
        } else {
            // 如果没有SweetAlert，使用原生确认对话框
            const confirmed = confirm(`确认购买 ${params.amount} 个代币，总价 ${params.totalPrice.toFixed(2)} USDC？`);
            if (confirmed) {
                executePurchase(params);
            }
        }
    }

    // 执行购买
    function executePurchase(params) {
        console.log('开始执行购买:', params);
        
        // 检查是否有完整购买流程
        if (window.completePurchaseFlow && typeof window.completePurchaseFlow.initiatePurchase === 'function') {
            console.log('使用完整购买流程');
            window.completePurchaseFlow.initiatePurchase(params.assetId, params.amount);
        } else if (typeof window.handlePurchaseClick === 'function') {
            console.log('使用备用购买处理器');
            window.handlePurchaseClick();
        } else {
            console.error('没有找到可用的购买处理器');
            showError('购买功能暂时不可用，请刷新页面重试');
        }
    }

    // 显示错误信息
    function showError(message) {
        console.error('购买错误:', message);
        
        // 尝试使用SweetAlert显示错误
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: '购买失败',
                text: message,
                icon: 'error',
                confirmButtonText: '确定'
            });
        } else {
            // 尝试使用页面上的错误显示区域
            const errorDiv = document.getElementById('buy-error');
            if (errorDiv) {
                errorDiv.textContent = message;
                errorDiv.style.display = 'block';
                setTimeout(() => {
                    errorDiv.style.display = 'none';
                }, 5000);
            } else {
                // 最后使用alert
                alert(message);
            }
        }
    }

    // 初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializePurchaseHandler);
    } else {
        // DOM已经加载完成，延迟一点执行以确保其他脚本也加载完成
        setTimeout(initializePurchaseHandler, 100);
    }

    console.log('购买处理器模块已加载');
}



