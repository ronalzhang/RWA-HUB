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
                } else if (storedWalletType === 'phantom' && window.solana && window.solana.isPhantom) {
                    canReconnect = true;
                    console.log('检测到Phantom钱包可用，将尝试重连');
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
                            // 已经在connect方法内更新了UI，无需重复
                            
                            // 通知状态变化
                            this.notifyStateChange({
                                type: 'reconnect', 
                                address: this.address,
                                walletType: this.walletType
                            });
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
            
            // 完成初始化
            this.initialized = true;
            console.log('钱包初始化完成');
            
            return true;
        } catch (error) {
            console.error('初始化钱包出错:', error);
            return false;
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
        try {
            console.log(`尝试连接钱包类型: ${walletType}`);
            
            if (!walletType) {
                console.error('未指定钱包类型');
                showError('请选择要连接的钱包类型');
                    return false;
                }
            
            // 如果当前已经连接了同类型的钱包，先断开连接
            if (this.connected && this.walletType === walletType) {
                await this.disconnect();
            }
            
            // 在移动设备上进行特殊处理
            if (this.isMobile()) {
                console.log('检测到移动设备，特殊处理钱包连接');
                
                // 检查是否在dApp浏览器中
                let inDAppBrowser = false;
                
                if (walletType.toLowerCase() === 'phantom' || walletType.toLowerCase() === 'solflare') {
                    // 检查Solana对象是否存在
                    inDAppBrowser = window.solana !== undefined;
                } else if (walletType.toLowerCase() === 'ethereum' || walletType.toLowerCase() === 'metamask') {
                    // 检查ethereum对象是否存在
                    inDAppBrowser = window.ethereum !== undefined;
                }
                
                if (!inDAppBrowser) {
                    console.log('未在dApp浏览器中，尝试直接跳转到钱包App');
                    
                    // 根据钱包类型构建移动端深度链接
                    let deepLink = '';
                    
                    if (walletType.toLowerCase() === 'phantom') {
                        // 构建Phantom钱包链接 - 使用更可靠的Universal Link格式
                        const currentUrl = encodeURIComponent(window.location.href);
                        // 使用新的深度链接格式
                        deepLink = `https://phantom.app/ul/browse/${currentUrl}`;
                        
                        // 保存当前钱包连接尝试状态到LocalStorage以便返回后检查
                        localStorage.setItem('pendingWalletType', walletType);
                        localStorage.setItem('pendingWalletConnection', 'true');
                        localStorage.setItem('pendingWalletTimestamp', Date.now().toString());
                        localStorage.setItem('lastConnectionAttemptUrl', window.location.href);
                        
                        // 创建并发送一个自定义事件，通知页面即将跳转到钱包
                        document.dispatchEvent(new CustomEvent('walletAppRedirect', {
                            detail: {
                                walletType: walletType,
                                timestamp: Date.now()
                            }
                        }));
                        
                        console.log('跳转到Phantom钱包App:', deepLink);
                        // 跳转到钱包App
                        window.location.href = deepLink;
                        return true; // 返回true表示已尝试连接
                    } else if (walletType.toLowerCase() === 'metamask') {
                        // 构建MetaMask钱包链接
                        const currentUrl = encodeURIComponent(window.location.href);
                        deepLink = `https://metamask.app.link/dapp/${window.location.host}${window.location.pathname}`;
                        
                        // 保存当前钱包连接尝试状态
                        localStorage.setItem('pendingWalletType', walletType);
                        localStorage.setItem('pendingWalletConnection', 'true');
                        localStorage.setItem('pendingWalletTimestamp', Date.now().toString());
                        localStorage.setItem('lastConnectionAttemptUrl', window.location.href);
                        
                        console.log('跳转到MetaMask钱包App:', deepLink);
                        // 跳转到钱包App
                        window.location.href = deepLink;
                        return true; // 返回true表示已尝试连接
                    }
                }
            }
            
            // 记录要连接的钱包类型
            const requestedWalletType = walletType;
            let success = false;
            
            // 根据钱包类型调用不同的连接方法
            switch (requestedWalletType.toLowerCase()) {
                    case 'ethereum':
                case 'metamask':
                    success = await this.connectEthereum();
                        break;
                    case 'phantom':
                    success = await this.connectPhantom();
                        break;
                case 'solflare':
                    success = await this.connectSolflare();
                    break;
                case 'coinbase':
                    success = await this.connectCoinbase();
                    break;
                case 'slope':
                    success = await this.connectSlope();
                    break;
                case 'glow':
                    success = await this.connectGlow();
                    break;
                    default:
                    console.error(`不支持的钱包类型: ${requestedWalletType}`);
                    showError(`不支持的钱包类型: ${requestedWalletType}`);
                    return false;
                }
            
            // 如果连接成功
            if (success) {
                console.log(`${requestedWalletType}钱包连接成功`);
            
                // 关闭钱包选择器
                this.closeWalletSelector();
            
            // 更新UI
                this.updateUI();
                
                // 获取余额和资产
                try {
                    await this.getWalletBalance();
                    await this.getUserAssets(this.address);
                await this.checkIsAdmin();
                } catch (error) {
                    console.warn('获取钱包信息时出错:', error);
                }
                
                // 通知状态变化
                this.notifyStateChange({
                    type: 'connect',
                    address: this.address,
                    walletType: this.walletType
                });
                
                // 广播自定义事件
                document.dispatchEvent(new CustomEvent('walletConnected', {
                    detail: {
                        walletType: this.walletType,
                        address: this.address
                    }
                }));
            
                    return true;
            } else {
                console.log(`${requestedWalletType}钱包连接失败`);
                
                // 确保清除部分连接状态
                this.connected = false;
                this.walletType = null;
                this.address = null;
                
                // 更新UI
                this.updateUI();
                
                return false;
            }
        } catch (error) {
            console.error('连接钱包时出错:', error);
            showError('连接钱包时出错: ' + (error.message || '未知错误'));
            
            // 确保清除部分连接状态
            this.connected = false;
            this.walletType = null;
            this.address = null;
            
            // 更新UI
            this.updateUI();
            
                            return false;
        }
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
        try {
            console.log('断开钱包连接');
            
            // 如果没有连接钱包，不执行任何操作
            if (!this.connected || !this.walletType) {
                console.log('钱包未连接，无需断开');
                return;
            }
            
            // 根据钱包类型执行不同的断开操作
            if (this.walletType === 'ethereum' && window.ethereum) {
                console.log('断开以太坊钱包连接');
                // 以太坊钱包没有专门的断开连接方法，只需清除状态
                
                // 尝试移除事件监听器
                window.ethereum.removeAllListeners?.();
            } else if ((this.walletType === 'phantom' || this.walletType === 'solana') && window.solana) {
                console.log('断开Phantom钱包连接');
                try {
                    // 断开Phantom钱包连接
                    await window.solana.disconnect();
                } catch (err) {
                    console.error('断开Phantom钱包时出错:', err);
                }
                
                // 尝试移除事件监听器
                window.solana.removeAllListeners?.();
            }
            
            // 清除钱包状态
            this.clearState();
            
            // 清除存储中的钱包信息，但不触发页面刷新或重载
            this.clearStoredWalletData();
            
            // 触发断开连接事件，通知其他组件
            this.notifyStateChange({ type: 'disconnect' });
            
            // 更新UI
            this.updateUI();
            
            if (reload) {
                console.log('断开连接后重新加载页面');
                // 重新加载页面以确保状态完全重置
                setTimeout(() => {
                    window.location.reload();
                }, 100);
        } else {
                console.log('断开连接，但不重新加载页面');
                showSuccess('已断开钱包连接');
            }
        } catch (error) {
            console.error('断开钱包连接时出错:', error);
            showError('断开钱包连接时出错: ' + (error.message || '未知错误'));
            
            // 即使出错，也清除状态
            this.clearState();
            this.updateUI();
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
                        this.isAdmin = Boolean(data.is_admin || data.admin);
                        console.log(`从API获取到管理员状态: ${this.isAdmin ? '是管理员' : '不是管理员'}`);
                        
                        // 更新管理员链接
                        if (typeof window.updateAdminNavLink === 'function') {
                            window.updateAdminNavLink();
                        }
                        
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
        if (!this.connected || !this.address) {
            console.log('钱包未连接，无法获取余额');
            this.balance = 0;
            this.updateBalanceDisplay();
            return;
            }
            
            try {
            console.log(`获取钱包余额 - 地址: ${this.address}, 类型: ${this.walletType}`);
            
            // 构建API请求URL，添加时间戳防止缓存
            const timestamp = new Date().getTime();
            const url = `/api/wallet/balance?address=${this.address}&wallet_type=${this.walletType}&_=${timestamp}`;
            
            console.log(`请求余额API: ${url}`);
                const response = await fetch(url);
                
                if (response.ok) {
                    const data = await response.json();
                console.log('余额API返回数据:', data);
                
                // 增强USDC余额提取逻辑 - 支持更多种API返回格式
                let usdcBalance = null;
                
                // 详细的日志记录帮助调试
                if (!data) {
                    console.warn('API返回了空数据');
                } else if (typeof data !== 'object') {
                    console.warn('API返回的不是对象:', typeof data);
                } else {
                    console.log('尝试从API响应中解析余额信息');
                    
                    // 优先使用balances中的USDC余额（针对Phantom钱包）
                    if (data.balances && typeof data.balances === 'object' && data.balances.USDC !== undefined) {
                        usdcBalance = parseFloat(data.balances.USDC);
                        console.log('  从data.balances.USDC中获取到余额:', usdcBalance);
                    }
                    // 其次使用通用balance字段
                    else if (data.balance !== undefined) {
                        usdcBalance = parseFloat(data.balance);
                        console.log('  从data.balance中获取到余额:', usdcBalance);
                    } else if (data.usdc_balance !== undefined) {
                        usdcBalance = parseFloat(data.usdc_balance);
                        console.log('  从data.usdc_balance中获取到余额:', usdcBalance);
                    } else if (data.data && typeof data.data === 'object') {
                        if (data.data.balance !== undefined) {
                            usdcBalance = parseFloat(data.data.balance);
                            console.log('  从data.data.balance中获取到余额:', usdcBalance);
                        } else if (data.data.usdc_balance !== undefined) {
                            usdcBalance = parseFloat(data.data.usdc_balance);
                            console.log('  从data.data.usdc_balance中获取到余额:', usdcBalance);
                        }
                    } else if (data.result && typeof data.result === 'object') {
                        if (data.result.balance !== undefined) {
                            usdcBalance = parseFloat(data.result.balance);
                            console.log('  从data.result.balance中获取到余额:', usdcBalance);
                        } else if (data.result.usdc_balance !== undefined) {
                            usdcBalance = parseFloat(data.result.usdc_balance);
                            console.log('  从data.result.usdc_balance中获取到余额:', usdcBalance);
                        }
                    }
                    
                    // 如果上面的方法没有找到余额，尝试递归搜索对象的所有属性
                    if (usdcBalance === null) {
                        console.log('  未在常规位置找到余额，尝试递归搜索');
                        const findBalance = (obj, depth = 0) => {
                            if (depth > 3 || typeof obj !== 'object' || obj === null) return null;
                            
                            for (const key in obj) {
                                if (key === 'balance' || key === 'usdc_balance') {
                                    const value = parseFloat(obj[key]);
                                    if (!isNaN(value)) {
                                        console.log(`  在深度${depth}处找到余额 [${key}]:`, value);
                                        return value;
                                    }
                                } else if (typeof obj[key] === 'object' && obj[key] !== null) {
                                    const nestedResult = findBalance(obj[key], depth + 1);
                                    if (nestedResult !== null) return nestedResult;
                                }
                            }
                            return null;
                        };
                        
                        const foundBalance = findBalance(data);
                        if (foundBalance !== null) {
                            usdcBalance = foundBalance;
                            console.log('  递归搜索找到余额:', usdcBalance);
                        }
                    }
                }
                
                // 确保余额是有效数字，但如果API返回null或未找到，保留当前余额
                if (usdcBalance !== null) {
                    usdcBalance = isNaN(usdcBalance) ? 0 : usdcBalance;
                    this.balance = usdcBalance;
                    console.log(`设置新的USDC余额: ${this.balance}`);
                    } else {
                    console.warn('未能从API响应中提取有效余额，设置余额为null');
                        this.balance = null;
                }
                
                // 先更新UI显示
                this.updateBalanceDisplay();
                
                // 再触发事件通知其他组件（使用延时避免潜在循环）
                setTimeout(() => {
                this.triggerBalanceUpdatedEvent();
                }, 100);
                        
                return this.balance;
            } else {
                console.error('获取余额API失败:', response.status, response.statusText);
                this.balance = null;  // API请求失败时设置为null而不是0
                this.updateBalanceDisplay();
                return this.balance;
            }
        } catch (error) {
            console.error('获取余额出错:', error);
            this.balance = null;  // 出错时设置为null而不是0
            this.updateBalanceDisplay();
            return this.balance;
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
    updateBalanceDisplay() {
        try {
            console.log('更新余额显示, 余额:', this.balance);
                
            // 确保余额处理更准确
            let formattedBalance = '--';
            
            // 处理三种情况：null/undefined、0、有效数字
                if (this.balance === null || this.balance === undefined) {
                // 余额未获取到，显示为 '--'
                formattedBalance = '--';
                } else {
                // 转换为数字
                const numericBalance = parseFloat(this.balance);
                if (isNaN(numericBalance)) {
                    // 无效数字，显示为 '--'
                    formattedBalance = '--';
                } else {
                    // 有效数字(包括0)，格式化为两位小数
                    formattedBalance = numericBalance.toFixed(2);
                }
            }
            
            // 更新顶部导航栏显示地址而不是余额
            const walletBtnText = document.getElementById('walletBtnText');
            if (walletBtnText && this.connected && this.address) {
                const formattedAddress = this.formatAddress(this.address);
                walletBtnText.textContent = formattedAddress;
                console.log('更新钱包按钮文本为地址:', formattedAddress);
            }
            
            // 更新下拉菜单中的余额显示
            const dropdownBalanceElement = document.getElementById('walletBalanceInDropdown');
            if (dropdownBalanceElement) {
                dropdownBalanceElement.textContent = formattedBalance;
                console.log('更新下拉菜单余额显示:', formattedBalance);
            } else {
                console.warn('找不到下拉菜单余额显示元素(walletBalanceInDropdown)');
            }
            
            // 同时确保钱包地址也正确显示
            const walletAddressDisplay = document.getElementById('walletAddressDisplay');
            if (walletAddressDisplay && this.address) {
                const formattedAddress = this.formatAddress(this.address);
                walletAddressDisplay.textContent = formattedAddress;
                walletAddressDisplay.title = this.address; // 设置完整地址为悬停提示
                
                // 添加点击复制功能
                walletAddressDisplay.style.cursor = 'pointer';
                walletAddressDisplay.onclick = () => this.copyWalletAddress();
                
                console.log('更新钱包地址显示:', formattedAddress, '(完整地址:', this.address, ')');
            } else if (!walletAddressDisplay) {
                console.warn('找不到钱包地址显示元素(walletAddressDisplay)');
            }
            
            // 不再触发余额更新事件，以避免循环调用
            // this.triggerBalanceUpdatedEvent(); // 删除这行以防止循环调用
        } catch (error) {
            console.error('更新余额显示出错:', error);
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
        
        // 检查Phantom钱包是否安装
        if (!window.solana || !window.solana.isPhantom) {
            console.error('Phantom钱包未安装');
            
            // 在移动设备上，我们已经尝试过重定向到钱包App
            if (this.isMobile() && returningFromWallet) {
                showError('钱包连接未完成，请确保在Phantom App中授权连接');
            } else if (!isReconnect) {
                if (this.isMobile()) {
                    showError('请在Phantom App中打开本页面，或使用桌面浏览器');
                } else {
                    showError('请安装Phantom钱包浏览器扩展');
                }
            }
            return false;
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
     * 使用Solana钱包发送代币
     * @param {string} tokenSymbol 代币符号
     * @param {string} to 接收地址
     * @param {number} amount 转账金额
     * @returns {Promise<{success: boolean, txHash: string, error: string}>} 交易结果
     */
    async transferSolanaToken(tokenSymbol, to, amount) {
        try {
            console.log('使用Solana钱包转账');
            
            // 确保Phantom钱包已连接
            if (!window.solana || !window.solana.isPhantom) {
                console.error('Phantom钱包未安装或不可用');
                throw new Error('Phantom钱包未安装或不可用');
            }
            
            let fromAddress = '';
            
            // 检查钱包连接状态并获取地址
            if (!window.solana.isConnected || !window.solana.publicKey) {
                console.log('Phantom钱包未连接，尝试连接...');
                try {
                    // 尝试连接钱包
                    await window.solana.connect();
                    console.log('Phantom钱包连接成功');
                    
                    if (!window.solana.publicKey) {
                        throw new Error('连接成功但无法获取公钥');
                    }
                    
                    fromAddress = window.solana.publicKey.toString();
                } catch (connError) {
                    console.error('连接Phantom钱包失败:', connError);
                    throw new Error('无法连接到钱包: ' + (connError.message || '未知错误'));
                }
            } else {
                // 钱包已连接，直接获取地址
                fromAddress = window.solana.publicKey.toString();
                console.log('Phantom钱包已连接，地址:', fromAddress);
            }
            
            // 检查是否成功获取发送地址
            if (!fromAddress) {
                throw new Error('无法获取钱包地址');
            }
            
            // 检查接收地址是否有效
            if (!to || typeof to !== 'string' || to.length < 32) {
                console.error('无效的接收地址:', to);
                throw new Error('无效的接收地址');
            }
            
            // 检查金额
            if (!amount || isNaN(amount) || amount <= 0) {
                console.error('无效的转账金额:', amount);
                throw new Error('无效的转账金额');
            }
            
            console.log(`准备转账 ${amount} ${tokenSymbol} 到 ${to}`);
            console.log(`从地址: ${fromAddress}`);
            
            // 记录Phantom钱包版本和环境信息
            console.log('Phantom信息:', {
                isPhantom: window.solana.isPhantom,
                version: window.solana.version || '未知',
                isConnected: window.solana.isConnected,
                publicKey: fromAddress,
                isMobile: /Mobi|Android/i.test(navigator.userAgent),
                userAgent: navigator.userAgent
            });
            
            // 调用后端API执行真实的链上转账
            console.log('调用后端API执行转账...');
            const transferResponse = await fetch('/api/solana/execute_transfer_v2', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Eth-Address': fromAddress,
                        'X-Wallet-Address': fromAddress,
                        'X-Wallet-Type': 'phantom'
                    },
                    body: JSON.stringify({
                        token_symbol: tokenSymbol,
                        to_address: to,
                        amount: parseFloat(amount).toString(), // 使用parseFloat保留小数
                        from_address: fromAddress,
                        wallet_address: fromAddress // 额外添加钱包地址字段，增加兼容性
                    })
                });
                
            console.log('转账请求状态码:', transferResponse.status);
            
            if (!transferResponse.ok) {
                let errorText = '';
                try {
                    const errorJson = await transferResponse.json();
                    errorText = errorJson.error || '未知错误';
                } catch {
                    errorText = await transferResponse.text();
                }
                console.error('转账请求失败:', transferResponse.status, errorText);
                throw new Error('发送转账请求失败: ' + errorText);
            }
            
            const transferResult = await transferResponse.json();
            console.log('转账响应:', transferResult);
            
            if (!transferResult.success) {
                console.error('转账处理失败:', transferResult.error || '未知错误');
                throw new Error(`转账失败: ${transferResult.error || '未知错误'}`);
            }
            
            console.log('转账请求已发送！签名:', transferResult.signature);
            
            // 显示交易状态和签名
            this._showTransactionStatus(transferResult.signature, tokenSymbol, amount, to);
                
            // 返回成功结果
            return {
                success: true,
                txHash: transferResult.signature,
                status: transferResult.tx_status || 'processing'
            };
            
        } catch (error) {
            console.error('Solana转账失败:', error);
            // 记录错误详情
            console.error('错误详情:', {
                name: error.name,
                message: error.message,
                stack: error.stack,
                code: error.code
            });
            return {
                success: false,
                error: error.message || 'Solana转账失败'
            };
        }
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
            const connection = new window.solanaWeb3.Connection(
                window.SOLANA_NETWORK_URL || 'https://api.mainnet-beta.solana.com', // 从全局或默认
                'confirmed'
            );

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
    
    // 验证钱包连接和钱包地址
    if (!walletState.isConnected || !walletState.address) {
        console.error("钱包未连接或地址不可用");
        showError("请先连接钱包");
        if (modalErrorDiv) {
            modalErrorDiv.textContent = "请先连接钱包";
            modalErrorDiv.style.display = "block";
        }
        return;
    }
    
    // 验证传入的钱包地址（如果有）与当前连接的钱包地址是否一致
    if (purchaseData.wallet_address && purchaseData.wallet_address !== walletState.address) {
        console.warn(`传入的钱包地址(${purchaseData.wallet_address})与当前连接的钱包地址(${walletState.address})不一致，将使用当前连接的钱包地址`);
    }
    
    // 确保一定使用当前连接的钱包地址
    const walletAddress = walletState.address;
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
    
    // 获取当前资产ID - 使用多种方式尝试获取
    let assetId = document.getElementById('asset-id')?.value || 
                 document.querySelector('[data-asset-id]')?.getAttribute('data-asset-id');
    
    // 如果没找到，尝试从URL中获取
    if (!assetId) {
        const pathMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
        if (pathMatch && pathMatch[1]) {
            assetId = pathMatch[1];
            console.log("从URL中获取到资产ID:", assetId);
        }
    }
    
    // 如果页面上有token_symbol元素，也尝试获取
    if (!assetId) {
        const tokenSymbolElem = document.getElementById('token_symbol') || 
                               document.querySelector('.token-symbol');
        if (tokenSymbolElem) {
            assetId = tokenSymbolElem.textContent || tokenSymbolElem.value;
            console.log("从token_symbol元素获取到资产ID:", assetId);
        }
    }
    
    // 尝试从全局变量获取
    if (!assetId && window.assetData && window.assetData.token_symbol) {
        assetId = window.assetData.token_symbol;
        console.log("从全局变量获取到资产ID:", assetId);
    }
    
    if (!assetId) {
        console.error("无法获取资产ID，无法刷新资产信息");
        return;
    }
    
    // 使用加载动画
    const assetInfoSection = document.querySelector('.asset-details') || document.querySelector('.asset-info');
    if (assetInfoSection) {
        assetInfoSection.classList.add('loading');
    }
    
    // 调用API获取最新的资产信息
    console.log("正在获取资产信息, ID:", assetId);
    
    // 添加时间戳防止缓存
    const timestamp = new Date().getTime();
    let apiUrl = `/api/assets/${assetId}?_=${timestamp}`;
    
    // 尝试格式检测，对于RH-前缀的资产ID使用symbol API
    if (assetId.startsWith('RH-')) {
        apiUrl = `/api/assets/symbol/${assetId}?_=${timestamp}`;
        console.log("使用资产符号API:", apiUrl);
    }
    
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`获取资产信息失败: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("API返回数据:", data);
            
            // 处理不同的API响应格式
            let assetData = null;
            
            if (data.success === true && data.asset) {
                // 标准格式
                assetData = data.asset;
            } else if (data.success === true && data.data) {
                // 符号API格式
                assetData = data.data;
            } else if (data.token_symbol) {
                // 直接是资产对象
                assetData = data;
            } else {
                throw new Error("API响应格式不正确");
            }
            
            if (!assetData) {
                throw new Error("无法从API响应中提取资产数据");
            }
            
            console.log("获取到最新资产信息:", assetData);
            updateAssetInfoDisplay(assetData);
        })
        .catch(error => {
            console.error("刷新资产信息出错:", error);
            // 不显示错误提示，静默失败以避免用户体验问题
            console.log("刷新失败，但不影响用户操作");
        })
        .finally(() => {
            // 移除加载动画
            if (assetInfoSection) {
                assetInfoSection.classList.remove('loading');
            }
        });
}

/**
 * 更新页面上的资产信息显示
 * @param {Object} asset - 资产数据对象
 */
function updateAssetInfoDisplay(asset) {
    if (!asset) {
        console.error("资产数据为空，无法更新显示");
        return;
    }
    
    try {
        // 更新剩余数量
        const remainingSupplyElem = document.querySelector('.remaining-supply') || 
                                document.getElementById('remaining-supply');
        if (remainingSupplyElem && asset.remaining_supply !== undefined) {
            remainingSupplyElem.textContent = asset.remaining_supply;
        }
        
        // 更新总供应量
        const totalSupplyElem = document.querySelector('.total-supply') || 
                            document.getElementById('total-supply');
        if (totalSupplyElem && asset.total_supply !== undefined) {
            totalSupplyElem.textContent = asset.total_supply;
        }
        
        // 更新价格
        const priceElem = document.querySelector('.asset-price') || 
                        document.getElementById('asset-price') || 
                        document.getElementById('price-per-token');
        if (priceElem && (asset.price !== undefined || asset.price_per_token !== undefined)) {
            priceElem.textContent = asset.price || asset.price_per_token;
        }
        
        // 更新资产状态
        const statusElem = document.querySelector('.asset-status') || 
                        document.getElementById('asset-status');
        if (statusElem && asset.status !== undefined) {
            statusElem.textContent = asset.status;
            
            // 可选：根据状态更新UI样式
            if (asset.status === 'active' || asset.status === 'approved') {
                statusElem.classList.remove('status-inactive');
                statusElem.classList.add('status-active');
            } else {
                statusElem.classList.remove('status-active');
                statusElem.classList.add('status-inactive');
            }
        }
        
        // 更新"购买"按钮状态
        const buyButton = document.querySelector('.buy-button') || 
                        document.getElementById('buy-button');
        
        if (buyButton) {
            // 如果剩余供应量为0或状态不是active/approved，禁用购买按钮
            const validStatus = ['active', 'approved'].includes(asset.status);
            if ((asset.remaining_supply !== undefined && asset.remaining_supply <= 0) || !validStatus) {
                buyButton.disabled = true;
                buyButton.classList.add('disabled');
            } else {
                buyButton.disabled = false;
                buyButton.classList.remove('disabled');
            }
        }
        
        // 显示持有信息（如果有）
        if (asset.user_holdings && asset.user_holdings > 0) {
            const holdingsElem = document.querySelector('.user-holdings') || 
                            document.getElementById('user-holdings');
            if (holdingsElem) {
                holdingsElem.textContent = asset.user_holdings;
                
                // 显示持有信息区域
                const holdingsSection = document.querySelector('.holdings-section');
                if (holdingsSection) {
                    holdingsSection.style.display = 'block';
                }
            }
        }
        
        console.log("资产信息显示已更新");
    } catch (error) {
        console.error("更新资产信息显示出错:", error);
    }
}

function confirmPurchase() {
    console.log("购买确认数据:", purchaseData);
    
    // 验证字段是否齐全
    if (!purchaseData || !purchaseData.assetId || !purchaseData.amount || !purchaseData.tradeId) {
      showError("购买信息不完整，请重试");
      return;
    }
    
    // 显示加载状态
    $("#confirmPurchaseBtn").prop("disabled", true).html('<i class="fa fa-spinner fa-spin"></i> 处理中...');
    $("#cancelPurchaseBtn").prop("disabled", true);
    
    // 获取收款人地址和金额
    const recipientAddress = purchaseData.recipientAddress;
    const amount = parseFloat(purchaseData.amount);
    const assetId = purchaseData.assetId;
    const tradeId = purchaseData.tradeId;
    
    // 验证收款人地址
    if (!recipientAddress || recipientAddress.trim() === "") {
      showError("收款人地址无效");
      resetPurchaseButtons();
      return;
    }
    
    // 验证金额
    if (isNaN(amount) || amount <= 0) {
      showError("金额必须大于0");
      resetPurchaseButtons();
      return;
    }
    
    console.log(`准备发送 ${amount} USDC 到 ${recipientAddress}`);
    
    // 第一步：转移代币
    transferToken(
      recipientAddress, 
      amount.toString(), 
      "USDC",
      function(signature) {
        console.log("代币转移成功，交易签名:", signature);
        
        // 显示中间状态
        $("#confirmPurchaseBtn").html('<i class="fa fa-spinner fa-spin"></i> 确认中...');
        
        // 第二步：通知后端更新交易状态
        confirmPurchaseOnBackend(tradeId, signature);
      },
      function(error) {
        console.error("代币转移失败:", error);
        showError("代币转移失败: " + error);
        resetPurchaseButtons();
      }
    );
  }
  
  // 新增：后端确认购买
  function confirmPurchaseOnBackend(tradeId, txHash) {
    // 准备请求数据
    const requestData = {
      trade_id: tradeId,
      tx_hash: txHash
    };
    
    console.log("发送购买确认请求:", requestData);
    
    // 发送请求到后端API
    $.ajax({
      url: "/api/trades/confirm_purchase",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify(requestData),
      headers: {
        "X-Wallet-Address": getWalletAddress()
      },
      success: function(response) {
        console.log("购买确认响应:", response);
        
        if (response.success) {
          // 显示成功消息
          showSuccess("购买成功！资产将在几分钟内添加到您的钱包");
          
          // 关闭模态框
          setTimeout(function() {
            $("#purchaseModal").modal("hide");
            
            // 刷新资产信息
            if (typeof refreshAssetInfo === 'function') {
              refreshAssetInfo();
            } else if (typeof safeRefreshAssetInfo === 'function') {
              safeRefreshAssetInfo();
            }
            
            // 刷新用户资产列表
            if (typeof loadUserAssets === 'function') {
              loadUserAssets();
            }
          }, 2000);
        } else {
          showError("购买确认失败: " + (response.error || "未知错误"));
          resetPurchaseButtons();
        }
      },
      error: function(xhr, status, error) {
        console.error("购买确认请求失败:", xhr.responseText);
        let errorMessage = "购买确认请求失败";
        
        try {
          const response = JSON.parse(xhr.responseText);
          if (response.error) {
            errorMessage += ": " + response.error;
          }
        } catch (e) {
          errorMessage += ": " + error;
        }
        
        showError(errorMessage);
        resetPurchaseButtons();
      }
    });
  }
  
  // 重置购买按钮状态
  function resetPurchaseButtons() {
    $("#confirmPurchaseBtn").prop("disabled", false).html('确认购买');
    $("#cancelPurchaseBtn").prop("disabled", false);
  }

// 页面加载时自动检测从钱包应用返回的情况
(function detectWalletAppReturn() {
    // 检查是否有钱包应用相关的参数
    try {
        const pendingWalletType = localStorage.getItem('pendingWalletType');
        const pendingWalletConnection = localStorage.getItem('pendingWalletConnection');
        const pendingWalletTimestamp = localStorage.getItem('pendingWalletTimestamp');
        
        if (pendingWalletType && pendingWalletConnection === 'true') {
            console.log('页面加载时检测到可能从钱包应用返回', {
                type: pendingWalletType,
                timestamp: pendingWalletTimestamp
            });
            
            // 检查时间戳是否在合理范围内（5分钟内）
            const timestamp = parseInt(pendingWalletTimestamp, 10);
            const now = Date.now();
            const timeDiff = now - timestamp;
            
            if (timeDiff <= 5 * 60 * 1000) {
                console.log('时间戳在有效范围内，可能是从钱包应用返回');
                
                // 添加页面可见性变化监听，以便在页面变为可见时尝试连接钱包
                const visibilityHandler = function() {
                    if (document.visibilityState === 'visible') {
                        console.log('页面变为可见，尝试检查钱包连接状态');
                        // 如果钱包对象已初始化，则调用检查方法
                        if (window.wallet && typeof window.wallet.checkWalletConnection === 'function') {
                            window.wallet.checkWalletConnection();
                        }
                        // 移除事件监听器，避免重复处理
                        document.removeEventListener('visibilitychange', visibilityHandler);
                    }
                };
                
                // 添加事件监听器
                document.addEventListener('visibilitychange', visibilityHandler);
                
                // 添加一次性触发器，页面完全加载后自动检查
                if (document.readyState === 'complete') {
                    setTimeout(() => {
                        if (window.wallet && typeof window.wallet.checkWalletConnection === 'function') {
                            console.log('页面已加载完成，直接检查钱包连接状态');
                            window.wallet.checkWalletConnection();
                        }
                    }, 500);
                } else {
                    window.addEventListener('load', () => {
                        setTimeout(() => {
                            if (window.wallet && typeof window.wallet.checkWalletConnection === 'function') {
                                console.log('页面加载事件触发，检查钱包连接状态');
                                window.wallet.checkWalletConnection();
                            }
                        }, 500);
                    });
                }
            } else {
                console.log('时间戳已过期，清除钱包连接尝试状态');
                localStorage.removeItem('pendingWalletType');
                localStorage.removeItem('pendingWalletConnection');
                localStorage.removeItem('pendingWalletTimestamp');
                localStorage.removeItem('lastConnectionAttemptUrl');
            }
        }
    } catch (error) {
        console.error('检查钱包应用返回状态出错:', error);
    }
})();