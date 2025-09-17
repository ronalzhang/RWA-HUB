/**
 * 统一的钱包连接管理器
 * 解决多个文件中重复和冲突的钱包管理逻辑
 */

class UnifiedWalletManager {
    constructor() {
        this.initialized = false;
        this.connecting = false;
        this.retryAttempts = 0;
        this.maxRetries = 3;

        // 确保只初始化一次
        if (window.unifiedWalletManager) {
            return window.unifiedWalletManager;
        }

        window.unifiedWalletManager = this;
        this.init();
    }

    init() {
        if (this.initialized) return;
        this.initialized = true;

        console.log('🚀 初始化统一钱包管理器');

        // 监听Phantom钱包事件
        this.setupWalletEventListeners();

        // 初始化连接状态检查
        this.checkInitialConnection();
    }

    /**
     * 设置钱包事件监听器
     */
    setupWalletEventListeners() {
        // 监听Phantom钱包连接状态变化
        if (window.solana) {
            window.solana.on('connect', (publicKey) => {
                console.log('🔗 Phantom钱包已连接:', publicKey.toString());
                this.handleWalletConnect(publicKey.toString(), publicKey);
            });

            window.solana.on('disconnect', () => {
                console.log('🔌 Phantom钱包已断开');
                this.handleWalletDisconnect();
            });

            window.solana.on('accountChanged', (publicKey) => {
                if (publicKey) {
                    console.log('👤 Phantom钱包账户已切换:', publicKey.toString());
                    this.handleWalletConnect(publicKey.toString(), publicKey);
                } else {
                    console.log('👤 Phantom钱包账户已清空');
                    this.handleWalletDisconnect();
                }
            });
        }

        // 定期检查Phantom钱包可用性
        let checkCount = 0;
        const checkInterval = setInterval(() => {
            if (window.solana?.isPhantom) {
                this.setupWalletEventListeners();
                clearInterval(checkInterval);
            } else if (++checkCount >= 10) {
                clearInterval(checkInterval);
                console.log('⚠️ Phantom钱包未检测到');
            }
        }, 1000);
    }

    /**
     * 检查初始连接状态
     */
    async checkInitialConnection() {
        try {
            // 优先检查持久化的钱包状态
            if (window.walletPersistenceManager) {
                await window.walletPersistenceManager.restoreWalletConnection();
            }

            // 如果持久化恢复失败, 检查当前连接状态
            if (!window.walletState?.connected && window.solana?.isConnected) {
                const address = window.solana.publicKey?.toString();
                if (address) {
                    this.handleWalletConnect(address, window.solana.publicKey);
                }
            }
        } catch (error) {
            console.error('❌ 初始连接状态检查失败:', error);
        }
    }

    /**
     * 统一获取钱包地址
     */
    getWalletAddress() {
        // 优先级1: 检查全局钱包状态
        if (window.walletState?.address && window.walletState?.connected) {
            return window.walletState.address;
        }

        // 优先级2: 检查Phantom钱包直接连接状态
        if (window.solana?.isConnected && window.solana?.publicKey) {
            const address = window.solana.publicKey.toString();
            // 自动同步状态
            this.handleWalletConnect(address, window.solana.publicKey);
            return address;
        }

        // 优先级3: 检查持久化状态
        if (window.walletPersistenceManager) {
            const savedState = window.walletPersistenceManager.loadWalletState();
            if (savedState?.address && savedState?.connected) {
                return savedState.address;
            }
        }

        // 优先级4: 兼容性检查
        return localStorage.getItem('walletAddress') ||
               localStorage.getItem('eth_address') ||
               this.getCookieValue('eth_address');
    }

    /**
     * 获取Cookie值
     */
    getCookieValue(name) {
        const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? match[2] : null;
    }

