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
// 检查钱包连接状态
function initializeWalletCheck() {
    console.log('执行钱包连接状态检查...');
        const walletCheck = document.getElementById('walletCheck');
        const formContent = document.getElementById('formContent');
        
    if (!walletCheck || !formContent) {
        console.error('找不到钱包检查或表单内容元素');
        return;
    }
    
    // 先检查sessionStorage中是否有钱包信息（可能比walletState更可靠）
    const sessionWalletAddress = sessionStorage.getItem('walletAddress');
    const sessionWalletType = sessionStorage.getItem('walletType');
    
    // 然后检查localStorage中是否有钱包信息
    const localWalletAddress = localStorage.getItem('walletAddress');
    const localWalletType = localStorage.getItem('walletType');
    
    // 最后检查window.walletState
    const walletStateConnected = window.walletState && window.walletState.connected && window.walletState.address;
    
    // 优先级：sessionStorage > localStorage > walletState
    if (sessionWalletAddress && sessionWalletType) {
        console.log('从sessionStorage找到钱包地址:', sessionWalletAddress);
                walletCheck.style.display = 'none';
                formContent.style.display = 'block';
        
        // 检查管理员状态
        setTimeout(() => checkAdmin(sessionWalletAddress), 100);
        return;
            }
    
    if (localWalletAddress && localWalletType) {
        console.log('从localStorage找到钱包地址:', localWalletAddress);
        walletCheck.style.display = 'none';
        formContent.style.display = 'block';
        
        // 检查管理员状态
        setTimeout(() => checkAdmin(localWalletAddress), 100);
        return;
    }
    
    if (walletStateConnected) {
        console.log('从walletState找到钱包地址:', window.walletState.address);
        walletCheck.style.display = 'none';
        formContent.style.display = 'block';
        
        // 检查管理员状态
        setTimeout(() => checkAdmin(window.walletState.address), 100);
        return;
    }
    
    // 如果上述三种方式都没有找到钱包地址，则显示钱包检查
    console.log('未找到已连接的钱包地址，显示连接提示');
    walletCheck.style.display = 'block';
    formContent.style.display = 'none';
    }

    // 检查管理员状态
function checkAdmin(address) {
    if (!address || window.checkingAdmin) return;
        
    window.checkingAdmin = true;
        
    console.log('检查管理员状态:', address);
        fetch('/api/admin/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Eth-Address': address
            },
            body: JSON.stringify({ wallet_address: address })
        })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
        .then(data => {
        isAdminUser = data.is_admin === true;
        console.log('管理员状态:', isAdminUser);
        updateUiForAdminStatus(isAdminUser);
        })
        .catch(error => {
        console.error('检查管理员状态出错:', error);
        // 如果API调用失败，默认为非管理员
        isAdminUser = false;
        updateUiForAdminStatus(false);
    })
    .finally(() => {
        window.checkingAdmin = false;
        });
    }

// 更新UI显示管理员状态
function updateUiForAdminStatus(isAdmin) {
        const platformFeeNote = document.getElementById('platformFeeNote');
        if (platformFeeNote) {
            platformFeeNote.textContent = isAdmin ? 
                'Admin users only need to pay the basic transaction fee' : 
                'Regular users need to pay platform fee (2.5% of the asset value)';
        }
    }

    // 初始化表单字段
    function initializeFormFields() {
    // 资产类型选择
        const typeSelect = document.getElementById('type');
        if (typeSelect) {
        typeSelect.addEventListener('change', function() {
            const type = this.value;
            toggleAssetTypeFields(type);
            generateTokenSymbol(type)
                .then(symbol => {
                    const symbolInput = document.getElementById('tokensymbol');
                    if (symbolInput) symbolInput.value = symbol;
                    calculatePublishingFee();
                })
                .catch(error => {
                    console.error('生成代币符号出错:', error);
                });
        });
        }
        
    // 不动产面积
        const areaInput = document.getElementById('area');
        if (areaInput) {
            areaInput.addEventListener('input', handleAreaChange);
        }
        
        // 不动产总价值
        const totalValueInput = document.getElementById('total_value');
        if (totalValueInput) {
        totalValueInput.addEventListener('input', updateTokenPrice);
        }
        
    // 类不动产代币数量
        const tokenSupplyInput = document.getElementById('token_supply');
        if (tokenSupplyInput) {
        tokenSupplyInput.addEventListener('input', updateTokenPriceSimilar);
        }
        
    // 类不动产总价值
        const totalValueSimilarInput = document.getElementById('total_value_similar');
        if (totalValueSimilarInput) {
        totalValueSimilarInput.addEventListener('input', updateTokenPriceSimilar);
        }
        
    // 预览按钮
        const previewButton = document.getElementById('previewForm');
        if (previewButton) {
        previewButton.addEventListener('click', function() {
            if (validateForm()) {
                showAssetPreview();
            }
        });
        }
        
    // 支付并发布按钮
        const publishButton = document.getElementById('payAndPublish');
        if (publishButton) {
        publishButton.addEventListener('click', function() {
            if (validateForm()) {
                showPaymentConfirmation();
            }
        });
    }
    
    // 表单提交
    const form = document.getElementById('assetForm');
    if (form) {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            validateAndSubmitForm();
        });
    }
    
    // 初始化计算
    calculatePublishingFee();
    
    // 初始化文件上传
    initializeFileUploads();
    
    // 初始化上传区域显示状态
    resetUploadAreas();
    
    // 初始化时禁用上传区域，直到选择资产类型
    toggleUploadAreas(false);
}

// 启用/禁用上传区域
function toggleUploadAreas(enabled) {
    const imageDropzone = document.getElementById('imageDropzone');
    const documentDropzone = document.getElementById('documentDropzone');
    const imageInput = document.getElementById('imageInput');
    const documentInput = document.getElementById('documentInput');
    
    if (imageDropzone) {
        const imageText = imageDropzone.querySelector('p');
        if (enabled) {
            imageDropzone.classList.remove('disabled');
            imageDropzone.style.opacity = '1';
            imageDropzone.style.pointerEvents = 'auto';
            if (imageText) {
                imageText.textContent = safeTranslate('Drag and drop images here or click to select');
            }
        } else {
            imageDropzone.classList.add('disabled');
            imageDropzone.style.opacity = '0.5';
            imageDropzone.style.pointerEvents = 'none';
            if (imageText) {
                imageText.textContent = safeTranslate('Please select asset type first');
            }
        }
    }
    
    if (documentDropzone) {
        const documentText = documentDropzone.querySelector('p');
        if (enabled) {
            documentDropzone.classList.remove('disabled');
            documentDropzone.style.opacity = '1';
            documentDropzone.style.pointerEvents = 'auto';
            if (documentText) {
                documentText.textContent = safeTranslate('Drag and drop documents here or click to select');
            }
        } else {
            documentDropzone.classList.add('disabled');
            documentDropzone.style.opacity = '0.5';
            documentDropzone.style.pointerEvents = 'none';
            if (documentText) {
                documentText.textContent = safeTranslate('Please select asset type first');
            }
        }
    }
    
    if (imageInput) {
        imageInput.disabled = !enabled;
    }
    
    if (documentInput) {
        documentInput.disabled = !enabled;
    }
}

// 重置上传区域状态
function resetUploadAreas() {
    // 重置图片上传区域
    const imageUploadProgress = document.getElementById('imageUploadProgress');
    const imageUploadStatus = document.getElementById('imageUploadStatus');
    const imageUploadPercent = document.getElementById('imageUploadPercent');
    
    if (imageUploadProgress) {
        imageUploadProgress.style.display = 'none';
    }
    
    if (imageUploadStatus) {
        imageUploadStatus.textContent = '';
    }
    
    if (imageUploadPercent) {
        imageUploadPercent.textContent = '0';
    }
    
    // 重置文档上传区域
    const documentUploadProgress = document.getElementById('documentUploadProgress');
    const documentUploadStatus = document.getElementById('documentUploadStatus');
    const documentUploadPercent = document.getElementById('documentUploadPercent');
    
    if (documentUploadProgress) {
        documentUploadProgress.style.display = 'none';
    }
    
    if (documentUploadStatus) {
        documentUploadStatus.textContent = '';
    }
    
    if (documentUploadPercent) {
        documentUploadPercent.textContent = '0';
    }
    
    // 初始化渲染空的图片和文档区域
    renderImages();
    renderDocuments();
}

// 初始化文件上传
function initializeFileUploads() {
    // 图片上传
    const imageDropzone = document.getElementById('imageDropzone');
    const imageInput = document.getElementById('imageInput');
    
    if (imageDropzone && imageInput) {
        imageDropzone.addEventListener('click', () => imageInput.click());
        
        imageInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
            handleFiles(e.target.files, 'IMAGE');
            }
        });

        // 拖放功能
        imageDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            imageDropzone.classList.add('border-primary');
        });

        imageDropzone.addEventListener('dragleave', () => {
            imageDropzone.classList.remove('border-primary');
        });

        imageDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            imageDropzone.classList.remove('border-primary');
            if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files, 'IMAGE');
            }
        });
    }

    // 文档上传
    const documentDropzone = document.getElementById('documentDropzone');
        const documentInput = document.getElementById('documentInput');
    
    if (documentDropzone && documentInput) {
        documentDropzone.addEventListener('click', () => documentInput.click());
        
        documentInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
            handleFiles(e.target.files, 'DOCUMENT');
            }
        });

        // 拖放功能
        documentDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            documentDropzone.classList.add('border-primary');
        });

        documentDropzone.addEventListener('dragleave', () => {
            documentDropzone.classList.remove('border-primary');
        });

        documentDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            documentDropzone.classList.remove('border-primary');
            if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files, 'DOCUMENT');
            }
        });
    }
    }

