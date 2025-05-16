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
    // -- 修改：注释掉回调数组和相关方法，统一使用浏览器事件 --
    // stateChangeCallbacks: [],  // 状态变更回调函数数组 
    web3: null,                // Web3实例（以太坊钱包）
    provider: null,            // 钱包提供商实例
    pendingWalletAppOpen: false, // 是否正在等待打开钱包App（移动端）
    pendingWalletType: null,   // 待连接的钱包类型（移动端打开App时）
    web3Available: true,       // 标记Web3.js是否可用
    initialized: false,        // 标记钱包是否已初始化
    
    /**
     * 初始化钱包状态
     * 检查是否已经有连接的钱包，并恢复连接
     */
    async init() {
        try {
        console.log('初始化钱包...');
            
            // 防止重复初始化
            if (this.initialized) {
                console.log('钱包已初始化，跳过');
                return;
            }
            
            // 设置移动设备检测
            this._isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

            // 检查是否从钱包App返回 - 这需要在恢复存储的钱包信息之前进行
            if (this._isMobile) {
                console.log('检测到移动设备，检查是否从钱包App返回');
                
                // 检查各种可能的钱包类型
                const walletTypes = ['phantom', 'metamask', 'ethereum', 'solflare'];
                
                for (const type of walletTypes) {
                    if (this.checkIfReturningFromWalletApp(type)) {
                        console.log(`检测到从${type}钱包App返回，将尝试恢复连接`);
                        
                        // 先清除之前的连接信息，确保重新连接
                        this.clearState();
                        
                        // 等待DOM完全加载
                        await this.waitForDocumentReady();
                        
                        // 尝试连接钱包
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
                                // 更新UI和触发事件
                                this.updateUI();
                                this.triggerWalletStateChanged();
                                break; // 连接成功，退出循环
                            } else {
                                console.log(`从钱包App返回后连接${type}钱包失败`);
                            }
                        } catch (err) {
                            console.error('从钱包App返回后连接钱包失败:', err);
                        }
                    }
                }
            }

            // 尝试从localStorage和sessionStorage中读取钱包信息，优先使用localStorage
            const storedWalletType = localStorage.getItem('walletType') || sessionStorage.getItem('walletType');
            const storedWalletAddress = localStorage.getItem('walletAddress') || sessionStorage.getItem('walletAddress');
            
            console.log(`钱包初始化 - 类型: ${storedWalletType || '无'}, 地址: ${storedWalletAddress || '无'}`);
            
            // 立即设置基本状态，确保UI可以立即响应
            if (storedWalletType && storedWalletAddress) {
                console.log(`尝试恢复之前的钱包连接 - 类型: ${storedWalletType}, 地址: ${storedWalletAddress}`);
                
                // 设置初始状态，即使重连失败也有基本信息
                this.walletType = storedWalletType;
                this.address = storedWalletAddress;
                this.connected = true;  // 先假设连接成功，立即更新UI
                
                // 立即更新UI，不等待钱包重连结果
                this.updateUI();
                
                // 触发自定义事件，通知其他组件钱包已连接
                this.triggerWalletStateChanged();
                
                // 尝试加载资产信息
                this.getUserAssets(storedWalletAddress).catch(err => 
                    console.error('初始加载资产失败:', err)
                );
                
                // 检查浏览器是否支持所需的钱包
                let canReconnect = false;
                
                if (storedWalletType === 'ethereum' && window.ethereum) {
                    canReconnect = true;
                    console.log('检测到以太坊钱包可用，将尝试重连');
                } else if (storedWalletType === 'phantom') {
                    // 修改逻辑：给Phantom钱包更多时间初始化
                    if (window.solana && window.solana.isPhantom) {
                        canReconnect = true;
                        console.log('检测到Phantom钱包可用，将尝试重连');
                    } else {
                        // 新增：延迟检查Phantom钱包
                        console.log('未立即检测到Phantom钱包，将延迟再次检查');
                        setTimeout(() => {
                            if (window.solana && window.solana.isPhantom) {
                                console.log('延迟检测到Phantom钱包，现在可用');
                                this.delayedPhantomReconnect();
                            } else {
                                console.log('延迟检测后仍未发现Phantom钱包，使用localStorage保持状态');
                            }
                        }, 2000); // 给插件2秒钟初始化时间
                    }
                } else if (storedWalletType === 'solana' && window.solana) {
                    canReconnect = true;
                    console.log('检测到Solana钱包可用，将尝试重连');
                } else {
                    console.log(`未检测到${storedWalletType}钱包，无法自动重连，但保持界面状态`);
                }
                
                // 根据钱包类型进行静默重连
                if (canReconnect) {
                    try {
                        console.log(`尝试静默重连到${storedWalletType}钱包...`);
                        let success = false;
                        
                        if (storedWalletType === 'ethereum') {
                            success = await this.connectEthereum(true); // 传入true表示重连操作
                        } else if (storedWalletType === 'phantom' || storedWalletType === 'solana') {
                            success = await this.connectPhantom(true); // 传入true表示重连操作
                        }
                        
                        if (success) {
                            console.log('钱包重连成功');
                            this.triggerWalletStateChanged(); // 触发事件
                        } else {
                            console.log('钱包重连失败，但保持界面状态');
                            // 确保UI显示钱包信息，即使重连失败
                            this.updateUI();
                        }
                    } catch (error) {
                        console.error('静默重连失败:', error);
                        // 错误时也保持UI显示
                        this.updateUI();
                    }
                }
            } else {
                console.log('没有找到已存储的钱包信息');
                this.connected = false;
                this.address = '';
                this.walletType = '';
                this.updateUI();
            }
            
            // 添加页面卸载前保存钱包状态的事件
            window.addEventListener('beforeunload', () => {
                if (this.connected && this.walletType && this.address) {
                    console.log('页面卸载前保存钱包状态:', this.walletType, this.address);
                    localStorage.setItem('walletType', this.walletType);
                    localStorage.setItem('walletAddress', this.address);
                }
            });
            
            // 设置页面可见性变化事件，用于处理标签页切换后的钱包状态检查
            document.addEventListener('visibilitychange', () => {
                if (document.visibilityState === 'visible' && this.connected) {
                    console.log('页面变为可见，检查钱包状态...');
                    this.checkWalletConnection();
                }
            });
            
            // 监听localStorage变化事件
            window.addEventListener('storage', (event) => {
                if (event.key === 'walletAddress' || event.key === 'walletType') {
                    console.log('检测到其他标签页钱包状态变化:', event.key, event.newValue);
                    this.handleStorageChange();
                }
            });
            
            // 确保钱包状态与本地存储一致
            this.checkWalletConsistency();
            
            // 设置定期检查
            setInterval(() => this.checkWalletConsistency(), 5000);
            
            // 完成初始化
            this.initialized = true;
            console.log('钱包初始化完成');
            
            return true;
        } catch (error) {
            console.error('初始化钱包出错:', error);
            return false;
        }
    },
    
    // 确保钱包状态与本地存储一致
    checkWalletConsistency() {
        try {
            // 检查本地存储
            const storedAddress = localStorage.getItem('walletAddress');
            const storedType = localStorage.getItem('walletType');
            
            if (storedAddress && storedType) {
                // 本地存储有钱包信息，但状态对象显示未连接
                if (!this.connected || !this.address) {
                    console.log('检测到状态不一致：本地存储有钱包信息但状态显示未连接');
                    this.connected = true;
                    this.address = storedAddress;
                    this.walletType = storedType;
                    
                    // 更新UI
                    this.updateUI();
                }
            } else {
                // 本地存储没有钱包信息，但状态对象显示已连接
                if (this.connected && this.address) {
                    console.log('检测到状态不一致：状态显示已连接但本地存储无钱包信息');
                    this.connected = false;
                    this.address = null;
                    this.walletType = null;
                    this.balance = null;
                    
                    // 更新UI
                    this.updateUI();
                }
            }
            
            // 为全局一致性保留数据
            if (this.connected && this.address && this.walletType) {
                if (!localStorage.getItem('walletAddress') || !localStorage.getItem('walletType')) {
                    localStorage.setItem('walletAddress', this.address);
                    localStorage.setItem('walletType', this.walletType);
                }
            }
        } catch (err) {
            console.error('钱包状态一致性检查失败:', err);
        }
    },
    
    // 为资产详情页提供的购买按钮状态更新函数
    updateDetailPageButtonState() {
        console.log('购买按钮状态更新函数被调用');
        
        // 先确保钱包状态一致
        this.checkWalletConsistency();
        
        // 获取购买按钮
        const buyButton = document.getElementById('buy-button');
        if (!buyButton) {
            console.warn('找不到购买按钮元素，无法更新状态');
            return;
        }
        
        // 检查钱包是否已连接
        const isConnected = this.connected && this.address;
        
        // 更新购买按钮状态
        if (isConnected) {
            buyButton.disabled = false;
            buyButton.innerHTML = '<i class="fas fa-shopping-cart me-2"></i>Buy';
            buyButton.removeAttribute('title');
        } else {
            buyButton.disabled = true;
            buyButton.innerHTML = '<i class="fas fa-wallet me-2"></i>请先连接钱包';
            buyButton.title = '请先连接钱包';
        }
        
        // 如果存在分红按钮检查函数，也一并调用
        if (typeof window.checkDividendManagementAccess === 'function') {
            try {
                window.checkDividendManagementAccess();
            } catch (error) {
                console.error('分红按钮检查失败:', error);
            }
        }
    },
    
    /**
     * 等待文档完全加载
     */
    waitForDocumentReady() {
        return new Promise(resolve => {
            if (document.readyState === 'complete' || document.readyState === 'interactive') {
                resolve();
            } else {
                document.addEventListener('DOMContentLoaded', () => resolve());
            }
        });
    },
    
    /**
     * 处理localStorage变化，同步钱包状态
     */
    async handleStorageChange() {
        try {
            const storedWalletType = localStorage.getItem('walletType');
            const storedWalletAddress = localStorage.getItem('walletAddress');
            console.log('处理存储变化:', storedWalletType, storedWalletAddress);
            
            // 如果本地存储中的钱包信息与当前状态不一致
            if (storedWalletType && storedWalletAddress) {
                // 存储中有钱包信息，但当前未连接或地址不同
                if (!this.connected || this.address !== storedWalletAddress || this.walletType !== storedWalletType) {
                    console.log('同步钱包状态，准备重连:', storedWalletType, storedWalletAddress);
                    // 防止无限循环重连
                    if (!this._isReconnecting) {
                        this._isReconnecting = true;
                        
                        // 更新状态
                        this.walletType = storedWalletType;
                        this.address = storedWalletAddress;
                                this.connected = true;
                        
                        // 更新UI
                        this.updateUI();
                        
                        // 如果浏览器支持该钱包类型，尝试静默重连
                        let canReconnect = false;
                        
                        if (storedWalletType === 'ethereum' && window.ethereum) {
                            canReconnect = true;
                        } else if ((storedWalletType === 'phantom' || storedWalletType === 'solana') && 
                                  window.solana && window.solana.isPhantom) {
                            canReconnect = true;
                        }
                        
                        if (canReconnect) {
                            try {
                                console.log('尝试静默重连钱包...');
                                if (storedWalletType === 'ethereum') {
                                    await this.connectEthereum(true);
                                } else if (storedWalletType === 'phantom' || storedWalletType === 'solana') {
                                    await this.connectPhantom(true);
                            }
                        } catch (err) {
                                console.error('静默重连失败:', err);
                            }
                        }
                        
                        // 尝试获取余额和资产
                        this.getWalletBalance().catch(err => console.error('获取余额失败:', err));
                        this.getUserAssets(this.address).catch(err => console.error('获取资产失败:', err));
                        
                        this._isReconnecting = false;
                    }
                }
            } else if (!storedWalletType || !storedWalletAddress) {
                // 存储中没有钱包信息，但当前已连接
                if (this.connected) {
                    console.log('检测到其他标签页钱包断开连接，同步断开');
                    // 断开连接，不刷新页面
                    this.disconnect(false);
                }
            }
        } catch (error) {
            console.error('处理存储变化时出错:', error);
            this._isReconnecting = false;
        }
    },
    
    /**
     * 清除存储的钱包数据
     */
    clearStoredWalletData() {
        try {
            console.log('清除存储的钱包数据');
            localStorage.removeItem('walletType');
            localStorage.removeItem('walletAddress');
            localStorage.removeItem('lastWalletType');
            localStorage.removeItem('lastWalletAddress');
            localStorage.removeItem('pendingWalletType');
            sessionStorage.removeItem('returningFromWalletApp');
        } catch (error) {
            console.error('清除钱包数据失败:', error);
        }
    },
    
    /**
     * 检查钱包连接状态
     * 当从后台切换到前台或标签页激活时调用
     */
    async checkWalletConnection() {
        try {
            console.log('检查钱包连接状态...');
            
            // 首先检查是否从钱包App返回
            if (this.isMobile()) {
                // 检查各种可能的钱包类型
                const walletTypes = ['phantom', 'metamask', 'ethereum', 'solflare'];
                
                for (const type of walletTypes) {
                    if (this.checkIfReturningFromWalletApp(type)) {
                        console.log(`[页面可见性变化] 检测到从${type}钱包App返回，将尝试连接`);
                        
                        // 尝试连接钱包
                        let connected = false;
                        try {
                            if (type === 'phantom' || type === 'solana') {
                                connected = await this.connectPhantom();
                            } else if (type === 'ethereum' || type === 'metamask') {
                                connected = await this.connectEthereum();
                            }
                            
                            if (connected) {
                                console.log(`[页面可见性变化] 成功连接${type}钱包`);
                                return; // 连接成功，结束函数
                            }
                        } catch (error) {
                            console.error('[页面可见性变化] 连接钱包失败:', error);
                        }
                    }
                }
            }
            
            // 常规的钱包连接状态检查
            if (!this.connected || !this.address || !this.walletType) {
                console.log('钱包未连接，无需检查');
                return;
            }
            
            // 检查localStorage中是否存在钱包信息
            const storedWalletType = localStorage.getItem('walletType');
            const storedWalletAddress = localStorage.getItem('walletAddress');
            
            if (!storedWalletType || !storedWalletAddress) {
                console.log('localStorage中没有钱包信息，可能在其他标签页断开了连接');
                // 设置为未连接状态但不刷新页面
                this.disconnect(false);
                return;
            }
            
            // 检查当前连接的钱包是否仍然可访问
            let isConnected = false;
            
            if (this.walletType === 'ethereum' && window.ethereum) {
                try {
                    // 检查以太坊连接状态
                    const accounts = await window.ethereum.request({ method: 'eth_accounts' });
                    isConnected = accounts && accounts.length > 0 && accounts[0].toLowerCase() === this.address.toLowerCase();
                    console.log('以太坊钱包检查结果:', isConnected);
                } catch (err) {
                    console.error('检查以太坊钱包连接失败:', err);
                    isConnected = false;
                }
            } else if ((this.walletType === 'phantom' || this.walletType === 'solana') && window.solana && window.solana.isPhantom) {
                try {
                    // 检查Phantom连接状态
                    isConnected = window.solana.isConnected && window.solana.publicKey && 
                                   window.solana.publicKey.toString() === this.address;
                    console.log('Phantom钱包检查结果:', isConnected);
                } catch (err) {
                    console.error('检查Phantom钱包连接失败:', err);
                    isConnected = false;
                }
            }
            
            if (!isConnected) {
                console.log('钱包已断开连接，但保持UI显示');
                // 不改变连接状态，保持UI显示，等待用户手动重连
            } else {
                console.log('钱包仍然连接，刷新数据');
                // 更新余额和资产
                this.getWalletBalance().catch(err => console.error('获取余额失败:', err));
                this.getUserAssets(this.address).catch(err => console.error('获取资产失败:', err));
            }
        } catch (error) {
            console.error('检查钱包连接状态出错:', error);
        }
    },
    
    /**
     * 清除所有钱包状态
     */
    clearState() {
        console.log('清除钱包状态');
        this.address = null;
        this.connected = false;
        this.walletType = null;
        this.balance = null;
        this.isAdmin = false;
        
        // 清除存储的钱包数据
        this.clearStoredWalletData();
        
        // 清除事件监听器
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
     * 统一的钱包连接方法
     * @param {string} walletType - 钱包类型
     * @returns {Promise<boolean>} 连接是否成功
     */
    async connect(walletType) {
        console.log(`尝试连接钱包: ${walletType}`);
        this.connecting = true;
        this.updateUI();
        
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
                console.log(`${walletType} 钱包连接成功`);
                // -- 修改：连接成功后触发事件 --
                this.triggerWalletStateChanged();
                
                // 更新详情页购买按钮状态
                this.updateDetailPageButtonState();
            } else {
                console.log(`${walletType} 钱包连接失败或被用户取消`);
                // 确保状态回滚
                if (!this.connected) { // 只有在确实没连上的情况下才清除
                    this.clearState();
                }
            }
        } catch (error) {
            console.error(`连接 ${walletType} 钱包失败:`, error);
            this.clearState(); // 出错时彻底清除状态
            showError(`连接失败: ${error.message}`);
        } finally {
            this.connecting = false;
            this.updateUI();
        }
        return success;
    },
    
    /**
     * 更新UI显示
     */
    updateUI() {
        try {
            console.log('更新钱包UI, 连接状态:', this.connected);
            
            // 获取UI元素
            const walletBtn = document.getElementById('walletBtn');
            const walletBtnText = document.getElementById('walletBtnText');
            const walletAddressDisplay = document.getElementById('walletAddressDisplay');
            const walletMenu = document.getElementById('walletMenu');
            const adminEntry = document.getElementById('adminEntry');
            
            if (!walletBtn) {
                console.warn('找不到钱包按钮元素');
                return;
            }
            
        if (this.connected && this.address) {
                // 钱包已连接状态
                if (walletBtnText) {
                    // 显示格式化的地址而不是余额
                    const formattedAddress = this.formatAddress(this.address);
                    walletBtnText.textContent = formattedAddress;
                    console.log('已设置按钮文本为地址:', formattedAddress);
                }
                
                // 确保下拉菜单中的钱包地址显示正确
                if (walletAddressDisplay) {
                    const formattedAddress = this.formatAddress(this.address);
                    walletAddressDisplay.textContent = formattedAddress;
                    walletAddressDisplay.title = this.address; // 设置完整地址为悬停提示
                    console.log('已设置地址显示:', formattedAddress);
                } else {
                    console.warn('找不到钱包地址显示元素 walletAddressDisplay');
                }
                
                // 更新下拉菜单中的余额显示
                const dropdownBalanceElement = document.getElementById('walletBalanceInDropdown');
                if (dropdownBalanceElement) {
                    const formattedBalance = this.balance !== null ? parseFloat(this.balance).toFixed(2) : '0.00';
                    dropdownBalanceElement.textContent = formattedBalance;
                    console.log('已设置下拉菜单余额显示:', formattedBalance);
                } else {
                    console.warn('找不到余额显示元素 walletBalanceInDropdown');
                }
                
                // 显示用户资产部分
                const userAssetsSection = document.getElementById('userAssetsSection');
                if (userAssetsSection) {
                    userAssetsSection.style.display = 'block';
                }
                
                // 根据管理员状态更新管理员入口显示
                if (adminEntry) {
                    console.log('更新管理员入口显示, 当前管理员状态:', this.isAdmin);
                    adminEntry.style.display = this.isAdmin ? 'block' : 'none';
                }
                
                // 确保余额也更新
                this.updateBalanceDisplay();
            } else {
                // 钱包未连接状态
                if (walletBtnText) {
                    walletBtnText.textContent = window._ ? window._('Connect Wallet') : 'Connect Wallet';
                    console.log('已设置按钮文本为连接钱包');
                }
                
                // 隐藏用户资产部分
                const userAssetsSection = document.getElementById('userAssetsSection');
                if (userAssetsSection) {
                    userAssetsSection.style.display = 'none';
                }
                
                // 隐藏管理员入口
                if (adminEntry) {
                    adminEntry.style.display = 'none';
                }
            }
            
            // 尝试触发钱包状态变化事件
            try {
                if (typeof this.triggerWalletStateChanged === 'function') {
                    this.triggerWalletStateChanged();
                }
            } catch (e) {
                console.warn('触发钱包状态变化事件失败:', e);
            }
        } catch (error) {
            console.error('更新UI出错:', error);
        }
    },
    
    /**
     * 触发钱包状态变化事件
     * 通知其他组件钱包状态已变化
     */
    triggerWalletStateChanged() {
        try {
            console.log('[triggerWalletStateChanged] 触发钱包状态变化事件');
            
            // 创建自定义事件
            const event = new CustomEvent('walletStateChanged', { 
                detail: { 
                    connected: this.connected,
                    address: this.address,
                    walletType: this.walletType,
                    balance: this.balance,
                    isAdmin: this.isAdmin,
                    timestamp: new Date().getTime()
                } 
            });
            
            // 在document上分发事件
            document.dispatchEvent(event);
            console.log('[triggerWalletStateChanged] 钱包状态变化事件已触发');
            
            // 更新详情页按钮状态
            if (typeof this.updateDetailPageButtonState === 'function') {
                try {
                    this.updateDetailPageButtonState();
                    console.log('[triggerWalletStateChanged] 详情页按钮状态已更新');
                } catch (btnError) {
                    console.error('[triggerWalletStateChanged] 更新按钮状态失败:', btnError);
                }
            }
            
        } catch (error) {
            console.error('[triggerWalletStateChanged] 触发钱包状态变化事件失败:', error);
            
            // 尝试发出备用自定义事件
            try {
                const simpleEvent = new Event('walletChanged');
                document.dispatchEvent(simpleEvent);
                console.log('[triggerWalletStateChanged] 发送了备用的walletChanged事件');
            } catch (backupError) {
                console.error('[triggerWalletStateChanged] 备用事件也触发失败:', backupError);
            }
        }
    },
    
    /**
     * 格式化钱包地址显示
     * @param {string} address - 完整的钱包地址
     * @returns {string} 格式化后的地址（如：0x1234...5678）
     */
    formatAddress: function(address) {
        if (!address) return '';
        
        if (address.length > 10) {
            return address.slice(0, 6) + '...' + address.slice(-4);
        }
        
        return address;
    },
    
    /**
     * 连接到特定钱包提供商
     * 根据钱包类型调用相应的连接方法
     * 
     * @param {string} provider - 钱包提供商名称
     * @returns {Promise<boolean>} 连接是否成功
     * @deprecated 使用更简洁的connect方法代替
     */
    async connectToProvider(provider) {
        return this.connect(provider);
    },
    
    /**
     * 断开钱包连接
     * @param {boolean} reload - 是否重新加载页面
     */
    async disconnect(reload = true) {
        console.log('断开钱包连接...');
            
        // 清除状态和存储
        this.clearState();
        this.clearStoredWalletData();
        
        // 移除监听器
        if (this.provider && this.provider.removeListener) {
            this.provider.removeListener('accountsChanged', this.handleAccountsChanged);
            this.provider.removeListener('chainChanged', this.handleChainChanged);
            this.provider.removeListener('disconnect', this.handleDisconnect);
        }
        if (window.solana && window.solana.removeListener) {
             window.solana.removeListener('disconnect', this.handlePhantomDisconnect);
             window.solana.removeListener('accountChanged', this.handlePhantomAccountChanged);
        }
        
        this.provider = null;
        this.web3 = null;
            
        // 更新UI
        this.updateUI();
            
        // -- 修改：断开连接后触发事件 --
        this.triggerWalletStateChanged();
        
        // 更新详情页购买按钮状态
        this.updateDetailPageButtonState();
        
        // 通知状态变更
        // -- 修改：移除 notifyStateChange 调用 --
        // this.notifyStateChange({ type: 'disconnect' });
        
        // 可选：刷新页面以确保完全重置
            if (reload) {
            console.log('刷新页面以完成断开连接');
                    window.location.reload();
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
     * 检查钱包是否为管理员
     */
    async checkIsAdmin() {
        try {
            console.log('检查钱包是否为管理员...');
            
            const address = this.getAddress();
            const walletType = this.getWalletType();
            const timestamp = new Date().getTime();
            
            // 修改API路径从/api/admin/check_admin到/api/admin/check
            const apiUrl = `/api/admin/check?address=${address}&wallet_type=${walletType}&_=${timestamp}`;
            console.log('调用管理员检查API:', apiUrl);
            
            const response = await fetch(apiUrl);
            if (!response.ok) {
              throw new Error(`${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            const isAdmin = data.is_admin === true;
            
            console.log('服务器返回的管理员状态:', isAdmin);
            this.isAdmin = isAdmin;
            
            // 更新管理员入口显示状态
            this.updateAdminDisplay();
            
            // 返回管理员状态
            return isAdmin;
        } catch (error) {
            console.error('管理员检查API响应不成功:', error.message);
            console.log('API管理员检查失败，使用备用逻辑');
            
            // 备用逻辑：使用缓存的状态或其他方式判断
            const cachedIsAdmin = localStorage.getItem('isAdmin') === 'true';
            
            if (this.isConnected() && this.address) {
              // 获取管理员配置
              const adminAddresses = [
                // 可以在这里添加已知的管理员地址列表
                '0x1234567890abcdef1234567890abcdef12345678'
              ];
              
              // 检查当前钱包是否在管理员列表中
              const isAdmin = adminAddresses.some(addr => 
                addr.toLowerCase() === this.address.toLowerCase()
              );
              
              console.log('钱包管理员状态(备用判断):', isAdmin ? '是管理员' : '不是管理员');
              this.isAdmin = isAdmin;
              this.updateAdminDisplay();
              return isAdmin;
            }
            
            return false;
        }
    },
    
    /**
     * 注册状态变更回调函数
     * @param {Function} callback 回调函数
     */
    onStateChange(callback) {
        if (typeof callback !== 'function') {
            console.warn('注册的状态变更回调不是函数');
            return;
        }
        
        if (!Array.isArray(this.stateChangeCallbacks)) {
            this.stateChangeCallbacks = [];
        }
        
            this.stateChangeCallbacks.push(callback);
        console.log('已注册钱包状态变更回调');
        
        // 立即调用回调一次，传递当前状态
        try {
            callback({
                type: 'initial',
                connected: this.connected,
                address: this.address,
                walletType: this.walletType,
                balance: this.balance,
                nativeBalance: this.nativeBalance,
                isAdmin: this.isAdmin,
                timestamp: Date.now()
            });
        } catch (error) {
            console.error('执行初始状态回调时出错:', error);
        }
    },
    
    /**
     * 取消注册钱包状态变更回调
     * 
     * @param {Function} callback - 要移除的回调函数
     */
    offStateChange(callback) {
        if (!Array.isArray(this.stateChangeCallbacks)) {
            this.stateChangeCallbacks = [];
            return;
        }
        
        const initialLength = this.stateChangeCallbacks.length;
        this.stateChangeCallbacks = this.stateChangeCallbacks.filter(cb => cb !== callback);
        
        const removed = initialLength - this.stateChangeCallbacks.length;
        if (removed > 0) {
            console.log(`已移除 ${removed} 个钱包状态变更回调`);
        }
    },
    
    /**
     * 通知状态变更
     * @param {Object} details 状态变更详情
     */
    notifyStateChange(details = {}) {
        try {
            if (!Array.isArray(this.stateChangeCallbacks)) {
                this.stateChangeCallbacks = [];
            }
            
            // 构建事件数据
            const eventData = {
                    connected: this.connected,
                    address: this.address,
                    walletType: this.walletType,
                    balance: this.balance,
                    isAdmin: this.isAdmin,
                    ...details
            };
            
            // 更新管理员入口显示状态，确保任何状态变化都会触发管理员入口更新
            this.updateAdminDisplay();
            
            // 更新管理员链接，确保包含钱包地址参数
            if (typeof window.updateAdminNavLink === 'function') {
                window.updateAdminNavLink();
            }
            
            // 通知所有注册的回调
            this.stateChangeCallbacks.forEach(callback => {
                try {
                    if (typeof callback === 'function') {
                        callback(eventData);
                    }
                } catch (callbackError) {
                    console.error('执行状态变化回调时出错:', callbackError);
                }
            });
            
            // 广播自定义事件
            document.dispatchEvent(new CustomEvent('walletStateChanged', {
                detail: eventData
            }));
            
            // 为特定类型的变化触发额外的事件
            if (details.type === 'connect' || details.type === 'init' || details.type === 'reconnect' || details.type === 'admin_status_changed') {
                // 触发余额更新事件
                document.dispatchEvent(new CustomEvent('walletBalanceUpdated', {
                    detail: {
                        address: this.address,
                        balance: this.balance,
                        walletType: this.walletType,
                        isAdmin: this.isAdmin
                    }
                }));
                
                // 如果是管理员状态变化，触发特定事件
                if (details.type === 'admin_status_changed') {
                    document.dispatchEvent(new CustomEvent('adminStatusChanged', {
                        detail: {
                            isAdmin: this.isAdmin,
                            address: this.address
                        }
                    }));
                }
            }
        } catch (error) {
            console.error('通知钱包状态变化时出错:', error);
        }
    },
    
    /**
     * 更新管理员显示状态
     * 独立函数，确保在任何状态变化时都可以单独调用
     */
    updateAdminDisplay() {
        try {
            console.log('更新管理员入口显示状态，当前状态:', this.isAdmin);
            const adminEntry = document.getElementById('adminEntry');
            if (adminEntry) {
                adminEntry.style.display = this.isAdmin ? 'block' : 'none';
                console.log('管理员入口显示状态已更新:', this.isAdmin ? '显示' : '隐藏');
                
                // 更新管理员链接
                if (this.isAdmin && typeof window.updateAdminNavLink === 'function') {
                    window.updateAdminNavLink();
                }
            }
            
            // 检查是否在资产详情页，如果是则更新分红入口
            const isDetailPage = document.querySelector('.asset-detail-page') !== null;
            if (isDetailPage) {
                if (typeof window.checkDividendManagementAccess === 'function') {
                    console.log('检测到资产详情页，更新分红入口状态');
                    window.checkDividendManagementAccess();
                } else {
                    console.log('检测到资产详情页，但分红入口检查函数不可用，尝试手动创建或显示');
                    this.createOrShowDividendButtons();
                }
            }
        } catch (error) {
            console.error('更新管理员显示状态失败:', error);
        }
    },
    
    /**
     * 手动创建或显示分红按钮
     * 当checkDividendManagementAccess函数不可用时的备用方案
     */
    createOrShowDividendButtons() {
        try {
            if (!this.isAdmin) {
                console.log('非管理员，无需显示分红按钮');
                return;
            }
            
            console.log('尝试手动创建或显示分红按钮');
            
            // 检查常规按钮
            let dividendBtn = document.getElementById('dividendManagementBtn');
            let dividendBtnMobile = document.getElementById('dividendManagementBtnMobile');
            let dividendBtnMedium = document.getElementById('dividendManagementBtnMedium');
            
            // 在窗口上查找资产符号
            const tokenSymbol = window.ASSET_CONFIG?.tokenSymbol || 
                               document.querySelector('[data-token-symbol]')?.getAttribute('data-token-symbol');
            
            if (!tokenSymbol) {
                console.warn('未能找到资产符号，无法创建分红按钮');
                return;
            }
            
            // 更新或创建常规按钮
            if (dividendBtn) {
                dividendBtn.href = `/assets/${tokenSymbol}/dividend?eth_address=${this.address}`;
                dividendBtn.style.display = 'inline-flex';
                console.log('更新并显示现有分红按钮');
            } else {
                // 查找按钮容器
                const buttonContainer = document.querySelector('.d-flex.align-items-center.gap-2');
                if (buttonContainer) {
                    // 创建分红管理按钮
                    dividendBtn = document.createElement('a');
                    dividendBtn.id = 'dividendManagementBtn';
                    dividendBtn.href = `/assets/${tokenSymbol}/dividend?eth_address=${this.address}`;
                    dividendBtn.className = 'btn btn-outline-primary';
                    dividendBtn.style.display = 'inline-flex';
                    dividendBtn.innerHTML = '<i class="fas fa-coins me-2"></i>Dividend Management';
                    
                    // 添加到容器中
                    buttonContainer.appendChild(dividendBtn);
                    console.log('成功创建分红管理按钮');
                }
            }
            
            // 更新或创建移动端按钮
            if (dividendBtnMobile) {
                dividendBtnMobile.href = `/assets/${tokenSymbol}/dividend?eth_address=${this.address}`;
                dividendBtnMobile.style.display = 'block';
                console.log('更新并显示移动端分红按钮');
            } else {
                // 查找移动端按钮容器
                const mobileButtonContainer = document.querySelector('.d-flex.gap-2');
                if (mobileButtonContainer) {
                    // 创建移动端分红管理按钮
                    dividendBtnMobile = document.createElement('a');
                    dividendBtnMobile.id = 'dividendManagementBtnMobile';
                    dividendBtnMobile.href = `/assets/${tokenSymbol}/dividend?eth_address=${this.address}`;
                    dividendBtnMobile.className = 'btn btn-sm btn-outline-primary d-md-none d-block';
                    dividendBtnMobile.style.display = 'block';
                    dividendBtnMobile.innerHTML = '<i class="fas fa-coins me-2"></i>Dividend';
                    
                    // 添加到容器中
                    mobileButtonContainer.appendChild(dividendBtnMobile);
                    console.log('成功创建移动端分红管理按钮');
                }
            }
            
            // 更新或创建中屏按钮
            if (dividendBtnMedium) {
                dividendBtnMedium.href = `/assets/${tokenSymbol}/dividend?eth_address=${this.address}`;
                dividendBtnMedium.style.display = 'block';
                console.log('更新并显示中屏分红按钮');
            } else {
                // 查找中屏按钮容器
                const mediumButtonContainer = document.querySelector('.d-flex.gap-2');
                if (mediumButtonContainer) {
                    // 创建中屏分红管理按钮
                    dividendBtnMedium = document.createElement('a');
                    dividendBtnMedium.id = 'dividendManagementBtnMedium';
                    dividendBtnMedium.href = `/assets/${tokenSymbol}/dividend?eth_address=${this.address}`;
                    dividendBtnMedium.className = 'btn btn-outline-primary d-none d-md-block d-lg-none';
                    dividendBtnMedium.style.display = 'block';
                    dividendBtnMedium.innerHTML = '<i class="fas fa-coins me-2"></i>Dividend Management';
                    
                    // 添加到容器中
                    mediumButtonContainer.appendChild(dividendBtnMedium);
                    console.log('成功创建中屏分红管理按钮');
                }
            }
        } catch (error) {
            console.error('手动创建或显示分红按钮失败:', error);
        }
    },
    
    /**
     * 更新钱包余额
     * 从区块链获取最新的钱包余额
     * @returns {Promise<number|null>} 更新后的余额，失败时返回null
     */
    async getWalletBalance() {
        try {
            // 直接从区块链获取USDC余额，跳过API调用
            // 根据钱包类型选择不同的余额查询方式
            if (this.walletType === 'phantom' && window.solana && window.solana.isConnected) {
                await this.ensureSolanaLibraries();
                // 使用主网RPC节点
                const connection = new window.solanaWeb3.Connection(window.solanaWeb3.clusterApiUrl('mainnet-beta'));
                const publicKey = new window.solanaWeb3.PublicKey(this.address);
                
                // 使用Solana上的USDC合约地址
                const usdcMint = new window.solanaWeb3.PublicKey('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v');
                
                try {
                    // 直接查询代币账户余额
                    const tokenAccounts = await connection.getParsedTokenAccountsByOwner(publicKey, { mint: usdcMint });
                    
                    if (tokenAccounts.value.length > 0) {
                        const balance = tokenAccounts.value[0].account.data.parsed.info.tokenAmount.uiAmount;
                        this.balance = parseFloat(balance);
                        console.log(`直接从Solana区块链获取到钱包USDC余额: ${this.balance}`);
                        return this.balance;
                    } else {
                        console.log('未找到USDC代币账户，余额为0');
                        this.balance = 0;
                        return 0;
                    }
                } catch (solanaError) {
                    console.error('直接查询Solana USDC余额出错:', solanaError);
                    
                    // 作为备选方案，尝试API获取
                    console.log('尝试通过API获取USDC余额');
                    const response = await fetch(`/api/service/wallet/token_balance?address=${this.address}&token=USDC`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.success && data.balance) {
                            this.balance = parseFloat(data.balance);
                            console.log(`通过API获取到钱包余额: ${this.balance} USDC`);
                            return this.balance;
                        }
                    }
                    
                    // 如果备选方案也失败，返回0而不是cached值
                    console.warn('无法获取USDC余额，默认为0');
                    return 0;
                }
            } else if (this.walletType === 'metamask' && window.ethereum) {
                // 以太坊钱包的USDC余额获取
                const ethProvider = new window.ethers.providers.Web3Provider(window.ethereum);
                const usdcAddress = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'; // USDC在以太坊上的合约地址
                const usdcAbi = [
                    "function balanceOf(address owner) view returns (uint256)",
                    "function decimals() view returns (uint8)"
                ];
                const usdcContract = new window.ethers.Contract(usdcAddress, usdcAbi, ethProvider);
                const decimals = await usdcContract.decimals();
                const balance = await usdcContract.balanceOf(this.address);
                this.balance = parseFloat(window.ethers.utils.formatUnits(balance, decimals));
                console.log(`直接从以太坊区块链获取到钱包余额: ${this.balance} USDC`);
                return this.balance;
            }
            
            console.warn('不支持的钱包类型或钱包未连接，无法获取USDC余额');
            return 0;
        } catch (error) {
            console.error('获取钱包USDC余额失败:', error);
            // 返回0而非缓存的值，避免显示过期数据
            return 0;
        }
    },
    
    /**
     * 触发余额更新事件
     * 将余额变更通知到UI
     */
    triggerBalanceUpdatedEvent() {
        try {
            console.log(`[triggerBalanceUpdatedEvent] 触发余额更新事件: USDC=${this.balance}`);
            
            // 创建并分发自定义事件
            const event = new CustomEvent('walletBalanceUpdated', {
                detail: {
                    balance: this.balance,
                    currency: 'USDC',
                    timestamp: new Date().getTime()
                }
            });
            
            // 在document上分发事件
            document.dispatchEvent(event);
            console.log('[triggerBalanceUpdatedEvent] 余额更新事件已触发');
            
            // 直接更新UI，但不再重复触发事件
            // this.updateBalanceDisplay(); // 删除这行以防止循环调用
        } catch (error) {
            console.error('[triggerBalanceUpdatedEvent] 触发余额更新事件失败:', error);
        }
    },
    
    /**
     * 更新余额显示
     */
    updateBalanceDisplay(balance = null) {
        try {
            console.log('更新余额显示, 余额:', balance);
            
            // 如果没有提供余额，尝试从walletState获取
            if (balance === null && this.state) {
                balance = this.state.balance;
            }
            
            // 更新全局按钮文本
            if (this.address) {
                const shortAddress = this.formatAddress(this.address);
                console.log('更新钱包按钮文本为地址:', shortAddress);
                $('.wallet-address-text, .wallet-address').text(shortAddress);
            }
            
            // 更新下拉菜单余额显示
            const balanceStr = (balance !== null && !isNaN(parseFloat(balance))) 
                ? parseFloat(balance).toFixed(2) 
                : '--';
            console.log('更新下拉菜单余额显示:', balanceStr);
            $('.wallet-balance').text(balanceStr);
            
            // 更新钱包地址显示
            if (this.address) {
                const shortAddress = this.formatAddress(this.address);
                console.log('更新钱包地址显示:', shortAddress, `(完整地址: ${this.address} )`);
                $('.wallet-address-full').text(this.address);
                $('.wallet-address').text(shortAddress);
            }
        } catch (error) {
            console.error('更新钱包余额显示出错:', error);
            // 出错时不抛出异常，保持UI稳定
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
            
            console.log('[updateAssetsUI] 当前资产数据:', assets);
            
            // 检查是否有资产
            if (!assets || !Array.isArray(assets) || assets.length === 0) {
                console.log('[updateAssetsUI] 没有资产可显示');
                const emptyItem = document.createElement('li');
                emptyItem.className = 'text-muted text-center py-1';
                emptyItem.style.fontSize = '11px';
                emptyItem.textContent = 'No Assets Found';
                assetsList.appendChild(emptyItem);
                
                // 仍然显示资产容器，只是显示"没有资产"的信息
                const assetContainers = document.querySelectorAll('.assets-container, .user-assets');
                assetContainers.forEach(container => {
                    if (container) {
                        container.style.display = 'block';
                    }
                });
                return;
            }
            
            console.log(`[updateAssetsUI] 显示 ${assets.length} 个资产`);
            
            // 创建文档片段来优化DOM操作
            const fragment = document.createDocumentFragment();
            
            // 遍历资产并创建列表项
            assets.forEach(asset => {
                // 提取资产数据
                const assetId = asset.asset_id || asset.id || 0;
                const assetName = asset.name || 'Unknown Asset';
                const quantity = asset.quantity || asset.amount || asset.holding_amount || 0;
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
            
            // 显示所有资产容器
            const assetContainers = document.querySelectorAll('.assets-container, .user-assets');
            assetContainers.forEach(container => {
                if (container) {
                    container.style.display = 'block';
                }
            });
            
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
            
            // 如果已有钱包选择器打开，先关闭
            this.closeWalletSelector();
            
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
                this.closeWalletSelector();
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
                    this.closeWalletSelector();
                    
                    // 在移动设备上设置从钱包应用返回的标记
                    if (this.isMobile()) {
                        sessionStorage.setItem('returningFromWalletApp', 'true');
                        this.pendingWalletAppOpen = true;
                        this.pendingWalletType = wallet.type;
                    }
                    
                    // 调用连接方法
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
            walletSelector.addEventListener('click', (e) => {
                if (e.target === walletSelector) {
                    this.closeWalletSelector();
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

    /**
      * 关闭钱包选择器
      */
     closeWalletSelector() {
         try {
             const walletSelector = document.getElementById('walletSelector');
             if (walletSelector) {
                 walletSelector.remove();
                 console.log('钱包选择器已关闭');
                 
                 // 发送钱包选择器关闭事件
                 document.dispatchEvent(new CustomEvent('walletSelectorClosed'));
                 return true;
             }
             return false;
            } catch (error) {
             console.error('关闭钱包选择器时出错:', error);
             return false;
        }
    },

    /**
     * 显示钱包选择对话框
     * 这是为了兼容旧代码，实际上是调用openWalletSelector方法
     * @returns {Promise<string|null>} 选中的钱包类型或null（取消选择）
     */
    showWalletOptions() {
        return new Promise((resolve, reject) => {
            try {
                // 调用openWalletSelector打开钱包选择器
                this.openWalletSelector();
                
                // 监听钱包连接事件
                const walletConnectedListener = (e) => {
                    if (e && e.detail && e.detail.walletType) {
                        document.removeEventListener('walletConnected', walletConnectedListener);
                        resolve(e.detail.walletType);
                    }
                };
                
                // 添加事件监听器
                document.addEventListener('walletConnected', walletConnectedListener);
                
                // 30秒后自动拒绝，避免Promise永远不解决
                setTimeout(() => {
                    document.removeEventListener('walletConnected', walletConnectedListener);
                    reject(new Error('选择钱包超时'));
                }, 30000);
                    } catch (error) {
                console.error('显示钱包选择对话框失败:', error);
                reject(error);
            }
        });
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
                    
                    // 更新资产UI
                    this.updateAssetsUI();
                    
                    return formattedAssets;
                } else {
                    console.warn('[getUserAssets] API响应不成功:', response.status, response.statusText);
                    this.assets = [];
                    this.updateAssetsUI();
                    return [];
                }
            } catch (error) {
                console.warn('[getUserAssets] API请求失败:', error);
                this.assets = [];
                this.updateAssetsUI();
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
            showError('连接Solflare钱包失败: ' + (error.message || '未知错误'));
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

/**
 * 连接到Phantom钱包
 * @param {boolean} isReconnect - 是否是重新连接操作
 * @returns {Promise<boolean>} 连接是否成功
 */
async connectPhantom(isReconnect = false) {
    console.log('尝试连接Phantom钱包' + (isReconnect ? ' (重连)' : ''));
    
    try {
        // 检查是否是从钱包App返回
        const returningFromWallet = this.checkIfReturningFromWalletApp('phantom');
        if (returningFromWallet && !isReconnect) {
            console.log('检测到从Phantom钱包App返回，尝试恢复连接状态');
            
            // 移动设备上，如果浏览器不支持直接连接，返回的时候可能没有自动连接
            // 我们需要尝试通过状态恢复连接，或给出适当提示
            if (this.isMobile() && (!window.solana || !window.solana.isPhantom)) {
                console.warn('从Phantom钱包返回，但浏览器不支持钱包连接');
                showError('钱包连接未完成，请尝试使用Phantom App内置浏览器访问');
                return false;
            }
        }
        
        // 增强型Phantom钱包检测 - 确保即使延迟加载也能正确检测
        if (!window.solana || !window.solana.isPhantom) {
            console.log('暂未检测到Phantom钱包，尝试等待...');
            
            // 如果是重连操作，我们尝试等待一小段时间再检测
            if (isReconnect || this.walletType === 'phantom') {
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                if (!window.solana || !window.solana.isPhantom) {
                    console.log('等待后仍未检测到Phantom钱包');
                    
                    // 如果有localStorage存储的Phantom地址，我们保持UI状态但不报错
                    if (isReconnect && localStorage.getItem('walletAddress') && localStorage.getItem('walletType') === 'phantom') {
                        console.log('使用localStorage存储的钱包状态');
                        return false;
                    }
                    
                    if (!isReconnect) {
                        if (this.isMobile()) {
                            showError('请在Phantom App中打开本页面，或使用桌面浏览器');
                        } else {
                            showError('请安装Phantom钱包浏览器扩展');
                        }
                    }
                    return false;
                } else {
                    console.log('等待后成功检测到Phantom钱包');
                }
            } else {
                // 非重连模式下，检查是否有Phantom地址存储在localStorage
                if (localStorage.getItem('walletType') === 'phantom' && localStorage.getItem('walletAddress')) {
                    console.log('虽然未检测到Phantom钱包，但有存储的钱包地址，保持状态');
                    this.connected = true;
                    this.walletType = 'phantom';
                    this.address = localStorage.getItem('walletAddress');
                    this.updateUI();
                    return false;
                }
                
                console.error('Phantom钱包未安装或未加载');
                
                if (!isReconnect) {
                    if (this.isMobile()) {
                        showError('请在Phantom App中打开本页面，或使用桌面浏览器');
                    } else {
                        showError('请安装Phantom钱包浏览器扩展');
                    }
                }
                return false;
            }
        }
        
        console.log('Phantom钱包状态:', {
            'isPhantom': window.solana.isPhantom,
            'isConnected': window.solana.isConnected,
            'publicKey': window.solana.publicKey ? window.solana.publicKey.toString() : null
        });
        
        // 如果已经连接，可以直接使用现有连接
        if (window.solana.isConnected && window.solana.publicKey) {
            console.log('Phantom钱包已经连接，使用现有连接');
            return this.afterSuccessfulConnection(window.solana.publicKey.toString(), 'phantom', window.solana);
        }
        
        // 请求连接到钱包，设置超时
        let connectionTimeout;
        try {
            const timeoutPromise = new Promise((_, reject) => {
                connectionTimeout = setTimeout(() => {
                    reject(new Error('连接Phantom钱包超时'));
                }, 20000); // 20秒超时
            });
            
            console.log('正在请求Phantom钱包连接...');
            const response = await Promise.race([
                window.solana.connect({ onlyIfTrusted: false }),
                timeoutPromise
            ]);
            
            clearTimeout(connectionTimeout);
            
            console.log('Phantom连接响应:', response);
            
            if (!response || !response.publicKey) {
                console.error('无法获取Phantom钱包公钥');
                if (!isReconnect) {
                    showError('连接Phantom钱包失败: 无法获取公钥');
                }
                return false;
            }
            
            console.log('成功获取Phantom公钥:', response.publicKey.toString());
            
            // 确保设置钱包已连接状态
            window.solana.isConnected = true;
            
            // 设置事件监听器
            this.setupPhantomListeners();
            
            // 连接成功，使用afterSuccessfulConnection方法处理
            return this.afterSuccessfulConnection(response.publicKey.toString(), 'phantom', window.solana);
        } catch (connectError) {
            clearTimeout(connectionTimeout);
            console.error('连接Phantom钱包时出错:', connectError);
            
            // 如果是用户拒绝连接，给出特定提示
            if (connectError.code === 4001) {
                if (!isReconnect) {
                    showError('用户拒绝了钱包连接请求');
                }
                return false;
            }
            
            // 如果是移动设备并且从钱包App返回，给出更明确的提示
            if (this.isMobile() && returningFromWallet) {
                showError('请确保在Phantom App中授权连接');
                return false;
            }
            
            // 尝试再次连接，但使用另一种方式
            try {
                console.log('尝试备用连接方法...');
                // 先尝试仅受信任的连接，这在某些情况下更容易成功
                const retryResponse = await window.solana.connect({ onlyIfTrusted: true }).catch(() => null);
                
                if (retryResponse && retryResponse.publicKey) {
                    console.log('使用onlyIfTrusted方式连接成功');
                    return this.afterSuccessfulConnection(retryResponse.publicKey.toString(), 'phantom', window.solana);
                }
                
                // 如果上面方式失败，再使用常规方式
                const fallbackResponse = await window.solana.connect({ onlyIfTrusted: false });
                
                if (!fallbackResponse || !fallbackResponse.publicKey) {
                    throw new Error('备用连接方法失败');
                }
                
                console.log('备用连接方法成功，公钥:', fallbackResponse.publicKey.toString());
                return this.afterSuccessfulConnection(fallbackResponse.publicKey.toString(), 'phantom', window.solana);
            } catch (retryError) {
                console.error('备用连接方法也失败:', retryError);
                if (!isReconnect) {
                    if (this.isMobile()) {
                        showError('无法连接到Phantom钱包，请确保已允许连接授权');
                    } else {
                        showError('无法连接到Phantom钱包，请确保已安装并授权');
                    }
                }
                return false;
            }
        }
    } catch (error) {
        console.error('连接Phantom钱包时出错:', error);
        console.error('错误详情:', {
            name: error.name,
            message: error.message,
            code: error.code,
            stack: error.stack
        });
        
        if (!isReconnect) {
            showError('连接Phantom钱包失败: ' + (error.message || '未知错误'));
        }
        return false;
    }
},

/**
 * 检查是否从钱包App返回
 * @param {string} walletType - 钱包类型
 * @returns {boolean} 是否从钱包App返回
 */
checkIfReturningFromWalletApp(walletType) {
    try {
        // 检查localStorage中的标记
        const pendingWalletType = localStorage.getItem('pendingWalletType');
        const pendingWalletConnection = localStorage.getItem('pendingWalletConnection');
        const pendingWalletTimestamp = localStorage.getItem('pendingWalletTimestamp');
        const lastConnectionUrl = localStorage.getItem('lastConnectionAttemptUrl');
        
        // 检查是否与当前情况匹配
        const isReturning = pendingWalletType === walletType &&
                           pendingWalletConnection === 'true' &&
                           pendingWalletTimestamp &&
                           lastConnectionUrl === window.location.href;
        
        if (isReturning) {
            console.log(`检测到从${walletType}钱包App返回`);
            
            // 检查时间戳是否在合理范围内（5分钟内）
            const timestamp = parseInt(pendingWalletTimestamp, 10);
            const now = Date.now();
            const timeDiff = now - timestamp;
            
            if (timeDiff > 5 * 60 * 1000) {
                console.log('返回时间超过5分钟，可能不是从钱包App直接返回');
                return false;
            }
            
            // 清除这些标记，避免重复处理
            localStorage.removeItem('pendingWalletType');
            localStorage.removeItem('pendingWalletConnection');
            localStorage.removeItem('pendingWalletTimestamp');
            localStorage.removeItem('lastConnectionAttemptUrl');
            
            return true;
        }
        
        return false;
    } catch (error) {
        console.error('检查钱包App返回状态出错:', error);
        return false;
    }
},

/**
     * 连接到以太坊钱包（MetaMask等）
     * @param {boolean} isReconnect - 是否是重新连接
     * @returns {Promise<boolean>} 连接是否成功
     */
    async connectEthereum(isReconnect = false) {
        console.log('尝试连接以太坊钱包' + (isReconnect ? ' (重连)' : ''));
        
        try {
            // 检查以太坊对象是否存在
            if (!window.ethereum) {
                console.error('MetaMask或其他以太坊钱包未安装');
                if (!isReconnect) {
                    showError('请安装MetaMask或其他以太坊钱包');
                }
                return false;
            }
            
            const provider = window.ethereum;
            
            // 创建Web3实例
            const web3 = new Web3(provider);
            
            // 连接前检查chainId，确保是主网或测试网
            try {
                const chainId = await web3.eth.getChainId();
                console.log('当前链ID:', chainId);
                this.chainId = chainId;
            } catch (chainError) {
                console.warn('无法获取链ID:', chainError);
            }
            
            // 请求用户账户授权
            console.log('请求账户授权...');
            const accounts = await provider.request({ method: 'eth_requestAccounts' });
            
            if (!accounts || accounts.length === 0) {
                console.error('用户拒绝连接或无法获取账户');
                if (!isReconnect) {
                    showError('用户拒绝连接或无法获取账户');
                }
                return false;
            }
            
            // 连接成功，使用afterSuccessfulConnection方法处理
            return this.afterSuccessfulConnection(accounts[0], 'ethereum', provider);
        } catch (error) {
            console.error('连接以太坊钱包时出错:', error);
            if (!isReconnect) {
                showError('连接以太坊钱包失败: ' + (error.message || '未知错误'));
            }
            return false;
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
     * 格式化钱包地址为友好显示形式
     * @param {string} address - 钱包地址
     * @returns {string} 格式化后的地址
     */
    formatAddress(address) {
        if (!address) return '';
        
        // 检查地址长度，区分以太坊和Solana地址
        if (address.startsWith('0x')) {
            // 以太坊地址: 0x1234...5678
            return address.substring(0, 6) + '...' + address.substring(address.length - 4);
        } else {
            // Solana地址: ABCD...WXYZ
            return address.substring(0, 4) + '...' + address.substring(address.length - 4);
        }
    },

    /**
     * 复制钱包地址到剪贴板并显示成功提示
     * 对接base.html中定义的全局复制方法
     */
    copyWalletAddress() {
        try {
            if (!this.address) {
                console.warn('没有可复制的钱包地址');
                return;
            }
            
            console.log('复制钱包地址:', this.address);
            
            // 使用现代Clipboard API复制文本
            navigator.clipboard.writeText(this.address).then(() => {
                console.log('已复制地址到剪贴板');
                // 显示成功提示
                this.showCopySuccess();
            }).catch(err => {
                console.error('Clipboard API失败:', err);
                
                // 尝试备用方法
                const tempInput = document.createElement('input');
                tempInput.value = this.address;
                document.body.appendChild(tempInput);
                tempInput.select();
                document.execCommand('copy');
                document.body.removeChild(tempInput);
                
                // 显示成功提示
                this.showCopySuccess();
            });
        } catch (error) {
            console.error('复制地址出错:', error);
            // 尝试调用全局错误提示函数
            if (typeof showError === 'function') {
                showError('复制地址失败');
            }
        }
    },
    
    /**
     * 显示地址复制成功提示
     */
    showCopySuccess() {
        // 1. 尝试使用复制成功元素显示
        const successMsg = document.getElementById('copyAddressSuccess');
        if (successMsg) {
            successMsg.style.opacity = '1';
            setTimeout(() => {
                successMsg.style.opacity = '0';
            }, 3000); // 延长到3秒
            
            // 2. 临时改变地址显示元素样式以给予视觉反馈
            const addressDisplay = document.getElementById('walletAddressDisplay');
            if (addressDisplay) {
                // 添加背景色变化效果
                addressDisplay.style.backgroundColor = '#e0f7e0';
                addressDisplay.style.borderColor = '#28a745';
                addressDisplay.style.transition = 'all 0.3s ease';
                
                // 4秒后恢复原样
                setTimeout(() => {
                    addressDisplay.style.backgroundColor = '#f5f8ff';
                    addressDisplay.style.borderColor = 'transparent';
                }, 4000);
            }
        }
    },
    
    /**
     * 转账代币到指定地址
     * @param {string} tokenSymbol 代币符号，如'USDC'
     * @param {string} to 接收地址
     * @param {number} amount 转账金额
     * @returns {Promise<{success: boolean, txHash: string, error: string}>} 交易结果
     */
    async transferToken(tokenSymbol, to, amount) {
        try {
            console.log(`准备转账 ${amount} ${tokenSymbol} 到 ${to}`);
            
            // 检查钱包连接状态
            if (!this.connected || !this.address) {
                throw new Error('钱包未连接');
            }
            
            // 根据钱包类型执行不同的转账逻辑
            if (this.walletType === 'phantom' || this.walletType === 'solana') {
                // Phantom钱包转账
                return await this.transferSolanaToken(tokenSymbol, to, amount);
            } else if (this.walletType === 'ethereum') {
                // 以太坊钱包转账
                return await this.transferEthereumToken(tokenSymbol, to, amount);
            } else {
                throw new Error(`不支持的钱包类型: ${this.walletType}`);
            }
        } catch (error) {
            console.error('转账失败:', error);
            return {
                success: false,
                error: error.message || '转账失败'
            };
        }
    },
    
    /**
     * 使用Solana钱包发送SPL代币(USDC)
     * @param {string} tokenSymbol 代币符号(USDC)
     * @param {string} to 接收地址
     * @param {number} amount 转账金额
     * @returns {Promise<{success: boolean, txHash: string, error: string}>} 交易结果
     */
    async transferSolanaToken(tokenSymbol, to, amount) {
        try {
            console.log(`开始执行真实Solana ${tokenSymbol}转账，接收地址: ${to}, 金额: ${amount}`);
            
            // 1. 确保Solana库已加载
            await this.ensureSolanaLibraries();
            
            // 确保SPL Token库的程序ID已正确初始化
            if (window.splToken && typeof window.splToken.initializeProgramIds === 'function') {
                window.splToken.initializeProgramIds();
            }
            
            // 2. 获取钱包连接信息
            if (!window.solana || !window.solana.isConnected) {
                throw new Error('Solana钱包未连接，请先连接钱包');
            }
            
            // 3. 使用环境变量或配置中的mint地址
            let mintAddress = null;
            
            if (tokenSymbol === 'USDC') {
                // 从API获取USDC的mint地址
                const paymentSettingsResponse = await fetch('/api/service/config/payment_settings');
                if (!paymentSettingsResponse.ok) {
                    throw new Error('获取支付配置失败');
                }
                
                const paymentSettings = await paymentSettingsResponse.json();
                if (!paymentSettings || !paymentSettings.usdc_mint) {
                    throw new Error('支付配置中缺少USDC Mint地址');
                }
                
                mintAddress = paymentSettings.usdc_mint;
                console.log('使用支付配置中的USDC Mint地址:', mintAddress);
            } else {
                throw new Error(`不支持的代币: ${tokenSymbol}`);
            }
            
            const usdcMint = new window.solanaWeb3.PublicKey(mintAddress);
            const fromPubkey = new window.solanaWeb3.PublicKey(this.address);
            const toPubkey = new window.solanaWeb3.PublicKey(to);
            
            // 4. 获取一个连接到Solana网络的连接对象，使用代理API减少直接RPC依赖
            console.log('获取代币账户...');
            
            // 指定正确的程序ID
            const tokenProgramId = new window.solanaWeb3.PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
            const associatedTokenProgramId = new window.solanaWeb3.PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL");
            const systemProgramId = new window.solanaWeb3.PublicKey("11111111111111111111111111111111");
            
            // 7. 获取最新区块哈希
            console.log('获取区块哈希...');
            const latestBlockhashResponse = await fetch('/api/solana/get_latest_blockhash');
            if (!latestBlockhashResponse.ok) {
                throw new Error('获取区块哈希失败');
            }
            
            const blockHashResult = await latestBlockhashResponse.json();
            
            if (!blockHashResult.success) {
                throw new Error(`无法获取区块哈希: ${blockHashResult.error}`);
            }
            
            // 9. 构建交易
            const transaction = new solanaWeb3.Transaction();
            transaction.recentBlockhash = blockHashResult.blockhash;
            transaction.feePayer = fromPubkey;
            
            // 获取发送方的代币账户
            const fromTokenAccount = await splToken.getAssociatedTokenAddress(
                usdcMint,
                fromPubkey,
                false,
                tokenProgramId,
                associatedTokenProgramId
            );
            
            // 获取接收方的代币账户
            const toTokenAccount = await splToken.getAssociatedTokenAddress(
                usdcMint,
                toPubkey,
                false,
                tokenProgramId,
                associatedTokenProgramId
            );
            
            // 检查接收方账户
            console.log('检查接收方账户...');
            // 使用服务器API检查账户，而不是直接连接Solana节点
            const checkAccountResponse = await fetch(`/api/solana/check_account?address=${toTokenAccount.toString()}`);
            if (!checkAccountResponse.ok) {
                throw new Error('检查接收方账户失败');
            }
            
            const checkAccountResult = await checkAccountResponse.json();
            const toTokenAccountExists = checkAccountResult.exists;
            
            // 如果接收方代币账户不存在，添加创建指令
            if (!toTokenAccountExists) {
                console.log('接收方代币账户不存在，添加创建指令');
                
                try {
                    // 修复：确保使用正确的参数顺序创建关联代币账户指令
                    const createAtaInstruction = splToken.createAssociatedTokenAccountInstruction(
                        fromPubkey,                // payer 
                        toTokenAccount,            // associatedToken
                        toPubkey,                  // owner
                        usdcMint,                  // mint
                        tokenProgramId,            // 可选：程序ID，默认是TOKEN_PROGRAM_ID
                        associatedTokenProgramId   // 可选：关联程序ID，默认是ASSOCIATED_TOKEN_PROGRAM_ID
                    );
                    
                    transaction.add(createAtaInstruction);
                } catch (ataError) {
                    console.error('创建ATA指令错误:', ataError);
                    throw new Error(`创建接收方账户失败: ${ataError.message}`);
                }
            }
            
            // 10. 准备转账金额（USDC有6位小数）
            const lamportsAmount = Math.round(amount * 1000000); // 转换为USDC的最小单位
            
            // 11. 添加转账指令
            console.log('添加转账指令...');
            try {
                // 修复: 使用SPL库提供的最新方法，不再需要手动检查所有者权限
                const transferInstruction = splToken.createTransferCheckedInstruction(
                    fromTokenAccount,           // 源代币账户
                    usdcMint,                   // 代币Mint地址
                    toTokenAccount,             // 目标代币账户  
                    fromPubkey,                 // 源代币账户的所有者（必须是签名者）
                    BigInt(lamportsAmount),     // 金额，使用BigInt类型
                    6,                          // 小数位数（USDC为6位）
                    []                          // 多重签名者（空数组表示没有）
                );
                
                transaction.add(transferInstruction);
            } catch (instructionError) {
                console.error('创建转账指令错误:', instructionError);
                throw new Error(`创建转账指令失败: ${instructionError.message}`);
            }
            
            // 12. 签名交易
            console.log('请求钱包签名交易...');
            let signedTransaction;
            
            try {
                signedTransaction = await window.solana.signTransaction(transaction);
            } catch (signError) {
                console.error('签名交易失败:', signError);
                throw new Error(`签名失败: ${signError.message || '用户拒绝交易'}`);
            }
            
            // 13. 通过服务器API发送交易，而不是直接发送到Solana网络
            console.log('通过服务器API发送已签名交易...');
            
            const transactionBuffer = signedTransaction.serialize();
            const transactionBase64 = window.btoa(String.fromCharCode(...transactionBuffer));
            
            const submitResponse = await fetch('/api/solana/submit_transaction', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    transaction: transactionBase64,
                    skipPreflight: false // 启用预检查以捕获错误
                })
            });
            
            if (!submitResponse.ok) {
                const errorText = await submitResponse.text();
                console.error('发送交易失败:', errorText);
                throw new Error(`发送交易失败: ${errorText}`);
            }
            
            const submitResult = await submitResponse.json();
            if (!submitResult.success) {
                throw new Error(`链上转账失败: ${submitResult.error || '未知错误'}`);
            }
            
            const signature = submitResult.signature;
            console.log('交易已发送，签名:', signature);
            
            // 14. 显示交易状态 
            this._showTransactionStatus(signature, tokenSymbol, amount, to);
            
            // 15. 返回成功结果
            return {
                success: true,
                txHash: signature
            };
        } catch (error) {
            console.error('Solana链上转账失败:', error);
            return {
                success: false,
                error: `转账失败: ${error.message || '未知错误'}`
            };
        }
    },
    
    /**
     * 确保Solana库已经正确加载
     */
    async ensureSolanaLibraries() {
        // 检查Solana Web3.js库
        if (!window.solanaWeb3) {
            if (window.solanaWeb3js) {
                window.solanaWeb3 = window.solanaWeb3js;
            } else if (window.solana && window.solana.web3) {
                window.solanaWeb3 = window.solana.web3;
            } else {
                console.log('未找到已加载的Solana Web3.js库，尝试加载...');
                await this.loadSolanaLibraries();
            }
        }
        
        // 检查SPL Token库
        if (!window.splToken) {
            if (window.spl && window.spl.token) {
                window.splToken = window.spl.token;
                console.log('已从window.spl.token初始化splToken库');
            } else {
                console.log('未找到已加载的SPL Token库，尝试加载...');
                await this.loadSolanaLibraries();
            }
        }
        
        // 最终检查
        if (!window.solanaWeb3 || !window.splToken) {
            throw new Error('无法加载必要的Solana区块链库，请刷新页面重试');
        }

        // 确保程序ID已初始化为PublicKey对象
        if (window.splToken.initializeProgramIds) {
            window.splToken.initializeProgramIds();
            
            // 额外检查，如果程序ID仍然是字符串，则手动创建PublicKey对象
            if (window.splToken.TOKEN_PROGRAM_ID && typeof window.splToken.TOKEN_PROGRAM_ID === 'string') {
                window.splToken.TOKEN_PROGRAM_ID = new window.solanaWeb3.PublicKey(window.splToken.TOKEN_PROGRAM_ID);
            }
            
            if (window.splToken.ASSOCIATED_TOKEN_PROGRAM_ID && typeof window.splToken.ASSOCIATED_TOKEN_PROGRAM_ID === 'string') {
                window.splToken.ASSOCIATED_TOKEN_PROGRAM_ID = new window.solanaWeb3.PublicKey(window.splToken.ASSOCIATED_TOKEN_PROGRAM_ID);
            }
        }
        
        console.log('Solana库已准备就绪:', {
            'solanaWeb3': !!window.solanaWeb3,
            'splToken': !!window.splToken,
            'hasGetAssociatedTokenAddress': !!(window.splToken && window.splToken.getAssociatedTokenAddress),
            'TOKEN_PROGRAM_ID类型': typeof window.splToken.TOKEN_PROGRAM_ID,
            'ASSOCIATED_TOKEN_PROGRAM_ID类型': typeof window.splToken.ASSOCIATED_TOKEN_PROGRAM_ID
        });
    },
    
    /**
     * 加载Solana相关库
     * @private
     */
    async loadSolanaLibraries() {
        return new Promise((resolve, reject) => {
            try {
                // 加载 solana/web3.js
                if (!window.solanaWeb3) {
                    const web3Script = document.createElement('script');
                    // 优先使用本地文件
                    web3Script.src = '/static/js/contracts/solana-web3.iife.min.js';
                    web3Script.onload = () => {
                        console.log('Solana Web3.js 库已从本地加载');
                        
                        // 确保全局变量正确设置
                        if (window.solanaWeb3js) {
                            window.solanaWeb3 = window.solanaWeb3js;
                        } else if (window.solana && window.solana.web3) {
                            window.solanaWeb3 = window.solana.web3;
                        }
                        
                        // 加载 SPL Token 库
                        this.loadSplTokenLibrary().then(resolve).catch(reject);
                    };
                    web3Script.onerror = (e) => {
                        console.error('加载本地Solana Web3.js库失败, 尝试CDN:', e);
                        // 尝试从CDN加载
                        const cdnScript = document.createElement('script');
                        cdnScript.src = 'https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js';
                        cdnScript.onload = () => {
                            console.log('Solana Web3.js 库已从CDN加载');
                            if (window.solanaWeb3js) {
                                window.solanaWeb3 = window.solanaWeb3js;
                            } else if (window.solana && window.solana.web3) {
                                window.solanaWeb3 = window.solana.web3;
                            }
                            this.loadSplTokenLibrary().then(resolve).catch(reject);
                        };
                        cdnScript.onerror = (cdnErr) => {
                            console.error('从CDN加载Solana Web3.js库失败:', cdnErr);
                            reject(new Error('无法加载Solana Web3.js库'));
                        };
                        document.head.appendChild(cdnScript);
                    };
                    document.head.appendChild(web3Script);
                } else {
                    // Web3.js已加载，继续加载SPL Token
                    this.loadSplTokenLibrary().then(resolve).catch(reject);
                }
            } catch (error) {
                console.error('加载Solana库出错:', error);
                reject(error);
            }
        });
    },
    
    /**
     * 加载SPL Token库
     * @private
     */
    async loadSplTokenLibrary() {
        return new Promise((resolve, reject) => {
            try {
                // 检查是否已加载
                if (window.splToken) {
                    console.log('SPL Token已加载，直接使用现有实例');
                    return resolve();
                }
                
                // 检查是否可以从现有变量中获取
                if (window.spl && window.spl.token) {
                    window.splToken = window.spl.token;
                    console.log('已从window.spl.token初始化splToken库');
                    return resolve();
                }
                
                // 获取库加载状态
                const isPreparing = document.getElementById('spl-token-loading') !== null;
                const isError = document.getElementById('spl-token-error') !== null;
                
                // 如果已在加载中，等待结果
                if (isPreparing) {
                    console.log('SPL Token库正在加载中，等待完成...');
                    
                    // 等待加载完成
                    const checkInterval = setInterval(() => {
                        if (window.splToken || (window.spl && window.spl.token)) {
                            clearInterval(checkInterval);
                            window.splToken = window.splToken || window.spl.token;
                            console.log('等待后，SPL Token库已加载完成');
                            resolve();
                        } else if (isError) {
                            clearInterval(checkInterval);
                            reject(new Error('SPL Token库加载失败(检测到错误)'));
                        }
                    }, 300);
                    
                    // 设置超时
                    setTimeout(() => {
                        clearInterval(checkInterval);
                        reject(new Error('SPL Token库加载超时'));
                    }, 10000);
                    
                    return;
                }
                
                console.log('开始加载SPL Token库...');
                
                // 创建标记元素，避免重复加载
                const loadingMark = document.createElement('div');
                loadingMark.id = 'spl-token-loading';
                loadingMark.style.display = 'none';
                document.body.appendChild(loadingMark);
                
                // 尝试多种CDN源加载库
                const cdnUrls = [
                    '/static/js/contracts/spl-token.iife.min.js', // 本地备份优先
                    'https://unpkg.com/@solana/spl-token@0.3.8/lib/index.iife.min.js',
                    'https://cdn.jsdelivr.net/npm/@solana/spl-token@0.3.8/lib/index.iife.min.js',
                    'https://raw.githack.com/solana-labs/solana-program-library/master/token/js/dist/index.iife.min.js'
                ];
                
                let loadAttempt = 0;
                
                // 尝试加载库的函数
                const attemptLoad = (urlIndex) => {
                    if (urlIndex >= cdnUrls.length) {
                        const errorMark = document.createElement('div');
                        errorMark.id = 'spl-token-error';
                        errorMark.style.display = 'none';
                        document.body.appendChild(errorMark);
                        
                        // 所有尝试都失败了
                        document.body.removeChild(loadingMark);
                        reject(new Error('所有SPL Token库加载源都失败'));
                        return;
                    }
                    
                    loadAttempt++;
                    console.log(`尝试加载SPL Token库 (尝试 ${loadAttempt}/${cdnUrls.length}): ${cdnUrls[urlIndex]}`);
                    
                    const splTokenScript = document.createElement('script');
                    splTokenScript.src = cdnUrls[urlIndex];
                    splTokenScript.async = true;
                    
                    // 设置超时处理
                    let timeoutId = setTimeout(() => {
                        console.warn(`加载 ${cdnUrls[urlIndex]} 超时，尝试下一个源`);
                        attemptLoad(urlIndex + 1);
                    }, 10000);
                    
                    // 成功处理
                    splTokenScript.onload = () => {
                        clearTimeout(timeoutId);
                        console.log(`SPL Token库已从 ${cdnUrls[urlIndex]} 加载`);
                        
                        // 延迟检查库是否实际加载成功
                        setTimeout(() => {
                            // 设置全局变量
                            if (window.spl && window.spl.token) {
                                window.splToken = window.spl.token;
                                console.log('已从window.spl.token初始化splToken库');
                                
                                // 检查关键方法是否存在
                                if (!window.splToken.getAssociatedTokenAddress) {
                                    console.error('SPL Token库已加载但找不到getAssociatedTokenAddress方法');
                                    
                                    // 使用备选方案
                                    if (window.splToken.ASSOCIATED_TOKEN_PROGRAM_ID) {
                                        console.log('找到ASSOCIATED_TOKEN_PROGRAM_ID，尝试自定义实现getAssociatedTokenAddress');
                                        
                                        // 自定义实现
                                        window.splToken.getAssociatedTokenAddress = async function(mint, owner) {
                                            const { PublicKey, SystemProgram } = window.solanaWeb3;
                                            return PublicKey.findProgramAddressSync(
                                                [
                                                    owner.toBuffer(),
                                                    window.splToken.TOKEN_PROGRAM_ID.toBuffer(),
                                                    mint.toBuffer(),
                                                ],
                                                window.splToken.ASSOCIATED_TOKEN_PROGRAM_ID
                                            )[0];
                                        };
                                        
                                        console.log('成功实现自定义getAssociatedTokenAddress');
                                    } else {
                                        document.body.removeChild(loadingMark);
                                        attemptLoad(urlIndex + 1);
                                        return;
                                    }
                                }
                                
                                // 成功加载
                                document.body.removeChild(loadingMark);
                                resolve();
                            } else {
                                console.warn('SPL Token库加载后window.spl.token不可用，尝试下一个源');
                                attemptLoad(urlIndex + 1);
                            }
                        }, 500);
                    };
                    
                    // 错误处理
                    splTokenScript.onerror = (e) => {
                        clearTimeout(timeoutId);
                        // 特别检查本地文件加载错误
                        if (urlIndex === 0) {
                            console.error(`本地SPL Token库加载失败:`, e);
                            console.warn(`请确保服务器上存在文件: ${cdnUrls[0]}`); 
                            console.warn(`可以通过命令创建: mkdir -p app/static/js/contracts/ && curl -o app/static/js/contracts/spl-token.iife.min.js https://unpkg.com/@solana/spl-token@0.3.8/lib/index.iife.min.js`);
                        } else {
                            console.error(`从 ${cdnUrls[urlIndex]} 加载SPL Token库失败:`, e);
                        }
                        attemptLoad(urlIndex + 1);
                    };
                    
                    document.head.appendChild(splTokenScript);
                };
                
                // 开始尝试
                attemptLoad(0);
                
            } catch (error) {
                console.error('加载SPL Token库出错:', error);
                reject(error);
            }
        });
    },
    
    /**
     * 显示交易状态
     * @param {string} signature 交易签名
     * @param {string} tokenSymbol 代币符号
     * @param {number} amount 转账金额
     * @param {string} to 接收地址
     * @private
     */
    _showTransactionStatus(signature, tokenSymbol, amount, to) {
        // 使用SweetAlert2显示交易状态
        if (window.Swal) {
            Swal.fire({
                title: '交易处理中',
                html: `
                    <div class="text-center">
                        <div class="mb-3">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                        <p>您的 ${amount} ${tokenSymbol} 转账正在处理中...</p>
                        <p class="small text-muted">
                            交易签名: <a href="https://solscan.io/tx/${signature}" target="_blank">${signature.substring(0, 8)}...${signature.substring(signature.length - 8)}</a>
                        </p>
                        <p class="small">请勿关闭此窗口，交易确认通常需要几秒钟到几分钟不等</p>
                    </div>
                `,
                showConfirmButton: false,
                allowOutsideClick: false,
                didOpen: () => {
                    // 启动轮询检查交易状态
                    this._pollTransactionStatus(signature, tokenSymbol, amount, to);
                }
            });
        } else {
            // 如果没有SweetAlert2，使用简单的alert
            alert(`交易已提交，签名: ${signature}`);
        }
    },
    
    /**
     * 轮询检查交易状态
     * @param {string} signature 交易签名
     * @param {string} tokenSymbol 代币符号
     * @param {number} amount 转账金额
     * @param {string} to 接收地址
     * @private
     */
    async _pollTransactionStatus(signature, tokenSymbol, amount, to) {
        let retryCount = 0;
        const maxRetries = 30;
        const pollInterval = 3000; // 3秒
        
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/blockchain/solana/check-transaction?signature=${signature}`);
                if (!response.ok) {
                    throw new Error('检查交易状态失败');
                }
                
                const result = await response.json();
                
                if (result.confirmed) {
                    // 交易确认成功
                    if (window.Swal) {
                        Swal.fire({
                            title: '交易成功',
                            html: `
                                <div class="text-center">
                                    <div class="mb-3">
                                        <i class="fas fa-check-circle text-success" style="font-size: 3rem;"></i>
                                    </div>
                                    <p>您已成功转账 ${amount} ${tokenSymbol}</p>
                                    <p class="small text-muted">
                                        交易签名: <a href="https://solscan.io/tx/${signature}" target="_blank">${signature.substring(0, 8)}...${signature.substring(signature.length - 8)}</a>
                                    </p>
                                </div>
                            `,
                            icon: 'success',
                            confirmButtonText: '确定'
                        });
                    }
                    return;
                }
                
                // 交易失败
                if (result.error) {
                    if (window.Swal) {
                        Swal.fire({
                            title: '交易失败',
                            html: `
                                <div class="text-center">
                                    <div class="mb-3">
                                        <i class="fas fa-times-circle text-danger" style="font-size: 3rem;"></i>
                                    </div>
                                    <p>转账失败: ${result.error}</p>
                                    <p class="small text-muted">
                                        交易签名: <a href="https://solscan.io/tx/${signature}" target="_blank">${signature.substring(0, 8)}...${signature.substring(signature.length - 8)}</a>
                                    </p>
                                </div>
                            `,
                            icon: 'error',
                            confirmButtonText: '确定'
                        });
                    }
                    return;
                }
                
                // 交易仍在处理中
                retryCount++;
                if (retryCount < maxRetries) {
                    setTimeout(checkStatus, pollInterval);
                } else {
                    // 达到最大重试次数
                    if (window.Swal) {
                        Swal.fire({
                            title: '交易状态未知',
                            html: `
                                <div class="text-center">
                                    <div class="mb-3">
                                        <i class="fas fa-question-circle text-warning" style="font-size: 3rem;"></i>
                                    </div>
                                    <p>交易已提交，但尚未收到确认。您可以稍后查看交易状态。</p>
                                    <p class="small text-muted">
                                        交易签名: <a href="https://solscan.io/tx/${signature}" target="_blank">${signature.substring(0, 8)}...${signature.substring(signature.length - 8)}</a>
                                    </p>
                                </div>
                            `,
                            icon: 'warning',
                            confirmButtonText: '确定'
                        });
                    }
                }
        } catch (error) {
                console.error('检查交易状态出错:', error);
                // 发生错误，继续重试
                retryCount++;
                if (retryCount < maxRetries) {
                    setTimeout(checkStatus, pollInterval);
                } else {
                    // 达到最大重试次数
                    if (window.Swal) {
                        Swal.fire({
                            title: '检查交易状态失败',
                            html: `
                                <div class="text-center">
                                    <div class="mb-3">
                                        <i class="fas fa-exclamation-circle text-warning" style="font-size: 3rem;"></i>
                                    </div>
                                    <p>无法检查交易状态，但交易可能已经成功。您可以稍后查看。</p>
                                    <p class="small text-muted">
                                        交易签名: <a href="https://solscan.io/tx/${signature}" target="_blank">${signature.substring(0, 8)}...${signature.substring(signature.length - 8)}</a>
                                    </p>
                                </div>
                            `,
                            icon: 'warning',
                            confirmButtonText: '确定'
                        });
                    }
                }
            }
        };
        
        // 启动状态检查
        setTimeout(checkStatus, 2000); // 等待2秒后开始检查
    },
    
    /**
     * 通过以太坊钱包转账代币
     * @param {string} tokenSymbol 代币符号
     * @param {string} to 接收地址
     * @param {number} amount 转账金额
     * @returns {Promise<{success: boolean, txHash: string, error: string}>} 交易结果
     */
    async transferEthereumToken(tokenSymbol, to, amount) {
        try {
            console.log('使用以太坊钱包转账');
            
            // 检查Web3是否可用
            if (!this.web3) {
                throw new Error('Web3实例不可用');
            }
            
            // 这里应该实现基于Web3.js的ERC20代币转账
            // 由于我们的应用主要使用Solana，这里暂时返回一个错误
            throw new Error('以太坊转账功能尚未实现');
            
        } catch (error) {
            console.error('以太坊转账失败:', error);
            return {
                success: false,
                error: error.message || '以太坊转账失败'
            };
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
     * 成功连接钱包后的操作
     * 更新UI并获取余额
     */
    afterSuccessfulConnection(address, walletType, provider = null) {
        console.log('钱包连接成功，地址:', address, '类型:', walletType);
        
        // 更新钱包状态
        this.address = address;
        this.walletType = walletType;
        this.connected = true;
        
        // 保存连接信息到本地存储
        this.saveWalletData(address, walletType);
        
        // 存储钱包提供商对象（如果有）
        if (provider) {
            this.walletProvider = provider;
        }
        
        // 更新UI
        this.updateUI();
        
        // 获取余额
        this.getWalletBalance();
        
        // 检查是否为管理员并更新状态
        this.checkIsAdmin().then(isAdmin => {
            console.log('管理员状态检查结果:', isAdmin);
            this.isAdmin = isAdmin;
            
            // 更新管理员入口显示
            const adminEntry = document.getElementById('adminEntry');
            if (adminEntry) {
                adminEntry.style.display = isAdmin ? 'block' : 'none';
                console.log('已更新管理员入口显示状态:', isAdmin ? '显示' : '隐藏');
            }
            
            // 触发状态变化通知
            this.notifyStateChange({ type: 'admin_status_changed', isAdmin });
        }).catch(error => {
            console.error('检查管理员状态时出错:', error);
        });
        
        // 通知状态变化
        this.notifyStateChange({ type: 'connect' });
        
        return true;
    },

    /**
     * 保存钱包数据到本地存储
     * @param {string} address - 钱包地址
     * @param {string} walletType - 钱包类型
     */
    saveWalletData(address, walletType) {
        try {
            console.log(`保存钱包数据: 地址=${address}, 类型=${walletType}`);
            localStorage.setItem('walletType', walletType);
            localStorage.setItem('walletAddress', address);
            localStorage.setItem('lastWalletType', walletType);
            localStorage.setItem('lastWalletAddress', address);
        } catch (error) {
            console.error('保存钱包数据失败:', error);
        }
    },

    // 安全的Base64解码函数，处理非Latin1字符
    safeAtob(str) {
        try {
            // 创建一个Base64解码器
            const base64Chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
            const base64Map = {};
            for (let i = 0; i < base64Chars.length; i++) {
                base64Map[base64Chars.charAt(i)] = i;
            }
            
            // 替换URL安全字符
            const base64 = str.replace(/-/g, '+').replace(/_/g, '/');
            
            // 手动解码Base64
            let result = '';
            let i = 0;
            
            // 处理填充
            let encodedStr = base64;
            if (encodedStr.length % 4 === 1) {
                throw new Error('Invalid base64 string');
            }
            
            // 添加缺失的填充
            while (encodedStr.length % 4 !== 0) {
                encodedStr += '=';
            }
            
            // 手动解码
            while (i < encodedStr.length) {
                const enc1 = base64Map[encodedStr.charAt(i++)];
                const enc2 = base64Map[encodedStr.charAt(i++)];
                const enc3 = base64Map[encodedStr.charAt(i++)];
                const enc4 = base64Map[encodedStr.charAt(i++)];
                
                const chr1 = (enc1 << 2) | (enc2 >> 4);
                const chr2 = ((enc2 & 15) << 4) | (enc3 >> 2);
                const chr3 = ((enc3 & 3) << 6) | enc4;
                
                result += String.fromCharCode(chr1);
                
                if (enc3 !== 64) {
                    result += String.fromCharCode(chr2);
                }
                if (enc4 !== 64) {
                    result += String.fromCharCode(chr3);
                }
            }
            
            return result;
        } catch (e) {
            console.error('自定义Base64解码失败', e);
            
            // 尝试使用浏览器API但进行错误处理
            try {
                // 使用TextDecoder和Uint8Array间接处理
                const binaryString = window.atob(str);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                    bytes[i] = binaryString.charCodeAt(i);
                }
                return String.fromCharCode.apply(null, bytes);
            } catch (fallbackError) {
                console.error('所有Base64解码方法都失败', fallbackError);
                // 最后的尝试：返回一个安全的空二进制字符串
                return '';
            }
        }
    },

    // 将ArrayBuffer转换为Base64字符串
    arrayBufferToBase64(buffer) {
        // 首先转成Uint8Array确保我们有 .reduce 方法
        const uint8Array = new Uint8Array(buffer);
        // 然后将每个字节转换为字符
        const binary = uint8Array.reduce((str, byte) => str + String.fromCharCode(byte), '');
        // 最后使用btoa转为base64
        return btoa(binary);
    },

    /**
     * 调用购买合约 (已重构以适配Anchor合约)
     * 与Solana智能合约交互，执行资产购买操作
     * @param {Object} params - 合约交互参数
     * @param {string} params.contractAddress - 购买合约程序ID (rwa-trade program ID)
     * @param {string} params.assetId - 资产的唯一标识符 (用于查找资产账户地址和价格)
     * @param {string} params.buyerAddress - 买家钱包地址
     * @param {string} params.sellerAddress - 卖家钱包地址 (实际合约未使用，但保留用于查找ATA)
     * @param {number} params.totalAmount - 用户支付的总金额 (USDC)
     * @returns {Promise<Object>} 包含交易结果的对象，成功时包含txHash
     */
    async callPurchaseContract(params) {
        console.log('开始调用购买合约 (Anchor版)，参数:', params);

        try {
            // --- 1. 参数与环境校验 ---
            if (!params.contractAddress) throw new Error('缺少购买合约程序ID');
            if (!params.assetId) throw new Error('缺少资产ID');
            if (!params.buyerAddress) throw new Error('缺少买家地址');
            if (!params.sellerAddress) throw new Error('缺少卖家地址'); // 用于计算卖家ATA
            if (typeof params.totalAmount !== 'number' || params.totalAmount <= 0) throw new Error('无效的总支付金额');

            if (!this.connected || (this.walletType !== 'phantom' && this.walletType !== 'solana')) {
                throw new Error('请先连接Phantom或兼容的Solana钱包');
            }
            if (!window.solanaWeb3 || !window.solanaWeb3.Connection || !window.solanaWeb3.PublicKey || !window.solanaWeb3.Transaction || !window.solanaWeb3.SystemProgram) {
                throw new Error('Solana Web3.js基础库未完全加载');
            }
            // 检查SPL Token库和Anchor库
            if (!window.splToken || !window.splToken.getAssociatedTokenAddress || !window.splToken.TOKEN_PROGRAM_ID) {
                 console.error("SPL Token库或关键函数未加载");
                 // 尝试动态加载或初始化
                 if (typeof window.initSplTokenLib === 'function') {
                     console.log("尝试动态初始化SPL Token库...");
                     await window.initSplTokenLib();
                     if (!window.splToken || !window.splToken.getAssociatedTokenAddress) {
                         throw new Error('SPL Token库初始化失败或不完整');
                     }
                 } else {
                     throw new Error('SPL Token库未加载且无法动态初始化');
                 }
            }
            // 检查Anchor库
            if (!window.anchor || !window.anchor.Program || !window.anchor.workspace) {
                 // Anchor库可能不是全局变量，需要通过Provider访问
                 console.warn('全局Anchor对象不可用，将尝试通过Provider构建Program实例');
            }

            // --- 2. 获取必要信息 ---
            console.log('获取资产信息...');
            // !!关键假设!!: 后端API `/api/asset_details/{assetId}` 返回资产账户地址和价格
            // 或者这些信息存储在全局变量 `window.currentAssetInfo` 中
            let assetAccountAddress, assetPrice;
            try {
                if (window.currentAsset && window.currentAsset.asset_account_address && window.currentAsset.price) {
                    assetAccountAddress = window.currentAsset.asset_account_address;
                    assetPrice = parseFloat(window.currentAsset.price);
                    console.log('从全局变量 window.currentAsset 获取资产信息:', { assetAccountAddress, assetPrice });
                } else {
                    console.log(`尝试通过API获取资产 ${params.assetId} 的信息...`);
                    const response = await fetch(`/api/asset_details/${params.assetId}`);
                    if (!response.ok) throw new Error(`无法获取资产信息: ${response.statusText}`);
                    const assetInfo = await response.json();
                    if (!assetInfo.asset_account_address || !assetInfo.price) {
                        throw new Error('API返回的资产信息不完整');
                    }
                    assetAccountAddress = assetInfo.asset_account_address;
                    assetPrice = parseFloat(assetInfo.price);
                    console.log('从API获取资产信息:', { assetAccountAddress, assetPrice });
                }
                 if (!assetAccountAddress || isNaN(assetPrice) || assetPrice <= 0) {
                     throw new Error('无效的资产账户地址或价格');
                 }
            } catch (err) {
                 console.error("获取资产信息失败:", err);
                 throw new Error(`获取资产信息失败: ${err.message}`);
            }

            // 计算购买的代币数量 (amount)
            // 合约期望的是代币数量，前端传递的是总金额
            const amount = params.totalAmount / assetPrice;
            // !!重要!!: Solana代币通常有小数位，这里需要处理精度
            // 假设资产代币和USDC都有6位小数
            const amountInSmallestUnit = BigInt(Math.round(amount * Math.pow(10, 6)));
            console.log('计算的代币数量:', { amount, amountInSmallestUnit: amountInSmallestUnit.toString() });
             if (amountInSmallestUnit <= 0) {
                 throw new Error('计算出的购买数量无效');
             }

            // 获取其他地址
            const platformFeeAddress = window.PLATFORM_FEE_WALLET_ADDRESS || 'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd'; // 从全局或默认
            const usdcMintAddress = window.USDC_MINT_ADDRESS || 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'; // 从全局或默认
            const tokenProgramId = window.splToken.TOKEN_PROGRAM_ID;
            const systemProgramId = window.solanaWeb3.SystemProgram.programId;

            // 创建公钥对象
            const buyerPublicKey = new window.solanaWeb3.PublicKey(params.buyerAddress);
            const sellerPublicKey = new window.solanaWeb3.PublicKey(params.sellerAddress);
            const assetPublicKey = new window.solanaWeb3.PublicKey(assetAccountAddress);
            const platformFeePublicKey = new window.solanaWeb3.PublicKey(platformFeeAddress);
            const usdcMintPublicKey = new window.solanaWeb3.PublicKey(usdcMintAddress);
            const contractPublicKey = new window.solanaWeb3.PublicKey(params.contractAddress);

            console.log('准备公钥:', {
                buyer: buyerPublicKey.toString(),
                seller: sellerPublicKey.toString(),
                asset: assetPublicKey.toString(),
                platformFeeWallet: platformFeePublicKey.toString(),
                usdcMint: usdcMintPublicKey.toString(),
                contract: contractPublicKey.toString(),
                tokenProgram: tokenProgramId.toString(),
                systemProgram: systemProgramId.toString()
            });

            // 计算ATA地址
            console.log('计算ATA地址...');
            const buyerTokenAccount = await window.splToken.getAssociatedTokenAddress(usdcMintPublicKey, buyerPublicKey);
            const sellerTokenAccount = await window.splToken.getAssociatedTokenAddress(usdcMintPublicKey, sellerPublicKey);
            const platformFeeTokenAccount = await window.splToken.getAssociatedTokenAddress(usdcMintPublicKey, platformFeePublicKey);

            console.log('计算得到的ATA地址:', {
                buyerATA: buyerTokenAccount.toString(),
                sellerATA: sellerTokenAccount.toString(),
                platformFeeATA: platformFeeTokenAccount.toString()
            });

            // --- 3. 构建和发送交易 ---
            // 原版: 
            // const connection = new window.solanaWeb3.Connection(
            //    window.SOLANA_NETWORK_URL || 'https://api.mainnet-beta.solana.com', // 从全局或默认
            //    'confirmed'
            // );
            
            // 修改为使用我们的服务器API中继
            let connection;
            console.log('正在使用服务器中继API代替直接连接Solana节点');
            try {
                connection = new window.solanaWeb3.Connection(
                    '/api/solana', // 使用我们的服务器API中继
                    'confirmed'
                );
                // 覆盖某些方法以确保使用API中继
                const originalGetLatestBlockhash = connection.getLatestBlockhash;
                connection.getLatestBlockhash = async function(commitment) {
                    try {
                        console.log('通过服务器API中继获取最新blockhash');
                        const response = await fetch('/api/solana/latest-blockhash');
                        if (!response.ok) throw new Error('API请求失败');
                        const data = await response.json();
                        if (!data.success) throw new Error(data.error || '未知错误');
                        return data.result;
                    } catch (error) {
                        console.warn('通过API中继获取blockhash失败，尝试回退到原始方法', error);
                        return originalGetLatestBlockhash.call(this, commitment);
                    }
                };
                
                const originalSendRawTransaction = connection.sendRawTransaction;
                connection.sendRawTransaction = async function(rawTransaction, options) {
                    try {
                        console.log('通过服务器API中继发送交易');
                        const txBase64 = Buffer.from(rawTransaction).toString('base64');
                        const response = await fetch('/api/solana/send-transaction', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ 
                                transaction: txBase64,
                                options: options
                            })
                        });
                        if (!response.ok) throw new Error('API请求失败');
                        const data = await response.json();
                        if (!data.success) throw new Error(data.error || '未知错误');
                        return data.signature;
                    } catch (error) {
                        console.warn('通过API中继发送交易失败，尝试回退到原始方法', error);
                        return originalSendRawTransaction.call(this, rawTransaction, options);
                    }
                };
                
                const originalConfirmTransaction = connection.confirmTransaction;
                connection.confirmTransaction = async function(signature, commitment) {
                    try {
                        console.log('通过服务器API中继确认交易');
                        const response = await fetch(`/api/solana/confirm-transaction?signature=${signature}&commitment=${commitment || 'confirmed'}`);
                        if (!response.ok) throw new Error('API请求失败');
                        const data = await response.json();
                        if (!data.success) throw new Error(data.error || '未知错误');
                        return data.result;
                    } catch (error) {
                        console.warn('通过API中继确认交易失败，尝试回退到原始方法', error);
                        return originalConfirmTransaction.call(this, signature, commitment);
                    }
                };
            } catch (error) {
                console.error('创建中继API连接失败，回退到直接连接:', error);
                connection = new window.solanaWeb3.Connection(
                    window.SOLANA_NETWORK_URL || 'https://api.mainnet-beta.solana.com',
                    'confirmed'
                );
            }

            // 使用Anchor Provider和Program (如果全局Anchor可用)
            let program;
             let txSignature;

            try {
                 // 优先尝试使用 Anchor Provider 和 workspace 构建 program
                 const provider = new window.anchor.AnchorProvider(connection, window.solana, window.anchor.AnchorProvider.defaultOptions());
                 // 假设合约IDL已加载到 workspace
                 if (window.anchor.workspace && window.anchor.workspace.RwaTrade) {
                      program = window.anchor.workspace.RwaTrade;
                      console.log("使用全局 Anchor workspace 构建 Program 实例");
                 } else {
                      console.warn("全局 Anchor workspace 或 RwaTrade 不可用，尝试手动构建 Program");
                      // 需要合约的 IDL JSON 对象
                      // !!关键假设!!: 合约IDL存储在 window.RWA_TRADE_IDL
                      if (!window.RWA_TRADE_IDL) throw new Error("缺少 RWA Trade 合约的 IDL");
                      program = new window.anchor.Program(window.RWA_TRADE_IDL, contractPublicKey, provider);
                 }

                 console.log('构建 Anchor 交易...');
                 const tx = await program.methods
                     .buyAsset(new window.anchor.BN(amountInSmallestUnit.toString())) // 传递 u64 金额 (BN类型)
                     .accounts({
                         buyer: buyerPublicKey,
                         asset: assetPublicKey,
                         buyerTokenAccount: buyerTokenAccount,
                         sellerAccount: sellerTokenAccount, // 合约中是seller_account
                         platformFeeAccount: platformFeeTokenAccount, // 合约中是platform_fee_account
                         tokenProgram: tokenProgramId,
                         systemProgram: systemProgramId,
                     })
                      // .signers([provider.wallet.payer]) // Anchor Provider 会自动添加签名者
                     .transaction(); // 获取未签名的交易对象

                 console.log('交易已构建，请求用户签名...');
                 const signedTx = await provider.wallet.signTransaction(tx); // 请求钱包签名

                 console.log('交易已签名，发送到网络...');
                 txSignature = await connection.sendRawTransaction(signedTx.serialize());
                 console.log('交易已发送，签名:', txSignature);

             } catch (anchorError) {
                  console.error("使用 Anchor Provider 构建/发送交易失败:", anchorError);
                  console.log("尝试回退到手动构建 TransactionInstruction...");

                  // --- 回退方案：手动构建 TransactionInstruction ---
                  // (如果Anchor Provider方式失败或不可用)
                  const transaction = new window.solanaWeb3.Transaction();
                  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash();
                  transaction.recentBlockhash = blockhash;
                  transaction.lastValidBlockHeight = lastValidBlockHeight;
                  transaction.feePayer = buyerPublicKey;

                  // 构建 Anchor 指令数据 (序列化方法名 + 参数)
                  const instructionName = "buy_asset"; // 小驼峰或蛇形，取决于Anchor版本和IDL
                  const instructionData = window.anchor.coder.instruction.encode(instructionName, {
                      amount: new window.anchor.BN(amountInSmallestUnit.toString())
                  });

                  // 手动构建指令
                  transaction.add(
                      new window.solanaWeb3.TransactionInstruction({
                          keys: [
                              { pubkey: buyerPublicKey, isSigner: true, isWritable: true },
                              { pubkey: assetPublicKey, isSigner: false, isWritable: true }, // 假设asset账户会被修改
                              { pubkey: buyerTokenAccount, isSigner: false, isWritable: true },
                              { pubkey: sellerTokenAccount, isSigner: false, isWritable: true },
                              { pubkey: platformFeeTokenAccount, isSigner: false, isWritable: true },
                              { pubkey: tokenProgramId, isSigner: false, isWritable: false },
                              { pubkey: systemProgramId, isSigner: false, isWritable: false },
                          ],
                          programId: contractPublicKey,
                          data: instructionData,
                      })
                  );

                  console.log('手动构建交易完成，请求用户签名...');
                  const signedTransaction = await window.solana.signTransaction(transaction);

                  console.log('交易已签名，发送到网络...');
                  txSignature = await connection.sendRawTransaction(signedTransaction.serialize());
                  console.log('交易已发送，签名:', txSignature);
             }


            // --- 4. 确认交易 ---
            console.log('等待交易确认...');
            const confirmationStatus = await connection.confirmTransaction({
                signature: txSignature,
                blockhash: (await connection.getLatestBlockhash()).blockhash, // 获取最新的 blockhash
                lastValidBlockHeight: (await connection.getLatestBlockhash()).lastValidBlockHeight // 获取最新的 LBH
            }, 'confirmed'); // 使用 'confirmed' 或 'finalized'

            if (confirmationStatus.value.err) {
                console.error('交易确认失败:', confirmationStatus.value.err);
                throw new Error('交易确认失败: ' + JSON.stringify(confirmationStatus.value.err));
            }

            console.log('交易已确认，签名:', txSignature);

            // --- 5. 返回成功结果 ---
            return {
                success: true,
                txHash: txSignature,
                // 可以选择性返回计算的费用等信息
                // platformFee: ...,
                // sellerAmount: ...
            };
        } catch (error) {
            console.error('调用购买合约失败:', error);
            return {
                success: false,
                error: error.message || '未知错误'
            };
        }
    },

    // 添加一个新方法用于延迟重连到Phantom钱包
    delayedPhantomReconnect() {
        if (this.walletType !== 'phantom' || !this.address) return;
        
        console.log('执行延迟的Phantom钱包重连...');
        this.connectPhantom(true).then(success => {
            if (success) {
                console.log('延迟Phantom钱包重连成功');
                this.triggerWalletStateChanged();
            } else {
                console.log('延迟Phantom钱包重连失败，但保持UI状态');
            }
        }).catch(err => {
            console.error('延迟Phantom钱包重连出错:', err);
        });
    },

    // 检查代币余额
    checkTokenBalance: async function(tokenSymbol) {
        try {
            if (!tokenSymbol) {
                tokenSymbol = 'USDC';
            }
            
            // 尝试获取余额
            const balance = await this.getWalletBalance();
            
            return {
                success: true,
                balance: balance,
                symbol: tokenSymbol
            };
        } catch (error) {
            console.warn(`检查${tokenSymbol}余额失败:`, error);
            return {
                success: false,
                balance: 0,
                symbol: tokenSymbol,
                error: error.message
            };
        }
    },
}

// 页面初始化时就自动调用钱包初始化方法
document.addEventListener('DOMContentLoaded', async function() {
    console.log('页面加载完成，初始化钱包状态');
    try {
        // 确保全局访问
        window.walletState = walletState;
        
        // 初始化钱包状态
        await walletState.init();
        console.log('钱包初始化完成');
    } catch (error) {
        console.error('钱包初始化失败:', error);
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

// --- DOMContentLoaded Listener (or equivalent setup) ---
document.addEventListener('DOMContentLoaded', async () => {
    // ... other initializations ...
    // Ensure walletState.init() is called here or elsewhere appropriately
    // await walletState.init(); 

    // --- Asset Detail Page Specific Logic ---
    const buyButton = document.getElementById('buy-button');
    const purchaseAmountInput = document.getElementById('purchase-amount');
    const totalPriceDisplay = document.getElementById('totalPrice');
    
    // Check if we are on the asset detail page by checking for the buy button
    if (buyButton && purchaseAmountInput && totalPriceDisplay) {
        console.log('Asset detail page elements found. Setting up purchase listeners.');
        
        // 获取资产ID - 从URL中提取
        const pathParts = window.location.pathname.split('/');
        let assetId = pathParts[pathParts.length - 1];
        // 如果资产ID以RH-开头，则使用该ID
        if (!assetId.startsWith('RH-')) {
            // 尝试从页面中其他位置获取
            assetId = document.querySelector('[data-asset-id]')?.dataset.assetId;
        }
        
        if (!assetId) {
            console.error("无法确定资产ID");
            return; 
        }
        console.log(`资产ID: ${assetId}`);

        // 获取代币价格
        const pricePerToken = parseFloat(buyButton.dataset.tokenPrice || '0');
        if (pricePerToken <= 0) {
            console.warn("未找到有效的代币价格，无法计算总额");
        }

        // 更新总价格的函数
        const updateTotalPrice = () => {
            const amount = parseInt(purchaseAmountInput.value) || 0;
            if (amount > 0 && pricePerToken > 0) {
                totalPriceDisplay.value = (amount * pricePerToken).toFixed(2);
            } else {
                totalPriceDisplay.value = '0.00';
            }
        };

        // 添加输入事件监听器
        purchaseAmountInput.addEventListener('input', updateTotalPrice);
        updateTotalPrice(); // 初始计算

        // 修改后的购买按钮点击事件处理
        buyButton.addEventListener('click', () => {
            // 明确传递所有必要参数，不再使用event对象
            handleBuy(assetId, purchaseAmountInput, buyButton, pricePerToken);
        });
    } else {
        console.log('当前页面不包含购买元素');
    }
    // ... other page specific logic ...
});


// --- Purchase Functions ---

/**
 * 处理"Buy"按钮的点击事件
 * 通过调用后端API准备购买并显示确认模态框
 */
async function handleBuy(assetIdOrEvent, amountInput, buttonElement, pricePerToken) {
    console.log(`handleBuy 被调用，参数:`, {assetIdOrEvent, amountInput, buttonElement, pricePerToken});
    try {
        // 防止重复调用的标记
        const currentTime = new Date().getTime();
        if (window.lastHandleBuyCall && (currentTime - window.lastHandleBuyCall < 500)) {
            console.log('阻止handleBuy短时间内的重复调用');
            return false;
        }
        window.lastHandleBuyCall = currentTime;
        
        // 处理不同的调用方式 - 统一确定参数
        let assetId, buyErrorDiv;
        
        // 如果第一个参数是事件对象
        if (typeof assetIdOrEvent === 'object' && assetIdOrEvent.type === 'click') {
            const targetElement = assetIdOrEvent.currentTarget || assetIdOrEvent.target;
            assetId = targetElement.getAttribute('data-asset-id');
            
            // 获取数量输入元素
            amountInput = document.getElementById('purchase-amount');
            buttonElement = targetElement;
            
            // 尝试获取代币价格
            pricePerToken = parseFloat(targetElement.getAttribute('data-token-price'));
        } else {
            // 直接使用传入的参数
            assetId = assetIdOrEvent;
        }
        
        // 验证资产ID
        if (!assetId) {
            console.error('handleBuy: 缺少必要参数：资产ID必须是字符串', assetId);
            return false;
        }
        
        // 获取和验证购买数量
        if (!amountInput) {
            console.error('handleBuy: 缺少必要参数：购买数量输入框');
            return false;
        }
        
        // 处理按钮元素
        if (!buttonElement) {
            console.warn('handleBuy: 缺少按钮元素，将不会显示加载状态');
        }
        
        // 获取错误显示区域
        buyErrorDiv = document.getElementById('buy-error');
        
        // 获取并验证数量
        const amount = amountInput.value;
        console.log("原始输入金额:", amount, "类型:", typeof amount);
        
        // 将输入金额强制转换为数字类型，确保发送正确的格式
        let amountNum;
        try {
            // 尝试转换为浮点数
            amountNum = parseFloat(amount);
            if (isNaN(amountNum) || amountNum <= 0) {
                showError('请输入有效的购买数量', buyErrorDiv);
                return false;
            }
            // 确保金额是正数
            amountNum = Math.max(1, amountNum);
            console.log("处理后的金额:", amountNum, "类型:", typeof amountNum);
        } catch (e) {
            console.error("金额转换失败:", e);
            showError('无效的购买数量格式', buyErrorDiv);
            return false;
        }
        
        // 设置加载状态
        if (buttonElement) {
            setButtonLoading(buttonElement, '准备中...');
        }
        showLoadingState('正在准备购买...');

        try {
            // 获取钱包地址
            const walletAddress = walletState.address;
            console.log(`使用钱包地址: ${walletAddress}`);

            // 准备请求数据对象，确保所有字段都是正确的类型
            const requestData = {
                asset_id: assetId.toString(),  // 确保asset_id始终是字符串类型
                amount: amountNum,  // 使用整数类型的金额
                wallet_address: walletAddress
            };
            
            console.log("发送到后端的数据:", JSON.stringify(requestData));

            // API请求 - 确保数字格式正确
            const response = await fetch('/api/trades/prepare_purchase', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Eth-Address': walletAddress,
                    'X-Wallet-Address': walletAddress,
                    'Authorization': `Wallet ${walletAddress}`
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                let errorMsg = `准备购买失败。状态: ${response.status}`;
                try {
                    const errData = await response.json();
                    errorMsg = errData.error || errorMsg;
                } catch (e) { /* 忽略JSON解析错误 */ }
                throw new Error(errorMsg);
            }

            const prepareData = await response.json();
            console.log('购买准备成功:', prepareData);

            // 确保prepareData包含必要的字段
            if (!prepareData.asset_name) prepareData.asset_name = document.querySelector('.asset-name, h1, h2, h3, h4')?.textContent?.trim() || '未知资产';
        
            // 确保价格数据正确
            prepareData.price_per_token = parseFloat(pricePerToken) || prepareData.price_per_token || 0;
            prepareData.amount = amountNum;
            prepareData.asset_id = assetId;
            
            // 计算小计（如果API没有提供）
            if (!prepareData.subtotal && prepareData.price_per_token && prepareData.amount) {
                prepareData.subtotal = prepareData.price_per_token * prepareData.amount;
            }
            
            // 确保总成本有值
            if (!prepareData.total_cost && prepareData.total_amount) {
                prepareData.total_cost = prepareData.total_amount;
            } else if (!prepareData.total_cost && prepareData.subtotal) {
                // 如果没有平台费用数据，但有小计，则使用小计作为总成本
                prepareData.total_cost = prepareData.subtotal;
            }
            
            // 确保接收地址存在
            if (!prepareData.recipient_address && prepareData.seller_address) {
                prepareData.recipient_address = prepareData.seller_address;
            }

            // 显示确认模态框
            showBuyModal(prepareData);

        } catch (error) {
            console.error('购买准备失败:', error);
            showError(error.message || '发生意外错误', buyErrorDiv);
            return false; // <-- 添加 return false 阻止后续执行
        } finally {
            hideLoadingState();
            if (buttonElement) {
                resetButton(buttonElement);
            }
        }
    } catch (unexpected) {
        // 捕获所有意外错误，确保不会导致页面崩溃
        console.error('handleBuy函数发生意外错误:', unexpected);
        showError('处理购买请求时发生意外错误，请刷新页面后重试');
        hideLoadingState();
    }
}

/**
 * Populates and shows the purchase confirmation modal.
 * @param {object} prepareData - Data returned from the /api/trades/prepare_purchase endpoint.
 */
function showBuyModal(prepareData) {
    console.log("Showing buy modal with data:", prepareData);
    try {
        const modalElement = document.getElementById('buyModal');
        if (!modalElement) {
            console.error('Buy modal element not found!');
            showError('{{ _("UI Error: Could not display confirmation.") }}');
            return;
        }

        // Get or initialize Bootstrap modal instance
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);

        // --- Populate Modal Content ---
        // Use helper function to safely set text content
        const setText = (id, text) => {
            const el = modalElement.querySelector(`#${id}`);
            if (el) el.textContent = text !== null && typeof text !== 'undefined' ? text : 'N/A';
             else console.warn(`Modal element #${id} not found`);
        };
         const setCode = (id, text) => {
             const el = modalElement.querySelector(`#${id}`);
             if (el) el.textContent = text || 'N/A';
             else console.warn(`Modal element #${id} not found`);
        };

        setText('modalAssetName', prepareData.asset_name);
        setText('modalAmount', prepareData.amount);
        setText('modalPricePerToken', typeof prepareData.price_per_token === 'number' ? prepareData.price_per_token.toFixed(2) : parseFloat(prepareData.price_per_token)?.toFixed(2) || 'N/A');
        setText('modalSubtotal', typeof prepareData.subtotal === 'number' ? prepareData.subtotal.toFixed(2) : parseFloat(prepareData.subtotal)?.toFixed(2) || 'N/A');
        setText('modalFee', typeof prepareData.fee === 'number' ? prepareData.fee.toFixed(2) : parseFloat(prepareData.fee)?.toFixed(2) || 'N/A');
        setText('modalTotalCost', typeof prepareData.total_cost === 'number' ? prepareData.total_cost.toFixed(2) : parseFloat(prepareData.total_cost)?.toFixed(2) || 'N/A');
        setCode('modalRecipientAddress', prepareData.recipient_address);


        // Clear previous errors
        const modalErrorDiv = modalElement.querySelector('#buyModalError');
        if (modalErrorDiv) modalErrorDiv.style.display = 'none';

        // --- Setup Confirm Button ---
        const confirmBtn = modalElement.querySelector('#confirmPurchaseBtn');
        if (!confirmBtn) {
            console.error('Confirm purchase button not found in modal!');
            return;
        }
        
        // **Important:** Remove previous listener to avoid duplicates. Cloning is a robust way.
        const newConfirmBtn = confirmBtn.cloneNode(true);
        // Make sure the spinner is initially hidden on the clone
        const spinner = newConfirmBtn.querySelector('.spinner-border');
        if (spinner) spinner.style.display = 'none';
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        // Attach new event listener to the cloned button
        newConfirmBtn.addEventListener('click', async () => {
            // Pass the *original* prepareData which contains all context
            await confirmPurchase(prepareData, modalElement, newConfirmBtn); 
        }, { once: true }); // Use { once: true } as an alternative way to prevent multiple clicks if cloning isn't preferred

        // Show the modal
        modal.show();

    } catch (error) {
        console.error("Error setting up or showing buy modal:", error);
        showError(`{{ _("UI Error: Could not display confirmation.") }} ${error.message}`);
    }
}


