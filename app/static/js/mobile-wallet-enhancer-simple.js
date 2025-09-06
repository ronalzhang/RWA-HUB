/**
 * 移动端钱包连接增强器 - 简化版
 * 专门处理移动端钱包连接问题
 * 版本: 2.0.0 - 简化流程版
 */

(function() {
    'use strict';

    // 防止重复加载
    if (window.MOBILE_WALLET_ENHANCER_SIMPLE_LOADED) {
        return;
    }
    window.MOBILE_WALLET_ENHANCER_SIMPLE_LOADED = true;

    console.log('[移动端钱包增强器-简化版] 开始加载...');

    // 移动端检测
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isAndroid = /Android/i.test(navigator.userAgent);
    const isSafari = /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent);

    // 简化的移动端钱包增强器
    class SimpleMobileWalletEnhancer {
        constructor() {
            this.debug = true;
            this.pendingConnection = null;
            this.connectionCheckInterval = null;
            
            // 钱包配置
            this.walletConfigs = {
                phantom: {
                    name: 'Phantom',
                    deepLink: 'phantom://browse',
                    universalLink: 'https://phantom.app/ul/browse',
                    downloadUrls: {
                        ios: 'https://apps.apple.com/app/phantom-solana-wallet/id1598432977',
                        android: 'https://play.google.com/store/apps/details?id=app.phantom'
                    },
                    checkFunction: () => {
                        // 更全面的钱包检测
                        return (window.solana && window.solana.isPhantom) || 
                               (window.phantom && window.phantom.solana) ||
                               (window.solana && window.solana.publicKey) ||
                               (window.solana && typeof window.solana.connect === 'function');
                    }
                }
            };

            this.init();
        }

        log(message, data = null) {
            if (this.debug) {
                console.log(`[移动端钱包增强器-简化版] ${message}`, data || '');
            }
        }

        // 检查是否从钱包返回
        checkWalletReturn() {
            const urlParams = new URLSearchParams(window.location.search);
            const phantomConnect = urlParams.get('phantom_connect');
            const walletRequest = urlParams.get('wallet_request');
            
            if (phantomConnect === '1' && walletRequest === 'phantom') {
                this.log('检测到从Phantom钱包返回');
                
                // 清理URL参数
                const url = new URL(window.location);
                url.searchParams.delete('phantom_connect');
                url.searchParams.delete('wallet_request');
                window.history.replaceState({}, document.title, url.toString());
                
                // 设置待处理连接
                this.pendingConnection = {
                    walletType: 'phantom',
                    timestamp: Date.now(),
                    config: this.walletConfigs.phantom,
                    fromReturn: true
                };
                
                // 延迟检查连接状态，给钱包对象时间加载
                setTimeout(() => {
                    this.checkConnectionAfterReturn();
                }, 1000);
            }
        }

        init() {
            this.log('初始化移动端钱包增强器-简化版');
            
            // 检查是否从钱包返回
            this.checkWalletReturn();
            
            // 监听页面可见性变化（用户从钱包App返回时触发）
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden && this.pendingConnection) {
                    this.log('用户从钱包App返回，检查连接状态');
                    this.log(`当前钱包状态: solana=${!!window.solana}, isConnected=${window.solana?.isConnected}, publicKey=${!!window.solana?.publicKey}`);
                    setTimeout(() => this.checkConnectionAfterReturn(), 1000);
                }
            });

            // 监听页面焦点（备用检测方法）
            window.addEventListener('focus', () => {
                if (this.pendingConnection) {
                    this.log('页面获得焦点，检查连接状态');
                    this.log(`当前钱包状态: solana=${!!window.solana}, isConnected=${window.solana?.isConnected}, publicKey=${!!window.solana?.publicKey}`);
                    setTimeout(() => this.checkConnectionAfterReturn(), 1000);
                }
            });

            // 监听钱包连接事件
            if (window.solana) {
                window.solana.on('connect', (publicKey) => {
                    this.log('钱包连接事件触发', publicKey);
                    if (this.pendingConnection) {
                        this.onConnectionSuccess();
                    }
                });
                
                window.solana.on('disconnect', () => {
                    this.log('钱包断开连接事件触发');
                });
            }

            this.log('移动端钱包增强器-简化版初始化完成');
        }

        // 增强钱包管理器的连接方法
        async enhanceWalletConnection(walletType) {
            if (!isMobile) {
                this.log('非移动端环境，跳过增强');
                return false;
            }

            this.log(`开始增强钱包连接: ${walletType}`);
            
            const config = this.walletConfigs[walletType];
            if (!config) {
                this.log(`不支持的钱包类型: ${walletType}`);
                return false;
            }

            // 设置待处理连接
            this.pendingConnection = {
                walletType,
                timestamp: Date.now(),
                config
            };

            // 直接跳转到钱包App
            return await this.jumpToWalletApp(walletType);
        }

        // 直接跳转到钱包App
        async jumpToWalletApp(walletType) {
            const config = this.walletConfigs[walletType];
            if (!config) {
                this.log(`钱包配置不存在: ${walletType}`);
                return false;
            }

            try {
                // 构建连接URL
                const connectUrl = this.buildConnectUrl(walletType);
                
                this.log(`准备跳转到${config.name}钱包App`);
                this.log(`连接URL: ${connectUrl}`);

                // 显示跳转提示
                this.showJumpingMessage(config.name);

                // 直接跳转（优先使用深度链接）
                if (isIOS && isSafari) {
                    // Safari优先使用通用链接
                    const universalUrl = connectUrl.replace(config.deepLink, config.universalLink);
                    this.log(`Safari环境，使用通用链接: ${universalUrl}`);
                    
                    // 尝试深度链接，如果失败则使用通用链接
                    try {
                        window.location.href = connectUrl;
                        // 等待一下，如果没有跳转成功则使用通用链接
                        setTimeout(() => {
                            if (!document.hidden) {
                                this.log('深度链接可能失败，尝试通用链接');
                                window.location.href = universalUrl;
                            }
                        }, 1000);
                    } catch (error) {
                        this.log('深度链接失败，使用通用链接');
                        window.location.href = universalUrl;
                    }
                } else {
                    // 其他环境优先使用深度链接
                    this.log(`使用深度链接: ${connectUrl}`);
                    window.location.href = connectUrl;
                }

                // 开始检查连接状态
                this.startConnectionCheck();
                
                return true;

            } catch (error) {
                this.log(`跳转到钱包App失败: ${error.message}`);
                this.showError(`跳转到${config.name}失败，请确保已安装钱包App`);
                return false;
            }
        }

        // 构建连接URL
        buildConnectUrl(walletType) {
            const config = this.walletConfigs[walletType];
            
            if (walletType === 'phantom') {
                // Phantom移动端使用browse模式，直接访问网站让钱包检测
                const currentUrl = window.location.href;
                
                // 添加特殊参数让页面知道这是从钱包返回的
                const url = new URL(currentUrl);
                url.searchParams.set('phantom_connect', '1');
                url.searchParams.set('wallet_request', 'phantom');
                
                const finalUrl = `${config.deepLink}?url=${encodeURIComponent(url.toString())}`;
                this.log(`构建的Phantom连接URL: ${finalUrl}`);
                
                return finalUrl;
            } else {
                // 其他钱包使用原有逻辑
                const currentUrl = window.location.href;
                const appUrl = window.location.origin;
                
                // 生成加密公钥（简化版本）
                const dappEncryptionPublicKey = this.generatePublicKey();
                
                // 使用URLSearchParams正确构建参数
                const searchParams = new URLSearchParams();
                searchParams.set('dapp_encryption_public_key', dappEncryptionPublicKey);
                searchParams.set('cluster', 'mainnet-beta');
                searchParams.set('app_url', appUrl);
                searchParams.set('redirect_link', currentUrl);

                const finalUrl = `${config.deepLink}?${searchParams.toString()}`;
                this.log(`构建的连接URL: ${finalUrl}`);
                
                return finalUrl;
            }
        }

        // 生成简单的公钥（用于演示）
        generatePublicKey() {
            // 这里使用一个固定的公钥，实际应用中应该动态生成
            return '126742706e7340dec9e7fd03264e1024fdafb6116b6a8703702d5dda66069e2a';
        }

        // 显示跳转提示
        showJumpingMessage(walletName) {
            // 创建提示框
            const messageDiv = document.createElement('div');
            messageDiv.id = 'wallet-jumping-message';
            messageDiv.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                z-index: 10000;
                font-size: 16px;
                max-width: 300px;
            `;
            messageDiv.innerHTML = `
                <div>正在跳转到${walletName}...</div>
                <div style="margin-top: 10px; font-size: 14px; opacity: 0.8;">
                    请在钱包App中确认连接
                </div>
            `;

            document.body.appendChild(messageDiv);

            // 5秒后自动移除提示
            setTimeout(() => {
                const msg = document.getElementById('wallet-jumping-message');
                if (msg) {
                    msg.remove();
                }
            }, 5000);
        }

        // 开始检查连接状态
        startConnectionCheck() {
            this.log('开始检查连接状态');
            
            // 清除之前的检查
            if (this.connectionCheckInterval) {
                clearInterval(this.connectionCheckInterval);
            }

            // 每2秒检查一次连接状态
            this.connectionCheckInterval = setInterval(() => {
                this.checkConnectionStatus();
            }, 2000);

            // 30秒后停止检查
            setTimeout(() => {
                if (this.connectionCheckInterval) {
                    clearInterval(this.connectionCheckInterval);
                    this.connectionCheckInterval = null;
                }
                
                if (this.pendingConnection) {
                    this.log('连接检查超时');
                    this.showRetryOption();
                }
            }, 30000);
        }

        // 检查连接状态
        checkConnectionStatus() {
            if (!this.pendingConnection) {
                return;
            }

            const config = this.pendingConnection.config;
            
            // 详细的钱包状态日志
            this.log('=== 钱包状态检查 ===');
            this.log(`window.solana: ${!!window.solana}`);
            this.log(`window.phantom: ${!!window.phantom}`);
            if (window.solana) {
                this.log(`solana.isPhantom: ${window.solana.isPhantom}`);
                this.log(`solana.isConnected: ${window.solana.isConnected}`);
                this.log(`solana.publicKey: ${!!window.solana.publicKey}`);
                this.log(`solana.connect: ${typeof window.solana.connect}`);
            }
            if (window.phantom && window.phantom.solana) {
                this.log(`phantom.solana.isConnected: ${window.phantom.solana.isConnected}`);
                this.log(`phantom.solana.publicKey: ${!!window.phantom.solana.publicKey}`);
            }
            
            // 检查钱包是否已连接
            if (config.checkFunction && config.checkFunction()) {
                this.log(`${config.name}钱包已检测到`);
                
                // 获取钱包对象
                let walletObj = window.solana;
                if (window.phantom && window.phantom.solana) {
                    walletObj = window.phantom.solana;
                    this.log('使用 phantom.solana 对象');
                }
                
                // 尝试获取连接状态
                if (walletObj && walletObj.isConnected) {
                    this.log('钱包已连接成功');
                    this.onConnectionSuccess();
                    return;
                } else if (walletObj && walletObj.publicKey) {
                    // 有些情况下isConnected可能为false但publicKey存在
                    this.log('检测到钱包公钥，认为连接成功');
                    this.onConnectionSuccess();
                    return;
                }
                
                // 钱包存在但未连接，尝试连接
                this.log('钱包对象存在但未连接，尝试连接');
                this.attemptConnection();
            } else {
                // 钱包对象不存在，可能还在加载
                this.log('钱包对象未检测到，继续等待...');
                this.log(`checkFunction结果: ${config.checkFunction ? config.checkFunction() : 'checkFunction不存在'}`);
            }
        }

        // 用户从钱包App返回后检查连接
        async checkConnectionAfterReturn() {
            if (!this.pendingConnection) {
                return;
            }

            this.log('检查用户返回后的连接状态');
            
            const config = this.pendingConnection.config;
            
            // 等待一下让钱包对象加载
            await this.sleep(1000);
            
            // 多次检查，因为钱包对象可能需要时间加载
            for (let i = 0; i < 5; i++) {
                if (config.checkFunction && config.checkFunction()) {
                    this.log(`${config.name}钱包对象已加载 (尝试 ${i + 1}/5)`);
                    
                    if (window.solana && (window.solana.isConnected || window.solana.publicKey)) {
                        this.log('钱包已连接');
                        this.onConnectionSuccess();
                        return;
                    } else {
                        this.log('钱包对象存在但未连接，尝试连接');
                        await this.attemptConnection();
                        return;
                    }
                } else {
                    this.log(`钱包对象未检测到 (尝试 ${i + 1}/5)，等待...`);
                    await this.sleep(1000);
                }
            }
            
            // 5次尝试后仍未检测到钱包
            this.log('多次尝试后仍未检测到钱包，可能用户取消了连接或钱包未安装');
            this.showRetryOption();
        }

        // 尝试连接钱包
        async attemptConnection() {
            if (!this.pendingConnection) {
                return;
            }

            try {
                this.log('=== 尝试连接钱包 ===');
                
                // 获取钱包对象
                let walletObj = window.solana;
                if (window.phantom && window.phantom.solana) {
                    walletObj = window.phantom.solana;
                    this.log('使用 phantom.solana 对象进行连接');
                } else if (window.solana) {
                    this.log('使用 window.solana 对象进行连接');
                }
                
                this.log(`钱包对象: ${!!walletObj}`);
                this.log(`connect方法: ${typeof walletObj?.connect}`);
                this.log(`isConnected: ${walletObj?.isConnected}`);
                this.log(`publicKey: ${!!walletObj?.publicKey}`);
                
                if (walletObj && walletObj.connect) {
                    // 设置连接选项
                    const connectOptions = {
                        onlyIfTrusted: false // 允许显示连接提示
                    };
                    
                    this.log('调用钱包连接方法...');
                    const response = await walletObj.connect(connectOptions);
                    this.log('钱包连接响应:', response);
                    
                    if (response && (response.publicKey || walletObj.publicKey)) {
                        this.log('钱包连接成功');
                        this.onConnectionSuccess();
                    } else {
                        this.log('钱包连接响应无效，等待状态更新...');
                        // 等待一下让状态更新
                        setTimeout(() => {
                            if (walletObj && (walletObj.isConnected || walletObj.publicKey)) {
                                this.log('延迟检测到钱包连接成功');
                                this.onConnectionSuccess();
                            } else {
                                this.log('延迟检测仍未连接，显示重试选项');
                                this.showRetryOption();
                            }
                        }, 3000);
                    }
                } else if (walletObj && walletObj.isConnected) {
                    // 钱包已经连接但没有connect方法
                    this.log('钱包已连接，无需重新连接');
                    this.onConnectionSuccess();
                } else if (walletObj && walletObj.publicKey) {
                    // 有公钥但isConnected为false
                    this.log('检测到钱包公钥，认为已连接');
                    this.onConnectionSuccess();
                } else {
                    this.log('钱包连接方法不可用或钱包对象不存在');
                    this.log(`walletObj: ${!!walletObj}`);
                    this.log(`connect方法: ${typeof walletObj?.connect}`);
                    
                    // 等待一下再重试
                    setTimeout(() => {
                        // 重新检查钱包状态
                        const currentWallet = window.phantom?.solana || window.solana;
                        if (currentWallet && (currentWallet.isConnected || currentWallet.publicKey)) {
                            this.log('延迟检测到钱包连接');
                            this.onConnectionSuccess();
                        } else {
                            this.log('延迟检测仍未发现钱包连接，显示重试选项');
                            this.showRetryOption();
                        }
                    }, 3000);
                }
            } catch (error) {
                this.log(`钱包连接失败: ${error.message}`);
                this.log('错误详情:', error);
                
                // 检查是否是用户取消
                if (error.message.includes('User rejected') || 
                    error.message.includes('User cancelled') ||
                    error.code === 4001) {
                    this.log('用户取消了连接');
                    this.pendingConnection = null;
                    this.closeRetryMessage();
                } else {
                    this.log('连接错误，显示重试选项');
                    this.showRetryOption();
                }
            }
        }

        // 连接成功处理
        onConnectionSuccess() {
            this.log('钱包连接成功！');
            
            // 清理状态
            this.pendingConnection = null;
            if (this.connectionCheckInterval) {
                clearInterval(this.connectionCheckInterval);
                this.connectionCheckInterval = null;
            }

            // 移除提示信息
            const msg = document.getElementById('wallet-jumping-message');
            if (msg) {
                msg.remove();
            }

            // 触发钱包管理器的连接成功事件
            if (window.walletManager && window.walletManager.onWalletConnected) {
                window.walletManager.onWalletConnected();
            }

            // 刷新页面状态
            if (typeof updateWalletUI === 'function') {
                updateWalletUI();
            }
        }

        // 显示重试选项
        showRetryOption() {
            const config = this.pendingConnection?.config;
            if (!config) {
                return;
            }

            this.log('显示重试选项');

            // 移除跳转提示
            const jumpMsg = document.getElementById('wallet-jumping-message');
            if (jumpMsg) {
                jumpMsg.remove();
            }

            // 创建重试提示
            const retryDiv = document.createElement('div');
            retryDiv.id = 'wallet-retry-message';
            retryDiv.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                z-index: 10000;
                font-size: 16px;
                max-width: 300px;
            `;
            retryDiv.innerHTML = `
                <div>连接${config.name}失败</div>
                <div style="margin: 15px 0; font-size: 14px; opacity: 0.8;">
                    请确保已安装${config.name}钱包App
                </div>
                <button onclick="window.simpleMobileWalletEnhancer.retry()" 
                        style="background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; margin: 5px; cursor: pointer;">
                    重试连接
                </button>
                <button onclick="window.simpleMobileWalletEnhancer.closeRetryMessage()" 
                        style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 5px; margin: 5px; cursor: pointer;">
                    取消
                </button>
            `;

            document.body.appendChild(retryDiv);
        }

        // 重试连接
        async retry() {
            this.log('用户选择重试连接');
            this.closeRetryMessage();
            
            if (this.pendingConnection) {
                await this.jumpToWalletApp(this.pendingConnection.walletType);
            }
        }

        // 关闭重试消息
        closeRetryMessage() {
            const retryMsg = document.getElementById('wallet-retry-message');
            if (retryMsg) {
                retryMsg.remove();
            }
            this.pendingConnection = null;
        }

        // 显示错误信息
        showError(message) {
            this.log(`错误: ${message}`);
            
            // 这里可以集成到现有的错误显示系统
            if (typeof showErrorMessage === 'function') {
                showErrorMessage(message);
            } else {
                alert(message);
            }
        }

        // 工具方法：延时
        sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    }

    // 只在移动端初始化
    if (isMobile) {
        console.log('[移动端钱包增强器-简化版] 移动端环境，初始化增强器');
        window.simpleMobileWalletEnhancer = new SimpleMobileWalletEnhancer();
        
        // 增强现有的钱包管理器 - 直接拦截连接请求
        if (window.walletManager) {
            const originalConnect = window.walletManager.connect;
            window.walletManager.connect = async function(walletType) {
                console.log(`[移动端钱包增强器-简化版] 拦截钱包连接请求: ${walletType}`);
                
                // 直接使用移动端增强连接，不显示选择器
                const enhanced = await window.simpleMobileWalletEnhancer.enhanceWalletConnection(walletType);
                if (enhanced) {
                    console.log('[移动端钱包增强器-简化版] 使用增强连接方式');
                    return true;
                }
                
                // 回退到原始连接方法
                console.log('[移动端钱包增强器-简化版] 回退到原始连接方法');
                return originalConnect.call(this, walletType);
            };
            
            // 拦截openWalletSelector方法，直接连接Phantom
            const originalOpenWalletSelector = window.walletManager.openWalletSelector;
            window.walletManager.openWalletSelector = async function() {
                console.log('[移动端钱包增强器-简化版] 拦截钱包选择器，直接连接Phantom');
                // 直接连接Phantom，不显示选择器
                return await this.connect('phantom');
            };
        }
        
        // 等待钱包管理器加载后再进行拦截
        const waitForWalletManager = () => {
            if (window.walletManager) {
                console.log('[移动端钱包增强器-简化版] 钱包管理器已加载，进行拦截设置');
                
                const originalConnect = window.walletManager.connect;
                window.walletManager.connect = async function(walletType) {
                    console.log(`[移动端钱包增强器-简化版] 拦截钱包连接请求: ${walletType}`);
                    
                    // 直接使用移动端增强连接
                    const enhanced = await window.simpleMobileWalletEnhancer.enhanceWalletConnection(walletType);
                    if (enhanced) {
                        console.log('[移动端钱包增强器-简化版] 使用增强连接方式');
                        return true;
                    }
                    
                    // 回退到原始连接方法
                    console.log('[移动端钱包增强器-简化版] 回退到原始连接方法');
                    return originalConnect.call(this, walletType);
                };
                
                // 拦截openWalletSelector方法
                const originalOpenWalletSelector = window.walletManager.openWalletSelector;
                window.walletManager.openWalletSelector = async function() {
                    console.log('[移动端钱包增强器-简化版] 拦截钱包选择器，直接连接Phantom');
                    // 直接连接Phantom，不显示选择器
                    return await this.connect('phantom');
                };
                
                // 拦截所有可能触发选择器的方法
                if (window.connectWallet) {
                    const originalConnectWallet = window.connectWallet;
                    window.connectWallet = async function(walletType) {
                        console.log(`[移动端钱包增强器-简化版] 拦截全局connectWallet: ${walletType}`);
                        if (walletType) {
                            return await window.walletManager.connect(walletType);
                        } else {
                            // 没有指定钱包类型，直接连接Phantom
                            return await window.walletManager.connect('phantom');
                        }
                    };
                }
            } else {
                // 钱包管理器还未加载，继续等待
                setTimeout(waitForWalletManager, 100);
            }
        };
        
        // 开始等待钱包管理器
        waitForWalletManager();
    } else {
        console.log('[移动端钱包增强器-简化版] 桌面端环境，跳过初始化');
    }

    console.log('[移动端钱包增强器-简化版] 加载完成');
})();