// 处理资产类型切换
    function toggleAssetTypeFields(type) {
        const realEstateFields = document.querySelectorAll('.asset-type-field.real-estate');
        const similarAssetsFields = document.querySelectorAll('.asset-type-field.similar-assets');
        
        if (type === '10') { // 不动产
            realEstateFields.forEach(el => el.style.display = 'block');
            similarAssetsFields.forEach(el => el.style.display = 'none');
        } else if (type === '20') { // 类不动产
            realEstateFields.forEach(el => el.style.display = 'none');
            similarAssetsFields.forEach(el => el.style.display = 'block');
        }
        
        // 启用/禁用文件上传区域
        toggleUploadAreas(!!type);
    }

    // 处理面积变化
    function handleAreaChange() {
        const areaValue = parseFloat(document.getElementById('area').value) || 0;
        const tokenCountElement = document.getElementById('token_count');
        
        if (areaValue > 0 && tokenCountElement) {
        // 计算代币数量
            const tokenCount = Math.floor(areaValue * CONFIG.CALCULATION.TOKENS_PER_SQUARE_METER);
            tokenCountElement.textContent = tokenCount.toLocaleString();
        
        // 更新代币价格
        updateTokenPrice();
        } else if (tokenCountElement) {
            tokenCountElement.textContent = '0';
        
            const tokenPriceElement = document.getElementById('token_price');
            if (tokenPriceElement) {
                tokenPriceElement.textContent = '0.000000';
            }
        }
    }

// 更新不动产代币价格
function updateTokenPrice() {
    const area = parseFloat(document.getElementById('area').value) || 0;
    const totalValue = parseFloat(document.getElementById('total_value').value) || 0;
            const tokenCountElement = document.getElementById('token_count');
            const tokenPriceElement = document.getElementById('token_price');
            
    if (!tokenCountElement || !tokenPriceElement) return;
    
    const tokenCountText = tokenCountElement.textContent.replace(/,/g, '');
    const tokenCount = parseInt(tokenCountText) || 0;
    
                if (tokenCount > 0 && totalValue > 0) {
                    const tokenPrice = totalValue / tokenCount;
                    tokenPriceElement.textContent = tokenPrice.toFixed(CONFIG.CALCULATION.PRICE_DECIMALS);
                } else {
                    tokenPriceElement.textContent = '0.000000';
                }
    
    // 计算发布费用
    calculatePublishingFee();
            }

