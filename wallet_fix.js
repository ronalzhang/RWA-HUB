/**
 * 钱包状态和购买按钮状态修复脚本
 * 解决wallet.js和detail.html中的函数冲突问题
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('*** 钱包状态修复脚本已加载 ***');
    
    // 等待所有js加载完毕
    setTimeout(function() {
        console.log('开始执行钱包状态修复...');
        
        // 统一的购买按钮状态更新函数
        function updateBuyButtonState() {
            console.log('统一购买按钮状态更新函数被调用');
            
            // 获取购买按钮
            const buyButton = document.getElementById('buy-button');
            if (!buyButton) {
                console.warn('找不到购买按钮元素，无法更新状态');
                return;
            }
            
            // 全面检查钱包连接状态
            let isConnected = false;
            
            // 检查window.walletState
            if (window.walletState && (window.walletState.isConnected || window.walletState.connected || window.walletState.address)) {
                isConnected = true;
            }
            
            // 检查window.wallet对象
            if (!isConnected && window.wallet && (
                window.wallet.connected ||
                window.wallet.getAddress && window.wallet.getAddress() ||
                window.wallet.getConnectionStatus && window.wallet.getConnectionStatus())
            ) {
                isConnected = true;
            }
            
            // 检查全局地址变量
            if (!isConnected && (window.connectedWalletAddress || window.ethereumAddress || window.solanaAddress)) {
                isConnected = true;
            }
            
            // 记录连接状态
            console.log('钱包连接状态检查结果:', isConnected, {
                'walletState存在': !!window.walletState,
                'wallet存在': !!window.wallet,
                '地址变量存在': !!(window.connectedWalletAddress || window.ethereumAddress || window.solanaAddress)
            });
            
            // 更新按钮状态
            if (isConnected) {
                buyButton.disabled = false;
                buyButton.innerHTML = '<i class="fas fa-shopping-cart me-2"></i>Buy';
                buyButton.removeAttribute('title');
            } else {
                buyButton.disabled = true;
                buyButton.innerHTML = '<i class="fas fa-wallet me-2"></i>Connect Wallet';
                buyButton.title = 'Please connect your wallet first';
            }
            
            // 如果存在分红按钮检查函数，也一并调用
            if (typeof window.checkDividendManagementAccess === 'function') {
                try {
                    window.checkDividendManagementAccess();
                } catch (error) {
                    console.error('分红按钮检查失败:', error);
                }
            }
        }
        
        // 统一的购买处理函数
        async function handleBuy(assetIdOrEvent, amountInput, buyButton, tokenPrice) {
            console.log('统一购买处理函数被调用:', {assetIdOrEvent, amountInput: !!amountInput, buyButton: !!buyButton, tokenPrice});
            
            // 阻止事件默认行为（如果是事件对象）
            if (assetIdOrEvent && assetIdOrEvent.preventDefault) {
                assetIdOrEvent.preventDefault();
            }
            
            // 参数处理
            let assetId;
            
            // 如果第一个参数是事件对象
            if (assetIdOrEvent && assetIdOrEvent.type === 'click') {
                const targetElement = assetIdOrEvent.currentTarget || assetIdOrEvent.target;
                assetId = targetElement.getAttribute('data-asset-id');
                
                // 获取必要元素
                if (!amountInput) {
                    amountInput = document.getElementById('purchase-amount');
                }
                
                if (!buyButton) {
                    buyButton = targetElement;
                }
                
                // 尝试获取代币价格
                if (!tokenPrice) {
                    tokenPrice = parseFloat(targetElement.getAttribute('data-token-price') || '0');
                }
            } else {
                // 直接使用传入的参数
                assetId = assetIdOrEvent;
            }
            
            // 显示加载状态
            if (typeof window.showLoadingState === 'function') {
                window.showLoadingState('正在处理购买请求...');
            }
            
            // 保存按钮原始状态
            const originalButtonText = buyButton ? buyButton.innerHTML : '';
            
            // 设置按钮为加载状态
            if (buyButton) {
                buyButton.disabled = true;
                buyButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 处理中...';
            }
            
            try {
                // 检查钱包连接状态
                const walletConnected = window.walletState && (window.walletState.isConnected || window.walletState.connected) && window.walletState.address;
                
                if (!walletConnected) {
                    console.error('钱包未连接，无法执行购买操作');
                    
                    // 恢复按钮状态
                    if (buyButton) {
                        buyButton.disabled = false;
                        buyButton.innerHTML = originalButtonText;
                    }
                    
                    // 隐藏加载状态
                    if (typeof window.hideLoadingState === 'function') {
                        window.hideLoadingState();
                    }
                    
                    // 显示错误信息
                    if (typeof window.showError === 'function') {
                        window.showError('请先连接钱包');
                    } else {
                        alert('请先连接钱包');
                    }
                    
                    return;
                }
                
                // 钱包地址
                const walletAddress = window.walletState.address;
                
                // 验证必要参数
                if (!amountInput) {
                    throw new Error('找不到购买数量输入框');
                }
                
                // 获取购买数量
                const amount = amountInput.value;
                if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
                    throw new Error('请输入有效的购买数量');
                }
                
                // 格式化为整数
                const cleanAmount = parseInt(amount);
                
                // 准备API请求数据
                const requestData = {
                    asset_id: assetId,
                    amount: cleanAmount,
                    wallet_address: walletAddress
                };
                
                console.log('发送购买准备请求:', requestData);
                
                // 调用API
                const response = await fetch('/api/trades/prepare_purchase', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-Eth-Address': walletAddress,
                        'X-Wallet-Address': walletAddress
                    },
                    body: JSON.stringify(requestData)
                });
                
                if (!response.ok) {
                    let errorMessage = '服务器错误';
                    try {
                        const errorData = await response.json();
                        errorMessage = errorData.error || errorMessage;
                    } catch (e) {
                        // 忽略JSON解析错误
                    }
                    throw new Error(errorMessage);
                }
                
                // 解析API响应
                const data = await response.json();
                
                if (!data.success) {
                    throw new Error(data.error || '准备购买失败');
                }
                
                console.log('购买准备成功:', data);
                
                // 显示确认购买模态框
                const buyModal = new bootstrap.Modal(document.getElementById('buyModal'));
                
                // 填充确认对话框数据
                const modalAssetName = document.getElementById('modalAssetName');
                const modalAmount = document.getElementById('modalAmount');
                const modalPricePerToken = document.getElementById('modalPricePerToken');
                const modalSubtotal = document.getElementById('modalSubtotal');
                const modalFee = document.getElementById('modalFee');
                const modalTotalCost = document.getElementById('modalTotalCost');
                const modalRecipientAddress = document.getElementById('modalRecipientAddress');
                
                if (modalAssetName) modalAssetName.textContent = data.asset_name || document.querySelector('h1, h2').textContent;
                if (modalAmount) modalAmount.textContent = cleanAmount;
                if (modalPricePerToken) modalPricePerToken.textContent = tokenPrice;
                if (modalSubtotal) modalSubtotal.textContent = (cleanAmount * tokenPrice).toFixed(2);
                if (modalFee) modalFee.textContent = data.platform_fee || '0.00';
                if (modalTotalCost) modalTotalCost.textContent = data.total_amount;
                if (modalRecipientAddress) modalRecipientAddress.textContent = data.recipient_address || data.seller_address;
                
                // 存储交易ID和其他必要数据，用于确认时调用
                window.pendingPurchase = {
                    trade_id: data.trade_id,
                    total: data.total_amount,
                    amount: cleanAmount,
                    total_cost: data.total_amount,
                    seller: data.seller_address,
                    recipient_address: data.seller_address || data.recipient_address,
                    platform_fee_basis_points: data.platform_fee_basis_points,
                    contract_address: data.purchase_contract_address
                };
                
                // 显示确认对话框
                buyModal.show();
                
            } catch (error) {
                console.error('购买处理出错:', error);
                
                // 显示错误信息
                if (typeof window.showError === 'function') {
                    window.showError(error.message || '购买处理出错');
                } else {
                    alert(error.message || '购买处理出错');
                }
            } finally {
                // 恢复按钮状态
                if (buyButton) {
                    buyButton.disabled = false;
                    buyButton.innerHTML = originalButtonText;
                }
                
                // 隐藏加载状态
                if (typeof window.hideLoadingState === 'function') {
                    window.hideLoadingState();
                }
            }
        }
        
        // 统一的钱包状态变化处理函数
        function handleWalletStateChange(event) {
            console.log('统一钱包状态变化处理函数被调用:', event.type);
            
            // 立即更新购买按钮状态
            updateBuyButtonState();
            
            // 如果是连接事件，刷新页面资产
            if (event.type === 'walletConnected' || event.type === 'walletStateChanged') {
                // 刷新页面资产数据
                if (typeof window.refreshAssetInfoNow === 'function') {
                    window.refreshAssetInfoNow();
                }
            }
        }
        
        // 保存原始函数以便恢复
        const originalUpdateBuyButtonState = window.updateBuyButtonState;
        const originalHandleBuy = window.handleBuy;
        
        // 替换全局函数
        window.updateBuyButtonState = updateBuyButtonState;
        window.handleBuy = handleBuy;
        
        // 注册钱包状态变化事件
        const walletEvents = [
            'walletConnected', 
            'walletDisconnected', 
            'walletStateChanged', 
            'balanceUpdated',
            'addressChanged'
        ];
        
        walletEvents.forEach(function(eventName) {
            window.addEventListener(eventName, handleWalletStateChange);
            console.log(`已注册${eventName}事件监听器`);
        });
        
        // 初始更新按钮状态
        updateBuyButtonState();
        
        // 每5秒自动检查一次状态，确保UI始终保持同步
        setInterval(updateBuyButtonState, 5000);
        
        console.log('钱包状态修复完成');
    }, 2000); // 延迟2秒执行，确保所有脚本已加载
}); 