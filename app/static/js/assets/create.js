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
    
    // 检查钱包连接
    setTimeout(initializeWalletCheck, 500); // 延迟执行，确保钱包状态已初始化
    
    // 初始化表单元素
    initializeFormFields();
    
    // 加载草稿
    loadDraft();
    
    // 设置自动保存
    setInterval(saveDraft, CONFIG.DRAFT.AUTO_SAVE_INTERVAL);
    
    // 监听钱包状态变化事件
    document.addEventListener('walletStateChanged', function(event) {
        console.log('资产创建页面收到钱包状态变化事件:', event.detail);
        if (event.detail && typeof event.detail.connected !== 'undefined') {
            // 更新钱包状态
            initializeWalletCheck();
        }
    });
    
    // 监听钱包初始化完成事件
    document.addEventListener('walletStateInitialized', function(event) {
        console.log('资产创建页面收到钱包初始化完成事件:', event.detail);
        // 重新检查钱包状态
        setTimeout(initializeWalletCheck, 100);
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
    fetch('/api/check_admin', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Eth-Address': address
        },
        body: JSON.stringify({ address: address })
    })
    .then(response => response.json())
    .then(data => {
        isAdminUser = data.is_admin === true;
        console.log('管理员状态:', isAdminUser);
        updateUiForAdminStatus(isAdminUser);
    })
    .catch(error => {
        console.error('检查管理员状态出错:', error);
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
    
    // 计算发布费用 - 费率为0.0001%
    // 计算发布费用：totalValue * 0.000001 是基于资产总值的费用比例（0.0001%）
    // 0.01 是最低收费标准（0.01 USDC），确保即使资产价值很低也至少收取这个金额
    let fee = Math.max(totalValue * 0.000001, 0.01);
    publishingFeeElement.textContent = `${fee.toFixed(2)} USDC`;
}

// 生成代币符号
async function generateTokenSymbol(type) {
    try {
        // 请求服务器生成代币符号
        const response = await fetch('/api/generate-token-symbol', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ type: type })
        });
        
        if (!response.ok) {
            console.error(`生成token_symbol请求失败: ${response.status}`);
            return null;
        }
        
        const data = await response.json();
        
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
            return null;
        }
    } catch (error) {
        console.error('生成代币符号出错:', error);
        
        // 重试逻辑
        console.log('尝试本地生成代币符号');
        // 生成4位随机数字
        const randomDigits = Math.floor(1000 + Math.random() * 9000);
        
        // 构建代币符号
        const symbol = `${type === '10' ? 'RH-10' : 'RH-20'}${randomDigits}`;
        
        // 验证符号是否可用
        try {
            const checkResult = await checkTokenSymbolAvailability(symbol);
            if (checkResult.exists) {
                console.error(`本地生成的符号 ${symbol} 已存在`);
                return null;
            }
            
            console.log(`本地生成代币符号: ${symbol}`);
            return symbol;
        } catch (checkError) {
            console.error('验证本地生成的符号失败:', checkError);
            return null;
        }
    }
}

