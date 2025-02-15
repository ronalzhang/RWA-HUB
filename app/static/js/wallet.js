// 钱包状态管理
const walletState = {
    address: null,
    isConnected: false,
    isAdmin: false,
    currentAccount: null,
    
    // 初始化钱包状态
    init() {
        // 从localStorage获取保存的状态
        const savedAddress = localStorage.getItem('walletAddress');
        if (savedAddress) {
            this.address = savedAddress;
            this.currentAccount = savedAddress;
            this.isConnected = true;
            this.updateUI();
            this.checkIsAdmin(); // 检查管理员权限
        }
        
        // 监听钱包事件
        if (window.ethereum) {
            window.ethereum.on('accountsChanged', (accounts) => {
                if (accounts.length === 0) {
                    this.disconnect();
                } else {
                    this.address = accounts[0];
                    this.isConnected = true;
                    this.updateUI();
                    this.saveState();
                }
            });

            window.ethereum.on('disconnect', () => {
                this.disconnect();
            });
        }
    },
    
    // 连接钱包
    async connect() {
        try {
            if (!window.ethereum) {
                throw new Error('请安装MetaMask钱包');
            }
            
            const accounts = await window.ethereum.request({ 
                method: 'eth_requestAccounts' 
            });
            
            if (accounts.length > 0) {
                this.address = accounts[0];
                this.isConnected = true;
                this.updateUI();
                this.saveState();
                return true;
            }
            return false;
        } catch (error) {
            console.error('连接钱包失败:', error);
            throw error;
        }
    },
    
    // 断开钱包连接
    disconnect() {
        this.address = null;
        this.isConnected = false;
        this.updateUI();
        this.clearState();
    },
    
    // 切换钱包
    async switchWallet() {
        try {
            await window.ethereum.request({
                method: 'wallet_requestPermissions',
                params: [{ eth_accounts: {} }]
            });
        } catch (error) {
            console.error('切换钱包失败:', error);
            throw error;
        }
    },
    
    // 保存状态到localStorage
    saveState() {
        if (this.address) {
            localStorage.setItem('walletAddress', this.address);
            document.cookie = `eth_address=${this.address}; path=/; max-age=86400`;
        }
    },
    
    // 清除保存的状态
    clearState() {
        localStorage.removeItem('walletAddress');
        document.cookie = 'eth_address=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    },
    
    // 更新UI显示
    updateUI() {
        const walletBtn = document.getElementById('walletBtn');
        const walletMenu = document.getElementById('walletMenu');
        const walletBtnText = document.getElementById('walletBtnText');
        
        if (!walletBtn || !walletMenu || !walletBtnText) return;
        
        if (this.isConnected && this.address) {
            // 显示简短的钱包地址
            const shortAddress = `${this.address.substring(0, 6)}...${this.address.substring(38)}`;
            walletBtnText.textContent = shortAddress;
            walletBtn.classList.remove('btn-outline-primary');
            walletBtn.classList.add('btn-primary');
            walletMenu.style.display = 'none';
        } else {
            walletBtnText.textContent = '连接钱包';
            walletBtn.classList.remove('btn-primary');
            walletBtn.classList.add('btn-outline-primary');
            walletMenu.style.display = 'none';
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
        if (!this.currentAccount) return false;
        
        try {
            const response = await fetch('/api/admin/check', {
                headers: {
                    'X-Eth-Address': this.currentAccount
                }
            });
            
            if (!response.ok) {
                throw new Error('检查管理员权限失败');
            }
            
            const data = await response.json();
            this.isAdmin = data.is_admin;
            
            // 更新管理员入口
            const adminEntry = document.getElementById('adminEntry');
            const adminLink = document.getElementById('adminLink');
            
            if (adminEntry && adminLink) {
                if (this.isAdmin) {
                    adminEntry.classList.remove('d-none');
                    adminLink.href = `/admin?eth_address=${this.currentAccount}`;
                    adminLink.onclick = function(e) {
                        e.preventDefault();
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
};

// 初始化钱包UI
function initWalletUI() {
    const walletBtn = document.getElementById('walletBtn');
    const walletMenu = document.getElementById('walletMenu');
    const walletBtnText = document.getElementById('walletBtnText');
    
    if (!walletBtn || !walletMenu || !walletBtnText) return;
    
    // 初始化UI状态
    if (window.walletState && window.walletState.getConnectionStatus()) {
        const address = window.walletState.getAddress();
        if (address) {
            walletBtnText.textContent = `${address.slice(0, 6)}...${address.slice(-4)}`;
            walletBtn.classList.remove('btn-outline-primary');
            walletBtn.classList.add('btn-primary');
        }
    } else {
        walletBtnText.textContent = '连接钱包';
        walletBtn.classList.remove('btn-primary');
        walletBtn.classList.add('btn-outline-primary');
        walletMenu.style.display = 'none';
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', async function() {
    // 初始化钱包状态
    window.walletState = walletState;
    walletState.init();
    
    // 初始化UI和事件监听
    initWalletUI();
    setupWalletListeners();
    await checkInitialWalletState();
    
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
                walletMenu.style.display = walletMenu.style.display === 'block' ? 'none' : 'block';
            }
        });
    }
    
    // 切换钱包
    if (switchWalletBtn) {
        switchWalletBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                await walletState.switchWallet();
                walletMenu.style.display = 'none';
            } catch (error) {
                showError(error.message);
            }
        });
    }
    
    // 断开连接
    if (disconnectWalletBtn) {
        disconnectWalletBtn.addEventListener('click', (e) => {
            e.preventDefault();
            walletState.disconnect();
            walletMenu.style.display = 'none';
        });
    }
    
    // 点击其他地方关闭菜单
    document.addEventListener('click', (e) => {
        if (walletMenu && walletMenu.style.display === 'block' && 
            !walletBtn.contains(e.target) && !walletMenu.contains(e.target)) {
            walletMenu.style.display = 'none';
        }
    });
    
    // 语言切换功能
    const languageDropdown = document.getElementById('languageDropdown');
    if (languageDropdown) {
        const currentLanguage = document.cookie.split(';').find(c => c.trim().startsWith('language='));
        const lang = currentLanguage ? currentLanguage.split('=')[1].trim() : 'en';
        languageDropdown.textContent = lang === 'en' ? 'English' : '繁體中文';
    }
});

// 显示错误信息
function showError(message) {
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    document.getElementById('errorMessage').textContent = message;
    errorModal.show();
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

// 检查初始钱包状态
async function checkInitialWalletState() {
    if (typeof window.ethereum !== 'undefined') {
        try {
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                window.walletState.currentAccount = accounts[0];
                window.walletState.address = accounts[0];
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
                window.walletState.address = accounts[0];
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

// 语言切换函数
window.changeLanguage = function(lang) {
    document.cookie = `language=${lang};path=/;max-age=31536000`;
    window.location.reload();
} 