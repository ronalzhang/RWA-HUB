// 钱包状态管理
const walletState = {
    address: null,
    isConnected: false,
    isAdmin: false,
    eventCallbacks: new Set(), // 用于存储状态变化的回调函数
    connecting: false,
    usdcBalance: '0.00', // 添加USDC余额属性
    
    // 支持的网络配置
    NETWORK_CONFIG: {
        mainnet: {
            name: 'Solana Mainnet',
            endpoint: 'https://api.mainnet-beta.solana.com',
            chainId: '101',
        },
        devnet: {
            name: 'Solana Devnet',
            endpoint: 'https://api.devnet.solana.com',
            chainId: '103',
        },
        testnet: {
            name: 'Solana Testnet',
            endpoint: 'https://api.testnet.solana.com',
            chainId: '102',
        }
    },

    // 初始化钱包状态
    async init() {
        console.log('初始化钱包...');
        
        try {
            // 检查是否存在Solana钱包
            if (!window.solana) {
                console.warn('未检测到Solana钱包，将使用模拟实现');
                // 这里不抛出错误，因为我们有模拟实现作为备选
            } else {
                console.log('检测到Solana钱包');
                
                // 检查钱包是否已经连接
                try {
                    if (window.solana._connected || (window.solana.isConnected && await window.solana.isConnected())) {
                        console.log('Solana钱包已连接，获取地址');
                        
                        // 获取已连接的地址
                        const publicKey = window.solana._publicKey || 
                                         (window.solana.publicKey ? window.solana.publicKey : null);
                        
                        if (publicKey) {
                            this.address = publicKey.toString();
                            this.isConnected = true;
                            console.log(`检测到已连接的钱包地址: ${this.address}`);
                            
                            // 更新UI显示
                            const walletBtn = document.getElementById('wallet-btn');
                            if (walletBtn) {
                                walletBtn.innerText = this.address.slice(0, 4) + '...' + this.address.slice(-4);
                            }
                            
                            // 获取余额
                            await this.getWalletBalance();
                            
                            // 监听断开连接事件
                            window.solana.on('disconnect', () => {
                                console.log('钱包断开连接');
                                this.isConnected = false;
                                this.address = null;
                                
                                const updateElement = document.getElementById('wallet-btn');
                                if (updateElement) {
                                    updateElement.innerText = '连接钱包';
                                }
                            });
                            
                            return true;
                        }
                    } else {
                        console.log('Solana钱包未连接');
                    }
                } catch (err) {
                    console.warn('检查钱包连接状态时出错:', err);
                }
            }
            
            return false;
        } catch (error) {
            console.error('钱包初始化失败:', error);
            throw error;
        }
    },

    // 清理所有状态
    clearAllStates() {
        this.address = null;
        this.isConnected = false;
        this.isAdmin = false;
        this.connecting = false;
        this.eventCallbacks.clear();
        
        // 清除本地存储
        localStorage.removeItem('walletConnected');
        sessionStorage.removeItem('walletAddress');
        
        // 清除所有相关的 cookie
        this.clearState();
        
        // 移除所有事件监听器
        if (window.solana) {
            window.solana.removeAllListeners('disconnect');
        }
    },

    // 检查并切换网络
    async checkAndSwitchNetwork(chainId) {
        const networkInfo = this.NETWORK_CONFIG[chainId];
        if (!networkInfo) {
            const supportedNetworks = Object.values(this.NETWORK_CONFIG)
                .map(n => n.name)
                .join('、');
                
            const message = `当前网络不受支持，请切换到以下网络之一：${supportedNetworks}`;
            if (confirm(message)) {
                try {
                    await window.solana.connect({ cluster: chainId });
                    console.log('Network switched successfully');
                    return true;
                } catch (switchError) {
                    if (switchError.code === 4902) {
                        try {
                            const mainnet = this.NETWORK_CONFIG.mainnet;
                            await window.solana.connect({ cluster: mainnet.chainId });
                            console.log('Network added successfully');
                            return true;
                        } catch (addError) {
                            console.error('Failed to add network:', addError);
                            showError('添加网络失败，请手动切换到支持的网络');
                            return false;
                        }
                    }
                    console.error('Failed to switch network:', switchError);
                    showError('网络切换失败，请手动切换到支持的网络');
                    return false;
                }
            }
            return false;
        }
        return true;
    },

    // 设置事件监听器
    setupEventListeners() {
        if (!window.solana) return;

        // 断开连接事件
        window.solana.on('disconnect', async (error) => {
            console.log('Wallet disconnected', error);
            await this.disconnect();
        });
    },
    
    // 检查网络连接
    async checkNetworkConnectivity() {
        try {
            // 尝试连接以太坊主网
            const response = await fetch('https://api.etherscan.io/api', {
                method: 'HEAD',
                mode: 'no-cors'
            });
            return true;
        } catch (error) {
            console.warn('Network connectivity check failed:', error);
            return false;
        }
    },
    
    // 检查是否正在处理连接请求
    async checkProcessingState() {
        try {
            // 首先检查网络连接
            const isNetworkConnected = await this.checkNetworkConnectivity();
            if (!isNetworkConnected) {
                throw new Error('无法连接到以太坊网络，请检查网络连接或使用VPN');
            }

            // 检查 MetaMask 是否已解锁
            const isUnlocked = await window.solana._metamask.isUnlocked();
            if (!isUnlocked) {
                return true; // MetaMask 未解锁，需要用户操作
            }

            // 检查是否有正在处理的请求
            try {
                await window.solana.connection.getClusterNodes();
                return false;
            } catch (error) {
                if (error.code === -32002) {
                    return true;
                }
                return false;
            }
        } catch (error) {
            console.warn('Failed to check processing state:', error);
            if (error.message.includes('VPN')) {
                throw error; // 如果是网络连接问题，直接抛出
            }
            return false;
        }
    },
    
    /**
     * 连接钱包
     */
    async connect() {
        console.log('尝试连接钱包...');
        
        // 如果已经连接，直接返回
        if (this.isConnected) {
            console.log('钱包已经连接，无需重复连接');
            return true;
        }
        
        // 重置连接状态，避免重复连接错误
        this.connecting = false;
        
        if (this.connecting) {
            console.warn('正在处理连接请求，请稍候...');
            throw new Error('正在处理连接请求，请稍候...');
        }
        
        try {
            this.connecting = true;
            console.log('设置连接状态: connecting = true');
            
            // 检查是否存在Solana钱包
            if (!window.solana) {
                console.error('未检测到Solana钱包扩展');
                this.connecting = false;
                throw new Error('未检测到Solana钱包，请安装Phantom或Solflare等Solana钱包');
            }

            console.log('检测到Solana钱包，开始连接...');
            // 检查是否是Phantom钱包
            if (window.solana.isPhantom) {
                console.log('检测到Phantom钱包');
            }
            
            const updateElement = document.getElementById('walletBtn');
            if (updateElement) {
                updateElement.innerText = '连接中...';
            }
            
            try {
                // 连接Solana钱包
                console.log('请求连接Solana钱包...');
                const resp = await window.solana.connect();
                console.log('Solana钱包连接成功:', resp);
                
                // 更新地址和连接状态
                this.address = resp.publicKey.toString();
                this.isConnected = true;
                
                // 更新UI显示
                if (updateElement) {
                    updateElement.innerText = this.address.slice(0, 4) + '...' + this.address.slice(-4);
                }
                
                console.log(`钱包已连接，地址: ${this.address}`);
                
                // 监听断开连接事件
                window.solana.on('disconnect', () => {
                    console.log('钱包断开连接');
                    this.isConnected = false;
                    this.address = null;
                    
                    if (updateElement) {
                        updateElement.innerText = '连接钱包';
                    }
                });
                
                // 尝试获取余额
                await this.getWalletBalance();
                
                return true;
            } catch (error) {
                console.error('连接钱包时发生错误:', error);
                
                if (updateElement) {
                    updateElement.innerText = '连接钱包';
                }
                
                throw new Error(`连接钱包失败: ${error.message}`);
            } finally {
                this.connecting = false;
                console.log('重置连接状态: connecting = false');
            }
        } catch (error) {
            this.connecting = false;
            console.error('钱包连接过程出错:', error);
            throw error;
        }
    },
    
    // 断开钱包连接
    async disconnect(silent = false) {
        console.log('Disconnecting wallet...');
        try {
            if (window.solana) {
                await window.solana.disconnect();
            }

            this.address = null;
            this.isConnected = false;
            this.isAdmin = false;
            
            localStorage.removeItem('walletConnected');
            sessionStorage.removeItem('walletAddress');
            
            this.clearState();
            this.updateUI();
            
            if (!silent) {
                this.notifyStateChange();
            }
            
            const walletMenu = document.getElementById('walletMenu');
            if (walletMenu) {
                walletMenu.classList.remove('show');
            }
            
            return true;
        } catch (error) {
            console.error('Error during wallet disconnect:', error);
            return false;
        }
    },
    
    // 切换钱包
    async switchWallet() {
        console.log('Switching wallet...');
        try {
            // 请求切换账户
            await window.solana.connect({ cluster: 'devnet' });

            // 获取新的账户
            const resp = await window.solana.connect();

            // 验证新账户
            if (resp) {
                this.address = resp.publicKey.toString();
                this.isConnected = true;
                localStorage.setItem('walletConnected', 'true');
                await this.checkIsAdmin();
                this.updateUI();
                this.notifyStateChange();
                return true;
            } else {
                // 如果没有选择新账户，则断开连接
                await this.disconnect();
                return false;
            }
        } catch (error) {
            console.error('Failed to switch wallet:', error);
            // 如果用户取消或发生错误，保持当前连接状态
            if (error.code === 4001) { // 用户拒绝
                return false;
            }
            // 其他错误则断开连接
            await this.disconnect();
            throw error;
        }
    },
    
    // 获取钱包余额
    async getWalletBalance() {
        if (!this.isConnected || !this.address) {
            console.log('钱包未连接，无法获取余额');
            return null;
        }
        
        try {
            // 测试环境下返回模拟数据
            console.log('获取钱包余额 (模拟)');
            
            // 生成随机余额，并保存到对象属性中
            const mockBalance = (Math.random() * 10000).toFixed(2);
            this.usdcBalance = mockBalance;
            console.log('获取到的USDC余额:', mockBalance);
            
            return {
                value: mockBalance,
                symbol: 'USDC'
            };
            
            // 实际实现 (注释掉)
            /*
            // 获取 USDC 代币账户
            const USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'; // Solana USDC
            const connection = new solanaWeb3.Connection(this.NETWORK_CONFIG.mainnet.endpoint);
            const publicKey = new solanaWeb3.PublicKey(this.address);
            
            // 查找 USDC 代币账户
            const tokenAccounts = await connection.getParsedTokenAccountsByOwner(publicKey, {
                mint: new solanaWeb3.PublicKey(USDC_MINT)
            });
            
            if (tokenAccounts.value.length > 0) {
                const balance = tokenAccounts.value[0].account.data.parsed.info.tokenAmount.uiAmount;
                this.usdcBalance = balance.toFixed(1);
                return {
                    value: this.usdcBalance,
                    symbol: 'USDC'
                };
            }
            
            this.usdcBalance = '0.0';
            return {
                value: '0.0',
                symbol: 'USDC'
            };
            */
        } catch (error) {
            console.error('获取余额失败:', error);
            return null;
        }
    },

    // 更新UI
    async updateUI() {
        console.log('更新钱包状态显示');
        
        const walletBtn = document.getElementById('walletBtn');
        const walletMenu = document.getElementById('walletMenu');
        const walletBtnText = document.getElementById('walletBtnText');
        const balanceDisplay = document.getElementById('walletBalance');
        
        if (!walletBtn || !walletBtnText) {
            console.warn('钱包按钮元素未找到');
            return;
        }
        
        console.log('连接状态:', this.isConnected, '地址:', this.address);
        
        if (this.isConnected && this.address) {
            // 尝试获取余额
            try {
                walletBtnText.textContent = '获取余额中...';
                const balance = await this.getWalletBalance();
                
                if (balance) {
                    const displayText = `${this.address.substring(0, 4)}...${this.address.substring(this.address.length - 4)} (${balance.value} ${balance.symbol})`;
                    console.log('显示余额:', displayText);
                    walletBtnText.textContent = displayText;
                } else {
                    const shortAddress = `${this.address.substring(0, 4)}...${this.address.substring(this.address.length - 4)}`;
                    console.log('无法获取余额，只显示地址:', shortAddress);
                    walletBtnText.textContent = shortAddress;
                }
                
                // 更新按钮样式
                walletBtn.classList.remove('btn-outline-primary');
                walletBtn.classList.add('btn-primary');
                
                // 更新钱包菜单中的地址显示
                if (walletMenu) {
                    const addressElem = walletMenu.querySelector('.wallet-address');
                    if (addressElem) {
                        addressElem.textContent = this.address;
                    }
                    
                    // 更新余额显示
                    if (balanceDisplay && balance) {
                        balanceDisplay.textContent = `${balance.value} ${balance.symbol}`;
                    }
                }
            } catch (error) {
                console.error('获取余额失败:', error);
                walletBtnText.textContent = `${this.address.substring(0, 4)}...${this.address.substring(this.address.length - 4)}`;
            }
        } else {
            console.log('钱包未连接，显示默认文本');
            walletBtnText.textContent = '连接钱包';
            walletBtn.classList.remove('btn-primary');
            walletBtn.classList.add('btn-outline-primary');
            
            // 关闭钱包菜单
            if (walletMenu && walletMenu.classList.contains('show')) {
                walletMenu.classList.remove('show');
            }
        }
    },
    
    // 获取连接状态
    getConnectionStatus() {
        return this.isConnected;
    },
    
    // 获取当前钱包地址
    getAddress() {
        return this.address;
    },
    
    // 检查管理员权限
    async checkIsAdmin() {
        if (!this.address) return false;
        
        try {
            // 根据地址类型决定是否转换为小写
            // ETH地址以0x开头，需要转为小写
            // SOL地址不以0x开头，保持原样（大小写敏感）
            const addressStr = this.address.startsWith('0x') ? this.address.toLowerCase() : this.address;
            
            const response = await fetch('/api/admin/check', {
                headers: {
                    'X-Eth-Address': addressStr
                }
            });
            
            if (!response.ok) {
                throw new Error('检查管理员权限失败');
            }
            
            const data = await response.json();
            this.isAdmin = data.is_admin;
            this.updateUI();
            
            return data.is_admin;
        } catch (error) {
            console.error('Failed to check admin status:', error);
            return false;
        }
    },

    // 注册状态变化回调
    onStateChange(callback) {
        this.eventCallbacks.add(callback);
    },

    // 移除状态变化回调
    offStateChange(callback) {
        this.eventCallbacks.delete(callback);
    },

    // 通知所有注册的回调
    notifyStateChange() {
        const state = {
            address: this.address,
            isConnected: this.isConnected,
            isAdmin: this.isAdmin
        };
        this.eventCallbacks.forEach(callback => callback(state));
    },

    // 清除状态
    clearState() {
        document.cookie = 'eth_address=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    }
};

// 初始化
let walletInitialized = false;
document.addEventListener('DOMContentLoaded', async function() {
    if (walletInitialized) return;
    walletInitialized = true;

    console.log('Initializing wallet...');
    window.walletState = walletState;
    await walletState.init();
    
    // 绑定钱包按钮事件
    const walletBtn = document.getElementById('walletBtn');
    const walletMenu = document.getElementById('walletMenu');
    const switchWalletBtn = document.getElementById('switchWallet');
    const disconnectWalletBtn = document.getElementById('disconnectWallet');
    
    if (walletBtn) {
        walletBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Wallet button clicked, isConnected:', walletState.isConnected); // 加入状态信息
            
            // 在点击连接钱包时检查钱包插件
            if (typeof window.solana === 'undefined') {
                const userAgent = navigator.userAgent.toLowerCase();
                if (userAgent.includes('mobile')) {
                    alert('请在移动设备上安装支持的钱包插件，如MetaMask或Trust Wallet。');
                } else {
                    alert('请安装支持的钱包插件，如MetaMask。');
                }
                return;
            }
            
            if (!walletState.getConnectionStatus()) {
                try {
                    console.log('Attempting to connect wallet...'); // 添加连接尝试日志
                    await walletState.connect();
                } catch (error) {
                    console.error('Connection failed:', error); // 添加错误日志
                    showError(error.message);
                }
            } else {
                // 如果已连接，显示下拉菜单
                console.log('Wallet already connected, toggling menu'); // 添加菜单切换日志
                walletMenu.classList.toggle('show');
            }
        });
    }
    
    // 绑定切换钱包事件
    if (switchWalletBtn) {
        switchWalletBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Switch wallet button clicked'); // 调试输出
            try {
                await walletState.switchWallet();
                if (walletMenu) {
                    walletMenu.classList.remove('show');
                }
            } catch (error) {
                showError(error.message);
            }
        });
    }

    // 绑定断开连接事件
    if (disconnectWalletBtn) {
        disconnectWalletBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Disconnect wallet button clicked'); // 调试输出
            try {
                await walletState.disconnect();
                if (walletMenu) {
                    walletMenu.classList.remove('show');
                }
            } catch (error) {
                showError(error.message);
            }
        });
    }
    
    // 点击其他地方关闭菜单
    document.addEventListener('click', (e) => {
        if (walletMenu.classList.contains('show') && 
            !walletBtn.contains(e.target) && !walletMenu.contains(e.target)) {
            walletMenu.classList.remove('show');
        }
    });

    // ESC 键关闭菜单
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && walletMenu && walletMenu.classList.contains('show')) {
            walletMenu.classList.remove('show');
        }
    });
});

// 显示错误信息
function showError(message) {
    const errorModal = document.getElementById('errorModal');
    if (errorModal) {
        const errorMessage = document.getElementById('errorMessage');
        if (errorMessage) {
            errorMessage.textContent = message;
        }
        const modal = new bootstrap.Modal(errorModal);
        modal.show();
    } else {
        console.error(message);
        alert(message);
    }
}

// 语言切换函数
window.changeLanguage = function(lang) {
    document.cookie = `language=${lang};path=/;max-age=31536000`;
    window.location.reload();
}

// 自动检测已安装钱包
async function detectWallet() {
    const walletConnectButton = document.getElementById('walletBtn'); // 确保获取到钱包按钮
    if (window.solana) {
        // 显示连接选项
        walletConnectButton.style.display = 'block';
    } else {
        // 只在用户点击连接钱包时提示
        walletConnectButton.style.display = 'none'; // 隐藏按钮
    }
}

// 在页面加载时不再调用 detectWallet
// detectWallet(); // 移除此行 