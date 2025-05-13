/**
 * 统一购买处理脚本
 * 支持多语言界面
 * 版本：1.3.0 - 修复浏览器卡死问题，优化性能和事件处理
 */

// 定义全局变量
let timeoutId = null;
let preparePurchaseController = null;
let confirmPurchaseController = null;

(function() {
    // 避免重复加载和初始化
    if (window.buyHandlerInitialized) {
        console.debug('购买处理脚本已经初始化，跳过重复执行');
        return;
    }
    window.buyHandlerInitialized = true;
    
    console.log('加载购买处理脚本 v1.3.0');
    
    // 文本资源
    const TEXTS = {
        'zh': {
            processing: '处理中...',
            walletNotConnected: '请先连接您的钱包',
            missingAmountInput: '找不到购买数量输入框',
            invalidAmount: '请输入有效的购买数量',
            serverError: '服务器错误',
            prepareFailed: '准备购买请求失败',
            purchaseError: '处理购买请求时出错',
            insufficientFunds: '余额不足，无法完成购买',
            purchaseSuccess: '购买请求已提交！请耐心等待交易确认。',
            purchaseCompleted: '购买成功！资产将在几分钟内添加到您的钱包'
        },
        'en': {
            processing: 'Processing purchase request...',
            walletNotConnected: 'Please connect your wallet first',
            missingAmountInput: 'Purchase amount input not found',
            invalidAmount: 'Please enter a valid purchase amount',
            serverError: 'Server error',
            prepareFailed: 'Failed to prepare purchase request',
            purchaseError: 'Error processing purchase request',
            insufficientFunds: 'Insufficient funds to complete purchase',
            purchaseSuccess: 'Purchase request submitted! Please wait for transaction confirmation.',
            purchaseCompleted: 'Purchase successful! Asset will be added to your wallet shortly'
        }
    };
    
    // 配置
    const CONFIG = {
        debug: false,              // 减少调试日志输出
        apiTimeoutMs: 10000,       // API请求超时时间降低到10秒
        enableApiCache: true,      // 启用API缓存
        cacheExpiry: 30000,        // 缓存过期时间：30秒
        maxRetries: 2,             // 最大重试次数降低到2次
        retryDelayMs: 1000,        // 重试延迟降低到1秒
        defaultAssetId: 'RH-205020',
        lastRequestTime: 0,        // 上次请求时间
        minRequestInterval: 2000,  // 最小请求间隔降低到2秒
        requestCount: 0,           // 请求计数器
        maxRequestsPerMinute: 15,  // 每分钟最大请求数减少到15
        safetyTimeout: 8000        // 安全超时，确保操作不会无限挂起
    };
    
    // API缓存
    const apiCache = new Map();
    
    // 状态
    let state = {
        lastPurchaseTime: 0,
        purchaseInProgress: false,
        modalVisible: false,
        purchaseData: null,
        confirmedPurchases: new Set(),
        apiEndpoints: {
            prepare: [
                '/api/trades/prepare_purchase',
                '/api/v1/trades/prepare_purchase'
            ],
            confirm: [
                '/api/trades/confirm_purchase',
                '/api/v1/trades/confirm_purchase'
            ]
        },
        initialized: false,
        eventHandlersAttached: false,  // 跟踪事件处理器是否已附加
        initializationTimestamp: Date.now()  // 记录初始化时间戳
    };
    
    // 获取当前语言
    function getCurrentLanguage() {
        return (document.documentElement.lang || 'en').toLowerCase().split('-')[0];
    }
    
    // 获取当前语言的文本
    function getText(key) {
        const lang = getCurrentLanguage();
        return (TEXTS[lang] && TEXTS[lang][key]) || TEXTS['en'][key];
    }
    
    // 日志输出
    function log(message, data) {
        if (CONFIG.debug) {
            if (data !== undefined) {
                console.log(`[购买处理] ${message}`, data);
            } else {
                console.log(`[购买处理] ${message}`);
            }
        }
    }
    
    // 安全执行函数 - 防止任何操作导致页面卡死
    function safeExecute(fn, fallbackFn, timeout = CONFIG.safetyTimeout) {
        let hasCompleted = false;
        let localTimeoutId = null;
        
        // 设置安全超时
        localTimeoutId = setTimeout(() => {
            if (!hasCompleted) {
                console.debug('[购买处理] 操作超时终止', fn.name || '匿名函数');
                hasCompleted = true;
                
                if (typeof fallbackFn === 'function') {
                    try {
                        fallbackFn();
                    } catch (e) {
                        console.debug('[购买处理] 降级操作执行失败', e);
                    }
                }
            }
        }, timeout);
        
        // 执行主函数
        try {
            const result = fn();
            
            // 处理Promise
            if (result && typeof result.then === 'function') {
                // 返回竞态Promise，确保不会无限等待
                return Promise.race([
                    result.then(value => {
                        if (!hasCompleted) {
                            clearTimeout(localTimeoutId);
                            hasCompleted = true;
                        }
                        return value;
                    }).catch(err => {
                        if (!hasCompleted) {
                            clearTimeout(localTimeoutId);
                            hasCompleted = true;
                        }
                        throw err;
                    }),
                    new Promise((_, reject) => {
                        // 此Promise会在超时时被处理，但我们在timeoutId中已经有逻辑了
                    })
                ]);
            }
            
            // 同步结果
            clearTimeout(localTimeoutId);
            hasCompleted = true;
            return result;
        } catch (error) {
            if (!hasCompleted) {
                clearTimeout(localTimeoutId);
                hasCompleted = true;
                console.debug('[购买处理] 操作执行失败', error);
                
                if (typeof fallbackFn === 'function') {
                    try {
                        return fallbackFn();
                    } catch (e) {
                        console.debug('[购买处理] 降级操作执行失败', e);
                    }
                }
            }
            throw error;
        }
    }
    
    // 标准化资产ID
    function normalizeAssetId(assetId) {
        if (!assetId) return CONFIG.defaultAssetId;
        
        // 如果是纯数字，添加RH-前缀
        if (/^\d+$/.test(assetId)) {
            return `RH-${assetId}`;
        }
        
        // 如果已经是RH-格式，保持不变
        if (assetId.startsWith('RH-')) {
            return assetId;
        }
        
        // 尝试提取数字部分
        const match = assetId.match(/(\d+)/);
        if (match && match[1]) {
            return `RH-${match[1]}`;
        }
        
        return assetId;
    }
    
    // 检查钱包连接状态 - 增强版
    function isWalletConnected() {
        try {
            // 1. 检查window.walletState
            if (window.walletState) {
                if (window.walletState.isConnected === true || 
                    window.walletState.connected === true ||
                    window.walletState.address) {
                    log('钱包状态检查：通过walletState对象确认已连接');
                    return true;
                }
            }
            
            // 2. 检查全局钱包连接API
            if (typeof window.isWalletConnected === 'function') {
                if (window.isWalletConnected() === true) {
                    log('钱包状态检查：通过全局isWalletConnected函数确认已连接');
                    return true;
                }
            }
            
            // 3. 检查localStorage中的钱包地址
            const storedAddress = localStorage.getItem('walletAddress');
            if (storedAddress) {
                log('钱包状态检查：通过localStorage确认已连接');
                return true;
            }
            
            // 4. 检查特定元素
            const walletButton = document.querySelector('#connect-wallet-button, #wallet-button, #walletBtn');
            if (walletButton && walletButton.getAttribute('data-connected') === 'true') {
                log('钱包状态检查：通过UI元素确认已连接');
                return true;
            }
            
            // 默认为未连接
            return false;
        } catch (error) {
            console.debug('[购买处理] 检查钱包连接状态时出错', error);
            return false;
        }
    }
    
    // 获取当前钱包地址
    function getWalletAddress() {
        try {
            // 1. 从window.walletState获取
            if (window.walletState && window.walletState.address) {
                return window.walletState.address;
            }
            
            // 2. 从localStorage获取
            const storedAddress = localStorage.getItem('walletAddress');
            if (storedAddress) {
                return storedAddress;
            }
            
            // 3. 从钱包按钮获取
            const walletButton = document.querySelector('#connect-wallet-button, #wallet-button, #walletBtn');
            if (walletButton && walletButton.getAttribute('data-address')) {
                return walletButton.getAttribute('data-address');
            }
            
            return null;
        } catch (error) {
            console.debug('[购买处理] 获取钱包地址时出错', error);
            return null;
        }
    }
    
    // 检查API请求限制
    function checkApiRateLimit() {
        const now = Date.now();
        
        // 重置计数器（每分钟）
        if (now - CONFIG.lastRequestTime > 60000) {
            CONFIG.requestCount = 0;
            CONFIG.lastRequestTime = now;
            return true;
        }
        
        // 检查最小请求间隔
        if (now - CONFIG.lastRequestTime < CONFIG.minRequestInterval) {
            console.debug(`[购买处理] API请求频率过高，已限制`);
            return false;
        }
        
        // 检查每分钟最大请求数
        if (CONFIG.requestCount >= CONFIG.maxRequestsPerMinute) {
            console.debug(`[购买处理] 已达到每分钟最大API请求数限制`);
            return false;
        }
        
        // 更新请求时间和计数
        CONFIG.lastRequestTime = now;
        CONFIG.requestCount++;
        return true;
    }
    
    // 从缓存获取数据
    function getFromCache(key) {
        if (!CONFIG.enableApiCache) return null;
        
        const cached = apiCache.get(key);
        if (!cached) return null;
        
        // 检查是否过期
        if (Date.now() - cached.timestamp > CONFIG.cacheExpiry) {
            apiCache.delete(key);
            return null;
        }
        
        log(`使用缓存数据: ${key}`);
        return cached.data;
    }
    
    // 添加数据到缓存
    function addToCache(key, data) {
        if (!CONFIG.enableApiCache) return;
        
        apiCache.set(key, {
            data: data,
            timestamp: Date.now()
        });
        
        log(`数据已缓存: ${key}`);
    }
    
    // 创建提示信息
    function createAlert(message, type = 'info') {
        const container = document.querySelector('.alert-container') || document.querySelector('.message-container');
        
        if (!container) {
            // 如果没有容器，使用toast
            showToast(message, type === 'error' ? 'danger' : type);
            return;
        }
        
        // 创建alert元素
        const alert = document.createElement('div');
        alert.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alert.setAttribute('role', 'alert');
        
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // 添加到容器
        container.appendChild(alert);
        
        // 自动关闭
        setTimeout(() => {
            if (alert.parentNode) {
                alert.classList.remove('show');
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.parentNode.removeChild(alert);
                    }
                }, 150);
            }
        }, 5000);
    }
    
    // 显示Toast消息
    function showToast(message, type = 'info') {
        try {
            // 检查是否有Toast容器
            let toastContainer = document.querySelector('.toast-container');
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                document.body.appendChild(toastContainer);
            }
            
            // 创建Toast元素
            const toastId = `toast-${Date.now()}`;
            const toast = document.createElement('div');
            toast.className = `toast bg-${type} text-white`;
            toast.id = toastId;
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            toast.setAttribute('data-bs-delay', '5000');
            toast.innerHTML = `
                <div class="toast-header bg-${type} text-white">
                    <strong class="me-auto">通知</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            `;
            
            // 添加到容器
            toastContainer.appendChild(toast);
            
            // 使用Bootstrap的Toast API显示（如果可用）
            if (window.bootstrap && window.bootstrap.Toast) {
                const bsToast = new window.bootstrap.Toast(toast);
                bsToast.show();
            } else {
                // 否则手动处理
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                    setTimeout(() => {
                        if (toast.parentNode) {
                            toast.parentNode.removeChild(toast);
                        }
                    }, 300);
                }, 5000);
            }
        } catch (error) {
            console.error('显示Toast消息出错:', error);
            // 降级到alert
            alert(message);
        }
    }
    
    // 创建和显示模态窗口
    function showModal(title, content, confirmCallback = null) {
        try {
            // 防止同时显示多个模态窗口
            if (state.modalVisible) {
                log('已有模态窗口显示中，忽略请求');
                return;
            }
            
            // 使用现有模态窗口或创建新的
            let modal = document.getElementById('purchase-modal');
            if (!modal) {
                modal = document.createElement('div');
                modal.className = 'modal fade';
                modal.id = 'purchase-modal';
                modal.setAttribute('tabindex', '-1');
                modal.setAttribute('aria-labelledby', 'purchase-modal-title');
                modal.setAttribute('aria-hidden', 'true');
                
                modal.innerHTML = `
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="purchase-modal-title">${title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                ${content}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                                <button type="button" class="btn btn-primary" id="modal-confirm-btn">确认</button>
                            </div>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(modal);
            } else {
                // 更新现有模态窗口
                modal.querySelector('.modal-title').textContent = title;
                modal.querySelector('.modal-body').innerHTML = content;
            }
            
            // 设置确认按钮事件
            const confirmBtn = modal.querySelector('#modal-confirm-btn');
            if (confirmBtn) {
                // 移除旧的事件监听器
                const newConfirmBtn = confirmBtn.cloneNode(true);
                confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
                
                // 添加新的事件监听器
                if (confirmCallback) {
                    newConfirmBtn.addEventListener('click', confirmCallback);
                }
            }
            
            // 显示模态窗口
            if (window.bootstrap && window.bootstrap.Modal) {
                const bsModal = new window.bootstrap.Modal(modal);
                bsModal.show();
                
                // 监听模态窗口关闭事件
                modal.addEventListener('hidden.bs.modal', function () {
                    state.modalVisible = false;
                });
                
                state.modalVisible = true;
            } else {
                // 降级显示
                modal.style.display = 'block';
                modal.classList.add('show');
                document.body.classList.add('modal-open');
                
                // 创建背景
                let backdrop = document.createElement('div');
                backdrop.className = 'modal-backdrop fade show';
                document.body.appendChild(backdrop);
                
                state.modalVisible = true;
                
                // 关闭按钮事件
                const closeBtn = modal.querySelector('.btn-close, .btn-secondary');
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => hideModal(modal, backdrop));
                }
            }
        } catch (error) {
            console.error('显示模态窗口失败:', error);
            // 降级到确认对话框
            if (confirmCallback && confirm(`${title}\n\n${content.replace(/<[^>]*>/g, '')}`)) {
                confirmCallback();
            }
        }
    }
    
    // 隐藏模态窗口
    function hideModal(modal = null, backdrop = null) {
        try {
            if (!modal) {
                modal = document.getElementById('purchase-modal');
            }
            
            if (!modal) return;
            
            if (window.bootstrap && window.bootstrap.Modal) {
                const bsModal = window.bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            } else {
                // 手动隐藏
                modal.style.display = 'none';
                modal.classList.remove('show');
                document.body.classList.remove('modal-open');
                
                // 移除背景
                if (backdrop) {
                    backdrop.parentNode.removeChild(backdrop);
                } else {
                    const backdrops = document.querySelectorAll('.modal-backdrop');
                    backdrops.forEach(el => el.parentNode.removeChild(el));
                }
            }
            
            state.modalVisible = false;
        } catch (error) {
            console.error('隐藏模态窗口失败:', error);
        }
    }
    
    // 更新按钮状态
    function updateButtonState(button, isLoading) {
        if (!button) return;
        
        // 检查是否存在全局的更新按钮函数
        if (typeof window.updateBuyButtonState === 'function') {
            const buttonText = isLoading ? getText('processing') : button.dataset.originalText || '购买';
            window.updateBuyButtonState(button, buttonText, true);
            return;
        }
        
        // 备用方法：直接更新按钮
        try {
            // 保存原始文本
            if (!button.dataset.originalText && !isLoading) {
                button.dataset.originalText = button.textContent.trim();
            }
            
            // 更新按钮内容和状态
            if (isLoading) {
                button.disabled = true;
                const spinnerExists = button.querySelector('.spinner-border') !== null;
                
                if (!spinnerExists) {
                    button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${getText('processing')}`;
                }
            } else {
                button.disabled = false;
                button.innerHTML = button.dataset.originalText || '购买';
            }
        } catch (error) {
            console.debug('[购买处理] 更新按钮状态失败:', error);
        }
    }
    
    // 准备购买请求
    async function preparePurchase(assetId, amount) {
        updateStatus('准备购买请求...', 'info');
        log('准备购买请求:', { assetId, amount });
        
        // 清除之前的超时
        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
        
        // 清除之前的controller
        if (preparePurchaseController) {
            try {
                preparePurchaseController.abort();
            } catch (e) {}
        }
        
        // 检查缓存
        const cacheKey = `prepare_${assetId}_${amount}`;
        const cachedData = getFromCache(cacheKey);
        if (cachedData) return cachedData;
        
        // 构建请求参数
        const walletAddress = getWalletAddress();
        if (!walletAddress) {
            throw new Error(getText('walletNotConnected'));
        }
        
        const params = {
            asset_id: assetId.replace('RH-', ''),  // 移除RH-前缀
            amount: amount,
            wallet_address: walletAddress
        };
        
        log('准备购买请求:', params);
        
        // 尝试多个API端点
        for (let i = 0; i < state.apiEndpoints.prepare.length; i++) {
            const endpoint = state.apiEndpoints.prepare[i];
            try {
                // 创建AbortController用于超时控制
                preparePurchaseController = new AbortController();
                const signal = preparePurchaseController.signal;
                
                // 设置超时
                timeoutId = setTimeout(() => preparePurchaseController.abort(), CONFIG.apiTimeoutMs);
                
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify(params),
                    signal: signal
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP错误 ${response.status}`);
                }
                
                const data = await response.json();
                
                // 验证响应
                if (!data || !data.success) {
                    throw new Error(data.message || getText('prepareFailed'));
                }
                
                // 缓存成功的响应
                addToCache(cacheKey, data);
                
                return data;
            } catch (error) {
                log(`API端点 ${endpoint} 失败:`, error.message);
                
                // 确保清除超时
                if (timeoutId) {
                    clearTimeout(timeoutId);
                    timeoutId = null;
                }
                
                // 如果是最后一个API，则抛出错误
                if (i === state.apiEndpoints.prepare.length - 1) {
                    throw error;
                }
                
                // 否则尝试下一个API
                continue;
            }
        }
        
        // 不应该到达这里
        throw new Error(getText('serverError'));
    }
    
    // 确认购买请求
    async function confirmPurchase(purchaseData) {
        updateStatus('确认购买中...', 'info');
        log('确认购买请求:', purchaseData);
        
        // 清除之前的超时
        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
        
        // 清除之前的controller
        if (confirmPurchaseController) {
            try {
                confirmPurchaseController.abort();
            } catch (e) {}
        }
        
        if (!purchaseData || !purchaseData.purchase_id) {
            throw new Error(getText('purchaseError'));
        }
        
        // 检查是否已确认过
        if (state.confirmedPurchases.has(purchaseData.purchase_id)) {
            log('跳过重复确认:', purchaseData.purchase_id);
            return { success: true, already_confirmed: true };
        }
        
        // 构建请求参数
        const walletAddress = getWalletAddress();
        if (!walletAddress) {
            throw new Error(getText('walletNotConnected'));
        }
        
        const params = {
            purchase_id: purchaseData.purchase_id,
            wallet_address: walletAddress,
            signature: purchaseData.signature || '',
            transaction_id: purchaseData.transaction_id || ''
        };
        
        log('确认购买请求:', params);
        
        // 尝试多个API端点
        for (let i = 0; i < state.apiEndpoints.confirm.length; i++) {
            const endpoint = state.apiEndpoints.confirm[i];
            try {
                // 创建AbortController用于超时控制
                confirmPurchaseController = new AbortController();
                const signal = confirmPurchaseController.signal;
                
                // 设置超时
                timeoutId = setTimeout(() => confirmPurchaseController.abort(), CONFIG.apiTimeoutMs);
                
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify(params),
                    signal: signal
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP错误 ${response.status}`);
                }
                
                const data = await response.json();
                
                // 验证响应
                if (!data || !data.success) {
                    throw new Error(data.message || getText('purchaseError'));
                }
                
                // 记录已确认的购买
                state.confirmedPurchases.add(purchaseData.purchase_id);
                
                return data;
            } catch (error) {
                log(`API端点 ${endpoint} 失败:`, error.message);
                
                // 确保清除超时
                if (timeoutId) {
                    clearTimeout(timeoutId);
                    timeoutId = null;
                }
                
                // 如果是最后一个API，则抛出错误
                if (i === state.apiEndpoints.confirm.length - 1) {
                    throw error;
                }
                
                // 否则尝试下一个API
                continue;
            }
        }
        
        // 不应该到达这里
        throw new Error(getText('serverError'));
    }
    
    // 处理购买按钮点击事件
    async function handleBuyButtonClick(event) {
        // 使用safeExecute避免潜在的无限循环或阻塞
        return safeExecute(async () => {
            // 防止短时间内重复点击
            const now = Date.now();
            if (state.purchaseInProgress || now - state.lastPurchaseTime < 3000) {
                log('忽略重复点击，间隔时间过短或处理中');
                event.preventDefault();
                event.stopPropagation();
                return false;
            }
            
            state.purchaseInProgress = true;
            state.lastPurchaseTime = now;
            
            try {
                // 获取按钮和相关数据
                const button = event.currentTarget;
                updateButtonState(button, true);
                
                // 检查钱包连接状态
                if (!isWalletConnected()) {
                    // 尝试打开钱包连接模态窗口
                    if (typeof window.connectWallet === 'function') {
                        window.connectWallet();
                    } else if (document.getElementById('connect-wallet-button')) {
                        document.getElementById('connect-wallet-button').click();
                    } else {
                        throw new Error(getText('walletNotConnected'));
                    }
                    return false;
                }
                
                // 获取资产ID
                let assetId = button.getAttribute('data-asset-id');
                if (!assetId) {
                    const assetElement = document.querySelector('[data-asset-id]');
                    if (assetElement) {
                        assetId = assetElement.getAttribute('data-asset-id');
                    }
                }
                
                if (!assetId) {
                    // 尝试从URL获取
                    const urlMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
                    if (urlMatch && urlMatch[1]) {
                        assetId = urlMatch[1];
                    }
                }
                
                // 规范化资产ID
                assetId = normalizeAssetId(assetId);
                
                // 获取购买数量
                let amount = 1; // 默认为1个
                
                // 首先尝试从按钮属性获取
                if (button.hasAttribute('data-amount')) {
                    amount = parseFloat(button.getAttribute('data-amount')) || 1;
                } else {
                    // 尝试从输入框获取
                    const amountInput = document.querySelector('#amount-input, #purchase-amount, input[name="amount"]');
                    if (amountInput) {
                        amount = parseFloat(amountInput.value) || 1;
                    }
                }
                
                // 验证输入
                if (isNaN(amount) || amount <= 0) {
                    throw new Error(getText('invalidAmount'));
                }
                
                log(`处理购买请求: 资产=${assetId}, 数量=${amount}`);
                
                // 准备购买请求
                const prepareResult = await preparePurchase(assetId, amount);
                
                if (!prepareResult || !prepareResult.success) {
                    throw new Error(prepareResult.message || getText('prepareFailed'));
                }
                
                log('购买请求准备成功:', prepareResult);
                state.purchaseData = prepareResult;
                
                // 显示确认模态窗口
                const modalContent = `
                    <p>确认购买以下资产:</p>
                    <ul>
                        <li>资产ID: ${assetId}</li>
                        <li>数量: ${amount}</li>
                        <li>价格: ${prepareResult.total_price || '获取中...'}</li>
                    </ul>
                    <p>点击确认完成购买。</p>
                `;
                
                showModal('确认购买', modalContent, async () => {
                    try {
                        hideModal();
                        
                        // 确认购买
                        const confirmResult = await confirmPurchase(prepareResult);
                        
                        if (!confirmResult || !confirmResult.success) {
                            throw new Error(confirmResult.message || getText('purchaseError'));
                        }
                        
                        log('购买确认成功:', confirmResult);
                        
                        // 显示成功消息
                        createAlert(getText('purchaseSuccess'), 'success');
                        
                        // 更新UI
                        updateUIAfterPurchase(assetId, amount);
                        
                    } catch (error) {
                        console.error('确认购买时出错:', error);
                        createAlert(error.message || getText('purchaseError'), 'error');
                    } finally {
                        updateButtonState(button, false);
                        state.purchaseInProgress = false;
                    }
                });
                
            } catch (error) {
                console.error('处理购买请求时出错:', error);
                createAlert(error.message || getText('purchaseError'), 'error');
                state.purchaseInProgress = false;
                
                // 尝试更新按钮状态
                try {
                    updateButtonState(event.currentTarget, false);
                } catch (e) {
                    console.debug('更新按钮状态失败:', e);
                }
            }
            
            // 阻止默认行为
            event.preventDefault();
            event.stopPropagation();
            return false;
        }, () => {
            // 降级处理：恢复UI状态
            console.debug('[购买处理] 处理购买按钮点击超时');
            state.purchaseInProgress = false;
            
            // 尝试更新按钮状态
            if (event && event.currentTarget) {
                try {
                    updateButtonState(event.currentTarget, false);
                } catch (e) {
                    console.debug('更新按钮状态失败:', e);
                }
            }
            
            createAlert('处理请求超时，请稍后重试', 'error');
            return false;
        });
    }
    
    // 购买成功后更新UI
    function updateUIAfterPurchase(assetId, amount) {
        // 刷新余额显示
        if (typeof window.updateWalletBalance === 'function') {
            window.updateWalletBalance();
        }
        
        // 刷新资产列表
        if (typeof window.refreshUserAssets === 'function') {
            window.refreshUserAssets();
        }
    }
    
    // 设置购买按钮事件
    function setupBuyButton() {
        // 如果已经设置过事件处理器，不要重复设置
        if (state.eventHandlersAttached) {
            log('事件处理器已附加，跳过重复设置');
            return;
        }
        
        try {
            // 查找所有购买按钮
            const buyButtons = document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"], #buyButton, .btn-buy, #buy-button');
            if (!buyButtons || buyButtons.length === 0) {
                log('页面上没有找到购买按钮');
                return;
            }
            
            log(`找到 ${buyButtons.length} 个购买按钮`);
            
            // 设置事件处理器
            buyButtons.forEach((button, index) => {
                // 跳过无效按钮
                if (!button || button.tagName !== 'BUTTON') return;
                
                // 检查是否已经设置过事件处理器
                if (button.getAttribute('data-buy-handler-attached') === 'true') {
                    log(`按钮 #${index} 已附加事件处理器，跳过`);
                    return;
                }
                
                // 保存原始文本
                if (!button.dataset.originalText) {
                    button.dataset.originalText = button.textContent.trim();
                }
                
                // 移除旧的事件监听器并附加新的
                const newButton = button.cloneNode(true);
                button.parentNode.replaceChild(newButton, button);
                
                newButton.addEventListener('click', handleBuyButtonClick);
                newButton.setAttribute('data-buy-handler-attached', 'true');
                
                log(`已设置按钮 #${index} 的点击事件处理器`);
            });
            
            // 标记已设置事件处理器
            state.eventHandlersAttached = true;
            
        } catch (error) {
            console.error('设置购买按钮事件时出错:', error);
        }
    }
    
    // 初始化函数
    function init() {
        return safeExecute(() => {
            // 防止重复初始化
            if (state.initialized) {
                log('购买处理已初始化，跳过重复执行');
                return;
            }
            
            log('正在初始化购买处理脚本...');
            
            // 初始化模块状态
            state.initialized = true;
            state.eventHandlersAttached = false;
            state.initializationTimestamp = Date.now();
            
            // 设置购买按钮事件处理器
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    setTimeout(setupBuyButton, 500);
                });
            } else {
                setTimeout(setupBuyButton, 500);
            }
            
            // 添加页面变化监听器，处理动态添加的按钮
            let lastSetupTime = 0;
            const observer = new MutationObserver((mutations) => {
                // 限制处理频率，避免性能问题
                const now = Date.now();
                if (now - lastSetupTime < 2000) return;
                
                // 检查是否有新的购买按钮
                const hasBuyButtons = document.querySelector('.buy-btn, .buy-button, [data-action="buy"], #buyButton, .btn-buy, #buy-button:not([data-buy-handler-attached="true"])');
                if (hasBuyButtons) {
                    lastSetupTime = now;
                    setTimeout(setupBuyButton, 200);
                }
            });
            
            // 配置并启动观察器
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: false,
                characterData: false
            });
            
            // 监听URL变化（单页应用）
            let lastUrl = location.href;
            const urlObserver = new MutationObserver(() => {
                const currentUrl = location.href;
                if (currentUrl !== lastUrl) {
                    lastUrl = currentUrl;
                    log('URL已变化，重新设置按钮...');
                    state.eventHandlersAttached = false;
                    setTimeout(setupBuyButton, 500);
                }
            });
            
            urlObserver.observe(document, { subtree: true, childList: true });
            
            log('购买处理脚本初始化完成');
            
            // 发布初始化完成事件
            document.dispatchEvent(new CustomEvent('buyHandlerReady'));
        }, () => {
            console.error('[购买处理] 初始化超时');
            state.initialized = true; // 防止重试
        });
    }
    
    // 启动初始化
    init();
})(); 