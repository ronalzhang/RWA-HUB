/**
 * 简化版购买处理器 - 确保可靠执行
 */

console.log('开始加载简化购买处理器...');

// 立即执行的函数，确保代码运行
(function() {
    'use strict';
    
    console.log('简化购买处理器开始初始化');
    
    // 购买流程管理器
    class SimplePurchaseManager {
        constructor() {
            this.isProcessing = false;
            console.log('SimplePurchaseManager 已创建');
        }
        
        // 获取钱包地址
        getWalletAddress() {
            const address = window.walletState?.address || 
                           localStorage.getItem('walletAddress') || 
                           localStorage.getItem('eth_address');
            console.log('获取钱包地址:', address);
            return address;
        }
        

        
        // 显示错误
        showError(title, message) {
            console.error(`错误: ${title} - ${message}`);
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
        
        // 显示成功
        showSuccess(title, message) {
            console.log(`成功: ${title} - ${message}`);
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: title,
                    text: message,
                    icon: 'success',
                    confirmButtonText: '确定'
                });
            } else {
                alert(`${title}: ${message}`);
            }
        }
        
        // 处理购买点击
        async handlePurchaseClick(event) {
            console.log('=== 购买按钮被点击 ===');
            console.log('事件详情:', {
                type: event.type,
                target: event.target.id,
                timestamp: new Date().toISOString()
            });
            
            if (this.isProcessing) {
                console.warn('购买流程正在进行中');
                return;
            }
            
            // 检查钱包
            const walletAddress = this.getWalletAddress();
            if (!walletAddress) {
                this.showError('钱包未连接', '请先连接您的钱包再进行购买');
                return;
            }
            
            // 获取购买数量
            const amountInput = document.getElementById('purchase-amount');
            const amount = parseInt(amountInput?.value || 0);
            console.log('购买数量:', amount);
            
            if (!amount || amount <= 0) {
                this.showError('输入错误', '请输入有效的购买数量');
                amountInput?.focus();
                return;
            }
            
            // 获取资产ID
            const assetId = document.querySelector('meta[name="asset-id"]')?.content || 
                           document.querySelector('[data-asset-id]')?.getAttribute('data-asset-id') ||
                           window.ASSET_CONFIG?.id;
            console.log('资产ID:', assetId);
            
            if (!assetId) {
                this.showError('系统错误', '无法获取资产信息');
                return;
            }
            
            // 显示确认对话框
            console.log('显示确认对话框...');
            const confirmed = await this.showConfirmDialog(amount);
            console.log('确认对话框结果:', confirmed);
            
            if (!confirmed) {
                console.log('用户取消购买');
                return;
            }
            
            console.log('用户确认购买，开始购买流程...');
            // 开始购买流程
            await this.startPurchaseFlow(parseInt(assetId), amount, walletAddress);
        }
        
        // 显示确认对话框
        async showConfirmDialog(amount) {
            console.log('showConfirmDialog被调用，数量:', amount);
            console.log('SweetAlert可用性:', typeof Swal !== 'undefined');
            
            if (typeof Swal !== 'undefined') {
                console.log('使用SweetAlert显示确认对话框');
                try {
                    const result = await Swal.fire({
                        title: '确认购买',
                        text: `您确定要购买 ${amount} 个代币吗？`,
                        icon: 'question',
                        showCancelButton: true,
                        confirmButtonText: '确认',
                        cancelButtonText: '取消'
                    });
                    console.log('SweetAlert结果:', result);
                    return result.isConfirmed;
                } catch (error) {
                    console.error('SweetAlert错误:', error);
                    return confirm(`您确定要购买 ${amount} 个代币吗？`);
                }
            } else {
                console.log('使用原生confirm对话框');
                return confirm(`您确定要购买 ${amount} 个代币吗？`);
            }
        }
        
        // 开始购买流程
        async startPurchaseFlow(assetId, amount, walletAddress) {
            console.log('开始购买流程:', { assetId, amount, walletAddress });
            this.isProcessing = true;
            
            try {
                // 步骤1: 创建交易
                const createResult = await this.createTrade(assetId, amount, walletAddress);
                if (!createResult.success) {
                    throw new Error(createResult.error?.message || '创建交易失败');
                }
                
                console.log('交易创建成功:', createResult);
                this.showSuccess('购买成功', '交易已创建，正在处理中...');
                
                // 这里可以添加更多步骤，如钱包签名等
                
            } catch (error) {
                console.error('购买流程失败:', error);
                this.showError('购买失败', error.message || '请稍后重试');
            } finally {
                this.isProcessing = false;
            }
        }
        
        // 创建交易
        async createTrade(assetId, amount, walletAddress) {
            console.log('调用创建交易API...');
            
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
            console.log('API响应:', data);
            
            return data;
        }
    }
    
    // 创建全局实例
    window.simplePurchaseManager = new SimplePurchaseManager();
    console.log('全局购买管理器已创建');
    
    // 初始化购买按钮
    function initPurchaseButton() {
        console.log('开始初始化购买按钮...');
        
        const buyButton = document.getElementById('buy-button');
        if (!buyButton) {
            console.warn('购买按钮不存在');
            return false;
        }
        
        console.log('找到购买按钮，绑定事件...');
        
        // 移除可能存在的旧事件监听器
        const newButton = buyButton.cloneNode(true);
        buyButton.parentNode.replaceChild(newButton, buyButton);
        
        // 绑定新的事件监听器
        newButton.addEventListener('click', async function(event) {
            event.preventDefault();
            event.stopPropagation();
            await window.simplePurchaseManager.handlePurchaseClick(event);
        });
        
        console.log('购买按钮初始化成功');
        return true;
    }
    
    // 多种方式确保初始化
    function ensureInitialization() {
        console.log('确保购买按钮初始化...');
        
        if (initPurchaseButton()) {
            console.log('购买按钮初始化成功');
            return;
        }
        
        // 如果失败，重试几次
        let retryCount = 0;
        const maxRetries = 5;
        
        const retryInterval = setInterval(() => {
            retryCount++;
            console.log(`重试初始化购买按钮 (${retryCount}/${maxRetries})`);
            
            if (initPurchaseButton() || retryCount >= maxRetries) {
                clearInterval(retryInterval);
                if (retryCount >= maxRetries) {
                    console.error('购买按钮初始化失败，已达到最大重试次数');
                }
            }
        }, 500);
    }
    
    // DOM加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM加载完成，开始初始化');
            setTimeout(ensureInitialization, 100);
        });
    } else {
        console.log('DOM已加载，立即初始化');
        setTimeout(ensureInitialization, 100);
    }
    
    // 备用初始化
    window.addEventListener('load', function() {
        console.log('页面完全加载，备用初始化');
        setTimeout(() => {
            if (!document.getElementById('buy-button')?.onclick) {
                console.log('备用初始化触发');
                ensureInitialization();
            }
        }, 200);
    });
    
    // 标记初始化完成
    window.simplePurchaseHandlerLoaded = true;
    console.log('简化购买处理器加载完成');
    
})();

console.log('简化购买处理器脚本执行完成');