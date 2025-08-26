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
        
        // 检查钱包连接状态
        checkWalletConnection() {
            const address = this.getWalletAddress();
            const isConnected = !!address;
            
            console.log('检查钱包连接状态:', isConnected, address);
            
            // 更新UI状态
            this.updateWalletUI(isConnected, address);
            
            return isConnected;
        }
        
        // 更新钱包UI状态
        updateWalletUI(isConnected, address) {
            const walletDisconnected = document.getElementById('wallet-disconnected');
            const walletConnected = document.getElementById('wallet-connected');
            const connectedAddress = document.getElementById('connected-address');
            const connectButton = document.getElementById('connect-wallet-button');
            const buyButton = document.getElementById('buy-button');
            
            if (isConnected && address) {
                // 钱包已连接
                if (walletDisconnected) walletDisconnected.style.display = 'none';
                if (walletConnected) walletConnected.style.display = 'block';
                if (connectedAddress) connectedAddress.textContent = `${address.slice(0, 6)}...${address.slice(-4)}`;
                if (connectButton) connectButton.style.display = 'none';
                if (buyButton) buyButton.style.display = 'block';
            } else {
                // 钱包未连接
                if (walletDisconnected) walletDisconnected.style.display = 'block';
                if (walletConnected) walletConnected.style.display = 'none';
                if (connectButton) connectButton.style.display = 'block';
                if (buyButton) buyButton.style.display = 'none';
            }
        }
        
        // 连接钱包
        async connectWallet() {
            console.log('尝试连接钱包...');
            
            try {
                // 检查是否有Phantom钱包
                if (window.solana && window.solana.isPhantom) {
                    console.log('检测到Phantom钱包');
                    const response = await window.solana.connect();
                    const address = response.publicKey.toString();
                    
                    // 保存地址
                    localStorage.setItem('walletAddress', address);
                    localStorage.setItem('eth_address', address);
                    
                    // 更新钱包状态
                    if (window.walletState) {
                        window.walletState.address = address;
                        window.walletState.connected = true;
                    }
                    
                    console.log('Phantom钱包连接成功:', address);
                    this.updateWalletUI(true, address);
                    
                    this.showSuccess('钱包连接成功', `已连接到钱包: ${address.slice(0, 6)}...${address.slice(-4)}`);
                    return true;
                }
                
                // 检查是否有MetaMask或其他以太坊钱包
                if (window.ethereum) {
                    console.log('检测到以太坊钱包');
                    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                    const address = accounts[0];
                    
                    // 保存地址
                    localStorage.setItem('walletAddress', address);
                    localStorage.setItem('eth_address', address);
                    
                    // 更新钱包状态
                    if (window.walletState) {
                        window.walletState.address = address;
                        window.walletState.connected = true;
                    }
                    
                    console.log('以太坊钱包连接成功:', address);
                    this.updateWalletUI(true, address);
                    
                    this.showSuccess('钱包连接成功', `已连接到钱包: ${address.slice(0, 6)}...${address.slice(-4)}`);
                    return true;
                }
                
                // 没有检测到钱包
                this.showError('未检测到钱包', '请安装Phantom钱包或MetaMask钱包');
                return false;
                
            } catch (error) {
                console.error('连接钱包失败:', error);
                this.showError('连接失败', '钱包连接被取消或发生错误');
                return false;
            }
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
            const confirmed = await this.showConfirmDialog(amount);
            if (!confirmed) {
                console.log('用户取消购买');
                return;
            }
            
            // 开始购买流程
            await this.startPurchaseFlow(parseInt(assetId), amount, walletAddress);
        }
        
        // 显示确认对话框
        async showConfirmDialog(amount) {
            if (typeof Swal !== 'undefined') {
                const result = await Swal.fire({
                    title: '确认购买',
                    text: `您确定要购买 ${amount} 个代币吗？`,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: '确认',
                    cancelButtonText: '取消'
                });
                return result.isConfirmed;
            } else {
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
        console.log('开始初始化购买按钮和钱包连接...');
        
        // 初始化钱包连接按钮
        const connectButton = document.getElementById('connect-wallet-button');
        if (connectButton) {
            console.log('找到钱包连接按钮，绑定事件...');
            connectButton.addEventListener('click', async function(event) {
                event.preventDefault();
                event.stopPropagation();
                await window.simplePurchaseManager.connectWallet();
            });
        }
        
        // 初始化购买按钮
        const buyButton = document.getElementById('buy-button');
        if (!buyButton) {
            console.warn('购买按钮不存在');
            // 即使购买按钮不存在，也要检查钱包状态
            window.simplePurchaseManager.checkWalletConnection();
            return !!connectButton; // 如果有连接按钮就算成功
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
        
        // 检查钱包连接状态
        window.simplePurchaseManager.checkWalletConnection();
        
        console.log('购买按钮和钱包连接初始化成功');
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