/**
 * Handles the actual purchase confirmation: wallet transfer and backend execution call.
 * @param {object} purchaseData - Data originally from prepare_purchase, passed from showBuyModal.
 * @param {HTMLElement} modalElement - The modal DOM element.
 * @param {HTMLElement} confirmBtn - The confirmation button element.
 */
async function confirmPurchase(purchaseData, modalElement, confirmBtn) {
    console.log("confirmPurchase called with data:", purchaseData);
    const modalErrorDiv = modalElement.querySelector('#buyModalError');
    modalErrorDiv.style.display = 'none'; // Clear previous errors

    setButtonLoading(confirmBtn, '{{ _("Processing...") }}');
    showLoadingState('{{ _("Processing payment via wallet...") }}');

    try {
        // Extract necessary data (ensure field names match API response)
        const recipient = purchaseData.recipient_address;
        const totalAmount = parseFloat(purchaseData.total_cost || purchaseData.total_amount); // 确保处理各种格式的总金额
        const assetId = purchaseData.asset_id;
        const purchaseAmount = parseInt(purchaseData.amount); // 购买的代币数量是整数

        if (!recipient || isNaN(totalAmount) || totalAmount <= 0 || !assetId || isNaN(purchaseAmount) || purchaseAmount <= 0) {
            throw new Error('{{ _("Invalid purchase data for confirmation.") }}');
        }

        console.log(`Attempting to transfer ${totalAmount} USDC to ${recipient}`);

        // --- Step 1: Wallet Transfer ---
        const transferResult = await walletState.transferSolanaToken('USDC', recipient, totalAmount);

        if (!transferResult || !transferResult.success) {
            // 转账失败或被用户拒绝
            throw new Error(transferResult?.error || '钱包转账失败或被取消');
        }
        
        // 获取交易签名
        const signature = transferResult.txHash;
        
        console.log(`钱包转账成功。签名: ${signature}`);
        showLoadingState(`{{ _("Finalizing purchase...") }}`); // Update loading message

        // --- Step 2: Execute Purchase on Backend ---
        const executeResponse = await fetch('/api/trades/execute_purchase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': walletState.address,
                'X-Eth-Address': walletState.address // 为兼容性保留
            },
            body: JSON.stringify({
                asset_id: assetId,
                amount: purchaseAmount, // Send the number of tokens purchased
                signature: signature // Send the Solana transaction signature
            })
        });

        if (!executeResponse.ok) {
             let errorMsg = `{{ _("Failed to finalize purchase") }}. Status: ${executeResponse.status}`;
            try {
                const errData = await executeResponse.json();
                errorMsg = errData.error || errorMsg;
            } catch (e) { /* Ignore JSON parsing error */ }
            throw new Error(errorMsg);
        }

        const executeData = await executeResponse.json();
        console.log('Purchase executed successfully:', executeData);

        // --- Success ---
        bootstrap.Modal.getInstance(modalElement).hide();
        showSuccess(executeData.message || '{{ _("Purchase successful!") }}');
        
        // Optional: Refresh page data or redirect
         setTimeout(() => window.location.reload(), 2000); // Simple refresh after 2s

    } catch (error) {
        console.error('Purchase confirmation failed:', error);
        // Show error inside the modal
        modalErrorDiv.textContent = error.message || '{{ _("An unexpected error occurred during confirmation.") }}';
        modalErrorDiv.style.display = 'block';
    } finally {
        hideLoadingState();
        resetButton(confirmBtn); // Reset the modal's confirm button
    }
}

