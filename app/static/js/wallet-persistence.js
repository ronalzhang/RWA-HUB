/**
 * 钱包连接状态持久化管理器
 * 解决页面刷新后钱包连接状态丢失的问题
 */

class WalletPersistenceManager {
    constructor() {
        this.STORAGE_KEY = 'rwa_hub_wallet_state';
        this.AUTO_RECONNECT_KEY = 'rwa_hub_auto_reconnect';
        this.initialized = false;
        this.isRestoring = false;  // 防止重复恢复
        
        this.init();
    }

    init() {
        if (this.initialized) return;
        this.initialized = true;
        
        // 页面加载时尝试恢复钱包连接（只在主要页面执行）
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.restoreWalletConnection();
            });
        } else {
            this.restoreWalletConnection();
        }
        
        // 监听钱包断开事件
        this.setupDisconnectionHandlers();
    }

    /**
     * 保存钱包连接状态到localStorage
     */
    saveWalletState(walletState) {
        try {
            const stateToSave = {
                connected: walletState.connected,
                isConnected: walletState.isConnected,
                address: walletState.address,
                walletType: walletState.walletType || 'phantom',
                timestamp: Date.now()
            };

            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(stateToSave));
            localStorage.setItem(this.AUTO_RECONNECT_KEY, 'true');
            
            // 设置cookie让后端知道钱包地址
            this.setWalletCookie(walletState.address);
        } catch (error) {
            console.error('❌ 保存钱包状态失败:', error);
        }
    }

    /**
     * 从localStorage读取钱包状态
     */
    loadWalletState() {
        try {
            const savedState = localStorage.getItem(this.STORAGE_KEY);
            const autoReconnect = localStorage.getItem(this.AUTO_RECONNECT_KEY);
            
            if (!savedState || autoReconnect !== 'true') {
                return null;
            }

            const walletState = JSON.parse(savedState);
            
            // 检查状态是否过期（24小时）
            const now = Date.now();
            const stateAge = now - (walletState.timestamp || 0);
            const maxAge = 24 * 60 * 60 * 1000; // 24小时
            
            if (stateAge > maxAge) {
                this.clearWalletState();
                return null;
            }
            
            return walletState;
        } catch (error) {
            console.error('❌ 读取钱包状态失败:', error);
            return null;
        }
    }

    /**
     * 清除保存的钱包状态
     */
    clearWalletState() {
        try {
            localStorage.removeItem(this.STORAGE_KEY);
            localStorage.removeItem(this.AUTO_RECONNECT_KEY);
            
            // 清除cookie
            this.clearWalletCookie();
        } catch (error) {
            console.error('❌ 清除钱包状态失败:', error);
        }
    }

    /**
     * 页面加载时恢复钱包连接
     */
    async restoreWalletConnection() {
        if (this.isRestoring) return;  // 防止重复执行
        this.isRestoring = true;
        
        try {
            const savedState = this.loadWalletState();
            if (!savedState || !savedState.connected) {
                return;
            }

            // 检查钱包是否仍然可用
            if (savedState.walletType === 'phantom') {
                if (window.solana && window.solana.isPhantom) {
                    // 检查钱包是否仍然连接
                    if (window.solana.isConnected) {
                        // 钱包仍然连接，恢复状态
                        const currentAddress = window.solana.publicKey?.toString();
                        
                        if (currentAddress && currentAddress === savedState.address) {
                            this.restoreWalletUI(savedState);
                            return;
                        }
                    }

                    // 尝试无用户交互的重连（如果钱包支持）
                    try {
                        const response = await window.solana.connect({ onlyIfTrusted: true });
                        if (response && response.publicKey) {
                            const address = response.publicKey.toString();
                            if (address === savedState.address) {
                                this.restoreWalletUI({
                                    ...savedState,
                                    address: address,
                                    publicKey: response.publicKey
                                });
                                return;
                            }
                        }
                    } catch (error) {
                        // 静默处理，无需日志
                    }
                }
            }

            // 如果无法自动恢复，清除保存的状态
            this.clearWalletState();

        } catch (error) {
            this.clearWalletState();
        } finally {
            this.isRestoring = false;
        }
    }

    /**
     * 恢复钱包UI状态
     */
    restoreWalletUI(walletState) {
        try {
            // 恢复全局钱包状态
            window.walletState = {
                connected: true,
                isConnected: true,
                address: walletState.address,
                publicKey: walletState.publicKey || (window.solana?.publicKey),
                walletType: walletState.walletType || 'phantom',
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

            // 更新连接按钮文本 - 使用统一的更新逻辑
            this.updateWalletConnectedUI(walletState.address);

            // 设置cookie让后端知道钱包地址
            this.setWalletCookie(walletState.address);

            // 触发钱包连接事件
            const event = new CustomEvent('walletRestored', {
                detail: { address: walletState.address, walletType: walletState.walletType }
            });
            document.dispatchEvent(event);

            console.log('🎯 钱包UI状态已恢复:', walletState.address);

        } catch (error) {
            console.error('❌ 恢复钱包UI失败:', error);
        }
    }

    /**
     * 更新钱包已连接状态的UI
     */
    updateWalletConnectedUI(address) {
        try {
            // 更新主要连接按钮
            const walletBtnText = document.getElementById('walletBtnText');
            if (walletBtnText && window.walletState?.formatAddress) {
                walletBtnText.textContent = window.walletState.formatAddress(address);
            }

            // 更新下拉菜单中的地址显示
            const walletAddressDisplay = document.getElementById('walletAddressDisplay');
            if (walletAddressDisplay && window.walletState?.formatAddress) {
                walletAddressDisplay.textContent = window.walletState.formatAddress(address);
            }

            // 更新其他钱包相关UI元素
            this.updateWalletUI(address);

            console.log('🔄 钱包UI已更新为已连接状态:', address);
        } catch (error) {
            console.error('❌ 更新钱包连接UI失败:', error);
        }
    }

    /**
     * 设置钱包地址cookie供后端使用
     */
    setWalletCookie(address) {
        try {
            if (address) {
                // 设置cookie，24小时过期
                const expires = new Date();
                expires.setTime(expires.getTime() + 24 * 60 * 60 * 1000);
                document.cookie = `eth_address=${address}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
            }
        } catch (error) {
            console.error('❌ 设置钱包cookie失败:', error);
        }
    }

    /**
     * 清除钱包地址cookie
     */
    clearWalletCookie() {
        try {
            document.cookie = 'eth_address=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; SameSite=Lax';
        } catch (error) {
            console.error('❌ 清除钱包cookie失败:', error);
        }
    }

    /**
     * 更新钱包相关的UI元素
     */
    updateWalletUI(address) {
        try {
            // 更新所有可能显示钱包地址的元素
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
                        element.textContent = window.walletState.formatAddress(address);
                    } else if (id === 'walletAddressDisplay') {
                        element.textContent = window.walletState.formatAddress(address);
                    } else if (element.tagName === 'SPAN' || element.tagName === 'DIV') {
                        element.textContent = address;
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

        } catch (error) {
            console.error('❌ 更新钱包UI失败:', error);
        }
    }

    /**
     * 设置钱包断开事件监听
     */
    setupDisconnectionHandlers() {
        try {
            // 监听Phantom钱包断开事件
            if (window.solana) {
                window.solana.on('disconnect', () => {
                    console.log('🔌 钱包已断开连接');
                    this.clearWalletState();
                    this.resetWalletUI();
                });

                window.solana.on('accountChanged', (publicKey) => {
                    if (publicKey) {
                        console.log('👤 钱包账户已切换:', publicKey.toString());
                        // 更新保存的状态
                        if (window.walletState) {
                            const newState = {
                                ...window.walletState,
                                address: publicKey.toString(),
                                publicKey: publicKey
                            };
                            window.walletState = newState;
                            this.saveWalletState(newState);
                            this.updateWalletUI(publicKey.toString());
                        }
                    } else {
                        console.log('🔌 钱包账户已清空');
                        this.clearWalletState();
                        this.resetWalletUI();
                    }
                });
            }

            // 监听页面卸载时的清理
            window.addEventListener('beforeunload', () => {
                // 保持状态，不清除，以便下次页面加载时恢复
                console.log('📄 页面即将卸载，钱包状态已保持');
            });

        } catch (error) {
            console.error('❌ 设置钱包事件监听失败:', error);
        }
    }

    /**
     * 重置钱包UI到未连接状态
     */
    resetWalletUI() {
        try {
            // 清除全局钱包状态
            window.walletState = null;

            // 重置连接按钮
            const walletBtnText = document.getElementById('walletBtnText');
            if (walletBtnText) {
                walletBtnText.textContent = 'Connect Wallet';
            }

            // 重置其他UI元素
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

            // 触发钱包断开事件
            const event = new CustomEvent('walletDisconnected');
            document.dispatchEvent(event);

            console.log('🔄 钱包UI已重置为未连接状态');

        } catch (error) {
            console.error('❌ 重置钱包UI失败:', error);
        }
    }

    /**
     * 手动触发钱包状态保存（供其他脚本调用）
     */
    static saveCurrentWalletState() {
        if (window.walletPersistenceManager && window.walletState) {
            window.walletPersistenceManager.saveWalletState(window.walletState);
        }
    }

    /**
     * 手动清除钱包状态（供其他脚本调用）
     */
    static clearCurrentWalletState() {
        if (window.walletPersistenceManager) {
            window.walletPersistenceManager.clearWalletState();
            window.walletPersistenceManager.resetWalletUI();
        }
    }
}

// 全局初始化
if (typeof window !== 'undefined') {
    window.walletPersistenceManager = new WalletPersistenceManager();
    
    // 提供全局方法
    window.saveWalletState = WalletPersistenceManager.saveCurrentWalletState;
    window.clearWalletState = WalletPersistenceManager.clearCurrentWalletState;
    
    console.log('🎯 钱包持久化管理器已加载');
}