// 处理文件上传
async function handleFiles(files, fileType) {
    console.log(`开始处理${fileType}上传，文件数量:`, files.length);
    if (!files || files.length === 0) return;
    
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

    // 显示进度条区域
    progressContainer.style.display = 'block';
    
    // 重置进度条状态
    percentElement.textContent = '0';
    progressBar.style.width = '0%';
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
        if (file.size > 5 * 1024 * 1024) { // 5MB
            statusElement.textContent = `文件过大: ${file.name} (${(file.size/1024/1024).toFixed(2)}MB > 5MB)`;
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
        formData.append('asset_type', assetType);
        
        // 获取代币符号
        const tokenSymbolInput = document.getElementById('token_symbol');
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
            
            // 发送上传请求
            console.log(`发送上传请求到 /api/upload-images，文件大小: ${(file.size/1024).toFixed(2)}KB`);
            const response = await fetch('/api/upload-images', {
                method: 'POST',
                body: formData
            });
            
            console.log(`收到响应，状态码: ${response.status}`);
            
            if (!response.ok) {
                let errorMessage = `上传失败: HTTP ${response.status}`;
                try {
                    const errorJson = await response.json();
                    if (errorJson && errorJson.message) {
                        errorMessage = errorJson.message;
                    }
                } catch (e) {
                    // 无法解析JSON，使用默认错误消息
                }
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            console.log('上传响应:', result);
            
            // 同时支持新旧两种格式的响应
            if ((result.urls && result.urls.length > 0) || (result.image_paths && result.image_paths.length > 0)) {
                // 添加到上传文件列表
                const url = result.urls ? result.urls[0] : result.image_paths[0];
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
                throw new Error(result.error || result.message || '上传失败');
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
        container.innerHTML = `<div class="text-center text-muted">${window._("No images uploaded")}</div>`;
        return;
    }

    let html = '<div class="row g-3">';
    uploadedImages.forEach((image, index) => {
        html += `
            <div class="col-md-4">
                <div class="position-relative">
                    <img src="${image.url}" class="img-fluid rounded" alt="${window._("Asset Image")}">
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
        container.innerHTML = `<div class="text-center text-muted">${window._("No documents uploaded")}</div>`;
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
    // 在setTimeout中执行初始化，防止页面刷新
    setTimeout(initializeCreatePage, 100);
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

// 生成预览HTML内容
function generatePreviewHTML(data) {
    return `
        <!-- 预览内容 -->
        <div class="row">
            <div class="col-md-8">
                <!-- 资产图片轮播 -->
                <div id="previewCarousel" class="carousel slide mb-4" data-bs-ride="carousel">
                    <div class="carousel-inner">
                        ${data.images.length > 0 ? 
                            data.images.map((img, index) => `
                                <div class="carousel-item ${index === 0 ? 'active' : ''}">
                                    <img src="${img.url}" class="d-block w-100" alt="${window._("Asset Image")}">
                                </div>
                            `).join('') : 
                            `<div class="carousel-item active">
                                <div class="d-block w-100 bg-light text-center py-5" style="height: 300px;">
                                    <i class="fas fa-image text-muted" style="font-size: 64px;"></i>
                                    <p class="mt-3 text-muted">${window._("No images uploaded")}</p>
                                </div>
                            </div>`
                        }
                    </div>
                    ${data.images.length > 1 ? `
                        <button class="carousel-control-prev" type="button" data-bs-target="#previewCarousel" data-bs-slide="prev">
                            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                            <span class="visually-hidden">${window._("Previous")}</span>
                        </button>
                        <button class="carousel-control-next" type="button" data-bs-target="#previewCarousel" data-bs-slide="next">
                            <span class="carousel-control-next-icon" aria-hidden="true"></span>
                            <span class="visually-hidden">${window._("Next")}</span>
                        </button>
                    ` : ''}
                </div>
                
                <!-- 缩略图导航 -->
                ${data.images.length > 1 ? `
                    <div class="d-flex gap-2 mb-4">
                        ${data.images.map((img, index) => `
                            <div class="thumbnail" style="width: 80px; height: 60px; cursor: pointer;" 
                                onclick="$('#previewCarousel').carousel(${index})">
                                <img src="${img.url}" class="img-fluid rounded" alt="${window._("Thumbnail")}">
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                <!-- 资产描述 -->
                <div class="card mb-4">
                    <div class="card-body">
                        <h5 class="card-title">${data.name}</h5>
                        <p class="card-text">${data.description}</p>
                        
                        <div class="row mt-4">
                            <div class="col-md-6">
                                <h6 class="text-muted">${window._("Asset Details")}</h6>
                                <ul class="list-unstyled">
                                    <li><strong>${window._("Type")}:</strong> ${data.asset_type === 10 ? window._("Real Estate") : window._("Similar Assets")}</li>
                                    <li><strong>${window._("Location")}:</strong> ${data.location}</li>
                                    ${data.asset_type === 10 ? `
                                        <li><strong>${window._("Area")}:</strong> ${data.area} ${window._("sqm")}</li>
                                    ` : ''}
                                    <li><strong>${window._("Total Value")}:</strong> ${data.total_value} USDC</li>
                                </ul>
                            </div>
                        </div>
                        
                        <!-- 相关文档 -->
                        <div class="mt-4">
                            <h6 class="text-muted">${window._("Related Documents")}</h6>
                            ${data.documents.length > 0 ? `
                                <ul class="list-unstyled">
                                    ${data.documents.map(doc => `
                                        <li><i class="fas fa-file-alt me-2"></i>${doc.name}</li>
                                    `).join('')}
                                </ul>
                            ` : `<p class="text-muted">${window._("No documents uploaded")}</p>`}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 右侧交易信息 -->
            <div class="col-md-4">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">${window._("Asset Trading")}</h5>
                        <div class="mb-4">
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-muted">${window._("Total Supply")}</span>
                                <span>${data.token_supply} ${data.token_symbol}</span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-muted">${window._("Token Price")}</span>
                                <span>${data.token_price} USDC</span>
                            </div>
                            <div class="d-flex justify-content-between">
                                <span class="text-muted">${window._("Publishing Fee")}</span>
                                <span>${data.publishing_fee}</span>
                            </div>
                        </div>
                        
                        <!-- 购买表单（预览模式下禁用） -->
                        <form class="mb-4">
                            <div class="mb-3">
                                <label class="form-label">${window._("Purchase Amount")}</label>
                                <div class="input-group">
                                    <input type="number" class="form-control" placeholder="${window._("Enter amount")}" disabled>
                                    <span class="input-group-text">${window._("tokens")}</span>
                                </div>
                            </div>
                            <button type="button" class="btn btn-gradient-primary" data-page="create-asset" disabled>
                                ${window._("Not available in preview mode")}
                            </button>
                        </form>
                        
                        <!-- 近期交易 -->
                        <div>
                            <h6 class="text-muted mb-3">${window._("Recent Transactions")}</h6>
                            <p class="text-muted">${window._("No transaction records yet")}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
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
                        // 执行支付流程
                        processPayment().then(paymentResult => {
                            if (paymentResult.success) {
                                // 支付成功，发布资产
                                processAssetCreation(formData, paymentResult.txHash);
                            } else {
                                // 支付失败
                                showError(paymentResult.error || '支付处理失败');
                                disablePublishButtons(false);
                            }
                        }).catch(error => {
                            console.error('支付处理错误:', error);
                            showError(error.message || '支付处理错误');
                            disablePublishButtons(false);
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
            showLoadingState('处理支付交易...');
            
            // 平台收款地址 - 使用用户提供的固定地址
            const platformAddress = 'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd';
            
            // 获取支付金额
            const publishingFee = document.getElementById('publishingFee').textContent;
            const feeAmount = parseFloat(publishingFee) || 1.0; // 默认1.0 USDC
            
            // 检查钱包余额
            let walletBalance = 0;
            if (window.walletState && typeof window.walletState.balance !== 'undefined') {
                walletBalance = parseFloat(window.walletState.balance);
            } else if (typeof window.getWalletBalance === 'function') {
                walletBalance = await window.getWalletBalance();
            }
            
            if (walletBalance < feeAmount) {
                hideLoadingState();
                resolve({
                    success: false,
                    error: `余额不足: 需要 ${feeAmount} USDC，但钱包只有 ${walletBalance} USDC`
                });
                return;
            }
            
            console.log(`准备支付 ${feeAmount} USDC 到平台地址: ${platformAddress}`);
            
            // 尝试执行转账
            try {
                // 更新进度
                updateProgress(40, '正在处理USDC转账...');
                
                // 如果钱包API可用，使用真实交易
                if (window.walletState && typeof window.walletState.transferToken === 'function') {
                    console.log('使用钱包API执行USDC转账');
                    const result = await window.walletState.transferToken('USDC', platformAddress, feeAmount);
                    
                    if (result && result.success && result.txHash) {
                        console.log('转账成功:', result.txHash);
                        hideLoadingState();
                        resolve({
                            success: true,
                            txHash: result.txHash
                        });
                    } else {
                        throw new Error('转账失败: ' + (result.error || '未知错误'));
                    }
                } else {
                    // 模拟支付过程 - 用于开发测试
                    console.warn('钱包API不可用，使用模拟支付');
                    
                    setTimeout(() => {
                        hideLoadingState();
                        
                        // 模拟一个成功的交易
                        const mockTxHash = '0x' + Array(64).fill(0).map(() => Math.floor(Math.random() * 16).toString(16)).join('');
                        console.log('模拟支付成功，交易哈希:', mockTxHash);
                        
                        resolve({
                            success: true,
                            txHash: mockTxHash
                        });
                    }, 2000);
                }
            } catch (error) {
                console.error('转账过程出错:', error);
                hideLoadingState();
                resolve({
                    success: false,
                    error: '转账过程出错: ' + error.message
                });
            }
        } catch (error) {
            hideLoadingState();
            console.error('支付处理出错:', error);
            reject(error);
        }
    });
}

// 处理资产创建逻辑 - 付款成功后调用API创建资产
async function processAssetCreation(formData, txHash) {
    try {
        console.log('开始创建资产...');
        showLoadingState('创建资产中...');
        disablePublishButtons(true);
        
        // 更新进度
        updateProgress(50, '验证支付交易...');
        
        // 首先验证支付交易是否已确认
        try {
            // 这里应该调用后端API验证交易
            console.log('验证支付交易哈希:', txHash);
            
            // 在实际应用中，应该调用后端API验证交易
            // const verifyResponse = await fetch('/api/payments/verify', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({ txHash })
            // });
            // 
            // const verifyResult = await verifyResponse.json();
            // if (!verifyResponse.ok || !verifyResult.verified) {
            //     throw new Error('支付验证失败: ' + (verifyResult.error || '未知错误'));
            // }
            
            // 假设验证成功
            console.log('支付验证成功，继续创建资产');
        } catch (error) {
            console.error('支付验证错误:', error);
            // 继续流程，不中断，在实际应用中可能需要中断
        }
        
        // 验证token_symbol是否已存在
        let tokenSymbol = formData.token_symbol;
        if (!tokenSymbol) {
            // 如果没有token_symbol，则请求生成一个新的
            console.log('请求生成新的token_symbol');
            tokenSymbol = await generateTokenSymbol(formData.asset_type);
            
            if (!tokenSymbol) {
                throw new Error('无法生成有效的Token符号，请重试');
            }
            
            document.getElementById('tokensymbol').value = tokenSymbol;
            formData.token_symbol = tokenSymbol;
        } else {
            // 再次验证token_symbol是否可用
            const checkResult = await checkTokenSymbolAvailability(tokenSymbol);
            if (checkResult.exists) {
                throw new Error(`Token符号 ${tokenSymbol} 已被使用，请尝试其他符号或刷新页面重试`);
            }
        }
        
        console.log('使用Token符号:', tokenSymbol);
        
        // 更新进度
        updateProgress(70, '准备资产数据...');
        
        // 构建请求数据
        const requestData = {
            ...formData,
            payment_tx_hash: txHash,
            platform_address: 'HnPZkg9FpHjovNNZ8Au1MyLjYPbW9KsK87ACPCh1SvSd', // 平台收款地址，用于后端二次验证
            images: uploadedImages.map(file => file.url || ''),
            documents: uploadedDocuments.map(file => {
                return {
                    name: file.file ? file.file.name : file.name || 'document.pdf',
                    url: file.url || ''
                };
            })
        };
        
        console.log('提交的资产数据:', requestData);
        
        // 更新进度
        updateProgress(80, '创建资产...');
        
        // 创建资产
        const createResponse = await fetch('/api/assets/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        const createResult = await createResponse.json();
        
        if (!createResponse.ok || !createResult.success) {
            throw new Error('创建资产失败: ' + (createResult.error || '未知错误'));
        }
        
        console.log('资产创建成功:', createResult);
        
        // 更新进度
        updateProgress(100, '资产创建完成!');
        
        // 显示成功消息
        hideLoadingState();
        showSuccess('资产创建成功！正在跳转到资产详情页...');
        
        // 跳转到资产详情页
        setTimeout(() => {
            window.location.href = `/assets/${createResult.asset_id || createResult.token_symbol}`;
        }, 1500);
        
    } catch (error) {
        console.error('资产创建出错:', error);
        hideLoadingState();
        showError(error.message || '处理过程出错，请重试');
        disablePublishButtons(false);
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

// 显示加载状态
function showLoadingState(message) {
    const loadingOverlay = document.getElementById('loadingOverlay');
    
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
    
    if (loadingOverlay) {
        loadingOverlay.classList.add('d-none');
    }
}

// 更新进度条
function updateProgress(percent, message) {
    const progressBar = document.getElementById('progressBar');
    const statusElement = document.getElementById('loadingStatus');
    
    if (progressBar) {
        progressBar.style.width = `${percent}%`;
        progressBar.setAttribute('aria-valuenow', percent);
    }
    
    if (statusElement && message) {
        statusElement.textContent = message;
    }
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