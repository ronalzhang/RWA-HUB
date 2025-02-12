// 初始化钱包状态
window.walletState = {
    currentAccount: null,
    isConnected: false,
    isAdmin: false,
    permissions: []
};

// 连接钱包
async function connectWallet() {
    try {
        if (!window.ethereum) {
            throw new Error('请安装 MetaMask');
        }

        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });

        if (accounts.length > 0) {
            window.walletState.currentAccount = accounts[0];
            window.walletState.isConnected = true;
            
            // 触发连接成功事件
            const event = new CustomEvent('walletConnected', {
                detail: { account: accounts[0] }
            });
            window.dispatchEvent(event);
            
            return accounts[0];
        }
    } catch (error) {
        console.error('连接钱包失败:', error);
        throw error;
    }
}

// 断开钱包连接
async function disconnectWallet() {
    try {
        window.walletState.currentAccount = null;
        window.walletState.isConnected = false;
        window.walletState.isAdmin = false;
        window.walletState.permissions = [];
        
        // 触发断开连接事件
        const event = new CustomEvent('walletDisconnected');
        window.dispatchEvent(event);
    } catch (error) {
        console.error('断开钱包失败:', error);
        throw error;
    }
}

// 检查钱包连接状态
async function checkWalletConnection() {
    try {
        if (!window.ethereum) {
            return false;
        }

        const accounts = await window.ethereum.request({
            method: 'eth_accounts'
        });

        if (accounts.length > 0) {
            window.walletState.currentAccount = accounts[0];
            window.walletState.isConnected = true;
            return true;
        }

        return false;
    } catch (error) {
        console.error('检查钱包连接失败:', error);
        return false;
    }
}

// 监听钱包事件
function initWalletListeners() {
    if (!window.ethereum) return;

    // 账户变更
    window.ethereum.on('accountsChanged', async (accounts) => {
        if (accounts.length === 0) {
            await disconnectWallet();
        } else {
            window.walletState.currentAccount = accounts[0];
            window.walletState.isConnected = true;
            
            // 触发账户变更事件
            const event = new CustomEvent('accountChanged', {
                detail: { account: accounts[0] }
            });
            window.dispatchEvent(event);
        }
    });

    // 链变更
    window.ethereum.on('chainChanged', () => {
        window.location.reload();
    });
}

// 导出函数
window.wallet = {
    connect: connectWallet,
    disconnect: disconnectWallet,
    checkConnection: checkWalletConnection,
    initListeners: initWalletListeners
};

// 支持的网络配置
const SUPPORTED_NETWORKS = {
    1: {
        name: 'Mainnet',
        currency: 'ETH',
        explorerUrl: 'https://etherscan.io'
    },
    5: {
        name: 'Goerli',
        currency: 'ETH',
        explorerUrl: 'https://goerli.etherscan.io'
    }
};

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// 优化的钱包状态管理器
const WalletStateManager = {
    state: {
        currentAccount: null,
        isConnected: false,
        isAdmin: false,
        permissions: [],
        networkId: null,
        networkName: null,
        lastError: null,
        lastCheck: null
    },
    
    checkInterval: 5000, // 5秒内不重复检查
    
    async updateState(newState) {
        const now = Date.now();
        if (this.state.lastCheck && (now - this.state.lastCheck < this.checkInterval)) {
            return this.state;
        }
        
        this.state = { 
            ...this.state, 
            ...newState, 
            lastCheck: now 
        };
        
        // 持久化状态
        localStorage.setItem('walletState', JSON.stringify({
            currentAccount: this.state.currentAccount,
            isConnected: this.state.isConnected,
            networkId: this.state.networkId,
            lastCheck: this.state.lastCheck
        }));
        
        // 触发状态变更事件
        window.dispatchEvent(new CustomEvent('walletStateChanged', {
            detail: this.state
        }));
        
        return this.state;
    },
    
    // 批量更新状态
    async batchUpdateState(updates) {
        const combinedUpdates = updates.reduce((acc, update) => ({
            ...acc,
            ...update
        }), {});
        
        await this.updateState(combinedUpdates);
    },

    // 清除状态
    clearState() {
        this.state = {
            currentAccount: null,
            isConnected: false,
            isAdmin: false,
            permissions: [],
            networkId: null,
            networkName: null,
            lastError: null,
            lastCheck: null
        };
        localStorage.removeItem('walletState');
        window.dispatchEvent(new CustomEvent('walletStateChanged', {
            detail: this.state
        }));
    }
};

