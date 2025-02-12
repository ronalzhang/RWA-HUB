// 初始化钱包状态
if (!window.walletState) {
    window.walletState = {
        currentAccount: null,
        connectionStatus: localStorage.getItem('walletConnectionStatus') || 'disconnected', // disconnected, connecting, connected, error
        isAdmin: false,
        networkId: null,
        networkName: null,
        permissions: [],
        lastError: null,
        permissionCache: new Map(),
        
        // 获取当前账户
        getCurrentAccount() {
            return this.currentAccount;
        },
        
        // 检查是否已连接
        isConnected() {
            return this.connectionStatus === 'connected' && this.currentAccount !== null;
        },
        
        // 设置连接状态
        setConnectionStatus(status) {
            this.connectionStatus = status;
            localStorage.setItem('walletConnectionStatus', status);
        },
        
        // 检查是否是管理员
        async checkIsAdmin() {
            try {
                if (!this.currentAccount) return false;
                
                const response = await fetch('/api/admin/check', {
                    method: 'GET',
                    headers: {
                        'X-Eth-Address': this.currentAccount
                    }
                });
                
                if (!response.ok) {
                    throw new Error('检查管理员状态失败');
                }
                
                const data = await response.json();
                this.isAdmin = data.is_admin;
                this.permissions = data.is_admin ? data.permissions : [];
                return this.isAdmin;
            } catch (error) {
                console.error('检查管理员状态失败:', error);
                this.isAdmin = false;
                this.permissions = [];
                return false;
            }
        },
        
        // 清除状态
        clearState() {
            this.currentAccount = null;
            this.setConnectionStatus('disconnected');
            this.isAdmin = false;
            this.networkId = null;
            this.networkName = null;
            this.permissions = [];
            this.lastError = null;
            this.permissionCache.clear();
        }
    };
}

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

// 初始化钱包
async function initWallet() {
    try {
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
            window.walletState.connectionStatus = 'connected';
            // 检查新账户的管理员权限
            await window.walletState.checkIsAdmin();
            
            // 保存连接状态
            localStorage.setItem('walletConnectionStatus', 'connected');
            localStorage.setItem('userAddress', accounts[0]);
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

// 连接钱包
async function connectWallet() {
    try {
        if (!window.ethereum) {
            throw new Error('请安装 MetaMask 钱包');
        }
        
        window.walletState.setConnectionStatus('connecting');
        window.walletState.lastError = null;
        
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        
        await handleNetworkChanged(chainId);
        await handleAccountsChanged(accounts);
        
        return accounts[0];
    } catch (error) {
        console.error('连接钱包失败:', error);
        window.walletState.setConnectionStatus('error');
        
        let message = '连接钱包失败';
        if (error.code === 4001) {
            message = '您取消了连接钱包';
        } else if (error.code === -32002) {
            message = '钱包连接请求正在处理中,请检查 MetaMask';
        }
        
        window.walletState.lastError = message;
        throw new Error(message);
    }
}

// 断开钱包连接
async function disconnectWallet() {
    window.walletState.clearState();
    
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
}

// 添加网络变更监听
if (window.ethereum) {
    window.ethereum.on('chainChanged', handleNetworkChanged);
    window.ethereum.on('accountsChanged', handleAccountsChanged);
    window.ethereum.on('disconnect', () => {
        window.walletState.clearState();
    });
    
    // 初始化钱包
    initWallet().catch(console.error);
}

// 导出函数到全局作用域
window.connectWallet = connectWallet;
window.disconnectWallet = disconnectWallet; 