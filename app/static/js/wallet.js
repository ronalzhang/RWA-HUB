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
            return Boolean(this.currentAccount);
        },
        
        // 设置连接状态
        setConnectionStatus(status) {
            this.connectionStatus = status;
            localStorage.setItem('walletConnectionStatus', status);
            this.updateUI();
        },
        
        // 检查是否是管理员
        async checkIsAdmin() {
            return await checkAdminStatus();
        },
        
        // 更新UI
        updateUI() {
            // 更新钱包按钮
            const walletBtn = document.getElementById('walletBtn');
            const walletBtnText = document.getElementById('walletBtnText');
            const walletMenu = document.getElementById('walletMenu');
            const adminEntry = document.getElementById('adminEntry');
            const adminLink = document.getElementById('adminLink');
            
            if (walletBtn && walletBtnText) {
                if (this.isConnected()) {
                    walletBtn.classList.remove('btn-outline-primary');
                    walletBtn.classList.add('btn-primary');
                    walletBtnText.textContent = `${this.currentAccount.slice(0, 6)}...${this.currentAccount.slice(-4)}`;
                    if (walletMenu) walletMenu.style.display = 'block';
                } else {
                    walletBtn.classList.add('btn-outline-primary');
                    walletBtn.classList.remove('btn-primary');
                    walletBtnText.textContent = '连接钱包';
                    if (walletMenu) walletMenu.style.display = 'none';
                }
            }
            
            // 更新管理员入口
            if (adminEntry && adminLink) {
                if (this.isAdmin && this.currentAccount) {
                    adminEntry.classList.remove('d-none');
                    adminLink.href = `/admin?eth_address=${this.currentAccount.toLowerCase()}`;
                } else {
                    adminEntry.classList.add('d-none');
                }
            }
        },
        
        // 清除状态
        async clearState() {
            this.currentAccount = null;
            this.setConnectionStatus('disconnected');
            this.isAdmin = false;
            this.networkId = null;
            this.networkName = null;
            this.permissions = [];
            this.lastError = null;
            this.permissionCache.clear();
            this.updateUI();
            localStorage.removeItem('walletAddress');
            const adminEntry = document.getElementById('adminEntry');
            if (adminEntry) {
                adminEntry.classList.add('d-none');
            }
            
            // 如果在管理后台页面，则重定向到首页
            if (window.location.pathname.startsWith('/admin')) {
                window.location.href = '/';
            }
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
            window.walletState.currentAccount = accounts[0].toLowerCase();
            window.walletState.setConnectionStatus('connected');
            // 检查新账户的管理员权限
            await window.walletState.checkIsAdmin();
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
            window.walletState.updateUI();
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

// 初始化钱包UI
function initWalletUI() {
    const walletBtn = document.getElementById('walletBtn');
    const walletMenu = document.getElementById('walletMenu');
    const walletBtnText = document.getElementById('walletBtnText');
    const switchWallet = document.getElementById('switchWallet');
    const disconnectWallet = document.getElementById('disconnectWallet');

    if (!walletBtn || !walletMenu || !walletBtnText) return;

    // 从localStorage获取菜单状态
    const menuState = localStorage.getItem('walletMenuState');
    if (menuState === 'open' && window.walletState.isConnected()) {
        walletMenu.style.display = 'block';
    }

    // 点击钱包按钮
    walletBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (!window.ethereum) {
            showError('请安装MetaMask钱包');
            return;
        }

        if (!window.walletState.isConnected()) {
            try {
                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                if (accounts.length > 0) {
                    window.walletState.currentAccount = accounts[0];
                    await window.walletState.checkIsAdmin();
                    updateWalletUI(true);
                    // 保存菜单状态
                    localStorage.setItem('walletMenuState', 'open');
                    walletMenu.style.display = 'block';
                }
            } catch (error) {
                console.error('连接钱包失败:', error);
                showError('连接钱包失败: ' + error.message);
            }
        } else {
            const isVisible = walletMenu.style.display === 'block';
            walletMenu.style.display = isVisible ? 'none' : 'block';
            // 保存菜单状态
            localStorage.setItem('walletMenuState', isVisible ? 'closed' : 'open');
        }
    });

    // 点击其他地方关闭菜单
    document.addEventListener('click', function(e) {
        if (!walletBtn.contains(e.target) && !walletMenu.contains(e.target)) {
            walletMenu.style.display = 'none';
            localStorage.setItem('walletMenuState', 'closed');
        }
    });

    // 切换钱包
    if (switchWallet) {
        switchWallet.addEventListener('click', async function(e) {
            e.preventDefault();
            try {
                await window.ethereum.request({
                    method: 'wallet_requestPermissions',
                    params: [{ eth_accounts: {} }]
                });
                walletMenu.style.display = 'none';
                localStorage.setItem('walletMenuState', 'closed');
            } catch (error) {
                console.error('切换钱包失败:', error);
                showError('切换钱包失败: ' + error.message);
            }
        });
    }
    
    // 断开连接
    if (disconnectWallet) {
        disconnectWallet.addEventListener('click', async function(e) {
            e.preventDefault();
            try {
                await window.walletState.clearState();
                walletBtnText.textContent = '连接钱包';
                walletMenu.style.display = 'none';
                localStorage.setItem('walletMenuState', 'closed');
                walletBtn.classList.remove('btn-primary');
                walletBtn.classList.add('btn-outline-primary');
                window.location.reload();
            } catch (error) {
                console.error('断开连接失败:', error);
                showError('断开连接失败: ' + error.message);
            }
        });
    }
}

