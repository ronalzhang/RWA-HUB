/**
 * 移动端钱包连接增强器
 * 专门处理移动端钱包连接问题
 * 版本: 1.0.0
 */

(function() {
    'use strict';

    // 防止重复加载
    if (window.MOBILE_WALLET_ENHANCER_LOADED) {
        return;
    }
    window.MOBILE_WALLET_ENHANCER_LOADED = true;

    console.log('[移动端钱包增强器] 开始加载...');

    // 移动端检测
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isAndroid = /Android/i.test(navigator.userAgent);

    // 移动端钱包增强器类
    class MobileWalletEnhancer {
        constructor() {
            this.debug = true;
            this.retryAttempts = 0;
            this.maxRetries = 3;
            this.connectionTimeout = 30000; // 30秒超时
            this.deepLinkTimeout = 3000; // 深度链接超时
            
            // 钱包配置
            this.walletConfigs = {
                phantom: {
                    name: 'Phantom',
                    deepLink: 'phantom://v1/connect',
                    universalLink: 'https://phantom.app/ul/v1/connect',
                    downloadUrls: {
                        ios: 'https://apps.apple.com/app/phantom-solana-wallet/id1598432977',
                        android: 'https://play.google.com/store/apps/details?id=app.phantom'
                    },
                    checkFunction: () => window.solana && window.solana.isPhantom
                },
                metamask: {
                    name: 'MetaMask',
                    deepLink: 'metamask://dapp/',
                    universalLink: 'https://metamask.app.link/dapp/',
                    downloadUrls: {
                        ios: 'https://apps.apple.com/app/metamask/id1438144202',
                        android: 'https://play.google.com/store/apps/details?id=io.metamask'
                    },
                    checkFunction: () => window.ethereum && window.ethereum.isMetaMask
                }
            };

            this.init();
        }

        log(...args) {
            if (this.debug) {
                console.log('[移动端钱包增强器]', ...args);
            }
        }

        error(...args) {
            console.error('[移动端钱包增强器]', ...args);
        }

        init() {
            if (!isMobile) {
                this.log('非移动端设备，跳过初始化');
                return;
            }

            this.log('初始化移动端钱包增强器');
            
            // 检查是否从钱包App返回
            this.checkWalletAppReturn();
            
            // 设置页面可见性监听
            this.setupVisibilityListener();
            
            // 增强现有的钱包连接功能
            this.enhanceWalletConnection();
            
            this.log('移动端钱包增强器初始化完成');
        }

        // 检查是否从钱包App返回
        checkWalletAppReturn() {
            const pendingConnection = sessionStorage.getItem('pendingWalletConnection');
            const connectionStartTime = sessionStorage.getItem('walletConnectionStartTime');
            
            if (pendingConnection && connectionStartTime) {
                const timeDiff = Date.now() - parseInt(connectionStartTime);
                
                // 如果在5分钟内返回
                if (timeDiff < 300000) {
                    this.log(`检测到从${pendingConnection}钱包App返回，时间差: ${timeDiff}ms`);
                    
                    // 延迟处理，等待页面完全加载
                    setTimeout(() => {
                        this.handleWalletAppReturn(pendingConnection);
                    }, 1000);
                } else {
                    this.log('钱包连接超时，清除临时数据');
                    this.clearPendingConnection();
                }
            }
        }

        // 处理从钱包App返回
        async handleWalletAppReturn(walletType) {
            try {
                this.log(`处理从${walletType}钱包App返回`);
                
                // 显示连接状态
                this.showConnectionStatus('正在连接钱包...');
                
                // 等待钱包对象加载
                const walletAvailable = await this.waitForWallet(walletType);
                
                if (walletAvailable) {
                    this.log(`${walletType}钱包对象已加载，尝试连接`);
                    
                    // 尝试连接
                    const connected = await this.attemptConnection(walletType);
                    
                    if (connected) {
                        this.log('钱包连接成功');
                        this.showConnectionStatus('钱包连接成功！', 'success');
                        this.clearPendingConnection();
                        
                        // 通知主应用
                        this.notifyConnectionSuccess(walletType);
                    } else {
                        this.log('钱包连接失败');
                        this.showConnectionStatus('连接失败，请重试', 'error');
                    }
                } else {
                    this.log(`${walletType}钱包对象加载失败`);
                    this.showConnectionStatus('钱包未检测到，请确保已安装钱包应用', 'error');
                }
                
            } catch (error) {
                this.error('处理钱包App返回失败:', error);
                this.showConnectionStatus('连接过程中发生错误', 'error');
            }
        }

        // 等待钱包对象加载
        waitForWallet(walletType, timeout = 10000) {
            return new Promise((resolve) => {
                const config = this.walletConfigs[walletType];
                if (!config) {
                    resolve(false);
                    return;
                }

                // 检查钱包是否已经可用
                if (config.checkFunction()) {
                    resolve(true);
                    return;
                }

                // 轮询检查
                const startTime = Date.now();
                const checkInterval = setInterval(() => {
                    if (config.checkFunction()) {
                        clearInterval(checkInterval);
                        resolve(true);
                    } else if (Date.now() - startTime > timeout) {
                        clearInterval(checkInterval);
                        resolve(false);
                    }
                }, 100);
            });
        }

        // 尝试连接钱包
        async attemptConnection(walletType) {
            try {
                if (walletType === 'phantom') {
                    return await this.connectPhantom();
                } else if (walletType === 'metamask') {
                    return await this.connectMetaMask();
                }
                return false;
            } catch (error) {
                this.error(`连接${walletType}失败:`, error);
                return false;
            }
        }

        // 连接Phantom钱包
        async connectPhantom() {
            try {
                if (!window.solana || !window.solana.isPhantom) {
                    throw new Error('Phantom钱包不可用');
                }

                const response = await window.solana.connect();
                if (response && response.publicKey) {
                    this.log('Phantom连接成功:', response.publicKey.toString());
                    return true;
                }
                return false;
            } catch (error) {
                if (error.code === 4001) {
                    this.log('用户拒绝连接Phantom');
                    return false;
                }
                throw error;
            }
        }

        // 连接MetaMask钱包
        async connectMetaMask() {
            try {
                if (!window.ethereum || !window.ethereum.isMetaMask) {
                    throw new Error('MetaMask钱包不可用');
                }

                const accounts = await window.ethereum.request({ 
                    method: 'eth_requestAccounts' 
                });
                
                if (accounts && accounts.length > 0) {
                    this.log('MetaMask连接成功:', accounts[0]);
                    return true;
                }
                return false;
            } catch (error) {
                if (error.code === 4001) {
                    this.log('用户拒绝连接MetaMask');
                    return false;
                }
                throw error;
            }
        }

        // 增强钱包连接功能
        enhanceWalletConnection() {
            // 拦截钱包连接请求
            const originalConnect = window.connectWallet;
            if (typeof originalConnect === 'function') {
                window.connectWallet = (walletType) => {
                    this.log(`拦截钱包连接请求: ${walletType}`);
                    return this.enhancedConnect(walletType, originalConnect);
                };
            }

            // 增强钱包管理器
            if (window.walletManager && typeof window.walletManager.connect === 'function') {
                const originalManagerConnect = window.walletManager.connect.bind(window.walletManager);
                window.walletManager.connect = (walletType, isReconnect = false) => {
                    this.log(`增强钱包管理器连接: ${walletType}`);
                    return this.enhancedManagerConnect(walletType, isReconnect, originalManagerConnect);
                };
            }
        }

        // 增强的连接方法
        async enhancedConnect(walletType, originalConnect) {
            if (!isMobile) {
                return originalConnect(walletType);
            }

            this.log(`移动端增强连接: ${walletType}`);
            
            // 设置连接标记
            this.setPendingConnection(walletType);
            
            // 尝试深度链接
            const deepLinkSuccess = await this.tryDeepLink(walletType);
            if (deepLinkSuccess) {
                return true;
            }

            // 回退到原始方法
            return originalConnect(walletType);
        }

        // 增强的管理器连接方法
        async enhancedManagerConnect(walletType, isReconnect, originalConnect) {
            if (!isMobile || isReconnect) {
                return originalConnect(walletType, isReconnect);
            }

            this.log(`移动端增强管理器连接: ${walletType}`);
            
            // 设置连接标记
            this.setPendingConnection(walletType);
            
            // 尝试深度链接
            const deepLinkSuccess = await this.tryDeepLink(walletType);
            if (deepLinkSuccess) {
                return true;
            }

            // 回退到原始方法
            return originalConnect(walletType, isReconnect);
        }

        // 尝试深度链接
        async tryDeepLink(walletType) {
            const config = this.walletConfigs[walletType];
            if (!config) {
                this.log(`不支持的钱包类型: ${walletType}`);
                return false;
            }

            try {
                this.log(`尝试${config.name}深度链接`);
                
                // 构建连接参数
                const params = this.buildConnectionParams(walletType);
                const deepLinkUrl = this.buildDeepLinkUrl(walletType, params);
                const universalLinkUrl = this.buildUniversalLinkUrl(walletType, params);
                
                this.log('深度链接URL:', deepLinkUrl);
                this.log('通用链接URL:', universalLinkUrl);
                
                // 尝试深度链接
                let success = await this.attemptDeepLink(deepLinkUrl);
                if (success) {
                    this.log('深度链接成功');
                    return true;
                }
                
                // 尝试通用链接
                success = await this.attemptUniversalLink(universalLinkUrl);
                if (success) {
                    this.log('通用链接成功');
                    return true;
                }
                
                // 提示下载
                this.promptAppDownload(walletType);
                return false;
                
            } catch (error) {
                this.error(`深度链接失败:`, error);
                return false;
            }
        }

        // 构建连接参数
        buildConnectionParams(walletType) {
            const baseUrl = window.location.origin;
            const currentUrl = window.location.href;
            
            if (walletType === 'phantom') {
                return {
                    dapp_encryption_public_key: this.generateRandomKey(),
                    cluster: 'mainnet-beta',
                    app_url: baseUrl,
                    redirect_link: currentUrl
                };
            } else if (walletType === 'metamask') {
                return {
                    url: currentUrl
                };
            }
            
            return {};
        }

        // 构建深度链接URL
        buildDeepLinkUrl(walletType, params) {
            const config = this.walletConfigs[walletType];
            
            if (walletType === 'phantom') {
                const queryString = new URLSearchParams(params).toString();
                return `${config.deepLink}?${queryString}`;
            } else if (walletType === 'metamask') {
                return `${config.deepLink}${window.location.host}${window.location.pathname}`;
            }
            
            return config.deepLink;
        }

        // 构建通用链接URL
        buildUniversalLinkUrl(walletType, params) {
            const config = this.walletConfigs[walletType];
            
            if (walletType === 'phantom') {
                const queryString = new URLSearchParams(params).toString();
                return `${config.universalLink}?${queryString}`;
            } else if (walletType === 'metamask') {
                return `${config.universalLink}${window.location.host}${window.location.pathname}`;
            }
            
            return config.universalLink;
        }

        // 尝试深度链接
        attemptDeepLink(url) {
            return new Promise((resolve) => {
                const timeout = setTimeout(() => resolve(false), this.deepLinkTimeout);
                
                // 创建隐藏iframe
                const iframe = document.createElement('iframe');
                iframe.style.display = 'none';
                iframe.src = url;
                
                document.body.appendChild(iframe);
                
                // 检测页面焦点变化
                const startTime = Date.now();
                const checkVisibility = () => {
                    if (document.hidden || Date.now() - startTime > 1000) {
                        clearTimeout(timeout);
                        this.cleanupElement(iframe);
                        resolve(true);
                    } else {
                        setTimeout(checkVisibility, 100);
                    }
                };
                
                setTimeout(() => {
                    checkVisibility();
                    setTimeout(() => this.cleanupElement(iframe), 1000);
                }, 500);
            });
        }

        // 尝试通用链接
        attemptUniversalLink(url) {
            return new Promise((resolve) => {
                const timeout = setTimeout(() => resolve(false), this.deepLinkTimeout);
                
                // 创建隐藏链接
                const link = document.createElement('a');
                link.href = url;
                link.target = '_blank';
                link.style.display = 'none';
                
                document.body.appendChild(link);
                link.click();
                
                // 检测页面焦点变化
                const startTime = Date.now();
                const checkVisibility = () => {
                    if (document.hidden || Date.now() - startTime > 1500) {
                        clearTimeout(timeout);
                        this.cleanupElement(link);
                        resolve(true);
                    } else if (Date.now() - startTime < 2500) {
                        setTimeout(checkVisibility, 100);
                    }
                };
                
                setTimeout(() => {
                    checkVisibility();
                    setTimeout(() => this.cleanupElement(link), 1000);
                }, 500);
            });
        }

        // 清理DOM元素
        cleanupElement(element) {
            if (element && element.parentNode) {
                element.parentNode.removeChild(element);
            }
        }

        // 提示下载应用
        promptAppDownload(walletType) {
            const config = this.walletConfigs[walletType];
            const downloadUrl = isIOS ? config.downloadUrls.ios : config.downloadUrls.android;
            
            const message = `${config.name} 钱包应用未检测到。是否前往下载？`;
            
            if (confirm(message)) {
                window.open(downloadUrl, '_blank');
            }
        }

        // 设置页面可见性监听
        setupVisibilityListener() {
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible') {
                    this.log('页面重新获得焦点');
                    
                    // 检查是否有待处理的连接
                    const pendingConnection = sessionStorage.getItem('pendingWalletConnection');
                    if (pendingConnection) {
                        this.log('检测到待处理的钱包连接');
                        setTimeout(() => {
                            this.checkWalletAppReturn();
                        }, 500);
                    }
                }
            });
        }

        // 显示连接状态
        showConnectionStatus(message, type = 'info') {
            this.log(`连接状态: ${message} (${type})`);
            
            // 创建状态提示
            const statusDiv = document.createElement('div');
            statusDiv.id = 'walletConnectionStatus';
            statusDiv.style.cssText = `
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                padding: 12px 20px;
                border-radius: 8px;
                color: white;
                font-weight: 500;
                z-index: 10000;
                transition: all 0.3s ease;
                ${type === 'success' ? 'background-color: #28a745;' : 
                  type === 'error' ? 'background-color: #dc3545;' : 
                  'background-color: #007bff;'}
            `;
            statusDiv.textContent = message;
            
            // 移除现有状态
            const existing = document.getElementById('walletConnectionStatus');
            if (existing) {
                existing.remove();
            }
            
            // 添加新状态
            document.body.appendChild(statusDiv);
            
            // 自动移除
            setTimeout(() => {
                if (statusDiv.parentNode) {
                    statusDiv.remove();
                }
            }, type === 'success' ? 2000 : 4000);
        }

        // 设置待处理连接
        setPendingConnection(walletType) {
            sessionStorage.setItem('pendingWalletConnection', walletType);
            sessionStorage.setItem('walletConnectionStartTime', Date.now().toString());
            this.log(`设置待处理连接: ${walletType}`);
        }

        // 清除待处理连接
        clearPendingConnection() {
            sessionStorage.removeItem('pendingWalletConnection');
            sessionStorage.removeItem('walletConnectionStartTime');
            this.log('清除待处理连接标记');
        }

        // 通知连接成功
        notifyConnectionSuccess(walletType) {
            // 触发自定义事件
            const event = new CustomEvent('mobileWalletConnected', {
                detail: { walletType }
            });
            document.dispatchEvent(event);
            
            // 调用钱包管理器更新
            if (window.walletManager && typeof window.walletManager.updateUI === 'function') {
                window.walletManager.updateUI();
            }
            
            // 刷新页面以确保状态同步
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }

        // 生成随机密钥
        generateRandomKey() {
            const array = new Uint8Array(32);
            crypto.getRandomValues(array);
            return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
        }
    }

    // 创建增强器实例
    if (isMobile) {
        window.mobileWalletEnhancer = new MobileWalletEnhancer();
        console.log('[移动端钱包增强器] 已加载并初始化');
    } else {
        console.log('[移动端钱包增强器] 非移动端设备，跳过加载');
    }

})();