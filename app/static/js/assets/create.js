// 配置常量
const CONFIG = {
    IMAGE: {
        MAX_FILES: 10,
        MAX_SIZE: 5 * 1024 * 1024, // 5MB
        ALLOWED_TYPES: ['image/jpeg', 'image/png', 'image/jpg', 'image/gif', 'image/webp'],
        COMPRESS: {
            MAX_WIDTH: 1920,
            MAX_HEIGHT: 1080,
            QUALITY: 0.8
        }
    },
    DOCUMENT: {
        MAX_FILES: 10,
        MAX_SIZE: 10 * 1024 * 1024, // 10MB
        ALLOWED_TYPES: ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
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
    }
};

// 全局变量声明
let form, nameInput, typeInput, locationInput, descriptionInput, areaInput, 
    totalValueInput, tokenCountInput, tokenSymbolInput, annualRevenueInput, 
    imageDropzone, documentDropzone, errorModal, errorMessageElement,
    uploadedImages = [], uploadedDocuments = [];

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', async function() {
    // 等待 Bootstrap 加载完成
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap is not loaded');
        return;
    }

    try {
        // 等待钱包状态初始化
        if (!window.ethereum) {
            console.error('MetaMask not installed');
            showWalletPrompt();
            return;
        }

        // 检查钱包连接状态
        const walletCheck = document.getElementById('walletCheck');
        const formContent = document.getElementById('formContent');
        
        // 注册钱包状态变化的处理函数
        window.walletState.onStateChange((state) => {
            console.log('Wallet state changed:', state);
            if (state.isConnected) {
                walletCheck.style.display = 'none';
                formContent.style.display = 'block';
            } else {
                walletCheck.style.display = 'block';
                formContent.style.display = 'none';
            }
        });

        // 初始检查
        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
        if (accounts.length === 0) {
            console.log('No wallet connected');
            showWalletPrompt();
            return;
        }

        // 有连接的钱包，显示表单
        console.log('Wallet connected:', accounts[0]);
        walletCheck.style.display = 'none';
        formContent.style.display = 'block';
        
        await initializeFormElements();
        await initializeEventListeners();
        console.log('Form initialization completed');
    } catch (error) {
        console.error('Form initialization failed:', error);
        showError('页面初始化失败，请刷新重试');
    }
});

// 显示钱包提示
function showWalletPrompt() {
    const walletCheck = document.getElementById('walletCheck');
    const formContent = document.getElementById('formContent');
    
    walletCheck.style.display = 'block';
    formContent.style.display = 'none';
}

// 初始化表单元素
async function initializeFormElements() {
    // 获取表单元素
    form = document.getElementById('assetForm');
    if (!form) {
        throw new Error('Form element not found');
    }

    // 必需的表单元素
    const requiredElements = {
        name: 'name',
        type: 'type',
        location: 'location',
        description: 'description',
        tokensymbol: 'tokensymbol'  // 添加 tokensymbol 作为必需元素
    };

    // 可选的表单元素
    const optionalElements = {
        area: 'area',
        totalValue: 'total_value',
        tokenCount: 'token_count',
        annualRevenue: 'annual_revenue',
        imageDropzone: 'imageDropzone',
        documentDropzone: 'documentDropzone'
    };

    // 验证必需的元素
    for (const [key, id] of Object.entries(requiredElements)) {
        const element = document.getElementById(id);
        if (!element) {
            console.error(`Required element not found: ${id}`);
            throw new Error(`Required element not found: ${id}`);
        }
        // 将元素赋值给对应的全局变量
        switch (key) {
            case 'name': nameInput = element; break;
            case 'type': typeInput = element; break;
            case 'location': locationInput = element; break;
            case 'description': descriptionInput = element; break;
            case 'tokensymbol': tokenSymbolInput = element; break;
        }
    }

    // 获取可选元素
    for (const [key, id] of Object.entries(optionalElements)) {
        const element = document.getElementById(id);
        if (element) {
            // 将元素赋值给对应的全局变量
            switch (key) {
                case 'area': areaInput = element; break;
                case 'totalValue': totalValueInput = element; break;
                case 'tokenCount': tokenCountInput = element; break;
                case 'annualRevenue': annualRevenueInput = element; break;
                case 'imageDropzone': imageDropzone = element; break;
                case 'documentDropzone': documentDropzone = element; break;
            }
        } else {
            console.warn(`Optional element not found: ${id}`);
        }
    }

    // 初始化错误模态框
    const errorModalElement = document.getElementById('errorModal');
    if (errorModalElement) {
        try {
            errorModal = new bootstrap.Modal(errorModalElement);
            errorMessageElement = document.getElementById('errorMessage');
            if (!errorMessageElement) {
                console.warn('Error message element not found, creating one');
                errorMessageElement = document.createElement('div');
                errorMessageElement.id = 'errorMessage';
                errorModalElement.querySelector('.modal-body')?.appendChild(errorMessageElement);
            }
        } catch (error) {
            console.error('Failed to initialize error modal:', error);
        }
    } else {
        console.warn('Error modal element not found, errors will be logged to console');
    }

    console.log('Form elements initialized successfully');
}

