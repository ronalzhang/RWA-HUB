/**
 * RWA-HUB 统一钱包管理器
 * 版本: 2.0.0
 * 解决移动端钱包连接问题和代码重复问题
 */

// 防止重复加载
if (window.RWA_WALLET_MANAGER_LOADED) {
    console.warn('Wallet manager already loaded');
} else {
    window.RWA_WALLET_MANAGER_LOADED = true;

    // 调试模式
    const DEBUG_MODE = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' || 
                       window.DEBUG_MODE === true;

    // 调试日志函数
    function debugLog(...args) {
        if (DEBUG_MODE) {
            console.log('[WalletManager]', ...args);
        }
    }

    function debugError(...args) {
        console.error('[WalletManager]', ...args);
    }

    // 统一钱包管理器
    class WalletManager {
        constructor() {
            this.state = {
                address: null,
                walletType: null,
                connected: false,
                isAdmin: false,
                balance: 0,
                commissionBalance: 0,
                nativeBalance: 0,
                connecting: false,
                chainId: null,
                assets: [],
                provider: null,
                initialized: false
            };

            this.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            this.callbacks = [];
            this.retryCount = 0;
            this.maxRetries = 3;
        }

        // 初始化钱包管理器
        async init() {
            try {
                debugLog('初始化钱包管理器...');
                
                if (this.state.initialized) {
                    debugLog('钱包管理器已初始化');
                    return true;
                }

                // 检查是否从钱包App返回
                if (this.isMobile) {
                    await this.handleMobileWalletReturn();
                }

                // 恢复之前的连接状态
                await this.restorePreviousConnection();

                // 设置事件监听器
                this.setupEventListeners();

                this.state.initialized = true;
                debugLog('钱包管理器初始化完成');
                return true;

            } catch (error) {
                debugError('初始化钱包管理器失败:', error);
                return false;
            }
        }

        // 处理移动端钱包App返回
        async handleMobileWalletReturn() {
            const pendingWalletType = sessionStorage.getItem('pendingWalletConnection');
            const connectionStartTime = sessionStorage.getItem('walletConnectionStartTime');
            
            if (pendingWalletType && connectionStartTime) {
                const timeDiff = Date.now() - parseInt(connectionStartTime);
                
                // 如果在5分钟内返回，尝试连接
                if (timeDiff < 300000) {
                    debugLog(`检测到从${pendingWalletType}钱包App返回，尝试连接...`);
                    
                    // 等待页面完全加载
                    await this.waitForPageReady();
                    
                    // 尝试连接钱包
                    setTimeout(async () => {
                        try {
                            const success = await this.connect(pendingWalletType, true);
                            if (success) {
                                debugLog('从钱包App返回后连接成功');
                                // 清除临时标记
                                sessionStorage.removeItem('pendingWalletConnection');
                                sessionStorage.removeItem('walletConnectionStartTime');
                            }
                        } catch (error) {
                            debugError('从钱包App返回后连接失败:', error);
                        }
                    }, 1000);
                }
            }
        }

        // 等待页面准备就绪
        waitForPageReady() {
            return new Promise(resolve => {
                if (document.readyState === 'complete') {
                    resolve();
                } else {
                    window.addEventListener('load', resolve);
                }
            });
        }

        // 恢复之前的连接状态
        async restorePreviousConnection() {
            const storedWalletType = localStorage.getItem('walletType');
            const storedWalletAddress = localStorage.getItem('walletAddress');
            
            if (storedWalletType && storedWalletAddress) {
                debugLog('恢复之前的钱包连接:', storedWalletType, storedWalletAddress);
                
                this.state.walletType = storedWalletType;
                this.state.address = storedWalletAddress;
                this.state.connected = true;
                
                this.updateUI();
                this.notifyStateChange();
                
                // 尝试静默重连
                try {
                    await this.connect(storedWalletType, true);
                } catch (error) {
                    debugLog('静默重连失败:', error);
                }
            }
        }

        // 设置事件监听器
        setupEventListeners() {
            // 页面可见性变化
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible' && this.state.connected) {
                    this.checkConnection();
                }
            });

            // 存储变化
            window.addEventListener('storage', (event) => {
                if (event.key === 'walletAddress' || event.key === 'walletType') {
                    this.handleStorageChange();
                }
            });

            // 页面卸载前保存状态
            window.addEventListener('beforeunload', () => {
                if (this.state.connected && this.state.walletType && this.state.address) {
                    localStorage.setItem('walletType', this.state.walletType);
                    localStorage.setItem('walletAddress', this.state.address);
                }
            });
        }

        // 连接钱包
        async connect(walletType, isReconnect = false) {
            try {
                debugLog(`连接钱包: ${walletType}, 重连: ${isReconnect}`);
                
                this.state.connecting = true;
                this.updateUI();

                // 移动端处理
                if (this.isMobile && !isReconnect) {
                    const deepLinkSuccess = await this.handleMobileWalletConnection(walletType);
                    if (deepLinkSuccess) {
                        this.state.connecting = false;
                        this.updateUI();
                        return true;
                    }
                }

                let success = false;

                // 根据钱包类型连接
                if (walletType === 'phantom' || walletType === 'solana') {
                    success = await this.connectPhantom(isReconnect);
                } else if (walletType === 'ethereum' || walletType === 'metamask') {
                    success = await this.connectEthereum(isReconnect);
                } else {
                    throw new Error(`不支持的钱包类型: ${walletType}`);
                }

                if (success) {
                    debugLog('钱包连接成功');
                    this.notifyStateChange();
                    
                    // 保存连接状态
                    localStorage.setItem('walletType', this.state.walletType);
                    localStorage.setItem('walletAddress', this.state.address);
                } else {
                    debugLog('钱包连接失败');
                    this.clearState();
                }

                return success;

            } catch (error) {
                debugError('连接钱包失败:', error);
                this.clearState();
                this.showError('连接失败', error.message);
                return false;
            } finally {
                this.state.connecting = false;
                this.updateUI();
            }
        }

        // 处理移动端钱包连接
        async handleMobileWalletConnection(walletType) {
            try {
                debugLog(`处理移动端${walletType}钱包连接`);
                
                let deepLinkUrl = '';
                let universalLinkUrl = '';
                let appStoreUrl = '';
                
                const baseUrl = window.location.origin;
                const currentUrl = window.location.href;
                
                if (walletType === 'phantom' || walletType === 'solana') {
                    // Phantom钱包链接
                    const connectParams = new URLSearchParams({
                        dapp_encryption_public_key: this.generateRandomKey(),
                        cluster: 'mainnet-beta',
                        app_url: baseUrl,
                        redirect_link: currentUrl
                    }).toString();
                    
                    deepLinkUrl = `phantom://v1/connect?${connectParams}`;
                    universalLinkUrl = `https://phantom.app/ul/v1/connect?${connectParams}`;
                    
                    if (this.isIOS()) {
                        appStoreUrl = 'https://apps.apple.com/app/phantom-solana-wallet/id1598432977';
                    } else {
                        appStoreUrl = 'https://play.google.com/store/apps/details?id=app.phantom';
                    }
                    
                } else if (walletType === 'ethereum' || walletType === 'metamask') {
                    // MetaMask钱包链接
                    deepLinkUrl = `https://metamask.app.link/dapp/${window.location.host}${window.location.pathname}`;
                    universalLinkUrl = deepLinkUrl;
                    
                    if (this.isIOS()) {
                        appStoreUrl = 'https://apps.apple.com/app/metamask/id1438144202';
                    } else {
                        appStoreUrl = 'https://play.google.com/store/apps/details?id=io.metamask';
                    }
                }

                // 设置返回检测标记
                sessionStorage.setItem('pendingWalletConnection', walletType);
                sessionStorage.setItem('walletConnectionStartTime', Date.now().toString());

                // 尝试深度链接
                const deepLinkSuccess = await this.attemptDeepLink(deepLinkUrl);
                if (deepLinkSuccess) {
                    debugLog('深度链接跳转成功');
                    return true;
                }

                // 尝试通用链接
                const universalLinkSuccess = await this.attemptUniversalLink(universalLinkUrl);
                if (universalLinkSuccess) {
                    debugLog('通用链接跳转成功');
                    return true;
                }

                // 提示下载应用
                const walletName = walletType === 'phantom' ? 'Phantom' : 'MetaMask';
                const shouldDownload = confirm(`${walletName} 钱包应用未检测到。是否前往下载？`);
                
                if (shouldDownload && appStoreUrl) {
                    window.open(appStoreUrl, '_blank');
                }

                return false;

            } catch (error) {
                debugError('移动端钱包连接处理失败:', error);
                return false;
            }
        }

        // 尝试深度链接
        async attemptDeepLink(deepLinkUrl) {
            return new Promise((resolve) => {
                const timeout = setTimeout(() => resolve(false), 2500);
                
                const iframe = document.createElement('iframe');
                iframe.style.display = 'none';
                iframe.src = deepLinkUrl;
                
                document.body.appendChild(iframe);
                
                const startTime = Date.now();
                const checkVisibility = () => {
                    if (document.hidden || Date.now() - startTime > 1000) {
                        clearTimeout(timeout);
                        if (iframe.parentNode) {
                            document.body.removeChild(iframe);
                        }
                        resolve(true);
                    } else {
                        setTimeout(checkVisibility, 100);
                    }
                };
                
                setTimeout(() => {
                    checkVisibility();
                    setTimeout(() => {
                        if (iframe.parentNode) {
                            document.body.removeChild(iframe);
                        }
                    }, 1000);
                }, 500);
            });
        }

        // 尝试通用链接
        async attemptUniversalLink(universalLinkUrl) {
            return new Promise((resolve) => {
                const timeout = setTimeout(() => resolve(false), 3000);
                
                const link = document.createElement('a');
                link.href = universalLinkUrl;
                link.target = '_blank';
                link.style.display = 'none';
                
                document.body.appendChild(link);
                link.click();
                
                const startTime = Date.now();
                const checkVisibility = () => {
                    if (document.hidden || Date.now() - startTime > 1500) {
                        clearTimeout(timeout);
                        if (link.parentNode) {
                            document.body.removeChild(link);
                        }
                        resolve(true);
                    } else if (Date.now() - startTime < 2500) {
                        setTimeout(checkVisibility, 100);
                    }
                };
                
                setTimeout(() => {
                    checkVisibility();
                    setTimeout(() => {
                        if (link.parentNode) {
                            document.body.removeChild(link);
                        }
                    }, 1000);
                }, 500);
            });
        }

        // 连接Phantom钱包
        async connectPhantom(isReconnect = false) {
            try {
                debugLog('连接Phantom钱包...');
                
                // 等待Phantom加载
                if (!window.solana) {
                    await this.waitForPhantom();
                }
                
                if (!window.solana || !window.solana.isPhantom) {
                    throw new Error('Phantom钱包未安装或不可用');
                }

                let response;
                if (isReconnect) {
                    // 静默重连
                    response = await window.solana.connect({ onlyIfTrusted: true });
                } else {
                    // 正常连接
                    response = await window.solana.connect();
                }

                if (response && response.publicKey) {
                    this.state.address = response.publicKey.toString();
                    this.state.walletType = 'phantom';
                    this.state.connected = true;
                    this.state.provider = window.solana;
                    
                    debugLog('Phantom钱包连接成功:', this.state.address);
                    
                    // 设置事件监听
                    this.setupPhantomListeners();
                    
                    return true;
                }
                
                return false;

            } catch (error) {
                if (error.code === 4001 || error.message.includes('User rejected')) {
                    debugLog('用户拒绝连接Phantom钱包');
                    return false;
                }
                debugError('连接Phantom钱包失败:', error);
                throw error;
            }
        }

        // 连接以太坊钱包
        async connectEthereum(isReconnect = false) {
            try {
                debugLog('连接以太坊钱包...');
                
                if (!window.ethereum) {
                    throw new Error('MetaMask钱包未安装或不可用');
                }

                let accounts;
                if (isReconnect) {
                    // 静默重连
                    accounts = await window.ethereum.request({ method: 'eth_accounts' });
                } else {
                    // 正常连接
                    accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                }

                if (accounts && accounts.length > 0) {
                    this.state.address = accounts[0];
                    this.state.walletType = 'ethereum';
                    this.state.connected = true;
                    this.state.provider = window.ethereum;
                    
                    debugLog('以太坊钱包连接成功:', this.state.address);
                    
                    // 设置事件监听
                    this.setupEthereumListeners();
                    
                    return true;
                }
                
                return false;

            } catch (error) {
                if (error.code === 4001) {
                    debugLog('用户拒绝连接以太坊钱包');
                    return false;
                }
                debugError('连接以太坊钱包失败:', error);
                throw error;
            }
        }

        // 等待Phantom加载
        waitForPhantom(timeout = 15000) {
            return new Promise((resolve, reject) => {
                if (window.solana && window.solana.isPhantom) {
                    resolve();
                    return;
                }

                let attempts = 0;
                const maxAttempts = timeout / 200;

                const checkInterval = setInterval(() => {
                    attempts++;
                    
                    if (window.solana && window.solana.isPhantom) {
                        clearInterval(checkInterval);
                        clearTimeout(timeoutId);
                        debugLog('Phantom钱包检测成功，尝试次数:', attempts);
                        resolve();
                    } else if (attempts >= maxAttempts) {
                        clearInterval(checkInterval);
                        clearTimeout(timeoutId);
                        
                        // 移动端给出更友好的提示
                        if (this.isMobile()) {
                            reject(new Error('请确保已安装Phantom钱包App，并从钱包App返回后重试'));
                        } else {
                            reject(new Error('Phantom钱包扩展未检测到，请安装Phantom浏览器扩展'));
                        }
                    }
                }, 200);

                const timeoutId = setTimeout(() => {
                    clearInterval(checkInterval);
                    if (this.isMobile()) {
                        reject(new Error('钱包连接超时，请确保已安装Phantom App'));
                    } else {
                        reject(new Error('Phantom钱包加载超时'));
                    }
                }, timeout);
            });
        }

        // 设置Phantom事件监听
        setupPhantomListeners() {
            if (window.solana && window.solana.on) {
                window.solana.on('disconnect', () => {
                    debugLog('Phantom钱包断开连接');
                    this.clearState();
                    this.updateUI();
                    this.notifyStateChange();
                });

                window.solana.on('accountChanged', (publicKey) => {
                    if (publicKey) {
                        debugLog('Phantom账户变更:', publicKey.toString());
                        this.state.address = publicKey.toString();
                        this.updateUI();
                        this.notifyStateChange();
                    } else {
                        this.clearState();
                        this.updateUI();
                        this.notifyStateChange();
                    }
                });
            }
        }

        // 设置以太坊事件监听
        setupEthereumListeners() {
            if (window.ethereum && window.ethereum.on) {
                window.ethereum.on('accountsChanged', (accounts) => {
                    if (accounts.length === 0) {
                        debugLog('以太坊钱包断开连接');
                        this.clearState();
                    } else {
                        debugLog('以太坊账户变更:', accounts[0]);
                        this.state.address = accounts[0];
                    }
                    this.updateUI();
                    this.notifyStateChange();
                });

                window.ethereum.on('chainChanged', (chainId) => {
                    debugLog('以太坊链变更:', chainId);
                    this.state.chainId = chainId;
                    this.updateUI();
                    this.notifyStateChange();
                });
            }
        }

        // 断开钱包连接
        async disconnect(reload = true) {
            try {
                debugLog('断开钱包连接');
                
                // 清除存储的连接信息
                localStorage.removeItem('walletType');
                localStorage.removeItem('walletAddress');
                sessionStorage.removeItem('pendingWalletConnection');
                sessionStorage.removeItem('walletConnectionStartTime');
                
                // 清除状态
                this.clearState();
                
                // 更新UI
                this.updateUI();
                this.notifyStateChange();
                
                if (reload) {
                    window.location.reload();
                }
                
                return true;

            } catch (error) {
                debugError('断开钱包连接失败:', error);
                return false;
            }
        }

        // 打开钱包选择器
        openWalletSelector() {
            try {
                debugLog('打开钱包选择器');
                
                // 关闭现有选择器
                this.closeWalletSelector();
                
                // 如果已连接，先断开
                if (this.state.connected) {
                    this.disconnect(false);
                }
                
                // 创建选择器
                const selector = this.createWalletSelector();
                document.body.appendChild(selector);
                
                return selector;

            } catch (error) {
                debugError('打开钱包选择器失败:', error);
                return null;
            }
        }

        // 创建钱包选择器
        createWalletSelector() {
            const selector = document.createElement('div');
            selector.id = 'walletSelector';
            selector.className = 'wallet-selector-modal';
            selector.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
            `;

            const content = document.createElement('div');
            content.className = 'wallet-selector-content';
            content.style.cssText = `
                background-color: #fff;
                border-radius: 10px;
                padding: 20px;
                width: 90%;
                max-width: 450px;
                max-height: 90vh;
                overflow: auto;
            `;

            // 标题
            const title = document.createElement('h5');
            title.textContent = '选择钱包';
            title.style.cssText = `
                margin-bottom: 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            `;

            // 关闭按钮
            const closeButton = document.createElement('button');
            closeButton.innerHTML = '&times;';
            closeButton.style.cssText = `
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
            `;
            closeButton.onclick = () => this.closeWalletSelector();

            title.appendChild(closeButton);
            content.appendChild(title);

            // 钱包网格
            const walletGrid = document.createElement('div');
            walletGrid.style.cssText = `
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
            `;

            // 钱包选项
            const wallets = [
                {
                    name: 'Phantom',
                    icon: '/static/images/wallets/phantom.png',
                    type: 'phantom'
                },
                {
                    name: 'MetaMask',
                    icon: '/static/images/wallets/MetaMask.png',
                    type: 'ethereum'
                }
            ];

            wallets.forEach(wallet => {
                const option = this.createWalletOption(wallet);
                walletGrid.appendChild(option);
            });

            content.appendChild(walletGrid);
            selector.appendChild(content);

            // 点击背景关闭
            selector.addEventListener('click', (e) => {
                if (e.target === selector) {
                    this.closeWalletSelector();
                }
            });

            return selector;
        }

        // 创建钱包选项
        createWalletOption(wallet) {
            const option = document.createElement('div');
            option.className = 'wallet-option';
            option.style.cssText = `
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 15px;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.2s ease;
                border: 1px solid #eee;
                background: #fff;
            `;

            // 悬停效果
            option.onmouseover = function() {
                this.style.backgroundColor = '#f5f8ff';
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
            };

            option.onmouseout = function() {
                this.style.backgroundColor = '#fff';
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = 'none';
            };

            // 图标
            const icon = document.createElement('img');
            icon.src = wallet.icon;
            icon.alt = wallet.name;
            icon.style.cssText = `
                width: 40px;
                height: 40px;
                margin-bottom: 10px;
            `;

            // 名称
            const name = document.createElement('span');
            name.textContent = wallet.name;
            name.style.cssText = `
                font-size: 14px;
                font-weight: 500;
            `;

            option.appendChild(icon);
            option.appendChild(name);

            // 点击事件
            option.onclick = () => {
                // 设置移动端标记
                if (this.isMobile) {
                    sessionStorage.setItem('pendingWalletConnection', wallet.type);
                    sessionStorage.setItem('walletConnectionStartTime', Date.now().toString());
                }

                this.closeWalletSelector();
                this.connect(wallet.type);
            };

            return option;
        }

        // 关闭钱包选择器
        closeWalletSelector() {
            const selector = document.getElementById('walletSelector');
            if (selector) {
                selector.remove();
                debugLog('钱包选择器已关闭');
                return true;
            }
            return false;
        }

        // 清除状态
        clearState() {
            this.state = {
                ...this.state,
                address: null,
                walletType: null,
                connected: false,
                isAdmin: false,
                balance: 0,
                commissionBalance: 0,
                nativeBalance: 0,
                connecting: false,
                chainId: null,
                assets: [],
                provider: null
            };
        }

        // 更新UI
        updateUI() {
            // 更新钱包按钮
            const walletBtn = document.getElementById('walletBtn');
            if (walletBtn) {
                if (this.state.connected && this.state.address) {
                    walletBtn.textContent = this.formatAddress(this.state.address);
                    walletBtn.classList.add('connected');
                } else if (this.state.connecting) {
                    walletBtn.textContent = '连接中...';
                    walletBtn.classList.remove('connected');
                } else {
                    walletBtn.textContent = '连接钱包';
                    walletBtn.classList.remove('connected');
                }
            }

            // 更新购买按钮
            this.updateBuyButtons();
        }

        // 更新购买按钮
        updateBuyButtons() {
            const buyButtons = document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"], #buyButton');
            
            buyButtons.forEach(btn => {
                if (this.state.connected) {
                    btn.textContent = 'Buy';
                    btn.disabled = false;
                } else {
                    btn.textContent = 'Connect Wallet';
                    btn.disabled = false;
                }
            });
        }

        // 格式化地址
        formatAddress(address) {
            if (!address) return '';
            if (address.length > 10) {
                return address.slice(0, 6) + '...' + address.slice(-4);
            }
            return address;
        }

        // 检查连接状态
        async checkConnection() {
            try {
                if (!this.state.connected) return;

                let isStillConnected = false;

                if (this.state.walletType === 'phantom' && window.solana) {
                    isStillConnected = window.solana.isConnected;
                } else if (this.state.walletType === 'ethereum' && window.ethereum) {
                    const accounts = await window.ethereum.request({ method: 'eth_accounts' });
                    isStillConnected = accounts && accounts.length > 0;
                }

                if (!isStillConnected) {
                    debugLog('钱包连接已断开');
                    this.clearState();
                    this.updateUI();
                    this.notifyStateChange();
                }

            } catch (error) {
                debugError('检查连接状态失败:', error);
            }
        }

        // 处理存储变化
        handleStorageChange() {
            const storedWalletType = localStorage.getItem('walletType');
            const storedWalletAddress = localStorage.getItem('walletAddress');

            if (!storedWalletType || !storedWalletAddress) {
                if (this.state.connected) {
                    this.clearState();
                    this.updateUI();
                    this.notifyStateChange();
                }
            }
        }

        // 通知状态变化
        notifyStateChange() {
            this.callbacks.forEach(callback => {
                try {
                    callback(this.state);
                } catch (error) {
                    debugError('状态变化回调执行失败:', error);
                }
            });

            // 发送自定义事件
            const event = new CustomEvent(this.state.connected ? 'walletConnected' : 'walletDisconnected', {
                detail: this.state
            });
            document.dispatchEvent(event);
        }

        // 添加状态变化监听器
        onStateChange(callback) {
            this.callbacks.push(callback);
        }

        // 移除状态变化监听器
        offStateChange(callback) {
            const index = this.callbacks.indexOf(callback);
            if (index > -1) {
                this.callbacks.splice(index, 1);
            }
        }

        // 显示错误
        showError(title, message) {
            debugError(`${title}: ${message}`);
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

        // 工具方法
        isIOS() {
            return /iPad|iPhone|iPod/.test(navigator.userAgent);
        }

        generateRandomKey() {
            const array = new Uint8Array(32);
            crypto.getRandomValues(array);
            return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
        }

        // 获取器方法
        getAddress() {
            return this.state.address;
        }

        getWalletType() {
            return this.state.walletType;
        }

        isConnected() {
            return this.state.connected;
        }

        getState() {
            return { ...this.state };
        }
    }

    // 创建全局钱包管理器实例
    window.walletManager = new WalletManager();
    
    // 兼容性：保持原有的walletState接口
    window.walletState = {
        get address() { return window.walletManager.state.address; },
        get walletType() { return window.walletManager.state.walletType; },
        get connected() { return window.walletManager.state.connected; },
        get isConnected() { return window.walletManager.state.connected; },
        get connecting() { return window.walletManager.state.connecting; },
        get balance() { return window.walletManager.state.balance; },
        get isAdmin() { return window.walletManager.state.isAdmin; },
        
        init: () => window.walletManager.init(),
        connect: (type) => window.walletManager.connect(type),
        disconnect: (reload) => window.walletManager.disconnect(reload),
        openWalletSelector: () => window.walletManager.openWalletSelector(),
        closeWalletSelector: () => window.walletManager.closeWalletSelector(),
        formatAddress: (addr) => window.walletManager.formatAddress(addr),
        onStateChange: (cb) => window.walletManager.onStateChange(cb),
        offStateChange: (cb) => window.walletManager.offStateChange(cb)
    };

    // 自动初始化
    document.addEventListener('DOMContentLoaded', () => {
        window.walletManager.init();
    });

    debugLog('钱包管理器加载完成');
}