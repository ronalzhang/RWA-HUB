/**
 * RWA-HUB 钱包管理模块
 * 支持多种钱包类型的连接、管理和状态同步
 */

// 防止重复加载
if (window.RWA_WALLET_LOADED) {
    console.warn('Wallet script already loaded, but continuing...');
}
window.RWA_WALLET_LOADED = true;

// 添加调试模式检查 - 只在开发环境或明确启用时输出详细日志
const DEBUG_MODE = window.location.hostname === 'localhost' || 
                   window.location.hostname === '127.0.0.1' || 
                   window.DEBUG_MODE === true;

// 调试日志函数
function debugLog(...args) {
    if (DEBUG_MODE) {
        console.log(...args);
    }
}

function debugWarn(...args) {
    if (DEBUG_MODE) {
        console.warn(...args);
    }
}

function debugError(...args) {
    // 错误总是显示，但在非调试模式下简化
    if (DEBUG_MODE) {
        console.error(...args);
    } else {
        console.error(args[0]); // 只显示第一个参数（主要错误信息）
    }
}

// 钱包状态管理类
const walletState = {
    // 状态变量
    address: null,             // 当前连接的钱包地址
    walletType: null,          // 当前连接的钱包类型: 'ethereum', 'phantom' 等
    connected: false,          // 是否已连接钱包
    isAdmin: false,            // 是否是管理员账户
    balance: 0,                // 当前钱包余额
    commissionBalance: 0,      // 分佣余额
    nativeBalance: 0,          // 原生代币余额
    connecting: false,         // 是否正在连接中
    chainId: null,             // 当前连接的链ID
    assets: [],                // 当前钱包拥有的资产
    web3: null,                // Web3实例（以太坊钱包）
    provider: null,            // 钱包提供商实例
    pendingWalletAppOpen: false, // 是否正在等待打开钱包App（移动端）
    pendingWalletType: null,   // 待连接的钱包类型（移动端打开App时）
    web3Available: true,       // 标记Web3.js是否可用
    initialized: false,        // 标记钱包是否已初始化
    
    /**
     * 初始化钱包状态
     * 检查是否已经有连接的钱包，并恢复连接
     */
    async init() {
        try {
            console.log('初始化钱包...');
            if (this.initialized) {
                console.log('钱包已初始化，跳过');
                return;
            }
            
            this._isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

            if (this._isMobile) {
                console.log('检测到移动设备，检查是否从钱包App返回');
                const walletTypes = ['phantom', 'metamask', 'ethereum', 'solflare'];
                for (const type of walletTypes) {
                    if (this.checkIfReturningFromWalletApp(type)) {
                        console.log(`检测到从${type}钱包App返回，将尝试恢复连接`);
                        this.clearState();
                        await this.waitForDocumentReady();
                        console.log(`尝试连接${type}钱包...`);
                        let connected = false;
                        try {
                            if (type === 'phantom' || type === 'solana') {
                                connected = await this.connectPhantom();
                            } else if (type === 'ethereum' || type === 'metamask') {
                                connected = await this.connectEthereum();
                            }
                            
                            if (connected) {
                                console.log(`从钱包App返回后成功连接${type}钱包`);
                                this.updateUI();
                                this.triggerWalletStateChanged();
                                break;
                            } else {
                                console.log(`从钱包App返回后连接${type}钱包失败`);
                            }
                        } catch (err) {
                            console.error('从钱包App返回后连接钱包失败:', err);
                        }
                    }
                }
            }

            const storedWalletType = localStorage.getItem('walletType') || sessionStorage.getItem('walletType');
            const storedWalletAddress = localStorage.getItem('walletAddress') || sessionStorage.getItem('walletAddress');
            
            console.log(`钱包初始化 - 类型: ${storedWalletType || '无'}, 地址: ${storedWalletAddress || '无'}`);
            
            if (storedWalletType && storedWalletAddress) {
                console.log(`尝试恢复之前的钱包连接 - 类型: ${storedWalletType}, 地址: ${storedWalletAddress}`);
                this.walletType = storedWalletType;
                this.address = storedWalletAddress;
                this.connected = true;
                this.updateUI();
                this.triggerWalletStateChanged();
                this.getUserAssets(storedWalletAddress).catch(err => console.error('初始加载资产失败:', err));
                
                let canReconnect = false;
                if (storedWalletType === 'ethereum' && window.ethereum) {
                    canReconnect = true;
                } else if (storedWalletType === 'phantom') {
                    if (window.solana && window.solana.isPhantom) {
                        canReconnect = true;
                    } else {
                        setTimeout(() => {
                            if (window.solana && window.solana.isPhantom) {
                                this.delayedPhantomReconnect();
                            }
                        }, 2000);
                    }
                } else if (storedWalletType === 'solana' && window.solana) {
                    canReconnect = true;
                }
                
                if (canReconnect) {
                    try {
                        let success = false;
                        if (storedWalletType === 'ethereum') {
                            success = await this.connectEthereum(true);
                        } else if (storedWalletType === 'phantom' || storedWalletType === 'solana') {
                            success = await this.connectPhantom(true);
                        }
                        if (success) {
                            this.triggerWalletStateChanged();
                        }
                    } catch (error) {
                        console.error('静默重连失败:', error);
                    }
                }
            } else {
                this.clearState();
                this.updateUI();
            }
            
            window.addEventListener('beforeunload', () => {
                if (this.connected && this.walletType && this.address) {
                    localStorage.setItem('walletType', this.walletType);
                    localStorage.setItem('walletAddress', this.address);
                }
            });
            
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible' && this.connected) {
                    this.checkWalletConnection();
                }
            });
            
            window.addEventListener('storage', (event) => {
                if (event.key === 'walletAddress' || event.key === 'walletType') {
                    if (!this._storageChangeTimer) {
                        this._storageChangeTimer = setTimeout(() => {
                            this.handleStorageChange();
                            this._storageChangeTimer = null;
                        }, 2000);
                    }
                }
            });
            
            this.checkWalletConsistency();
            setInterval(() => this.checkWalletConsistency(), 30000);
            this.initialized = true;
            console.log('钱包初始化完成');
            return true;
        } catch (error) {
            console.error('初始化钱包出错:', error);
            return false;
        }
    },
    
    checkWalletConsistency(forceUpdate = false) {
        // ... (Implementation from file)
    },
    
    async handleStorageChange() {
        this.checkWalletConsistency(true);
    },
    
    updateDetailPageButtonState() {
        // ... (Implementation from file)
    },
    
    waitForDocumentReady() {
        return new Promise(resolve => {
            if (document.readyState === 'complete' || document.readyState === 'interactive') {
                resolve();
            } else {
                document.addEventListener('DOMContentLoaded', () => resolve());
            }
        });
    },
    
    clearStoredWalletData() {
        // ... (Implementation from file)
    },
    
    async checkWalletConnection() {
        // ... (Implementation from file)
    },
    
    clearState() {
        // ... (Implementation from file)
    },
    
    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    },

    async connect(walletType) {
        console.log(`尝试连接钱包: ${walletType}`);
        this.connecting = true;
        this.updateUI();
        
        if (this.isMobile() && !this._isReconnecting) {
            console.log('检测到移动设备，尝试跳转到钱包应用');
            const deepLinkSuccess = await this.tryMobileWalletRedirect(walletType);
            if (deepLinkSuccess) {
                console.log('深度链接跳转成功，等待用户从钱包应用返回');
                this.connecting = false;
                this.updateUI();
                return true;
            }
        }
        
        let success = false;
        try {
            if (walletType === 'ethereum') {
                success = await this.connectEthereum();
            } else if (walletType === 'phantom' || walletType === 'solana') {
                success = await this.connectPhantom();
            } else {
                throw new Error(`不支持的钱包类型: ${walletType}`);
            }
            
            if (success) {
                this.triggerWalletStateChanged();
                this.updateDetailPageButtonState();
            } else {
                if (walletType === 'phantom') {
                    this.showPhantomRetryOption();
                }
                if (!this.connected) {
                    this.clearState();
                }
            }
        } catch (error) {
            console.error(`连接 ${walletType} 钱包失败:`, error);
            this.clearState();
            showError(`连接失败: ${error.message}`);
        } finally {
            this.connecting = false;
            this.updateUI();
        }
        return success;
    },
    
    updateUI() {
        // ... (Implementation from file)
    },
    
    triggerWalletStateChanged(details = {}) {
        // ... (Implementation from file)
    },
    
    formatAddress: function(address) {
        if (!address) return '';
        if (address.length > 10) {
            return address.slice(0, 6) + '...' + address.slice(-4);
        }
        return address;
    },
    
    async connectToProvider(provider) {
        return this.connect(provider);
    },
    
    async disconnect(reload = true) {
        // ... (Implementation from file)
    },
    
    async switchWallet() {
        // ... (Implementation from file)
    },
    
    getConnectionStatus() {
        return this.connected;
    },
    
    getAddress() {
        return this.address;
    },
    
    getWalletType() {
        return this.walletType;
    },
    
    async checkIsAdmin() {
        // ... (Implementation from file)
    },
    
    onStateChange(callback) {
        // ... (Implementation from file)
    },
    
    offStateChange(callback) {
        // ... (Implementation from file)
    },
    
    notifyStateChange(details = {}) {
        // ... (Implementation from file)
    },
    
    updateAdminDisplay() {
        // ... (Implementation from file)
    },
    
    shouldCheckAdminStatus() {
        // ... (Implementation from file)
    },
    
    createOrShowDividendButtons() {
        // ... (Implementation from file)
    },
    
    async getWalletBalance() {
        // ... (Implementation from file)
    },
    
    async ensureSolanaLibrariesOptimized() {
        // ... (Implementation from file)
    },
    
    async loadSolanaWeb3FromCDN() {
        // ... (Implementation from file)
    },
    
    createBasicSplTokenInterface() {
        // ... (Implementation from file)
    },
    
    createMinimalSolanaInterface() {
        // ... (Implementation from file)
    },
    
    triggerBalanceUpdatedEvent() {
        // ... (Implementation from file)
    },
    
    updateBalanceDisplay(balance = null) {
        // ... (Implementation from file)
    },
    
    updateAssetsUI() {
        // ... (Implementation from file)
    },

    openWalletSelector() {
        // ... (Implementation from file)
    },

    closeWalletSelector() {
        // ... (Implementation from file)
    },

    showWalletOptions() {
        // ... (Implementation from file)
    },

    async getUserAssets(address) {
        // ... (Implementation from file)
    },

    connectSolflare: async function() {
        // ... (Implementation from file)
    },

    connectCoinbase: async function() {
        // ... (Implementation from file)
    },

    connectSlope: async function() {
        // ... (Implementation from file)
    },

    connectGlow: async function() {
        // ... (Implementation from file)
    },

    async connectPhantom(isReconnect = false) {
        // ... (Implementation from file)
    },

    checkIfReturningFromWalletApp(walletType) {
        // ... (Implementation from file)
    },

    async connectEthereum(isReconnect = false) {
        // ... (Implementation from file)
    },

    setupEthereumListeners() {
        // ... (Implementation from file)
    },

    setupPhantomListeners() {
        // ... (Implementation from file)
    },

    copyWalletAddress() {
        // ... (Implementation from file)
    },
    
    showCopySuccess() {
        // ... (Implementation from file)
    },
    
    async transferToken(tokenSymbol, to, amount) {
        // ... (Implementation from file)
    },
    
    async transferSolanaToken(tokenSymbol, to, amount) {
        // ... (Implementation from file)
    },
    
    delayedPhantomReconnect() {
        // ... (Implementation from file)
    },
    
    checkTokenBalance: async function(tokenSymbol) {
        // ... (Implementation from file)
    },
    
    async connectWallet(options) {
        // ... (Implementation from file)
    },
    
    async getBalanceWithFallback(address, tokenSymbol) {
        // ... (Implementation from file)
    },
    
    async getCommissionBalance() {
        // ... (Implementation from file)
    },

    async getUSDCBalance() {
        // ... (Implementation from file)
    },

    _getBalanceCache(key) {
        // ... (Implementation from file)
    },

    _setBalanceCache(key, balance) {
        // ... (Implementation from file)
    },

    async refreshAllBalances(force = false) {
        // ... (Implementation from file)
    },

    async afterSuccessfulConnection(address, walletType, provider) {
        // ... (Implementation from file)
    },

    showPhantomRetryOption() {
        // ... (Implementation from file)
    },

    async registerWalletUser(address, walletType) {
        try {
            console.log(`[registerWalletUser] 注册用户: ${address}, 钱包类型: ${walletType}`);
            const response = await fetch('/api/service/user/register_wallet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': address,
                    'X-Wallet-Type': walletType
                },
                body: JSON.stringify({
                    address: address,
                    wallet_type: walletType
                })
            });
            if (!response.ok) {
                throw new Error(`注册用户API响应错误: ${response.status}`);
            }
            const data = await response.json();
            if (data.success) {
                console.log(`[registerWalletUser] 用户注册成功:`, data.user);
                return data.user;
            } else {
                throw new Error(data.error || '用户注册失败');
            }
        } catch (error) {
            console.error('[registerWalletUser] 注册用户失败:', error);
            throw error;
        }
    },

    // ====================================================================
    // REFACTORED MOBILE REDIRECT LOGIC
    // ====================================================================
    async tryMobileWalletRedirect(walletType) {
        if (!this.isMobile()) {
            return false;
        }
        
        try {
            console.log(`[tryMobileWalletRedirect] 开始尝试${walletType}钱包跳转`);
            
            let universalLinkUrl = '';
            const redirectUrl = window.location.href;
            const baseUrl = window.location.origin;
            
            if (walletType === 'phantom' || walletType === 'solana') {
                const connectParams = new URLSearchParams({
                    dapp_encryption_public_key: this.generateRandomKey(),
                    cluster: 'mainnet-beta',
                    app_url: encodeURIComponent(baseUrl), // Phantom docs recommend encoding app_url
                    redirect_link: redirectUrl
                }).toString();
                universalLinkUrl = `https://phantom.app/ul/v1/connect?${connectParams}`;

            } else if (walletType === 'ethereum' || walletType === 'metamask') {
                universalLinkUrl = `https://metamask.app.link/dapp/${window.location.host}${window.location.pathname}`;

            } else {
                console.warn(`[tryMobileWalletRedirect] 不支持的钱包类型: ${walletType}`);
                return false;
            }
            
            sessionStorage.setItem('pendingWalletConnection', walletType);
            sessionStorage.setItem('walletConnectionStartTime', Date.now().toString());
            
            console.log(`[tryMobileWalletRedirect] 正在跳转到: ${universalLinkUrl}`);
            window.location.href = universalLinkUrl;
            
            // 返回一个永远不会解析的Promise，以防止后续代码（例如显示“下载”提示）执行。
            return new Promise(() => {}); 
            
        } catch (error) {
            console.error(`[tryMobileWalletRedirect] 移动端钱包跳转失败:`, error);
            return false;
        }
    },

    generateRandomKey() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    }
}

