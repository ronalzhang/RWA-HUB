// 安全的翻译函数
function safeTranslate(text) {
    if (typeof window._ === 'function') {
        return window._(text);
    }
    return text;
}

// 配置常量
const CONFIG = {
    IMAGE: {
        MAX_FILES: 10,
        MAX_SIZE: 5 * 1024 * 1024, // 5MB
        ALLOWED_TYPES: ['jpg', 'jpeg', 'png', 'gif', 'webp']
    },
    DOCUMENT: {
        MAX_FILES: 10,
        MAX_SIZE: 10 * 1024 * 1024, // 10MB
        ALLOWED_TYPES: ['pdf', 'doc', 'docx', 'txt']
    },
    DRAFT: {
        AUTO_SAVE_INTERVAL: 30000, // 30秒
        KEY: 'assetDraft'
    },
    ASSET_TYPE: {
        REAL_ESTATE: '10',
        SIMILAR_ASSETS: '20'
    },
    CALCULATION: {
        TOKENS_PER_SQUARE_METER: 10000,
        PRICE_DECIMALS: 6,
        VALUE_DECIMALS: 2
    },
    FEES: {
        BASE_FEE: 3.25, // 基础上链费用（USDC）
        PLATFORM_FEE_RATE: 0.025, // 平台佣金比例（2.5%）
        MIN_FEE: 10 // 最低收费（USDC）
    }
};

// 全局变量
let uploadedImages = [];
let uploadedDocuments = [];
let isAdminUser = false;
let isPageInitialized = false;

// 防止重复初始化的标志
window.assetFormInitialized = false;

// 主初始化函数
function initializeCreatePage() {
    console.log('初始化资产创建页面...');
    
    // 检查是否已初始化
    if (window.assetFormInitialized) {
        console.log('页面已初始化，跳过');
        return;
    }
        
    // 设置初始化标志
    window.assetFormInitialized = true;
        
    // 立即检查钱包连接状态，不延迟
    initializeWalletCheck();
    
    // 初始化表单元素
    initializeFormFields();
    
    // 重置上传区域状态
    resetUploadAreas();
    
    // 加载草稿（异步执行，不阻塞页面）
    setTimeout(loadDraft, 100);
    
    // 设置自动保存（降低频率，减少性能影响）
    setInterval(saveDraft, CONFIG.DRAFT.AUTO_SAVE_INTERVAL);
    
    // 监听钱包状态变化事件
    document.addEventListener('walletStateChanged', function(event) {
        console.log('资产创建页面收到钱包状态变化事件:', event.detail);
        // 重新检查钱包状态并更新UI
        if (event.detail && typeof event.detail.connected !== 'undefined') {
            initializeWalletCheck();
        }
    });
        
    // 监听钱包初始化完成事件
    document.addEventListener('walletStateInitialized', function(event) {
        console.log('资产创建页面收到钱包初始化完成事件:', event.detail);
        // 重新检查钱包状态
        initializeWalletCheck();
    });
        
    console.log('初始化完成');
}

// 检查钱包连接状态
function initializeWalletCheck() {
    console.log('执行钱包连接状态检查...');
    const walletCheck = document.getElementById('walletCheck');
    const formContent = document.getElementById('formContent');
        
    if (!walletCheck || !formContent) {
        console.error('找不到钱包检查或表单内容元素');
        return;
    }
    
    const sessionWalletAddress = sessionStorage.getItem('walletAddress');
    const localWalletAddress = localStorage.getItem('walletAddress');
    const walletStateConnected = window.walletState && window.walletState.connected && window.walletState.address;
    
    if (sessionWalletAddress || localWalletAddress || walletStateConnected) {
        const address = sessionWalletAddress || localWalletAddress || window.walletState.address;
        console.log('找到钱包地址:', address);
        walletCheck.style.display = 'none';
        formContent.style.display = 'block';
        setTimeout(() => checkAdmin(address), 100);
    } else {
        console.log('未找到已连接的钱包地址，显示连接提示');
        walletCheck.style.display = 'block';
        formContent.style.display = 'none';
    }
}

// 检查管理员状态
function checkAdmin(address) {
    if (!address || window.checkingAdmin) return;
    window.checkingAdmin = true;
    fetch('/api/admin/check', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Eth-Address': address
        },
        body: JSON.stringify({ address: address })
    })
    .then(response => response.ok ? response.json() : Promise.reject(`HTTP error ${response.status}`))
    .then(data => {
        isAdminUser = data.is_admin === true;
        updateUiForAdminStatus(isAdminUser);
    })
    .catch(error => {
        console.error('检查管理员状态出错:', error);
        isAdminUser = false;
        updateUiForAdminStatus(false);
    })
    .finally(() => { window.checkingAdmin = false; });
}

// ... (The rest of the file content remains largely the same until the changed functions)

// This is a placeholder for all the intermediate functions that are not changed

// REFACTORED AND FIXED FUNCTIONS START HERE

/**
 * 部署资产智能合约
 */