// Helper functions (ensure they exist or add them)
function showSuccess(message, container = null) {
    // Implementation depends on how you want to show success (e.g., toast, alert)
    console.log("SUCCESS:", message);
    alert(message); // Simple alert for now
}

function showError(message, container = null) {
     // Implementation depends on how you want to show errors
    console.error("ERROR:", message);
     if (container) {
         container.textContent = message;
         container.style.display = 'block';
     } else {
         alert(message); // Simple alert fallback
     }
}

// 将confirmPurchase函数设置为全局函数以便于其他模块调用
window.confirmPurchase = async function(purchaseData, modalElement, confirmBtn) {
    console.log("全局confirmPurchase调用，数据:", purchaseData);
    
    const modalErrorDiv = modalElement?.querySelector('#buyModalError');
    
    // 增强型钱包连接状态检查
    let isConnected = false;
    let walletAddress = '';
    
    // 方法1: 检查全局walletState对象
    if (window.walletState && (window.walletState.isConnected || window.walletState.connected) && window.walletState.address) {
        isConnected = true;
        walletAddress = window.walletState.address;
        console.log("从全局walletState检测到钱包连接:", walletAddress);
    }
    
    // 方法2: 检查传入的钱包地址
    if (!isConnected && purchaseData && purchaseData.wallet_address) {
        isConnected = true;
        walletAddress = purchaseData.wallet_address;
        console.log("从传入参数检测到钱包地址:", walletAddress);
    }
    
    // 方法3: 检查localStorage
    if (!isConnected) {
        const storedAddress = localStorage.getItem('walletAddress');
        if (storedAddress) {
            isConnected = true;
            walletAddress = storedAddress;
            console.log("从localStorage检测到钱包连接:", walletAddress);
        }
    }
    
    // 如果仍然未检测到连接，显示错误
    if (!isConnected || !walletAddress) {
        console.error("所有方法均未检测到钱包连接");
        showError("请先连接钱包");
        if (modalErrorDiv) {
            modalErrorDiv.textContent = "请先连接钱包";
            modalErrorDiv.style.display = "block";
        }
        return;
    }
    
    // 使用检测到的钱包地址
    console.log("使用钱包地址:", walletAddress);
    
    try {
        // 显示按钮加载状态
        if (confirmBtn) {
            const spinner = confirmBtn.querySelector('.spinner-border');
            if (spinner) spinner.style.display = 'inline-block';
            confirmBtn.disabled = true;
            confirmBtn.textContent = '处理中...';
        }
        
        // 获取必要的参数
        const { trade_id, amount, total_cost, recipient_address } = purchaseData;
        
        // 验证参数完整性
        if (!trade_id) {
            throw new Error("缺少交易ID");
        }
        
        if (!recipient_address) {
            throw new Error("缺少接收地址");
        }
        
        if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
            throw new Error("无效的购买数量");
        }
        
        if (!total_cost || isNaN(parseFloat(total_cost)) || parseFloat(total_cost) <= 0) {
            throw new Error("无效的总成本");
        }
        
        // 1. 转移USDC到卖家
        console.log(`准备转移 ${total_cost} USDC 到 ${recipient_address}`);
        
        // 实际转账请求
        const transferResult = await fetch('/api/execute_transfer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-Wallet-Address': walletAddress,
                'X-Eth-Address': walletAddress
            },
            body: JSON.stringify({
                token_symbol: 'USDC',
                amount: parseFloat(total_cost),
                to_address: recipient_address,
                from_address: walletAddress
            })
        });
        
        // 检查转账结果
        if (!transferResult.ok) {
            const errorData = await transferResult.json();
            throw new Error(errorData.error || "转账失败");
        }
        
        const transferData = await transferResult.json();
        console.log("转账结果:", transferData);
        
        if (!transferData.success) {
            throw new Error(transferData.error || "转账处理失败");
        }
        
        // 2. 确认购买
        console.log("转账成功，现在确认购买");
        
        const confirmResult = await fetch('/api/trades/confirm_purchase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-Wallet-Address': walletAddress,
                'X-Eth-Address': walletAddress
            },
            body: JSON.stringify({
                trade_id: trade_id,
                tx_hash: transferData.tx_hash
            })
        });
        
        // 检查确认结果
        if (!confirmResult.ok) {
            const errorData = await confirmResult.json();
            throw new Error(errorData.error || "确认购买失败");
        }
        
        const confirmData = await confirmResult.json();
        console.log("确认购买结果:", confirmData);
        
        if (!confirmData.success) {
            throw new Error(confirmData.error || "确认购买处理失败");
        }
        
        // 3. 处理成功
        console.log("购买流程完成");
        
        // 隐藏模态框
        const bsModal = bootstrap.Modal.getInstance(modalElement);
        if (bsModal) {
            bsModal.hide();
        }
        
        // 显示成功消息
        showSuccess('购买成功！交易已提交');
        
        // 刷新页面数据
        if (typeof refreshAssetInfoNow === 'function') {
            try {
                await refreshAssetInfoNow();
            } catch (error) {
                console.error("刷新资产信息失败:", error);
            }
        }
        
        // 恢复按钮状态
        if (confirmBtn) {
            const spinner = confirmBtn.querySelector('.spinner-border');
            if (spinner) spinner.style.display = 'none';
            confirmBtn.disabled = false;
            confirmBtn.textContent = '确认购买';
        }
        
        return confirmData;
        
    } catch (error) {
        console.error("确认购买过程中出错:", error);
        
        // 显示错误消息
        showError(error.message || "购买过程中出现错误");
        
        // 在模态框中显示错误
        if (modalErrorDiv) {
            modalErrorDiv.textContent = error.message || "购买过程中出现错误";
            modalErrorDiv.style.display = "block";
        }
        
        // 恢复按钮状态
        if (confirmBtn) {
            const spinner = confirmBtn.querySelector('.spinner-border');
            if (spinner) spinner.style.display = 'none';
            confirmBtn.disabled = false;
            confirmBtn.textContent = '确认购买';
        }
        
        throw error;
    }
};

