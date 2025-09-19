/**
 * 统一钱包管理系统 v2.0
 * 简洁、可靠、持久化的钱包连接管理
 *
 * 功能特性：
 * - 只支持Phantom钱包
 * - 自动持久化连接状态
 * - 刷新页面保持连接
 * - 统一的状态管理
 * - 简洁的API接口
 */

class UnifiedWalletManager {
    constructor() {
        this.isInitialized = false;
        this.walletState = {
            connected: false,
            address: null,
            publicKey: null
        };

        // 存储键名
        this.STORAGE_KEY = 'rwa_wallet_state';

        this.init();
    }

    async init() {
        if (this.isInitialized) return;

        console.log('🔄 初始化统一钱包管理器...');

        // 加载持久化状态
        this.loadPersistedState();

        // 设置Phantom钱包事件监听
        this.setupWalletListeners();

        // 尝试自动重连
        await this.autoReconnect();

        this.isInitialized = true;
        console.log('✅ 统一钱包管理器初始化完成');
    }

    // 加载持久化状态
    loadPersistedState() {
        try {
            const saved = localStorage.getItem(this.STORAGE_KEY);
            if (saved) {
                const state = JSON.parse(saved);
                if (state.connected && state.address) {
                    this.walletState = { ...state };
                    console.log('📄 加载已保存的钱包状态:', this.formatAddress(state.address));
                }
            }
        } catch (error) {
            console.warn('⚠️ 加载钱包状态失败:', error);
            this.clearPersistedState();
        }
    }

