// 钱包状态管理
const walletState = {
    address: null,
    isConnected: false,
    isAdmin: false,
    eventCallbacks: new Set(), // 用于存储状态变化的回调函数
    connecting: false,
    
    // 初始化钱包状态
    async init() {
        console.log('Initializing wallet state...');
        if (!window.ethereum) {
            console.warn('MetaMask not installed');
            return;
        }

        try {
            // 设置事件监听
            this.setupEventListeners();
            
            // 检查本地存储状态
            const shouldConnect = localStorage.getItem('walletConnected') === 'true';
            
            if (!shouldConnect) {
                console.log('Wallet was previously disconnected');
                // 确保完全断开状态
                await this.disconnect(true);
                return;
            }
            
            // 检查当前是否有账户连接
            const accounts = await window.ethereum.request({ 
                method: 'eth_accounts'
            });
            
            // 只有当真实有账户连接时才恢复连接
            if (accounts && accounts.length > 0) {
                // 验证连接状态
                try {
                    const chainId = await window.ethereum.request({ method: 'eth_chainId' });
                    if (!chainId) {
                        throw new Error('Unable to get chain ID');
                    }
                    this.address = accounts[0].toLowerCase();
                    this.isConnected = true;
                    await this.checkIsAdmin();
                    this.updateUI();
                    this.notifyStateChange();
                } catch (error) {
                    console.error('Failed to verify connection:', error);
                    await this.disconnect(true);
                }
            } else {
                // 如果没有实际连接的账户，清除存储的状态
                await this.disconnect(true);
            }
        } catch (error) {
            console.error('Failed to initialize wallet state:', error);
            // 发生错误时也清除存储的状态
            await this.disconnect(true);
        }
    },

    // 支持的网络配置
    SUPPORTED_NETWORKS: {
        1: {
            name: 'Mainnet',
            currency: 'ETH',
            explorerUrl: 'https://etherscan.io',
            chainId: '0x1',
            rpcUrls: ['https://mainnet.infura.io/v3/'],
            nativeCurrency: {
                name: 'ETH',
                symbol: 'ETH',
                decimals: 18
            }
        },
        5: {
            name: 'Goerli',
            currency: 'ETH',
            explorerUrl: 'https://goerli.etherscan.io',
            chainId: '0x5',
            rpcUrls: ['https://goerli.infura.io/v3/'],
            nativeCurrency: {
                name: 'ETH',
                symbol: 'ETH',
                decimals: 18
            }
        }
    },

    // 检查并切换网络
    async checkAndSwitchNetwork(chainId) {
        const networkInfo = this.SUPPORTED_NETWORKS[parseInt(chainId, 16)];
        if (!networkInfo) {
            // 如果是不支持的网络，尝试切换到主网
            try {
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: this.SUPPORTED_NETWORKS[1].chainId }]
                });
                return true;
            } catch (switchError) {
                if (switchError.code === 4902) {
                    try {
                        await window.ethereum.request({
                            method: 'wallet_addEthereumChain',
                            params: [{
                                chainId: this.SUPPORTED_NETWORKS[1].chainId,
                                chainName: this.SUPPORTED_NETWORKS[1].name,
                                rpcUrls: this.SUPPORTED_NETWORKS[1].rpcUrls,
                                nativeCurrency: this.SUPPORTED_NETWORKS[1].nativeCurrency,
                                blockExplorerUrls: [this.SUPPORTED_NETWORKS[1].explorerUrl]
                            }]
                        });
                        return true;
                    } catch (addError) {
                        console.error('Failed to add network:', addError);
                        throw new Error('请手动切换到支持的网络');
                    }
                }
                console.error('Failed to switch network:', switchError);
                throw new Error('请手动切换到支持的网络');
            }
        }
        return true;
    },

    // 设置事件监听器
    setupEventListeners() {
        if (!window.ethereum) return;

        // 账户变更事件
        window.ethereum.on('accountsChanged', async (accounts) => {
            console.log('Accounts changed:', accounts);
            if (accounts.length === 0) {
                await this.disconnect();
            } else {
                // 验证新账户连接状态
                try {
                    const chainId = await window.ethereum.request({ method: 'eth_chainId' });
                    if (!chainId) {
                        throw new Error('Unable to get chain ID');
                    }
                    
                    // 检查并切换网络
                    await this.checkAndSwitchNetwork(chainId);

                    this.address = accounts[0].toLowerCase();
                    this.isConnected = true;
                    localStorage.setItem('walletConnected', 'true');
                    await this.checkIsAdmin();
                    this.updateUI();
                    this.notifyStateChange();
                } catch (error) {
                    console.error('Failed to verify new account:', error);
                    await this.disconnect();
                    showError(error.message);
                }
            }
        });

        // 断开连接事件
        window.ethereum.on('disconnect', async (error) => {
            console.log('Wallet disconnected', error);
            await this.disconnect();
        });

        // 链变更事件
        window.ethereum.on('chainChanged', async (chainId) => {
            console.log('Chain changed:', chainId);
            try {
                await this.checkAndSwitchNetwork(chainId);
            } catch (error) {
                console.error('Network switch failed:', error);
                showError(error.message);
                await this.disconnect();
                return;
            }
            window.location.reload();
        });
    },
    
    // 检查网络连接
    async checkNetworkConnectivity() {
        try {
            // 尝试连接以太坊主网
            const response = await fetch('https://api.etherscan.io/api', {
                method: 'HEAD',
                mode: 'no-cors'
            });
            return true;
        } catch (error) {
            console.warn('Network connectivity check failed:', error);
            return false;
        }
    },

    // 检查是否正在处理连接请求
    async checkProcessingState() {
        try {
            // 首先检查网络连接
            const isNetworkConnected = await this.checkNetworkConnectivity();
            if (!isNetworkConnected) {
                throw new Error('无法连接到以太坊网络，请检查网络连接或使用VPN');
            }

            // 检查 MetaMask 是否已解锁
            const isUnlocked = await window.ethereum._metamask.isUnlocked();
            if (!isUnlocked) {
                return true; // MetaMask 未解锁，需要用户操作
            }

            // 检查是否有正在处理的请求
            try {
                await window.ethereum.request({
                    method: 'eth_accounts'
                });
                return false;
            } catch (error) {
                if (error.code === -32002) {
                    return true;
                }
                return false;
            }
        } catch (error) {
            console.warn('Failed to check processing state:', error);
            if (error.message.includes('VPN')) {
                throw error; // 如果是网络连接问题，直接抛出
            }
            return false;
        }
    },
    
    // 连接钱包
    async connect(showPrompt = true) {
        console.log('Connecting wallet...');
        
        if (!window.ethereum) {
            throw new Error('请安装MetaMask钱包');
        }
        
        // 如果已经连接，直接返回
        if (this.isConnected && this.address) {
            return true;
        }
        
        // 防止重复连接
        if (this.connecting) {
            throw new Error('正在处理连接请求，请稍候...');
        }
        
        this.connecting = true;
        const walletBtn = document.getElementById('walletBtn');
        const walletBtnText = document.getElementById('walletBtnText');
        const originalText = walletBtnText ? walletBtnText.textContent : '连接钱包';
        
        try {
            // 检查是否有正在处理的请求
            try {
                const isProcessing = await this.checkProcessingState();
                if (isProcessing) {
                    // 更新按钮状态
                    if (walletBtnText) {
                        walletBtnText.textContent = '请打开MetaMask...';
                    }
                    if (walletBtn) {
                        walletBtn.disabled = true;
                    }
                    
                    // 等待一段时间后恢复按钮状态
                    setTimeout(() => {
                        if (walletBtnText) {
                            walletBtnText.textContent = originalText;
                        }
                        if (walletBtn) {
                            walletBtn.disabled = false;
                        }
                        this.connecting = false;
                    }, 3000);
                    
                    throw new Error('请打开MetaMask完成操作后重试');
                }
            } catch (error) {
                if (error.message.includes('VPN')) {
                    // 如果是网络连接问题，显示特定的错误信息
                    this.connecting = false;
                    throw error;
                }
            }
            
            // 更新按钮状态
            if (walletBtnText) {
                walletBtnText.textContent = '连接中...';
            }
            if (walletBtn) {
                walletBtn.disabled = true;
            }

            // 先检查并切换网络
            try {
                const chainId = await window.ethereum.request({ method: 'eth_chainId' });
                await this.checkAndSwitchNetwork(chainId);
            } catch (error) {
                if (error.message.includes('网络连接') || error.message.includes('VPN')) {
                    throw error;
                }
                console.error('Network check failed:', error);
                throw new Error('网络连接失败，请检查网络连接或使用VPN');
            }
            
            // 请求连接
            let accounts;
            try {
                accounts = await window.ethereum.request({ 
                    method: showPrompt ? 'eth_requestAccounts' : 'eth_accounts'
                });
            } catch (error) {
                const actualError = error.err || error;
                
                if (actualError.code === 4001) {
                    throw new Error('用户拒绝了连接请求');
                }
                
                if (actualError.code === -32002) {
                    throw new Error('请打开MetaMask完成操作后重试');
                }
                
                if (actualError.message && (
                    actualError.message.includes('网络连接') || 
                    actualError.message.includes('VPN') ||
                    actualError.message.includes('Network Error')
                )) {
                    throw new Error('无法连接到以太坊网络，请检查网络连接或使用VPN');
                }
                
                throw error;
            }
            
            if (accounts && accounts.length > 0) {
                this.address = accounts[0].toLowerCase();
                this.isConnected = true;
                localStorage.setItem('walletConnected', 'true');
                await this.checkIsAdmin();
                this.updateUI();
                this.notifyStateChange();
                
                // 连接成功后关闭钱包菜单
                const walletMenu = document.getElementById('walletMenu');
                if (walletMenu) {
                    walletMenu.classList.remove('show');
                }
                
                return true;
            }
            
            return false;
        } catch (error) {
            // 重置状态
            this.connecting = false;
            this.isConnected = false;
            this.address = null;
            
            // 恢复按钮状态
            if (walletBtnText) {
                walletBtnText.textContent = originalText;
            }
            if (walletBtn) {
                walletBtn.disabled = false;
            }
            
            // 如果是已经处理过的错误，直接抛出
            if (error instanceof Error && error.message) {
                throw error;
            }
            
            // 处理其他未知错误
            console.error('Connection failed:', error);
            throw new Error('连接钱包失败，请重试');
        }
    },
    
    // 断开钱包连接
    async disconnect(silent = false) {
        console.log('Disconnecting wallet...');
        try {
            // 尝试通过 MetaMask 断开连接
            try {
                if (window.ethereum && window.ethereum._metamask) {
                    // 移除所有已授权的账户
                    await window.ethereum.request({
                        method: 'wallet_revokePermissions',
                        params: [{ eth_accounts: {} }]
                    });
                }
            } catch (error) {
                console.warn('Failed to revoke permissions:', error);
            }

            // 清除状态
            this.address = null;
            this.isConnected = false;
            this.isAdmin = false;
            
            // 清除本地存储
            localStorage.removeItem('walletConnected');
            sessionStorage.removeItem('walletAddress');
            
            // 清除所有相关的 cookie
            this.clearState();
            
            // 移除所有事件监听器并重新设置
            if (window.ethereum) {
                window.ethereum.removeAllListeners('accountsChanged');
                window.ethereum.removeAllListeners('disconnect');
                window.ethereum.removeAllListeners('chainChanged');
                this.setupEventListeners();
            }
            
            // 更新 UI
            this.updateUI();
            
            // 只在非静默模式下通知状态变化
            if (!silent) {
                this.notifyStateChange();
            }
            
            // 关闭钱包菜单
            const walletMenu = document.getElementById('walletMenu');
            if (walletMenu) {
                walletMenu.classList.remove('show');
            }
            
            return true;
        } catch (error) {
            console.error('Error during wallet disconnect:', error);
            return false;
        }
    },
    
    // 切换钱包
    async switchWallet() {
        console.log('Switching wallet...');
        try {
            // 请求切换账户
            await window.ethereum.request({
                method: 'wallet_requestPermissions',
                params: [{ eth_accounts: {} }]
            });

            // 获取新的账户
            const accounts = await window.ethereum.request({
                method: 'eth_accounts'
            });

            // 验证新账户
            if (accounts && accounts.length > 0) {
                this.address = accounts[0].toLowerCase();
                this.isConnected = true;
                localStorage.setItem('walletConnected', 'true');
                await this.checkIsAdmin();
                this.updateUI();
                this.notifyStateChange();
                return true;
            } else {
                // 如果没有选择新账户，则断开连接
                await this.disconnect();
                return false;
            }
        } catch (error) {
            console.error('Failed to switch wallet:', error);
            // 如果用户取消或发生错误，保持当前连接状态
            if (error.code === 4001) { // 用户拒绝
                return false;
            }
            // 其他错误则断开连接
            await this.disconnect();
            throw error;
        }
    },
    
    // 更新UI显示
    updateUI() {
        const walletBtn = document.getElementById('walletBtn');
        const walletMenu = document.getElementById('walletMenu');
        const walletBtnText = document.getElementById('walletBtnText');
        const adminEntry = document.getElementById('adminEntry');
        const adminLink = document.getElementById('adminLink');
        
        if (!walletBtn || !walletBtnText) return;
        
        if (this.isConnected && this.address) {
            const shortAddress = `${this.address.substring(0, 6)}...${this.address.substring(38)}`;
            walletBtnText.textContent = shortAddress;
            walletBtn.classList.remove('btn-outline-primary');
            walletBtn.classList.add('btn-primary');
            
            // 更新管理员入口
            if (adminEntry && adminLink) {
                if (this.isAdmin) {
                    adminEntry.classList.remove('d-none');
                    adminLink.href = `/admin?eth_address=${this.address}`;
                } else {
                    adminEntry.classList.add('d-none');
                }
            }
        } else {
            walletBtnText.textContent = '连接钱包';
            walletBtn.classList.remove('btn-primary');
            walletBtn.classList.add('btn-outline-primary');
            if (walletMenu) {
                walletMenu.classList.remove('show');
            }
        }
    },
    
    // 获取连接状态
    getConnectionStatus() {
        return this.isConnected;
    },
    
    // 获取当前钱包地址
    getAddress() {
        return this.address;
    },
    
    // 检查管理员权限
    async checkIsAdmin() {
        if (!this.address) return false;
        
        try {
            const response = await fetch('/api/admin/check', {
                headers: {
                    'X-Eth-Address': this.address
                }
            });
            
            if (!response.ok) {
                throw new Error('检查管理员权限失败');
            }
            
            const data = await response.json();
            this.isAdmin = data.is_admin;
            this.updateUI();
            
            return data.is_admin;
        } catch (error) {
            console.error('Failed to check admin status:', error);
            return false;
        }
    },

    // 注册状态变化回调
    onStateChange(callback) {
        this.eventCallbacks.add(callback);
    },

    // 移除状态变化回调
    offStateChange(callback) {
        this.eventCallbacks.delete(callback);
    },

    // 通知所有注册的回调
    notifyStateChange() {
        const state = {
            address: this.address,
            isConnected: this.isConnected,
            isAdmin: this.isAdmin
        };
        this.eventCallbacks.forEach(callback => callback(state));
    },

    // 清除状态
    clearState() {
        document.cookie = 'eth_address=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    }
};