// 确保在DOM加载完成后连接钱包
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，初始化钱包...');
    
    // 初始化钱包状态
    if (window.walletState) {
        walletState.init().catch(e => console.error('钱包初始化失败:', e));
    }
    
    // 确保全局函数可用
    if (!window.showLoadingState) {
        window.showLoadingState = function(message) {
            console.log('显示加载状态:', message);
            // 实现加载状态显示逻辑
        };
    }
    
    if (!window.hideLoadingState) {
        window.hideLoadingState = function() {
            console.log('隐藏加载状态');
            // 实现隐藏加载状态逻辑
        };
    }
});

/**
 * 刷新当前页面上的资产信息
 * 在购买成功后调用，更新剩余数量等信息
 */
function refreshAssetInfo() {
    console.log("刷新资产信息...");
    
    // 获取资产ID和配置信息
    let assetId = '';
    const timestamp = new Date().getTime();
    
    // 尝试多种方式获取资产ID
    if (window.ASSET_CONFIG && window.ASSET_CONFIG.id) {
        assetId = window.ASSET_CONFIG.id;
        console.log("从ASSET_CONFIG获取资产ID:", assetId);
    } else {
        // 尝试从URL获取
        const urlMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
        if (urlMatch && urlMatch[1]) {
            assetId = urlMatch[1];
            console.log("从URL获取资产ID:", assetId);
        } else {
            // 尝试从页面元素获取
            const assetIdElement = document.querySelector('[data-asset-id]');
            if (assetIdElement) {
                assetId = assetIdElement.getAttribute('data-asset-id');
                console.log("从页面元素获取资产ID:", assetId);
            }
        }
    }
    
    // 如果仍找不到资产ID，使用默认值
    if (!assetId) {
        // 查看是否有全局变量或在localStorage中设置的默认资产ID
        assetId = window.defaultAssetId || 'RH-205020';
        console.log("未找到资产ID，使用默认ID:", assetId);
    }
    
    // 准备多个可能的API URL
    const apiUrls = [
        `/api/assets/symbol/${assetId}?_=${timestamp}`,
        `/api/assets/${assetId}?_=${timestamp}`,
        `/api/assets/RH-${assetId}?_=${timestamp}`
    ];
    
    // 如果ID包含前缀，也尝试不带前缀的版本
    if (assetId.includes('-')) {
        const numericId = assetId.split('-')[1];
        if (numericId) {
            apiUrls.push(`/api/assets/${numericId}?_=${timestamp}`);
        }
    }
    
    // 尝试按顺序请求多个URL
    fetchWithMultipleUrls(apiUrls)
        .then(data => {
            if (!data || !data.id) {
                console.warn("API返回的资产数据无效，使用默认值");
                return createDefaultAssetData(assetId);
            }
            
            // 更新资产信息显示
            updateAssetInfoDisplay(data);
            
            // 存储最新的资产数据
            window.lastAssetInfo = data;
            
            // 如果有分红数据刷新函数，也刷新分红
            if (typeof window.refreshDividendData === 'function') {
                window.refreshDividendData(data.id || data.symbol);
            }
        })
        .catch(error => {
            console.debug("获取资产信息失败，使用默认值:", error);
            
            // 使用默认数据或最后已知的数据
            const defaultData = createDefaultAssetData(assetId);
            updateAssetInfoDisplay(defaultData);
        });
}

