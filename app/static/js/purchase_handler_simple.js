/**
 * 简化的购买按钮处理器 - 专门解决初始化问题
 */

console.log('开始加载简化购买处理器...');

// 防止重复初始化
if (!window.simplePurchaseHandlerLoaded) {
    window.simplePurchaseHandlerLoaded = true;
    
    console.log('简化购买处理器开始初始化');
    
    // 简单的购买处理函数
    function handlePurchaseClick(event) {
        event.preventDefault();
        event.stopPropagation();
        
        console.log('=== 购买按钮被点击 ===');
        console.log('事件详情:', {
            type: event.type,
            target: event.target.id,
            timestamp: new Date().toISOString()
        });
        
        // 获取购买数量
        const amountInput = document.getElementById('purchase-amount');
        const amount = parseInt(amountInput?.value || 0);
        console.log('购买数量:', amount);
        
        if (!amount || amount <= 0) {
            alert('请输入有效的购买数量');
            return;
        }
        
        // 获取资产ID
        const assetId = document.querySelector('meta[name="asset-id"]')?.content || 
                       document.querySelector('[data-asset-id]')?.getAttribute('data-asset-id') ||
                       window.ASSET_CONFIG?.id;
        console.log('资产ID:', assetId);
        
        if (!assetId) {
            alert('无法获取资产信息');
            return;
        }
        
        // 检查钱包
        const walletAddress = localStorage.getItem('walletAddress') || 
                             localStorage.getItem('eth_address') ||
                             window.walletState?.address;
        console.log('钱包地址:', walletAddress);
        
        if (!walletAddress) {
            alert('请先连接您的钱包再进行购买');
            return;
        }
        
        // 显示确认
        const confirmed = confirm(`您确定要购买 ${amount} 个代币吗？`);
        if (!confirmed) {
            console.log('用户取消购买');
            return;
        }
        
        // 开始购买流程
        console.log('开始购买流程...');
        startPurchaseFlow(assetId, amount, walletAddress);
    }
    
    // 购买流程
    async function startPurchaseFlow(assetId, amount, walletAddress) {
        try {
            console.log('调用创建交易API...');
            
            const response = await fetch('/api/v2/trades/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': walletAddress
                },
                body: JSON.stringify({
                    asset_id: parseInt(assetId),
                    amount: amount
                })
            });
            
            console.log('API响应状态:', response.status);
            const data = await response.json();
            console.log('API响应数据:', data);
            
            if (data.success) {
                alert('交易创建成功！（这是简化版本，实际需要钱包签名）');
                console.log('交易创建成功，交易ID:', data.trade_id);
            } else {
                alert('交易创建失败: ' + (data.error?.message || '未知错误'));
                console.error('交易创建失败:', data.error);
            }
            
        } catch (error) {
            console.error('购买流程异常:', error);
            alert('购买过程中发生错误: ' + error.message);
        }
    }
    
    // 初始化购买按钮
    function initPurchaseButton() {
        const buyButton = document.getElementById('buy-button');
        if (buyButton) {
            console.log('找到购买按钮，绑定事件监听器');
            
            // 移除可能存在的旧监听器
            buyButton.removeEventListener('click', handlePurchaseClick);
            
            // 添加新的监听器
            buyButton.addEventListener('click', handlePurchaseClick);
            
            console.log('购买按钮事件监听器绑定成功');
            return true;
        } else {
            console.warn('未找到购买按钮 (id=buy-button)');
            return false;
        }
    }
    
    // DOM加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM加载完成，初始化购买按钮');
            setTimeout(initPurchaseButton, 100);
        });
    } else {
        console.log('DOM已加载，立即初始化购买按钮');
        setTimeout(initPurchaseButton, 100);
    }
    
    // 备用初始化
    window.addEventListener('load', function() {
        console.log('页面完全加载，检查购买按钮');
        setTimeout(function() {
            const buyButton = document.getElementById('buy-button');
            if (buyButton && !buyButton.onclick) {
                console.log('备用初始化购买按钮');
                initPurchaseButton();
            }
        }, 200);
    });
    
    // 导出到全局作用域以便调试
    window.debugPurchase = {
        handlePurchaseClick: handlePurchaseClick,
        initPurchaseButton: initPurchaseButton,
        startPurchaseFlow: startPurchaseFlow
    };
    
    console.log('简化购买处理器初始化完成');
}

console.log('简化购买处理器加载完成');