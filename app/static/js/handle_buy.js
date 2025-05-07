/**
 * 统一购买处理脚本
 * 支持多语言界面
 * 版本：1.0.1 - 增强钱包检测与错误处理
 */

(function() {
    console.log('加载购买处理脚本 v1.0.1');
    
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
            insufficientFunds: '余额不足，无法完成购买'
        },
        'en': {
            processing: 'Processing purchase request...',
            walletNotConnected: 'Please connect your wallet first',
            missingAmountInput: 'Purchase amount input not found',
            invalidAmount: 'Please enter a valid purchase amount',
            serverError: 'Server error',
            prepareFailed: 'Failed to prepare purchase',
            purchaseError: 'Error processing purchase',
            insufficientFunds: 'Insufficient funds to complete purchase'
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
    
    /**
     * 检查钱包连接状态 - 增强版
     * 返回对象 {isConnected, address, type}
     */
    function checkWalletStatus() {
        let walletConnected = false;
        let walletAddress = '';
        let walletType = '';
        
        // 检查window.walletState
        if (window.walletState) {
            if ((window.walletState.isConnected || window.walletState.connected) && window.walletState.address) {
                walletConnected = true;
                walletAddress = window.walletState.address;
                walletType = window.walletState.walletType || 'phantom';
            }
        }
        
        // 检查localStorage
        if (!walletConnected) {
            walletAddress = localStorage.getItem('walletAddress');
            walletType = localStorage.getItem('walletType') || 'phantom';
            if (walletAddress) {
                walletConnected = true;
            }
        }
        
        // 检查全局wallet对象
        if (!walletConnected && window.wallet && typeof window.wallet.getAddress === 'function') {
            try {
                walletAddress = window.wallet.getAddress();
                if (walletAddress) {
                    walletConnected = true;
                    walletType = window.wallet.getWalletType ? window.wallet.getWalletType() : 'phantom';
                }
            } catch (e) {
                console.debug('从wallet对象获取地址失败', e);
            }
        }
        
        return {
            isConnected: walletConnected,
            address: walletAddress,
            type: walletType
        };
    }
    
    /**
     * 显示连接钱包模态框
     */
    function showConnectWalletModal() {
        // 尝试使用适当的UI函数显示钱包选择器
        if (typeof window.openWalletSelector === 'function') {
            window.openWalletSelector();
            return true;
        }
        
        // 尝试使用全局wallet对象
        if (window.wallet && typeof window.wallet.showWalletOptions === 'function') {
            window.wallet.showWalletOptions();
            return true;
        }
        
        // 尝试打开已知的钱包模态框
        const walletModal = document.getElementById('walletModal');
        if (walletModal) {
            try {
                const bsModal = new bootstrap.Modal(walletModal);
                bsModal.show();
                return true;
            } catch (e) {
                console.debug('显示钱包模态框失败', e);
            }
        }
        
        return false;
    }
    
    /**
     * 统一的购买处理函数
     */
    async function handleBuy(assetIdOrEvent, amountInput, buyButton, tokenPrice) {
        console.log('全局购买处理函数被调用:', {assetIdOrEvent, amountInput: !!amountInput, buyButton: !!buyButton, tokenPrice});
        
        // 阻止事件默认行为（如果是事件对象）
        if (assetIdOrEvent && assetIdOrEvent.preventDefault) {
            assetIdOrEvent.preventDefault();
        }
        
        // 参数处理
        let assetId;
        
        // 如果第一个参数是事件对象
        if (assetIdOrEvent && assetIdOrEvent.type === 'click') {
            const targetElement = assetIdOrEvent.currentTarget || assetIdOrEvent.target;
            assetId = targetElement.getAttribute('data-asset-id');
            
            // 获取必要元素
            if (!amountInput) {
                amountInput = document.getElementById('purchase-amount') || 
                              document.querySelector('input[name="purchase-amount"]') ||
                              document.querySelector('.purchase-amount');
            }
            
            if (!buyButton) {
                buyButton = targetElement;
            }
            
            // 尝试获取代币价格
            if (!tokenPrice) {
                tokenPrice = parseFloat(targetElement.getAttribute('data-token-price') || document.querySelector('[data-token-price]')?.getAttribute('data-token-price') || '0');
            }
        } else {
            // 直接使用传入的参数
            assetId = assetIdOrEvent;
        }
        
        // 进一步尝试获取资产ID
        if (!assetId) {
            // 从URL获取
            const urlMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
            if (urlMatch && urlMatch[1]) {
                assetId = urlMatch[1];
            } else if (window.ASSET_CONFIG && window.ASSET_CONFIG.id) {
                assetId = window.ASSET_CONFIG.id;
            }
        }
        
        // 确保有资产ID
        if (!assetId) {
            console.error('无法确定资产ID');
            if (typeof window.showError === 'function') {
                window.showError('无法确定要购买的资产');
            } else {
                alert('无法确定要购买的资产');
            }
            return;
        }
        
        // 显示加载状态
        if (typeof window.showLoadingState === 'function') {
            window.showLoadingState(getText('processing'));
        }
        
        // 保存按钮原始状态
        const originalButtonText = buyButton ? buyButton.innerHTML : '';
        
        // 设置按钮为加载状态
        if (buyButton) {
            buyButton.disabled = true;
            buyButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ' + getText('processing');
        }
        
        try {
            // 检查钱包连接状态
            const walletStatus = checkWalletStatus();
            
            if (!walletStatus.isConnected) {
                console.warn('钱包未连接，尝试打开钱包选择器');
                
                // 重置按钮状态
                if (buyButton) {
                    buyButton.disabled = false;
                    buyButton.innerHTML = originalButtonText;
                }
                
                // 隐藏加载状态
                if (typeof window.hideLoadingState === 'function') {
                    window.hideLoadingState();
                }
                
                // 显示钱包连接对话框
                const modalShown = showConnectWalletModal();
                
                // 如果没有成功显示模态框，显示错误信息
                if (!modalShown) {
                    throw new Error(getText('walletNotConnected'));
                }
                
                return; // 终止购买流程
            }
            
            // 验证必要参数
            if (!amountInput) {
                // 尝试再次查找
                amountInput = document.getElementById('purchase-amount') || 
                              document.querySelector('input[name="purchase-amount"]') ||
                              document.querySelector('.purchase-amount');
                              
                if (!amountInput) {
                    throw new Error(getText('missingAmountInput'));
                }
            }
            
            // 获取购买数量
            const amount = amountInput.value;
            if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
                throw new Error(getText('invalidAmount'));
            }
            
            // 格式化为整数
            const cleanAmount = parseInt(amount);
            
            // 准备API请求数据
            const requestData = {
                asset_id: assetId,
                amount: cleanAmount,
                wallet_address: walletStatus.address,
                wallet_type: walletStatus.type
            };
            
            console.log('发送购买准备请求:', requestData);
            
            // 调用API
            const response = await fetch('/api/trades/prepare_purchase', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-Eth-Address': walletStatus.address,
                    'X-Wallet-Address': walletStatus.address
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                let errorMessage = getText('serverError');
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    // 忽略JSON解析错误
                }
                throw new Error(errorMessage);
            }
            
            // 解析API响应
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || getText('prepareFailed'));
            }
            
            console.log('购买准备成功:', data);
            
            // 查找或创建确认购买模态框
            let buyModal = document.getElementById('buyModal');
            let modalCreated = false;
            
            if (!buyModal) {
                // 创建一个简单的模态框
                modalCreated = true;
                buyModal = document.createElement('div');
                buyModal.id = 'buyModal';
                buyModal.className = 'modal fade';
                buyModal.setAttribute('tabindex', '-1');
                buyModal.setAttribute('role', 'dialog');
                buyModal.setAttribute('aria-hidden', 'true');
                
                buyModal.innerHTML = `
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">确认购买</h5>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <p>您将购买 <strong id="modalAmount"></strong> 个 <strong id="modalAssetName"></strong> 代币。</p>
                            <div class="purchase-details">
                                <div class="row">
                                    <div class="col-6">单价:</div>
                                    <div class="col-6 text-right">$<span id="modalPricePerToken"></span></div>
                                </div>
                                <div class="row">
                                    <div class="col-6">小计:</div>
                                    <div class="col-6 text-right">$<span id="modalSubtotal"></span></div>
                                </div>
                                <div class="row">
                                    <div class="col-6">平台费:</div>
                                    <div class="col-6 text-right">$<span id="modalFee"></span></div>
                                </div>
                                <div class="row font-weight-bold">
                                    <div class="col-6">总计:</div>
                                    <div class="col-6 text-right">$<span id="modalTotalCost"></span></div>
                                </div>
                            </div>
                            <p class="mt-3">收款地址: <small id="modalRecipientAddress" class="text-monospace"></small></p>
                            <div data-trade-id="${data.trade_id}" id="trade-id-container"></div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" id="confirmPurchaseBtn">确认购买</button>
                        </div>
                    </div>
                </div>`;
                
                document.body.appendChild(buyModal);
                
                // 绑定确认按钮事件
                document.getElementById('confirmPurchaseBtn').addEventListener('click', function() {
                    if (typeof window.confirmPurchase === 'function') {
                        window.confirmPurchase(window.pendingPurchase, buyModal, this);
                    }
                });
            }
            
            // 初始化模态框
            let bsModal;
            try {
                bsModal = new bootstrap.Modal(buyModal);
            } catch (e) {
                console.warn('无法使用Bootstrap初始化模态框，尝试替代方案', e);
                
                // 简单的显示逻辑
                buyModal.style.display = 'block';
                buyModal.classList.add('show');
                
                // 关闭按钮逻辑
                const closeButtons = buyModal.querySelectorAll('[data-dismiss="modal"]');
                closeButtons.forEach(button => {
                    button.addEventListener('click', function() {
                        buyModal.style.display = 'none';
                        buyModal.classList.remove('show');
                    });
                });
            }
            
            // 填充确认对话框数据
            const modalAssetName = document.getElementById('modalAssetName');
            const modalAmount = document.getElementById('modalAmount');
            const modalPricePerToken = document.getElementById('modalPricePerToken');
            const modalSubtotal = document.getElementById('modalSubtotal');
            const modalFee = document.getElementById('modalFee');
            const modalTotalCost = document.getElementById('modalTotalCost');
            const modalRecipientAddress = document.getElementById('modalRecipientAddress');
            const tradeIdContainer = document.getElementById('trade-id-container');
            
            if (modalAssetName) modalAssetName.textContent = data.asset_name || document.querySelector('h1, h2').textContent;
            if (modalAmount) modalAmount.textContent = cleanAmount;
            if (modalPricePerToken) modalPricePerToken.textContent = data.token_price || tokenPrice;
            if (modalSubtotal) modalSubtotal.textContent = data.subtotal || (cleanAmount * tokenPrice).toFixed(2);
            if (modalFee) modalFee.textContent = data.platform_fee || '0.00';
            if (modalTotalCost) modalTotalCost.textContent = data.total_amount;
            if (modalRecipientAddress) modalRecipientAddress.textContent = data.recipient_address || data.seller_address;
            if (tradeIdContainer) tradeIdContainer.setAttribute('data-trade-id', data.trade_id);
            
            // 存储交易ID和其他必要数据，用于确认时调用
            window.pendingPurchase = {
                trade_id: data.trade_id,
                total: data.total_amount,
                amount: cleanAmount,
                total_cost: data.total_amount,
                seller: data.seller_address,
                recipient_address: data.seller_address || data.recipient_address,
                platform_fee_basis_points: data.platform_fee_basis_points || 200,
                contract_address: data.purchase_contract_address,
                asset_id: assetId,
                asset_name: data.asset_name,
                token_price: data.token_price || tokenPrice
            };
            
            // 显示确认对话框
            if (bsModal) {
                bsModal.show();
            } else {
                // 简单的显示逻辑（兜底）
                buyModal.style.display = 'block';
                buyModal.classList.add('show');
            }
            
        } catch (error) {
            console.error('购买处理出错:', error);
            
            // 显示错误信息
            if (typeof window.showError === 'function') {
                window.showError(error.message || getText('purchaseError'));
            } else {
                alert(error.message || getText('purchaseError'));
            }
        } finally {
            // 恢复按钮状态
            if (buyButton) {
                buyButton.disabled = false;
                buyButton.innerHTML = originalButtonText;
            }
            
            // 隐藏加载状态
            if (typeof window.hideLoadingState === 'function') {
                window.hideLoadingState();
            }
        }
    }
    
    // 添加帮助函数用于动态创建购买模态框
    function ensureBuyModalExists() {
        let buyModal = document.getElementById('buyModal');
        
        if (!buyModal) {
            buyModal = document.createElement('div');
            buyModal.id = 'buyModal';
            buyModal.className = 'modal fade';
            buyModal.setAttribute('tabindex', '-1');
            buyModal.setAttribute('role', 'dialog');
            buyModal.setAttribute('aria-hidden', 'true');
            
            // 添加基本的模态框结构
            buyModal.innerHTML = `
            <div class="modal-dialog" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">确认购买</h5>
                        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <p>您将购买 <strong id="modalAmount"></strong> 个 <strong id="modalAssetName"></strong> 代币。</p>
                        <div class="purchase-details">
                            <div class="row">
                                <div class="col-6">单价:</div>
                                <div class="col-6 text-right">$<span id="modalPricePerToken"></span></div>
                            </div>
                            <div class="row">
                                <div class="col-6">小计:</div>
                                <div class="col-6 text-right">$<span id="modalSubtotal"></span></div>
                            </div>
                            <div class="row">
                                <div class="col-6">平台费:</div>
                                <div class="col-6 text-right">$<span id="modalFee"></span></div>
                            </div>
                            <div class="row font-weight-bold">
                                <div class="col-6">总计:</div>
                                <div class="col-6 text-right">$<span id="modalTotalCost"></span></div>
                            </div>
                        </div>
                        <p class="mt-3">收款地址: <small id="modalRecipientAddress" class="text-monospace"></small></p>
                        <div id="trade-id-container"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" id="confirmPurchaseBtn">确认购买</button>
                    </div>
                </div>
            </div>`;
            
            document.body.appendChild(buyModal);
            
            // 绑定确认按钮事件
            document.getElementById('confirmPurchaseBtn').addEventListener('click', function() {
                if (typeof window.confirmPurchase === 'function') {
                    window.confirmPurchase(window.pendingPurchase, buyModal, this);
                }
            });
        }
        
        return buyModal;
    }
    
    // 导出全局函数
    window.handleBuy = handleBuy;
    window.ensureBuyModalExists = ensureBuyModalExists;
    
    // 在DOM加载完毕后初始化
    document.addEventListener('DOMContentLoaded', function() {
        // 确保买入模态框存在
        ensureBuyModalExists();
        
        // 在资产详情页自动绑定购买按钮
        if (window.location.pathname.includes('/assets/')) {
            const buyButtons = document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"]');
            
            buyButtons.forEach(button => {
                if (!button.hasAttribute('data-buy-handler-bound')) {
                    button.setAttribute('data-buy-handler-bound', 'true');
                    button.addEventListener('click', handleBuy);
                    console.log('已绑定购买按钮:', button);
                }
            });
        }
    });
    
    // 监听语言变化事件
    window.addEventListener('languageChanged', () => {
        console.log('语言已变更，更新购买处理UI');
    });
    
    // 触发加载完成事件
    document.dispatchEvent(new Event('buyHandlerLoaded'));
})(); 