/**
 * 创建默认的资产数据对象
 */
function createDefaultAssetData(assetId) {
    // 使用最后已知的数据或创建新的默认数据
    if (window.lastKnownData) {
        console.log("使用最后已知的资产数据:", window.lastKnownData);
        return window.lastKnownData;
    }
    
    // 创建默认数据
    return {
        id: assetId,
        symbol: assetId,
        name: document.querySelector('h1,h2,.asset-name')?.textContent || "资产详情",
        description: document.querySelector('.asset-description')?.textContent || "",
        token_price: 0.23,
        total_supply: 100000000,
        remaining_supply: 99988520,
        image_url: "/static/img/assets/default.jpg"
    };
}

/**
 * 使用多个URL尝试获取数据
 */
async function fetchWithMultipleUrls(urls) {
    let lastError = null;
    
    for (let i = 0; i < urls.length; i++) {
        const url = urls[i];
        console.log(`尝试API端点 ${i+1}/${urls.length}: ${url}`);
        
        try {
            // 添加超时控制
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const response = await fetch(url, { signal: controller.signal });
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log(`API端点 ${i+1}/${urls.length} 请求成功:`, data);
            return data;
    } catch (error) {
            console.debug(`API端点 ${i+1}/${urls.length} 请求失败: ${error.message}`);
            lastError = error;
        }
    }
    
    // 所有URL都失败了
    throw new Error(`所有API端点请求失败: ${lastError?.message}`);
}