// 初始化事件监听器
function initializeEventListeners() {
    // 初始化图片上传
    if (imageDropzone) {
        const imageInput = document.getElementById('imageInput');
        if (!imageInput) {
            console.error('Image input element not found');
            return;
        }

        // 点击上传区域时触发文件选择
        imageDropzone.addEventListener('click', () => {
            imageInput.click();
        });

        // 处理文件选择
        imageInput.addEventListener('change', (e) => {
            handleFiles(e.target.files, 'IMAGE');
        });

        // 处理拖放
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
            handleFiles(e.dataTransfer.files, 'IMAGE');
        });
    }

    // 初始化文档上传
    if (documentDropzone) {
        const documentInput = document.getElementById('documentInput');
        if (!documentInput) {
            console.error('Document input element not found');
            return;
        }

        // 点击上传区域时触发文件选择
        documentDropzone.addEventListener('click', () => {
            documentInput.click();
        });

        // 处理文件选择
        documentInput.addEventListener('change', (e) => {
            handleFiles(e.target.files, 'DOCUMENT');
        });

        // 处理拖放
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
            handleFiles(e.dataTransfer.files, 'DOCUMENT');
        });
    }

    if (typeInput) {
        typeInput.addEventListener('change', async function() {
            const type = this.value;
            if (!type) return;
            
            // 先切换显示字段，提高响应速度
            toggleAssetTypeFields(type);
            
            try {
                // 立即生成代币符号
                const symbol = await generateTokenSymbol(type);
                if (tokenSymbolInput) {
                    tokenSymbolInput.value = symbol;
                    
                    let successMsg = document.getElementById('tokenSymbolSuccess');
                    if (!successMsg) {
                        successMsg = document.createElement('div');
                        successMsg.id = 'tokenSymbolSuccess';
                        successMsg.className = 'text-success mt-1';
                        const parentElement = tokenSymbolInput.closest('.input-group');
                        if (parentElement) {
                            parentElement.insertAdjacentElement('afterend', successMsg);
                        } else {
                            tokenSymbolInput.parentNode.appendChild(successMsg);
                        }
                    }
                    successMsg.innerHTML = '<i class="fas fa-check-circle me-1"></i>代币代码可用';
                }
            } catch (error) {
                console.error('生成代币代码失败:', error);
                showError(error.message);
            }
            
            // 更新文档要求
            updateDocumentRequirements(type);
        });
    }

    // 添加类不动产相关字段的事件监听
    const tokenSupplyInput = document.getElementById('token_supply');
    const totalValueSimilarInput = document.getElementById('total_value_similar');
    
    if (tokenSupplyInput) {
        tokenSupplyInput.addEventListener('input', function() {
            calculateSimilarAssetsTokenPrice();
        });
    }
    
    if (totalValueSimilarInput) {
        totalValueSimilarInput.addEventListener('input', function() {
            calculateSimilarAssetsTokenPrice();
        });
    }

    // 不动产相关字段的事件监听
    const areaInput = document.getElementById('area');
    const totalValueInput = document.getElementById('total_value');
    
    if (areaInput) {
        areaInput.addEventListener('input', function() {
            calculateRealEstateTokens();
        });
    }
    
    if (totalValueInput) {
        totalValueInput.addEventListener('input', function() {
            calculateRealEstateTokens();
        });
    }

    // 添加预览按钮事件监听器
    const previewBtn = document.getElementById('previewForm');
    if (previewBtn) {
        previewBtn.addEventListener('click', previewAsset);
    }

    // 添加表单提交事件监听器
    const form = document.getElementById('assetForm');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            await submitForm();
        });
    }

    // 添加预览模态框提交按钮事件监听器
    const previewModal = document.getElementById('previewModal');
    if (previewModal) {
        const submitBtn = previewModal.querySelector('.modal-footer .btn-primary');
        if (submitBtn) {
            submitBtn.addEventListener('click', async function() {
                const modal = bootstrap.Modal.getInstance(previewModal);
                if (modal) {
                    modal.hide();
                }
                await submitForm();
            });
        }
    }
}

// 切换资产类型显示
function toggleAssetTypeFields(type) {
    const realEstateFields = document.querySelectorAll('.asset-type-field.real-estate');
    const similarAssetsFields = document.querySelectorAll('.asset-type-field.similar-assets');
    
    if (type === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        realEstateFields.forEach(el => el.classList.remove('hidden'));
        similarAssetsFields.forEach(el => el.classList.add('hidden'));
        
        // 清空类不动产字段
        const tokenSupplyInput = document.getElementById('token_supply');
        const totalValueSimilarInput = document.getElementById('total_value_similar');
        if (tokenSupplyInput) tokenSupplyInput.value = '';
        if (totalValueSimilarInput) totalValueSimilarInput.value = '';
        
        // 重新计算不动产代币数量
        calculateRealEstateTokens();
    } else if (type === CONFIG.ASSET_TYPE.SIMILAR_ASSETS) {
        realEstateFields.forEach(el => el.classList.add('hidden'));
        similarAssetsFields.forEach(el => el.classList.remove('hidden'));
        
        // 清空不动产字段
        const areaInput = document.getElementById('area');
        const totalValueInput = document.getElementById('total_value');
        if (areaInput) areaInput.value = '';
        if (totalValueInput) totalValueInput.value = '';
        
        // 重置计算结果
        const tokenCountDisplay = document.getElementById('token_count');
        const tokenPriceDisplay = document.getElementById('token_price');
        if (tokenCountDisplay) tokenCountDisplay.textContent = '0';
        if (tokenPriceDisplay) tokenPriceDisplay.textContent = '0.000000';
    }
    
    // 更新文档要求显示
    updateDocumentRequirements(type);
}