// 立即将walletState暴露到全局作用域，确保其他文件可以立即访问
window.walletState = walletState;
console.log('钱包状态对象已暴露到全局作用域');

// 添加钱包状态恢复功能
function recoverWalletStateFromStorage() {
    // ... (Implementation from file)
}

// 立即尝试恢复钱包状态
recoverWalletStateFromStorage();

// 页面初始化时就自动调用钱包初始化方法
document.addEventListener('DOMContentLoaded', async function() {
    // ... (Implementation from file)
});

function showSuccess(message, container = null) {
    // ... (Implementation from file)
}

function showError(message, container = null) {
    // ... (Implementation from file)
}

// 初始化事件并注册全局点击监听器
document.addEventListener('DOMContentLoaded', function() {
    // ... (Implementation from file)
});

function refreshAssetInfo() {
    // ... (Implementation from file)
}

function createDefaultAssetData(assetId) {
    // ... (Implementation from file)
}

async function fetchWithMultipleUrls(urls) {
    // ... (Implementation from file)
}

function updateAssetInfoDisplay(data) {
    // ... (Implementation from file)
}

function formatNumber(num) {
    // ... (Implementation from file)
}

function formatCurrency(value) {
    // ... (Implementation from file)
}

window.refreshAssetInfoNow = refreshAssetInfo;

async function signAndConfirmTransaction(transactionData) {
  // ... (Implementation from file)
}

async function signEthereumTransaction(transactionData) {
  // ... (Implementation from file)
}

async function signSolanaTransaction(transactionData) {
  // ... (Implementation from file)
}

window.signAndConfirmTransaction = signAndConfirmTransaction;

// ====================================================================
// REFACTORED AND SIMPLIFIED window.wallet
// ====================================================================
window.wallet = {
    getCurrentWallet: function() {
        return window.walletState?.getCurrentWallet?.();
    },
    
    transferToken: async function(tokenSymbol, to, amount) {
        return window.walletState?.transferToken?.(tokenSymbol, to, amount);
    }
}

// 确保已有walletState对象
if (!window.walletState) {
    console.warn('walletState未找到，使用window.wallet时将无法获取钱包信息');
}

// ... (rest of the helper functions at the end of the file)