    /**
     * 统一连接钱包
     */
    async connectWallet(walletType = 'phantom') {
        if (this.connecting) {
            console.log('钱包连接正在进行中...');
            return false;
        }

        this.connecting = true;

        try {
            console.log(`🔗 开始连接${walletType}钱包...`);

            if (walletType === 'phantom') {
                return await this.connectPhantomWallet();
            }

            throw new Error(`不支持的钱包类型: ${walletType}`);
        } catch (error) {
            console.error('❌ 钱包连接失败:', error);
            this.showError('钱包连接失败', error.message);
            return false;
        } finally {
            this.connecting = false;
        }
    }

    /**
     * 连接Phantom钱包
     */
    async connectPhantomWallet() {
        try {
            // 检查Phantom是否可用
            if (!window.solana?.isPhantom) {
                throw new Error('Phantom钱包未安装或不可用');
            }

            // 尝试连接
            const response = await window.solana.connect();
            const address = response.publicKey.toString();

            console.log('✅ Phantom钱包连接成功:', address);
            this.handleWalletConnect(address, response.publicKey);

            return true;
        } catch (error) {
            if (error.code === 4001) {
                throw new Error('用户拒绝了连接请求');
            }
            throw error;
        }
    }

    /**
     * 处理钱包连接成功
     */
    handleWalletConnect(address, publicKey) {
        try {
            // 创建统一的钱包状态对象
            const walletState = {
                connected: true,
                isConnected: true,
                address: address,
                publicKey: publicKey,
                walletType: 'phantom',
                formatAddress: function(addr) {
                    return addr ? addr.slice(0, 6) + '...' + addr.slice(-4) : '';
                },
                copyWalletAddress: function() {
                    if (this.address) {
                        navigator.clipboard.writeText(this.address).then(() => {
                            const successMsg = document.getElementById('copyAddressSuccess');
                            if (successMsg) {
                                successMsg.style.opacity = '1';
                                setTimeout(() => successMsg.style.opacity = '0', 2000);
                            }
                        }).catch(() => {
                            alert('Address: ' + this.address);
                        });
                    }
                }
            };

            // 更新全局状态
            window.walletState = walletState;

            // 保存到持久化管理器
            if (window.walletPersistenceManager) {
                window.walletPersistenceManager.saveWalletState(walletState);
            }

            // 更新所有UI
            this.updateAllWalletUI(address);

            // 触发连接事件
            this.dispatchWalletEvent('walletConnected', {
                address: address,
                walletType: 'phantom'
            });

            console.log('🎯 钱包状态已更新:', address);
        } catch (error) {
            console.error('❌ 处理钱包连接失败:', error);
        }
    }

    /**
     * 处理钱包断开连接
     */
    handleWalletDisconnect() {
        try {
            // 清除全局状态
            window.walletState = null;

            // 清除持久化状态
            if (window.walletPersistenceManager) {
                window.walletPersistenceManager.clearWalletState();
            }

            // 重置所有UI
            this.resetAllWalletUI();

            // 触发断开事件
            this.dispatchWalletEvent('walletDisconnected', {});

            console.log('🔌 钱包已断开连接');
        } catch (error) {
            console.error('❌ 处理钱包断开失败:', error);
        }
    }

    /**
     * 更新所有钱包相关UI
     */
    updateAllWalletUI(address) {
        try {
            const formattedAddress = window.walletState?.formatAddress(address);

            // 更新主要连接按钮
            const walletBtnText = document.getElementById('walletBtnText');
            if (walletBtnText) {
                walletBtnText.textContent = formattedAddress;
            }

            // 更新下拉菜单中的地址显示
            const walletAddressDisplay = document.getElementById('walletAddressDisplay');
            if (walletAddressDisplay) {
                walletAddressDisplay.textContent = formattedAddress;
            }

            // 更新其他所有可能的钱包UI元素
            const walletElements = [
                'connectWalletBtn',
                'walletAddress',
                'userWalletAddress',
                'currentWalletAddress',
                'walletAddressDisplay'
            ];

            walletElements.forEach(id => {
                const element = document.getElementById(id);
                if (element) {
                    if (element.tagName === 'BUTTON' && element.textContent.includes('Connect')) {
                        element.textContent = formattedAddress;
                    } else if (element.tagName === 'SPAN' || element.tagName === 'DIV') {
                        element.textContent = formattedAddress;
                    }
                }
            });

            // 隐藏连接提示，显示已连接状态
            const connectPrompts = document.querySelectorAll('.wallet-connect-prompt, .connect-wallet-notice');
            connectPrompts.forEach(prompt => {
                if (prompt) prompt.style.display = 'none';
            });

            const connectedIndicators = document.querySelectorAll('.wallet-connected-indicator, .wallet-status-connected');
            connectedIndicators.forEach(indicator => {
                if (indicator) indicator.style.display = 'block';
            });

            console.log('🔄 所有钱包UI已更新:', address);
        } catch (error) {
            console.error('❌ 更新钱包UI失败:', error);
        }
    }