    // 保存状态到本地存储
    saveState() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.walletState));
        } catch (error) {
            console.error('❌ 保存钱包状态失败:', error);
        }
    }

    // 清除持久化状态
    clearPersistedState() {
        localStorage.removeItem(this.STORAGE_KEY);
        // 清理旧的存储键（兼容性）
        localStorage.removeItem('walletAddress');
        localStorage.removeItem('eth_address');
        localStorage.removeItem('phantomConnected');
    }

    // 设置钱包事件监听
    setupWalletListeners() {
        if (window.solana) {
            // 监听钱包断开事件
            window.solana.on('disconnect', () => {
                console.log('🔌 钱包已断开连接');
                this.handleDisconnect();
            });

            // 监听账户变更事件
            window.solana.on('accountChanged', (publicKey) => {
                if (publicKey) {
                    console.log('🔄 钱包账户已更改:', publicKey.toString());
                    this.updateWalletState(publicKey.toString(), publicKey);
                } else {
                    this.handleDisconnect();
                }
            });
        }
    }

    // 自动重连
    async autoReconnect() {
        if (!this.walletState.connected || !this.walletState.address) {
            return false;
        }

        console.log('🔄 尝试自动重连钱包...');

        if (!window.solana?.isPhantom) {
            console.log('⚠️ Phantom钱包未安装，清除已保存状态');
            this.handleDisconnect();
            return false;
        }

        try {
            // 检查Phantom是否已连接
            if (window.solana.isConnected && window.solana.publicKey) {
                const currentAddress = window.solana.publicKey.toString();

                if (currentAddress === this.walletState.address) {
                    console.log('✅ 自动重连成功:', this.formatAddress(currentAddress));
                    this.updateUI();
                    return true;
                } else {
                    console.log('🔄 检测到不同的钱包地址，更新状态');
                    this.updateWalletState(currentAddress, window.solana.publicKey);
                    return true;
                }
            } else {
                // 尝试静默连接（如果用户之前已授权）
                await window.solana.connect({ onlyIfTrusted: true });

                if (window.solana.isConnected && window.solana.publicKey) {
                    const address = window.solana.publicKey.toString();
                    console.log('✅ 静默重连成功:', this.formatAddress(address));
                    this.updateWalletState(address, window.solana.publicKey);
                    return true;
                }
            }
        } catch (error) {
            console.warn('⚠️ 自动重连失败:', error.message);
            this.handleDisconnect();
        }

        return false;
    }

    // 连接钱包
    async connect() {
        console.log('🔄 开始连接Phantom钱包...');

        if (!window.solana?.isPhantom) {
            alert('请安装Phantom钱包扩展\n\n访问: https://phantom.app/\n\n安装后刷新页面重试');
            return false;
        }

        try {
            const response = await window.solana.connect();

            if (response.publicKey) {
                const address = response.publicKey.toString();
                console.log('✅ 钱包连接成功:', this.formatAddress(address));

                this.updateWalletState(address, response.publicKey);
                return true;
            }
        } catch (error) {
            console.error('❌ 连接钱包失败:', error);

            if (error.code === 4001) {
                alert('用户拒绝了连接请求');
            } else if (error.code === -32002) {
                alert('钱包连接请求正在处理中，请检查Phantom钱包');
            } else {
                alert('连接钱包失败，请重试');
            }
        }

        return false;
    }

    // 断开连接
    async disconnect() {
        console.log('🔌 断开钱包连接...');

        try {
            if (window.solana?.isConnected) {
                await window.solana.disconnect();
            }
        } catch (error) {
            console.warn('断开连接时出现错误:', error);
        }

        this.handleDisconnect();
    }

    // 处理断开连接
    handleDisconnect() {
        this.walletState = {
            connected: false,
            address: null,
            publicKey: null
        };

        this.clearPersistedState();
        this.updateUI();

        console.log('🔌 钱包状态已重置');
    }

    // 更新钱包状态
    updateWalletState(address, publicKey) {
        this.walletState = {
            connected: true,
            address: address,
            publicKey: publicKey
        };

        this.saveState();
        this.updateUI();

        // 触发全局事件
        window.dispatchEvent(new CustomEvent('walletStateChanged', {
            detail: { ...this.walletState }
        }));
    }

    // 更新UI显示
    updateUI() {
        const walletBtn = document.getElementById('walletBtn');
        const walletBtnText = document.getElementById('walletBtnText');

        if (this.walletState.connected) {
            if (walletBtnText) {
                walletBtnText.textContent = this.formatAddress(this.walletState.address);
            }
            if (walletBtn) {
                walletBtn.classList.remove('btn-outline-primary');
                walletBtn.classList.add('btn-success');
            }
        } else {
            if (walletBtnText) {
                walletBtnText.textContent = 'Connect Wallet';
            }
            if (walletBtn) {
                walletBtn.classList.remove('btn-success');
                walletBtn.classList.add('btn-outline-primary');
            }
        }
    }

    // 格式化地址显示
    formatAddress(address) {
        if (!address) return '';
        return address.slice(0, 6) + '...' + address.slice(-4);
    }

    // 复制地址到剪贴板
    async copyAddress() {
        if (!this.walletState.address) return false;

        try {
            await navigator.clipboard.writeText(this.walletState.address);

            // 显示复制成功提示
            const successMsg = document.getElementById('copyAddressSuccess');
            if (successMsg) {
                successMsg.style.opacity = '1';
                setTimeout(() => {
                    successMsg.style.opacity = '0';
                }, 2000);
            }

            return true;
        } catch (error) {
            console.error('复制地址失败:', error);
            return false;
        }
    }

    // 获取当前状态
    getState() {
        return { ...this.walletState };
    }

    // 检查是否已连接
    isConnected() {
        return this.walletState.connected && !!this.walletState.address;
    }

    // 获取钱包地址
    getAddress() {
        return this.walletState.address;
    }
}

// 创建全局实例
if (!window.unifiedWalletManager) {
    window.unifiedWalletManager = new UnifiedWalletManager();

    // 为了兼容性，提供旧的API
    window.connectWallet = async () => {
        return await window.unifiedWalletManager.connect();
    };

    window.disconnectWallet = async () => {
        return await window.unifiedWalletManager.disconnect();
    };

    window.getWalletAddress = () => {
        return window.unifiedWalletManager.getAddress();
    };

    console.log('✅ 统一钱包管理器已加载');
}