// 更新类不动产代币价格
function updateTokenPriceSimilar() {
            const tokenSupply = parseInt(document.getElementById('token_supply').value) || 0;
            const totalValue = parseFloat(document.getElementById('total_value_similar').value) || 0;
            const tokenPriceElement = document.getElementById('calculatedTokenPriceSimilar');
            
    if (!tokenPriceElement) return;
    
                if (tokenSupply > 0 && totalValue > 0) {
                    const tokenPrice = totalValue / tokenSupply;
                    tokenPriceElement.textContent = tokenPrice.toFixed(CONFIG.CALCULATION.PRICE_DECIMALS);
                } else {
                    tokenPriceElement.textContent = '0.000000';
        }
        
    // 计算发布费用
        calculatePublishingFee();
    }

    // 计算发布费用
    function calculatePublishingFee() {
    const typeSelect = document.getElementById('type');
        const publishingFeeElement = document.getElementById('publishingFee');
    
    if (!typeSelect || !publishingFeeElement) return;
    
    const assetType = typeSelect.value;
    let totalValue = 0;
    
    if (assetType === '10') { // 不动产
        totalValue = parseFloat(document.getElementById('total_value').value) || 0;
    } else { // 类不动产
        totalValue = parseFloat(document.getElementById('total_value_similar').value) || 0;
    }
    
    // 计算发布费用 - 从API动态获取
    (async () => {
        let fee = 0.01; // 默认费用，如果API获取失败则使用此值
        
        try {
            // 从API获取最新的支付配置
            const configResponse = await fetch('/api/service/config/payment_settings');
            if (configResponse.ok) {
                const configData = await configResponse.json();
                fee = parseFloat(configData.creation_fee?.amount) || fee;
                console.log('从API获取发布费用:', fee, 'USDC');
            }
        } catch (configError) {
            console.warn('获取发布费用配置失败，使用默认值:', configError);
        }
        
        publishingFeeElement.textContent = `${fee.toFixed(2)} USDC`;
    })();
    }

    // 生成代币符号
    async function generateTokenSymbol(type) {
        try {
            console.log(`开始生成代币符号，资产类型: ${type}`);
            
            // 请求服务器生成代币符号
            const response = await fetch('/api/assets/generate-token-symbol', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ type: type || '10' })  // 提供默认值
            });
            
            console.log(`代币符号生成响应状态: ${response.status}`);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`生成token_symbol请求失败: ${response.status}, 响应: ${errorText}`);
                throw new Error(`服务器响应错误: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('代币符号生成响应数据:', data);
            
            // 检查success字段
            if (!data.success) {
                console.error('生成token_symbol失败:', data.error || '未知错误');
                throw new Error(data.error || '生成代币符号失败');
            }
            
            // 如果服务器返回了token_symbol，返回它
            if (data.token_symbol) {
                console.log(`生成代币符号: ${data.token_symbol}`);
                return data.token_symbol;
            } else {
                console.error('服务器未返回token_symbol');
                throw new Error('服务器未返回有效的代币符号');
            }
        } catch (error) {
            console.error('生成代币符号出错:', error);
            
            // 本地生成作为备用方案
            console.log('尝试本地生成代币符号');
            try {
                // 生成4位随机数字，使用资产类型前缀
                const randomDigits = Math.floor(1000 + Math.random() * 9000);
                
                // 构建代币符号 - 使用资产类型 + 4位数字格式
                const assetTypePrefix = type || '20'; // 默认使用20
                const symbol = `RH-${assetTypePrefix}${randomDigits}`;
                
                console.log(`本地生成代币符号: ${symbol}`);
                return symbol;
            } catch (localError) {
                console.error('本地生成代币符号失败:', localError);
                // 返回一个基于时间戳的符号作为最后的备用方案
                const timestamp = Date.now().toString().slice(-4); // 使用4位时间戳
                const assetTypePrefix = type || '20';
                return `RH-${assetTypePrefix}${timestamp}`;
            }
        }
    }

// 处理文件上传
async function handleFiles(files, fileType) {
    console.log(`开始处理${fileType}上传，文件数量:`, files.length);
    if (!files || files.length === 0) return;
    
    // 检查是否已选择资产类型
    const assetTypeSelect = document.getElementById('type');
    const assetType = assetTypeSelect ? assetTypeSelect.value : '';
    if (!assetType) {
        alert('请先选择资产类型再上传文件');
        return;
    }
    
    // 确定文件类型参数
    const isImage = fileType === 'IMAGE';
    const maxFiles = isImage ? CONFIG.IMAGE.MAX_FILES : CONFIG.DOCUMENT.MAX_FILES;
    const allowedTypes = isImage ? CONFIG.IMAGE.ALLOWED_TYPES : CONFIG.DOCUMENT.ALLOWED_TYPES;
    
    // 检查已上传文件数量
    const currentFiles = isImage ? uploadedImages.length : uploadedDocuments.length;
    if (currentFiles + files.length > maxFiles) {
        alert(`最多只能上传${maxFiles}个${isImage ? '图片' : '文档'}`);
        return;
    }

    // 使用进度条和上传状态元素
    const progressId = isImage ? 'imageUploadProgress' : 'documentUploadProgress';
    const statusId = isImage ? 'imageUploadStatus' : 'documentUploadStatus';
    const percentId = isImage ? 'imageUploadPercent' : 'documentUploadPercent';
    
    const progressContainer = document.getElementById(progressId);
    const statusElement = document.getElementById(statusId);
    const percentElement = document.getElementById(percentId);
    
    if (!progressContainer || !statusElement || !percentElement) {
        console.error(`找不到上传状态元素: #${progressId}, #${statusId}, #${percentId}`);
        alert(`上传失败: 找不到上传状态元素`);
        return;
    }
    
    const progressBar = progressContainer.querySelector('.progress-bar');
    if (!progressBar) {
        console.error('找不到进度条元素');
        alert('上传失败: 找不到进度条元素');
            return;
        }
        
    // 显示进度条区域并重置状态
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    percentElement.textContent = '0';
    statusElement.textContent = '准备上传文件...';
    
    // 处理文件上传
        let completed = 0;
        let failed = 0;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
        // 验证文件类型
        const fileExt = file.name.split('.').pop().toLowerCase();
        console.log(`检查文件 ${file.name}, 扩展名: ${fileExt}`);
        
        if (!allowedTypes.includes(fileExt)) {
            statusElement.textContent = `文件格式不支持: ${file.name}`;
            console.error(`不支持的文件类型: ${fileExt}，允许的类型:`, allowedTypes);
                    failed++;
            continue;
        }
        
        // 检查文件大小
        const maxSize = isImage ? CONFIG.IMAGE.MAX_SIZE : CONFIG.DOCUMENT.MAX_SIZE;
        if (file.size > maxSize) {
            statusElement.textContent = `文件过大: ${file.name} (${(file.size/1024/1024).toFixed(2)}MB > ${maxSize/1024/1024}MB)`;
            console.error(`文件过大: ${file.name}, 大小: ${(file.size/1024/1024).toFixed(2)}MB`);
                failed++;
            continue;
        }
        
        // 创建FormData
        const formData = new FormData();
        formData.append('file', file);
        formData.append('fileType', fileType);
        
        // 获取当前选择的资产类型
        const assetTypeSelect = document.getElementById('type');
        const assetType = assetTypeSelect ? assetTypeSelect.value : '';
        
        // 检查是否已选择资产类型
        if (!assetType) {
            statusElement.textContent = '请先选择资产类型再上传文件';
            console.error('未选择资产类型，无法上传文件');
            failed++;
            continue;
        }
        
        formData.append('asset_type', assetType);
        
        // 获取代币符号
        const tokenSymbolInput = document.getElementById('tokensymbol');
        const tokenSymbol = tokenSymbolInput ? tokenSymbolInput.value : '';
        if (tokenSymbol) {
            formData.append('token_symbol', tokenSymbol);
            console.log(`使用代币符号: ${tokenSymbol}`);
        }
        
        // 尝试获取当前用户的钱包地址
        let address = null;
        if (window.walletState && window.walletState.address) {
            address = window.walletState.address;
            formData.append('address', address);
            console.log(`使用地址: ${address}`);
        } else {
            console.warn('未找到用户地址');
            statusElement.textContent = '未找到用户地址，尝试使用默认地址上传';
            formData.append('address', 'anonymous');
        }
        
        try {
            statusElement.textContent = `正在上传: ${file.name} (${i+1}/${files.length})`;
            
            // 发送上传请求 - 使用正确的API路径
            console.log(`发送上传请求到 /api/assets/upload-images，文件大小: ${(file.size/1024).toFixed(2)}KB`);
            
            // 添加防抖动计时器，避免服务器过载
            await new Promise(resolve => setTimeout(resolve, i * 300)); // 每个文件间隔300ms
        
        const response = await fetch('/api/assets/upload-images', {
            method: 'POST',
            headers: {
                    'X-Wallet-Address': address || 'anonymous'
            },
            body: formData
        });
        
            console.log(`收到响应，状态码: ${response.status}`);
            
            // 处理HTTP错误
        if (!response.ok) {
                let errorMessage = `上传失败: HTTP ${response.status}`;
                
                // 尝试解析错误消息
                try {
                    const errorJson = await response.json();
                    if (errorJson && (errorJson.message || errorJson.error)) {
                        errorMessage = errorJson.message || errorJson.error;
                    }
                } catch (e) {
                    // 无法解析JSON，使用默认错误消息
                    console.warn('无法解析错误响应JSON:', e);
                }
                
                // 常见错误的更友好提示
                if (response.status === 413) {
                    errorMessage = `文件 ${file.name} 过大，超出服务器限制`;
                } else if (response.status === 404) {
                    errorMessage = `上传接口不存在，请联系管理员`;
                } else if (response.status === 500) {
                    errorMessage = `服务器处理错误，请稍后重试`;
                }
                
                throw new Error(errorMessage);
    }

            // 解析成功响应
            const result = await response.json();
            console.log('上传响应:', result);
            
            // 处理成功响应
            if (result.success || (result.urls && result.urls.length > 0) || (result.image_paths && result.image_paths.length > 0)) {
                // 确定URL
                let url;
                if (result.urls && result.urls.length > 0) {
                    url = result.urls[0];
                } else if (result.image_paths && result.image_paths.length > 0) {
                    url = result.image_paths[0];
                } else if (result.url) {
                    url = result.url;
                }
                
                if (!url) {
                    throw new Error('服务器返回的URL为空');
    }

                // 添加到上传文件列表
                if (isImage) {
                    uploadedImages.push({
                        name: file.name,
                        url: url
                    });
                    renderImages();
                } else {
                    uploadedDocuments.push({
                        name: file.name,
                        url: url
                    });
                    renderDocuments();
                }
                completed++;
                statusElement.textContent = `成功上传 ${completed} 个文件`;
            } else {
                throw new Error(result.error || result.message || '上传失败，服务器未返回有效数据');
            }
        } catch (error) {
            console.error(`上传文件失败:`, error);
            statusElement.textContent = `上传失败: ${error.message}`;
            failed++;
    }

        // 更新进度条
        const progress = Math.round(((completed + failed) / files.length) * 100);
        percentElement.textContent = progress.toString();
        progressBar.style.width = `${progress}%`;
    }
    
    // 更新最终状态
    if (failed > 0) {
        statusElement.textContent = `上传完成，成功: ${completed}，失败: ${failed}`;
    } else if (completed > 0) {
        statusElement.textContent = `全部 ${completed} 个文件上传成功`;
    }

    // 保存草稿
    saveDraft();
    
    // 延迟隐藏进度条
    setTimeout(() => {
        progressContainer.style.display = 'none';
    }, 3000);
    }

    // 渲染图片
    function renderImages() {
        const container = document.getElementById('imagePreview');
        if (!container) return;
        
    if (uploadedImages.length === 0) {
        container.innerHTML = `<div class="text-center text-muted">${safeTranslate("No images uploaded")}</div>`;
            return;
        }
        
        let html = '<div class="row g-3">';
    uploadedImages.forEach((image, index) => {
            html += `
                <div class="col-md-4">
                    <div class="position-relative">
                    <img src="${image.url}" class="img-fluid rounded" alt="${safeTranslate("Asset Image")}">
                        <button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0 m-2" 
                                onclick="removeImage(${index})">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    // 渲染文档
    function renderDocuments() {
        const container = document.getElementById('documentPreview');
        if (!container) return;
        
    if (uploadedDocuments.length === 0) {
        container.innerHTML = `<div class="text-center text-muted">${safeTranslate("No documents uploaded")}</div>`;
            return;
        }
        
        let html = '<div class="document-list">';
    uploadedDocuments.forEach((doc, index) => {
            html += `
            <div class="document-item d-flex justify-content-between align-items-center">
                    <div>
                        <i class="fas fa-file-alt me-2"></i>
                        <span>${doc.name}</span>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-danger" 
                            onclick="removeDocument(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    }

// 删除图片
function removeImage(index) {
    if (index >= 0 && index < uploadedImages.length) {
        uploadedImages.splice(index, 1);
            renderImages();
            saveDraft();
        }
}

// 删除文档
function removeDocument(index) {
    if (index >= 0 && index < uploadedDocuments.length) {
        uploadedDocuments.splice(index, 1);
            renderDocuments();
            saveDraft();
        }
}

// 保存草稿
function saveDraft() {
    try {
        const form = document.getElementById('assetForm');
        if (!form) return;
        
    const formData = new FormData(form);
        const draft = {};
        
        for (const [key, value] of formData.entries()) {
            draft[key] = value;
        }
        
        draft.images = uploadedImages;
        draft.documents = uploadedDocuments;
        draft.timestamp = new Date().toISOString();
        
    localStorage.setItem(CONFIG.DRAFT.KEY, JSON.stringify(draft));
        console.log('草稿已保存');
    } catch (error) {
        console.error('保存草稿失败:', error);
    }
}

// 加载草稿
function loadDraft() {
    try {
        const draftJson = localStorage.getItem(CONFIG.DRAFT.KEY);
        if (!draftJson) return;
        
        const draft = JSON.parse(draftJson);
        const form = document.getElementById('assetForm');
        if (!form) return;
        
        // 加载表单数据
        for (const key in draft) {
            if (key === 'images' || key === 'documents' || key === 'timestamp') continue;
            
            const input = form.elements[key];
            if (input) input.value = draft[key];
    }

        // 加载图片和文档
        if (draft.images) {
            uploadedImages = draft.images;
            renderImages();
        }
        
        if (draft.documents) {
            uploadedDocuments = draft.documents;
            renderDocuments();
        }
        
        // 触发资产类型字段切换
        const typeSelect = document.getElementById('type');
        if (typeSelect && typeSelect.value) {
            toggleAssetTypeFields(typeSelect.value);
        }
        
        // 触发计算
        if (typeSelect && typeSelect.value === '10') {
            handleAreaChange();
        } else {
            updateTokenPriceSimilar();
            }
    } catch (error) {
        console.error('加载草稿失败:', error);
        localStorage.removeItem(CONFIG.DRAFT.KEY);
        }
    }

// 表单验证和提交
function validateAndSubmitForm() {
        const form = document.getElementById('assetForm');
    if (!form) return;
        
    // 基本字段验证
    const requiredFields = ['name', 'type', 'description', 'tokensymbol'];
        
    for (const field of requiredFields) {
        const input = form.elements[field];
        if (!input || !input.value.trim()) {
            showError(`Please fill in ${getFieldLabel(field)}`);
    return;
        }
    }
        
        // 根据资产类型验证特定字段
        const assetType = form.elements['type'].value;
        
        if (assetType === '10') { // 不动产
        const specificFields = ['area', 'total_value'];
        for (const field of specificFields) {
            const input = form.elements[field];
            if (!input || !parseFloat(input.value)) {
            showError(`Please fill in ${getFieldLabel(field)}`);
                return;
            }
            }
        } else if (assetType === '20') { // 类不动产
        // 检查token_supply字段
        const tokenSupplyInput = form.elements['token_supply'];
        if (!tokenSupplyInput || !parseInt(tokenSupplyInput.value)) {
            showError(`Please fill in ${getFieldLabel('token_supply')}`);
            return;
        }
        
        // 检查total_value_similar字段（使用ID而不是name属性）
        const totalValueInput = form.elements['total_value_similar'];
        if (!totalValueInput || !parseFloat(totalValueInput.value)) {
            showError(`Please fill in ${getFieldLabel('total_value')}`);
            return;
            }
        }
        
    // TODO: 提交表单逻辑
    console.log('表单验证通过，准备提交');
    alert('表单验证通过，功能待实现');
    }

    // 获取字段标签
    function getFieldLabel(field) {
        const labels = {
        'name': 'Asset Name',
        'type': 'Asset Type',
        'description': 'Asset Description',
        'tokensymbol': 'Token Symbol',
        'area': 'Asset Area',
        'total_value': 'Total Value',
        'total_value_similar': 'Total Value',
        'token_supply': 'Token Supply'
        };
        
        return labels[field] || field;
    }

// 辅助函数：从cookie获取值
function getCookieValue(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
    }

// 检查并连接钱包
async function checkAndConnectWallet() {
    return new Promise(async (resolve, reject) => {
        try {
            // 检查是否已有全局钱包状态
            if (window.walletState && window.walletState.connected && window.walletState.address) {
                console.log('钱包已连接:', window.walletState.address);
                resolve(true);
                return;
            }
            
            // 尝试使用全局钱包选择器连接
            console.log('尝试连接钱包...');
            showLoadingState('正在连接钱包...');
            updateProgress(10, '正在连接钱包...', 1);
            
            // 使用全局钱包选择器
            if (typeof window.walletState === 'object' && typeof window.walletState.openWalletSelector === 'function') {
                console.log('使用全局钱包选择器连接');
                const connected = await window.walletState.openWalletSelector();
                hideLoadingState();
                
                if (connected) {
                    console.log('成功连接钱包');
                    resolve(true);
                    return;
                } else {
                    console.warn('钱包连接失败或被用户取消');
                }
            }
            
            // 没有可用的钱包
            hideLoadingState();
            console.error('没有找到可用的钱包或连接方法失败');
            showError('请安装并解锁兼容的钱包');
            resolve(false);
            
        } catch (error) {
            hideLoadingState();
            console.error('钱包连接检查出错:', error);
            reject(error);
        }
    });
    }

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM内容加载完成，准备初始化资产创建页面...');
    
    // 确保所有DOM元素都存在
    const requiredElements = [
        'imageDropzone', 'documentDropzone', 
        'imageUploadProgress', 'documentUploadProgress',
        'imageUploadStatus', 'documentUploadStatus',
        'imagePreview', 'documentPreview'
    ];
    
    let missingElements = [];
    for (const id of requiredElements) {
        if (!document.getElementById(id)) {
            missingElements.push(id);
        }
    }
    
    if (missingElements.length > 0) {
        console.warn(`以下元素缺失，可能在其他页面或DOM尚未完全加载: ${missingElements.join(', ')}`);
    }
    
    // 判断当前是否在创建资产页面
    const isCreateAssetPage = document.getElementById('assetForm') !== null;
    if (!isCreateAssetPage) {
        console.log('不在创建资产页面，跳过初始化');
        return;
    }
    
    // 在setTimeout中执行初始化，让DOM和其他脚本有时间完全加载
    setTimeout(initializeCreatePage, 100);
    
    // 添加500ms后的再次检查，以防DOM内容加载后又发生变化
    setTimeout(function() {
        if (!window.assetFormInitialized) {
            console.log('页面可能尚未初始化，再次尝试');
            initializeCreatePage();
        }
        
        // 无论如何，再次重置上传区域状态
        if (typeof resetUploadAreas === 'function') {
            resetUploadAreas();
        }
    }, 500);
});

// 验证表单
function validateForm() {
    const form = document.getElementById('assetForm');
    if (!form) return false;
    
    // 基本字段验证
    const requiredFields = ['name', 'type', 'description', 'tokensymbol'];
    
    for (const field of requiredFields) {
        const input = form.elements[field];
        if (!input || !input.value.trim()) {
            showError(`Please fill in ${getFieldLabel(field)}`);
            return false;
        }
            }
            
    // 根据资产类型验证特定字段
    const assetType = form.elements['type'].value;
    
    if (assetType === '10') { // 不动产
        const specificFields = ['area', 'total_value'];
        for (const field of specificFields) {
            const input = form.elements[field];
            if (!input || !parseFloat(input.value)) {
                showError(`Please fill in ${getFieldLabel(field)}`);
                return false;
            }
        }
    } else if (assetType === '20') { // 类不动产
        // 检查token_supply字段
        const tokenSupplyInput = form.elements['token_supply'];
        if (!tokenSupplyInput || !parseInt(tokenSupplyInput.value)) {
            showError(`Please fill in ${getFieldLabel('token_supply')}`);
            return false;
            }
            
        // 检查total_value_similar字段
        const totalValueInput = form.elements['total_value_similar'];
        if (!totalValueInput || !parseFloat(totalValueInput.value)) {
            showError(`Please fill in ${getFieldLabel('total_value')}`);
            return false;
        }
    }
    
    return true;
}

// 显示错误信息
function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    const errorModalElement = document.getElementById('errorModal');
    
    if (errorMessage && errorModalElement) {
        errorMessage.textContent = message;
        const errorModal = new bootstrap.Modal(errorModalElement);
        errorModal.show();
    } else {
        console.error('Error modal element not found');
        alert(message);
        }
    }

