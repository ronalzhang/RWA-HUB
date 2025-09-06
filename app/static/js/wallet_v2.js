
/**
 * RWA-HUB 钱包管理模块 (v2)
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
            
            if (storedWalletType && storedWalletAddress) {
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
    
    checkWalletConsistency(forceUpdate = false) {},
    
    async handleStorageChange() {
        this.checkWalletConsistency(true);
    },
    
    updateDetailPageButtonState() {},
    
    waitForDocumentReady() {
        return new Promise(resolve => {
            if (document.readyState === 'complete' || document.readyState === 'interactive') {
                resolve();
            } else {
                document.addEventListener('DOMContentLoaded', () => resolve());
            }
        });
    },
    
    clearStoredWalletData() {},
    
    async checkWalletConnection() {},
    
    clearState() {},
    
    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    },

    async connect(walletType) {
        this.connecting = true;
        this.updateUI();
        
        if (this.isMobile() && !this._isReconnecting) {
            const deepLinkSuccess = await this.tryMobileWalletRedirect(walletType);
            if (deepLinkSuccess) {
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
    
    updateUI() {},
    
    triggerWalletStateChanged(details = {}) {},
    
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
    
    async disconnect(reload = true) {},
    
    async switchWallet() {},
    
    getConnectionStatus() {
        return this.connected;
    },
    
    getAddress() {
        return this.address;
    },
    
    getWalletType() {
        return this.walletType;
    },
    
    async checkIsAdmin() {},
    
    onStateChange(callback) {},
    
    offStateChange(callback) {},
    
    notifyStateChange(details = {}) {},
    
    updateAdminDisplay() {},
    
    shouldCheckAdminStatus() {},
    
    createOrShowDividendButtons() {},
    
    async getWalletBalance() {},
    
    async ensureSolanaLibrariesOptimized() {},
    
    async loadSolanaWeb3FromCDN() {},
    
    createBasicSplTokenInterface() {},
    
    createMinimalSolanaInterface() {},
    
    triggerBalanceUpdatedEvent() {},
    
    updateBalanceDisplay(balance = null) {},
    
    updateAssetsUI() {},

    openWalletSelector() {},

    closeWalletSelector() {},

    showWalletOptions() {},

    async getUserAssets(address) {},

    connectSolflare: async function() {},

    connectCoinbase: async function() {},

    connectSlope: async function() {},

    connectGlow: async function() {},

    async connectPhantom(isReconnect = false) {},

    checkIfReturningFromWalletApp(walletType) {},

    async connectEthereum(isReconnect = false) {},

    setupEthereumListeners() {},

    setupPhantomListeners() {},

    copyWalletAddress() {},
    
    showCopySuccess() {},
    
    async transferToken(tokenSymbol, to, amount) {},
    
    async transferSolanaToken(tokenSymbol, to, amount) {},
    
    delayedPhantomReconnect() {},
    
    checkTokenBalance: async function(tokenSymbol) {},
    
    async connectWallet(options) {},
    
    async getBalanceWithFallback(address, tokenSymbol) {},
    
    async getCommissionBalance() {},

    async getUSDCBalance() {},

    _getBalanceCache(key) {},

    _setBalanceCache(key, balance) {},

    async refreshAllBalances(force = false) {},

    async afterSuccessfulConnection(address, walletType, provider) {},

    showPhantomRetryOption() {},

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

    async tryMobileWalletRedirect(walletType) {
        if (!walletState.isMobile()) { // FIX: Use explicit reference to walletState
            return false;
        }
        
        try {
            console.log(`[tryMobileWalletRedirect] 开始尝试${walletType}钱包跳转`);
            
            let deepLinkUrl = '';
            let universalLinkUrl = '';
            let appStoreUrl = '';
            
            const baseUrl = window.location.origin;
            
            // 根据钱包类型设置不同的链接
            if (walletType === 'phantom' || walletType === 'solana') {
                // Phantom钱包的深度链接和通用链接
                const connectParams = new URLSearchParams({
                    dapp_encryption_public_key: this.generateRandomKey(),
                    cluster: 'mainnet-beta',
                    app_url: baseUrl,
                    redirect_link: window.location.href // FIX: Use raw URL to prevent double-encoding
                }).toString();
                
                deepLinkUrl = `phantom://v1/connect?${connectParams}`;
                universalLinkUrl = `https://phantom.app/ul/v1/connect?${connectParams}`;
                
                // 应用商店链接
                if (navigator.userAgent.toLowerCase().includes('iphone') || 
                    navigator.userAgent.toLowerCase().includes('ipad')) {
                    appStoreUrl = 'https://apps.apple.com/app/phantom-solana-wallet/id1598432977';
                } else {
                    appStoreUrl = 'https://play.google.com/store/apps/details?id=app.phantom';
                }
            } else if (walletType === 'ethereum' || walletType === 'metamask') {
                // MetaMask的深度链接
                deepLinkUrl = `https://metamask.app.link/dapp/${window.location.host}${window.location.pathname}`;
                universalLinkUrl = deepLinkUrl;
                
                // 应用商店链接
                if (navigator.userAgent.toLowerCase().includes('iphone') || 
                    navigator.userAgent.toLowerCase().includes('ipad')) {
                    appStoreUrl = 'https://apps.apple.com/app/metamask/id1438144202';
                } else {
                    appStoreUrl = 'https://play.google.com/store/apps/details?id=io.metamask';
                }
            } else {
                console.warn(`[tryMobileWalletRedirect] 不支持的钱包类型: ${walletType}`);
                return false;
            }
            
            // 设置钱包返回检测标记
            sessionStorage.setItem('pendingWalletConnection', walletType);
            sessionStorage.setItem('walletConnectionStartTime', Date.now().toString());
            
            // 尝试深度链接跳转
            console.log(`[tryMobileWalletRedirect] 尝试深度链接: ${deepLinkUrl}`);
            const deepLinkSuccess = await this.attemptDeepLink(deepLinkUrl);
            
            if (deepLinkSuccess) {
                console.log(`[tryMobileWalletRedirect] 深度链接跳转成功`);
                return true;
            }
            
            // 深度链接失败，尝试通用链接
            console.log(`[tryMobileWalletRedirect] 深度链接失败，尝试通用链接: ${universalLinkUrl}`);
            const universalLinkSuccess = await this.attemptUniversalLink(universalLinkUrl);
            
            if (universalLinkSuccess) {
                console.log(`[tryMobileWalletRedirect] 通用链接跳转成功`);
                return true;
            }
            
            // 所有跳转都失败，提示用户下载应用
            console.log(`[tryMobileWalletRedirect] 所有跳转失败，提示下载应用`);
            const shouldDownload = confirm(`${walletType === 'phantom' ? 'Phantom' : 'MetaMask'} wallet app not detected. Would you like to download it?`);
            
            if (shouldDownload && appStoreUrl) {
                window.open(appStoreUrl, '_blank');
            }
            
            return false;
            
        } catch (error) {
            console.error(`[tryMobileWalletRedirect] 移动端钱包跳转失败:`, error);
            return false;
        }
    },

    async attemptDeepLink(deepLinkUrl) {
        return new Promise((resolve) => {
            const timeout = setTimeout(() => {
                resolve(false);
            }, 2500); // 2.5秒超时
            
            // 创建隐藏的iframe尝试跳转
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = deepLinkUrl;
            
            document.body.appendChild(iframe);
            
            // 检测页面是否失去焦点（表示跳转成功）
            const startTime = Date.now();
            const checkVisibility = () => {
                if (document.hidden || Date.now() - startTime > 1000) {
                    clearTimeout(timeout);
                    document.body.removeChild(iframe);
                    resolve(true);
                } else {
                    setTimeout(checkVisibility, 100);
                }
            };
            
            setTimeout(() => {
                checkVisibility();
                // 清理iframe
                setTimeout(() => {
                    if (iframe && iframe.parentNode) {
                        document.body.removeChild(iframe);
                    }
                }, 1000);
            }, 500);
        });
    },

    async attemptUniversalLink(universalLinkUrl) {
        return new Promise((resolve) => {
            const timeout = setTimeout(() => {
                resolve(false);
            }, 3000); // 3秒超时
            
            // 创建隐藏的链接并点击
            const link = document.createElement('a');
            link.href = universalLinkUrl;
            link.target = '_blank';
            link.style.display = 'none';
            
            document.body.appendChild(link);
            link.click();
            
            // 检测页面是否失去焦点
            const startTime = Date.now();
            const checkVisibility = () => {
                if (document.hidden || Date.now() - startTime > 1500) {
                    clearTimeout(timeout);
                    document.body.removeChild(link);
                    resolve(true);
                } else if (Date.now() - startTime < 2500) {
                    setTimeout(checkVisibility, 100);
                }
            };
            
            setTimeout(() => {
                checkVisibility();
                // 清理链接
                setTimeout(() => {
                    if (link && link.parentNode) {
                        document.body.removeChild(link);
                    }
                }, 1000);
            }, 500);
        });
    },

    generateRandomKey() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    }
}

window.walletState = walletState;

// MINIMAL window.wallet for compatibility
window.wallet = {
    getCurrentWallet: function() {
        return window.walletState?.getCurrentWallet?.();
    },
    transferToken: async function(tokenSymbol, to, amount) {
        return window.walletState?.transferToken?.(tokenSymbol, to, amount);
    }
};

// All other functions are now part of walletState or are global helpers

// ... (rest of the file with global helpers)
