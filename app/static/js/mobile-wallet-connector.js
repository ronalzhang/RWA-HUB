/**
 * 移动端钱包连接解决方案
 * 支持多种钱包和连接方式
 */

class MobileWalletConnector {
    constructor() {
        this.isMobile = this.detectMobile();
        this.supportedWallets = {
            phantom: {
                name: 'Phantom',
                deepLink: 'phantom://',
                universalLink: 'https://phantom.app/ul/',
                downloadUrl: 'https://phantom.app/download',
                icon: 'https://phantom.app/img/phantom-icon.svg'
            },
            solflare: {
                name: 'Solflare',
                deepLink: 'solflare://',
                universalLink: 'https://solflare.com/ul/',
                downloadUrl: 'https://solflare.com/download',
                icon: 'https://solflare.com/assets/logo.svg'
            },
            glow: {
                name: 'Glow',
                deepLink: 'glow://',
                universalLink: 'https://glow.app/ul/',
                downloadUrl: 'https://glow.app/download',
                icon: 'https://glow.app/logo.svg'
            }
        };
        
        this.currentWallet = null;
        this.isConnecting = false;
        this.connectionCallbacks = {
            onSuccess: null,
            onError: null,
            onCancel: null
        };
        
        this.init();
    }
    
    init() {
        // 检测已安装的钱包
        this.detectInstalledWallets();
        
        // 监听页面可见性变化（用于检测从钱包返回）
        if (this.isMobile) {
            document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
        }
    }
    
    detectMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }
    
    detectInstalledWallets() {
        const installedWallets = {};
        
        // 检测桌面端钱包插件
        if (!this.isMobile) {
            if (window.solana && window.solana.isPhantom) {
                installedWallets.phantom = true;
            }
            if (window.solflare && window.solflare.isSolflare) {
                installedWallets.solflare = true;
            }
            if (window.glow) {
                installedWallets.glow = true;
            }
        }
        
        this.installedWallets = installedWallets;
        return installedWallets;
    }
    
    /**
     * 连接钱包
     * @param {string} walletType - 钱包类型 ('phantom', 'solflare', 'glow')
     * @param {object} callbacks - 回调函数
     */
    async connectWallet(walletType = 'phantom', callbacks = {}) {
        this.connectionCallbacks = {
            onSuccess: callbacks.onSuccess || (() => {}),
            onError: callbacks.onError || (() => {}),
            onCancel: callbacks.onCancel || (() => {})
        };
        
        if (this.isConnecting) {
            this.connectionCallbacks.onError(new Error('连接进行中，请稍候'));
            return;
        }
        
        this.isConnecting = true;
        this.currentWallet = walletType;
        
        try {
            if (this.isMobile) {
                await this.connectMobileWallet(walletType);
            } else {
                await this.connectDesktopWallet(walletType);
            }
        } catch (error) {
            this.isConnecting = false;
            this.connectionCallbacks.onError(error);
        }
    }
    
    /**
     * 桌面端钱包连接
     */
    async connectDesktopWallet(walletType) {
        const wallet = this.getWalletProvider(walletType);
        
        if (!wallet) {
            throw new Error(`请安装 ${this.supportedWallets[walletType].name} 钱包插件`);
        }
        
        try {
            const response = await wallet.connect();
            this.isConnecting = false;
            
            this.connectionCallbacks.onSuccess({
                publicKey: response.publicKey.toString(),
                walletType: walletType,
                wallet: wallet
            });
        } catch (error) {
            this.isConnecting = false;
            if (error.code === 4001) {
                this.connectionCallbacks.onCancel();
            } else {
                throw error;
            }
        }
    }
    
    /**
     * 移动端钱包连接
     */
    async connectMobileWallet(walletType) {
        const walletConfig = this.supportedWallets[walletType];
        
        if (!walletConfig) {
            throw new Error('不支持的钱包类型');
        }
        
        // 生成连接请求
        const connectionRequest = this.generateConnectionRequest();
        
        // 尝试多种连接方式
        const connectionMethods = [
            () => this.tryDeepLink(walletConfig, connectionRequest),
            () => this.tryUniversalLink(walletConfig, connectionRequest),
            () => this.showQRCode(walletConfig, connectionRequest),
            () => this.showDownloadPrompt(walletConfig)
        ];
        
        for (const method of connectionMethods) {
            try {
                await method();
                break; // 成功则跳出循环
            } catch (error) {
                console.log(`连接方式失败，尝试下一种: ${error.message}`);
                continue;
            }
        }
    }
    
    /**
     * 尝试Deep Link连接
     */
    async tryDeepLink(walletConfig, connectionRequest) {
        return new Promise((resolve, reject) => {
            const deepLinkUrl = `${walletConfig.deepLink}v1/connect?${new URLSearchParams(connectionRequest)}`;
            
            // 设置超时检测
            const timeout = setTimeout(() => {
                reject(new Error('Deep Link 连接超时'));
            }, 3000);
            
            // 尝试打开深链接
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = deepLinkUrl;
            document.body.appendChild(iframe);
            
            // 检测是否成功跳转
            setTimeout(() => {
                document.body.removeChild(iframe);
                
                // 如果页面还在当前标签页，说明没有成功跳转到app
                if (document.visibilityState === 'visible') {
                    clearTimeout(timeout);
                    reject(new Error('未检测到钱包应用'));
                } else {
                    clearTimeout(timeout);
                    resolve();
                }
            }, 1000);
        });
    }
    
    /**
     * 尝试Universal Link连接
     */
    async tryUniversalLink(walletConfig, connectionRequest) {
        return new Promise((resolve, reject) => {
            const universalLinkUrl = `${walletConfig.universalLink}?${new URLSearchParams(connectionRequest)}`;
            
            // 创建隐藏的链接并点击
            const link = document.createElement('a');
            link.href = universalLinkUrl;
            link.target = '_blank';
            link.style.display = 'none';
            document.body.appendChild(link);
            
            link.click();
            document.body.removeChild(link);
            
            // 等待一段时间检测是否成功
            setTimeout(() => {
                if (document.visibilityState === 'visible') {
                    reject(new Error('Universal Link 连接失败'));
                } else {
                    resolve();
                }
            }, 2000);
        });
    }
    
    /**
     * 显示二维码连接
     */
    async showQRCode(walletConfig, connectionRequest) {
        return new Promise((resolve, reject) => {
            // 生成WalletConnect URI
            const wcUri = this.generateWalletConnectURI(connectionRequest);
            
            // 创建二维码模态框
            const modal = this.createQRModal(walletConfig, wcUri);
            document.body.appendChild(modal);
            
            // 显示模态框
            modal.style.display = 'flex';
            
            // 设置超时
            const timeout = setTimeout(() => {
                document.body.removeChild(modal);
                reject(new Error('二维码连接超时'));
            }, 60000); // 60秒超时
            
            // 监听连接成功
            const checkConnection = setInterval(() => {
                // 这里需要实现检查连接状态的逻辑
                // 实际项目中应该通过WebSocket或轮询检查连接状态
            }, 1000);
            
            // 取消按钮
            modal.querySelector('.cancel-btn').onclick = () => {
                clearTimeout(timeout);
                clearInterval(checkConnection);
                document.body.removeChild(modal);
                this.connectionCallbacks.onCancel();
            };
        });
    }
    
    /**
     * 显示下载提示
     */
    async showDownloadPrompt(walletConfig) {
        const shouldDownload = confirm(
            `未检测到 ${walletConfig.name} 钱包，是否前往下载？`
        );
        
        if (shouldDownload) {
            window.open(walletConfig.downloadUrl, '_blank');
        }
        
        throw new Error('用户取消下载');
    }
    
    /**
     * 生成连接请求参数
     */
    generateConnectionRequest() {
        const origin = window.location.origin;
        const redirectUri = `${origin}/wallet-callback`;
        
        return {
            dapp_encryption_public_key: this.generatePublicKey(),
            cluster: 'mainnet-beta',
            app_url: origin,
            redirect_link: redirectUri,
            request_id: this.generateRequestId()
        };
    }
    
    /**
     * 生成WalletConnect URI
     */
    generateWalletConnectURI(connectionRequest) {
        // 这里应该生成符合WalletConnect v2标准的URI
        // 简化示例
        return `wc:${connectionRequest.request_id}@2?relay-protocol=irn&symKey=${this.generateSymKey()}`;
    }
    
    /**
     * 创建二维码模态框
     */
    createQRModal(walletConfig, wcUri) {
        const modal = document.createElement('div');
        modal.className = 'wallet-qr-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;
        
        modal.innerHTML = `
            <div style="background: white; padding: 2rem; border-radius: 1rem; max-width: 400px; width: 90%; text-align: center;">
                <div style="margin-bottom: 1rem;">
                    <img src="${walletConfig.icon}" alt="${walletConfig.name}" style="width: 64px; height: 64px;">
                    <h3 style="margin: 1rem 0;">连接 ${walletConfig.name}</h3>
                </div>
                
                <div id="qrcode" style="margin: 1rem 0; display: flex; justify-content: center;">
                    <!-- 这里应该生成实际的二维码 -->
                    <div style="width: 200px; height: 200px; border: 2px dashed #ccc; display: flex; align-items: center; justify-content: center; font-size: 14px; color: #666;">
                        二维码区域<br>
                        <small>请用 ${walletConfig.name} 扫描</small>
                    </div>
                </div>
                
                <p style="font-size: 14px; color: #666; margin: 1rem 0;">
                    使用 ${walletConfig.name} App 扫描二维码完成连接
                </p>
                
                <button class="cancel-btn" style="background: #f3f4f6; border: none; padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer;">
                    取消
                </button>
            </div>
        `;
        
        return modal;
    }
    
    /**
     * 处理页面可见性变化（从钱包返回时）
     */
    handleVisibilityChange() {
        if (document.visibilityState === 'visible' && this.isConnecting) {
            // 页面重新可见，检查是否从钱包返回
            setTimeout(() => {
                this.checkConnectionResult();
            }, 1000);
        }
    }
    
    /**
     * 检查连接结果
     */
    async checkConnectionResult() {
        try {
            // 这里应该检查连接状态
            // 实际实现中可能需要：
            // 1. 检查localStorage中的连接信息
            // 2. 向服务器查询连接状态
            // 3. 尝试获取钱包公钥
            
            const connectionInfo = localStorage.getItem('wallet_connection_temp');
            if (connectionInfo) {
                const info = JSON.parse(connectionInfo);
                localStorage.removeItem('wallet_connection_temp');
                
                this.isConnecting = false;
                this.connectionCallbacks.onSuccess({
                    publicKey: info.publicKey,
                    walletType: this.currentWallet,
                    signature: info.signature
                });
            } else {
                // 连接失败或取消
                this.isConnecting = false;
                this.connectionCallbacks.onCancel();
            }
        } catch (error) {
            this.isConnecting = false;
            this.connectionCallbacks.onError(error);
        }
    }
    
    /**
     * 获取钱包提供者
     */
    getWalletProvider(walletType) {
        switch (walletType) {
            case 'phantom':
                return window.solana && window.solana.isPhantom ? window.solana : null;
            case 'solflare':
                return window.solflare && window.solflare.isSolflare ? window.solflare : null;
            case 'glow':
                return window.glow || null;
            default:
                return null;
        }
    }
    
    /**
     * 工具函数
     */
    generatePublicKey() {
        return Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, '0')).join('');
    }
    
    generateRequestId() {
        return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    }
    
    generateSymKey() {
        return Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, '0')).join('');
    }
    
    /**
     * 断开连接
     */
    async disconnect() {
        if (this.currentWallet && !this.isMobile) {
            const wallet = this.getWalletProvider(this.currentWallet);
            if (wallet && wallet.disconnect) {
                await wallet.disconnect();
            }
        }
        
        this.currentWallet = null;
        this.isConnecting = false;
        localStorage.removeItem('wallet_connection_temp');
    }
    
    /**
     * 获取支持的钱包列表
     */
    getSupportedWallets() {
        return Object.keys(this.supportedWallets).map(key => ({
            id: key,
            ...this.supportedWallets[key],
            installed: this.installedWallets[key] || false
        }));
    }
}

// 创建全局实例
window.MobileWalletConnector = MobileWalletConnector;

// 使用示例：
/*
const walletConnector = new MobileWalletConnector();

// 连接钱包
walletConnector.connectWallet('phantom', {
    onSuccess: (result) => {
        console.log('连接成功:', result);
    },
    onError: (error) => {
        console.error('连接失败:', error);
    },
    onCancel: () => {
        console.log('用户取消连接');
    }
});
*/