// 显示成功信息
function showSuccess(message) {
    const successMessage = document.getElementById('successMessage');
    const successModalElement = document.getElementById('successModal');
    
    if (successMessage && successModalElement) {
        successMessage.textContent = message;
        const successModal = new bootstrap.Modal(successModalElement);
        successModal.show();
    } else {
        console.error('Success modal element not found');
        alert(message);
        }
    }

    // 显示资产预览
    function showAssetPreview() {
    // 获取所有字段数据
        const formData = getAssetFormData();
        if (!formData) return false;
        
    try {
        const previewModalEl = document.getElementById('previewModal');
        
        if (!previewModalEl) {
            console.error('预览模态框元素不存在');
            return false;
        }
        
        // 生成预览HTML
        const html = generatePreviewHTML(formData);
        
        // 更新模态框内容
        const modalBody = previewModalEl.querySelector('.modal-body');
        if (modalBody) {
            modalBody.innerHTML = html;
        }
        
        // 显示底部固定按钮
        const previewFooter = document.getElementById('previewFooter');
        if (previewFooter) {
            previewFooter.style.display = 'block';
        }
        
        // 绑定底部按钮事件
        const closePreviewBtn = document.getElementById('closePreviewBtn');
        if (closePreviewBtn) {
            closePreviewBtn.addEventListener('click', function() {
                closePreview();
            });
        }
        
        const publishFromPreviewBtn = document.getElementById('publishFromPreviewBtn');
        if (publishFromPreviewBtn) {
            publishFromPreviewBtn.addEventListener('click', function() {
                // 关闭预览
                closePreview();
                
                // 先检查钱包连接状态，然后再显示支付确认对话框
                checkAndConnectWallet().then(connected => {
                    if (connected) {
                        // 显示支付确认对话框
                        showPaymentConfirmation();
                    } else {
                        showError('请先连接钱包以继续');
                    }
                }).catch(error => {
                    console.error('钱包连接检查出错:', error);
                    showError(error.message || '钱包连接失败，请重试');
                });
            });
        }
        
        // 绑定模态框中的按钮事件
        const previewPublishBtn = document.getElementById('previewPublishBtn');
        if (previewPublishBtn) {
            previewPublishBtn.addEventListener('click', function() {
                // 关闭预览模态框
                const previewModal = bootstrap.Modal.getInstance(document.getElementById('previewModal'));
                if (previewModal) previewModal.hide();
                
                // 先检查钱包连接状态，然后再显示支付确认对话框
                checkAndConnectWallet().then(connected => {
                    if (connected) {
                        // 显示支付确认对话框
                        showPaymentConfirmation();
                    } else {
                        showError('请先连接钱包以继续');
                    }
                }).catch(error => {
                    console.error('钱包连接检查出错:', error);
                    showError(error.message || '钱包连接失败，请重试');
                });
            });
        }
        
        // 显示预览模态框
        const previewModal = new bootstrap.Modal(previewModalEl);
        previewModal.show();
        
        // 模态框关闭时隐藏底部按钮
        previewModalEl.addEventListener('hidden.bs.modal', function() {
            closePreview();
        });
        
        return true;
    } catch (error) {
        console.error('显示预览出错:', error);
        showError(error.message);
        return false;
    }
}

// 关闭预览
function closePreview() {
    const previewFooter = document.getElementById('previewFooter');
    if (previewFooter) {
        previewFooter.style.display = 'none';
    }
    }

// 获取资产类型名称
function getAssetTypeName(assetType) {
    const types = {
        '10': 'Real Estate',
        '20': 'Mining/Energy',
        '30': 'Infrastructure',
        '40': 'Agriculture',
        '50': 'Other'
    };
    return types[assetType] || 'Unknown';
}

