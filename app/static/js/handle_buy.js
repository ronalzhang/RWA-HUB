/**
 * 统一购买处理脚本
 * 支持多语言界面
 * 版本：1.2.1 - 修复API调用问题和购买流程
 */

(function() {
    console.log('加载购买处理脚本 v1.2.1');
    
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
        debug: true,
        apiTimeoutMs: 15000,      // API请求超时时间增加到15秒
        enableApiCache: true,     // 启用API缓存
        cacheExpiry: 30000,       // 缓存过期时间：30秒
        maxRetries: 3,            // 最大重试次数增加到3次
        retryDelayMs: 1500,       // 重试延迟增加到1.5秒
        defaultAssetId: 'RH-205020',
        lastRequestTime: 0,       // 上次请求时间
        minRequestInterval: 3000, // 最小请求间隔减少到3秒
        requestCount: 0,          // 请求计数器
        maxRequestsPerMinute: 20  // 每分钟最大请求数增加到20
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
        }
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
                log('钱包状态检查：通过localStorage确认已连接，地址:' + storedAddress.substring(0,6) + '...');
                return true;
            }
            
            // 4. 检查特定元素
            const walletButton = document.querySelector('#connect-wallet-button, #wallet-button, #walletBtn');
            if (walletButton && walletButton.getAttribute('data-connected') === 'true') {
                log('钱包状态检查：通过UI元素确认已连接');
                return true;
            }
            
            // 默认为未连接
            log('钱包状态检查：未连接');
            return false;
        } catch (error) {
            log('检查钱包连接状态时出错', error);
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
            log('获取钱包地址时出错', error);
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
            log(`API请求频率过高，最后请求时间: ${new Date(CONFIG.lastRequestTime).toLocaleTimeString()}`);
            return false;
        }
        
        // 检查每分钟最大请求数
        if (CONFIG.requestCount >= CONFIG.maxRequestsPerMinute) {
            log(`已达到每分钟最大API请求数: ${CONFIG.maxRequestsPerMinute}`);
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
        try {
            // 首先尝试使用Sweetalert2或类似库
            if (window.Swal) {
                window.Swal.fire({
                    title: type === 'error' ? '错误' : '提示',
                    text: message,
                    icon: type,
                    confirmButtonText: '确定'
                });
                return;
            }
            
            // 尝试使用Bootstrap toast
            if (window.bootstrap && window.bootstrap.Toast) {
                // 查找或创建toast容器
                let toastContainer = document.getElementById('toast-container');
                if (!toastContainer) {
                    toastContainer = document.createElement('div');
                    toastContainer.id = 'toast-container';
                    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                    document.body.appendChild(toastContainer);
                }
                
                // 创建toast元素
                const toastId = 'toast-' + Date.now();
                const toastEl = document.createElement('div');
                toastEl.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : 'primary'} border-0`;
                toastEl.id = toastId;
                toastEl.setAttribute('role', 'alert');
                toastEl.setAttribute('aria-live', 'assertive');
                toastEl.setAttribute('aria-atomic', 'true');
                
                // 设置toast内容
                toastEl.innerHTML = `
                    <div class="d-flex">
                        <div class="toast-body">
                            ${message}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                `;
                
                // 添加到容器
                toastContainer.appendChild(toastEl);
                
                // 初始化并显示toast
                const toast = new window.bootstrap.Toast(toastEl, {
                    autohide: true,
                    delay: 5000
                });
                toast.show();
                
                // 设置自动移除
                toastEl.addEventListener('hidden.bs.toast', () => {
                    toastEl.remove();
                });
                
                return;
            }
            
            // 如果以上都不可用，回退到alert
            if (type === 'error') {
                alert('错误: ' + message);
            } else {
                alert(message);
            }
        } catch (error) {
            log('显示提示信息时出错', error);
            alert(message);
        }
    }
    
    // 创建较美观的模态框
    function showModal(title, content, confirmCallback = null) {
        try {
            // 查找现有模态框或创建新的
            let modal = document.getElementById('purchase-confirmation-modal');
            if (!modal) {
                // 创建模态框元素
                modal = document.createElement('div');
                modal.className = 'modal fade';
                modal.id = 'purchase-confirmation-modal';
                modal.setAttribute('tabindex', '-1');
                modal.setAttribute('aria-labelledby', 'modalLabel');
                modal.setAttribute('aria-hidden', 'true');
                
                // 设置模态框HTML结构
                modal.innerHTML = `
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="modalLabel">${title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                ${content}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                                <button type="button" class="btn btn-primary" id="modal-confirm-button">确认</button>
                            </div>
                        </div>
                    </div>
                `;
                
                // 添加到文档
                document.body.appendChild(modal);
            } else {
                // 更新现有模态框内容
                modal.querySelector('.modal-title').textContent = title;
                modal.querySelector('.modal-body').innerHTML = content;
            }
            
            // 初始化模态框
            let modalInstance;
            if (window.bootstrap && window.bootstrap.Modal) {
                modalInstance = new window.bootstrap.Modal(modal);
            }
            
            // 设置确认按钮事件
            const confirmButton = modal.querySelector('#modal-confirm-button');
            if (confirmButton && confirmCallback) {
                // 移除之前的事件监听器
                const newButton = confirmButton.cloneNode(true);
                confirmButton.parentNode.replaceChild(newButton, confirmButton);
                
                // 添加新的事件监听器
                newButton.addEventListener('click', async () => {
                    // 禁用按钮并显示加载状态
                    newButton.disabled = true;
                    newButton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 处理中...`;
                    
                    try {
                        // 调用回调函数
                        await confirmCallback();
                        
                        // 隐藏模态框
                        if (modalInstance) {
                            modalInstance.hide();
                        } else {
                            modal.style.display = 'none';
                        }
                    } catch (error) {
                        log('模态框确认回调执行出错', error);
                        
                        // 显示错误消息
                        const errorContainer = modal.querySelector('.modal-error');
                        if (errorContainer) {
                            errorContainer.textContent = error.message || '处理请求时出错';
                            errorContainer.style.display = 'block';
                        } else {
                            // 如果没有错误容器，创建一个
                            const errorDiv = document.createElement('div');
                            errorDiv.className = 'alert alert-danger mt-3 modal-error';
                            errorDiv.textContent = error.message || '处理请求时出错';
                            modal.querySelector('.modal-body').appendChild(errorDiv);
                        }
                    } finally {
                        // 恢复按钮状态
                        newButton.disabled = false;
                        newButton.textContent = '确认';
                    }
                });
            }
            
            // 显示模态框
            if (modalInstance) {
                modalInstance.show();
            } else {
                modal.style.display = 'block';
                modal.classList.add('show');
            }
            
            // 更新状态
            state.modalVisible = true;
            
        } catch (error) {
            log('显示模态框时出错', error);
            
            // 回退到基本确认对话框
            if (confirmCallback && confirm(content)) {
                confirmCallback();
            }
        }
    }
    
    // 隐藏模态框
    function hideModal() {
        try {
            const modal = document.getElementById('purchase-confirmation-modal');
            if (!modal) return;
            
            if (window.bootstrap && window.bootstrap.Modal) {
                const bsModal = window.bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            } else {
                // 简易隐藏
                modal.style.display = 'none';
                modal.classList.remove('show');
            }
            
            state.modalVisible = false;
        } catch (error) {
            log('隐藏模态框时出错', error);
        }
    }
    
    // 更新按钮状态，使用全局updateBuyButtonState函数
    function updateButtonState(button, isLoading) {
        if (!button) return;
        
        // 默认文本
        const defaultText = getText('processing');
        const originalText = button.dataset.originalText || 'Buy';
        
        if (isLoading) {
            // 保存原始文本，如果尚未保存
            if (!button.dataset.originalText) {
                button.dataset.originalText = button.textContent.trim();
            }
            
            // 设置加载状态
            button.disabled = true;
            
            // 使用全局函数更新按钮
            if (typeof window.updateBuyButtonState === 'function') {
                window.updateBuyButtonState(button, defaultText, true);
            } else {
                // 后备方案
                const spinner = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>`;
                button.innerHTML = spinner + defaultText;
            }
        } else {
            // 恢复按钮状态
            button.disabled = false;
            
            // 使用全局函数恢复按钮文本
            if (typeof window.updateBuyButtonState === 'function') {
                window.updateBuyButtonState(button, originalText, true);
            } else {
                // 后备方案
                button.textContent = originalText;
            }
        }
    }
    
    // 准备购买请求 - 修复API请求问题
    async function preparePurchase(assetId, amount) {
        // 检查API请求限制
        if (!checkApiRateLimit()) {
            return {
                success: false,
                error: '请求频率过高，请稍后再试'
            };
        }
        
        // 获取钱包地址
        const walletAddress = getWalletAddress();
        if (!walletAddress) {
            return {
                success: false,
                error: getText('walletNotConnected')
            };
        }
        
        // 标准化资产ID
        assetId = normalizeAssetId(assetId);
        
        // 准备请求数据
        const requestData = {
            asset_id: assetId,
            amount: amount,
            wallet_address: walletAddress,
            wallet_type: localStorage.getItem('walletType') || 'unknown'
        };
        
        // 缓存键
        const cacheKey = `prepare_${assetId}_${amount}_${walletAddress}`;
        
        // 检查缓存
        const cachedResult = getFromCache(cacheKey);
        if (cachedResult) {
            return cachedResult;
        }
        
        log('准备购买请求数据:', requestData);
        
        // 失败重试
        let lastError = null;
        
        // 尝试所有可能的API端点
        const endpoints = state.apiEndpoints.prepare;
        
        for (let i = 0; i < endpoints.length; i++) {
            try {
                // 设置请求超时
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), CONFIG.apiTimeoutMs);
                
                // 发送请求
                log(`尝试API端点 ${i+1}/${endpoints.length}: ${endpoints[i]}`);
                const response = await fetch(endpoints[i], {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData),
                    signal: controller.signal
                });
                
                // 清除超时
                clearTimeout(timeoutId);
                
                // 检查响应状态
                if (!response.ok) {
                    lastError = new Error(`API返回错误状态: ${response.status}`);
                    continue;
                }
                
                // 解析响应数据
                const result = await response.json();
                
                // 添加到缓存
                addToCache(cacheKey, result);
                
                log('准备购买请求成功:', result);
                return result;
            } catch (error) {
                lastError = error;
                log(`准备购买API端点 ${endpoints[i]} 失败:`, error);
            }
        }
        
        // 所有端点都失败
        log('所有准备购买API端点都失败，最后错误:', lastError);
        throw lastError || new Error('所有准备购买API端点都失败');
    }
    
    // 确认购买请求 - 修复API请求问题
    async function confirmPurchase(purchaseData) {
        // 检查API请求限制
        if (!checkApiRateLimit()) {
            return {
                success: false,
                error: '请求频率过高，请稍后再试'
            };
        }
        
        // 检查购买数据
        if (!purchaseData || !purchaseData.trade_id) {
            log('确认购买缺少必要数据:', purchaseData);
            return {
                success: false,
                error: '缺少购买交易ID'
            };
        }
        
        // 准备请求数据
        const requestData = {
            trade_id: purchaseData.trade_id
        };
        
        // 缓存键 - 确认请求不应该被缓存，但记录已确认的交易
        const tradeId = purchaseData.trade_id;
        
        // 检查是否已经确认过
        if (state.confirmedPurchases.has(tradeId)) {
            log(`交易 ${tradeId} 已经确认过，返回成功状态`);
            return {
                success: true,
                status: 'completed',
                message: getText('purchaseCompleted')
            };
        }
        
        log('确认购买请求数据:', requestData);
        
        // 失败重试
        let lastError = null;
        
        // 尝试所有可能的API端点
        const endpoints = state.apiEndpoints.confirm;
        
        for (let i = 0; i < endpoints.length; i++) {
            try {
                // 设置请求超时
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), CONFIG.apiTimeoutMs);
                
                // 发送请求
                log(`尝试确认API端点 ${i+1}/${endpoints.length}: ${endpoints[i]}`);
                const response = await fetch(endpoints[i], {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData),
                    signal: controller.signal
                });
                
                // 清除超时
                clearTimeout(timeoutId);
                
                // 检查响应状态
                if (!response.ok) {
                    lastError = new Error(`API返回错误状态: ${response.status}`);
                    continue;
                }
                
                // 解析响应数据
                const result = await response.json();
                
                // 如果成功，记录已确认的交易ID
                if (result.success) {
                    state.confirmedPurchases.add(tradeId);
                }
                
                log('确认购买请求成功:', result);
                return result;
            } catch (error) {
                lastError = error;
                log(`确认购买API端点 ${endpoints[i]} 失败:`, error);
            }
        }
        
        // 所有端点都失败
        log('所有确认购买API端点都失败，最后错误:', lastError);
        throw lastError || new Error('所有确认购买API端点都失败');
    }
    
    // 处理购买按钮点击
    async function handleBuyButtonClick(event) {
        // 防止表单提交和页面跳转
        event.preventDefault();
        event.stopPropagation();
        
        // 如果购买已在进行中，防止重复点击
        if (state.purchaseInProgress) {
            log('购买已在进行中，忽略重复点击');
            return;
        }
        
        try {
            // 标记购买正在进行中
            state.purchaseInProgress = true;
            
            // 获取按钮和相关元素
            const button = event.currentTarget;
            updateButtonState(button, true);
            
            // 检查钱包连接状态
            if (!isWalletConnected()) {
                log('钱包未连接，无法继续购买');
                createAlert(getText('walletNotConnected'), 'error');
                updateButtonState(button, false);
                state.purchaseInProgress = false;
                return;
            }
            
            // 获取资产ID
            let assetId = button.getAttribute('data-asset-id');
            if (!assetId) {
                // 尝试从页面其他位置获取
                assetId = document.querySelector('[data-asset-id]')?.getAttribute('data-asset-id');
            }
            if (!assetId) {
                // 尝试从URL获取
                const urlMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
                if (urlMatch) {
                    assetId = urlMatch[1];
                }
            }
            
            // 最后使用默认资产ID
            if (!assetId) {
                assetId = CONFIG.defaultAssetId;
                log('未找到资产ID，使用默认ID:', assetId);
            } else {
                log('找到资产ID:', assetId);
            }
            
            // 获取购买数量
            const amountInput = document.getElementById('purchase-amount') || 
                               document.querySelector('input[name="amount"]') || 
                               document.querySelector('.purchase-amount');
            
            if (!amountInput) {
                log('找不到购买数量输入框');
                createAlert(getText('missingAmountInput'), 'error');
                updateButtonState(button, false);
                state.purchaseInProgress = false;
                return;
            }
            
            // 解析购买数量
            const amount = parseFloat(amountInput.value);
            if (isNaN(amount) || amount <= 0) {
                log('无效的购买数量:', amountInput.value);
                createAlert(getText('invalidAmount'), 'error');
                updateButtonState(button, false);
                state.purchaseInProgress = false;
                return;
            }
            
            // 准备购买请求
            log('准备购买请求:', { assetId, amount });
            const prepareResult = await preparePurchase(assetId, amount);
            
            // 处理准备购买响应
            if (!prepareResult.success) {
                // 显示错误消息
                if (prepareResult.error) {
                    createAlert(prepareResult.error, 'error');
                } else {
                    createAlert(getText('prepareFailed'), 'error');
                }
                
                // 如果是API错误，清楚地告诉用户
                if (prepareResult.isApiError) {
                    createAlert('服务器API不可用，购买功能暂时无法使用。请联系管理员。', 'error');
                }
                
                updateButtonState(button, false);
                state.purchaseInProgress = false;
                
                return;
            }
            
            // 保存购买数据用于确认
            state.purchaseData = prepareResult;
            
            // 创建确认弹窗内容
            const modalContent = `
                <div>
                    <p>请确认以下购买信息:</p>
                    <ul class="list-group mb-3">
                        <li class="list-group-item d-flex justify-content-between">
                            <span>资产:</span>
                            <strong>${prepareResult.token_symbol || assetId}</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>购买数量:</span>
                            <strong>${prepareResult.amount || amount}</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>单价:</span>
                            <strong>${prepareResult.price} USDC</strong>
                        </li>
                        <li class="list-group-item d-flex justify-content-between">
                            <span>总价:</span>
                            <strong>${prepareResult.total} USDC</strong>
                        </li>
                    </ul>
                    <div class="alert alert-info">
                        <small>确认后，资产将添加到您的钱包: <code>${prepareResult.wallet_address}</code></small>
                    </div>
                    <div class="alert alert-danger mt-3 modal-error" style="display: none;"></div>
                </div>
            `;
            
            // 显示确认弹窗
            showModal('确认购买', modalContent, async () => {
                try {
                    log('用户确认购买，开始确认交易...');
                    const confirmResult = await confirmPurchase(prepareResult);
                    
                    // 处理确认响应
                    if (confirmResult.success) {
                        log('购买确认成功:', confirmResult);
                        
                        // 隐藏模态框
                        hideModal();
                        
                        // 显示成功消息
                        createAlert(getText('purchaseCompleted'), 'success');
                        
                        // 可选：刷新页面或更新UI
                        setTimeout(() => {
                            // 如果需要刷新页面，取消注释下一行
                            // window.location.reload();
                            
                            // 或者更新UI显示
                            updateUIAfterPurchase(assetId, amount);
                        }, 1500);
                    } else {
                        // 显示错误消息
                        const errorMessage = confirmResult.error || getText('purchaseError');
                        createAlert(errorMessage, 'error');
                        log('购买确认失败:', confirmResult);
                        
                        // 标记API错误
                        if (confirmResult.isApiError) {
                            createAlert('服务器API不可用，购买无法完成。请联系管理员。', 'error');
                        }
                    }
                } catch (error) {
                    log('确认购买过程中出错:', error);
                    createAlert(getText('purchaseError'), 'error');
                }
                
                // 恢复按钮状态
                updateButtonState(button, false);
                state.purchaseInProgress = false;
            });
        } catch (error) {
            log('处理购买按钮点击时出错:', error);
            createAlert(getText('purchaseError'), 'error');
            updateButtonState(event.currentTarget, false);
            state.purchaseInProgress = false;
        }
    }
    
    // 更新购买后的UI
    function updateUIAfterPurchase(assetId, amount) {
        // 尝试更新可用数量显示
        const remainingElement = document.querySelector('.asset-remaining, .remaining-supply, #remainingSupply');
        if (remainingElement) {
            const currentRemaining = parseInt(remainingElement.textContent) || 0;
            const newRemaining = Math.max(0, currentRemaining - amount);
            remainingElement.textContent = newRemaining.toString();
        }
        
        // 可能还需要更新其他UI元素
    }
    
    // 设置购买按钮监听器
    function setupBuyButton() {
        try {
            // 查找所有可能的购买按钮
            const selectors = [
                '#buy-button', 
                '.buy-button', 
                '.buy-btn', 
                '[data-action="buy"]',
                '.detail-buy-button',
                '[data-asset-action="buy"]'
            ];
            
            // 收集所有找到的按钮
            const allButtons = [];
            selectors.forEach(selector => {
                const buttons = document.querySelectorAll(selector);
                if (buttons.length > 0) {
                    buttons.forEach(btn => allButtons.push(btn));
                }
            });
            
            // 如果没有找到任何按钮，尝试等待DOM加载完成后再次尝试
            if (allButtons.length === 0) {
                log('找不到购买按钮，将在DOM加载完成后再次尝试');
                
                // 等待DOM加载完成
                if (document.readyState !== 'complete') {
                    window.addEventListener('load', setupBuyButton);
                } else {
                    // DOM已加载，但仍未找到按钮，尝试在短暂延迟后再次尝试
                    setTimeout(setupBuyButton, 1000);
                }
                return;
            }
            
            // 为每个按钮绑定点击事件
            allButtons.forEach(button => {
                // 保存原始文本，确保是"Buy"或本地化版本
                const originalText = button.textContent.trim();
                const buyTexts = ['Buy', 'buy', '购买', '买入'];
                if (!button.hasAttribute('data-original-text')) {
                    const textToSave = buyTexts.includes(originalText) ? originalText : 'Buy';
                    button.setAttribute('data-original-text', textToSave);
                }
                
                // 移除现有事件监听器，避免重复绑定
                const newButton = button.cloneNode(true);
                if (originalText && buyTexts.includes(originalText)) {
                    newButton.textContent = originalText;
                } else if (button.hasAttribute('data-original-text')) {
                    newButton.textContent = button.getAttribute('data-original-text');
                } else {
                    newButton.textContent = 'Buy';
                }
                
                // 确保按钮文本是正确的
                if (newButton.textContent.match(/^\d+(\.\d+)?$/)) {
                    newButton.textContent = 'Buy';
                }
                
                button.parentNode.replaceChild(newButton, button);
                
                // 绑定新的事件监听器
                newButton.addEventListener('click', handleBuyButtonClick);
            });
            
            log('购买按钮成功绑定点击事件');
        } catch (error) {
            log('设置购买按钮监听器时出错:', error);
        }
    }
    
    // 初始化
    function init() {
        log('初始化购买处理模块');
        
        // 设置购买按钮
        setupBuyButton();
        
        // 监听DOM变化，处理动态添加的按钮
        const observer = new MutationObserver(setupBuyButton);
        observer.observe(document.body, { 
            childList: true, 
            subtree: true 
        });
        
        // 设置全局购买处理函数
        window.handleBuy = handleBuyButtonClick;
        
        log('购买处理模块初始化完成');
    }
    
    // 文档加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // 当window.confirmPurchase函数被调用时处理
    window.confirmPurchase = async function(purchaseData, modalElement, confirmButton) {
        if (state.purchaseInProgress) {
            log('已有购买请求正在处理中，请等待');
            return;
        }
        
        state.purchaseInProgress = true;
        log('开始处理购买确认', purchaseData);
        
        try {
            // 更新按钮状态
            updateButtonState(confirmButton, true);
            
            // 检查钱包连接
            if (!isWalletConnected()) {
                throw new Error(getText('walletNotConnected'));
            }
            
            // 检查购买数据
            if (!purchaseData || !purchaseData.asset_id || !purchaseData.amount) {
                throw new Error('购买数据无效');
            }
            
            // 验证交易ID
            if (!purchaseData.trade_id) {
                log('交易ID不存在，将准备新的购买请求');
                // 准备购买请求
                const prepareResult = await preparePurchase(
                    purchaseData.asset_id,
                    purchaseData.amount
                );
                
                if (!prepareResult || !prepareResult.success) {
                    throw new Error(prepareResult?.error || getText('prepareFailed'));
                }
                
                // 更新交易ID
                purchaseData.trade_id = prepareResult.trade_id;
                log('已获取交易ID', purchaseData.trade_id);
            }
            
            // 确认购买
            log('执行购买确认', purchaseData);
            const confirmResult = await confirmPurchase(purchaseData);
            
            if (!confirmResult || !confirmResult.success) {
                throw new Error(confirmResult?.error || getText('purchaseError'));
            }
            
            // 购买成功
            log('购买确认成功', confirmResult);
            
            // 隐藏模态框
            if (modalElement && typeof bootstrap !== 'undefined') {
                const bsModal = bootstrap.Modal.getInstance(modalElement);
                if (bsModal) {
                    bsModal.hide();
                }
            }
            
            // 显示成功消息
            createAlert(getText('purchaseCompleted'), 'success');
            
            // 更新UI
            updateUIAfterPurchase(purchaseData.asset_id, purchaseData.amount);
            
            // 刷新钱包资产
            if (typeof window.refreshWalletAssets === 'function') {
                window.refreshWalletAssets();
            }
            
            return confirmResult;
        } catch (error) {
            log('购买确认失败', error);
            
            // 显示错误消息
            const modalError = document.getElementById('buyModalError');
            if (modalError) {
                modalError.textContent = error.message || getText('purchaseError');
                modalError.style.display = 'block';
            } else {
                // 如果找不到模态错误元素，使用弹出提示
                createAlert(error.message || getText('purchaseError'), 'danger');
            }
            
            throw error;
        } finally {
            // 恢复按钮状态
            updateButtonState(confirmButton, false);
            state.purchaseInProgress = false;
        }
    };
})(); 