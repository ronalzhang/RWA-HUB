/**
 * 统一购买处理脚本
 * 支持多语言界面
 * 版本：1.0.0
 */

(function() {
    console.log('加载购买处理脚本 v1.0.0');
    
    // 文本资源
    const TEXTS = {
        'zh': {
            processing: 'Processing...',
            walletNotConnected: 'Please connect your wallet first',
            missingAmountInput: 'Purchase amount input not found',
            invalidAmount: 'Please enter a valid purchase amount',
            serverError: 'Server error',
            prepareFailed: 'Failed to prepare purchase',
            purchaseError: 'Error processing purchase'
        },
        'en': {
            processing: 'Processing purchase request...',
            walletNotConnected: 'Please connect your wallet first',
            missingAmountInput: 'Purchase amount input not found',
            invalidAmount: 'Please enter a valid purchase amount',
            serverError: 'Server error',
            prepareFailed: 'Failed to prepare purchase',
            purchaseError: 'Error processing purchase'
        }
    };
    
    // 获取当前语言
    function getCurrentLanguage() {
        const htmlLang = document.documentElement.lang || 'en';
        const langCookie = document.cookie.split(';').find(c => c.trim().startsWith('language='));
        const cookieLang = langCookie ? langCookie.split('=')[1].trim() : null;
        
        return (cookieLang || htmlLang).startsWith('zh') ? 'zh' : 'en';
    }
    
    // 获取本地化文本
    function getText(key) {
        const lang = getCurrentLanguage();
        return (TEXTS[lang] && TEXTS[lang][key]) || TEXTS['en'][key];
    }
    
    /**
     * 统一的购买处理函数
     */
    async function handleBuy(assetIdOrEvent, amountInput, buyButton, tokenPrice) {
        console.log('全局购买处理函数被调用:', {assetIdOrEvent, amountInput: !!amountInput, buyButton: !!buyButton, tokenPrice});
        
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
            window.showLoadingState(getText('processing'));
        }
        
        // 保存按钮原始状态
        const originalButtonText = buyButton ? buyButton.innerHTML : '';
        
        // 设置按钮为加载状态
        if (buyButton) {
            buyButton.disabled = true;
            buyButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ' + getText('processing');
        }
        
        try {
            // 检查钱包连接状态
            let walletConnected = false;
            let walletAddress = '';
            
            // 检查window.walletState
            if (window.walletState && (window.walletState.isConnected || window.walletState.connected) && window.walletState.address) {
                walletConnected = true;
                walletAddress = window.walletState.address;
            }
            
            // 检查localStorage
            if (!walletConnected) {
                walletAddress = localStorage.getItem('walletAddress');
                if (walletAddress) {
                    walletConnected = true;
                }
            }
            
            if (!walletConnected) {
                console.error('钱包未连接，无法执行购买操作');
                throw new Error(getText('walletNotConnected'));
            }
            
            // 验证必要参数
            if (!amountInput) {
                throw new Error(getText('missingAmountInput'));
            }
            
            // 获取购买数量
            const amount = amountInput.value;
            if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
                throw new Error(getText('invalidAmount'));
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
                let errorMessage = getText('serverError');
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
                throw new Error(data.error || getText('prepareFailed'));
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
                window.showError(error.message || getText('purchaseError'));
            } else {
                alert(error.message || getText('purchaseError'));
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
    
    // 导出全局函数
    window.handleBuy = handleBuy;
    
    // 监听语言变化事件
    window.addEventListener('languageChanged', () => {
        console.log('语言已变更，更新购买处理UI');
    });
    
    // 触发加载完成事件
    document.dispatchEvent(new Event('buyHandlerLoaded'));
})(); 