/**
 * 更新资产信息显示
 */
function updateAssetInfoDisplay(data) {
    // 更新资产详情页面上的资产信息显示
    console.log("正在更新资产信息显示:", data);
    
    // 找到并更新各个信息元素
    const remainingSupplyElements = document.querySelectorAll('.remaining-supply, [data-remaining-supply]');
    remainingSupplyElements.forEach(el => {
        el.textContent = formatNumber(data.remaining_supply);
        
        // 更新数据属性
        if (el.hasAttribute('data-remaining-supply')) {
            el.setAttribute('data-remaining-supply', data.remaining_supply);
        }
    });
    
    // 更新百分比显示
    if (data.total_supply && data.total_supply > 0) {
        const percentRemaining = ((data.remaining_supply / data.total_supply) * 100).toFixed(2);
        const percentageBars = document.querySelectorAll('.supply-percentage, .remaining-percentage');
        percentageBars.forEach(el => {
            el.textContent = `${percentRemaining}%`;
            
            // 如果是进度条类元素，也更新宽度
            if (el.classList.contains('progress-bar')) {
                el.style.width = `${percentRemaining}%`;
            }
        });
    }
    
    // 更新价格显示
    const priceElements = document.querySelectorAll('.token-price, [data-token-price]');
    if (data.token_price) {
        priceElements.forEach(el => {
            el.textContent = formatCurrency(data.token_price);
            
            // 更新数据属性
            if (el.hasAttribute('data-token-price')) {
                el.setAttribute('data-token-price', data.token_price);
            }
        });
    }
    
    // 刷新交易表单金额计算（如果存在）
    if (typeof window.recalculateTradeAmount === 'function') {
        window.recalculateTradeAmount();
    }
}