// 生成预览HTML内容 - 与详情页保持一致的样式
function generatePreviewHTML(data) {
    const feeAmount = (parseFloat(data.total_value) * 0.035).toFixed(2);
    
    return `
    <div class="asset-detail-page">
        <div class="row">
            <!-- 左侧内容 -->
            <div class="col-lg-7">
                <!-- 资产图片轮播 -->
                <div id="previewCarousel" class="carousel slide mb-4" data-bs-ride="carousel">
                    <div class="carousel-inner">
                        ${data.images.length > 0 ? 
                            data.images.map((img, index) => `
                                <div class="carousel-item ${index === 0 ? 'active' : ''}">
                                    <img src="${img.url}" class="d-block w-100" style="border-radius: 12px; height: 400px; object-fit: cover;" alt="Asset Image">
                                </div>
                            `).join('') : 
                            `<div class="carousel-item active">
                                <div class="d-block w-100 bg-light text-center py-5" style="height: 400px; border-radius: 12px;">
                                    <i class="fas fa-image text-muted" style="font-size: 64px;"></i>
                                    <p class="mt-3 text-muted">No images uploaded</p>
                                </div>
                            </div>`
                        }
                    </div>
                    ${data.images.length > 1 ? `
                        <button class="carousel-control-prev" type="button" data-bs-target="#previewCarousel" data-bs-slide="prev">
                            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                        </button>
                        <button class="carousel-control-next" type="button" data-bs-target="#previewCarousel" data-bs-slide="next">
                            <span class="carousel-control-next-icon" aria-hidden="true"></span>
                        </button>
                    ` : ''}
                </div>

                <!-- 资产基本信息 -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h5 class="mb-0">Asset Information</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Asset Name:</strong> ${data.name}</p>
                                <p><strong>Location:</strong> ${data.location || 'Not specified'}</p>
                                <p><strong>Asset Type:</strong> ${getAssetTypeName(data.asset_type)}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Total Value:</strong> ${parseFloat(data.total_value).toLocaleString()} USDC</p>
                                <p><strong>Token Supply:</strong> ${parseInt(data.token_supply).toLocaleString()}</p>
                                <p><strong>Token Price:</strong> ${parseFloat(data.token_price).toFixed(4)} USDC</p>
                            </div>
                        </div>
                        <div class="mt-3">
                            <p><strong>Description:</strong></p>
                            <p class="text-muted">${data.description || 'No description provided'}</p>
                        </div>
                    </div>
                </div>

                <!-- 分红信息 -->
                <div class="card mb-4">
                    <div class="card-header">
                        <h5 class="mb-0">Dividend Information</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Annual Revenue:</strong> ${parseFloat(data.annual_revenue || 0).toLocaleString()} USDC</p>
                                <p><strong>Dividend Frequency:</strong> Quarterly</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Expected Yield:</strong> ${((parseFloat(data.annual_revenue || 0) / parseFloat(data.total_value)) * 100).toFixed(2)}%</p>
                                <p><strong>First Dividend:</strong> After asset launch</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 右侧交易卡片 -->
            <div class="col-lg-5">
                <div class="card trade-card">
                    <div class="card-header">
                        <h5 class="mb-0">Asset Preview</h5>
                    </div>
                    <div class="card-body">
                        <div class="mb-4">
                            <h4 class="mb-3 text-primary">RH-PREVIEW</h4>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-muted">Asset Name:</span>
                                <span>${data.name}</span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-muted">Token Price:</span>
                                <span class="fw-bold fs-5">${parseFloat(data.token_price).toFixed(4)} USDC</span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-muted">Token Supply:</span>
                                <span>${parseInt(data.token_supply).toLocaleString()}</span>
                            </div>
                            <div class="d-flex justify-content-between mb-4">
                                <span class="text-muted">Available:</span>
                                <span>${parseInt(data.token_supply).toLocaleString()}</span>
                            </div>
                        </div>

                        <!-- 发布成本信息 -->
                        <div class="alert alert-info">
                            <h6 class="alert-heading">Publishing Cost</h6>
                            <p class="mb-1"><strong>Platform Fee (3.5%):</strong> ${feeAmount} USDC</p>
                            <p class="mb-0 small text-muted">This fee covers asset tokenization and blockchain deployment costs.</p>
                        </div>

                        <!-- 预览说明 -->
                        <div class="alert alert-warning">
                            <i class="fas fa-info-circle me-2"></i>
                            <strong>Preview Mode</strong><br>
                            <small>This is how your asset will appear to investors after publishing. Review all information carefully before proceeding with payment.</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>`;
}

// 显示详细的进度步骤
function showDetailedProgress() {
    const progressSteps = [
        { id: 'step-1', title: '准备支付', description: '获取支付配置和验证钱包连接', status: 'pending' },
        { id: 'step-2', title: '处理支付', description: '在钱包中确认USDC转账交易', status: 'pending' },
        { id: 'step-3', title: '生成代币符号', description: '为资产生成唯一的代币标识符', status: 'pending' },
        { id: 'step-4', title: '创建资产', description: '在区块链上部署资产智能合约', status: 'pending' },
        { id: 'step-5', title: '完成', description: '资产创建完成，可以开始交易', status: 'pending' }
    ];

    const progressHtml = `
        <div class="progress-steps-container">
            <div class="progress-header mb-4">
                <h5 class="mb-2">资产创建进度</h5>
                <div class="progress mb-3" style="height: 8px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%" id="main-progress-bar"></div>
                </div>
            </div>
            <div class="steps-list">
                ${progressSteps.map(step => `
                    <div class="step-item" id="${step.id}">
                        <div class="step-icon">
                            <i class="fas fa-circle step-pending"></i>
                            <i class="fas fa-spinner fa-spin step-loading" style="display: none;"></i>
                            <i class="fas fa-check step-completed" style="display: none;"></i>
                            <i class="fas fa-times step-error" style="display: none;"></i>
                        </div>
                        <div class="step-content">
                            <div class="step-title">${step.title}</div>
                            <div class="step-description">${step.description}</div>
                            <div class="step-error-message" style="display: none;"></div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    return progressHtml;
}

// 更新步骤状态
function updateStepStatus(stepId, status, errorMessage = '') {
    const stepElement = document.getElementById(stepId);
    if (!stepElement) return;

    const icons = {
        pending: stepElement.querySelector('.step-pending'),
        loading: stepElement.querySelector('.step-loading'),
        completed: stepElement.querySelector('.step-completed'),
        error: stepElement.querySelector('.step-error')
    };

    const errorDiv = stepElement.querySelector('.step-error-message');

    // 隐藏所有图标
    Object.values(icons).forEach(icon => {
        if (icon) icon.style.display = 'none';
    });

    // 显示对应状态的图标
    if (icons[status]) {
        icons[status].style.display = 'inline-block';
    }

    // 更新步骤样式
    stepElement.className = `step-item step-${status}`;

    // 显示错误消息
    if (status === 'error' && errorMessage && errorDiv) {
        errorDiv.textContent = errorMessage;
        errorDiv.style.display = 'block';
    } else if (errorDiv) {
        errorDiv.style.display = 'none';
    }
}

// 更新主进度条
function updateMainProgress(percentage) {
    const progressBar = document.getElementById('main-progress-bar');
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
    }
}

