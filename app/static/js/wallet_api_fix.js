/**
 * RWA-HUB 钱包API修复脚本
 * 解决API 404错误和资产ID不一致问题
 * 版本: 1.3.0
 */

(function() {
    console.log('钱包API修复脚本已加载 - v1.3.0');
    
    // 调试设置
    const CONFIG = {
        debug: true,
        enableApiMocks: false, // 关闭模拟数据
        defaultAssetId: 'RH-205020',
        retryCount: 3,
        retryDelay: 500
    };
    
    // 调试日志
    function log(message, data = null) {
        if (CONFIG.debug) {
            if (data !== null) {
                console.log(`[钱包API修复] ${message}`, data);
            } else {
                console.log(`[钱包API修复] ${message}`);
            }
        }
    }
    
    // 存储原始fetch函数
    const originalFetch = window.fetch;
    
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
    
    // 改进的fetch函数 - 支持多端点尝试和错误处理
    async function fetchWithRetry(url, options = {}, retries = CONFIG.retryCount) {
        let lastError;
        
        // 标准化URL
        const normalizedUrl = normalizeApiUrl(url);
        
        // 尝试多次请求
        for (let i = 0; i < retries; i++) {
            try {
                if (i > 0) {
                    log(`重试API请求 (${i}/${retries}): ${normalizedUrl}`);
                    // 增加延迟，避免过多请求
                    await new Promise(resolve => setTimeout(resolve, CONFIG.retryDelay));
                }
                
                const response = await originalFetch(normalizedUrl, options);
                
                // 如果请求成功
                if (response.ok) {
                    return response;
                }
                
                lastError = new Error(`API请求失败: ${response.status} ${response.statusText}`);
                log(`API请求失败 (${i+1}/${retries}): ${normalizedUrl} - ${response.status}`);
            } catch (error) {
                lastError = error;
                log(`API请求异常 (${i+1}/${retries}): ${normalizedUrl}`, error);
            }
        }
        
        // 如果所有尝试都失败，抛出最后一个错误
        throw lastError || new Error(`无法完成API请求: ${normalizedUrl}`);
    }
    
    // 标准化API URL
    function normalizeApiUrl(url) {
        // 如果URL已经包含域名，不做修改
        if (url.startsWith('http')) {
            return url;
        }
        
        // 处理资产API路径
        if (url.includes('/api/assets/')) {
            // 检查URL中是否包含资产ID
            const assetIdMatch = url.match(/\/api\/assets\/([^\/\?]+)/);
            if (assetIdMatch && assetIdMatch[1]) {
                const originalId = assetIdMatch[1];
                const normalizedId = normalizeAssetId(originalId);
                
                // 只在需要时替换资产ID
                if (originalId !== normalizedId) {
                    return url.replace(originalId, normalizedId);
                }
            }
        }
        
        return url;
    }
    
    // 尝试多个可能的URL端点
    async function fetchWithMultipleUrls(urls, options = {}) {
        if (!Array.isArray(urls) || urls.length === 0) {
            throw new Error('没有提供有效的URL数组');
        }
        
        let lastError;
        
        // 尝试每个URL
        for (let i = 0; i < urls.length; i++) {
            try {
                log(`尝试API端点 ${i+1}/${urls.length}: ${urls[i]}`);
                const response = await fetchWithRetry(urls[i], options);
                return response;
            } catch (error) {
                lastError = error;
                log(`端点失败 ${i+1}/${urls.length}: ${urls[i]}`, error);
            }
        }
        
        // 所有URL都失败
        throw lastError || new Error('所有API端点请求失败');
    }
    
    // 钱包API - 多端点尝试获取钱包余额
    async function getWalletBalance(address) {
        if (!address) {
            throw new Error('获取余额需要钱包地址');
        }
        
        // 多个可能的API端点
        const urls = [
            `/api/get_wallet_balance?address=${address}`,
            `/api/balance?address=${address}`,
            `/api/wallet/balance?address=${address}`,
            `/api/user/balance?address=${address}`
        ];
        
        try {
            const response = await fetchWithMultipleUrls(urls);
            const data = await response.json();
            
            // 正常返回API结果
            return data;
        } catch (error) {
            log('获取钱包余额失败', error);
            throw new Error('无法获取钱包余额: ' + error.message);
        }
    }
    
    // 检查用户是否是管理员
    async function checkIsAdmin(address) {
        if (!address) {
            return { is_admin: false };
        }
        
        // 多个可能的API端点
        const urls = [
            `/api/is_admin?address=${address}`,
            `/api/check_admin?address=${address}`,
            `/api/user/admin_status?address=${address}`,
            `/api/admin/check?address=${address}`
        ];
        
        try {
            const response = await fetchWithMultipleUrls(urls);
            const data = await response.json();
            
            // 返回API结果
            return data;
        } catch (error) {
            log('检查管理员权限失败', error);
            // 在API失败时默认为非管理员，这是安全做法
            return { is_admin: false };
        }
    }
    
    // 重写fetch以支持重试和标准化URL
    window.fetch = async function(input, init) {
        let url = input;
        
        // 提取URL（如果input是Request对象）
        if (input instanceof Request) {
            url = input.url;
            if (!init) init = {};
        }
        
        // 检查是否是API调用
        if (typeof url === 'string' && url.includes('/api/')) {
            try {
                if (url.includes('/api/trades/prepare_purchase') || 
                    url.includes('/api/trades/confirm_purchase')) {
                    // 这些端点需要使用原始fetch并手动处理多端点尝试
                    return originalFetch(input, init);
                }
                
                // 对API请求应用重试逻辑
                return await fetchWithRetry(url, init);
            } catch (error) {
                // 只对标准错误类型进行处理
                throw error;
            }
        }
        
        // 对于非API请求，使用原始fetch
        return originalFetch(input, init);
    };
    
    // 改进资产详情API函数
    function enhanceAssetDetailApi() {
        // 查找原始函数
        const originalRefreshAssetInfo = window.refreshAssetInfo;
        
        if (typeof originalRefreshAssetInfo === 'function') {
            window.refreshAssetInfo = async function() {
                log('执行增强的资产详情刷新');
                
                try {
                    // 获取资产ID
                    let assetId = null;
                    
                    // 尝试多个可能的来源获取资产ID
                    // 1. 从全局ASSET_CONFIG
                    if (window.ASSET_CONFIG && window.ASSET_CONFIG.assetId) {
                        assetId = window.ASSET_CONFIG.assetId;
                        log('从ASSET_CONFIG获取资产ID:', assetId);
                    } 
                    // 2. 从URL参数
                    else if (window.location.pathname.includes('/assets/')) {
                        const pathMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
                        if (pathMatch && pathMatch[1]) {
                            assetId = pathMatch[1];
                            log('从URL路径获取资产ID:', assetId);
                        }
                    }
                    // 3. 从DOM元素
                    else {
                        const assetElement = document.querySelector('[data-asset-id]');
                        if (assetElement) {
                            assetId = assetElement.getAttribute('data-asset-id');
                            log('从DOM元素获取资产ID:', assetId);
                        }
                    }
                    
                    // 如果找不到资产ID，调用原始函数
                    if (!assetId) {
                        log('找不到资产ID，使用原始刷新函数');
                        return originalRefreshAssetInfo();
                    }
                    
                    // 标准化资产ID
                    const normalizedId = normalizeAssetId(assetId);
                    
                    // 多个可能的API端点
                    const urls = [
                        `/api/assets/symbol/${normalizedId}?_=${Date.now()}`,
                        `/api/assets/${normalizedId}?_=${Date.now()}`,
                        `/api/asset_details/${normalizedId}?_=${Date.now()}`,
                        `/api/assets/detail/${normalizedId}?_=${Date.now()}`
                    ];
                    
                    // 尝试请求可能的API端点
                    const response = await fetchWithMultipleUrls(urls);
                    const asset = await response.json();
                    
                    // 检查API响应
                    if (!asset || !asset.token_symbol) {
                        throw new Error('API返回的资产数据无效');
                    }
                    
                    // 更新UI元素
                    const updatedElements = updateAssetDetailsUI(asset);
                    log('资产详情API调用成功，已更新UI元素', updatedElements);
                    
                    // 保存最后获取的数据
                    window.lastAssetData = asset;
                    
                    return asset;
                } catch (error) {
                    log('增强资产详情API调用失败', error);
                    
                    // 如果有上次数据，使用它
                    if (window.lastAssetData) {
                        log('使用上次缓存的资产数据');
                        updateAssetDetailsUI(window.lastAssetData);
                        return window.lastAssetData;
                    }
                    
                    // 如果仍然失败，调用原始函数
                    log('调用原始刷新函数作为后备机制');
                    return originalRefreshAssetInfo();
                }
            };
            
            log('资产详情API函数已增强');
        }
    }
    
    // 更新资产详情UI元素
    function updateAssetDetailsUI(asset) {
        const updatedElements = [];
        
        try {
            // 更新资产名称
            const nameElements = document.querySelectorAll('.asset-name, #asset-name, [data-field="asset-name"]');
            nameElements.forEach(el => {
                el.textContent = asset.name || asset.token_symbol;
                updatedElements.push('asset-name');
            });
            
            // 更新资产符号
            const symbolElements = document.querySelectorAll('.asset-symbol, #asset-symbol, [data-field="asset-symbol"]');
            symbolElements.forEach(el => {
                el.textContent = asset.token_symbol;
                updatedElements.push('asset-symbol');
            });
            
            // 更新资产价格
            const priceElements = document.querySelectorAll('.asset-price, #asset-price, [data-field="asset-price"]');
            if (asset.token_price) {
                priceElements.forEach(el => {
                    el.textContent = `$${parseFloat(asset.token_price).toFixed(2)}`;
                    updatedElements.push('asset-price');
                });
            }
            
            // 更新资产总供应量
            const supplyElements = document.querySelectorAll('.asset-supply, #asset-supply, [data-field="asset-supply"]');
            if (asset.token_supply) {
                supplyElements.forEach(el => {
                    el.textContent = parseInt(asset.token_supply).toLocaleString();
                    updatedElements.push('asset-supply');
                });
            }
            
            // 更新资产剩余供应量
            const remainingElements = document.querySelectorAll('.asset-remaining, #asset-remaining, [data-field="asset-remaining"]');
            if (asset.remaining_supply) {
                remainingElements.forEach(el => {
                    el.textContent = parseInt(asset.remaining_supply).toLocaleString();
                    updatedElements.push('asset-remaining');
                });
            }
            
            // 更新购买按钮的数据属性
            const buyButtons = document.querySelectorAll('#buy-button, .buy-button, [data-action="buy"]');
            buyButtons.forEach(btn => {
                btn.setAttribute('data-asset-id', asset.id || asset.token_symbol);
                if (asset.token_price) {
                    btn.setAttribute('data-token-price', asset.token_price);
                }
                updatedElements.push('buy-button');
            });
            
            // 更新描述
            const descElements = document.querySelectorAll('.asset-description, #asset-description, [data-field="asset-description"]');
            if (asset.description) {
                descElements.forEach(el => {
                    el.textContent = asset.description;
                    updatedElements.push('asset-description');
                });
            }
        } catch (error) {
            log('更新资产详情UI时出错', error);
        }
        
        return updatedElements;
    }
    
    // 增强钱包连接检查
    function enhanceWalletConnectCheck() {
        // 保存原始函数
        if (typeof window.isWalletConnected === 'function') {
            const originalCheck = window.isWalletConnected;
            
            // 增强函数
            window.isWalletConnected = function() {
                try {
                    // 首先尝试原始方法
                    const originalResult = originalCheck();
                    
                    // 如果原始方法确认已连接，直接返回
                    if (originalResult === true) {
                        return true;
                    }
                    
                    // 多重检查
                    // 1. 检查localStorage
                    const storedAddress = localStorage.getItem('walletAddress');
                    if (storedAddress) {
                        return true;
                    }
                    
                    // 2. 检查walletState对象
                    if (window.walletState) {
                        if (window.walletState.isConnected || 
                            window.walletState.connected ||
                            window.walletState.address) {
                            return true;
                        }
                    }
                    
                    // 返回原始结果
                    return originalResult;
                } catch (error) {
                    log('增强钱包连接检查出错', error);
                    return false; // 安全默认值
                }
            };
            
            log('钱包连接检查函数已增强');
        }
    }
    
    // 增强全局钱包API
    function enhanceGlobalWalletApi() {
        // 增强或创建全局getWalletBalance函数
        window.getWalletBalance = async function(address) {
            try {
                return await getWalletBalance(address);
            } catch (error) {
                log('获取钱包余额失败', error);
                return { balance: 0 };
            }
        };
        
        // 增强或创建全局checkIsAdmin函数
        window.checkIsAdmin = async function(address) {
            try {
                return await checkIsAdmin(address);
            } catch (error) {
                log('检查管理员权限失败', error);
                return { is_admin: false };
            }
        };
        
        log('全局钱包API函数已增强');
    }
    
    // 初始化
    function init() {
        enhanceAssetDetailApi();
        enhanceWalletConnectCheck();
        enhanceGlobalWalletApi();
        log('钱包API修复脚本初始化完成');
    }
    
    // 在DOM加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(); 