// 初始化
let walletInitialized = false;
document.addEventListener('DOMContentLoaded', async function() {
    if (walletInitialized) return;
    walletInitialized = true;

    console.log('Initializing wallet...');
    window.walletState = walletState;
    await walletState.init();
    
    // 绑定钱包按钮事件
    const walletBtn = document.getElementById('walletBtn');
    const walletMenu = document.getElementById('walletMenu');
    const switchWalletBtn = document.getElementById('switchWallet');
    const disconnectWalletBtn = document.getElementById('disconnectWallet');
    
    if (walletBtn) {
        walletBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (!window.ethereum) {
                showError('请安装MetaMask钱包');
                return;
            }
            
            if (!walletState.getConnectionStatus()) {
                try {
                    await walletState.connect();
                } catch (error) {
                    showError(error.message);
                }
            } else if (walletMenu) {
                // 切换菜单显示状态
                const isVisible = walletMenu.classList.contains('show');
                if (!isVisible) {
                    // 关闭所有其他下拉菜单
                    document.querySelectorAll('.wallet-menu.show').forEach(el => {
                        if (el !== walletMenu) {
                            el.classList.remove('show');
                        }
                    });
                }
                walletMenu.classList.toggle('show');
            }
        });
    }
    
    // 绑定切换钱包事件
    if (switchWalletBtn) {
        switchWalletBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            try {
                await walletState.switchWallet();
                if (walletMenu) {
                    walletMenu.classList.remove('show');
                }
            } catch (error) {
                showError(error.message);
            }
        });
    }

    // 绑定断开连接事件
    if (disconnectWalletBtn) {
        disconnectWalletBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            try {
                await walletState.disconnect();
                if (walletMenu) {
                    walletMenu.classList.remove('show');
                }
            } catch (error) {
                showError(error.message);
            }
        });
    }
    
    // 点击其他地方关闭菜单
    document.addEventListener('click', (e) => {
        const target = e.target;
        if (walletMenu && walletMenu.classList.contains('show') && 
            !walletBtn.contains(target) && !walletMenu.contains(target)) {
            walletMenu.classList.remove('show');
        }
    });

    // ESC 键关闭菜单
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && walletMenu && walletMenu.classList.contains('show')) {
            walletMenu.classList.remove('show');
        }
    });
});

// 显示错误信息
function showError(message) {
    const errorModal = document.getElementById('errorModal');
    if (errorModal) {
        const errorMessage = document.getElementById('errorMessage');
        if (errorMessage) {
            errorMessage.textContent = message;
        }
        const modal = new bootstrap.Modal(errorModal);
        modal.show();
    } else {
        console.error(message);
        alert(message);
    }
}

// 语言切换函数
window.changeLanguage = function(lang) {
    document.cookie = `language=${lang};path=/;max-age=31536000`;
    window.location.reload();
} 