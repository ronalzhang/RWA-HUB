// 钱包状态管理
const walletState = {
    address: null,
    isConnected: false,
    isAdmin: false,
    eventCallbacks: new Set(), // 用于存储状态变化的回调函数
    
    // 初始化钱包状态
    async init() {
        console.log('Initializing wallet state...');
        if (!window.ethereum) {
            console.warn('MetaMask not installed');
            return;
        }

        try {
            // 获取当前连接的账户
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                this.address = accounts[0].toLowerCase();
                this.isConnected = true;
                this.updateUI();
                await this.checkIsAdmin();
                this.notifyStateChange();
            }
        } catch (error) {
            console.error('Failed to initialize wallet state:', error);
        }

        // 监听钱包事件
        this.setupEventListeners();
    },

    // 设置事件监听器
    setupEventListeners() {
        if (!window.ethereum) return;

        window.ethereum.on('accountsChanged', async (accounts) => {
            console.log('Accounts changed:', accounts);
            if (accounts.length === 0) {
                await this.disconnect();
            } else {
                this.address = accounts[0].toLowerCase();
                this.isConnected = true;
                await this.checkIsAdmin();
                this.updateUI();
                this.notifyStateChange();
            }
        });

        window.ethereum.on('disconnect', async () => {
            console.log('Wallet disconnected');
            await this.disconnect();
        });

        window.ethereum.on('chainChanged', () => {
            console.log('Chain changed, reloading...');
            window.location.reload();
        });
    },
    
    // 连接钱包
    async connect() {
        console.log('Connecting wallet...');
        try {
            if (!window.ethereum) {
                throw new Error('请安装MetaMask钱包');
            }
            
            const accounts = await window.ethereum.request({ 
                method: 'eth_requestAccounts' 
            });
            
            if (accounts.length > 0) {
                this.address = accounts[0].toLowerCase();
                this.isConnected = true;
                await this.checkIsAdmin();
                this.updateUI();
                this.notifyStateChange();
                return true;
            }
            return false;
        } catch (error) {
            console.error('Failed to connect wallet:', error);
            throw error;
        }
    },
    
    // 断开钱包连接
    async disconnect() {
        console.log('Disconnecting wallet...');
        this.address = null;
        this.isConnected = false;
        this.isAdmin = false;
        this.updateUI();
        this.notifyStateChange();
        
        // 清除状态
        this.clearState();
    },
    
    // 切换钱包
    async switchWallet() {
        console.log('Switching wallet...');
        try {
            await window.ethereum.request({
                method: 'wallet_requestPermissions',
                params: [{ eth_accounts: {} }]
            });
        } catch (error) {
            console.error('Failed to switch wallet:', error);
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
            } else {
                // 切换菜单显示状态
                if (walletMenu) {
                    walletMenu.classList.toggle('show');
                }
            }
        });
    }
    
    // 切换钱包
    if (switchWalletBtn) {
        switchWalletBtn.addEventListener('click', async (e) => {
            e.preventDefault();
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
    
    // 断开连接
    if (disconnectWalletBtn) {
        disconnectWalletBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await walletState.disconnect();
            if (walletMenu) {
                walletMenu.classList.remove('show');
            }
        });
    }
    
    // 点击其他地方关闭菜单
    document.addEventListener('click', (e) => {
        if (walletMenu && walletMenu.classList.contains('show') && 
            !walletBtn.contains(e.target) && !walletMenu.contains(e.target)) {
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

// 语言切换函数
window.changeLanguage = function(lang) {
    document.cookie = `language=${lang};path=/;max-age=31536000`;
    window.location.reload();
} 