// 显示进度模态框
function showProgressModal() {
    // 创建进度模态框
    const progressModalHtml = `
        <div class="modal fade" id="progressModal" tabindex="-1" aria-labelledby="progressModalLabel" aria-hidden="true" data-bs-backdrop="static" data-bs-keyboard="false">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="progressModalLabel">创建资产</h5>
                    </div>
                    <div class="modal-body">
                        ${showDetailedProgress()}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除已存在的进度模态框
    const existingModal = document.getElementById('progressModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 添加新的进度模态框
    document.body.insertAdjacentHTML('beforeend', progressModalHtml);
    
    // 显示模态框
    const progressModal = new bootstrap.Modal(document.getElementById('progressModal'));
    progressModal.show();
    
    return progressModal;
}

// 隐藏进度模态框
function hideProgressModal() {
    const progressModal = document.getElementById('progressModal');
    if (progressModal) {
        const modal = bootstrap.Modal.getInstance(progressModal);
        if (modal) {
            modal.hide();
        }
        // 延迟移除DOM元素
        setTimeout(() => {
            progressModal.remove();
        }, 300);
    }
}

// 显示支付确认对话框
    function showPaymentConfirmation() {
    try {
        // 获取表单数据并验证
        const formData = getAssetFormData();
        if (!formData) {
            throw new Error('获取表单数据失败');
        }
        
        // 获取支付金额
        const publishingFee = document.getElementById('publishingFee').textContent;
        
        // 显示确认模态框
        const confirmModalEl = document.getElementById('paymentConfirmModal');
        if (!confirmModalEl) {
            throw new Error('支付确认模态框不存在');
        }
        
        // 更新确认模态框内容
        const assetNameEl = document.getElementById('confirmAssetName');
        const tokenSymbolEl = document.getElementById('confirmTokenSymbol');
        const feeAmountEl = document.getElementById('confirmFeeAmount');
        
        if (assetNameEl) assetNameEl.textContent = formData.name;
        if (tokenSymbolEl) tokenSymbolEl.textContent = formData.token_symbol;
        if (feeAmountEl) feeAmountEl.textContent = publishingFee;
        
        // 显示模态框
        const confirmModal = new bootstrap.Modal(confirmModalEl);
        confirmModal.show();
        
        // 绑定确认按钮事件
        const confirmPaymentBtn = document.getElementById('confirmPaymentBtn');
        if (confirmPaymentBtn) {
            // 移除之前的事件监听器
            confirmPaymentBtn.replaceWith(confirmPaymentBtn.cloneNode(true));
            const newConfirmBtn = document.getElementById('confirmPaymentBtn');
            
            // 添加新的事件监听器
            newConfirmBtn.addEventListener('click', function() {
                // 检查并连接钱包
                checkAndConnectWallet().then(connected => {
                    if (connected) {
                        // 隐藏确认模态框
                confirmModal.hide();
                        // 显示进度对话框
                        showProgressModal();
                        
                        // 执行支付流程
                        processPayment().then(paymentResult => {
                            if (paymentResult.success) {
                                // 支付成功，发布资产
                                processAssetCreation(formData, paymentResult.txHash);
                            } else {
                                // 支付失败
                                showError(paymentResult.error || '支付处理失败');
                                disablePublishButtons(false);
                                hideProgressModal();
                            }
                        }).catch(error => {
                            console.error('支付处理错误:', error);
                            showError(error.message || '支付处理错误');
                            disablePublishButtons(false);
                            hideProgressModal();
            });
                    } else {
                        // 钱包连接失败
                        showError('请先连接钱包以继续');
                        disablePublishButtons(false);
                    }
                }).catch(error => {
                    console.error('钱包连接错误:', error);
                    showError(error.message || '钱包连接错误');
                    disablePublishButtons(false);
                });
            });
        }
        
    } catch (error) {
        console.error('显示支付确认出错:', error);
        showError(error.message);
        }
    }

    // 处理支付流程
async function processPayment() {
    return new Promise(async (resolve, reject) => {
        try {
            console.log('开始处理支付...');
            updateStepStatus('step-1', 'loading');
            updateMainProgress(30);
            
            // 检查并加载Solana Web3.js库
            if (typeof solanaWeb3 === 'undefined') {
                console.log('加载solanaWeb3库...');
                try {
                    await loadExternalScript('https://unpkg.com/@solana/web3.js@latest/lib/index.iife.min.js');
                    console.log('solanaWeb3库加载成功');
                
                    // 确保全局变量可用
                    if (typeof solanaWeb3 === 'undefined' && typeof solanaWeb3 !== 'undefined') {
                        window.solanaWeb3 = solanaWeb3;
                    }
                } catch (loadError) {
                    console.error('加载Solana Web3库失败:', loadError);
                    throw new Error('无法加载必要的区块链库');
                }
            }
            
            // 从API获取支付配置（不使用硬编码地址）
            let platformAddress = null;
            let feeAmount = null;
            
            try {
                // 从API获取最新的支付配置
                const configResponse = await fetch('/api/service/config/payment_settings');
                if (!configResponse.ok) {
                    throw new Error(`获取支付配置失败: HTTP ${configResponse.status}`);
                }
                
                const configData = await configResponse.json();
                // 使用资产创建收款地址，如果没有则使用平台收款地址
                platformAddress = configData.asset_creation_fee_address || configData.platform_fee_address;
                feeAmount = parseFloat(configData.creation_fee?.amount);
                
                if (!platformAddress || !feeAmount) {
                    throw new Error('API返回的支付配置不完整');
                }
                
                console.log('从API获取支付配置成功:', configData);
                console.log(`使用收款地址: ${platformAddress}, 费用: ${feeAmount} USDC`);
            } catch (configError) {
                console.error('获取支付配置失败:', configError);
                throw new Error(`无法获取支付配置: ${configError.message}`);
            }
            
            console.log(`准备支付 ${feeAmount} USDC 到 ${platformAddress}`);
            
            // 确保用户已连接钱包
            const walletData = window.wallet.getCurrentWallet();
            if (!walletData || !walletData.connected) {
                console.log('钱包未连接，尝试连接钱包');
                await checkAndConnectWallet();
            }
            
            // 获取表单数据（用于后续创建资产）
            const formData = getAssetFormData();
            console.log('获取的表单数据:', formData);
            
            if (!window.wallet) {
                throw new Error('钱包接口不可用');
            }
            
            try {
                updateStepStatus('step-1', 'completed');
                updateStepStatus('step-2', 'loading');
                updateMainProgress(30);
                
                // 添加延迟让用户看到进度变化
                await new Promise(resolve => setTimeout(resolve, 800));
                
                console.log('开始处理支付交易，不预先检查余额...');
                
                // 直接调用钱包进行支付，不预先检查余额
                const result = await window.wallet.transferToken(
                    'USDC',
                    platformAddress,
                    feeAmount
                );
            
                // 检查转账结果
                if (!result.success) {
                    console.error('支付失败:', result.error);
                    throw new Error(`转账失败: ${result.error || '未知原因'}`);
            }
            
                console.log('支付成功，交易哈希:', result.txHash);
                updateStepStatus('step-2', 'completed');
                updateMainProgress(50);
                
                // 添加延迟让用户看到支付成功状态
                await new Promise(resolve => setTimeout(resolve, 600));
            
                // 处理资产创建
                await handlePaymentSuccess(result.txHash, formData);
                
                // 完成整个流程
                resolve(result);
            } catch (paymentError) {
                console.error('支付失败:', paymentError);
            hideLoadingState();
                showError(`支付失败: ${paymentError.message || '支付处理出错'}`);
                throw new Error(`转账失败: ${paymentError.message || '支付处理出错'}`);
            }
        } catch (error) {
            console.error('支付处理错误:', error);
            updateProgress(0, '');
            hideLoadingState();
            reject(error);
        }
    });
}

// 辅助函数：动态加载外部脚本
function loadExternalScript(url) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = url;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`无法加载脚本: ${url}`));
        document.head.appendChild(script);
    });
    }

// 处理资产创建逻辑 - 付款后立即创建资产，不等待交易确认
async function processAssetCreation(formData, txHash) {
    try {
        console.log('开始创建资产...');
        showLoadingState('{{ _("Creating asset...") }}');
        disablePublishButtons(true);
        
        // 更新进度
        updateProgress(50, '{{ _("Preparing asset data...") }}');
        
        // 验证token_symbol
        let tokenSymbol = formData.token_symbol;
        if (!tokenSymbol) {
            const assetType = formData.asset_type || '20';
            console.log('Token Symbol不存在，生成新的，资产类型:', assetType);
            const newTokenSymbol = await generateTokenSymbol(assetType);
            
            if (newTokenSymbol) {
                formData.token_symbol = newTokenSymbol;
                console.log('使用新生成的Token Symbol:', newTokenSymbol);
                
                // 更新页面上的Token Symbol显示
                const tokenSymbolInput = document.getElementById('tokensymbol');
                if (tokenSymbolInput) {
                    tokenSymbolInput.value = newTokenSymbol;
                }
            } else {
                throw new Error('{{ _("Failed to generate valid Token Symbol, please try again.") }}');
            }
        } else {
            console.log('使用现有的Token Symbol:', formData.token_symbol);
            const checkResult = await checkTokenSymbolAvailability(tokenSymbol);
            if (checkResult.exists) throw new Error(`{{ _("Token symbol \'{tokenSymbol}\' is already in use. Please try another symbol or refresh the page.") }}`.replace('{tokenSymbol}', tokenSymbol));
        }
        console.log('{{ _("Using Token Symbol") }}:', tokenSymbol);
        
        updateProgress(70, '{{ _("Preparing asset data...") }}');
        
        // 构建请求数据，支付成功后设置为 PAYMENT_PROCESSING(8)
        // 确保包含支付交易信息
        const requestData = {
            ...formData,
            payment_tx_hash: Array.isArray(txHash) ? 
                txHash.map(byte => byte.toString(16).padStart(2, '0')).join('') : // 字节数组转十六进制字符串
                txHash, // 如果已经是字符串，直接使用
            payment_confirmed: false, // 初始设置为未确认
            images: uploadedImages.map(file => file.url || ''),
            documents: uploadedDocuments.map(file => ({
                name: file.file ? file.file.name : file.name || 'document.pdf',
                url: file.url || ''
            }))
        };
        
        console.log('提交的资产数据:', requestData);
        updateProgress(80, '{{ _("Creating asset...") }}');
        
        // 创建资产
        const createResponse = await fetch('/api/assets/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Eth-Address': window.walletState?.getAddress() || '',
                'X-Wallet-Type': window.walletState?.getWalletType() || '',
                'X-Payment-Hash': txHash // 额外添加支付哈希在头信息中
            },
            body: JSON.stringify(requestData)
        });
        
        const createResult = await createResponse.json();
        
        if (!createResponse.ok || !createResult.success) {
            throw new Error('{{ _("Failed to create asset") }}' + ': ' + (createResult.error || '{{ _("Unknown error") }}'));
        }
        
        console.log('资产创建请求成功:', createResult);
       
        updateProgress(90, '{{ _("Asset creation request submitted!") }}', 4);
        
        // 检查是否需要部署智能合约
        if (createResult.contract_ready) {
            console.log('资产智能合约已准备完成，需要部署到区块链');
            updateProgress(95, '准备部署智能合约到区块链...', 4);
            
            // 询问用户是否立即部署智能合约
            const shouldDeploy = await showDeploymentConfirmDialog();
            if (shouldDeploy) {
                try {
                    await deployAssetContract(createResult);
                    updateProgress(100, '智能合约部署成功！', 4);
                    hideLoadingState();
                    showSuccess('{{ _("Asset creation and smart contract deployment completed! Redirecting to asset page...") }}');
                } catch (deployError) {
                    console.error('智能合约部署失败:', deployError);
                    updateProgress(100, '资产创建成功，但智能合约部署失败', 4);
                    hideLoadingState();
                    showWarning('资产创建成功，但智能合约部署失败。您可以稍后在资产详情页面重新部署。');
                }
            } else {
                updateProgress(100, '资产创建成功，智能合约稍后部署', 4);
                hideLoadingState();
                showSuccess('{{ _("Asset creation request submitted successfully! You can deploy the smart contract later from the asset page.") }}');
            }
        } else {
            updateProgress(100, '{{ _("Asset creation request submitted!") }}', 4);
            hideLoadingState();
            showSuccess('{{ _("Asset creation request submitted successfully! Redirecting to asset page...") }}');
        }
        
        // 延迟跳转到资产详情页，给用户时间看到消息
        setTimeout(() => {
            window.location.href = `/assets/${createResult.token_symbol}`;
        }, 2000);
        
        return createResult;
    } catch (error) {
        console.error('{{ _("Asset creation error") }}' + ':', error);
        hideLoadingState();
        showError(error.message || '{{ _("Processing error, please try again.") }}');
        disablePublishButtons(false);
        throw error; // 重新抛出错误以便调用者处理
    }
}

/**
 * 显示智能合约部署确认对话框
 */
async function showDeploymentConfirmDialog() {
    return new Promise((resolve) => {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: '部署智能合约',
                text: '您的资产已创建成功！是否立即部署智能合约到区块链？这将启用真正的链上交易功能。',
                icon: 'question',
                showCancelButton: true,
                confirmButtonText: '立即部署',
                cancelButtonText: '稍后部署',
                confirmButtonColor: '#007bff',
                cancelButtonColor: '#6c757d'
            }).then((result) => {
                resolve(result.isConfirmed);
            });
        } else {
            const deploy = confirm('您的资产已创建成功！是否立即部署智能合约到区块链？');
            resolve(deploy);
        }
    });
}

/**
 * 部署资产智能合约
 */
async function deployAssetContract(createResult) {
    try {
        console.log('开始部署智能合约:', createResult);
        
        if (!createResult.contract_deployment) {
            throw new Error('缺少智能合约部署信息');
        }
        
        // 检查钱包连接
        if (!window.walletState || !window.walletState.connected) {
            throw new Error('钱包未连接，无法部署智能合约');
        }
        
        const walletAddress = window.walletState.getAddress();
        if (!walletAddress) {
            throw new Error('无法获取钱包地址');
        }
        
        // 获取智能合约交易数据
        const deploymentData = {
            asset_id: createResult.id,
            wallet_address: walletAddress
        };
        
        console.log('请求智能合约部署数据:', deploymentData);
        
        // 请求智能合约部署交易
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
            throw new Error(deployData.error || '准备智能合约部署失败');
        }
        
        console.log('智能合约部署数据准备完成，等待用户签名');
        
        // 检查Solana钱包API
        if (!window.solana || !window.solana.signAndSendTransaction) {
            throw new Error('Solana钱包API不可用');
        }
        
        // 解码并签名智能合约部署交易
        const transactionBuffer = Uint8Array.from(atob(deployData.transaction_data), c => c.charCodeAt(0));
        const transaction = solanaWeb3.Transaction.from(transactionBuffer);
        
        // 请求钱包签名并发送交易
        const result = await window.solana.signAndSendTransaction(transaction);
        
        if (!result.signature) {
            throw new Error('智能合约部署交易失败：无签名返回');
        }
        
        console.log('智能合约部署交易成功，签名:', result.signature);
        
        // 等待交易确认（可选）
        // 这里可以添加交易确认逻辑
        
        return {
            success: true,
            signature: result.signature,
            message: '智能合约部署成功'
        };
        
    } catch (error) {
        console.error('智能合约部署失败:', error);
        throw error;
    }
}

/**
 * 显示警告消息
 */
function showWarning(message) {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: '注意',
            text: message,
            icon: 'warning',
            confirmButtonText: '确定',
            confirmButtonColor: '#ffc107'
        });
    } else {
        alert(message);
    }
}

// 检查token symbol可用性
async function checkTokenSymbolAvailability(symbol) {
    try {
        const response = await fetch(`/api/assets/check_token_symbol?symbol=${symbol}`);
        
        if (!response.ok) {
            throw new Error(`请求失败: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('检查token_symbol可用性出错:', error);
        // 默认返回不存在，让后端进行最终验证
        return { available: true, exists: false };
    }
}