// 更新钱包UI显示
function updateWalletUI(connected) {
    const walletBtnText = document.getElementById('walletBtnText');
    const walletBtn = document.getElementById('walletBtn');
    const walletMenu = document.getElementById('walletMenu');
    
    if (!walletBtnText || !walletBtn || !walletMenu) return;

    if (connected) {
        const address = window.walletState.currentAccount;
        walletBtnText.textContent = `${address.slice(0, 6)}...${address.slice(-4)}`;
        walletBtn.classList.remove('btn-outline-primary');
        walletBtn.classList.add('btn-primary');
    } else {
        walletBtnText.textContent = '连接钱包';
        walletBtn.classList.remove('btn-primary');
        walletBtn.classList.add('btn-outline-primary');
        walletMenu.classList.remove('show');
    }
}

// 检查初始钱包状态
async function checkInitialWalletState() {
    if (typeof window.ethereum !== 'undefined') {
        try {
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                window.walletState.currentAccount = accounts[0];
                await window.walletState.checkIsAdmin();
                updateWalletUI(true);
            }
        } catch (error) {
            console.error('检查钱包状态失败:', error);
        }
    }
}

// 监听钱包事件
function setupWalletListeners() {
    if (typeof window.ethereum !== 'undefined') {
        window.ethereum.on('accountsChanged', async function(accounts) {
            if (accounts.length === 0) {
                await window.walletState.clearState();
                updateWalletUI(false);
            } else {
                window.walletState.currentAccount = accounts[0];
                await window.walletState.checkIsAdmin();
                updateWalletUI(true);
            }
        });

        window.ethereum.on('disconnect', async function() {
            await window.walletState.clearState();
            updateWalletUI(false);
        });
    }
}

// 错误提示函数
function showError(message) {
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    const errorMessage = document.getElementById('errorMessage');
    if (errorMessage) {
        errorMessage.textContent = message;
    }
    errorModal.show();
}

// 检查管理员权限
async function checkAdminStatus() {
    if (!window.walletState.currentAccount) return false;
    
    try {
        const response = await fetch('/api/admin/check', {
            headers: {
                'X-Eth-Address': window.walletState.currentAccount
            }
        });
        
        if (!response.ok) {
            throw new Error('检查管理员权限失败');
        }
        
        const data = await response.json();
        window.walletState.isAdmin = data.is_admin;
        
        // 更新管理员入口
        const adminEntry = document.getElementById('adminEntry');
        const adminLink = document.getElementById('adminLink');
        
        if (adminEntry && adminLink) {
            if (window.walletState.isAdmin) {
                adminEntry.classList.remove('d-none');
                // 更新管理后台链接，添加当前地址作为参数
                adminLink.href = `/admin?eth_address=${window.walletState.currentAccount}`;
                // 添加点击事件处理
                adminLink.onclick = function(e) {
                    e.preventDefault();
                    // 确保地址参数正确传递
                    window.location.href = this.href;
                };
            } else {
                adminEntry.classList.add('d-none');
            }
        }
        
        return data.is_admin;
    } catch (error) {
        console.error('检查管理员权限失败:', error);
        return false;
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initWalletUI();
    setupWalletListeners();
    checkInitialWalletState();
}); 