// 权限管理器
const PermissionManager = {
    cache: new Map(),
    cacheTimeout: 5 * 60 * 1000, // 5分钟缓存
    pendingChecks: new Map(), // 存储进行中的权限检查
    
    async checkPermissions(address) {
        if (!address) return null;
        
        // 检查是否有正在进行的请求
        if (this.pendingChecks.has(address)) {
            return await this.pendingChecks.get(address);
        }
        
        // 检查缓存
        const cached = this.getFromCache(address);
        if (cached) return cached;
        
        // 创建新的请求
        const checkPromise = this._doPermissionCheck(address);
        this.pendingChecks.set(address, checkPromise);
        
        try {
            const result = await checkPromise;
            return result;
        } finally {
            this.pendingChecks.delete(address);
        }
    },
    
    // 从缓存获取权限
    getFromCache(address) {
        const cached = this.cache.get(address?.toLowerCase());
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }
        return null;
    },
    
    // 设置缓存
    setToCache(address, permissions) {
        this.cache.set(address?.toLowerCase(), {
            data: permissions,
            timestamp: Date.now()
        });
    },
    
    // 实际进行权限检查的私有方法
    async _doPermissionCheck(address) {
        try {
            const response = await fetch('/api/admin/check', {
                headers: { 
                    'X-Eth-Address': address,
                    'Cache-Control': 'max-age=300' // 添加缓存控制头
                }
            });
            
            if (!response.ok) throw new Error('权限检查失败');
            
            const permissions = await response.json();
            this.setToCache(address, permissions);
            return permissions;
        } catch (error) {
            console.error('权限检查失败:', error);
            return null;
        }
    },
    
    // 清除缓存
    clearCache() {
        this.cache.clear();
        this.pendingChecks.clear();
    }
};

// 初始化钱包
async function initWallet() {
    try {
        // 等待 MetaMask 注入完成
        if (document.readyState === 'loading') {
            await new Promise(resolve => document.addEventListener('DOMContentLoaded', resolve));
        }
        
        if (!window.ethereum) {
            throw new Error('请安装 MetaMask 钱包');
        }
        
        // 检查是否已经有连接的账户，且未主动断开
        if (window.walletState.connectionStatus !== 'disconnected') {
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                // 获取网络信息
                const chainId = await window.ethereum.request({ method: 'eth_chainId' });
                await handleNetworkChanged(chainId);
                await handleAccountsChanged(accounts);
            } else {
                window.walletState.clearState();
            }
        }
    } catch (error) {
        console.error('初始化钱包失败:', error);
        window.walletState.lastError = error.message;
        window.walletState.setConnectionStatus('error');
    }
}