// 计算不动产代币数量
function calculateRealEstateTokens() {
    const areaElement = document.getElementById('area');
    const totalValueElement = document.getElementById('total_value');
    const tokenCountElement = document.getElementById('token_count');
    const tokenPriceElement = document.getElementById('token_price');

    if (!areaElement || !totalValueElement || !tokenCountElement || !tokenPriceElement) {
        return;
    }

    const area = parseFloat(areaElement.value) || 0;
    const totalValue = parseFloat(totalValueElement.value) || 0;
    
    if (area > 0) {
        const tokenCount = Math.floor(area * CONFIG.CALCULATION.TOKENS_PER_SQUARE_METER);
        tokenCountElement.textContent = formatNumber(tokenCount);
        
        if (totalValue > 0) {
            const tokenPrice = totalValue / tokenCount;
            tokenPriceElement.textContent = tokenPrice.toFixed(CONFIG.CALCULATION.PRICE_DECIMALS);
        }
    }
}

// 计算结果元素
const calculatedElements = {
    realEstate: {
        tokenCount: document.getElementById('token_count'),
        tokenPrice: document.getElementById('token_price')
    },
    similarAssets: {
        tokenPrice: document.getElementById('calculatedTokenPriceSimilar')  // 修正ID
    }
};

// 进度条元素
const imageUploadProgress = document.getElementById('imageUploadProgress');
const imageUploadStatus = document.getElementById('imageUploadStatus');
const imageUploadPercent = document.getElementById('imageUploadPercent');
const documentUploadProgress = document.getElementById('documentUploadProgress');
const documentUploadStatus = document.getElementById('documentUploadStatus');
const documentUploadPercent = document.getElementById('documentUploadPercent');

// 草稿相关元素
const draftInfo = document.getElementById('draftInfo');
if (draftInfo) {
    draftInfo.style.display = 'none';  // 默认隐藏草稿信息
}

// 资产类型相关元素
const realEstateFields = document.querySelectorAll('.asset-type-field.real-estate');
const similarAssetsFields = document.querySelectorAll('.asset-type-field.similar-assets');
const realEstateInfo = document.querySelector('.real-estate-info');

