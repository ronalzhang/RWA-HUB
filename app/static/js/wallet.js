/**
 * RWA-HUB 钱包管理模块
 * 支持多种钱包类型的连接、管理和状态同步
 */

// 钱包状态管理类
const walletState = {
    // 状态变量
    address: null,             // 当前连接的钱包地址
    walletType: null,          // 当前连接的钱包类型: 'ethereum', 'phantom' 等
    connected: false,          // 是否已连接钱包
    isAdmin: false,            // 是否是管理员账户
    balance: 0,                // 当前钱包余额
    nativeBalance: 0,          // 原生代币余额
    connecting: false,         // 是否正在连接中
    chainId: null,             // 当前连接的链ID
    assets: [],                // 当前钱包拥有的资产
    stateChangeCallbacks: [],  // 状态变更回调函数数组
    web3: null,                // Web3实例（以太坊钱包）
    provider: null,            // 钱包提供商实例
    pendingWalletAppOpen: false, // 是否正在等待打开钱包App（移动端）
    pendingWalletType: null,   // 待连接的钱包类型（移动端打开App时）
    web3Available: true,       // 标记Web3.js是否可用
    initialized: false,        // 标记钱包是否已初始化
    
    /**
     * 初始化钱包状态
     * 检查之前保存的钱包状态并尝试自动恢复连接
     * @returns {Promise<void>}
     */
    async init() {
        console.log('初始化钱包...');
        this.stateChangeCallbacks = [];
        
        try {
            // 检查是否从钱包App返回
            const isMobile = this.isMobile();
            const fromWalletApp = sessionStorage.getItem('returningFromWalletApp');
            const pendingWalletType = localStorage.getItem('pendingWalletType');
            
            // 如果从钱包应用返回，尝试立即连接
            if (isMobile && fromWalletApp && pendingWalletType) {
                console.log(`检测到从钱包应用返回，尝试连接: ${pendingWalletType}`);
                sessionStorage.removeItem('returningFromWalletApp');
                localStorage.removeItem('pendingWalletType');
                
                try {
                    await this.connectToProvider(pendingWalletType);
                    return; // 如果连接成功，直接返回
                } catch (err) {
                    console.warn(`自动连接钱包 ${pendingWalletType} 失败:`, err);
                }
            }
            
            // 从持久化存储恢复钱包状态
            const savedWalletType = localStorage.getItem('walletType');
            const savedWalletAddress = localStorage.getItem('walletAddress');
            
            console.log(`从本地存储检查钱包状态: ${savedWalletType} ${savedWalletAddress}`);
            
            if (!savedWalletType || !savedWalletAddress) {
                console.log('未找到保存的钱包信息');
                return;
            }
            
            // 根据不同钱包类型恢复连接
            let restored = false;
            
            switch (savedWalletType) {
                case 'ethereum':
                    if (window.ethereum) {
                        try {
                            // 检查以太坊钱包状态
                            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
                            
                            if (accounts && accounts.length > 0) {
                                // 验证地址是否匹配
                                if (accounts[0].toLowerCase() === savedWalletAddress.toLowerCase()) {
                                    console.log('恢复以太坊钱包连接');
                                    this.address = accounts[0];
                                    this.walletType = 'ethereum';
                                    this.connected = true;
                                    
                                    // 设置Web3实例
                                    if (window.Web3) {
                                        this.web3 = new Web3(window.ethereum);
                                    }
                                    
                                    // 获取链ID
                                    this.chainId = await window.ethereum.request({ method: 'eth_chainId' });
                                    
                                    // 设置事件监听器
                                    this.setupEthereumListeners();
                                    
                                    // 获取余额和资产
                                    await this.getWalletBalance();
                                    await this.getUserAssets(this.address);
                                    
                                    // 检查是否为管理员
                                    await this.checkIsAdmin();
                                    
                                    restored = true;
                                }
                    }
                } catch (err) {
                            console.error('恢复以太坊钱包连接失败:', err);
                        }
                    }
                    break;
                    
                case 'phantom':
                    if (window.solana?.isPhantom) {
                        try {
                            // 检查Phantom钱包状态
                            const resp = await window.solana.connect({ onlyIfTrusted: true });
                            
                            if (resp.publicKey.toString() === savedWalletAddress) {
                                console.log('恢复Phantom钱包连接');
                                this.address = resp.publicKey.toString();
                                this.walletType = 'phantom';
                                this.connected = true;
                                this.provider = window.solana;
                                
                                // 设置事件监听器
                                this.setupPhantomListeners();
                                
                                // 获取余额和资产
                                await this.getWalletBalance();
                                await this.getUserAssets(this.address);
                                
                                // 检查是否为管理员
                                await this.checkIsAdmin();
                                
                                restored = true;
                            }
                        } catch (err) {
                            console.error('恢复Phantom钱包连接失败:', err);
                        }
                    }
                    break;
                    
                // 可以添加其他钱包类型的恢复逻辑
            }
            
            if (!restored) {
                console.log('无法恢复保存的钱包连接，清除存储');
                this.clearState();
            } else {
                console.log('成功恢复钱包连接:', {
                    address: this.address ? this.address.substring(0, 8) + '...' : 'none',
                    walletType: this.walletType,
                    connected: this.connected
                });
                
                // 成功恢复时，设置标志以便其他组件可以识别恢复的状态
                this.isRestoredConnection = true;
            }
            
        } catch (error) {
            console.error('钱包初始化失败:', error);
            this.clearState();
        } finally {
            // 更新UI显示
            await this.updateUI();
            
            // 设置页面离开前处理钱包App返回
            window.addEventListener('beforeunload', () => {
                if (this.pendingWalletAppOpen) {
                    sessionStorage.setItem('returningFromWalletApp', 'true');
                    localStorage.setItem('pendingWalletType', this.pendingWalletType || '');
                }
            });
            
            // 初始化完成，触发状态变更事件
            this.notifyStateChange();
        }
    },
    
    /**
     * 清除所有钱包状态
     */
    clearState() {
        // 清除内存中的状态
        this.address = null;
        this.walletType = null;
        this.connected = false;
        this.isAdmin = false;
        this.balance = 0;
        this.nativeBalance = 0;
        this.assets = [];
        this.chainId = null;
        this.web3 = null;
        this.provider = null;
        
        // 清除本地存储
        localStorage.removeItem('walletType');
        localStorage.removeItem('walletAddress');
        localStorage.removeItem('lastWalletType');
        localStorage.removeItem('lastWalletAddress');
        localStorage.removeItem('pendingWalletType');
        sessionStorage.removeItem('returningFromWalletApp');
        
        // 移除可能存在的事件监听器
        if (window.ethereum) {
            window.ethereum.removeAllListeners?.();
        }
        
        if (window.solana) {
            window.solana.removeAllListeners?.();
        }
    },
    
    /**
     * 检测是否为移动设备
     * @returns {boolean} 是否为移动设备
     */
    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    },

    /**
     * 连接钱包
     * 显示钱包选择对话框，允许用户选择钱包类型
     * @returns {Promise<boolean>} 连接成功返回true，失败返回false
     */
    async connect() {
        if (this.connecting) {
            console.log('已有连接请求正在进行中');
                            return false;
                        }
        
        this.connecting = true;
        
        try {
            // 显示钱包选择对话框
            const walletType = await this.showWalletOptions();
            
            if (!walletType) {
                console.log('用户取消了钱包选择');
                    return false;
                }
            
            console.log(`用户选择了 ${walletType} 钱包`);
            
            // 连接到选定的钱包
            await this.connectToProvider(walletType);
            
            // 更新UI
            await this.updateUI();
            
                    return true;
        } catch (error) {
            console.error('连接钱包失败:', error);
            showError(error.message || '连接钱包失败');
                            return false;
        } finally {
            this.connecting = false;
        }
    },
    
    /**
     * 连接到指定钱包提供商
     * @param {string} provider 钱包提供商类型
     * @returns {Promise<boolean>} 连接是否成功
     */
    async connectToProvider(provider) {
        console.log(`尝试连接到 ${provider} 钱包...`);
        
        // 记录当前尝试连接的钱包类型，用于移动端返回处理
        this.pendingWalletType = provider;
        
        // 如果已连接，先断开
        if (this.connected && this.address) {
            console.log('已经连接到钱包，先断开当前连接');
            await this.disconnect(true);
        }
        
        try {
            // 检测是否是移动设备
            const isMobile = this.isMobile();
            
            // 标记可能将要打开钱包应用
            if (isMobile) {
                this.pendingWalletAppOpen = true;
                
                // 2秒后重置标记，避免误判
                setTimeout(() => {
                    this.pendingWalletAppOpen = false;
                }, 2000);
            }
            
            let result = false;
            
            try {
                switch (provider) {
                    case 'ethereum':
                        result = await this.connectEthereum();
                        break;
                    case 'phantom':
                        result = await this.connectPhantom();
                        break;
                    // 其他钱包类型的连接方法
                    default:
                        throw new Error(`不支持的钱包类型: ${provider}`);
                }
            } catch (error) {
                console.error(`连接到 ${provider} 钱包时出错:`, error);
                // 显示用户友好的错误提示
                showError(error.message || `连接到 ${provider} 钱包失败`);
                throw error;
            }
            
            if (result && this.address) {
                // 连接成功，保存状态到本地存储
                localStorage.setItem('walletType', provider);
                localStorage.setItem('walletAddress', this.address);
                localStorage.setItem('lastWalletType', provider);
                localStorage.setItem('lastWalletAddress', this.address);
                
                // 获取余额
                await this.getWalletBalance();
                
                // 获取用户资产
                await this.getUserAssets(this.address);
                
                // 检查是否为管理员
                await this.checkIsAdmin();
                
                // 触发状态变更事件
                this.notifyStateChange();
                
                // 连接成功提示
                const truncatedAddress = this.address.slice(0, 6) + '...' + this.address.slice(-4);
                showSuccess(`${provider} 钱包已连接: ${truncatedAddress}`);
                
                console.log(`${provider} 钱包连接成功:`, this.address);
            }
            
            // 连接成功后重置标记
            this.pendingWalletAppOpen = false;
            this.pendingWalletType = null;
            
            return result;
        } catch (error) {
            // 连接失败也要重置标记
            this.pendingWalletAppOpen = false;
            this.pendingWalletType = null;
            
            console.error(`连接到 ${provider} 钱包时出错:`, error);
            this.clearState();
            this.updateUI();
            throw error;
        }
    },
    
    /**
     * 断开钱包连接
     * @param {boolean} reload 是否刷新页面，默认为true
     */
    async disconnect(reload = true) {
        console.log('[disconnect] 断开钱包连接');
        
        // 保存当前状态以便记录变化
        const wasConnected = this.connected;
        const previousAddress = this.address;
        
        // 清除连接状态
        this.connected = false;
        this.address = null;
        this.walletType = null;
        this.balance = 0;
        this.nativeBalance = 0;
        this.isAdmin = false;
        this.assets = [];
        
        try {
            // 清除本地存储
            localStorage.removeItem('walletAddress');
            localStorage.removeItem('walletType');
            sessionStorage.removeItem('walletAddress');
            sessionStorage.removeItem('walletType');
            
            console.log('[disconnect] 已清除本地存储的钱包信息');
            
            // 如果在连接状态下断开，才触发事件
            if (wasConnected) {
                console.log('[disconnect] 触发断开连接事件');
                this.notifyStateChange({
                    type: 'disconnect',
                    address: previousAddress,
                    message: '钱包已断开连接'
                });
            }
            
            // 更新UI显示
            this.updateUI();
            
            // 如果需要，刷新页面以重置所有状态
            if (reload) {
                console.log('[disconnect] 即将刷新页面...');
                setTimeout(function() {
                    window.location.reload();
                }, 500);
            } else {
                console.log('[disconnect] 不刷新页面');
            }
        } catch (error) {
            console.error('[disconnect] 断开钱包连接时出错:', error);
        }
    },
    
    /**
     * 切换钱包
     * @returns {Promise<boolean>} 切换是否成功
     */
    async switchWallet() {
        try {
            // 先断开当前连接
            await this.disconnect(true);
            
            // 然后打开钱包选择对话框
            return await this.connect();
        } catch (error) {
            console.error('切换钱包失败:', error);
            showError(window._('Failed to switch wallet'));
            return false;
        }
    },
    
    /**
     * 更新UI显示
     * 根据当前钱包状态更新界面元素
     * @returns {Promise<void>}
     */
    async updateUI() {
        const walletBtnText = document.getElementById('walletBtnText');
        const walletAddressDisplay = document.getElementById('walletAddressDisplay');
        const walletBalanceDisplay = document.getElementById('walletBalanceDisplay');
        const userAssetsSection = document.getElementById('userAssetsSection');
        const walletAssetsList = document.getElementById('walletAssetsList');
        const adminEntry = document.getElementById('adminEntry');
        
        console.log('更新钱包状态显示');
        console.log(`连接状态: ${this.connected} 地址: ${this.address}`);
        
        if (this.connected && this.address) {
            // 已连接状态
            // 简化显示地址
            const shortAddress = this.address.slice(0, 6) + '...' + this.address.slice(-4);
            
            // 更新连接按钮文本
            if (walletBtnText) {
                walletBtnText.textContent = shortAddress;
            }
            
            // 更新地址显示
            if (walletAddressDisplay) {
                walletAddressDisplay.textContent = shortAddress;
            }
            
            // 更新余额显示
            if (walletBalanceDisplay) {
                walletBalanceDisplay.innerHTML = `<i class="fas fa-coins me-2"></i>${window._('USDC Balance')}: ${this.balance?.toFixed(2) || '未知'}`;
            }
            
            // 显示资产列表
            if (userAssetsSection) {
                // 总是显示资产列表区域，即使没有资产也显示（内部会提示"暂无资产"）
                userAssetsSection.style.display = 'block';
                console.log('[updateDisplay] 显示资产列表区域');
                
                if (walletAssetsList) {
                    // 清空资产列表
                    walletAssetsList.innerHTML = '';
                    
                    if (this.assets && this.assets.length > 0) {
                        // 添加资产列表项
                        this.assets.forEach(asset => {
                            const assetItem = document.createElement('div');
                            assetItem.className = 'wallet-asset-item';
                            assetItem.innerHTML = `
                                <a href="/assets/${asset.asset_id}" class="asset-link d-flex justify-content-between align-items-center p-2">
                                    <div class="d-flex align-items-center">
                                        <span class="asset-name">${asset.name}</span>
                                        <span class="asset-quantity ms-2">${asset.quantity} ${asset.symbol}</span>
                                    </div>
                                    <i class="fas fa-chevron-right text-muted"></i>
                                </a>
                            `;
                            
                            walletAssetsList.appendChild(assetItem);
                        });
                    } else {
                        // 没有资产
                        walletAssetsList.innerHTML = `
                            <div class="text-center py-3">
                                <span class="text-muted">${window._('No assets found')}</span>
                            </div>
                        `;
                    }
                }
            }
            
            // 显示管理员入口
            if (adminEntry && this.isAdmin) {
                adminEntry.style.display = 'block';
            } else if (adminEntry) {
                adminEntry.style.display = 'none';
            }
        } else {
            // 未连接状态
            if (walletBtnText) {
                walletBtnText.textContent = window._('Connect Wallet');
            }
            
            if (walletAddressDisplay) {
                walletAddressDisplay.textContent = window._('Not Connected');
            }
            
            if (walletBalanceDisplay) {
                walletBalanceDisplay.innerHTML = `<i class="fas fa-coins me-2"></i>${window._('USDC Balance')}: 0.00`;
            }
            
            if (userAssetsSection) {
                userAssetsSection.style.display = 'none';
            }
            
            if (adminEntry) {
                adminEntry.style.display = 'none';
            }
        }
    },
    
    /**
     * 获取连接状态
     * @returns {boolean} 是否已连接钱包
     */
    getConnectionStatus() {
        return this.connected;
    },
    
    /**
     * 获取当前连接的钱包地址
     * @returns {string|null} 钱包地址或null
     */
    getAddress() {
        return this.address;
    },
    
    /**
     * 获取当前钱包类型
     * @returns {string|null} 钱包类型或null
     */
    getWalletType() {
        return this.walletType;
    },
    
    /**
     * 检查当前连接的钱包是否为管理员
     * @returns {Promise<boolean>} 是否为管理员
     */
    async checkIsAdmin() {
        if (!this.connected || !this.address) {
            this.isAdmin = false;
                return false;
        }
        
        try {
            console.log('检查钱包是否为管理员...');
            
            // 启用API调用，获取真实管理员状态
            try {
                const walletType = this.walletType || 'ethereum';
                const url = `/api/user/check_admin?address=${this.address}&wallet_type=${walletType}&_=${new Date().getTime()}`;
                console.log(`调用管理员检查API: ${url}`);
                
                const response = await fetch(url);
                
                if (response.ok) {
                    const data = await response.json();
                    console.log('管理员检查API返回数据:', data);
                    
                    if (data.success !== undefined) {
                        this.isAdmin = Boolean(data.is_admin || data.admin || data.success);
                        console.log(`从API获取到管理员状态: ${this.isAdmin ? '是管理员' : '不是管理员'}`);
                        return this.isAdmin;
                    } else {
                        console.warn('管理员检查API返回未知格式');
                    }
                } else {
                    console.warn('管理员检查API响应不成功:', response.status, response.statusText);
            }
        } catch (error) {
                console.warn('获取管理员状态API失败:', error);
            }
            
            // 如果API获取失败，使用备用逻辑
            console.log('API管理员检查失败，使用备用逻辑');
            
            // 假设特定地址是管理员
            const adminAddresses = {
                'ethereum': ['0x6394993426DBA3b654eF0052698Fe9E0B6A98870'],
                'phantom': ['EeYfRd8nRFiEjXdUn2XxE8Pt6YyQrX8x6jAsqL7srkPD']
            };
            
            const addressList = adminAddresses[this.walletType] || [];
            this.isAdmin = addressList.includes(this.address);
            
            console.log(`钱包管理员状态(备用判断): ${this.isAdmin ? '是管理员' : '不是管理员'}`);
            return this.isAdmin;
        } catch (error) {
            console.error('检查管理员状态失败:', error);
            this.isAdmin = false;
            return false;
        }
    },
    
    /**
     * 注册状态变更回调函数
     * @param {Function} callback 回调函数
     */
    onStateChange(callback) {
        if (typeof callback === 'function' && !this.stateChangeCallbacks.includes(callback)) {
            this.stateChangeCallbacks.push(callback);
        }
    },
    
    /**
     * 移除状态变更回调函数
     * @param {Function} callback 回调函数
     */
    offStateChange(callback) {
        const index = this.stateChangeCallbacks.indexOf(callback);
        if (index !== -1) {
            this.stateChangeCallbacks.splice(index, 1);
        }
    },
    
    /**
     * 通知状态变更
     * @param {Object} details 状态变更详情
     */
    notifyStateChange: function(details = {}) {
        try {
            console.log('[notifyStateChange] 触发钱包状态变更事件');
            
            // 创建事件对象
            const event = new CustomEvent('walletStateChanged', {
                detail: {
                    connected: this.connected,
                    address: this.address,
                    walletType: this.walletType,
                    balance: this.balance,
                    assets: this.assets,
                    isAdmin: this.isAdmin,
                    chainId: this.chainId,
                    ...details
                }
            });
            
            // 分发事件
            document.dispatchEvent(event);
            
            // 分发具体的事件类型
            if (details.type === 'connect') {
                console.log('[notifyStateChange] 触发钱包连接事件');
                document.dispatchEvent(new CustomEvent('walletConnected', {
                    detail: {
                        address: this.address,
                        walletType: this.walletType,
                        balance: this.balance
                    }
                }));
                
                // 强制更新UI显示
                this.updateDisplay();
                
                // 全局调用余额更新
                if (typeof window.updateWalletBalance === 'function') {
                    console.log('[notifyStateChange] 调用全局updateWalletBalance函数');
                    window.updateWalletBalance();
                }
            } else if (details.type === 'disconnect') {
                console.log('[notifyStateChange] 触发钱包断开事件');
                document.dispatchEvent(new CustomEvent('walletDisconnected'));
                
                // 强制更新UI显示
                this.updateDisplay();
            }
            
            // 触发余额更新事件
            console.log('[notifyStateChange] 触发钱包余额更新事件');
            this.triggerBalanceUpdatedEvent();
        } catch (error) {
            console.error('[notifyStateChange] 触发钱包状态变更事件失败:', error);
        }
    },
    
    /**
     * 更新钱包余额
     * 从区块链获取最新的钱包余额
     * @returns {Promise<number|null>} 更新后的余额，失败时返回null
     */
    async updateWalletBalance() {
        if (!this.connected || !this.address) {
            console.log('[updateWalletBalance] 钱包未连接，设置余额为0');
            this.balance = 0;
            this.nativeBalance = 0;
            return 0;
            }
            
            try {
            console.log('[updateWalletBalance] 开始获取钱包余额...');
            
            // 从API获取真实数据
            try {
                const walletType = this.walletType || 'ethereum';
                const url = `/api/wallet/balance?address=${this.address}&wallet_type=${walletType}&_=${new Date().getTime()}`;
                console.log(`[updateWalletBalance] 调用钱包余额API: ${url}`);
                
                const response = await fetch(url);
                console.log(`[updateWalletBalance] API响应状态: ${response.status}`);
                
                if (response.ok) {
                    const data = await response.json();
                    console.log('[updateWalletBalance] 余额API返回数据:', JSON.stringify(data));
                    
                    if (data.success) {
                        // 使用API返回的真实余额，即使是0
                        const oldBalance = this.balance;
                        this.balance = parseFloat(data.balance) || 0;
                        
                        // 处理API返回的多种余额
                        if (data.balances) {
                            // 根据钱包类型设置原生代币余额
                            if (this.walletType === 'phantom') {
                                this.nativeBalance = parseFloat(data.balances.SOL) || 0;
                                console.log(`[updateWalletBalance] SOL余额: ${this.nativeBalance}`);
                            } else if (this.walletType === 'ethereum') {
                                this.nativeBalance = parseFloat(data.balances.ETH) || 0;
                                console.log(`[updateWalletBalance] ETH余额: ${this.nativeBalance}`);
                            }
                        }
                        
                        console.log(`[updateWalletBalance] 从API获取到钱包余额: ${this.balance} USDC (旧余额: ${oldBalance}), 原生代币余额: ${this.nativeBalance}`);
                        
                        // 记录余额是否变化
                        if (oldBalance !== this.balance) {
                            console.log(`[updateWalletBalance] 余额已变化: ${oldBalance} -> ${this.balance}`);
                        } else {
                            console.log(`[updateWalletBalance] 余额未变化: ${this.balance}`);
                        }
                        
                        // 立即触发余额更新事件
                        this.triggerBalanceUpdatedEvent();
                        
                        return this.balance;
                    } else {
                        console.warn('[updateWalletBalance] 余额API返回失败状态:', data.message || '未知错误');
                        // 标记余额为未知状态
                        this.balance = null;
                        this.nativeBalance = null;
                        
                        // 立即触发余额更新事件
                        this.triggerBalanceUpdatedEvent();
                        
            return null;
        }
                } else {
                    console.warn('[updateWalletBalance] 余额API响应不成功:', response.status, response.statusText);
                    // 标记余额为未知状态
                    this.balance = null;
                    this.nativeBalance = null;
                    
                    // 立即触发余额更新事件
                    this.triggerBalanceUpdatedEvent();
                    
            return null;
        }
            } catch (error) {
                console.warn('[updateWalletBalance] 获取真实余额API失败:', error);
                // 标记余额为未知状态
                this.balance = null;
                this.nativeBalance = null;
                
                // 立即触发余额更新事件
                this.triggerBalanceUpdatedEvent();
                
                return null;
            }
        } catch (error) {
            console.error('[updateWalletBalance] 获取钱包余额失败:', error);
            // 标记余额为未知状态
            this.balance = null;
            this.nativeBalance = null;
            
            // 立即触发余额更新事件
            this.triggerBalanceUpdatedEvent();
            
            return null;
        }
    },
    
    /**
     * 触发余额更新事件
     * 将余额变更通知到UI
     */
    triggerBalanceUpdatedEvent() {
        try {
            console.log(`[triggerBalanceUpdatedEvent] 触发余额更新事件: USDC=${this.balance}, SOL=${this.nativeBalance}`);
            
            // 创建并分发自定义事件
            const event = new CustomEvent('walletBalanceUpdated', {
                detail: {
                    balance: this.balance,
                    nativeBalance: this.nativeBalance,
                    currency: 'USDC',
                    nativeCurrency: 'SOL',  // 始终使用SOL作为原生代币
                    timestamp: new Date().getTime()
                }
            });
            
            // 在document上分发事件
            document.dispatchEvent(event);
            console.log('[triggerBalanceUpdatedEvent] 余额更新事件已触发');
            
            // 尝试直接更新UI
            this.updateBalanceDisplay();
        } catch (error) {
            console.error('[triggerBalanceUpdatedEvent] 触发余额更新事件失败:', error);
        }
    },
    
    /**
     * 直接更新余额显示
     */
    updateBalanceDisplay() {
        try {
            const balanceElement = document.getElementById('walletBalanceDisplay');
            if (balanceElement) {
                console.log(`[updateBalanceDisplay] 直接更新余额显示元素: ${this.balance}`);
                
                if (this.balance === null || this.balance === undefined) {
                    balanceElement.textContent = '--';
                } else {
                    balanceElement.textContent = parseFloat(this.balance).toFixed(2);
                }
                
                console.log(`[updateBalanceDisplay] 余额显示已更新: ${balanceElement.textContent}`);
            } else {
                console.warn('[updateBalanceDisplay] 未找到余额显示元素');
                }
        } catch (error) {
            console.error('[updateBalanceDisplay] 更新余额显示失败:', error);
        }
    },
    
    // 保留其他重要方法如connectMetaMask, connectPhantom, getWalletBalance, getUserAssets等
    // 这些方法将在后续实现...

    /**
     * 更新资产列表UI
     * 完全使用DOM API创建元素，彻底解决箭头问题
     */
    updateAssetsUI() {
        try {
            console.log('[updateAssetsUI] 更新资产列表UI');
            
            // 获取资产列表容器
            const assetsList = document.getElementById('walletAssetsList');
            if (!assetsList) {
                console.warn('[updateAssetsUI] 资产列表容器不存在');
                return;
            }
            
            // 清空现有内容
            assetsList.innerHTML = '';
            
            // 使用当前资产列表
            const assets = this.assets;
            
            // 检查是否有资产
            if (!assets || !Array.isArray(assets) || assets.length === 0) {
                console.log('[updateAssetsUI] 没有资产可显示');
                const emptyItem = document.createElement('li');
                emptyItem.className = 'text-muted text-center py-1';
                emptyItem.style.fontSize = '11px';
                emptyItem.textContent = 'No assets found';
                assetsList.appendChild(emptyItem);
                return;
            }
            
            console.log(`[updateAssetsUI] 显示 ${assets.length} 个资产`);
            
            // 创建文档片段来优化DOM操作
            const fragment = document.createDocumentFragment();
            
            // 遍历资产并创建列表项
            assets.forEach(asset => {
                // 提取资产数据
                const assetId = asset.id || asset.asset_id || 0;
                const assetName = asset.name || 'Unknown Asset';
                const quantity = asset.quantity || asset.amount || 0;
                const symbol = asset.symbol || `RH-${assetId}`;
                
                // 创建列表项元素
                const listItem = document.createElement('li');
                listItem.className = 'wallet-asset-item';
                listItem.style.marginBottom = '1px';
                
                // 创建链接元素
                const link = document.createElement('a');
                link.href = `/assets/${assetId}`;
                Object.assign(link.style, {
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '3px 4px',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '4px',
                    color: '#333',
                    textDecoration: 'none',
                    height: '24px',
                    border: 'none',
                    boxShadow: 'none'
                });
                
                // 添加鼠标悬停效果
                link.onmouseover = function() {
                    this.style.backgroundColor = '#e9ecef';
                    this.style.color = '#0d6efd';
                };
                
                link.onmouseout = function() {
                    this.style.backgroundColor = '#f8f9fa';
                    this.style.color = '#333';
                };
                
                // 创建资产名称元素
                const nameSpan = document.createElement('span');
                nameSpan.textContent = assetName;
                Object.assign(nameSpan.style, {
                    fontSize: '11px',
                    fontWeight: '500',
                    maxWidth: '110px',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                });
                
                // 创建资产信息容器
                const infoDiv = document.createElement('div');
                Object.assign(infoDiv.style, {
                    display: 'flex',
                    alignItems: 'center',
                    minWidth: '60px',
                    justifyContent: 'flex-end'
                });
                
                // 创建数量元素
                const quantitySpan = document.createElement('span');
                quantitySpan.textContent = quantity;
                Object.assign(quantitySpan.style, {
                    fontSize: '11px',
                    color: '#333',
                    backgroundColor: '#eeeeee',
                    padding: '1px 3px',
                    borderRadius: '2px',
                    textAlign: 'center'
                });
                
                // 创建符号元素
                const symbolSpan = document.createElement('span');
                symbolSpan.textContent = symbol;
                Object.assign(symbolSpan.style, {
                    fontSize: '10px',
                    color: '#666',
                    marginLeft: '2px',
                    minWidth: '30px',
                    textAlign: 'right'
                });
                
                // 组装DOM结构
                infoDiv.appendChild(quantitySpan);
                infoDiv.appendChild(symbolSpan);
                link.appendChild(nameSpan);
                link.appendChild(infoDiv);
                listItem.appendChild(link);
                fragment.appendChild(listItem);
            });
            
            // 一次性添加所有元素到DOM
            assetsList.appendChild(fragment);
            
            // 显示包含资产列表的区域
            const userAssetsSection = document.getElementById('userAssetsSection');
            if (userAssetsSection) {
                userAssetsSection.style.display = 'block';
                console.log('[updateAssetsUI] 显示资产列表区域');
            }
            
            console.log('[updateAssetsUI] 资产列表更新完成');
        } catch (error) {
            console.error('[updateAssetsUI] 更新资产列表失败:', error);
        }
    },

    /**
     * 打开钱包选择器
     * 允许用户切换连接不同的钱包
     */
    openWalletSelector() {
        try {
            console.log('[openWalletSelector] 打开钱包选择器');
            
            // 如果已经连接了钱包，先断开连接
            if (this.connected) {
                console.log('[openWalletSelector] 已连接钱包，先断开现有连接');
                // 只断开连接但不刷新页面
                this.disconnect(false); 
            }
            
            // 移除任何已有的钱包选择器
            const existingSelector = document.getElementById('walletSelector');
            if (existingSelector) {
                existingSelector.remove();
            }
            
            // 创建钱包选择器
            const walletSelector = document.createElement('div');
            walletSelector.id = 'walletSelector';
            walletSelector.className = 'wallet-selector-modal';
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
            title.textContent = '选择钱包';
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
            closeButton.onclick = function() {
                walletSelector.remove();
            };
            
            title.appendChild(closeButton);
            walletSelectorContent.appendChild(title);
            
            // 添加钱包选项 - 使用wallet-grid样式
            const walletGrid = document.createElement('div');
            walletGrid.className = 'wallet-grid';
            walletGrid.style.display = 'grid';
            walletGrid.style.gridTemplateColumns = 'repeat(3, 1fr)';
            walletGrid.style.gap = '15px';
            
            // 定义钱包列表
            const wallets = [
                {
                    name: 'Phantom',
                    icon: '/static/images/wallets/phantom.png',
                    class: 'phantom',
                    onClick: () => this.connectPhantom()
                },
                {
                    name: 'MetaMask',
                    icon: '/static/images/wallets/metamask.png',
                    class: 'ethereum',
                    onClick: () => this.connectEthereum()
                },
                {
                    name: 'Solflare',
                    icon: '/static/images/wallets/solflare.png',
                    class: 'solana',
                    onClick: () => this.connectSolflare()
                },
                {
                    name: 'Coinbase',
                    icon: '/static/images/wallets/coinbase.png',
                    class: 'ethereum',
                    onClick: () => this.connectCoinbase()
                },
                {
                    name: 'Slope',
                    icon: '/static/images/wallets/slope.png',
                    class: 'solana',
                    onClick: () => this.connectSlope()
                },
                {
                    name: 'Glow',
                    icon: '/static/images/wallets/glow.png',
                    class: 'solana',
                    onClick: () => this.connectGlow()
                }
            ];
            
            // 创建钱包选项
            wallets.forEach(wallet => {
                const option = document.createElement('div');
                option.className = 'wallet-option';
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
                    walletSelector.remove();
                    wallet.onClick();
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
            walletSelector.addEventListener('click', function(e) {
                if (e.target === walletSelector) {
                    walletSelector.remove();
                }
            });
            
            console.log('[openWalletSelector] 钱包选择器已显示');
        } catch (error) {
            console.error('[openWalletSelector] 打开钱包选择器失败:', error);
        }
    },

    /**
     * 更新钱包显示状态
     * 直接操作DOM元素，强制更新UI
     */
    updateDisplay() {
        try {
            console.log('[updateDisplay] 强制更新钱包显示');
            
            // 获取关键元素
        const walletBtnText = document.getElementById('walletBtnText');
            const walletAddressDisplay = document.getElementById('walletAddressDisplay');
            const userAssetsSection = document.getElementById('userAssetsSection');
            const adminEntry = document.getElementById('adminEntry');
            
            // 更新显示
            if (this.connected && this.address) {
                // 已连接状态
                // 简化显示地址
                const shortAddress = this.address.slice(0, 6) + '...' + this.address.slice(-4);
                
                console.log(`[updateDisplay] 已连接状态，显示地址: ${shortAddress}，钱包类型: ${this.walletType}`);
                
                // 更新连接按钮文本
                if (walletBtnText) {
                    walletBtnText.textContent = shortAddress;
                    console.log('[updateDisplay] 已更新按钮文本');
                }
                
                // 更新地址显示
                if (walletAddressDisplay) {
                    walletAddressDisplay.textContent = shortAddress;
                    console.log('[updateDisplay] 已更新地址显示');
                }
                
                // 更新原生代币标签
                const nativeCurrencyLabel = document.querySelector('.native-balance span:first-child');
                if (nativeCurrencyLabel) {
                    // 根据钱包类型设置正确的原生代币名称
                    if (this.walletType === 'phantom') {
                        nativeCurrencyLabel.textContent = 'SOL:';
                    } else if (this.walletType === 'ethereum') {
                        nativeCurrencyLabel.textContent = 'ETH:';
                    }
                    console.log(`[updateDisplay] 已更新原生代币标签为: ${nativeCurrencyLabel.textContent}`);
                }
                
                // 显示/隐藏资产列表
                if (userAssetsSection) {
                    // 总是显示资产列表区域，即使没有资产也显示（内部会提示"暂无资产"）
                    userAssetsSection.style.display = 'block';
                    console.log('[updateDisplay] 显示资产列表区域');
                }
                
                // 显示/隐藏管理员入口
                if (adminEntry) {
                    adminEntry.style.display = this.isAdmin ? 'block' : 'none';
                    console.log('[updateDisplay] 已更新管理员入口显示状态');
                }
                
                // 更新资产列表
                this.updateAssetsUI();
                
                // 更新余额显示
                const balanceElement = document.getElementById('walletBalanceDisplay');
                const nativeBalanceElement = document.getElementById('nativeBalanceDisplay');
                
                if (balanceElement && this.balance !== undefined) {
                    balanceElement.textContent = parseFloat(this.balance).toFixed(2);
                    console.log(`[updateDisplay] 已更新USDC余额: ${this.balance}`);
                }
                
                if (nativeBalanceElement && this.nativeBalance !== undefined) {
                    nativeBalanceElement.textContent = parseFloat(this.nativeBalance).toFixed(4);
                    console.log(`[updateDisplay] 已更新${this.walletType === 'phantom' ? 'SOL' : 'ETH'}余额: ${this.nativeBalance}`);
                }
                } else {
                // 未连接状态
                console.log('[updateDisplay] 未连接状态，显示默认UI');
                
                if (walletBtnText) {
                    walletBtnText.textContent = window._('Connect Wallet') || '连接钱包';
                    console.log('[updateDisplay] 已更新按钮文本为默认状态');
                }
                
                if (walletAddressDisplay) {
                    walletAddressDisplay.textContent = window._('Not Connected') || '未连接';
                    console.log('[updateDisplay] 已更新地址显示为默认状态');
                }
                
                if (userAssetsSection) {
                    userAssetsSection.style.display = 'none';
                    console.log('[updateDisplay] 已隐藏资产列表');
                }
                
                if (adminEntry) {
                    adminEntry.style.display = 'none';
                    console.log('[updateDisplay] 已隐藏管理员入口');
                }
                
                // 重置余额显示
                const balanceElement = document.getElementById('walletBalanceDisplay');
                const nativeBalanceElement = document.getElementById('nativeBalanceDisplay');
                
                if (balanceElement) {
                    balanceElement.textContent = '0.00';
                    console.log('[updateDisplay] 已重置USDC余额显示');
                }
                
                if (nativeBalanceElement) {
                    nativeBalanceElement.textContent = '0.0000';
                    console.log('[updateDisplay] 已重置原生代币余额显示');
                }
            }
            
            console.log('[updateDisplay] 钱包显示更新完成');
            } catch (error) {
            console.error('[updateDisplay] 更新钱包显示失败:', error);
        }
    },

    /**
     * 设置以太坊钱包的事件监听器
     * 这是作为单独函数实现，避免重复代码
     */
    setupEthereumListeners() {
        if (!window.ethereum) {
            console.warn('无法设置以太坊事件监听器：window.ethereum不存在');
            return;
        }

        try {
            console.log('设置以太坊钱包事件监听器');
            
            // 移除现有监听器
            if (typeof window.ethereum.removeAllListeners === 'function') {
                try {
                    window.ethereum.removeAllListeners('accountsChanged');
                    window.ethereum.removeAllListeners('chainChanged');
                    window.ethereum.removeAllListeners('disconnect');
                    console.log('已移除旧的以太坊事件监听器');
                } catch(e) {
                    console.warn('移除以太坊事件监听器失败:', e);
                }
            }
            
            // 账号变更事件
            window.ethereum.on('accountsChanged', (accounts) => {
                console.log('MetaMask账户已更改:', accounts);
                if (accounts.length === 0) {
                    console.log('MetaMask已断开连接');
                    this.disconnect(false);
                } else {
                    // 切换到新账户
                    const newAddress = accounts[0]; 
                    console.log('MetaMask已切换到新账户:', newAddress);
                    this.address = newAddress;
                    
                    // 保存新地址到本地存储
                    try {
                        localStorage.setItem('walletType', 'ethereum');
                        localStorage.setItem('walletAddress', newAddress);
                        console.log('账户变更: 已保存新地址到本地存储', newAddress);
                    } catch (error) {
                        console.warn('账户变更: 保存地址到本地存储失败:', error);
                    }
                    
                    this.getWalletBalance().then(() => {
                        this.updateUI();
                        this.notifyStateChange({
                            type: 'connect',
                            address: this.address,
                            walletType: this.walletType,
                            balance: this.balance,
                            nativeBalance: this.nativeBalance
                        });
                    });
                }
            });
            
            // 链ID变更事件
            window.ethereum.on('chainChanged', (chainId) => {
                console.log('MetaMask链ID已更改:', chainId);
                // 记录新的链ID
                this.chainId = chainId;
                // 刷新页面以确保UI与新链相匹配
                window.location.reload();
            });
            
            // 断开连接事件
            window.ethereum.on('disconnect', (error) => {
                console.log('MetaMask断开连接:', error);
                this.disconnect(false);
            });
            
            console.log('以太坊钱包事件监听器设置完成');
        } catch (listenerError) {
            console.warn('设置以太坊事件监听器失败:', listenerError);
        }
    },

    /**
     * 为Phantom钱包设置事件监听器
     */
    setupPhantomListeners() {
        if (!window.solana || !window.solana.isPhantom) return;
        
        try {
            // 移除现有监听器，避免重复
            if (typeof window.solana.removeAllListeners === 'function') {
                window.solana.removeAllListeners('disconnect');
                window.solana.removeAllListeners('accountChanged');
            }
            
            // 断开连接事件
            window.solana.on('disconnect', async () => {
                console.log('Phantom钱包断开连接');
                await this.disconnect(true);
            });
            
            // 账户变更事件
            window.solana.on('accountChanged', async (publicKey) => {
                if (publicKey) {
                    console.log('Phantom账户已变更:', publicKey.toString());
                    this.address = publicKey.toString();
                    localStorage.setItem('walletAddress', this.address);
                    
                    // 更新余额和资产
                    await this.getWalletBalance();
                    await this.getUserAssets(this.address);
                    
                    // 检查是否为管理员
                    await this.checkIsAdmin();
                    
                    // 更新UI
                    await this.updateUI();
                    
                    // 触发状态变更事件
                    this.notifyStateChange();
                } else {
                    console.log('Phantom账户已断开');
                    await this.disconnect(true);
                }
            });
        } catch (error) {
            console.warn('设置Phantom事件监听器失败:', error);
        }
    },

    /**
     * 获取钱包余额
     * @returns {Promise<number>} 钱包余额（USDC）
     */
    async getWalletBalance() {
        if (!this.connected || !this.address) {
            console.log('钱包未连接，无法获取余额');
            this.balance = 0;
            this.nativeBalance = 0;
            return 0;
        }
        
        try {
            console.log(`[getWalletBalance] 尝试获取 ${this.walletType} 钱包 ${this.address} 的余额`);
            
            // 直接调用新的updateWalletBalance方法获取真实数据
            console.log('[getWalletBalance] 调用updateWalletBalance方法获取真实数据');
            const balance = await this.updateWalletBalance();
            console.log(`[getWalletBalance] 从updateWalletBalance获取到余额: ${balance}`);
            
            // 余额已经在updateWalletBalance中设置了this.balance
            return balance;
        } catch (error) {
            console.error('[getWalletBalance] 获取钱包余额失败:', error);
            this.balance = 0;
            this.nativeBalance = 0;
            return 0;
        }
    },

    /**
     * 获取用户资产
     * @param {string} address 钱包地址
     * @returns {Promise<Array>} 用户资产列表
     */
    async getUserAssets(address) {
        if (!address) {
            this.assets = [];
            return [];
        }
        
        try {
            // 获取当前钱包类型
            const walletType = this.walletType || 'ethereum';
            console.log(`[getUserAssets] 获取 ${walletType} 钱包 ${address} 的资产`);
            
            // 通过API获取真实数据
            try {
                // 构建API请求URL，添加时间戳防止缓存
                const timestamp = new Date().getTime();
                const url = `/api/user/assets?address=${address}&wallet_type=${walletType}&_=${timestamp}`;
                console.log(`[getUserAssets] 调用API: ${url}`);
                
                const response = await fetch(url);
                
                if (response.ok) {
                    // 处理API返回数据
                    const data = await response.json();
                    console.log('[getUserAssets] API返回的资产数据:', data);
                    
                    let assets = Array.isArray(data) ? data : 
                                (data.assets || data.data || []);
                    
                    // 标准化资产格式
                    const formattedAssets = assets.map(asset => ({
                        asset_id: asset.asset_id || asset.id || 0,
                        name: asset.name || asset.asset_name || asset.title || 'Unknown Asset',
                        quantity: asset.holding_amount || asset.balance || asset.tokens || asset.amount || 0,
                        symbol: asset.symbol || asset.token_symbol || `RH-${asset.asset_id || asset.id || '???'}`
                    }));
                    
                    console.log(`[getUserAssets] 处理后的资产数据 (${formattedAssets.length} 个资产):`, formattedAssets);
                    this.assets = formattedAssets;
                    return formattedAssets;
                } else {
                    console.warn('[getUserAssets] API响应不成功:', response.status, response.statusText);
                    // API请求失败，返回空数组
                    this.assets = [];
                    return [];
                }
            } catch (error) {
                console.warn('[getUserAssets] API请求失败:', error);
                // API请求失败，返回空数组
                this.assets = [];
                return [];
            }
        } catch (error) {
            console.error('[getUserAssets] 获取用户资产失败:', error);
            // 错误情况下返回空数组
            this.assets = [];
            return [];
        }
    },

    /**
     * 连接到Solflare钱包
     * @returns {Promise<boolean>} 连接是否成功
     */
    connectSolflare: async function() {
        try {
            console.log('尝试连接Solflare钱包...');
            
            // 检查Solflare是否存在
            if (!window.solflare) {
                console.error('未检测到Solflare钱包');
                showError('未检测到Solflare，请安装Solflare钱包扩展');
                return false;
            }
            
            try {
                await window.solflare.connect();
            } catch (error) {
                console.error('连接到Solflare失败:', error);
                showError('连接Solflare失败: ' + (error.message || '请检查是否已登录Solflare'));
                return false;
            }
            
            if (window.solflare.publicKey) {
                const address = window.solflare.publicKey.toString();
                console.log('Solflare钱包连接成功:', address);
                
                // 更新钱包状态
                this.address = address;
                this.walletType = 'solana';
                this.connected = true;
                this.provider = window.solflare;
                
                // 保存状态到本地存储
                localStorage.setItem('walletType', 'solana');
                localStorage.setItem('walletAddress', address);
                localStorage.setItem('lastWalletType', 'solana');
                localStorage.setItem('lastWalletAddress', address);
                
                // 获取余额和资产
                try {
                    await this.getWalletBalance();
                    await this.getUserAssets(this.address);
                    await this.checkIsAdmin();
                    await this.updateUI();
                    this.updateDisplay();
                    
                    this.notifyStateChange({
                        type: 'connect',
                        address: this.address,
                        walletType: this.walletType,
                        balance: this.balance,
                        nativeBalance: this.nativeBalance
                    });
                    
                    const truncatedAddress = this.address.slice(0, 6) + '...' + this.address.slice(-4);
                    showSuccess(`钱包已连接: ${truncatedAddress}`);
                } catch (e) {
                    console.warn('处理Solflare连接后续操作失败:', e);
                }
                
                return true;
            } else {
                console.error('未能获取Solflare钱包地址');
                showError('未能获取Solflare钱包地址，请确保已授权访问');
                return false;
            }
        } catch (error) {
            console.error('连接Solflare钱包过程中发生错误:', error);
            showError('连接Solflare失败: ' + (error.message || '未知错误'));
            return false;
        }
    },

    /**
     * 连接到Coinbase钱包
     * @returns {Promise<boolean>} 连接是否成功
     */
    connectCoinbase: async function() {
        try {
            console.log('尝试连接Coinbase钱包...');
            
            // 检查Coinbase钱包是否存在
            if (!window.ethereum || !window.ethereum.isCoinbaseWallet) {
                console.error('未检测到Coinbase钱包');
                showError('未检测到Coinbase钱包，请安装Coinbase Wallet扩展');
                return false;
            }
            
            let accounts;
            try {
                accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            } catch (error) {
                console.error('连接到Coinbase钱包失败:', error);
                showError('连接Coinbase钱包失败: ' + (error.message || '请检查是否已登录'));
                return false;
            }
            
            if (accounts && accounts.length > 0) {
                const address = accounts[0];
                console.log('Coinbase钱包连接成功:', address);
                
                // 更新钱包状态
                this.address = address;
                this.walletType = 'ethereum';
                this.connected = true;
                this.provider = window.ethereum;
                
                // 保存状态到本地存储
                localStorage.setItem('walletType', 'ethereum');
                localStorage.setItem('walletAddress', address);
                localStorage.setItem('lastWalletType', 'ethereum');
                localStorage.setItem('lastWalletAddress', address);
                
                // 获取余额和资产
                try {
                    await this.getWalletBalance();
                    await this.getUserAssets(this.address);
                    await this.checkIsAdmin();
                    await this.updateUI();
                    this.updateDisplay();
                    
                    this.notifyStateChange({
                        type: 'connect',
                        address: this.address,
                        walletType: this.walletType,
                        balance: this.balance,
                        nativeBalance: this.nativeBalance
                    });
                    
                    const truncatedAddress = this.address.slice(0, 6) + '...' + this.address.slice(-4);
                    showSuccess(`钱包已连接: ${truncatedAddress}`);
                } catch (e) {
                    console.warn('处理Coinbase连接后续操作失败:', e);
                }
                
                return true;
            } else {
                console.error('未能获取Coinbase钱包地址');
                showError('未能获取Coinbase钱包地址，请确保已授权访问');
                return false;
            }
        } catch (error) {
            console.error('连接Coinbase钱包过程中发生错误:', error);
            showError('连接Coinbase钱包失败: ' + (error.message || '未知错误'));
            return false;
        }
    },

    /**
     * 连接到Slope钱包
     * @returns {Promise<boolean>} 连接是否成功
     */
    connectSlope: async function() {
        try {
            console.log('尝试连接Slope钱包...');
            
            // 检查Slope钱包是否存在
            if (!window.Slope) {
                console.error('未检测到Slope钱包');
                showError('未检测到Slope钱包，请安装Slope钱包扩展');
                return false;
            }
            
            try {
                const slope = new window.Slope();
                const { data, error } = await slope.connect();
                
                if (error) {
                    throw error;
                }
                
                const address = data.publicKey;
                console.log('Slope钱包连接成功:', address);
                
                // 更新钱包状态
                this.address = address;
                this.walletType = 'solana';
                this.connected = true;
                this.provider = slope;
                
                // 保存状态到本地存储
                localStorage.setItem('walletType', 'solana');
                localStorage.setItem('walletAddress', address);
                localStorage.setItem('lastWalletType', 'solana');
                localStorage.setItem('lastWalletAddress', address);
                
                // 获取余额和资产
                try {
                    await this.getWalletBalance();
                    await this.getUserAssets(this.address);
                    await this.checkIsAdmin();
                    await this.updateUI();
                    this.updateDisplay();
                    
                    this.notifyStateChange({
                        type: 'connect',
                        address: this.address,
                        walletType: this.walletType,
                        balance: this.balance,
                        nativeBalance: this.nativeBalance
                    });
                    
                    const truncatedAddress = this.address.slice(0, 6) + '...' + this.address.slice(-4);
                    showSuccess(`钱包已连接: ${truncatedAddress}`);
                } catch (e) {
                    console.warn('处理Slope连接后续操作失败:', e);
                }
                
                return true;
            } catch (error) {
                console.error('连接到Slope钱包失败:', error);
                showError('连接Slope钱包失败: ' + (error.message || '请检查是否已登录'));
                return false;
            }
        } catch (error) {
            console.error('连接Slope钱包过程中发生错误:', error);
            showError('连接Slope钱包失败: ' + (error.message || '未知错误'));
            return false;
        }
    },

    /**
     * 连接到Glow钱包
     * @returns {Promise<boolean>} 连接是否成功
     */
    connectGlow: async function() {
        try {
            console.log('尝试连接Glow钱包...');
            
            // 检查Glow钱包是否存在
            if (!window.glowSolana) {
                console.error('未检测到Glow钱包');
                showError('未检测到Glow钱包，请安装Glow钱包扩展');
                return false;
            }
            
            try {
                const publicKey = await window.glowSolana.connect();
                const address = publicKey.toString();
                console.log('Glow钱包连接成功:', address);
                
                // 更新钱包状态
                this.address = address;
                this.walletType = 'solana';
                this.connected = true;
                this.provider = window.glowSolana;
                
                // 保存状态到本地存储
                localStorage.setItem('walletType', 'solana');
                localStorage.setItem('walletAddress', address);
                localStorage.setItem('lastWalletType', 'solana');
                localStorage.setItem('lastWalletAddress', address);
                
                // 获取余额和资产
                try {
                    await this.getWalletBalance();
                    await this.getUserAssets(this.address);
                    await this.checkIsAdmin();
                    await this.updateUI();
                    this.updateDisplay();
                    
                    this.notifyStateChange({
                        type: 'connect',
                        address: this.address,
                        walletType: this.walletType,
                        balance: this.balance,
                        nativeBalance: this.nativeBalance
                    });
                    
                    const truncatedAddress = this.address.slice(0, 6) + '...' + this.address.slice(-4);
                    showSuccess(`钱包已连接: ${truncatedAddress}`);
                } catch (e) {
                    console.warn('处理Glow连接后续操作失败:', e);
                }
                
                return true;
            } catch (error) {
                console.error('连接到Glow钱包失败:', error);
                showError('连接Glow钱包失败: ' + (error.message || '请检查是否已登录'));
                return false;
            }
        } catch (error) {
            console.error('连接Glow钱包过程中发生错误:', error);
            showError('连接Glow钱包失败: ' + (error.message || '未知错误'));
            return false;
        }
    },
};

/**
 * 显示钱包选择对话框
 * 允许用户选择要连接的钱包类型
 * @returns {Promise<string|null>} 选中的钱包类型或null（取消选择）
 */
walletState.showWalletOptions = function() {
    return new Promise((resolve, reject) => {
        try {
            // 检查是否已存在模态框，如果存在则先移除
            const existingModal = document.getElementById('walletSelectorModal');
            if (existingModal) {
                try {
                    existingModal.remove();
                } catch (e) {
                    console.warn('移除已存在的模态框失败:', e);
                }
            }
            
            // 创建新的模态框
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'walletSelectorModal';
            modal.setAttribute('tabindex', '-1');
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-labelledby', 'walletSelectorModalLabel');
            modal.setAttribute('aria-hidden', 'true');
            
            // 检测是否是移动设备
            const isMobile = this.isMobile();
            
            // 定义支持的钱包
            const SUPPORTED_WALLETS = [
                {
                    name: 'MetaMask',
                    icon: 'fas fa-wallet text-warning',
                    provider: 'ethereum',
                    installed: !!window.ethereum?.isMetaMask,
                    mobileLink: 'https://metamask.app.link/dapp/' + window.location.href.replace(/^https?:\/\//, ''),
                    installLink: 'https://metamask.io/download/',
                    downloadText: '前往MetaMask官网下载'
                },
                {
                    name: 'Phantom',
                    icon: 'fas fa-ghost text-purple',
                    provider: 'phantom',
                    installed: !!window.solana?.isPhantom,
                    mobileLink: 'https://phantom.app/ul/browse/' + window.location.href.replace(/^https?:\/\//, ''),
                    installLink: 'https://phantom.app/download',
                    downloadText: '前往Phantom官网下载'
                }
                // 可以添加更多钱包类型
            ];
            
            // 根据环境调整安装状态
            SUPPORTED_WALLETS.forEach(wallet => {
                // 如果是移动设备且钱包有移动链接，则认为它是"可安装的"
                if (isMobile && wallet.mobileLink) {
                    wallet.installed = true;
                }
            });
            
            // 构建模态框HTML
            modal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content wallet-modal-content">
                        <div class="modal-header wallet-modal-header">
                            <h5 class="modal-title wallet-modal-title" id="walletSelectorModalLabel">
                                <i class="fas fa-wallet me-2"></i>${window._('Select Wallet')}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body wallet-modal-body">
                            <div class="wallet-grid">
                                ${SUPPORTED_WALLETS.map(wallet => `
                                    <div class="wallet-option ${this.walletType === wallet.provider ? 'connected' : ''}"
                                         data-wallet="${wallet.provider}" 
                                         data-installed="${wallet.installed}" 
                                         ${isMobile && wallet.mobileLink ? `data-mobile-link="${wallet.mobileLink}"` : ''}
                                         ${!wallet.installed && wallet.installLink ? `data-install-link="${wallet.installLink}"` : ''}>
                                        <div class="wallet-icon-container">
                                            <div class="wallet-icon-wrapper ${wallet.provider}">
                                                <i class="${wallet.icon}"></i>
                                            </div>
                                        </div>
                                        <span class="wallet-name">${wallet.name}</span>
                                        ${this.walletType === wallet.provider ? '<div class="wallet-connected-badge"><i class="fas fa-check-circle"></i></div>' : ''}
                                        ${!wallet.installed ? `
                                        <div class="wallet-not-installed">
                                            <span>${window._('Not Installed')}</span>
                                            <div class="install-action"><i class="fas fa-download me-1"></i>${window._('Click to install')}</div>
                                        </div>` : ''}
                                    </div>
                                `).join('')}
                            </div>
                            ${isMobile ? `
                            <div class="wallet-mobile-notice mt-3">
                                <div class="alert alert-info text-center py-2">
                                    <i class="fas fa-info-circle me-2"></i>
                                    <small>${window._('Tap a wallet to connect or install')}</small>
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
            
            // 添加到DOM并显示模态框
            document.body.appendChild(modal);
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();
            
            // 监听钱包选择
            const walletButtons = modal.querySelectorAll('.wallet-option');
            walletButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const walletType = this.getAttribute('data-wallet');
                    const mobileLink = this.getAttribute('data-mobile-link');
                    const installed = this.getAttribute('data-installed') === 'true';
                    const installLink = this.getAttribute('data-install-link');
                    
                    if (!installed && installLink) {
                        console.log(`打开钱包安装链接: ${installLink}`);
                        modalInstance.hide();
                        
                        // 显示确认对话框
                        if (confirm(window._('This wallet is not installed. Do you want to install it now?'))) {
                            // 打开安装链接
                            window.open(installLink, '_blank');
                        }
                        
                        // 由于用户需要安装钱包，不继续连接流程
                        resolve(null);
            return;
        }
        
                    modalInstance.hide();
                    
                    // 如果是移动设备且有移动链接，先尝试打开对应的应用
                    if (isMobile && mobileLink) {
                        console.log(`尝试打开移动钱包应用: ${mobileLink}`);
                        
                        // 记录当前钱包类型，以便回到页面时可以继续连接流程
                        localStorage.setItem('pendingWalletType', walletType);
                        
                        // 设置标记，指示我们尝试打开了钱包应用
                        walletState.pendingWalletAppOpen = true;
                        
                        // 打开钱包应用
                        window.location.href = mobileLink;
                        
                        // 设置一个超时，如果用户很快返回，说明可能没有安装应用
                        setTimeout(() => {
                            // 仍在同一页面上，可能应用未安装或用户取消了应用打开
                            resolve(walletType);
                        }, 2000);
                } else {
                        // 处理所选钱包类型
                        if (walletType) {
                            resolve(walletType);
                        } else {
                            resolve(null);
                        }
                    }
                });
            });
            
            // 监听模态框关闭事件
            modal.addEventListener('hidden.bs.modal', function () {
                document.body.removeChild(modal);
                resolve(null); // 用户关闭了对话框，没有选择钱包
            });
        } catch (error) {
            console.error('显示钱包选择对话框失败:', error);
            reject(error);
        }
    });
};

/**
 * 连接到以太坊钱包（如MetaMask）
 * @returns {Promise<boolean>} 连接是否成功
 */
walletState.connectEthereum = async function() {
    try {
        console.log('尝试连接以太坊钱包...');
        
        // 检查window.ethereum是否存在
        if (!window.ethereum) {
            console.error('未检测到MetaMask或其他以太坊钱包');
            showError('未检测到MetaMask，请安装MetaMask钱包扩展');
            return false;
        }
        
        // 检查Web3.js是否可用（可选项，只影响高级功能）
        if (!this.web3Available) {
            console.warn('Web3.js库未加载，某些高级钱包功能可能不可用');
            // 显示警告但继续连接
            showError('Web3.js加载失败，某些高级钱包功能可能不可用');
            // 不创建this.web3实例
        } else if (window.Web3) {
            // 如果Web3可用，创建实例
            try {
                this.web3 = new Web3(window.ethereum);
                console.log('Web3实例已创建');
            } catch (web3Error) {
                console.warn('创建Web3实例失败:', web3Error);
                // 继续执行，因为基本连接功能不依赖Web3实例
            }
        }
        
        let accounts;
        try {
            console.log('使用标准request方法连接');
            // 使用现代方法请求账户，不使用event listeners来避免兼容性问题
            accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        } catch (error) {
            console.error('连接到MetaMask失败:', error);
            showError('连接MetaMask失败: ' + (error.message || '请检查是否已登录MetaMask'));
            return false;
        }
        
        if (accounts && accounts.length > 0) {
            const address = accounts[0];
            console.log('以太坊钱包连接成功:', address);
            
            // 更新钱包状态
            this.address = address;
            this.walletType = 'ethereum';
            this.connected = true;
            this.provider = window.ethereum;
            
            // 尝试获取链ID（如果Web3可用）
            if (this.web3Available && window.ethereum.request) {
                try {
                    this.chainId = await window.ethereum.request({ method: 'eth_chainId' });
                    console.log('以太坊链ID:', this.chainId);
                } catch (chainIdError) {
                    console.warn('获取链ID失败:', chainIdError);
                    this.chainId = null;
                }
            }
            
            // 连接成功后处理
            // 1. 保存状态到本地存储
            try {
                localStorage.setItem('walletType', 'ethereum');
                localStorage.setItem('walletAddress', address);
                // 额外记录最后使用的钱包信息
                localStorage.setItem('lastWalletType', 'ethereum');
                localStorage.setItem('lastWalletAddress', address);
                console.log('[connectEthereum] 钱包信息已保存到本地存储:', {
                    walletType: 'ethereum',
                    address: address
                });
            } catch (storageError) {
                console.warn('[connectEthereum] 保存到本地存储失败:', storageError);
            }
            
            // 2. 获取余额和资产
            console.log('[connectEthereum] 获取钱包余额和资产');
            try {
                await this.getWalletBalance();
                await this.getUserAssets(this.address);
            } catch (balanceError) {
                console.warn('[connectEthereum] 获取余额或资产失败:', balanceError);
            }
            
            // 3. 检查是否为管理员
            console.log('[connectEthereum] 检查是否为管理员');
            try {
                await this.checkIsAdmin();
            } catch (adminError) {
                console.warn('[connectEthereum] 检查管理员状态失败:', adminError);
            }
            
            // 4. 更新UI显示
            console.log('[connectEthereum] 更新UI显示');
            try {
                await this.updateUI();
                // 显式调用UI更新
                this.updateDisplay();
            } catch (uiError) {
                console.warn('[connectEthereum] 更新UI失败:', uiError);
            }
            
            // 5. 触发状态变更事件
            console.log('[connectEthereum] 触发状态变更事件');
            try {
                // 使用更详细的状态对象
                this.notifyStateChange({
                    type: 'connect',
                    address: this.address,
                    walletType: this.walletType,
                    balance: this.balance,
                    nativeBalance: this.nativeBalance
                });
                
                // 显示连接成功提示
                const truncatedAddress = this.address.slice(0, 6) + '...' + this.address.slice(-4);
                showSuccess(`钱包已连接: ${truncatedAddress}`);
            } catch (eventError) {
                console.warn('[connectEthereum] 触发事件失败:', eventError);
            }
            
            // 6. 设置MetaMask断开连接监听器 - 简化监听器设置，避免兼容性问题
            try {
                // 简化版本的监听器设置
                if (window.ethereum) {
                    console.log('设置简化版以太坊钱包事件监听器');
                    
                    // 账户变更监听
                    const handleAccountsChanged = (newAccounts) => {
                        if (newAccounts.length === 0) {
                            // 用户断开连接
                            this.disconnect();
                        } else if (this.address !== newAccounts[0]) {
                            // 账户切换
                            this.address = newAccounts[0];
                            this.updateUI();
                            this.getWalletBalance();
                        }
                    };
                    
                    // 移除旧的监听器（如果存在）
                    if (this._accountsChangedHandler) {
                        try {
                            window.ethereum.removeListener('accountsChanged', this._accountsChangedHandler);
                        } catch (e) {
                            console.warn('移除旧的accountsChanged监听器失败:', e);
                        }
                    }
                    
                    // 添加新的监听器
                    this._accountsChangedHandler = handleAccountsChanged;
                    window.ethereum.on('accountsChanged', handleAccountsChanged);
                    
                    // 链变更监听
                    const handleChainChanged = (chainId) => {
                        console.log('以太坊网络已更改，刷新页面');
                        this.chainId = chainId;
                        this.updateUI();
                    };
                    
                    // 移除旧的监听器（如果存在）
                    if (this._chainChangedHandler) {
                        try {
                            window.ethereum.removeListener('chainChanged', this._chainChangedHandler);
                        } catch (e) {
                            console.warn('移除旧的chainChanged监听器失败:', e);
                        }
                    }
                    
                    // 添加新的监听器
                    this._chainChangedHandler = handleChainChanged;
                    window.ethereum.on('chainChanged', handleChainChanged);
                    
                    console.log('以太坊钱包事件监听器设置完成');
                }
            } catch (listenerError) {
                console.warn('设置MetaMask事件监听器失败:', listenerError);
            }
            
            return true;
        } else {
            console.error('未能获取以太坊钱包地址');
            showError('未能获取以太坊钱包地址，请确保已授权访问');
            return false;
        }
    } catch (error) {
        console.error('连接以太坊钱包过程中发生错误:', error);
        showError('连接MetaMask失败: ' + (error.message || '未知错误'));
        return false;
    }
};

/**
 * 连接到Phantom钱包
 * @returns {Promise<boolean>} 连接是否成功
 */
walletState.connectPhantom = async function() {
    try {
        console.log('[connectPhantom] 开始尝试连接Phantom钱包...');
        console.log('[connectPhantom] 检查window.solana:', window.solana ? '存在' : '不存在');
        
        if (!window.solana) {
            console.error('[connectPhantom] window.solana对象不存在，请安装Phantom钱包扩展');
            showError('未检测到Phantom钱包，请安装Phantom钱包扩展');
            return false;
        }
        
        console.log('[connectPhantom] window.solana.isPhantom:', window.solana.isPhantom ? '是' : '否');
        
        if (!window.solana.isPhantom) {
            console.error('[connectPhantom] 不是Phantom钱包，请安装Phantom钱包扩展');
            showError('未检测到Phantom钱包，请安装Phantom钱包扩展');
            return false;
        }
        
        let connected = false;
        let publicKey = null;
        
        // 首先尝试检查是否已连接
        console.log('[connectPhantom] 检查Phantom是否已连接:', window.solana.isConnected ? '已连接' : '未连接');
        
        if (window.solana.isConnected) {
            publicKey = window.solana.publicKey;
            console.log('[connectPhantom] Phantom已连接，publicKey:', publicKey ? publicKey.toString() : '无');
            
            if (publicKey) {
                console.log('[connectPhantom] Phantom已经连接，使用现有连接');
                connected = true;
                } else {
                console.log('[connectPhantom] Phantom声称已连接，但没有publicKey，尝试重新连接');
            }
        }
        
        // 如果未连接，尝试连接
        if (!connected) {
            console.log('[connectPhantom] 尝试新建Phantom连接...');
            
            try {
                // 尝试连接Phantom
                const resp = await window.solana.connect();
                console.log('[connectPhantom] Phantom连接响应:', resp);
                
                if (resp && resp.publicKey) {
                    publicKey = resp.publicKey;
                    connected = true;
                    console.log('[connectPhantom] 成功获取publicKey:', publicKey.toString());
                } else {
                    console.error('[connectPhantom] 连接响应没有publicKey');
                    throw new Error('未能获取Phantom钱包地址');
                }
            } catch (connectError) {
                console.error('[connectPhantom] 连接Phantom时出错:', connectError);
                showError('连接Phantom钱包失败: ' + (connectError.message || '未知错误'));
                throw connectError;
            }
        }
        
        if (connected && publicKey) {
            // 更新状态
            this.address = publicKey.toString();
            this.walletType = 'phantom';
            this.connected = true;
            this.provider = window.solana;
            
            console.log(`[connectPhantom] 更新钱包状态，地址: ${this.address}`);
            
            // 设置事件监听器
            this.setupPhantomListeners();
            
            console.log(`[connectPhantom] Phantom钱包连接成功: ${this.address}`);
            
            // 连接成功后处理
            // 1. 保存状态到本地存储
            try {
                localStorage.setItem('walletType', 'phantom');
                localStorage.setItem('walletAddress', this.address);
                console.log('[connectPhantom] 钱包信息已保存到本地存储');
            } catch (storageError) {
                console.warn('[connectPhantom] 保存到本地存储失败:', storageError);
            }
            
            // 2. 获取余额和资产
            console.log('[connectPhantom] 获取钱包余额和资产');
            try {
                await this.getWalletBalance();
                await this.getUserAssets(this.address);
            } catch (balanceError) {
                console.warn('[connectPhantom] 获取余额或资产失败:', balanceError);
            }
            
            // 3. 检查是否为管理员
            console.log('[connectPhantom] 检查是否为管理员');
            try {
                await this.checkIsAdmin();
            } catch (adminError) {
                console.warn('[connectPhantom] 检查管理员状态失败:', adminError);
            }
            
            // 4. 更新UI显示
            console.log('[connectPhantom] 更新UI显示');
            try {
                await this.updateUI();
            } catch (uiError) {
                console.warn('[connectPhantom] 更新UI失败:', uiError);
            }
            
            // 5. 触发状态变更事件
            console.log('[connectPhantom] 触发状态变更事件');
            try {
                // 使用更详细的状态对象
                this.notifyStateChange({
                    type: 'connect',
                    address: this.address,
                    walletType: this.walletType,
                    balance: this.balance,
                    nativeBalance: this.nativeBalance
                });
                
                // 显示连接成功提示
                const truncatedAddress = this.address.slice(0, 6) + '...' + this.address.slice(-4);
                showSuccess(`钱包已连接: ${truncatedAddress}`);
            } catch (eventError) {
                console.warn('[connectPhantom] 触发事件失败:', eventError);
            }
            
            return true;
        } else {
            console.error('[connectPhantom] 未能连接到Phantom钱包');
            throw new Error('未能连接到Phantom钱包');
        }
                } catch (error) {
        console.error('[connectPhantom] Phantom钱包连接失败:', error);
        showError('连接Phantom钱包失败: ' + (error.message || '未知错误'));
        return false;
    }
};

// 页面初始化时就自动调用钱包初始化方法
document.addEventListener('DOMContentLoaded', async function() {
    console.log('页面加载完成，初始化钱包');

    // 确保钱包状态对象全局可用
    window.walletState = walletState;
    
    // 添加兼容层，确保旧代码仍然能够工作
    // 为walletState对象添加getter，使旧代码能够通过isConnected访问connected属性
    Object.defineProperty(window.walletState, 'isConnected', {
        get: function() {
            console.log('通过兼容层访问isConnected');
            return this.connected;
        },
        configurable: true
    });
    
    // 监听Web3.js加载失败事件
    document.addEventListener('web3LoadFailed', function() {
        console.warn('Web3.js加载失败，某些钱包功能可能受限');
        // 将Web3依赖标记为不可用
        window.walletState.web3Available = false;
        
        // 即使Web3.js不可用，仍然初始化钱包状态
        initWalletState();
    });
    
    // 监听Web3.js加载成功事件
    document.addEventListener('web3Loaded', function() {
        console.log('Web3.js加载成功，所有钱包功能可用');
        window.walletState.web3Available = true;
        
        // Web3.js加载成功，初始化钱包状态
        initWalletState();
    });
    
    // 如果5秒后没有收到Web3.js加载事件，强制初始化钱包
    // 这是为了防止事件监听器可能没有正确触发的情况
    setTimeout(function() {
        if (window.walletState.web3Available === undefined) {
            console.warn('未检测到Web3.js加载事件，强制初始化钱包状态');
            window.walletState.web3Available = typeof Web3 !== 'undefined';
            initWalletState();
        }
    }, 5000);
    
    // 初始化钱包状态的函数
    async function initWalletState() {
        // 避免重复初始化
        if (window.walletState.initialized) {
            return;
        }
        window.walletState.initialized = true;
        
        // 立即初始化钱包
        try {
            console.log('开始初始化钱包...');
            await walletState.init();
            console.log('钱包初始化完成:', {
                connected: walletState.connected,
                address: walletState.address ? walletState.address.substring(0, 8) + '...' : 'none',
                walletType: walletState.walletType
            });
            
            // 立即派发钱包状态事件 - 这对于页面刷新后恢复状态很重要
            if (walletState.connected && walletState.address) {
                console.log('钱包已连接，派发walletConnected事件');
                // 延迟触发事件，确保页面已完全加载
                setTimeout(() => {
                    document.dispatchEvent(new CustomEvent('walletConnected', {
                        detail: {
                            address: walletState.address,
                            walletType: walletState.walletType,
                            balance: walletState.balance
                        }
                    }));
                }, 500);
            }
        } catch (err) {
            console.error('钱包初始化失败:', err);
        }
    }
});

// 显示成功消息
function showSuccess(message) {
    try {
        if (window.iziToast) {
            window.iziToast.success({
                title: '成功',
                message: message,
                position: 'topRight',
                timeout: 3000
            });
    } else {
            console.log('%c✅ ' + message, 'color: green; font-weight: bold;');
        }
    } catch (e) {
        console.log('%c✅ ' + message, 'color: green; font-weight: bold;');
    }
}

// 显示错误消息
function showError(message) {
    try {
        if (window.iziToast) {
            window.iziToast.error({
                title: '错误',
                message: message,
                position: 'topRight',
                timeout: 4000
            });
    } else {
            console.error('❌ ' + message);
        }
    } catch (e) {
        console.error('❌ ' + message);
    }
}

// 初始化事件并注册全局点击监听器
document.addEventListener('DOMContentLoaded', function() {
    // 获取钱包按钮和下拉菜单
    const walletMenu = document.getElementById('walletDropdown');

    if (walletMenu) {
        // 添加全局点击事件，点击页面任何其他区域关闭钱包菜单
        document.addEventListener('click', function(e) {
            const walletBtn = document.getElementById('walletBtn');
            // 如果点击的不是下拉菜单内部元素，也不是钱包按钮
            if (!walletMenu.contains(e.target) && e.target !== walletBtn && !walletBtn.contains(e.target)) {
                // 关闭菜单
                const menuElement = document.getElementById('walletMenu');
                if (menuElement && menuElement.classList.contains('show')) {
                    menuElement.classList.remove('show');
                }
            }
        });

        // 防止点击下拉菜单内部元素时关闭菜单
        const menuElement = document.getElementById('walletMenu');
        if (menuElement) {
            menuElement.addEventListener('click', function(e) {
                // 只有点击切换钱包或断开连接按钮时才允许事件传播
                const isActionButton = 
                    e.target.id === 'switchWalletBtn' || 
                    e.target.id === 'disconnectWalletBtn' ||
                    e.target.closest('#switchWalletBtn') || 
                    e.target.closest('#disconnectWalletBtn');
                    
                if (!isActionButton) {
                    e.stopPropagation();
                }
            });
        }
    }
});