    /**
     * 重置所有钱包UI
     */
    resetAllWalletUI() {
        try {
            // 重置连接按钮
            const walletBtnText = document.getElementById('walletBtnText');
            if (walletBtnText) {
                walletBtnText.textContent = 'Connect Wallet';
            }

            // 重置所有钱包相关元素
            const walletElements = document.querySelectorAll('[id*="wallet"], [class*="wallet"]');
            walletElements.forEach(element => {
                if (element.textContent && element.textContent.includes('...')) {
                    element.textContent = '';
                }
            });

            // 显示连接提示，隐藏已连接状态
            const connectPrompts = document.querySelectorAll('.wallet-connect-prompt, .connect-wallet-notice');
            connectPrompts.forEach(prompt => {
                if (prompt) prompt.style.display = 'block';
            });

            const connectedIndicators = document.querySelectorAll('.wallet-connected-indicator, .wallet-status-connected');
            connectedIndicators.forEach(indicator => {
                if (indicator) indicator.style.display = 'none';
            });

            console.log('🔄 所有钱包UI已重置');
        } catch (error) {
            console.error('❌ 重置钱包UI失败:', error);
        }
    }

    /**
     * 派发钱包事件
     */
    dispatchWalletEvent(eventName, detail) {
        try {
            const event = new CustomEvent(eventName, { detail });
            document.dispatchEvent(event);
        } catch (error) {
            console.error('❌ 派发钱包事件失败:', error);
        }
    }

    /**
     * 显示错误消息
     */
    showError(title, message) {
        console.error(`${title}: ${message}`);
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

    /**
     * 显示成功消息
     */
    showSuccess(title, message) {
        console.log(`${title}: ${message}`);
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: title,
                text: message,
                icon: 'success',
                confirmButtonText: '确定'
            });
        } else {
            alert(`${title}: ${message}`);
        }
    }

    /**
     * 手动断开钱包连接
     */
    async disconnectWallet() {
        try {
            console.log('🔌 手动断开钱包连接...');

            if (window.solana?.isConnected) {
                await window.solana.disconnect();
            }

            this.handleWalletDisconnect();
            this.showSuccess('钱包已断开', '钱包连接已成功断开');

            return true;
        } catch (error) {
            console.error('❌ 断开钱包连接失败:', error);
            this.showError('断开连接失败', error.message);
            return false;
        }
    }
}

// 全局初始化
if (typeof window !== 'undefined') {
    // 确保钱包管理器在DOM加载后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            new UnifiedWalletManager();
        });
    } else {
        new UnifiedWalletManager();
    }

    // 提供全局方法
    window.connectWallet = async function(walletType = 'phantom') {
        if (window.unifiedWalletManager) {
            return await window.unifiedWalletManager.connectWallet(walletType);
        }
        console.error('钱包管理器未初始化');
        return false;
    };

    window.disconnectWallet = async function() {
        if (window.unifiedWalletManager) {
            return await window.unifiedWalletManager.disconnectWallet();
        }
        console.error('钱包管理器未初始化');
        return false;
    };

    window.getWalletAddress = function() {
        if (window.unifiedWalletManager) {
            return window.unifiedWalletManager.getWalletAddress();
        }
        console.error('钱包管理器未初始化');
        return null;
    };

    console.log('🎯 统一钱包管理器已加载');
}