// 更新加载状态显示
function updateLoadingStatus(message) {
    const loadingText = document.querySelector('.loading-text');
    if (loadingText) {
        loadingText.textContent = message;
    }
}

// 显示加载遮罩层
function showLoadingOverlay(message = 'Loading...') {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div class="loading-text mt-3">${message}</div>
        </div>
    `;
    document.body.appendChild(overlay);
    document.body.classList.add('overlay-active');
}

// 隐藏加载遮罩层
function hideLoadingOverlay() {
    try {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay && loadingOverlay.parentNode) {
            loadingOverlay.parentNode.removeChild(loadingOverlay);
        } else if (loadingOverlay) {
            // 如果元素存在但没有父节点，直接移除
            loadingOverlay.remove();
        }
    } catch (error) {
        console.error('移除加载覆盖层时出错:', error);
    }
}

// 显示成功消息
function showSuccessMessage(title, message) {
    // 创建成功消息模态框
    const successModal = document.createElement('div');
    successModal.innerHTML = `
        <div class="modal fade" id="successModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title text-success">
                            <i class="fas fa-check-circle me-2"></i>${title}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body text-center">
                        <div class="py-3">
                            <i class="fas fa-check-circle text-success mb-3" style="font-size: 3rem;"></i>
                            <p>${message}</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-success" onclick="window.location.href='/assets'">
                            <i class="fas fa-list me-2"></i>查看我的资产
                        </button>
                        <button type="button" class="btn btn-primary" onclick="window.location.reload()">
                            <i class="fas fa-plus me-2"></i>创建新资产
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(successModal);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('successModal'));
    modal.show();
    
    // 模态框关闭时移除元素
    document.getElementById('successModal').addEventListener('hidden.bs.modal', function() {
        document.body.removeChild(successModal);
    });
}

// 禁用或启用发布按钮
function disablePublishButtons(disabled) {
    const buttons = [
        document.getElementById('previewForm'),
        document.getElementById('payAndPublish'),
        document.getElementById('previewPublishBtn'),
        document.getElementById('publishFromPreviewBtn')
    ];
    
    buttons.forEach(button => {
        if (button) {
            button.disabled = disabled;
            // 确保禁用状态下的样式变化
            if (disabled) {
                button.classList.add('disabled');
                button.style.opacity = '0.65';
                button.style.pointerEvents = 'none';
            } else {
                button.classList.remove('disabled');
                button.style.opacity = '';
                button.style.pointerEvents = '';
        }
        }
    });
    
    // 修复按钮样式
    fixButtonStyles();
}

// 启用发布按钮
function enablePublishButtons() {
    disablePublishButtons(false);
}

// 修复按钮样式函数
function fixButtonStyles() {
    const gradientButtons = document.querySelectorAll('.btn-gradient-primary');
    
    gradientButtons.forEach(button => {
        // 确保颜色和背景
        button.style.color = '#fff';
        button.style.background = 'linear-gradient(135deg, #0d6efd 0%, #0b5ed7 100%)';
        button.style.borderColor = '#0d6efd';
        button.style.fontWeight = '500';
        
        // 如果按钮在预览模态框中，特别强调
        if (button.closest('.preview-modal') || button.closest('#previewFooter')) {
            button.style.background = 'linear-gradient(135deg, #0d6efd 0%, #0b5ed7 100%)';
            button.style.color = '#fff';
        }
    });
}

// 页面加载后修复按钮样式
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(fixButtonStyles, 500);
});

    // 支付过程状态跟踪
    let isPaymentInProgress = false;

    // 显示加载状态
    function showLoadingState(message) {
        const loadingOverlay = document.getElementById('loadingOverlay');
        isPaymentInProgress = true;
        
        // 添加页面关闭警告
        window.addEventListener('beforeunload', handleBeforeUnload);
    
        if (loadingOverlay) {
            loadingOverlay.classList.remove('d-none');
            const loadingText = loadingOverlay.querySelector('.loading-text');
            if (loadingText) {
                loadingText.textContent = message || 'Processing...';
            }
    } else {
        // 如果没有找到加载覆盖层，创建一个
        showLoadingOverlay(message);
        }
    }

    // 隐藏加载状态
    function hideLoadingState() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        isPaymentInProgress = false;
        
        // 移除页面关闭警告
        window.removeEventListener('beforeunload', handleBeforeUnload);
    
        if (loadingOverlay) {
            loadingOverlay.classList.add('d-none');
        }
    }
    
    // 处理页面关闭前的警告
    function handleBeforeUnload(event) {
        if (isPaymentInProgress) {
            const message = '正在处理支付交易，关闭页面可能导致交易失败。确定要离开吗？';
            event.preventDefault();
            event.returnValue = message;
            return message;
        }
    }

// 更新进度条和步骤指示器
function updateProgress(percent, message, step = null) {
    const progressBar = document.getElementById('progressBar');
    const statusElement = document.getElementById('progressStatus');
    const loadingText = document.querySelector('.loading-text');
    
    if (progressBar) {
        progressBar.style.width = `${percent}%`;
        progressBar.setAttribute('aria-valuenow', percent);
    }
    
    if (statusElement && message) {
        statusElement.textContent = message;
    }
    
    if (loadingText && message) {
        loadingText.textContent = message;
    }
    
    // 更新步骤指示器
    updateStepIndicator(step, percent);
}