async function deployAssetContract(createResult) {
    try {
        console.log('开始部署智能合约:', createResult);
        
        if (!createResult || !createResult.id) {
            throw new Error('无效的资产创建结果，缺少ID');
        }
        
        const walletAddress = window.walletState.getAddress();
        if (!walletAddress) {
            throw new Error('无法获取钱包地址');
        }
        
        const deploymentData = {
            asset_id: createResult.id,
            wallet_address: walletAddress
        };
        
        console.log('请求智能合约部署数据:', deploymentData);
        
        // Use the CORRECT endpoint
        const response = await fetch('/api/deploy-contract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': walletAddress
            },
            body: JSON.stringify(deploymentData)
        });
        
        const deployData = await response.json();
        
        if (!response.ok || !deployData.success) {
            const errorMsg = deployData.error || '准备智能合约部署失败';
            console.error('部署API错误:', errorMsg);
            throw new Error(errorMsg);
        }
        
        console.log('智能合约部署成功，等待后续处理。');
        return { success: true, ...deployData };
        
    } catch (error) {
        console.error('智能合约部署失败:', error);
        throw error;
    }
}


// 处理支付成功的情况
async function handlePaymentSuccess(txHash, formData) {
    try {
        showLoadingOverlay('支付成功，正在创建资产记录...');
        updateStepStatus('step-3', 'loading');
        updateMainProgress(60);
        
        const result = await processAssetCreation(formData, txHash);
        
        if (result.success) {
            updateStepStatus('step-3', 'completed');
            updateStepStatus('step-4', 'loading');
            updateMainProgress(75);

            const shouldDeploy = await showDeploymentConfirmDialog();
            if (shouldDeploy) {
                showLoadingOverlay('正在部署智能合约...');
                await deployAssetContract(result);
                updateStepStatus('step-4', 'completed');
                updateStepStatus('step-5', 'completed');
                updateMainProgress(100);
                showSuccessMessage('操作成功', '资产已创建并成功部署智能合约！');
            } else {
                showSuccessMessage('创建成功', '资产创建请求已提交，您可以稍后在资产详情页手动部署合约。');
            }

            // 清理表单和草稿
            const form = document.getElementById('assetForm');
            if(form) form.reset();
            uploadedImages = [];
            uploadedDocuments = [];
            renderImages();
            renderDocuments();
            localStorage.removeItem(CONFIG.DRAFT.KEY);

            // 启动状态轮询，让用户了解后台进度
            _pollTransactionStatus(result.asset_id);

        } else {
            throw new Error(result.error || '创建资产失败');
        }
    } catch (error) {
        console.error('处理支付成功后发生错误:', error);
        showError(`资产创建过程出错: ${error.message || '未知错误'}`);
    } finally {
        hideLoadingOverlay();
        hideProgressModal();
        enablePublishButtons();
    }
}

// 轮询检查资产状态
async function _pollTransactionStatus(assetId, maxRetries = 12, retryInterval = 5000) {
    let retryCount = 0;
    console.log(`开始轮询资产 #${assetId} 的状态...`);

    const checkStatus = async () => {
        try {
            const response = await fetch(`/api/assets/${assetId}/status`);
            if (!response.ok) {
                // 如果API返回错误（如500），则在几次重试后停止
                if(retryCount >= 2) {
                    console.error('API状态检查失败，停止轮询。');
                    return;
                }
                throw new Error('检查资产状态API失败');
            }

            const result = await response.json();
            console.log('资产状态轮询结果:', result);

            if (result.success && result.asset.is_deployed) {
                console.log('资产已成功上链!');
                showSuccessMessage('部署成功', `资产 ${result.asset.name} 已成功上链！`);
                return; // 成功，停止轮询
            }

            retryCount++;
            if (retryCount < maxRetries) {
                setTimeout(checkStatus, retryInterval);
            } else {
                console.log('轮询超时，资产仍在后台处理中。');
                showWarning('资产正在后台处理中，请稍后刷新页面查看最终状态。');
            }
        } catch (error) {
            console.error('检查资产状态出错:', error);
            retryCount++;
            if (retryCount < maxRetries) {
                setTimeout(checkStatus, retryInterval);
            }
        }
    };

    setTimeout(checkStatus, retryInterval); // 首次检查前也等待一下
}

// ... (The rest of the file, including UI helper functions like showPaymentConfirmation, processPayment, etc.)
// In showPaymentConfirmation, I'll wrap the processPayment call with loading indicators.

// (Inside showPaymentConfirmation's event listener)
newConfirmBtn.addEventListener('click', async function() {
    disablePublishButtons(true);
    showLoadingOverlay('正在准备支付...');
    try {
        const connected = await checkAndConnectWallet();
        if (connected) {
            confirmModal.hide();
            showProgressModal();
            const paymentResult = await processPayment();
            if (paymentResult.success) {
                await handlePaymentSuccess(paymentResult.txHash, formData);
            } else {
                throw new Error(paymentResult.error || '支付处理失败');
            }
        } else {
            throw new Error('请先连接钱包以继续');
        }
    } catch (error) {
        console.error('支付或创建流程出错:', error);
        showError(error.message || '处理失败，请重试');
        hideProgressModal();
    } finally {
        hideLoadingOverlay();
        enablePublishButtons();
    }
});
