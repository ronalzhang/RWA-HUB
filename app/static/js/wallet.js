/**
 * RWA-HUB 钱包管理模块
 * 支持多种钱包类型的连接、管理和状态同步
 */

// 防止重复加载
if (window.RWA_WALLET_LOADED) {
    console.warn('Wallet script already loaded, skipping...');
    return;
}
window.RWA_WALLET_LOADED = true;

// 添加调试模式检查 - 只在开发环境或明确启用时输出详细日志
const DEBUG_MODE = window.location.hostname === 'localhost' || 
                   window.location.hostname === '127.0.0.1' || 
                   window.DEBUG_MODE === true;

// 调试日志函数
function debugLog(...args) {
    if (DEBUG_MODE) {
        console.log(...args);
    }
}

function debugWarn(...args) {
    if (DEBUG_MODE) {
        console.warn(...args);
    }
}

function debugError(...args) {
    // 错误总是显示，但在非调试模式下简化
    if (DEBUG_MODE) {
        console.error(...args);
    } else {
        console.error(args[0]); // 只显示第一个参数（主要错误信息）
    }
}

// 钱包状态管理类
const walletState = {
    // 状态变量
    address: null,             // 当前连接的钱包地址
    walletType: null,          // 当前连接的钱包类型: 'ethereum', 'phantom' 等
    connected: false,          // 是否已连接钱包
    isAdmin: false,            // 是否是管理员账户
    balance: 0,                // 当前钱包余额
    commissionBalance: 0,      // 分佣余额
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
                    
                    // 节流处理，延迟执行避免频繁调用
                    if (!this._storageChangeTimer) {
                        this._storageChangeTimer = setTimeout(() => {
                            this.handleStorageChange();
                            this._storageChangeTimer = null;
                        }, 2000);
                    }
                }
            });
            
            // 确保钱包状态与本地存储一致
            this.checkWalletConsistency();
            
            // 设置定期检查，但降低频率以减轻服务器负担
            setInterval(() => this.checkWalletConsistency(), 30000); // 30秒检查一次
            
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
    checkWalletConsistency(forceUpdate = false) {
        try {
            // 防止频繁处理
            const now = Date.now();
            if (!forceUpdate && this._lastConsistencyCheck && (now - this._lastConsistencyCheck) < 3000) {
                // 减少重复日志 - 只在debug模式下显示
                if (DEBUG_MODE && (!this._lastSkipLog || (now - this._lastSkipLog > 10000))) {
                    debugLog('短时间内已处理过一致性检查，跳过');
                    this._lastSkipLog = now;
                }
                return;
            }
            this._lastConsistencyCheck = now;
            
            // 检查本地存储
            const storedAddress = localStorage.getItem('walletAddress');
            const storedType = localStorage.getItem('walletType');
            
            // 1. 本地存储有钱包信息，但内存状态未连接
            if (storedAddress && storedType && (!this.connected || !this.address || this.address !== storedAddress || this.walletType !== storedType)) {
                debugLog('检测到状态不一致：本地存储有钱包信息但状态不匹配', {
                    stored: { address: storedAddress, type: storedType },
                    current: { address: this.address, type: this.walletType, connected: this.connected }
                });
                
                // 防止无限循环重连
                if (!this._isReconnecting) {
                    this._isReconnecting = true;
                    
                    // 更新内存状态
                    this.walletType = storedType;
                    this.address = storedAddress;
                    this.connected = true;
                    
                    // 更新UI
                    this.updateUI();
                    
                    // 如果浏览器支持该钱包类型，尝试静默重连
                    let canReconnect = false;
                    
                    if (storedType === 'ethereum' && window.ethereum) {
                        canReconnect = true;
                    } else if ((storedType === 'phantom' || storedType === 'solana') && 
                              window.solana && window.solana.isPhantom) {
                        canReconnect = true;
                    }
                    
                    if (canReconnect) {
                        // 使用setTimeout避免阻塞UI线程
                        setTimeout(async () => {
                            try {
                                debugLog('尝试静默重连钱包...');
                                if (storedType === 'ethereum') {
                                    await this.connectEthereum(true);
                                } else if (storedType === 'phantom' || storedType === 'solana') {
                                    await this.connectPhantom(true);
                                }
                            } catch (err) {
                                debugError('静默重连失败:', err);
                            } finally {
                                this._isReconnecting = false;
                            }
                            
                            // 更新余额和资产信息（有限频率）
                            if (!this._lastBalanceCheck || (now - this._lastBalanceCheck > 30000)) {
                                this._lastBalanceCheck = now;
                                this.getWalletBalance().catch(err => debugError('获取余额失败:', err));
                            }
                            
                            if (!this._lastAssetsCheck || (now - this._lastAssetsCheck > 60000)) {
                                this._lastAssetsCheck = now;
                                this.getUserAssets(this.address).catch(err => debugError('获取资产失败:', err));
                            }
                        }, 0);
                    } else {
                        this._isReconnecting = false;
                    }
                }
            } 
            // 2. 本地存储没有钱包信息，但内存状态显示已连接
            else if ((!storedAddress || !storedType) && this.connected && this.address) {
                debugLog('检测到状态不一致：状态显示已连接但本地存储无钱包信息');
                // 断开连接，不刷新页面
                this.disconnect(false);
            }
            // 3. 保持一致性
            else if (this.connected && this.address && this.walletType) {
                if (!localStorage.getItem('walletAddress') || !localStorage.getItem('walletType')) {
                    localStorage.setItem('walletAddress', this.address);
                    localStorage.setItem('walletType', this.walletType);
                }
            }
        } catch (err) {
            debugError('钱包状态一致性检查失败:', err);
        }
    },
    
    /**
     * 处理localStorage变化，同步钱包状态
     */
    async handleStorageChange() {
        // 委托给checkWalletConsistency函数，强制执行更新
        this.checkWalletConsistency(true);
    },
    
    // 为资产详情页提供的购买按钮状态更新函数
    updateDetailPageButtonState() {
        // 防止由triggerWalletStateChanged引起的循环调用
        if (this._internalUpdate) {
            debugLog('跳过内部更新，避免循环调用');
            return;
        }
        
        // 防止短时间内重复调用
        const now = Date.now();
        if (this._lastButtonUpdateTime && (now - this._lastButtonUpdateTime) < 800) {
            debugLog('购买按钮状态更新过于频繁，跳过此次更新');
            return;
        }
        this._lastButtonUpdateTime = now;
        
        // 减少日志频率
        if (!this._lastButtonLog || (now - this._lastButtonLog > 3000)) {
            debugLog('购买按钮状态更新函数被调用');
            this._lastButtonLog = now;
        }
        
        // 先确保钱包状态一致
        this.checkWalletConsistency();
        
        // 获取购买按钮
        const buyButton = document.getElementById('buy-button');
        if (!buyButton) {
            debugWarn('找不到购买按钮元素，无法更新状态');
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
            buyButton.innerHTML = '<i class="fas fa-wallet me-2"></i>Please Connect Wallet';
            buyButton.title = 'Please Connect Wallet';
        }
        
        // 如果存在分红按钮检查函数，也一并调用，但避免引起循环
        if (typeof window.checkDividendManagementAccess === 'function' && !this._checkingDividend) {
            try {
                this._checkingDividend = true;
                window.checkDividendManagementAccess();
                this._checkingDividend = false;
            } catch (error) {
                debugError('分红按钮检查失败:', error);
                this._checkingDividend = false;
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
     * @returns {Promise<boolean>} 钱包是否仍然连接
     */
    async checkWalletConnection() {
        try {
            console.log('检查钱包连接状态');
            if (!this.connected || !this.address || !this.walletType) {
                console.log('钱包未连接状态，跳过检查');
                return false;
            }
            
            let isConnected = false;
            
            // 根据钱包类型检查连接
            if (this.walletType === 'ethereum') {
                if (window.ethereum) {
                    const accounts = await window.ethereum.request({ method: 'eth_accounts' });
                    isConnected = accounts && accounts.length > 0 && accounts[0].toLowerCase() === this.address.toLowerCase();
                    
                    if (isConnected && this.chainId !== window.ethereum.chainId) {
                        // 更新chainId
                        this.chainId = window.ethereum.chainId;
                        console.log('更新以太坊链ID:', this.chainId);
                    }
                }
            } else if (this.walletType === 'phantom' || this.walletType === 'solana') {
                if (window.solana && window.solana.isPhantom) {
                    isConnected = window.solana.isConnected && window.solana.publicKey && window.solana.publicKey.toString() === this.address;
                }
            }
            
            console.log('钱包连接状态检查结果:', isConnected ? '已连接' : '已断开');
            
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
     * 统一的钱包连接方法
     * @param {string} walletType - 钱包类型
     * @returns {Promise<boolean>} 连接是否成功
     */
    async connect(walletType) {
        console.log(`尝试连接钱包: ${walletType}`);
        this.connecting = true;
        this.updateUI();
        
        // 在移动设备上，首先尝试跳转到钱包应用
        if (this.isMobile() && !this._isReconnecting) {
            console.log('检测到移动设备，尝试跳转到钱包应用');
            const deepLinkSuccess = await this.tryMobileWalletRedirect(walletType);
            if (deepLinkSuccess) {
                // 跳转成功，等待用户从钱包app返回
                console.log('深度链接跳转成功，等待用户从钱包应用返回');
                this.connecting = false;
                this.updateUI();
                return true; // 返回true表示跳转成功，但连接状态待定
            }
        }
        
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
                
                // 为用户提供重试选项
                if (walletType === 'phantom') {
                    this.showPhantomRetryOption();
                }
                
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
            // 减少日志输出频率
            if (!this._lastUIUpdate || (Date.now() - this._lastUIUpdate > 2000)) {
                debugLog('更新钱包UI, 连接状态:', this.connected);
                this._lastUIUpdate = Date.now();
            }
            
            // 获取UI元素
            const walletBtn = document.getElementById('walletBtn');
            const walletBtnText = document.getElementById('walletBtnText');
            const walletAddressDisplay = document.getElementById('walletAddressDisplay');
            const walletMenu = document.getElementById('walletMenu');
            const adminEntry = document.getElementById('adminEntry');
            
            if (!walletBtn) {
                debugWarn('找不到钱包按钮元素');
                return;
            }
            
        if (this.connected && this.address) {
                // 钱包已连接状态
                if (walletBtnText) {
                    // 显示格式化的地址而不是余额
                    const formattedAddress = this.formatAddress(this.address);
                    walletBtnText.textContent = formattedAddress;
                    debugLog('已设置按钮文本为地址:', formattedAddress);
                }
                
                // 确保下拉菜单中的钱包地址显示正确
                if (walletAddressDisplay) {
                    const formattedAddress = this.formatAddress(this.address);
                    walletAddressDisplay.textContent = formattedAddress;
                    walletAddressDisplay.title = this.address; // 设置完整地址为悬停提示
                    debugLog('已设置地址显示:', formattedAddress);
                } else {
                    debugWarn('找不到钱包地址显示元素 walletAddressDisplay');
                }
                
                // 更新下拉菜单中的余额显示
                const dropdownBalanceElement = document.getElementById('walletBalanceInDropdown');
                if (dropdownBalanceElement) {
                    const formattedBalance = this.balance !== null ? parseFloat(this.balance).toFixed(2) : '0.00';
                    dropdownBalanceElement.textContent = formattedBalance;
                    debugLog('已设置下拉菜单余额显示:', formattedBalance);
                } else {
                    debugWarn('找不到余额显示元素 walletBalanceInDropdown');
                }
                
                // 显示用户资产部分
                const userAssetsSection = document.getElementById('userAssetsSection');
                if (userAssetsSection) {
                    userAssetsSection.style.display = 'block';
                }
                
                // 根据管理员状态更新管理员入口显示
                if (adminEntry) {
                    debugLog('更新管理员入口显示, 当前管理员状态:', this.isAdmin);
                    adminEntry.style.display = this.isAdmin ? 'block' : 'none';
                }
                
                // 确保余额也更新
                this.updateBalanceDisplay();
            } else {
                // 钱包未连接状态
                if (walletBtnText) {
                    walletBtnText.textContent = window._ ? window._('Connect Wallet') : 'Connect Wallet';
                    debugLog('已设置按钮文本为连接钱包');
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
                debugWarn('触发钱包状态变化事件失败:', e);
            }
        } catch (error) {
            debugError('更新UI出错:', error);
        }
    },
    
    /**
     * 触发钱包状态变化事件
     * 通知其他组件钱包状态已变化
     */
    triggerWalletStateChanged(details = {}) {
        try {
            // 减少重复日志输出频率
            const now = Date.now();
            if (!this._lastStateChangeLog || (now - this._lastStateChangeLog > 5000)) {
                debugLog('[triggerWalletStateChanged] 详情页按钮状态已更新');
                this._lastStateChangeLog = now;
            }
            
            // 防止循环更新
            this._internalUpdate = true;
            
            try {
                // 创建自定义事件，包含当前钱包状态
                const walletEvent = new CustomEvent('walletStateChanged', {
                    detail: { 
                        address: this.address,
                        walletType: this.walletType,
                        connected: this.connected,
                        isAdmin: this.isAdmin,
                        balance: this.balance,
                        chainId: this.chainId,
                        assets: this.assets || [],
                        ...details
                    }
                });
                
                // 分发事件到文档对象
                document.dispatchEvent(walletEvent);
                
                // 通知状态变化回调
                this.notifyStateChange(details);
                
                // 如果在详情页，更新购买按钮状态
                if (window.location.pathname.includes('/detail/') || window.location.pathname.includes('/RH-')) {
                    // 延迟一点执行，避免与事件处理冲突
                    setTimeout(() => {
                        try {
                        this.updateDetailPageButtonState();
                        } catch (buttonError) {
                            debugError('[triggerWalletStateChanged] 更新按钮状态失败:', buttonError);
                        }
                    }, 50);
                }
                
            } finally {
                // 确保清除内部更新标志
                setTimeout(() => {
                    this._internalUpdate = false;
                }, 100);
            }
        } catch (error) {
            debugError('[triggerWalletStateChanged] 触发钱包状态变化事件失败:', error);
            this._internalUpdate = false;
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
            
            // 安全修复：删除本地硬编码的管理员列表和备用判断
            // 如果API检查失败，默认为非管理员
            console.log('API管理员检查失败，默认为非管理员');
            this.isAdmin = false;
            
            // 清除可能存在的管理员状态
            localStorage.removeItem('isAdmin');
            
            // 更新管理员显示
            this.updateAdminDisplay();
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
            // 只有在用户明确需要管理员功能时才进行检查
            const needsAdminCheck = this.shouldCheckAdminStatus();
            if (!needsAdminCheck) {
                return; // 跳过不必要的管理员检查
            }
            
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
            
            // 检查是否在资产详情页，如果是则更新分红入口（仅管理员）
            const isDetailPage = document.querySelector('.asset-detail-page') !== null;
            if (isDetailPage && this.isAdmin) {
                // 检查是否有缓存的分红权限结果
                const cachedResult = window.dividendPermissionCache;
                
                console.log('检查分红权限缓存:', {
                    hasCached: !!cachedResult,
                    cachedPermission: cachedResult ? cachedResult.hasPermission : null,
                    isAdmin: this.isAdmin,
                    address: this.address
                });
                
                // 特殊处理：如果管理员状态为true但缓存权限为false，清除缓存强制重新检查
                if (this.isAdmin && cachedResult && cachedResult.hasPermission === false) {
                    console.log('🔄 管理员状态为true但缓存权限为false，清除缓存强制重新检查');
                    window.dividendPermissionCache = null;
                    this._lastDividendCheckTime = 0; // 重置节流时间
                    
                    // 立即触发权限检查，不受节流限制
                    if (typeof window.checkDividendManagementAccess === 'function') {
                        console.log('强制重新检查分红管理权限');
                        window.checkDividendManagementAccess();
                    } else {
                        console.log('checkDividendManagementAccess不可用，使用备用方案');
                        this.createOrShowDividendButtons();
                    }
                    return; // 直接返回，避免后续节流检查
                }
                
                const hasCachedPermission = cachedResult &&
                    (Date.now() - cachedResult.timestamp) < 30000 && // 30秒缓存
                    cachedResult.hasPermission === true &&
                    cachedResult.address === this.address;
                
                if (hasCachedPermission) {
                    console.log('检测到缓存的分红权限，直接显示按钮');
                    if (typeof window.showDividendButtons === 'function') {
                        window.showDividendButtons(this.address);
                    } else {
                        this.createOrShowDividendButtons();
                    }
                    return;
                }
                
                // 获取当前时间用于节流检查
                const now = Date.now();
                
                // 优化节流机制：
                // 1. 如果是管理员且没有缓存，立即检查（不受节流限制）
                // 2. 否则使用3秒节流
                const shouldSkipThrottle = this.isAdmin && !cachedResult;
                const throttleInterval = shouldSkipThrottle ? 0 : 3000;
                const shouldCheck = !this._lastDividendCheckTime || (now - this._lastDividendCheckTime > throttleInterval);
                
                if (shouldCheck) {
                    this._lastDividendCheckTime = now;
                    
                    if (typeof window.checkDividendManagementAccess === 'function') {
                        const checkType = shouldSkipThrottle ? '立即检查' : '常规检查';
                        console.log(`检测到资产详情页，${checkType}分红入口状态`);
                        window.checkDividendManagementAccess();
                    } else {
                        console.log('分红权限检查函数不可用，使用备用方案');
                        this.createOrShowDividendButtons();
                    }
                } else {
                    console.log('分红检查被节流，跳过本次调用');
                }
            }
        } catch (error) {
            console.error('更新管理员显示状态失败:', error);
        }
    },
    
    /**
     * 判断是否需要检查管理员状态
     * 减少不必要的管理员权限检查
     */
    shouldCheckAdminStatus() {
        // 1. 如果页面中有管理员入口元素，则需要检查
        if (document.getElementById('adminEntry')) {
            return true;
        }
        
        // 2. 如果在管理员页面，则需要检查
        if (window.location.pathname.includes('/admin')) {
            return true;
        }
        
        // 3. 如果页面有分红管理相关元素，则需要检查
        if (document.querySelector('[id*="dividend"], [class*="dividend"]')) {
            return true;
        }
        
        // 4. 如果用户明确点击了管理相关按钮，则需要检查
        if (window._userRequestedAdminCheck) {
            window._userRequestedAdminCheck = false; // 重置标志
            return true;
        }
        
        // 其他情况不需要检查管理员状态
        return false;
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
            
            // 修复：改进资产符号获取逻辑，添加多种获取方式
            let tokenSymbol = null;
            
            // 方式1: 从全局ASSET_CONFIG获取
            if (window.ASSET_CONFIG && window.ASSET_CONFIG.tokenSymbol) {
                tokenSymbol = window.ASSET_CONFIG.tokenSymbol;
                console.log('从ASSET_CONFIG获取资产符号:', tokenSymbol);
            }
            
            // 方式2: 从现有按钮的data属性获取
            if (!tokenSymbol && dividendBtn) {
                tokenSymbol = dividendBtn.getAttribute('data-token-symbol');
                console.log('从现有按钮获取资产符号:', tokenSymbol);
            }
            
            // 方式3: 从页面中任何包含data-token-symbol的元素获取
            if (!tokenSymbol) {
                const tokenElement = document.querySelector('[data-token-symbol]');
                if (tokenElement) {
                    tokenSymbol = tokenElement.getAttribute('data-token-symbol');
                    console.log('从页面元素获取资产符号:', tokenSymbol);
                }
            }
            
            // 方式4: 从URL路径中提取
            if (!tokenSymbol) {
                const urlMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
                if (urlMatch && urlMatch[1]) {
                    tokenSymbol = urlMatch[1];
                    console.log('从URL路径获取资产符号:', tokenSymbol);
                }
            }
            
            // 方式5: 从页面元数据获取
            if (!tokenSymbol) {
                const metaTokenSymbol = document.querySelector('meta[name="asset-token-symbol"]');
                if (metaTokenSymbol) {
                    tokenSymbol = metaTokenSymbol.getAttribute('content');
                    console.log('从页面元数据获取资产符号:', tokenSymbol);
                }
            }
            
            if (!tokenSymbol) {
                console.error('所有方式都无法获取资产符号，分红按钮创建失败');
                return;
            }
            
            console.log('最终使用的资产符号:', tokenSymbol);
            
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
                    dividendBtn.setAttribute('data-token-symbol', tokenSymbol);
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
                    dividendBtnMobile.setAttribute('data-token-symbol', tokenSymbol);
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
                    dividendBtnMedium.setAttribute('data-token-symbol', tokenSymbol);
                    dividendBtnMedium.innerHTML = '<i class="fas fa-coins me-2"></i>Dividend Management';
                    
                    // 添加到容器中
                    mediumButtonContainer.appendChild(dividendBtnMedium);
                    console.log('成功创建中屏分红管理按钮');
                }
            }
            
            console.log('分红按钮创建或更新完成');
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
            if (!this.connected || !this.address) {
                debugWarn('[getWalletBalance] 钱包未连接，无法获取余额');
                return 0;
            }

            const address = this.address;
            debugLog(`[getWalletBalance] 开始获取 ${address} 的钱包余额`);

            // 修复：根据钱包类型获取余额
            let tokenSymbol = 'USDC'; // 默认获取USDC余额
            
            if (this.walletType === 'ethereum') {
                tokenSymbol = 'USDC'; // 以太坊也获取USDC
            } else if (this.walletType === 'phantom' || this.walletType === 'solana') {
                tokenSymbol = 'USDC'; // Solana获取USDC
            }

            // 修复：使用正确的API路径
            const apiUrl = `/api/service/wallet/token_balance?address=${address}&token=${tokenSymbol}&_=${Date.now()}`;
            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': address,
                    'X-Wallet-Type': this.walletType
                }
            });

            if (!response.ok) {
                throw new Error(`API响应错误: ${response.status} ${response.statusText}`);
            }

                        const data = await response.json();
            
            // 减少重复的API响应日志 - 只在debug模式或有错误时显示详细信息
            if (DEBUG_MODE || !data.success) {
                debugLog('[getWalletBalance] API响应数据:', data);
            }

            if (data.success) {
                const balance = parseFloat(data.balance || 0);
                
                // 减少重复的余额日志
                if (!this._lastBalanceLog || Math.abs(this.balance - balance) > 0.01 || 
                    (Date.now() - this._lastBalanceLog > 30000)) {
                    debugLog(`[getWalletBalance] 通过API获取到钱包余额: ${balance} ${data.symbol || tokenSymbol}`);
                    this._lastBalanceLog = Date.now();
                }
                
                // 更新余额
                this.balance = balance;
                this.updateBalanceDisplay(balance);
                
                // 触发余额更新事件
                this.triggerBalanceUpdatedEvent();
                
                return balance;
            } else {
                const errorMsg = data.error || '获取余额失败';
                debugError('[getWalletBalance] 获取余额失败:', errorMsg);
                
                // 在失败时尝试后备方案，但不记录过多日志
                return await this.getBalanceWithFallback(address, tokenSymbol);
            }
        } catch (error) {
            debugError('[getWalletBalance] 获取钱包余额出错:', error);
            
            // 尝试后备方案
            try {
                return await this.getBalanceWithFallback(this.address, 'USDC');
            } catch (fallbackError) {
                debugError('[getWalletBalance] 后备方案也失败:', fallbackError);
                    return 0;
                }
        }
    },
    
    /**
     * 优化的Solana库加载检查
     * 减少超时时间，改进错误处理
     */
    async ensureSolanaLibrariesOptimized() {
        // 如果库已经加载，直接返回
        if (window.solanaWeb3 && window.solanaWeb3.Connection && window.spl_token && window.spl_token.getAssociatedTokenAddress) {
            console.log('[ensureSolanaLibrariesOptimized] 库已完全加载，直接返回');
            return true;
        }
        
        console.log('[ensureSolanaLibrariesOptimized] 开始检查和加载Solana库');
        
        // 缩短超时时间到10秒，并使用更智能的检查
        const maxWaitTime = 10000; // 10秒超时
        const checkInterval = 200; // 减少检查间隔到200ms
        let elapsedTime = 0;
        
        // 尝试多种方法获取库
        const tryLoadLibraries = () => {
            console.log('[ensureSolanaLibrariesOptimized] 尝试加载库...');
            
            // 方法1: 检查全局对象
            if (typeof window.solanaWeb3 === 'undefined' && typeof SolanaWeb3 !== 'undefined') {
                window.solanaWeb3 = SolanaWeb3;
                console.log('[ensureSolanaLibrariesOptimized] 从SolanaWeb3全局对象加载');
            }
            
            if (typeof window.spl_token === 'undefined' && typeof window.splToken !== 'undefined') {
                window.spl_token = window.splToken;
                console.log('[ensureSolanaLibrariesOptimized] 从splToken全局对象加载');
            }
            
            if (typeof window.spl_token === 'undefined' && typeof SolanaToken !== 'undefined') {
                window.spl_token = SolanaToken;
                console.log('[ensureSolanaLibrariesOptimized] 从SolanaToken全局对象加载');
            }
            
            // 方法2: 尝试从CDN动态加载（如果没有）
            if (!window.solanaWeb3 && !this._loadingWeb3) {
                this._loadingWeb3 = true;
                this.loadSolanaWeb3FromCDN();
            }
        };
        
        // 立即尝试一次
        tryLoadLibraries();
        
        // 检查循环
        while (elapsedTime < maxWaitTime) {
            // 检查核心库
            if (window.solanaWeb3 && window.solanaWeb3.Connection) {
                console.log('[ensureSolanaLibrariesOptimized] Solana Web3库检查通过');
                
                // 检查SPL Token库
                if (window.spl_token && window.spl_token.getAssociatedTokenAddress) {
                    console.log('[ensureSolanaLibrariesOptimized] SPL Token库检查通过');
                    return true;
                }
                
                // 如果只有Web3但没有SPL Token，创建基本接口
                if (!window.spl_token || !window.spl_token.getAssociatedTokenAddress) {
                    console.log('[ensureSolanaLibrariesOptimized] 创建基本SPL Token接口');
                    if (this.createBasicSplTokenInterface()) {
                        console.log('[ensureSolanaLibrariesOptimized] 基本SPL Token接口创建成功');
                        return true;
                    }
                }
            }
            
            await new Promise(resolve => setTimeout(resolve, checkInterval));
            elapsedTime += checkInterval;
            
            // 每2秒重新尝试加载
            if (elapsedTime % 2000 === 0) {
                tryLoadLibraries();
            }
        }
        
        // 超时后尝试创建最小接口
        console.warn('[ensureSolanaLibrariesOptimized] 库加载超时，尝试创建基本接口');
        if (window.solanaWeb3 && window.solanaWeb3.Connection) {
            return this.createBasicSplTokenInterface();
        }
        
        // 最后的回退方案
        return this.createMinimalSolanaInterface();
    },
    
    /**
     * 从CDN动态加载Solana Web3库
     */
    async loadSolanaWeb3FromCDN() {
        if (this._web3Loading) return;
        this._web3Loading = true;
        
        try {
            console.log('[loadSolanaWeb3FromCDN] 开始从CDN加载Solana Web3库');
            
            const script = document.createElement('script');
            script.src = 'https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js';
            script.async = true;
            
            const loadPromise = new Promise((resolve, reject) => {
                script.onload = () => {
                    console.log('[loadSolanaWeb3FromCDN] CDN加载成功');
                    if (window.solanaWeb3js) {
                        window.solanaWeb3 = window.solanaWeb3js;
                    }
                    resolve();
                };
                script.onerror = reject;
                setTimeout(reject, 10000); // 10秒超时
            });
            
            document.head.appendChild(script);
            await loadPromise;
        } catch (error) {
            console.warn('[loadSolanaWeb3FromCDN] CDN加载失败:', error);
        } finally {
            this._web3Loading = false;
        }
    },
    
    /**
     * 创建基本的SPL Token接口
     */
    createBasicSplTokenInterface() {
        if (!window.solanaWeb3 || !window.solanaWeb3.PublicKey) {
            console.error('[createBasicSplTokenInterface] 缺少Solana Web3基础库');
            return false;
        }
        
        try {
            console.log('[createBasicSplTokenInterface] 创建基本SPL Token接口');
            
            window.spl_token = {
                TOKEN_PROGRAM_ID: new window.solanaWeb3.PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'),
                ASSOCIATED_TOKEN_PROGRAM_ID: new window.solanaWeb3.PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'),
                
                getAssociatedTokenAddress: async function(mint, owner, allowOffCurve = false, programId = this.TOKEN_PROGRAM_ID, associatedTokenProgramId = this.ASSOCIATED_TOKEN_PROGRAM_ID) {
                    const [address] = await window.solanaWeb3.PublicKey.findProgramAddress(
                        [
                            owner.toBuffer(),
                            programId.toBuffer(),
                            mint.toBuffer(),
                        ],
                        associatedTokenProgramId
                    );
                    return address;
                },
                
                // 简化的创建ATA指令函数 - 现在主要用于兼容性
                createAssociatedTokenAccountInstruction: function(payer, associatedToken, owner, mint, programId = null, associatedTokenProgramId = null) {
                    // 确保使用正确的程序ID
                    const tokenProgramId = programId || this.TOKEN_PROGRAM_ID;
                    const ataProgramId = associatedTokenProgramId || this.ASSOCIATED_TOKEN_PROGRAM_ID;
                    
                    console.log('[createAssociatedTokenAccountInstruction] 创建ATA指令');
                    console.log('  payer:', payer.toString());
                    console.log('  associatedToken:', associatedToken.toString());
                    console.log('  owner:', owner.toString());
                    console.log('  mint:', mint.toString());
                    console.log('  tokenProgramId:', tokenProgramId.toString());
                    console.log('  ataProgramId:', ataProgramId.toString());
                    
                    const keys = [
                        { pubkey: payer, isSigner: true, isWritable: true },
                        { pubkey: associatedToken, isSigner: false, isWritable: true },
                        { pubkey: owner, isSigner: false, isWritable: false },
                        { pubkey: mint, isSigner: false, isWritable: false },
                        { pubkey: window.solanaWeb3.SystemProgram.programId, isSigner: false, isWritable: false },
                        { pubkey: tokenProgramId, isSigner: false, isWritable: false },
                        { pubkey: window.solanaWeb3.SYSVAR_RENT_PUBKEY, isSigner: false, isWritable: false },
                    ];
                    
                    const data = new Uint8Array(0);
                    
                    const instruction = new window.solanaWeb3.TransactionInstruction({
                        keys,
                        programId: ataProgramId,
                        data,
                    });
                    
                    console.log('[createAssociatedTokenAccountInstruction] ATA指令创建完成，programId:', instruction.programId.toString());
                    return instruction;
                },
                
                // 简化的转账指令函数 - 现在主要用于兼容性，实际使用手动构建的版本
                createTransferInstruction: function(source, destination, owner, amount, multiSigners = [], programId = null) {
                    console.log('[createTransferInstruction] 创建转账指令');
                    
                    // 确保使用正确的程序ID
                    const tokenProgramId = programId || this.TOKEN_PROGRAM_ID;
                    
                    console.log('  source:', source.toString());
                    console.log('  destination:', destination.toString());
                    console.log('  owner:', owner.toString());
                    console.log('  amount:', amount.toString());
                    console.log('  tokenProgramId:', tokenProgramId.toString());
                    
                    const keys = [
                        { pubkey: source, isSigner: false, isWritable: true },
                        { pubkey: destination, isSigner: false, isWritable: true },
                        { pubkey: owner, isSigner: multiSigners.length === 0, isWritable: false },
                    ];
                    
                    multiSigners.forEach(signer => {
                            keys.push({ pubkey: signer, isSigner: true, isWritable: false });
                    });
                    
                    // 构建指令数据
                    const data = new Uint8Array(9);
                    data[0] = 3; // Transfer instruction discriminator
                    
                    // 将金额编码为Little Endian 64位整数
                    const amountValue = Number(amount); // 确保是数字类型
                    const amountBytes = new Uint8Array(8);
                    let tempAmount = amountValue;
                    
                    for (let i = 0; i < 8; i++) {
                        amountBytes[i] = tempAmount & 0xff;
                        tempAmount = Math.floor(tempAmount / 256);
                    }
                    
                    data.set(amountBytes, 1);
                    
                    const instruction = new window.solanaWeb3.TransactionInstruction({
                        keys,
                        programId: tokenProgramId,
                        data,
                    });
                    
                    console.log('[createTransferInstruction] 转账指令创建完成，programId:', instruction.programId.toString());
                    return instruction;
                }
            };
            
            console.log('[createBasicSplTokenInterface] 基本SPL Token接口创建成功');
            return true;
        } catch (error) {
            console.error('[createBasicSplTokenInterface] 创建基本接口失败:', error);
            return false;
        }
    },
    
    /**
     * 创建最小的Solana接口
     */
    createMinimalSolanaInterface() {
        console.warn('[createMinimalSolanaInterface] 创建最小Solana接口作为回退方案');
        
        try {
            // 创建最基本的对象结构
            window.solanaWeb3 = window.solanaWeb3 || {
                Connection: function() { throw new Error('Solana库未正确加载'); },
                PublicKey: function() { throw new Error('Solana库未正确加载'); },
                Transaction: function() { throw new Error('Solana库未正确加载'); }
            };
            
            window.spl_token = window.spl_token || {
                getAssociatedTokenAddress: async function() { 
                    throw new Error('SPL Token库未正确加载，请刷新页面重试'); 
                }
            };
            
            console.log('[createMinimalSolanaInterface] 最小接口创建完成');
            return false; // 返回false表示这只是回退方案
        } catch (error) {
            console.error('[createMinimalSolanaInterface] 创建最小接口失败:', error);
            return false;
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
            const displayBalance = balance !== null ? balance : this.balance;
            
            // 减少重复的余额更新日志
            if (!this._lastBalanceDisplayUpdate || 
                Math.abs(this._lastDisplayedBalance - displayBalance) > 0.01 ||
                (Date.now() - this._lastBalanceDisplayUpdate > 10000)) {
                
                debugLog('更新余额显示, 余额:', displayBalance);
                this._lastBalanceDisplayUpdate = Date.now();
                this._lastDisplayedBalance = displayBalance;
            }
            
            // 更新主钱包按钮上的地址显示（不是余额）
            const walletBtnText = document.getElementById('walletBtnText');
            if (walletBtnText && this.connected && this.address) {
                const formattedAddress = this.formatAddress(this.address);
                walletBtnText.textContent = formattedAddress;
                if (DEBUG_MODE) {
                    debugLog('更新钱包按钮文本为地址:', formattedAddress);
                }
            }
            
            // 更新下拉菜单中的余额显示
            const dropdownBalanceElement = document.getElementById('walletBalanceInDropdown');
            if (dropdownBalanceElement) {
                const formattedBalance = displayBalance !== null ? parseFloat(displayBalance).toFixed(2) : '0.00';
                dropdownBalanceElement.textContent = formattedBalance;
                if (DEBUG_MODE) {
                    debugLog('更新下拉菜单余额显示:', formattedBalance);
                }
            }
            
            // 更新分佣余额显示
            const commissionElements = document.querySelectorAll('#walletCommissionInDropdown, .commission-balance, [data-commission-balance]');
            if (commissionElements.length > 0) {
                const formattedCommission = this.commissionBalance !== null ? parseFloat(this.commissionBalance).toFixed(2) : '0.00';
                commissionElements.forEach(element => {
                    element.textContent = formattedCommission;
                });
                if (DEBUG_MODE) {
                    debugLog('更新分佣余额显示:', formattedCommission);
                }
            }
            
            // 更新Commission显示区域的完整文本
            const commissionDisplay = document.getElementById('commissionDisplay');
            if (commissionDisplay) {
                const commissionSpan = commissionDisplay.querySelector('#walletCommissionInDropdown');
                if (commissionSpan) {
                    const formattedCommission = this.commissionBalance !== null ? parseFloat(this.commissionBalance).toFixed(2) : '0.00';
                    commissionSpan.textContent = formattedCommission;
                }
            }
            
            // 更新钱包地址显示（在下拉菜单中）
            const walletAddressDisplay = document.getElementById('walletAddressDisplay');
            if (walletAddressDisplay && this.connected && this.address) {
                const formattedAddress = this.formatAddress(this.address);
                walletAddressDisplay.textContent = formattedAddress;
                walletAddressDisplay.title = this.address;
                if (DEBUG_MODE) {
                    debugLog('更新钱包地址显示:', formattedAddress, '(完整地址:', this.address, ')');
                }
            }
            
        } catch (error) {
            debugError('更新余额显示失败:', error);
        }
    },
    
    // 保留其他重要方法如connectMetaMask, connectPhantom, getWalletBalance, getUserAssets等
    // 这些方法将在后续实现...

    /**
     * 更新资产列表UI
     * 完全使用DOM API创建元素，彻底解决箭头问题
     */
    updateAssetsUI() {
        console.log('[updateAssetsUI] 更新资产列表UI');
        
        const assetsContainer = document.getElementById('userAssets');
        const assetsWrapper = document.querySelector('.assets-wrapper');
        
        if (!assetsContainer) {
            console.warn('[updateAssetsUI] 未找到资产容器');
            return;
        }
        
        const assets = this.assets || [];
        console.log(`[updateAssetsUI] 处理 ${assets.length} 个资产`);
        
        if (assets.length === 0) {
            assetsContainer.innerHTML = '<div class="no-assets">暂无资产</div>';
            if (assetsWrapper) assetsWrapper.style.display = 'none';
        } else {
            // 生成资产HTML
            const assetsHTML = assets.map(asset => `
                <div class="asset-item">
                    <div class="asset-info">
                        <h4>${asset.name}</h4>
                        <p>符号: ${asset.symbol}</p>
                        <p>数量: ${asset.quantity}</p>
                    </div>
                </div>
            `).join('');
            
            assetsContainer.innerHTML = assetsHTML;
            if (assetsWrapper) assetsWrapper.style.display = 'block';
            
            console.log('[updateAssetsUI] 资产列表更新完成');
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
        if (!address) return [];
        
        try {
            // 防抖机制，避免短时间内重复调用
            const now = Date.now();
            const lastCall = this._lastGetAssetsCall || 0;
            if (now - lastCall < 2000) {
                console.log('[getUserAssets] 调用过于频繁，使用缓存数据');
                return this._lastAssetsResult || [];
            }
            this._lastGetAssetsCall = now;
            
            const walletType = this.walletType || 'phantom';
            console.log(`[getUserAssets] 获取 ${walletType} 钱包 ${address} 的资产`);
            
            const apiUrl = `/api/user/assets?address=${address}&wallet_type=${walletType}&_=${Date.now()}`;
            
            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Eth-Address': address
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log(`[getUserAssets] 获取到 ${data.length || 0} 个资产`);
            
            // 缓存结果
            this._lastAssetsResult = data;
            
            return data;
        } catch (error) {
            console.error(`[getUserAssets] 获取资产失败:`, error);
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
                    
                    // 钱包连接成功，不显示弹出框，用户可以从UI状态看到连接状态
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
                    
                    // 钱包连接成功，不显示弹出框，用户可以从UI状态看到连接状态
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
                    
                    // 钱包连接成功，不显示弹出框，用户可以从UI状态看到连接状态
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
                    
                    // 钱包连接成功，不显示弹出框，用户可以从UI状态看到连接状态
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
    return this.connectWallet({
        walletType: 'phantom',
        isReconnect: isReconnect,
        
        // 1. 检查钱包是否可用
        checkWalletAvailability: async (returningFromWallet) => {
            // 如果是从钱包App返回但不支持直接连接
            if (returningFromWallet && !isReconnect && this.isMobile() && (!window.solana || !window.solana.isPhantom)) {
                console.warn('从Phantom钱包返回，但浏览器不支持钱包连接');
                showError('Connection not completed. Please use Phantom App\'s built-in browser to access this site');
                return false;
            }
            
            // 检查钱包是否存在
            if (!window.solana || !window.solana.isPhantom) {
                console.log('未检测到Phantom钱包扩展');
                
                if (!isReconnect) {
                    // 更友好的错误提示
                    const errorMsg = this.isMobile() 
                        ? '请在Phantom App中打开本页面，或在桌面浏览器中安装Phantom扩展' 
                        : '未检测到Phantom钱包扩展。请先安装Phantom钱包浏览器扩展';
                    
                    showError(errorMsg);
                    
                    // 显示安装指引
                    setTimeout(() => {
                        if (confirm('Would you like to download and install Phantom wallet now?')) {
                            if (this.isMobile()) {
                                // 移动设备跳转到应用商店
                                const userAgent = navigator.userAgent.toLowerCase();
                                if (userAgent.includes('iphone') || userAgent.includes('ipad')) {
                                    window.open('https://apps.apple.com/app/phantom-solana-wallet/id1598432977', '_blank');
                                } else if (userAgent.includes('android')) {
                                    window.open('https://play.google.com/store/apps/details?id=app.phantom', '_blank');
                                } else {
                                    window.open('https://phantom.app/download', '_blank');
                                }
                            } else {
                                window.open('https://phantom.app/', '_blank');
                            }
                        }
                    }, 2000);
                        }
                        return false;
                    }
                    
            // 检查钱包详细状态
            console.log('检测到Phantom钱包，检查状态...');
            const phantomStatus = {
                isPhantom: window.solana.isPhantom,
                isConnected: window.solana.isConnected,
                publicKey: window.solana.publicKey ? window.solana.publicKey.toString() : null
            };
            console.log('Phantom钱包状态:', phantomStatus);
            
            // 如果已经连接，可以直接使用现有连接
            if (window.solana.isConnected && window.solana.publicKey) {
                console.log('Phantom钱包已连接，将使用现有连接');
                    // 钱包已连接，不显示弹出框
                return true;
            }
            
            // 给用户提示即将打开钱包
            if (!isReconnect) {
                console.log('Phantom钱包准备就绪，等待用户授权');
            }
            
            return true;
        },
        
        // 2. 连接到钱包
        connectToWallet: async () => {
            try {
                console.log('正在请求Phantom钱包连接...');
                
                // 如果已经连接，直接返回当前连接
                if (window.solana.isConnected && window.solana.publicKey) {
                    console.log('Phantom钱包已连接，直接使用当前连接');
                    return {
                        success: true,
                        address: window.solana.publicKey.toString(),
                        provider: window.solana
                    };
                }
                
                // 钱包连接中，不显示弹出框
                
                // 简单的连接请求，不设置超时
                const response = await window.solana.connect();
                
                console.log('Phantom连接响应收到:', response);
                
                // 验证响应
                if (!response || !response.publicKey) {
                    console.error('无法获取Phantom钱包公钥');
                    if (!isReconnect) {
                        showError('连接失败：无法获取钱包地址，请重试');
                    }
                    return { success: false, error: '无法获取钱包地址' };
                }
                
                const addressString = response.publicKey.toString();
                console.log('Phantom钱包连接成功！地址:', addressString);
                
                // 钱包连接成功，不显示弹出框，用户可以从UI状态看到连接状态
                
                return {
                    success: true,
                    address: addressString,
                    provider: window.solana
                };
                
            } catch (connectError) {
                console.error('连接Phantom钱包时出错:', connectError);
                
                // 简化错误处理
                let userMessage = '';
                
                // 用户拒绝连接
                if (connectError.code === 4001 || connectError.message?.includes('User rejected')) {
                    console.log('用户拒绝了钱包连接请求');
                    userMessage = '您拒绝了连接请求，请重新点击连接并在Phantom钱包中确认授权';
                } else {
                    userMessage = `连接失败：${connectError.message || '请确保Phantom钱包已解锁并重试'}`;
                }
                
                if (!isReconnect) {
                    showError(userMessage);
                }
                
                        return {
                    success: false, 
                    error: 'connection_failed',
                    message: userMessage
                };
            }
        },
        
        // 3. 设置事件监听器
        setupListeners: () => this.setupPhantomListeners()
    });
},

/**
 * 检查是否从钱包App返回
 * @param {string} walletType - 钱包类型
 * @returns {boolean} 是否从钱包App返回
 */
checkIfReturningFromWalletApp(walletType) {
    try {
        // 优先检查sessionStorage中的标记（新的跳转方式）
        const pendingConnectionType = sessionStorage.getItem('pendingWalletConnection');
        const connectionStartTime = sessionStorage.getItem('walletConnectionStartTime');
        
        console.log(`[checkIfReturningFromWalletApp] 检查${walletType}钱包返回状态`);
        console.log(`[checkIfReturningFromWalletApp] sessionStorage pendingConnection: ${pendingConnectionType}`);
        
        if (pendingConnectionType === walletType && connectionStartTime) {
            const startTime = parseInt(connectionStartTime, 10);
            const now = Date.now();
            const timeDiff = now - startTime;
            
            console.log(`[checkIfReturningFromWalletApp] 时间差: ${timeDiff}ms`);
            
            // 检查时间是否在合理范围内（10分钟内）
            if (timeDiff < 10 * 60 * 1000 && timeDiff > 0) {
                console.log(`[checkIfReturningFromWalletApp] 检测到从${walletType}钱包App返回（新方式）`);
                
                // 清除标记，避免重复处理
                sessionStorage.removeItem('pendingWalletConnection');
                sessionStorage.removeItem('walletConnectionStartTime');
                
                return true;
            }
        }
        
        // 回退到检查localStorage中的标记（旧的方式）
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
            console.log(`[checkIfReturningFromWalletApp] 检测到从${walletType}钱包App返回（旧方式）`);
            
            // 检查时间戳是否在合理范围内（5分钟内）
            const timestamp = parseInt(pendingWalletTimestamp, 10);
            const now = Date.now();
            const timeDiff = now - timestamp;
            
            if (timeDiff > 5 * 60 * 1000) {
                console.log('[checkIfReturningFromWalletApp] 返回时间超过5分钟，可能不是从钱包App直接返回');
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
        return this.connectWallet({
            walletType: 'ethereum',
            isReconnect: isReconnect,
            
            // 1. 检查钱包是否可用
            checkWalletAvailability: async () => {
                // 检查以太坊对象是否存在
                if (!window.ethereum) {
                    console.error('MetaMask或其他以太坊钱包未安装');
                    if (!isReconnect) {
                        showError('请安装MetaMask或其他以太坊钱包');
                    }
                    return false;
                }
                
                return true;
            },
            
            // 2. 连接到钱包
            connectToWallet: async () => {
                try {
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
                        return { success: false };
                    }
                    
                    // 成功获取账户
                    return {
                        success: true,
                        address: accounts[0],
                        provider: provider
                    };
                } catch (error) {
                    console.error('连接以太坊钱包时出错:', error);
                    if (!isReconnect) {
                        showError('连接以太坊钱包失败: ' + (error.message || '未知错误'));
                    }
                    return { success: false };
                }
            },
            
            // 3. 设置事件监听器
            setupListeners: () => this.setupEthereumListeners()
        });
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
     * 使用Solana钱包发送SPL代币(USDC) - 重写版本
     * @param {string} tokenSymbol 代币符号(USDC)
     * @param {string} to 接收地址
     * @param {number} amount 转账金额
     * @returns {Promise<{success: boolean, txHash: string, error: string}>} 交易结果
     */
    async transferSolanaToken(tokenSymbol, to, amount) {
        try {
            console.log(`[transferSolanaToken] 开始真实Solana ${tokenSymbol}转账，接收地址: ${to}, 金额: ${amount}`);
            
            // 1. 确保Solana库已加载
            await this.ensureSolanaLibrariesOptimized();
            
            // 2. 检查钱包连接
            if (!window.solana || !window.solana.isConnected) {
                throw new Error('Solana wallet not connected, please connect wallet first');
            }

            if (tokenSymbol !== 'USDC') {
                throw new Error(`不支持的代币: ${tokenSymbol}`);
            }

            // 3. 使用标准的Solana主网USDC地址
            const USDC_MINT = new window.solanaWeb3.PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v");
            const TOKEN_PROGRAM_ID = new window.solanaWeb3.PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
            const ASSOCIATED_TOKEN_PROGRAM_ID = new window.solanaWeb3.PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL");
            
            const fromPubkey = new window.solanaWeb3.PublicKey(this.address);
            const toPubkey = new window.solanaWeb3.PublicKey(to);
            
            console.log('[transferSolanaToken] 公钥对象创建完成');

            // 4. 计算ATA地址
            const fromTokenAccount = await window.spl_token.getAssociatedTokenAddress(
                USDC_MINT,     // mint
                fromPubkey,    // owner
                false          // allowOwnerOffCurve
            );
            const toTokenAccount = await window.spl_token.getAssociatedTokenAddress(
                USDC_MINT,     // mint
                toPubkey,      // owner
                false          // allowOwnerOffCurve
            );

            console.log('[transferSolanaToken] ATA地址计算完成:', {
                from: fromTokenAccount.toString(),
                to: toTokenAccount.toString()
            });

            // 5. 使用代理API获取最新区块哈希
            console.log('[transferSolanaToken] 使用代理API获取区块哈希...');
            const blockhashResponse = await fetch("/api/solana/get_latest_blockhash");
            if (!blockhashResponse.ok) {
                throw new Error("获取区块哈希失败: " + blockhashResponse.statusText);
            }
            const blockhashData = await blockhashResponse.json();
            if (!blockhashData.success) {
                throw new Error("获取区块哈希失败: " + blockhashData.error);
            }
            const latestBlockhash = {
                blockhash: blockhashData.blockhash,
                lastValidBlockHeight: blockhashData.lastValidBlockHeight
            };
            console.log('[transferSolanaToken] 获取最新区块哈希:', latestBlockhash.blockhash);

            // 7. 创建交易
            const transaction = new window.solanaWeb3.Transaction();
            transaction.recentBlockhash = latestBlockhash.blockhash;
            transaction.lastValidBlockHeight = latestBlockhash.lastValidBlockHeight;
            transaction.feePayer = fromPubkey;

            // 8. 将转账金额转换为最小单位（USDC有6位小数）
            const decimals = 6; // USDC有6位小数
            const transferAmount = BigInt(Math.round(amount * Math.pow(10, decimals)));

            console.log('[transferSolanaToken] 转账金额转换:', {
                原始金额: amount,
                最小单位: transferAmount
            });

            // 9. 检查目标ATA是否存在，如果不存在则创建
            console.log('[transferSolanaToken] 检查目标ATA是否存在...');
            
            // 使用代理API检查目标ATA是否存在
            const checkAtaResponse = await fetch(`/api/solana/check_ata_exists?address=${toTokenAccount.toString()}`);
            if (!checkAtaResponse.ok) {
                throw new Error("检查ATA状态失败: " + checkAtaResponse.statusText);
            }
            const ataData = await checkAtaResponse.json();
            
            if (!ataData.success) {
                throw new Error("检查ATA状态失败: " + ataData.error);
            }
            
            // 如果目标ATA不存在，添加创建指令
            if (!ataData.exists) {
                console.log('[transferSolanaToken] 目标ATA不存在，添加创建指令...');
                
                // 手动创建ATA指令，避免函数调用问题
                const keys = [
                    { pubkey: fromPubkey, isSigner: true, isWritable: true },
                    { pubkey: toTokenAccount, isSigner: false, isWritable: true },
                    { pubkey: toPubkey, isSigner: false, isWritable: false },
                    { pubkey: USDC_MINT, isSigner: false, isWritable: false },
                    { pubkey: window.solanaWeb3.SystemProgram.programId, isSigner: false, isWritable: false },
                    { pubkey: new window.solanaWeb3.PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'), isSigner: false, isWritable: false },
                    { pubkey: window.solanaWeb3.SYSVAR_RENT_PUBKEY, isSigner: false, isWritable: false },
                ];
                
                const createAtaInstruction = new window.solanaWeb3.TransactionInstruction({
                    keys,
                    programId: new window.solanaWeb3.PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'),
                    data: new Uint8Array(0),
                });
                
                transaction.add(createAtaInstruction);
                console.log('[transferSolanaToken] ATA创建指令已添加');
            } else {
                console.log('[transferSolanaToken] 目标ATA已存在，无需创建');
            }
            
            // 10. 创建转账指令
            console.log('[transferSolanaToken] 创建转账指令...');
            
            // 手动创建转账指令，避免函数调用问题
            const keys = [
                { pubkey: fromTokenAccount, isSigner: false, isWritable: true },
                { pubkey: toTokenAccount, isSigner: false, isWritable: true },
                { pubkey: fromPubkey, isSigner: true, isWritable: false },
            ];
            
            // 构建指令数据
            const data = new Uint8Array(9);
            data[0] = 3; // Transfer instruction discriminator
            
            // 将金额编码为Little Endian 64位整数
            const amountValue = Number(transferAmount);
            const amountBytes = new Uint8Array(8);
            let tempAmount = amountValue;
            
            for (let i = 0; i < 8; i++) {
                amountBytes[i] = tempAmount & 0xff;
                tempAmount = Math.floor(tempAmount / 256);
            }
            
            data.set(amountBytes, 1);
            
            const transferInstruction = new window.solanaWeb3.TransactionInstruction({
                keys,
                programId: new window.solanaWeb3.PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'),
                data,
            });
            
            transaction.add(transferInstruction);

            console.log('[transferSolanaToken] 交易指令已添加');

            // 11. 使用钱包签名交易
            console.log('[transferSolanaToken] 请求钱包签名...');
            const signedTransaction = await window.solana.signTransaction(transaction);
            
            // 12. 序列化交易
            console.log('[transferSolanaToken] 序列化交易...');
            const serializedTx = signedTransaction.serialize();
            const base64Tx = btoa(String.fromCharCode(...serializedTx));
            
            console.log('[transferSolanaToken] 交易序列化完成，长度:', base64Tx.length);

            // 13. 使用代理API发送交易
            console.log('[transferSolanaToken] 使用代理API发送交易...');
            const requestBody = {
                serialized_transaction: base64Tx,
                skip_preflight: false,
                from_address: fromPubkey.toString(),
                to_address: to,
                amount: parseFloat(amount),
                token: tokenSymbol
            };
            
            console.log('[transferSolanaToken] 请求体:', requestBody);
            
            const sendResponse = await fetch("/api/solana/submit_transaction", {
                method: "POST",
                        headers: {
                    "Content-Type": "application/json"
                        },
                body: JSON.stringify(requestBody)
            });
            
            console.log('[transferSolanaToken] API响应状态:', sendResponse.status);

                    if (!sendResponse.ok) {
                const errorText = await sendResponse.text();
                console.error('[transferSolanaToken] API错误响应:', errorText);
                throw new Error("发送交易失败: " + sendResponse.statusText + " - " + errorText);
                    }

                    const sendData = await sendResponse.json();
            console.log('[transferSolanaToken] API响应数据:', sendData);
            
            if (!sendData.success) {
                throw new Error("发送交易失败: " + sendData.error);
                    }

            const txSignature = sendData.signature;
            
            console.log('[transferSolanaToken] 交易已发送，签名:', txSignature);
            
            // 13. 使用代理API确认交易
            console.log('[transferSolanaToken] 等待交易确认...');
            
            let confirmed = false;
            let attempts = 0;
            const maxAttempts = 30; // 最多等待30次，每次2秒
            
            while (!confirmed && attempts < maxAttempts) {
                attempts++;
                await new Promise(resolve => setTimeout(resolve, 2000)); // 等待2秒
                
                try {
                    const checkResponse = await fetch(`/api/solana/check_transaction?signature=${txSignature}&from_address=${fromPubkey.toString()}&to_address=${to}&amount=${parseFloat(amount)}&token=${tokenSymbol}`);
                    if (checkResponse.ok) {
                        const checkData = await checkResponse.json();
                        if (checkData.success && checkData.confirmed) {
                            confirmed = true;
                            console.log('[transferSolanaToken] 交易确认成功');
                            break;
                        }
                    }
                } catch (error) {
                    console.warn(`[transferSolanaToken] 检查交易状态失败 (尝试 ${attempts}/${maxAttempts}):`, error);
                }
            }
            
            if (!confirmed) {
                throw new Error('交易确认超时，请稍后检查交易状态');
            }

            console.log('[transferSolanaToken] 交易已确认，签名:', txSignature);

            // 14. 返回成功结果
            return {
                success: true,
                txHash: txSignature,
                message: `成功转账 ${amount} ${tokenSymbol}`
            };
            
        } catch (error) {
            console.error('[transferSolanaToken] 转账失败:', error);
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
    
    /**
     * 通用的钱包连接处理流程
     * 提取共用的钱包连接逻辑，减少代码重复
     * 
     * @param {Object} options - 配置选项
     * @param {string} options.walletType - 钱包类型 (如 'phantom', 'ethereum')
     * @param {boolean} options.isReconnect - 是否为重连操作
     * @param {Function} options.checkWalletAvailability - 检查钱包是否可用的函数
     * @param {Function} options.connectToWallet - 连接到钱包的函数
     * @param {Function} options.setupListeners - 设置事件监听器的函数
     * @returns {Promise<boolean>} 连接是否成功
     */
    async connectWallet(options) {
        const {
            walletType,
            isReconnect = false,
            checkWalletAvailability,
            connectToWallet,
            setupListeners
        } = options;
        
        console.log(`[connectWallet] 开始通用连接流程: 连接${walletType}钱包` + (isReconnect ? ' (重连)' : ''));
        
        try {
            // 检查是否从钱包App返回
            console.log(`[connectWallet] 检查是否从钱包App返回...`);
            const returningFromWallet = this.checkIfReturningFromWalletApp(walletType);
            console.log(`[connectWallet] 从钱包App返回检查结果: ${returningFromWallet}`);
            
            // 检查钱包是否可用
            console.log(`[connectWallet] 检查${walletType}钱包可用性...`);
            const walletAvailable = await checkWalletAvailability(returningFromWallet);
            console.log(`[connectWallet] ${walletType}钱包可用性检查结果: ${walletAvailable}`);
            
            if (!walletAvailable) {
                console.log(`[connectWallet] ${walletType}钱包不可用，终止连接`);
                return false;
            }
            
            // 连接到钱包
            console.log(`[connectWallet] 开始连接到${walletType}钱包...`);
            const connectionResult = await connectToWallet();
            console.log(`[connectWallet] ${walletType}钱包连接结果:`, connectionResult);
            
            if (!connectionResult || !connectionResult.success) {
                console.log(`[connectWallet] ${walletType}钱包连接失败:`, connectionResult);
                return false;
            }
            
            console.log(`[connectWallet] ${walletType}钱包连接成功，准备设置监听器...`);
            
            // 设置事件监听器
            if (setupListeners) {
                console.log(`[connectWallet] 设置${walletType}钱包事件监听器...`);
                setupListeners();
                console.log(`[connectWallet] ${walletType}钱包事件监听器设置完成`);
            }
            
            // 使用统一的成功处理流程
            console.log(`[connectWallet] 调用afterSuccessfulConnection处理连接成功...`);
            const afterConnectionResult = await this.afterSuccessfulConnection(
                connectionResult.address,
                walletType,
                connectionResult.provider
            );
            console.log(`[connectWallet] afterSuccessfulConnection处理结果: ${afterConnectionResult}`);
            
            return afterConnectionResult;
                
            } catch (error) {
            console.error(`[connectWallet] 连接${walletType}钱包时出错:`, error);
            console.error('[connectWallet] 错误详情:', {
                name: error.name,
                message: error.message,
                code: error.code,
                stack: error.stack
            });
            
            if (!isReconnect) {
                showError(`连接${walletType}钱包失败: ${error.message || '未知错误'}`);
            }
            return false;
        }
    },
    
    /**
     * 后备方案获取余额
     * @param {string} address 钱包地址
     * @param {string} tokenSymbol 代币符号
     */
    async getBalanceWithFallback(address, tokenSymbol) {
        try {
            debugLog('[getBalanceWithFallback] 尝试后备方案获取余额');
            
            // 修复：使用正确的API路径
            const fallbackResponse = await fetch(`/api/service/wallet/token_balance?address=${address}&token=${tokenSymbol}&_=${Date.now()}`);
            
            if (fallbackResponse.ok) {
                const fallbackData = await fallbackResponse.json();
                if (fallbackData.success && fallbackData.balance !== undefined) {
                    const balance = parseFloat(fallbackData.balance) || 0;
                    debugLog(`[getBalanceWithFallback] 后备方案成功获取余额: ${balance} ${tokenSymbol}`);
                    
                    this.balance = balance;
                    this.updateBalanceDisplay(balance);
                    this.triggerBalanceUpdatedEvent();
                    
                    return balance;
                }
            }
            
            // 如果后备方案也失败，返回0
            debugWarn('[getBalanceWithFallback] 后备方案也失败，返回余额0');
            this.balance = 0;
            this.updateBalanceDisplay(0);
            return 0;
            
        } catch (error) {
            debugError('[getBalanceWithFallback] 后备方案出错:', error);
            this.balance = 0;
            this.updateBalanceDisplay(0);
            return 0;
        }
    },
    
    /**
     * 获取钱包分佣余额
     * @returns {Promise<number>} 分佣余额
     */
    async getCommissionBalance() {
        try {
            if (!this.connected || !this.address) {
                debugWarn('[getCommissionBalance] 钱包未连接，无法获取分佣余额');
                return 0;
            }

            const address = this.address;
            debugLog(`[getCommissionBalance] 开始获取 ${address} 的分佣余额`);

            // 调用分佣余额API
            const apiUrl = `/api/service/wallet/commission_balance?address=${address}&_=${Date.now()}`;
            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': address,
                    'X-Wallet-Type': this.walletType
                }
            });

            if (!response.ok) {
                throw new Error(`API响应错误: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            if (DEBUG_MODE) {
                debugLog('[getCommissionBalance] API响应数据:', data);
            }

            if (data.success) {
                const commission = parseFloat(data.balance || 0);
                
                // 减少重复的分佣日志
                if (!this._lastCommissionLog || Math.abs(this.commissionBalance - commission) > 0.01 || 
                    (Date.now() - this._lastCommissionLog > 30000)) {
                    debugLog(`[getCommissionBalance] 获取到分佣余额: ${commission} USDC`);
                    this._lastCommissionLog = Date.now();
                }
                
                // 更新分佣余额
                this.commissionBalance = commission;
                this.updateBalanceDisplay();
                
                return commission;
            } else {
                const errorMsg = data.error || '获取分佣余额失败';
                debugError('[getCommissionBalance] 获取分佣余额失败:', errorMsg);
                return 0;
            }
        } catch (error) {
            debugError('[getCommissionBalance] 获取分佣余额出错:', error);
            return 0;
        }
    },

    /**
     * 获取USDC余额（服务器代理方式）
     * 支持长时间缓存，减少服务器负载
     */
    async getUSDCBalance() {
        try {
            if (!this.connected || !this.address) {
                debugWarn('[getUSDCBalance] 钱包未连接，无法获取USDC余额');
                return 0;
            }

            const address = this.address;
            const network = this.walletType === 'phantom' ? 'solana' : 'ethereum';
            
            // 检查缓存，避免频繁请求
            const cacheKey = `usdc_balance_${network}_${address}`;
            const cached = this._getBalanceCache(cacheKey);
            if (cached && (Date.now() - cached.timestamp < 7200000)) { // 2小时缓存
                debugLog(`[getUSDCBalance] 使用缓存的USDC余额: ${cached.balance}`);
                this.balance = cached.balance;
                this.updateBalanceDisplay();
                return cached.balance;
            }

            debugLog(`[getUSDCBalance] 开始获取 ${address} 的USDC余额 (${network})`);

            // 调用USDC余额API
            const apiUrl = `/api/service/wallet/usdc_balance?address=${address}&network=${network}&_=${Date.now()}`;
            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': address,
                    'X-Wallet-Type': this.walletType
                }
            });

            if (!response.ok) {
                throw new Error(`API响应错误: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            if (DEBUG_MODE) {
                debugLog('[getUSDCBalance] API响应数据:', data);
            }

            if (data.success) {
                const balance = parseFloat(data.balance || 0);
                
                // 缓存余额
                this._setBalanceCache(cacheKey, balance);
                
                // 减少重复的余额日志
                if (!this._lastUSDCLog || Math.abs(this.balance - balance) > 0.01 || 
                    (Date.now() - this._lastUSDCLog > 30000)) {
                    debugLog(`[getUSDCBalance] 获取到USDC余额: ${balance} USDC (${network})`);
                    this._lastUSDCLog = Date.now();
                }
                
                // 更新余额
                this.balance = balance;
                this.updateBalanceDisplay();
                
                return balance;
            } else {
                const errorMsg = data.error || '获取USDC余额失败';
                debugError('[getUSDCBalance] 获取USDC余额失败:', errorMsg);
                // 返回缓存的余额或0
                return cached ? cached.balance : 0;
            }
        } catch (error) {
            debugError('[getUSDCBalance] 获取USDC余额出错:', error);
            // 尝试返回缓存的余额
            const cacheKey = `usdc_balance_${this.walletType === 'phantom' ? 'solana' : 'ethereum'}_${this.address}`;
            const cached = this._getBalanceCache(cacheKey);
            return cached ? cached.balance : 0;
        }
    },

    /**
     * 获取余额缓存
     */
    _getBalanceCache(key) {
        try {
            const cached = localStorage.getItem(key);
            return cached ? JSON.parse(cached) : null;
        } catch (error) {
            debugError('获取余额缓存失败:', error);
            return null;
        }
    },

    /**
     * 设置余额缓存
     */
    _setBalanceCache(key, balance) {
        try {
            const cacheData = {
                balance: balance,
                timestamp: Date.now()
            };
            localStorage.setItem(key, JSON.stringify(cacheData));
        } catch (error) {
            debugError('设置余额缓存失败:', error);
        }
    },

    /**
     * 刷新所有余额信息
     * 支持手动刷新和定时刷新
     */
    async refreshAllBalances(force = false) {
        try {
            if (!this.connected || !this.address) {
                return;
            }

            debugLog('[refreshAllBalances] 开始刷新所有余额信息');

            // 并行获取余额信息
            const promises = [
                this.getUSDCBalance(),
                this.getCommissionBalance()
            ];

            const [usdcBalance, commissionBalance] = await Promise.all(promises);

            debugLog(`[refreshAllBalances] 余额刷新完成 - USDC: ${usdcBalance}, Commission: ${commissionBalance}`);

            // 触发余额更新事件
            this.triggerBalanceUpdatedEvent();

            return {
                usdc: usdcBalance,
                commission: commissionBalance
            };
        } catch (error) {
            debugError('[refreshAllBalances] 刷新余额失败:', error);
            return null;
        }
    },

    /**
     * 连接成功后的统一处理流程
     * @param {string} address - 钱包地址
     * @param {string} walletType - 钱包类型
     * @param {Object} provider - 钱包提供商实例
     * @returns {Promise<boolean>} 处理是否成功
     */
    async afterSuccessfulConnection(address, walletType, provider) {
        try {
            console.log(`[afterSuccessfulConnection] 处理${walletType}钱包连接成功，地址: ${address}`);
            
            // 更新钱包状态
            this.address = address;
            this.walletType = walletType;
            this.connected = true;
            this.provider = provider;
            
            // 保存状态到本地存储
            localStorage.setItem('walletType', walletType);
            localStorage.setItem('walletAddress', address);
            localStorage.setItem('lastWalletType', walletType);
            localStorage.setItem('lastWalletAddress', address);
            
            console.log(`[afterSuccessfulConnection] 钱包状态已保存到localStorage`);
            
            // 自动注册/更新用户信息到数据库
            try {
                await this.registerWalletUser(address, walletType);
            } catch (registerError) {
                console.warn('[afterSuccessfulConnection] 用户注册失败:', registerError);
                // 用户注册失败不应该影响钱包连接状态
            }
            
            // 获取余额和分佣余额
            try {
                await this.refreshAllBalances();
            } catch (balanceError) {
                console.warn('[afterSuccessfulConnection] 获取余额失败:', balanceError);
                // 余额获取失败不应该影响连接状态
            }
            
            // 获取用户资产
            try {
                await this.getUserAssets(address);
            } catch (assetsError) {
                console.warn('[afterSuccessfulConnection] 获取资产失败:', assetsError);
                // 资产获取失败不应该影响连接状态
            }
            
            // 检查是否为管理员
            try {
                await this.checkIsAdmin();
            } catch (adminError) {
                console.warn('[afterSuccessfulConnection] 管理员检查失败:', adminError);
                // 管理员检查失败不应该影响连接状态
            }
            
            // 更新UI
            this.updateUI();
            
            // 触发状态变更事件
            this.triggerWalletStateChanged({
                type: 'connect',
                address: this.address,
                walletType: this.walletType,
                balance: this.balance,
                commissionBalance: this.commissionBalance
            });
            
            // 钱包连接成功，不显示弹出框，用户可以从UI状态看到连接状态
            
            console.log(`[afterSuccessfulConnection] ${walletType}钱包连接处理完成`);
            return true;
            
        } catch (error) {
            console.error('[afterSuccessfulConnection] 连接后处理失败:', error);
            // 连接后处理失败，但连接本身可能是成功的，所以只记录错误
            return false;
        }
    },

    /**
     * 显示Phantom钱包重试选项
     * 当连接失败时为用户提供友好的重试界面
     */
    showPhantomRetryOption() {
        try {
            // 检查是否存在重试提示元素，避免重复创建
            let retryModal = document.getElementById('phantomRetryModal');
            if (retryModal) {
                retryModal.remove();
            }
            
            // 创建重试模态框
            retryModal = document.createElement('div');
            retryModal.id = 'phantomRetryModal';
            retryModal.className = 'modal fade';
            retryModal.setAttribute('tabindex', '-1');
            retryModal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                                Phantom钱包连接失败
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-info">
                                <h6 class="alert-heading">
                                    <i class="fas fa-info-circle me-2"></i>
                                    请检查以下几点：
                                </h6>
                                <ul class="mb-0">
                                    <li>确保Phantom钱包扩展已安装并已解锁</li>
                                    <li>检查浏览器是否拦截了弹出窗口</li>
                                    <li>如果看到连接请求，请在Phantom钱包中点击"连接"</li>
                                    <li>尝试刷新页面后重新连接</li>
                                </ul>
                            </div>
                            <div class="text-center">
                                <p class="mb-3">您可以：</p>
                                <div class="d-grid gap-2">
                                    <button id="retryPhantomBtn" class="btn btn-primary">
                                        <i class="fas fa-redo me-2"></i>重试连接
                                    </button>
                                    <button id="refreshPageBtn" class="btn btn-outline-secondary">
                                        <i class="fas fa-refresh me-2"></i>刷新页面
                                    </button>
                                    <a href="https://phantom.app/" target="_blank" class="btn btn-outline-info">
                                        <i class="fas fa-download me-2"></i>下载Phantom钱包
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // 添加到页面
            document.body.appendChild(retryModal);
            
            // 获取按钮元素
            const retryBtn = retryModal.querySelector('#retryPhantomBtn');
            const refreshBtn = retryModal.querySelector('#refreshPageBtn');
            
            // 添加重试按钮事件
            if (retryBtn) {
                retryBtn.addEventListener('click', async () => {
                    // 显示重试状态
                    retryBtn.disabled = true;
                    retryBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>正在重试...';
                    
                    // 关闭模态框
                    const modal = bootstrap.Modal.getInstance(retryModal);
                    if (modal) {
                        modal.hide();
                    }
                    
                    // 等待一下让模态框完全关闭
                    setTimeout(async () => {
                        try {
                            const success = await this.connectPhantom();
                            if (!success) {
                                // 如果重试还是失败，再次显示选项
                                setTimeout(() => this.showPhantomRetryOption(), 1000);
                            }
                    } catch (error) {
                            console.error('重试连接失败:', error);
                            showError('重试连接失败，请检查Phantom钱包状态');
                        }
                    }, 500);
                });
            }
            
            // 添加刷新按钮事件
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => {
                    window.location.reload();
                });
            }
            
            // 显示模态框
            const modal = new bootstrap.Modal(retryModal);
            modal.show();
            
            // 自动清理：模态框关闭后移除元素
            retryModal.addEventListener('hidden.bs.modal', () => {
                setTimeout(() => {
                    if (retryModal.parentNode) {
                        retryModal.parentNode.removeChild(retryModal);
                    }
                }, 100);
            });
            
        } catch (error) {
            console.error('显示重试选项失败:', error);
        }
    },

    /**
     * 自动注册/更新用户信息到数据库
     * @param {string} address - 钱包地址
     * @param {string} walletType - 钱包类型
     * @returns {Promise<Object>} 用户信息
     */
    async registerWalletUser(address, walletType) {
        try {
            console.log(`[registerWalletUser] 注册用户: ${address}, 钱包类型: ${walletType}`);
            
            const response = await fetch('/api/service/user/register_wallet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': address,
                    'X-Wallet-Type': walletType
                },
                body: JSON.stringify({
                    address: address,
                    wallet_type: walletType
                })
            });
            
            if (!response.ok) {
                throw new Error(`注册用户API响应错误: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.success) {
                console.log(`[registerWalletUser] 用户注册成功:`, data.user);
                return data.user;
            } else {
                throw new Error(data.error || '用户注册失败');
            }
            
        } catch (error) {
            console.error('[registerWalletUser] 注册用户失败:', error);
            throw error;
        }
    },
}

// 立即将walletState暴露到全局作用域，确保其他文件可以立即访问
window.walletState = walletState;
console.log('钱包状态对象已暴露到全局作用域');

// 添加钱包状态恢复功能
function recoverWalletStateFromStorage() {
    try {
        const storedAddress = localStorage.getItem('walletAddress');
        const storedType = localStorage.getItem('walletType');
        
        if (storedAddress && storedType) {
            console.log('从localStorage恢复钱包状态:', { address: storedAddress, type: storedType });
            walletState.address = storedAddress;
            walletState.walletType = storedType;
            walletState.connected = true;
            
            // 立即更新UI
            if (typeof walletState.updateUI === 'function') {
                walletState.updateUI();
            }
            
            // 触发状态变更事件
            if (typeof walletState.triggerWalletStateChanged === 'function') {
                walletState.triggerWalletStateChanged({
                    type: 'recovered',
                    address: storedAddress,
                    walletType: storedType
                });
            }
            
            return true;
            }
            return false;
    } catch (error) {
        console.error('从localStorage恢复钱包状态失败:', error);
            return false;
        }
}

// 立即尝试恢复钱包状态
recoverWalletStateFromStorage();

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

/**
 * 显示成功消息
 * @param {string} message - 成功消息
 * @param {HTMLElement} container - 可选，显示消息的容器元素
 */
function showSuccess(message, container = null) {
    try {
        // 首先记录到控制台
        console.log('%c✅ ' + message, 'color: green; font-weight: bold;');
        
        // 如果有指定容器，则在容器中显示
        if (container) {
            container.textContent = message;
            container.style.display = 'block';
            return;
        }
        
        // 使用iziToast显示
        if (window.iziToast) {
            window.iziToast.success({
                title: '成功',
                message: message,
                position: 'topRight',
                timeout: 3000
            });
        }
    } catch (e) {
        // 确保至少在控制台显示
        console.log('%c✅ ' + message, 'color: green; font-weight: bold;');
    }
}

/**
 * 显示错误消息
 * @param {string} message - 错误消息
 * @param {HTMLElement} container - 可选，显示错误的容器元素
 */
function showError(message, container = null) {
    try {
        // 首先记录到控制台
        console.error('❌ ' + message);
        
        // 如果有指定容器，则在容器中显示
        if (container) {
            container.textContent = message;
            container.style.display = 'block';
            return;
        }
        
        // 使用iziToast显示
        if (window.iziToast) {
            window.iziToast.error({
                title: '错误',
                message: message,
                position: 'topRight',
                timeout: 4000
            });
        }
    } catch (e) {
        // 确保至少在控制台显示
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

// 已移除重复函数，使用上方定义的统一showSuccess和showError函数

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
        showError("Please connect wallet first");
        if (modalErrorDiv) {
            modalErrorDiv.textContent = "Please connect wallet first";
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
    
    // 更新价格显示 - 使用更具体的选择器，避免选中购买按钮
    if (data.token_price) {
        // 明确排除按钮元素，只选择价格显示元素
        const priceElements = document.querySelectorAll('.token-price:not(button):not(.btn):not([role="button"]), [data-token-price]:not(button):not(.btn):not([role="button"])');
        priceElements.forEach(el => {
            // 双重检查：确保不是按钮类型的元素
            if (el.tagName.toLowerCase() !== 'button' && 
                !el.classList.contains('btn') && 
                !el.classList.contains('button') &&
                el.getAttribute('role') !== 'button') {
                
            el.textContent = formatCurrency(data.token_price);
            
            // 更新数据属性
            if (el.hasAttribute('data-token-price')) {
                el.setAttribute('data-token-price', data.token_price);
                }
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
        serialize: () => {
            // 使用atob解码base64，然后转换为Uint8Array
            const binaryString = atob(transactionData.message);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            return bytes;
        }
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
    /**
     * 尝试移动端钱包重定向
     * @param {string} walletType - 钱包类型
     * @returns {Promise<boolean>} 是否成功跳转
     */
    async tryMobileWalletRedirect(walletType) {
        if (!this.isMobile()) {
            return false;
        }
        
        try {
            console.log(`[tryMobileWalletRedirect] 开始尝试${walletType}钱包跳转`);
            
            let deepLinkUrl = '';
            let universalLinkUrl = '';
            let appStoreUrl = '';
            
            // 获取当前页面URL，用于回调
            const currentUrl = encodeURIComponent(window.location.href);
            const baseUrl = window.location.origin;
            
            // 根据钱包类型设置不同的链接
            if (walletType === 'phantom' || walletType === 'solana') {
                // Phantom钱包的深度链接和通用链接
                const connectParams = new URLSearchParams({
                    dapp_encryption_public_key: this.generateRandomKey(),
                    cluster: 'mainnet-beta',
                    app_url: baseUrl,
                    redirect_link: currentUrl
                }).toString();
                
                deepLinkUrl = `phantom://v1/connect?${connectParams}`;
                universalLinkUrl = `https://phantom.app/ul/v1/connect?${connectParams}`;
                
                // 应用商店链接
                if (navigator.userAgent.toLowerCase().includes('iphone') || 
                    navigator.userAgent.toLowerCase().includes('ipad')) {
                    appStoreUrl = 'https://apps.apple.com/app/phantom-solana-wallet/id1598432977';
                } else {
                    appStoreUrl = 'https://play.google.com/store/apps/details?id=app.phantom';
                }
            } else if (walletType === 'ethereum' || walletType === 'metamask') {
                // MetaMask的深度链接
                deepLinkUrl = `https://metamask.app.link/dapp/${window.location.host}${window.location.pathname}`;
                universalLinkUrl = deepLinkUrl;
                
                // 应用商店链接
                if (navigator.userAgent.toLowerCase().includes('iphone') || 
                    navigator.userAgent.toLowerCase().includes('ipad')) {
                    appStoreUrl = 'https://apps.apple.com/app/metamask/id1438144202';
                } else {
                    appStoreUrl = 'https://play.google.com/store/apps/details?id=io.metamask';
                }
            } else {
                console.warn(`[tryMobileWalletRedirect] 不支持的钱包类型: ${walletType}`);
                return false;
            }
            
            // 设置钱包返回检测标记
            sessionStorage.setItem('pendingWalletConnection', walletType);
            sessionStorage.setItem('walletConnectionStartTime', Date.now().toString());
            
            // 尝试深度链接跳转
            console.log(`[tryMobileWalletRedirect] 尝试深度链接: ${deepLinkUrl}`);
            const deepLinkSuccess = await this.attemptDeepLink(deepLinkUrl);
            
            if (deepLinkSuccess) {
                console.log(`[tryMobileWalletRedirect] 深度链接跳转成功`);
                return true;
            }
            
            // 深度链接失败，尝试通用链接
            console.log(`[tryMobileWalletRedirect] 深度链接失败，尝试通用链接: ${universalLinkUrl}`);
            const universalLinkSuccess = await this.attemptUniversalLink(universalLinkUrl);
            
            if (universalLinkSuccess) {
                console.log(`[tryMobileWalletRedirect] 通用链接跳转成功`);
                return true;
            }
            
            // 所有跳转都失败，提示用户下载应用
            console.log(`[tryMobileWalletRedirect] 所有跳转失败，提示下载应用`);
            const shouldDownload = confirm(`${walletType === 'phantom' ? 'Phantom' : 'MetaMask'} wallet app not detected. Would you like to download it?`);
            
            if (shouldDownload && appStoreUrl) {
                window.open(appStoreUrl, '_blank');
            }
            
            return false;
            
        } catch (error) {
            console.error(`[tryMobileWalletRedirect] 移动端钱包跳转失败:`, error);
            return false;
        }
    },
    
    /**
     * 尝试深度链接跳转
     * @param {string} deepLinkUrl - 深度链接URL
     * @returns {Promise<boolean>} 是否成功跳转
     */
    async attemptDeepLink(deepLinkUrl) {
        return new Promise((resolve) => {
            const timeout = setTimeout(() => {
                resolve(false);
            }, 2500); // 2.5秒超时
            
            // 创建隐藏的iframe尝试跳转
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = deepLinkUrl;
            
            document.body.appendChild(iframe);
            
            // 检测页面是否失去焦点（表示跳转成功）
            const startTime = Date.now();
            const checkVisibility = () => {
                if (document.hidden || Date.now() - startTime > 1000) {
                    clearTimeout(timeout);
                    document.body.removeChild(iframe);
                    resolve(true);
                } else {
                    setTimeout(checkVisibility, 100);
                }
            };
            
            setTimeout(() => {
                checkVisibility();
                // 清理iframe
                setTimeout(() => {
                    if (iframe && iframe.parentNode) {
                        document.body.removeChild(iframe);
                    }
                }, 1000);
            }, 500);
        });
    },
    
    /**
     * 尝试通用链接跳转
     * @param {string} universalLinkUrl - 通用链接URL
     * @returns {Promise<boolean>} 是否成功跳转
     */
    async attemptUniversalLink(universalLinkUrl) {
        return new Promise((resolve) => {
            const timeout = setTimeout(() => {
                resolve(false);
            }, 3000); // 3秒超时
            
            // 创建隐藏的链接并点击
            const link = document.createElement('a');
            link.href = universalLinkUrl;
            link.target = '_blank';
            link.style.display = 'none';
            
            document.body.appendChild(link);
            link.click();
            
            // 检测页面是否失去焦点
            const startTime = Date.now();
            const checkVisibility = () => {
                if (document.hidden || Date.now() - startTime > 1500) {
                    clearTimeout(timeout);
                    document.body.removeChild(link);
                    resolve(true);
                } else if (Date.now() - startTime < 2500) {
                    setTimeout(checkVisibility, 100);
                }
            };
            
            setTimeout(() => {
                checkVisibility();
                // 清理链接
                setTimeout(() => {
                    if (link && link.parentNode) {
                        document.body.removeChild(link);
                    }
                }, 1000);
            }, 500);
        });
    },
    
    /**
     * 生成随机密钥（用于钱包连接）
     * @returns {string} 随机密钥
     */
    generateRandomKey() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    },

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

// 钱包按钮初始化现在由 base.html 中的简单脚本处理
// 这里保留一些辅助函数供base.html调用

// 更新钱包菜单信息
window.updateWalletMenuInfo = function updateWalletMenuInfo() {
    if (!window.walletState) return;
    
    const addressDisplay = document.getElementById('walletAddressDisplay');
    const balanceDisplay = document.getElementById('walletBalanceInDropdown');
    const commissionDisplay = document.getElementById('walletCommissionInDropdown');
    const assetsSection = document.getElementById('userAssetsSection');
    const assetsList = document.getElementById('walletAssetsList');
    
    // 更新地址显示
    if (addressDisplay && window.walletState.address) {
        const shortAddress = window.walletState.formatAddress(window.walletState.address);
        addressDisplay.textContent = shortAddress;
    }
    
    // 更新余额显示
    if (balanceDisplay && window.walletState.balance !== null) {
        balanceDisplay.textContent = parseFloat(window.walletState.balance || 0).toFixed(2);
    }
    
    // 更新佣金显示
    if (commissionDisplay && window.walletState.commissionBalance !== undefined) {
        commissionDisplay.textContent = parseFloat(window.walletState.commissionBalance || 0).toFixed(2);
    }
    
    // 加载用户资产
    if (window.walletState.address) {
        loadUserAssets(window.walletState.address);
    }
}

// 加载用户资产
function loadUserAssets(address) {
    const assetsList = document.getElementById('walletAssetsList');
    const assetsSection = document.getElementById('userAssetsSection');
    
    if (!assetsList || !address) return;
    
    // 显示加载状态
    assetsList.innerHTML = '<li style="text-align:center; padding:10px; color:#666; font-size:12px;"><i class="fas fa-spinner fa-spin me-2"></i>Loading assets...</li>';
    
    // 获取用户资产
    fetch(`/api/user/${address}/assets`, {
        headers: {
            'Accept': 'application/json',
            'X-Eth-Address': address
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.assets && data.assets.length > 0) {
            // 显示资产部分
            if (assetsSection) {
                assetsSection.style.display = 'block';
            }
            
            // 构建资产列表
            let assetsHtml = '';
            data.assets.forEach(asset => {
                const quantity = parseFloat(asset.quantity || 0);
                if (quantity > 0) {
                    assetsHtml += `
                        <li class="wallet-asset-item">
                            <a href="/assets/${asset.token_symbol}" class="asset-link text-decoration-none">
                                <div class="asset-info">
                                    <span class="asset-name">${asset.name || asset.token_symbol}</span>
                                    <div>
                                        <span class="asset-quantity">${quantity.toLocaleString()}</span>
                                        <span class="asset-symbol">${asset.token_symbol}</span>
                                    </div>
                                </div>
                            </a>
                        </li>
                    `;
                }
            });
            
            if (assetsHtml) {
                assetsList.innerHTML = assetsHtml;
            } else {
                assetsList.innerHTML = '<li style="text-align:center; padding:10px; color:#666; font-size:12px;">No assets found</li>';
            }
        } else {
            // 隐藏资产部分或显示空状态
            assetsList.innerHTML = '<li style="text-align:center; padding:10px; color:#666; font-size:12px;">No assets found</li>';
            if (assetsSection) {
                assetsSection.style.display = 'none';
            }
        }
    })
    .catch(error => {
        console.error('Failed to load user assets:', error);
        assetsList.innerHTML = '<li style="text-align:center; padding:10px; color:#dc3545; font-size:12px;">Failed to load assets</li>';
    });
}

// 切换钱包并关闭菜单（供base.html调用）
window.switchWalletAndCloseMenu = function() {
    console.log('Switch wallet requested');
    
    // 关闭菜单
    const walletMenu = document.getElementById('walletMenu');
    if (walletMenu) {
        walletMenu.classList.remove('show');
        walletMenu.style.display = 'none';
    }
    
    // 打开钱包选择器
    if (window.walletState && typeof window.walletState.openWalletSelector === 'function') {
        window.walletState.openWalletSelector();
    } else {
        console.error('Wallet selector function not available');
        alert('Wallet switch temporarily unavailable, please refresh and try again');
    }
};

// 断开连接并关闭菜单（供base.html调用）
window.disconnectAndCloseMenu = function() {
    console.log('Disconnect wallet requested');
    
    // 关闭菜单
    const walletMenu = document.getElementById('walletMenu');
    if (walletMenu) {
        walletMenu.classList.remove('show');
        walletMenu.style.display = 'none';
    }
    
    // 断开钱包连接
    if (window.walletState && typeof window.walletState.disconnect === 'function') {
        window.walletState.disconnect();
    } else {
        // 手动清理
        localStorage.removeItem('walletAddress');
        localStorage.removeItem('walletType');
        window.location.reload();
    }
};

// 钱包按钮初始化现在由base.html统一处理
// 这样可以避免重复初始化和冲突

// 监听钱包状态变化，更新按钮显示
window.addEventListener('walletConnected', function() {
    const walletBtnText = document.getElementById('walletBtnText');
    if (walletBtnText && window.walletState && window.walletState.address) {
        const shortAddress = window.walletState.formatAddress(window.walletState.address);
        walletBtnText.textContent = shortAddress;
    }
});

window.addEventListener('walletDisconnected', function() {
    const walletBtnText = document.getElementById('walletBtnText');
    if (walletBtnText) {
        walletBtnText.textContent = 'Connect Wallet';
    }
});

// 导出钱包接口
console.log('钱包接口初始化完成');