// 数值格式化函数
function formatNumber(number, decimals = 0) {
    return Number(number).toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

// 图片压缩函数
async function compressImage(file) {
    try {
        if (!file || !(file instanceof File)) {
            throw new Error('无效的文件对象');
        }

        // 如果文件小于1MB且是JPEG/PNG，跳过压缩
        if (file.size < 1024 * 1024 && (file.type === 'image/jpeg' || file.type === 'image/png')) {
            return file;
        }

        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = new Image();
                img.onload = () => {
                    try {
                        const canvas = document.createElement('canvas');
                        let { width, height } = img;
                        
                        // 只有当图片尺寸超过限制时才进行缩放
                        const maxWidth = CONFIG.IMAGE.COMPRESS.MAX_WIDTH;
                        const maxHeight = CONFIG.IMAGE.COMPRESS.MAX_HEIGHT;
                        if (width > maxWidth || height > maxHeight) {
                            const ratio = Math.min(maxWidth / width, maxHeight / height);
                            width = Math.floor(width * ratio);
                            height = Math.floor(height * ratio);
                        }
                        
                        canvas.width = width;
                        canvas.height = height;
                        const ctx = canvas.getContext('2d');
                        ctx.imageSmoothingEnabled = true;
                        ctx.imageSmoothingQuality = 'high';
                        ctx.drawImage(img, 0, 0, width, height);
                        
                        canvas.toBlob(
                            (blob) => {
                                if (blob) {
                                    const compressedFile = new File([blob], file.name, {
                                        type: 'image/jpeg',
                                        lastModified: Date.now()
                                    });
                                    resolve(compressedFile);
                                } else {
                                    reject(new Error('压缩失败'));
                                }
                            },
                            'image/jpeg',
                            CONFIG.IMAGE.COMPRESS.QUALITY
                        );
                    } catch (error) {
                        reject(error);
                    }
                };
                img.onerror = reject;
                img.src = e.target.result;
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    } catch (error) {
        console.error('压缩图片失败:', error);
        return file; // 如果压缩失败，返回原始文件
    }
}

// 文件验证函数
function validateFiles(files, type) {
    if (!files || !type || !CONFIG[type.toUpperCase()]) {
        console.error('无效的文件验证参数');
        return {
            isValid: false,
            errors: ['文件验证失败']
        };
    }
    
    const config = CONFIG[type.toUpperCase()];
    const errors = [];
    
    // 检查文件数量
    if (files.length > config.MAX_FILES) {
        errors.push(`最多只能上传${config.MAX_FILES}个文件`);
        return {
            isValid: false,
            errors: errors
        };
    }
    
    // 检查每个文件
    for (const file of files) {
        if (!file || !file.name) {
            errors.push('无效的文件');
            continue;
        }
        
        // 检查文件大小
        if (file.size > config.MAX_SIZE) {
            const maxSizeMB = config.MAX_SIZE / (1024 * 1024);
            errors.push(`文件 ${file.name} 超过大小限制 (最大 ${maxSizeMB}MB)`);
        }
        
        // 检查文件类型
        if (!config.ALLOWED_TYPES.includes(file.type)) {
            const allowedTypes = config.ALLOWED_TYPES.map(type => type.split('/')[1].toUpperCase()).join(', ');
            errors.push(`文件 ${file.name} 类型不支持 (支持的格式: ${allowedTypes})`);
        }
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

// 显示上传进度
function showProgress(type, loaded, total) {
    const progress = (loaded / total) * 100;
    const elements = type === 'IMAGE' 
        ? { container: imageUploadProgress, status: imageUploadStatus, percent: imageUploadPercent }
        : { container: documentUploadProgress, status: documentUploadStatus, percent: documentUploadPercent };
    
    elements.container.style.display = 'block';
    elements.percent.textContent = Math.round(progress);
    elements.container.querySelector('.progress-bar').style.width = `${progress}%`;
    
    if (progress === 100) {
        setTimeout(() => {
            elements.container.style.display = 'none';
        }, 1000);
    }
}

// 处理文件上传
async function handleFiles(files, type) {
    try {
        if (!files || files.length === 0) {
            showError('请选择要上传的文件');
            return;
        }

        const fileType = type.toLowerCase();
        const progressElement = fileType === 'image' ? imageUploadProgress : documentUploadProgress;
        const percentElement = fileType === 'image' ? imageUploadPercent : documentUploadPercent;
        const statusElement = fileType === 'image' ? imageUploadStatus : documentUploadStatus;
        
        progressElement.style.display = 'block';
        
        // 初始化或获取上传数组
        const uploadArray = fileType === 'image' ? (window.uploadedImages = window.uploadedImages || []) : (window.uploadedDocuments = window.uploadedDocuments || []);

        // 验证文件
        const validation = validateFiles(files, type);
        if (!validation.isValid) {
            showError(validation.errors.join('\n'));
            return;
        }

        // 初始化进度变量
        let completedFiles = 0;
        let failedFiles = 0;
        const totalFiles = files.length;

        // 更新进度的函数
        const updateProgress = () => {
            const progress = ((completedFiles + failedFiles) / totalFiles) * 100;
            percentElement.textContent = Math.round(progress);
            progressElement.querySelector('.progress-bar').style.width = `${progress}%`;
            
            // 更新状态文本
            statusElement.textContent = `上传中... (${completedFiles}/${totalFiles})`;
            
            if (progress === 100) {
                setTimeout(() => {
                    progressElement.style.display = 'none';
                }, 1000);
            }
        };

        // 创建上传队列
        const uploadQueue = Array.from(files).map(async (file, index) => {
            try {
                // 处理文件（压缩图片或直接使用文档）
                const processedFile = fileType === 'image' ? await compressImage(file) : file;
                
                const formData = new FormData();
                formData.append('file', processedFile);
                formData.append('asset_type', document.getElementById('type').value || '10');
                formData.append('file_type', fileType);
                formData.append('asset_id', document.querySelector('input[name="asset_id"]')?.value || 'temp');

                // 使用 Promise 包装 XMLHttpRequest
                const uploadResult = await new Promise((resolve, reject) => {
                    const xhr = new XMLHttpRequest();
                    
                    xhr.upload.onprogress = (event) => {
                        if (event.lengthComputable) {
                            const fileProgress = (event.loaded / event.total) * 100;
                            const totalProgress = ((completedFiles + fileProgress / 100) / totalFiles) * 100;
                            percentElement.textContent = Math.round(totalProgress);
                            progressElement.querySelector('.progress-bar').style.width = `${totalProgress}%`;
                        }
                    };

                    xhr.onload = () => {
                        if (xhr.status === 200) {
                            resolve(JSON.parse(xhr.responseText));
                        } else {
                            reject(new Error(xhr.statusText));
                        }
                    };
                    
                    xhr.onerror = () => reject(new Error('上传失败'));
                    xhr.open('POST', '/api/upload', true);
                    xhr.send(formData);
                });

                if (uploadResult.urls && uploadResult.urls.length > 0) {
                    uploadArray.push(uploadResult.urls[0]);
                }
                
                completedFiles++;
                updateProgress();
                
            } catch (error) {
                console.error(`文件 ${file.name} 上传失败:`, error);
                failedFiles++;
                updateProgress();
            }
        });

        // 等待所有上传完成
        await Promise.all(uploadQueue);

        // 更新UI
        if (fileType === 'image') {
            updateImagePreview();
        } else {
            updateDocumentList();
        }

        // 隐藏进度条
        progressElement.style.display = 'none';

        // 显示结果消息
        if (failedFiles > 0) {
            showToast(`上传完成，${completedFiles}个成功，${failedFiles}个失败`);
        } else {
            showToast(`${fileType === 'image' ? '图片' : '文档'}上传完成`);
        }

    } catch (error) {
        console.error('处理文件失败:', error);
        showError(error.message);
    }
}

// 更新上传进度
function updateProgress() {
    const elements = type === 'IMAGE' 
        ? { container: imageUploadProgress, status: imageUploadStatus, percent: imageUploadPercent }
        : { container: documentUploadProgress, status: documentUploadStatus, percent: documentUploadPercent };
    
    const progress = ((completedFiles + failedFiles) / totalFiles) * 100;
    elements.percent.textContent = Math.round(progress);
    elements.container.querySelector('.progress-bar').style.width = `${progress}%`;
    
    if (progress === 100) {
        setTimeout(() => {
            elements.container.style.display = 'none';
        }, 1000);
    }
}

// 更新图片预览
function updateImagePreview() {
    const previewContainer = document.getElementById('imagePreview');
    previewContainer.innerHTML = '';

    if (window.uploadedImages && window.uploadedImages.length > 0) {
        window.uploadedImages.forEach((url, index) => {
            const col = document.createElement('div');
            col.className = 'col-md-4 mb-3';
            
            const card = document.createElement('div');
            card.className = 'card h-100';
            
            const img = document.createElement('img');
            img.src = url;
            img.className = 'card-img-top';
            img.style.height = '200px';
            img.style.objectFit = 'cover';
            img.alt = `预览图片 ${index + 1}`;
            
            const cardBody = document.createElement('div');
            cardBody.className = 'card-body';
            
            const removeBtn = document.createElement('button');
            removeBtn.className = 'btn btn-danger btn-sm w-100';
            removeBtn.innerHTML = '<i class="fas fa-trash-alt me-2"></i>删除';
            removeBtn.onclick = () => removeImage(index);
            
            cardBody.appendChild(removeBtn);
            card.appendChild(img);
            card.appendChild(cardBody);
            col.appendChild(card);
            previewContainer.appendChild(col);
        });
    }
}

// 更新文档列表
function updateDocumentList() {
    const container = document.getElementById('documentList');
    if (!container) return;

    container.innerHTML = '';
    
    if (!window.uploadedDocuments || window.uploadedDocuments.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">暂无文档</div>';
        return;
    }

    window.uploadedDocuments.forEach((docUrl, index) => {
        const div = document.createElement('div');
        div.className = 'mb-2 p-2 border rounded';
        div.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-file me-2"></i>
                <span class="flex-grow-1">${docUrl.split('/').pop()}</span>
                <button class="btn btn-sm btn-danger" 
                        onclick="removeDocument(${index})">
                    删除
                </button>
            </div>
        `;
        container.appendChild(div);
    });
}

function removeImage(index) {
    console.log('移除图片:', index);
    if (index >= 0 && index < window.uploadedImages.length) {
        window.uploadedImages.splice(index, 1);
        console.log('移除后的图片数组:', window.uploadedImages);
        updateImagePreview();
    }
}

function removeDocument(index) {
    if (index >= 0 && index < window.uploadedDocuments.length) {
        window.uploadedDocuments.splice(index, 1);
        updateDocumentList();
    }
}

function showError(message) {
    console.error(message);
    if (errorModal && errorMessageElement) {
        errorMessageElement.textContent = message;
        errorModal.show();
    } else {
        // 如果没有错误模态框，使用 alert
        alert(message);
    }
}

// 草稿保存和加载
function saveDraft() {
    const formData = new FormData(form);
    const draft = {
        data: Object.fromEntries(formData),
        images: uploadedImages,
        documents: uploadedDocuments,
        timestamp: Date.now()
    };
    localStorage.setItem(CONFIG.DRAFT.KEY, JSON.stringify(draft));
    showToast('草稿已保存');
}

function loadDraft() {
    try {
        const draft = JSON.parse(localStorage.getItem(CONFIG.DRAFT.KEY));
        if (!draft || !draft.data) return;
        
        // 填充表单数据
        Object.entries(draft.data).forEach(([key, value]) => {
            const input = form.elements[key];
            if (input) {
                input.value = value;
                input.removeAttribute('readonly'); // 移除只读属性
            }
        });
        
        // 加载图片和文档
        uploadedImages = draft.images || [];
        uploadedDocuments = draft.documents || [];
        updateImagePreview();
        updateDocumentList();
        
        // 触发计算
        calculateTokenPrice();
        
        draftInfo.style.display = 'none';
    } catch (error) {
        console.error('加载草稿失败:', error);
        localStorage.removeItem(CONFIG.DRAFT.KEY);
    }
}

function checkDraft() {
    // 暂时禁用草稿检查功能
    return;
}

// 表单验证增强
function validateForm() {
    const type = document.getElementById('type').value;
    const requiredFields = {
        common: ['name', 'description', 'tokensymbol'],
        '10': ['area', 'total_value'],
        '20': ['token_supply', 'total_value_similar']
    };
    
    // 验证必填字段
    const fieldsToValidate = [...requiredFields.common, ...requiredFields[type]];
    for (const field of fieldsToValidate) {
        const element = document.getElementById(field);
        if (!element || !element.value.trim()) {
            showError(`请填写${getFieldLabel(field)}`);
            return false;
        }
        
        // 特别检查代币符号
        if (field === 'tokensymbol' && element.value.trim().length === 0) {
            showError('代币代码不能为空');
            return false;
        }
    }
    
    return true;
}

// 获取字段标签
function getFieldLabel(field) {
    const labels = {
        'name': '资产名称',
        'description': '资产描述',
        'tokensymbol': '代币代码',
        'area': '资产面积',
        'total_value': '总价值',
        'total_value_similar': '总价值',
        'token_supply': '代币数量',
        'annual_revenue': '预期年收益'
    };
    return labels[field] || field;
}

// 修改表单提交处理
async function submitForm() {
    try {
        if (!validateForm()) {
            return;
        }

        // 检查钱包连接状态
        if (!window.ethereum || !window.walletState.getConnectionStatus()) {
            showError('请先连接钱包');
            return;
        }

        const formData = new FormData();
        
        // 添加创建者地址
        formData.append('creator_address', window.walletState.getAddress());
        
        // 添加基本字段
        formData.append('name', document.getElementById('name').value);
        formData.append('type', document.getElementById('type').value);
        formData.append('location', document.getElementById('location').value);
        formData.append('description', document.getElementById('description').value);
        formData.append('token_symbol', document.getElementById('tokensymbol').value);
        
        // 根据资产类型添加特定字段
        const assetType = document.getElementById('type').value;
        console.log('资产类型:', assetType);  // 添加日志

        if (assetType === '10') {  // 不动产
            const area = document.getElementById('area').value;
            const totalValue = document.getElementById('total_value').value;
            const annualRevenue = document.getElementById('annual_revenue').value;
            console.log('不动产字段:', { area, totalValue, annualRevenue });  // 添加日志

            formData.append('area', area);
            formData.append('total_value', totalValue);
            formData.append('annual_revenue', annualRevenue);
            formData.append('token_supply', document.getElementById('token_count').textContent.replace(/,/g, ''));
            formData.append('token_price', document.getElementById('token_price').textContent);
        } else {  // 类不动产
            const tokenSupply = document.getElementById('token_supply').value;
            const totalValue = document.getElementById('total_value_similar').value;
            const annualRevenue = document.getElementById('expectedAnnualRevenueSimilar').value;
            console.log('类不动产字段:', { tokenSupply, totalValue, annualRevenue });  // 添加日志

            formData.append('token_supply', tokenSupply);
            formData.append('total_value', totalValue);
            formData.append('annual_revenue', annualRevenue);
            formData.append('token_price', document.getElementById('calculatedTokenPriceSimilar').textContent);
        }

        // 添加图片和文档路径
        if (window.uploadedImages && window.uploadedImages.length > 0) {
            window.uploadedImages.forEach(url => {
                formData.append('images[]', url);
            });
            console.log('添加图片路径:', window.uploadedImages);
        }

        if (window.uploadedDocuments && window.uploadedDocuments.length > 0) {
            window.uploadedDocuments.forEach(url => {
                formData.append('documents[]', url);
            });
            console.log('添加文档路径:', window.uploadedDocuments);
        }

        // 打印所有表单数据
        console.log('表单数据:');
        for (let pair of formData.entries()) {
            console.log(pair[0] + ': ' + pair[1]);
        }

        // 发送请求
        const response = await fetch('/api/assets/create', {
            method: 'POST',
            headers: {
                'X-Eth-Address': window.walletState.getAddress()
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '创建资产失败');
        }

        const result = await response.json();
        console.log('Asset creation successful:', result);
        showToast('资产创建成功');
        
        // 清除草稿
        localStorage.removeItem('assetDraft');
        
        // 跳转到资产详情页
        setTimeout(() => {
            window.location.href = `/assets/${result.assetId}`;
        }, 1500);
        
    } catch (error) {
        console.error('Failed to submit form:', error);
        showError(error.message);
    }
}

// 连接钱包
async function connectWallet(event) {
    if (event) {
        event.preventDefault();
    }

    try {
        if (!window.ethereum) {
            throw new Error('请安装MetaMask钱包');
        }

        await window.walletState.connect();
    } catch (error) {
        console.error('Failed to connect wallet:', error);
        showError(error.message);
    }
}

// 生成代币代码
async function generateTokenSymbol(type, retryCount = 0) {
    try {
        // 检查 tokenSymbolInput 是否存在
        if (!tokenSymbolInput) {
            console.error('Token symbol input element not found in global variable');
            throw new Error('代币代码输入框未找到');
        }

        // 最大重试5次
        if (retryCount >= 5) {
            throw new Error('无法生成唯一的代币代码，请稍后重试');
        }

        // 使用更复杂的随机数生成方式
        const now = new Date();
        const timestamp = now.getTime();
        const random = Math.floor(Math.random() * 10000);
        
        // 使用时间戳的最后4位数字
        const timestampLast4 = timestamp % 10000;
        
        // 组合代币符号
        const prefix = type === CONFIG.ASSET_TYPE.REAL_ESTATE ? 'RH-10' : 'RH-20';
        const symbol = `${prefix}${timestampLast4.toString().padStart(4, '0')}`;
        
        console.log(`尝试生成代币代码: ${symbol}, 重试次数: ${retryCount}`);
        
        try {
            // 验证符号是否已存在
            const response = await fetch(`/api/check_token_symbol?symbol=${symbol}`);
            if (!response.ok) {
                throw new Error(`API请求失败: ${response.status}`);
            }
            
            const data = await response.json();
            
            // 如果响应包含错误信息
            if (data.error) {
                console.error('验证代币代码失败:', data.error);
                throw new Error(data.error);
            }
            
            // 如果代币已存在，立即重试
            if (data.exists) {
                console.log(`代币代码 ${symbol} 已存在，准备重试`);
                await new Promise(resolve => setTimeout(resolve, 100)); // 短暂延迟
                return generateTokenSymbol(type, retryCount + 1);
            }
            
            console.log(`成功生成代币代码: ${symbol}`);
            return symbol;
            
        } catch (error) {
            console.error('验证代币代码时出错:', error);
            throw new Error(`验证代币代码失败: ${error.message}`);
        }
        
    } catch (error) {
        console.error('生成代币代码失败:', error);
        throw error;
    }
}

// 计算类不动产代币价格
function calculateSimilarAssetsTokenPrice() {
    const tokenSupplyInput = document.getElementById('token_supply');
    const totalValueInput = document.getElementById('total_value_similar');
    const tokenPriceElement = document.getElementById('calculatedTokenPriceSimilar');
    
    if (!tokenPriceElement || !tokenSupplyInput || !totalValueInput) {
        console.warn('类不动产计算元素未找到');
        return;
    }
    
    const tokenCount = parseInt(tokenSupplyInput.value) || 0;
    const totalValue = parseFloat(totalValueInput.value) || 0;
    
    if (tokenCount <= 0) {
        tokenPriceElement.textContent = '0.000000';
        return;
    }
    
    if (totalValue > 0 && tokenCount > 0) {
        const price = totalValue / tokenCount;
        // 确保价格至少为0.000001
        const minPrice = Math.max(price, 0.000001);
        tokenPriceElement.textContent = formatNumber(minPrice, CONFIG.CALCULATION.PRICE_DECIMALS);
    } else {
        tokenPriceElement.textContent = '0.000000';
    }
}

// 辅助函数
async function dataURLtoBlob(dataURL) {
    try {
        // 如果是文件对象，直接返回
        if (dataURL instanceof File || dataURL instanceof Blob) {
            return dataURL;
        }
        
        // 如果是URL字符串，不需要转换
        if (typeof dataURL === 'string' && (dataURL.startsWith('http://') || dataURL.startsWith('https://'))) {
            return null;
        }
        
        // 处理 base64 数据URL
        if (typeof dataURL === 'string' && dataURL.startsWith('data:')) {
            const arr = dataURL.split(',');
            if (arr.length !== 2) {
                throw new Error('无效的数据URL格式');
            }
            
            const mimeMatch = arr[0].match(/:(.*?);/);
            if (!mimeMatch) {
                throw new Error('无法解析MIME类型');
            }
            
            const mime = mimeMatch[1];
            const bstr = atob(arr[1]);
            let n = bstr.length;
            const u8arr = new Uint8Array(n);
            
            while (n--) {
                u8arr[n] = bstr.charCodeAt(n);
            }
            
            return new Blob([u8arr], { type: mime });
        }
        
        throw new Error('不支持的数据格式');
    } catch (error) {
        console.error('转换数据URL到Blob失败:', error);
        throw new Error('文件格式转换失败');
    }
}

// 工具函数
function showToast(message) {
    // 实现一个简单的提示框
    const toast = document.createElement('div');
    toast.className = 'toast position-fixed bottom-0 end-0 m-3';
    toast.innerHTML = `
        <div class="toast-body">
            ${message}
        </div>
    `;
    document.body.appendChild(toast);
    new bootstrap.Toast(toast).show();
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// 更新文档要求显示
function updateDocumentRequirements(type) {
    const realEstateDocs = document.querySelector('.real-estate-docs');
    const similarAssetsDocs = document.querySelector('.similar-assets-docs');
    
    if (type === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        realEstateDocs.style.display = 'block';
        similarAssetsDocs.style.display = 'none';
    } else if (type === CONFIG.ASSET_TYPE.SIMILAR_ASSETS) {
        realEstateDocs.style.display = 'none';
        similarAssetsDocs.style.display = 'block';
    }
}

// 更新资产类型显示
function updateAssetTypeDisplay() {
    const type = document.getElementById('type').value;
    const realEstateFields = document.querySelectorAll('.real-estate');
    const similarAssetsFields = document.querySelectorAll('.similar-assets');

    if (type === '10') {
        realEstateFields.forEach(field => field.classList.remove('hidden'));
        similarAssetsFields.forEach(field => field.classList.add('hidden'));
    } else if (type === '20') {
        realEstateFields.forEach(field => field.classList.add('hidden'));
        similarAssetsFields.forEach(field => field.classList.remove('hidden'));
    }

    // 更新文档要求显示
    updateDocumentRequirements(type);
}

// 预览功能实现
function previewAsset() {
    try {
        if (!validateForm()) {
            return;
        }

        // 获取表单数据
        const formData = new FormData(document.getElementById('assetForm'));
        const assetType = formData.get('type');
        
        // 构建资产数据对象
        const assetData = {
            name: formData.get('name'),
            type: assetType,
            location: formData.get('location'),
            description: formData.get('description'),
            tokenSymbol: formData.get('tokensymbol'),
            images: window.uploadedImages || [],
            documents: window.uploadedDocuments || []
        };

        // 根据资产类型添加特定字段
        if (assetType === '10') { // 不动产
            assetData.area = formData.get('area');
            assetData.totalValue = formData.get('total_value');
            const tokenCountText = document.getElementById('token_count').textContent.replace(/,/g, '');
            assetData.tokenSupply = tokenCountText;
            assetData.tokenPrice = document.getElementById('token_price').textContent;
            assetData.annualRevenue = formData.get('annual_revenue');
        } else { // 类不动产
            assetData.tokenSupply = formData.get('token_supply');
            assetData.totalValue = formData.get('total_value_similar');
            assetData.tokenPrice = document.getElementById('calculatedTokenPriceSimilar').textContent;
            assetData.annualRevenue = formData.get('expectedAnnualRevenueSimilar');
        }

        console.log('Preview data:', assetData);

        // 创建预览内容
        const previewContent = `
            <div class="container-fluid">
                <!-- Image Carousel -->
                ${assetData.images && assetData.images.length > 0 ? `
                    <div id="previewCarousel" class="carousel slide mb-4" data-bs-ride="carousel">
                        <div class="carousel-indicators">
                            ${assetData.images.map((_, index) => `
                                <button type="button" data-bs-target="#previewCarousel" data-bs-slide-to="${index}" ${index === 0 ? 'class="active"' : ''}></button>
                            `).join('')}
                        </div>
                        <div class="carousel-inner">
                            ${assetData.images.map((imageUrl, index) => `
                                <div class="carousel-item ${index === 0 ? 'active' : ''}">
                                    <img src="${imageUrl}" class="d-block w-100" alt="Asset Image" style="height: 300px; object-fit: cover;">
                                </div>
                            `).join('')}
                        </div>
                        ${assetData.images.length > 1 ? `
                            <button class="carousel-control-prev" type="button" data-bs-target="#previewCarousel" data-bs-slide="prev">
                                <span class="carousel-control-prev-icon"></span>
                            </button>
                            <button class="carousel-control-next" type="button" data-bs-target="#previewCarousel" data-bs-slide="next">
                                <span class="carousel-control-next-icon"></span>
                            </button>
                        ` : ''}
                    </div>
                ` : '<div class="text-center p-4 bg-light mb-4"><i class="fas fa-image fa-3x text-muted"></i><p class="mt-2">No Images</p></div>'}

                <!-- Asset Information -->
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title mb-4">${assetData.name}</h5>
                                
                                <div class="row g-3">
                                    <!-- Basic Information -->
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">Asset Type</small>
                                            <h6 class="mb-0">${assetData.type === '10' ? 'Real Estate' : 'Similar Assets'}</h6>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">Location</small>
                                            <h6 class="mb-0">${assetData.location}</h6>
                                        </div>
                                    </div>

                                    <!-- Asset Specific Information -->
                                    ${assetData.type === '10' ? `
                                        <div class="col-md-6">
                                            <div class="bg-light rounded p-3">
                                                <small class="text-muted d-block mb-1">Area</small>
                                                <h6 class="mb-0">${assetData.area} m²</h6>
                                            </div>
                                        </div>
                                    ` : ''}
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">Total Value</small>
                                            <h6 class="mb-0">${assetData.totalValue} USDC</h6>
                                        </div>
                                    </div>
                                    
                                    <!-- Token Information -->
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">Token Symbol</small>
                                            <h6 class="mb-0">${assetData.tokenSymbol}</h6>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">Token Supply</small>
                                            <h6 class="mb-0">${assetData.tokenSupply}</h6>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">Token Price</small>
                                            <h6 class="mb-0">${assetData.tokenPrice} USDC</h6>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">Expected Annual Revenue</small>
                                            <h6 class="mb-0">${assetData.annualRevenue} USDC</h6>
                                        </div>
                                    </div>
                                </div>

                                <!-- Asset Description -->
                                <div class="mt-4">
                                    <h6 class="text-muted mb-2">Description</h6>
                                    <p class="mb-0">${assetData.description}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 创建预览模态框
        const previewModal = document.createElement('div');
        previewModal.className = 'modal fade';
        previewModal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Asset Preview</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        ${previewContent}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" onclick="submitPreview(event)">Submit</button>
                    </div>
                </div>
            </div>
        `;

        // 添加到页面
        document.body.appendChild(previewModal);
        const modal = new bootstrap.Modal(previewModal);
        modal.show();

        // 初始化轮播
        if (assetData.images && assetData.images.length > 0) {
            setTimeout(() => {
                const carousel = new bootstrap.Carousel(document.getElementById('previewCarousel'), {
                    interval: 5000,
                    wrap: true,
                    keyboard: true
                });
            }, 100);
        }
    } catch (error) {
        console.error('Failed to preview asset:', error);
        showError('Failed to preview asset, please try again');
    }
}

// 提交预览
function submitPreview(event) {
    event.preventDefault(); // 阻止默认行为
    const previewModal = document.querySelector('.modal.fade');
    if (previewModal) {
        previewModal.classList.remove('show');
        previewModal.classList.add('d-none');
        setTimeout(() => {
            previewModal.remove();
        }, 300);
    }
    // 提交表单
    submitForm();
}