// 处理账户变更
async function handleAccountsChanged(accounts) {
    try {
        if (accounts.length === 0) {
            window.walletState.clearState();
        } else if (accounts[0] !== window.walletState.currentAccount) {
            window.walletState.currentAccount = accounts[0];
            window.walletState.setConnectionStatus('connected');
            // 检查新账户的管理员权限
            await window.walletState.checkIsAdmin();
            
            // 保存连接状态
            localStorage.setItem('walletConnectionStatus', 'connected');
            localStorage.setItem('userAddress', accounts[0]);
            
            // 关闭下拉菜单
            const walletMenu = document.getElementById('walletMenu');
            if (walletMenu) {
                walletMenu.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('处理账户变更失败:', error);
        window.walletState.lastError = error.message;
    }
    
    // 触发状态变更事件
    window.dispatchEvent(new CustomEvent('walletStateChanged', {
        detail: {
            account: window.walletState.currentAccount,
            status: window.walletState.connectionStatus,
            isAdmin: window.walletState.isAdmin,
            networkId: window.walletState.networkId,
            networkName: window.walletState.networkName,
            permissions: window.walletState.permissions,
            error: window.walletState.lastError
        }
    }));
    
    // 如果在管理页面，检查权限并更新UI
    if (window.location.pathname.startsWith('/admin')) {
        const isAdmin = await window.walletState.checkIsAdmin();
        if (!isAdmin) {
            alert('当前钱包地址不是管理员');
            window.location.href = '/';
        }
    }
}

// 处理网络变更
async function handleNetworkChanged(chainId) {
    try {
        const networkId = parseInt(chainId, 16);
        window.walletState.networkId = networkId;
        
        const network = SUPPORTED_NETWORKS[networkId];
        if (!network) {
            // 如果是不支持的网络，显示警告
            window.walletState.lastError = '请切换到主网或测试网';
            window.walletState.networkName = `Chain ${networkId}`;
            // 清除管理员状态
            window.walletState.isAdmin = false;
            window.walletState.permissions = [];
        } else {
            window.walletState.networkName = network.name;
            // 在支持的网络上重新检查权限
            await window.walletState.checkIsAdmin();
        }
        
        // 触发网络变更事件
        window.dispatchEvent(new CustomEvent('networkChanged', {
            detail: {
                networkId: networkId,
                networkName: window.walletState.networkName,
                isSupported: !!network
            }
        }));
    } catch (error) {
        console.error('处理网络变更失败:', error);
        window.walletState.lastError = error.message;
    }
}

// 优化后的钱包连接和切换函数
const connectWallet = debounce(async () => {
    try {
        if (!window.ethereum) {
            throw new Error('请安装 MetaMask 钱包');
        }
        
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        await handleAccountsChanged(accounts);
        return accounts[0];
    } catch (error) {
        handleWalletError(error);
        throw error;
    }
}, 500);

const switchWallet = debounce(async () => {
    try {
        if (!window.ethereum) {
            throw new Error('请安装 MetaMask 钱包');
        }
        
        // 先清除当前状态
        WalletStateManager.clearState();
        PermissionManager.clearCache();
        
        // 请求切换钱包
        await window.ethereum.request({
            method: 'wallet_requestPermissions',
            params: [{
                eth_accounts: {}
            }]
        });
        
        // 获取新账户
        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
        if (accounts.length > 0) {
            await handleAccountsChanged(accounts);
            return accounts[0];
        }
        
        throw new Error('未选择账户');
    } catch (error) {
        handleWalletError(error);
        throw error;
    }
}, 500);

// 断开钱包连接
async function disconnectWallet() {
    window.walletState.clearState();
    
    // 关闭下拉菜单
    const walletMenu = document.getElementById('walletMenu');
    if (walletMenu) {
        walletMenu.style.display = 'none';
    }
    
    // 触发状态变更事件
    window.dispatchEvent(new CustomEvent('walletStateChanged', {
        detail: {
            account: null,
            status: 'disconnected',
            isAdmin: false,
            networkId: null,
            networkName: null,
            permissions: [],
            error: null
        }
    }));
    
    // 刷新页面
    window.location.reload();
}

// 添加网络变更监听
if (window.ethereum) {
    window.ethereum.on('chainChanged', handleNetworkChanged);
    window.ethereum.on('accountsChanged', handleAccountsChanged);
    window.ethereum.on('disconnect', () => {
        window.walletState.clearState();
        window.location.reload();
    });
    
    // 初始化钱包
    initWallet().catch(console.error);
}

// 导出全局函数
window.walletState = WalletStateManager.state;
window.connectWallet = connectWallet;
window.switchWallet = switchWallet;
window.disconnectWallet = () => {
    WalletStateManager.clearState();
    PermissionManager.clearCache();
    window.location.reload();
};

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    // 等待 MetaMask 注入完成
    if (typeof window.ethereum === 'undefined') {
        await new Promise(resolve => {
            const checkMetaMask = setInterval(() => {
                if (typeof window.ethereum !== 'undefined') {
                    clearInterval(checkMetaMask);
                    resolve();
                }
            }, 100);
            
            // 10秒后超时
            setTimeout(() => {
                clearInterval(checkMetaMask);
                resolve();
            }, 10000);
        });
    }
    
    // 恢复保存的状态
    const savedState = localStorage.getItem('walletState');
    if (savedState) {
        try {
            const state = JSON.parse(savedState);
            if (state.isConnected && state.currentAccount) {
                const accounts = await window.ethereum.request({ method: 'eth_accounts' });
                if (accounts.length > 0 && accounts[0].toLowerCase() === state.currentAccount.toLowerCase()) {
                    await handleAccountsChanged(accounts);
                } else {
                    WalletStateManager.clearState();
                }
            }
        } catch (error) {
            console.error('恢复状态失败:', error);
            WalletStateManager.clearState();
        }
    }
}); 