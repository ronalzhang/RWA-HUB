/**
 * 统一购买处理脚本
 * 支持多语言界面
 * 版本：1.1.5 - 增强钱包检测与API错误处理，提升API兼容性
 */

(function() {
    console.log('加载购买处理脚本 v1.1.5');
    
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
            prepareFailed: 'Failed to prepare purchase',
            purchaseError: 'Error processing purchase',
            insufficientFunds: 'Insufficient funds to complete purchase',
            purchaseSuccess: 'Purchase request submitted! Please wait for transaction confirmation.',
            purchaseCompleted: 'Purchase successful! Assets will be added to your wallet in a few minutes.'
        }
    };
    
    // 获取当前语言
    function getCurrentLanguage() {
        const htmlLang = document.documentElement.lang || 'en';
        const langCookie = document.cookie.split(';').find(c => c.trim().startsWith('language='));
        const cookieLang = langCookie ? langCookie.split('=')[1].trim() : null;
        
        return (cookieLang || htmlLang).startsWith('zh') ? 'zh' : 'en';
    }
    
    // 获取本地化文本
    function getText(key) {
        const lang = getCurrentLanguage();
        return (TEXTS[lang] && TEXTS[lang][key]) || TEXTS['en'][key];
    }
    
    // 配置
    const CONFIG = {
        debug: true,
        retryCount: 3,
        retryDelay: 1000,
        platformFeeRate: 0.035 // 3.5%平台费率
    };
    
    // 日志函数
    function log(message, data) {
        if (CONFIG.debug) {
            console.log(`[购买处理] ${message}`, data || '');
        }
    }
    
    // 资产ID格式标准化
    function normalizeAssetId(assetId) {
        if (!assetId) return '';
        
        // 如果是纯数字格式的ID，转换为RH-格式
        if (/^\d+$/.test(assetId)) {
            return `RH-${assetId}`;
        }
        
        // 如果已经是RH-格式，直接返回
        if (assetId.startsWith('RH-')) {
            return assetId;
        }
        
        // 其他情况，尝试提取数字部分并转换
        const numericMatch = assetId.match(/(\d+)/);
        if (numericMatch && numericMatch[1]) {
            return `RH-${numericMatch[1]}`;
        }
        
        return assetId;
    }
    
    // 检查钱包连接状态 - 增强版
    async function checkWalletConnection() {
        log('执行增强版钱包连接检查');
        
        // 方法1: 检查localStorage
        const storedAddress = localStorage.getItem('walletAddress');
        const storedType = localStorage.getItem('walletType');
        
        if (storedAddress && storedType) {
            log('本地存储发现钱包连接', { address: storedAddress, type: storedType });
            return {
                connected: true,
                address: storedAddress,
                walletType: storedType
            };
        }
        
        // 方法2: 检查walletState对象
        if (window.walletState) {
            // 如果有函数，使用函数检查
            if (typeof window.walletState.isWalletConnected === 'function') {
                try {
                    const isConnected = await window.walletState.isWalletConnected();
                    if (isConnected) {
                        log('walletState.isWalletConnected确认已连接', { 
                            address: window.walletState.address,
                            type: window.walletState.walletType
                        });
                        return {
                            connected: true,
                            address: window.walletState.address,
                            walletType: window.walletState.walletType
                        };
                    }
                } catch (e) {
                    log('walletState.isWalletConnected调用失败', e);
                }
            }
            
            // 否则检查属性
            if (window.walletState.isConnected || window.walletState.connected) {
                log('walletState属性确认已连接', { 
                    address: window.walletState.address,
                    type: window.walletState.walletType 
                });
                return {
                    connected: true,
                    address: window.walletState.address,
                    walletType: window.walletState.walletType
                };
            }
        }
        
        // 方法3: 在window对象上查找其他可能存在的钱包变量
        const possibleAddressVars = [
            'walletPublicKey', 
            'ethereumAddress', 
            'solanaAddress', 
            'connectedWalletAddress'
        ];
        
        for (const varName of possibleAddressVars) {
            if (window[varName]) {
                let address = '';
                
                // 尝试获取地址字符串
                if (typeof window[varName] === 'string') {
                    address = window[varName];
                } else if (typeof window[varName] === 'object' && typeof window[varName].toString === 'function') {
                    address = window[varName].toString();
                }
                
                if (address && address.length > 30) {
                    log(`从window.${varName}发现钱包地址`, address);
                    return {
                        connected: true,
                        address: address,
                        walletType: 'phantom' // 假设是phantom，因为地址长度符合Solana地址
                    };
                }
            }
        }
        
        // 如果以上方法都失败，尝试直接连接钱包
        try {
            log('尝试主动连接钱包');
            if (typeof window.connectWallet === 'function') {
                const address = await window.connectWallet();
                if (address) {
                    log('成功连接钱包', address);
                    return {
                        connected: true,
                        address: address,
                        walletType: 'phantom'
                    };
                }
            }
        } catch (e) {
            log('主动连接钱包失败', e);
        }
        
        // 所有方法都失败，返回未连接状态
        log('所有连接检查方法均失败，认为钱包未连接');
        return {
            connected: false,
            address: null,
            walletType: null
        };
    }
    
    // 显示消息
    function showMessage(message, type = 'info') {
        // 如果存在全局showMessage函数，优先使用
        if (typeof window.showMessage === 'function') {
            window.showMessage(message, type);
            return;
        }
        
        // 创建通知元素
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type} position-fixed top-0 start-50 translate-middle-x mt-3`;
        messageDiv.style.zIndex = '9999';
        messageDiv.innerHTML = message;
        document.body.appendChild(messageDiv);
        
        // 3秒后自动消失
        setTimeout(() => {
            messageDiv.remove();
        }, 3000);
    }
    
    // 准备购买API调用 - 多端点尝试
    async function preparePurchase(assetId, amount, walletAddress) {
        log('准备购买API调用', { assetId, amount, walletAddress });
        
        // 标准化资产ID
        const normalizedAssetId = normalizeAssetId(assetId);
        
        // 构建请求数据
        const requestData = {
            asset_id: normalizedAssetId,
            amount: parseInt(amount),
            wallet_address: walletAddress
        };
        
        // 多重尝试URLs
        const urls = [
            '/api/trades/prepare_purchase',
            '/api/prepare_purchase',
            '/api/purchase/prepare',
            '/api/trade/prepare'
        ];
        
        let lastError = null;
        
        // 尝试多个URLs
        for (let i = 0; i < urls.length; i++) {
            const url = urls[i];
            
            try {
                log(`尝试API端点 ${i+1}/${urls.length}: ${url}`);
                
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                if (response.ok) {
                    const data = await response.json();
                    log('准备购买API调用成功', data);
                    return data;
                }
                
                const errorText = await response.text().catch(() => '');
                lastError = new Error(`端点 ${url} 返回错误代码: ${response.status} ${errorText}`);
                log(lastError.message);
            } catch (error) {
                lastError = error;
                log(`端点 ${url} 调用失败`, error);
            }
        }
        
        // 如果所有端点都失败，抛出最后一个错误
        throw lastError || new Error('所有API端点调用失败');
    }
    
    // 确认购买API调用 - 多端点尝试
    async function confirmPurchase(tradeId, walletAddress) {
        log('确认购买API调用', { tradeId, walletAddress });
        
        // 检查tradeId参数
        if (!tradeId) {
            throw new Error('交易ID不存在，无法完成购买');
        }
        
        // 构建请求数据
        const requestData = {
            trade_id: tradeId,
            wallet_address: walletAddress
        };
        
        // 多重尝试URLs
        const urls = [
            '/api/trades/confirm_purchase',
            '/api/confirm_purchase',
            '/api/purchase/confirm',
            '/api/transactions/confirm'
        ];
        
        let lastError = null;
        
        // 尝试多个URLs
        for (let i = 0; i < urls.length; i++) {
            const url = urls[i];
            
            try {
                log(`尝试确认API端点 ${i+1}/${urls.length}: ${url}`);
                
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                if (response.ok) {
                    const data = await response.json();
                    log('确认购买API调用成功', data);
                    return data;
                }
                
                const errorText = await response.text().catch(() => '');
                lastError = new Error(`确认端点 ${url} 返回错误代码: ${response.status} ${errorText}`);
                log(lastError.message);
            } catch (error) {
                lastError = error;
                log(`确认端点 ${url} 调用失败`, error);
            }
        }
        
        // 如果所有端点都失败，抛出最后一个错误
        throw lastError || new Error('所有确认API端点调用失败');
    }
    
    // 核心购买逻辑
    async function handleBuy(assetId, amountInput, buyButton, tokenPrice, walletInfo) {
        log('购买处理开始', { assetId, tokenPrice });
        
        // 禁用购买按钮，防止重复点击
        buyButton.disabled = true;
        buyButton.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${getText('processing')}`;
        
        try {
            // 获取购买数量
            const amount = amountInput.value ? parseInt(amountInput.value) : 0;
            if (!amount || amount <= 0) {
                throw new Error(getText('invalidAmount'));
            }
            
            // 检查钱包连接 - 使用提供的walletInfo或检查连接状态
            let walletConnection = walletInfo;
            if (!walletConnection || !walletConnection.address) {
                walletConnection = await checkWalletConnection();
            }
            
            // 如果钱包未连接，抛出错误
            if (!walletConnection.connected || !walletConnection.address) {
                throw new Error(getText('walletNotConnected'));
            }
            
            // 1. 调用准备购买API
            log('开始准备购买', { assetId, amount, walletAddress: walletConnection.address });
            const prepareResponse = await preparePurchase(assetId, amount, walletConnection.address);
            
            if (!prepareResponse.success) {
                throw new Error(prepareResponse.error || getText('prepareFailed'));
            }
            
            // 保存交易ID
            const tradeId = prepareResponse.trade_id;
            log('获取到交易ID', tradeId);
            
            // 获取交易总价
            const totalAmount = prepareResponse.total || (amount * tokenPrice);
            log('计算交易总价', totalAmount);
            
            // 2. 显示购买确认模态框
            const modalAssetName = document.getElementById('modalAssetName');
            const modalAmount = document.getElementById('modalAmount');
            const modalPricePerToken = document.getElementById('modalPricePerToken');
            const modalSubtotal = document.getElementById('modalSubtotal');
            const modalFee = document.getElementById('modalFee');
            const modalTotalCost = document.getElementById('modalTotalCost');
            const modalRecipientAddress = document.getElementById('modalRecipientAddress');
            
            // 计算费用
            const pricePerToken = tokenPrice;
            const subtotal = amount * pricePerToken;
            const platformFee = subtotal * CONFIG.platformFeeRate;
            const totalCost = subtotal;
            
            // 设置模态框内容
            if (modalAssetName) modalAssetName.textContent = prepareResponse.asset_name || assetId;
            if (modalAmount) modalAmount.textContent = amount;
            if (modalPricePerToken) modalPricePerToken.textContent = (prepareResponse.token_price || pricePerToken).toFixed(2);
            if (modalSubtotal) modalSubtotal.textContent = (prepareResponse.subtotal || subtotal).toFixed(2);
            if (modalFee) modalFee.textContent = (prepareResponse.platform_fee || platformFee).toFixed(2);
            if (modalTotalCost) modalTotalCost.textContent = (prepareResponse.total_amount || totalCost).toFixed(2);
            
            // 设置接收地址
            const platformAddress = prepareResponse.recipient_address || 
                                   document.querySelector('meta[name="platform-fee-address"]')?.content || 
                                   'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd';
            if (modalRecipientAddress) modalRecipientAddress.textContent = platformAddress;
            
            // 保存待处理交易信息到全局变量
            window.pendingPurchase = {
                trade_id: tradeId,
                asset_id: assetId,
                amount: amount,
                total_cost: (prepareResponse.total_amount || totalCost).toFixed(2),
                recipient_address: platformAddress,
                wallet_address: walletConnection.address
            };
            
            // 显示模态框
            const buyModal = document.getElementById('buyModal');
            if (buyModal) {
                const bsModal = new bootstrap.Modal(buyModal);
                bsModal.show();
            } else {
                log('找不到购买确认模态框，直接继续');
                await completePurchase(window.pendingPurchase);
            }
        } catch (error) {
            log('购买处理错误', error);
            
            // 显示错误信息
            const buyError = document.getElementById('buy-error');
            if (buyError) {
                buyError.textContent = error.message || getText('purchaseError');
                buyError.style.display = 'block';
            } else {
                showMessage(error.message || getText('purchaseError'), 'danger');
            }
        } finally {
            // 恢复购买按钮
            buyButton.disabled = false;
            buyButton.innerHTML = `<i class="fas fa-shopping-cart me-2"></i>${getText('buy') || '购买'}`;
        }
    }
    
    // 完成购买流程
    async function completePurchase(purchaseData) {
        log('完成购买流程', purchaseData);
        
        try {
            // 显示处理中状态
            const confirmBtn = document.getElementById('confirmPurchaseBtn');
            if (confirmBtn) {
                confirmBtn.disabled = true;
                confirmBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${getText('processing')}`;
            }
            
            // 如果没有交易ID，抛出错误
            if (!purchaseData || !purchaseData.trade_id) {
                throw new Error('交易ID不存在，无法完成购买');
            }
            
            // 确认购买
            const confirmResponse = await confirmPurchase(
                purchaseData.trade_id,
                purchaseData.wallet_address
            );
            
            if (!confirmResponse.success) {
                throw new Error(confirmResponse.error || '确认购买失败');
            }
            
            // 关闭模态框
            const buyModal = document.getElementById('buyModal');
            if (buyModal) {
                const bsModal = bootstrap.Modal.getInstance(buyModal);
                if (bsModal) bsModal.hide();
            }
            
            // 显示成功消息
            showMessage(getText('purchaseSuccess'), 'success');
            
            // 刷新资产信息
            if (typeof window.refreshAssetInfoNow === 'function') {
                setTimeout(() => {
                    window.refreshAssetInfoNow();
                }, 1000);
            }
            
            // 如果存在，刷新用户资产列表
            if (typeof window.refreshWalletAssets === 'function') {
                setTimeout(() => {
                    window.refreshWalletAssets();
                }, 2000);
            }
            
            // 清除待处理交易
            window.pendingPurchase = null;
            
            return true;
        } catch (error) {
            log('完成购买流程错误', error);
            
            // 显示错误信息
            const modalError = document.getElementById('buyModalError');
            if (modalError) {
                modalError.textContent = error.message || getText('purchaseError');
                modalError.style.display = 'block';
            } else {
                showMessage(error.message || getText('purchaseError'), 'danger');
            }
            
            return false;
        } finally {
            // 恢复确认按钮
            const confirmBtn = document.getElementById('confirmPurchaseBtn');
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = getText('confirm') || '确认购买';
            }
        }
    }
    
    // 导出全局函数
    window.handleBuy = handleBuy;
    window.confirmPurchase = completePurchase;
    
    // 查找并绑定购买按钮
    function bindBuyButtons() {
        const buyButtons = document.querySelectorAll('#buy-button, .buy-button, [data-action="buy"]');
        
        buyButtons.forEach(button => {
            // 避免重复绑定
            if (button._buyHandlerBound) return;
            button._buyHandlerBound = true;
            
            // 绑定点击事件
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                // 获取资产ID和金额输入
                const assetId = this.getAttribute('data-asset-id');
                const tokenPrice = parseFloat(this.getAttribute('data-token-price') || '0');
                const amountInput = document.getElementById('purchase-amount');
                
                if (!assetId || !amountInput) {
                    log('无法找到资产ID或金额输入');
                    return;
                }
                
                // 调用处理函数
                handleBuy(assetId, amountInput, this, tokenPrice);
            });
        });
    }
    
    // DOM加载完成后绑定按钮
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindBuyButtons);
    } else {
        bindBuyButtons();
    }
    
    // 绑定模态框确认按钮
    document.addEventListener('DOMContentLoaded', function() {
        const confirmBtn = document.getElementById('confirmPurchaseBtn');
        if (confirmBtn) {
            // 移除所有现有事件监听器
            const newBtn = confirmBtn.cloneNode(true);
            confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);
            
            // 添加事件监听器
            newBtn.addEventListener('click', function() {
                completePurchase(window.pendingPurchase);
            });
        }
    });
})(); 