/**
 * 格式化数字为易读形式
 */
function formatNumber(num) {
    if (num === undefined || num === null) return '0';
    
    return new Intl.NumberFormat().format(num);
}

/**
 * 格式化货币值
 */
function formatCurrency(value) {
    if (value === undefined || value === null) return '$0.00';
    
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// 导出全局刷新函数
window.refreshAssetInfoNow = refreshAssetInfo;

// 在适当位置添加以下代码，替代wallet_api_fix.js的功能

/**
 * 签名并确认交易
 * @param {Object} transactionData - 交易数据
 * @returns {Promise<Object>} - 返回带有签名的Promise
 */
async function signAndConfirmTransaction(transactionData) {
  if (!transactionData) {
    return Promise.reject(new Error('交易数据为空'));
  }
  
  // 检查钱包连接
  if (!window.ethereum && !window.solana) {
    return Promise.reject(new Error('未检测到钱包'));
  }
  
  // 检查当前钱包类型
  const walletType = localStorage.getItem('walletType') || '';
  
  try {
    // 根据钱包类型处理签名
    if (walletType.toLowerCase().includes('metamask') || window.ethereum) {
      return await signEthereumTransaction(transactionData);
    } else if (walletType.toLowerCase().includes('phantom') || window.solana) {
      return await signSolanaTransaction(transactionData);
    } else {
      return Promise.reject(new Error('不支持的钱包类型'));
    }
  } catch (error) {
    console.error('签名失败:', error);
    return Promise.reject(error);
  }
}

/**
 * 签名以太坊交易
 * @param {Object} transactionData - 交易数据
 * @returns {Promise<Object>} - 返回签名结果
 */
async function signEthereumTransaction(transactionData) {
  if (!window.ethereum) {
    return Promise.reject(new Error('未检测到以太坊钱包'));
  }
  
  try {
    // 获取当前账户
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    const from = accounts[0];
    
    if (!from) {
      return Promise.reject(new Error('无法获取钱包地址'));
    }
    
    // 是否需要发送交易还是仅签名
    if (transactionData.method === 'eth_signTypedData_v4' || transactionData.method === 'eth_signTypedData') {
      // EIP-712签名
      const signature = await window.ethereum.request({
        method: transactionData.method || 'eth_signTypedData_v4',
        params: [from, JSON.stringify(transactionData.data)]
      });
      
      return { signature, wallet_address: from };
    } else {
      // 常规交易
      const txParams = {
        from,
        to: transactionData.to,
        value: transactionData.value || '0x0',
        data: transactionData.data || '0x',
        gas: transactionData.gas || undefined,
        gasPrice: transactionData.gasPrice || undefined
      };
      
      // 发送交易
      const txHash = await window.ethereum.request({
        method: 'eth_sendTransaction',
        params: [txParams]
      });
      
      return { signature: txHash, wallet_address: from };
    }
  } catch (error) {
    console.error('以太坊签名失败:', error);
    return Promise.reject(error);
  }
}

/**
 * 签名Solana交易
 * @param {Object} transactionData - 交易数据
 * @returns {Promise<Object>} - 返回签名结果
 */
async function signSolanaTransaction(transactionData) {
  if (!window.solana) {
    return Promise.reject(new Error('未检测到Solana钱包'));
  }
  
  try {
    // 连接到Solana钱包
    const response = await window.solana.connect();
    const publicKey = response.publicKey.toString();
    
    // 检查交易数据格式
    if (!transactionData.message) {
      return Promise.reject(new Error('无效的Solana交易数据'));
    }
    
    // 创建交易对象
    const transaction = {
      serialize: () => Buffer.from(transactionData.message, 'base64')
    };
    
    // 请求签名
    const signedTransaction = await window.solana.signTransaction(transaction);
    const signature = signedTransaction.signature.toString('base64');
    
    return { signature, wallet_address: publicKey };
  } catch (error) {
    console.error('Solana签名失败:', error);
    return Promise.reject(error);
  }
}

// 添加到全局命名空间
window.signAndConfirmTransaction = signAndConfirmTransaction;

// 添加全局wallet对象，提供与create.js兼容的接口
window.wallet = {
    // 获取当前钱包
    getCurrentWallet: function() {
        try {
            // 检查walletState是否已初始化
            if (!window.walletState || !window.walletState.connected) {
                console.log('当前未连接钱包');
                return null;
            }
            
            // 返回当前钱包信息
            return {
                type: window.walletState.walletType,
                address: window.walletState.address,
                connected: window.walletState.connected
            };
        } catch (error) {
            console.error('获取当前钱包信息失败:', error);
            return null;
        }
    },
    
    // 转账接口 - 直接调用walletState的转账方法
    transferToken: async function(tokenSymbol, to, amount) {
        console.log(`wallet.transferToken被调用: ${tokenSymbol}, ${to}, ${amount}`);
        
        try {
            // 检查当前钱包类型
            const currentWallet = this.getCurrentWallet();
            if (!currentWallet) {
                throw new Error('钱包未连接');
            }
            
            let result;
            // 根据钱包类型选择不同的转账方法
            if (currentWallet.type === 'phantom' || currentWallet.type === 'solana') {
                console.log('使用Solana转账方法');
                // 直接调用Solana转账方法
                result = await walletState.transferSolanaToken(tokenSymbol, to, amount);
            } else if (currentWallet.type === 'metamask' || currentWallet.type === 'ethereum') {
                console.log('使用以太坊转账方法');
                // 调用以太坊转账方法
                result = await walletState.transferEthereumToken(tokenSymbol, to, amount);
            } else {
                throw new Error(`不支持的钱包类型: ${currentWallet.type}`);
            }
            
            // 返回转账结果
            if (!result.success) {
                throw new Error(result.error || '转账失败');
            }
            
            console.log('转账成功:', result);
            return result;
        } catch (error) {
            console.error('转账失败:', error);
            return {
                success: false,
                txHash: null,
                error: error.message || '转账过程中发生错误'
            };
        }
    }
}

// 确保已有walletState对象
if (!window.walletState) {
    console.warn('walletState未找到，使用window.wallet时将无法获取钱包信息');
}

// 导出钱包接口
console.log('钱包接口初始化完成');

