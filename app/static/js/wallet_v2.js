
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

    openWalletSelector() {
        try {
            console.log('[openWalletSelector] 打开钱包选择器');
            
            // 如果已有钱包选择器打开，先关闭
            walletState.closeWalletSelector();
            
            // 如果已经连接了钱包，先断开连接
            if (this.connected) {
                console.log('[openWalletSelector] 已连接钱包，先断开现有连接');
                // 只断开连接但不刷新页面
                this.disconnect(false); 
            }
            
            // 创建钱包选择器
            const walletSelector = document.createElement('div');
            walletSelector.id = 'walletSelector';
            walletSelector.className = 'wallet-selector-modal';
            walletSelector.setAttribute('data-bs-backdrop', 'static');
            walletSelector.style.position = 'fixed';
            walletSelector.style.top = '0';
            walletSelector.style.left = '0';
            walletSelector.style.width = '100%';
            walletSelector.style.height = '100%';
            walletSelector.style.backgroundColor = 'rgba(0,0,0,0.5)';
            walletSelector.style.zIndex = '9999';
            walletSelector.style.display = 'flex';
            walletSelector.style.alignItems = 'center';
            walletSelector.style.justifyContent = 'center';
            
            // 创建钱包选择器内容
            const walletSelectorContent = document.createElement('div');
            walletSelectorContent.className = 'wallet-selector-content';
            walletSelectorContent.style.backgroundColor = '#fff';
            walletSelectorContent.style.borderRadius = '10px';
            walletSelectorContent.style.padding = '20px';
            walletSelectorContent.style.width = '90%';
            walletSelectorContent.style.maxWidth = '450px';
            walletSelectorContent.style.maxHeight = '90vh';
            walletSelectorContent.style.overflow = 'auto';
            
            // 添加标题
            const title = document.createElement('h5');
            title.textContent = window._('Select Wallet') || '选择钱包';
            title.style.marginBottom = '15px';
            title.style.display = 'flex';
            title.style.justifyContent = 'space-between';
            title.style.alignItems = 'center';
            
            // 添加关闭按钮
            const closeButton = document.createElement('button');
            closeButton.innerHTML = '&times;';
            closeButton.style.background = 'none';
            closeButton.style.border = 'none';
            closeButton.style.fontSize = '24px';
            closeButton.style.cursor = 'pointer';
            closeButton.onclick = () => {
                walletState.closeWalletSelector();
            };
            
            title.appendChild(closeButton);
            walletSelectorContent.appendChild(title);
            
            // 添加钱包选项 - 使用wallet-grid样式
            const walletGrid = document.createElement('div');
            walletGrid.className = 'wallet-grid';
            walletGrid.style.display = 'grid';
            walletGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
            walletGrid.style.gap = '15px';
            
            // 定义钱包列表
            const wallets = [
                {
                    name: 'Phantom',
                    icon: '/static/images/wallets/phantom.png',
                    class: 'phantom',
                    type: 'phantom',
                    onClick: () => this.connect('phantom')
                },
                {
                    name: 'MetaMask',
                    icon: '/static/images/wallets/MetaMask.png', // 使用正确的文件名大小写
                    class: 'ethereum',
                    type: 'ethereum',
                    onClick: () => this.connect('ethereum')
                }
            ];
            
            // 创建钱包选项
            wallets.forEach(wallet => {
                const option = document.createElement('div');
                option.className = 'wallet-option';
                option.setAttribute('data-wallet-type', wallet.type);
                option.style.display = 'flex';
                option.style.flexDirection = 'column';
                option.style.alignItems = 'center';
                option.style.padding = '10px';
                option.style.borderRadius = '8px';
                option.style.cursor = 'pointer';
                option.style.transition = 'all 0.2s ease';
                option.style.border = '1px solid #eee';
                
                // 悬停效果
                option.onmouseover = function() {
                    this.style.backgroundColor = '#f5f8ff';
                    this.style.transform = 'translateY(-2px)';
                    this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.05)';
                };
                
                option.onmouseout = function() {
                    this.style.backgroundColor = '#fff';
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = 'none';
                };
                
                // 创建图标容器
                const iconContainer = document.createElement('div');
                iconContainer.className = 'wallet-icon-container';
                iconContainer.style.marginBottom = '8px';
                
                // 创建图标包装器
                const iconWrapper = document.createElement('div');
                iconWrapper.className = `wallet-icon-wrapper ${wallet.class}`;
                iconWrapper.style.width = '40px';
                iconWrapper.style.height = '40px';
                iconWrapper.style.display = 'flex';
                iconWrapper.style.alignItems = 'center';
                iconWrapper.style.justifyContent = 'center';
                
                // 添加图标
                const icon = document.createElement('img');
                icon.src = wallet.icon;
                icon.alt = wallet.name;
                icon.style.width = '32px';
                icon.style.height = '32px';
                
                // 添加钱包名称
                const name = document.createElement('span');
                name.className = 'wallet-name';
                name.textContent = wallet.name;
                name.style.fontSize = '12px';
                name.style.fontWeight = '500';
                
                // 组装选项
                iconWrapper.appendChild(icon);
                iconContainer.appendChild(iconWrapper);
                option.appendChild(iconContainer);
                option.appendChild(name);
                
                // 添加点击事件
                option.onclick = () => {
                    // 记录点击的钱包类型，用于跟踪钱包应用返回情况
                    localStorage.setItem('pendingWalletType', wallet.type);
                    
                    // 移除钱包选择器
                    walletState.closeWalletSelector();
                    
                    // 在移动设备上设置从钱包应用返回的标记
                    if (this.isMobile()) {
                        sessionStorage.setItem('returningFromWalletApp', 'true');
                        this.pendingWalletAppOpen = true;
                        this.pendingWalletType = wallet.type;
                    }
                    
                    // 调用连接方法
                    this.connect(wallet.type);
                };
                
                // 添加到网格
                walletGrid.appendChild(option);
            });
            
            // 添加选项到钱包选择器
            walletSelectorContent.appendChild(walletGrid);
            
            // 添加内容到选择器
            walletSelector.appendChild(walletSelectorContent);
            
            // 添加选择器到页面
            document.body.appendChild(walletSelector);
            
            // 点击选择器背景关闭
            walletSelector.addEventListener('click', (e) => {
                if (e.target === walletSelector) {
                    walletState.closeWalletSelector();
                }
            });
            
            console.log('[openWalletSelector] 钱包选择器已显示');
            
            // 发送钱包选择器打开事件
            document.dispatchEvent(new CustomEvent('walletSelectorOpened'));
            
            return walletSelector;
        } catch (error) {
            console.error('[openWalletSelector] 打开钱包选择器失败:', error);
            return null;
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