// 更新步骤指示器
function updateStepIndicator(currentStep, percent) {
    const steps = ['step1', 'step2', 'step3', 'step4'];
    
    // 根据进度百分比自动确定步骤
    if (currentStep === null) {
        if (percent < 25) currentStep = 1;
        else if (percent < 50) currentStep = 2;
        else if (percent < 90) currentStep = 3;
        else currentStep = 4;
    }
    
    steps.forEach((stepId, index) => {
        const stepElement = document.getElementById(stepId);
        if (stepElement) {
            stepElement.classList.remove('active', 'completed');
            
            if (index + 1 < currentStep) {
                stepElement.classList.add('completed');
            } else if (index + 1 === currentStep) {
                stepElement.classList.add('active');
            }
        }
    });
}

// 获取表单数据
function getAssetFormData() {
    const form = document.getElementById('assetForm');
    if (!form) {
        showError('表单不存在');
        return null;
    }
    
    // 获取资产类型
    const assetType = form.elements['type'].value;
        
    // 通用字段
    const formData = {
        asset_type: parseInt(assetType),
        name: form.elements['name'].value.trim(),
        description: form.elements['description'].value.trim(),
        token_symbol: form.elements['tokensymbol'].value.trim(),
        location: form.elements['location'].value.trim(),
        // 添加上传的文件
        images: uploadedImages || [],
        documents: uploadedDocuments || [],
        // 发布费用在后端计算，不从前端传递
    };
    
    // 根据资产类型获取特定字段
    if (assetType === '10') { // 不动产
        formData.area = parseFloat(form.elements['area'].value) || 0;
        formData.total_value = parseFloat(form.elements['total_value'].value) || 0;
        
        // 代币数量和价格可能是自动计算的
        const tokenCountElement = document.getElementById('token_count');
        const tokenPriceElement = document.getElementById('token_price');
        
        formData.token_supply = parseInt(tokenCountElement.textContent.replace(/,/g, '')) || 0;
        formData.token_price = parseFloat(tokenPriceElement.textContent) || 0;
        
        // 年收益率 - 首先检查元素是否存在
        const annualRevenueElement = form.elements['annual_revenue'];
        formData.annual_revenue = annualRevenueElement ? (parseFloat(annualRevenueElement.value) || 1) : 1;
    } else { // 类不动产
        formData.total_value = parseFloat(form.elements['total_value_similar'].value) || 0;
        formData.token_supply = parseInt(form.elements['token_supply'].value) || 0;
        
        // 代币价格可能是自动计算的
        const tokenPriceElement = document.getElementById('calculatedTokenPriceSimilar');
        formData.token_price = parseFloat(tokenPriceElement.textContent) || 0;
        
        // 年收益率 - 首先检查元素是否存在
        const annualRevenueElement = form.elements['annual_revenue'];
        formData.annual_revenue = annualRevenueElement ? (parseFloat(annualRevenueElement.value) || 1) : 1;
    }
    
    console.log('获取的表单数据:', formData);
    return formData;
}

// 处理支付成功的情况
async function handlePaymentSuccess(txHash, formData) {
    try {
        updateStepStatus('step-3', 'loading');
        updateMainProgress(60);
        
        // 验证Token Symbol是否存在，如果不存在则生成
        if (!formData.token_symbol) {
            const assetType = formData.asset_type || '20';
            console.log('Token Symbol不存在，生成新的，资产类型:', assetType);
            const newTokenSymbol = await generateTokenSymbol(assetType);
            
            if (newTokenSymbol) {
                formData.token_symbol = newTokenSymbol;
                console.log('使用新生成的Token Symbol:', newTokenSymbol);
                
                // 更新页面上的Token Symbol显示
                const tokenSymbolInput = document.getElementById('tokensymbol');
                if (tokenSymbolInput) {
                    tokenSymbolInput.value = newTokenSymbol;
                }
            } else {
                throw new Error('无法生成Token Symbol，请重试');
            }
        } else {
            console.log('使用现有的Token Symbol:', formData.token_symbol);
        }
        
        // 创建资产
        updateStepStatus('step-3', 'completed');
        updateStepStatus('step-4', 'loading');
        updateMainProgress(75);
        
        const result = await processAssetCreation(formData, txHash);
        
        if (result.success) {
            // 更新进度显示
            updateStepStatus('step-3', 'completed');
            updateStepStatus('step-4', 'completed');
            updateStepStatus('step-5', 'completed');
            updateMainProgress(100);
            
            // 创建成功
            let successMessage = `
                <div class="text-center">
                    <i class="fas fa-check-circle text-success fa-3x mb-3"></i>
                    <h4>资产创建请求已提交</h4>
                    <p>您的资产创建请求已成功提交，系统正在处理中。</p>
                    <div class="card my-3 text-start">
                        <div class="card-body">
                            <h5 class="card-title">交易详情</h5>
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>资产ID:</span>
                                    <strong>${result.asset_id}</strong>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>交易哈希:</span>
                                    <a href="https://solscan.io/tx/${txHash}" target="_blank">${txHash.substring(0, 8)}...${txHash.substring(txHash.length - 8)}</a>
                                </li>
                                <li class="list-group-item d-flex justify-content-between">
                                    <span>状态:</span>
                                    <span class="badge bg-info">处理中</span>
                                </li>
                            </ul>
                    </div>
                </div>
                    <p class="text-muted">系统将自动确认交易状态，通常需要1-2分钟完成。</p>
                    <p class="text-muted">您可以在"我的资产"页面查看资产状态。</p>
            </div>
        `;
        
            // 显示成功消息
            try {
                Swal.fire({
                    title: '提交成功',
                    html: successMessage,
                    icon: 'success',
                    confirmButtonText: '查看资产',
                    showCancelButton: true,
                    cancelButtonText: '返回首页',
                    allowOutsideClick: false
                }).then((swalResult) => {
                    if (swalResult.isConfirmed) {
                        // 跳转到资产详情页
                        window.location.href = `/assets/${result.asset_id}`;
                    } else {
                        // 返回首页
                        window.location.href = '/';
                    }
                });
            } catch (swalError) {
                console.error('SweetAlert显示失败，使用备用跳转:', swalError);
                // 备用跳转逻辑
                if (confirm('资产创建成功！是否查看资产详情？')) {
                    window.location.href = `/assets/${result.asset_id}`;
                } else {
                    window.location.href = '/';
                }
            }
            
            // 设置定时任务轮询交易状态
            _pollTransactionStatus(txHash, result.asset_id);
            
            // 重置表单
            resetForm();
        } else {
            // 创建失败
            showError(`资产创建失败: ${result.error || '未知错误'}`);
            updateProgress(0, '创建失败，请重试');
            enablePublishButtons(false);
        }
    } catch (error) {
        console.error('处理支付成功后发生错误:', error);
        
        // 更新失败的步骤状态
        if (error.message.includes('生成代币符号')) {
            updateStepStatus('step-3', 'error', error.message);
        } else if (error.message.includes('创建资产')) {
            updateStepStatus('step-4', 'error', error.message);
        } else {
            updateStepStatus('step-4', 'error', error.message || '未知错误');
        }
        
        showError(`资产创建过程出错: ${error.message || '未知错误'}`);
        enablePublishButtons(false);
        }
}

// 轮询检查交易状态
async function _pollTransactionStatus(txHash, assetId, maxRetries = 12, retryInterval = 5000) {
    let retryCount = 0;
    
    const checkStatus = async () => {
        try {
            // 检查交易状态
            const response = await fetch(`/api/blockchain/solana/check-transaction?signature=${txHash}`);
            if (!response.ok) {
                throw new Error('检查交易状态失败');
            }
            
            const result = await response.json();
            console.log('交易状态:', result);
            
            if (result.confirmed) {
                console.log('交易已确认!');
                // 交易已确认，更新资产状态
                try {
                    // 更新Swal对话框内容
                    const swalContent = document.querySelector('.swal2-html-container');
                    if (swalContent) {
                        // 更新状态标签
                        const statusBadge = swalContent.querySelector('.badge');
                        if (statusBadge) {
                            statusBadge.className = 'badge bg-success';
                            statusBadge.textContent = '已确认';
    }

                        // 更新提示文本
                        const infoText = swalContent.querySelector('p.text-muted');
                        if (infoText) {
                            infoText.textContent = '交易已确认，资产已创建成功！';
                        }
                    }
                } catch (e) {
                    console.error('更新对话框状态失败:', e);
                }
            return;
        }
            
            // 交易失败
            if (result.error) {
                console.error('交易失败:', result.error);
                // 更新Swal对话框内容
                try {
                    const swalContent = document.querySelector('.swal2-html-container');
                    if (swalContent) {
                        // 更新状态标签
                        const statusBadge = swalContent.querySelector('.badge');
                        if (statusBadge) {
                            statusBadge.className = 'badge bg-danger';
                            statusBadge.textContent = '失败';
                        }
                        
                        // 更新提示文本
                        const infoText = swalContent.querySelector('p.text-muted');
                        if (infoText) {
                            infoText.textContent = `交易失败: ${result.error}。请联系客服处理。`;
                        }
                    }
                } catch (e) {
                    console.error('更新对话框状态失败:', e);
                }
                return;
            }
            
            // 交易仍在处理中
            retryCount++;
            if (retryCount < maxRetries) {
                setTimeout(checkStatus, retryInterval);
            }
        } catch (error) {
            console.error('检查交易状态出错:', error);
            retryCount++;
            if (retryCount < maxRetries) {
                setTimeout(checkStatus, retryInterval);
            }
        }
    };
    
    // 延迟几秒后开始轮询
    setTimeout(checkStatus, 2000);
}
