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
        await initializeFormElements();
        await initializeEventListeners();
        console.log('Form initialization completed');
    } catch (error) {
        console.error('Form initialization failed:', error);
        showError('页面初始化失败，请刷新重试');
    }
});

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
        // 检查文件参数
        if (!file || !(file instanceof File)) {
            throw new Error('无效的文件对象');
        }

        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                try {
                    if (!e.target || !e.target.result) {
                        reject(new Error('读取文件失败'));
                        return;
                    }

                    const img = new Image();
                    img.crossOrigin = "Anonymous";
                    
                    img.onload = () => {
                        try {
                            const canvas = document.createElement('canvas');
                            let width = img.width;
                            let height = img.height;
                            
                            // 优化缩放比例计算
                            const maxWidth = CONFIG.IMAGE.COMPRESS.MAX_WIDTH;
                            const maxHeight = CONFIG.IMAGE.COMPRESS.MAX_HEIGHT;
                            const ratio = Math.min(maxWidth / width, maxHeight / height, 1);
                            
                            width = Math.floor(width * ratio);
                            height = Math.floor(height * ratio);
                            
                            canvas.width = width;
                            canvas.height = height;
                            
                            const ctx = canvas.getContext('2d');
                            if (!ctx) {
                                reject(new Error('无法创建Canvas上下文'));
                                return;
                            }
                            
                            // 设置白色背景
                            ctx.fillStyle = '#FFFFFF';
                            ctx.fillRect(0, 0, width, height);
                            
                            // 使用更好的图像平滑算法
                            ctx.imageSmoothingEnabled = true;
                            ctx.imageSmoothingQuality = 'high';
                            
                            // 绘制图片
                            ctx.drawImage(img, 0, 0, width, height);
                            
                            // 转换为blob
                            canvas.toBlob(
                                (blob) => {
                                    if (blob) {
                                        // 创建新的 File 对象，保留原始文件名
                                        const compressedFile = new File([blob], file.name, {
                                            type: 'image/jpeg',
                                            lastModified: new Date().getTime()
                                        });
                                        resolve(compressedFile);
                                    } else {
                                        reject(new Error('转换为Blob失败'));
                                    }
                                },
                                'image/jpeg',
                                CONFIG.IMAGE.COMPRESS.QUALITY
                            );
                            
                        } catch (error) {
                            console.error('Canvas处理图片失败:', error);
                            reject(error);
                        }
                    };
                    
                    img.onerror = (error) => {
                        console.error('图片加载失败:', error);
                        reject(new Error('图片加载失败'));
                    };
                    
                    img.src = e.target.result;
                } catch (error) {
                    console.error('创建图片对象失败:', error);
                    reject(error);
                }
            };
            
            reader.onerror = (error) => {
                console.error('读取文件失败:', error);
                reject(new Error('读取文件失败'));
            };
            
            reader.readAsDataURL(file);
        });
    } catch (error) {
        console.error('压缩图片失败:', error);
        throw error;
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
        
        progressElement.style.display = 'block';
        
        // 初始化全局数组
        if (fileType === 'image') {
            if (!window.uploadedImages) window.uploadedImages = [];
        } else {
            if (!window.uploadedDocuments) window.uploadedDocuments = [];
        }

        const totalFiles = files.length;
        let completedFiles = 0;

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            
            // 如果是图片，先压缩
            let processedFile = file;
            if (fileType === 'image') {
                try {
                    processedFile = await compressImage(file);
                    console.log('图片压缩完成:', file.name);
                } catch (error) {
                    console.warn('图片压缩失败，使用原始文件:', error);
                }
            }
            
            formData.append('file', processedFile);
            formData.append('asset_type', document.getElementById('type').value);
            formData.append('file_type', fileType);

            try {
                // 使用 XMLHttpRequest 来获取上传进度
                const xhr = new XMLHttpRequest();
                
                // 处理单个文件的上传进度
                xhr.upload.onprogress = (event) => {
                    if (event.lengthComputable) {
                        const fileProgress = (event.loaded / event.total) * 100;
                        const totalProgress = ((completedFiles + fileProgress / 100) / totalFiles) * 100;
                        percentElement.textContent = Math.round(totalProgress);
                        progressElement.querySelector('.progress-bar').style.width = `${totalProgress}%`;
                    }
                };

                // 返回Promise以支持async/await
                const response = await new Promise((resolve, reject) => {
                    xhr.onload = () => {
                        if (xhr.status >= 200 && xhr.status < 300) {
                            try {
                                const result = JSON.parse(xhr.responseText);
                                resolve(result);
                            } catch (error) {
                                reject(new Error('解析响应失败'));
                            }
                        } else {
                            reject(new Error(`上传失败: ${xhr.statusText}`));
                        }
                    };
                    
                    xhr.onerror = () => reject(new Error('网络错误'));
                    
                    xhr.open('POST', '/api/upload', true);
                    xhr.setRequestHeader('X-Eth-Address', window.ethereum?.selectedAddress || '');
                    xhr.send(formData);
                });

                if (response && response.url) {
                    if (fileType === 'image') {
                        window.uploadedImages.push(response.url);
                        console.log('图片上传成功:', response.url);
                        updateImagePreview();
                    } else {
                        window.uploadedDocuments.push(response.url);
                        updateDocumentList();
                    }
                    completedFiles++;
                }
            } catch (error) {
                console.error('上传文件失败:', error);
                showError(`文件 ${file.name} 上传失败: ${error.message}`);
            }
        }

        // 上传完成后延迟隐藏进度条
        setTimeout(() => {
            progressElement.style.display = 'none';
            progressElement.querySelector('.progress-bar').style.width = '0%';
            percentElement.textContent = '0';
        }, 1000);

    } catch (error) {
        console.error('处理文件失败:', error);
        showError(error.message);
    }
}

// 更新图片预览
function updateImagePreview() {
    const container = document.getElementById('imagePreview');
    if (!container) return;

    container.innerHTML = '';
    console.log('更新图片预览，当前图片:', window.uploadedImages);
    
    if (!window.uploadedImages || window.uploadedImages.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">暂无图片</div>';
        return;
    }

    const row = document.createElement('div');
    row.className = 'row g-3';
    container.appendChild(row);

    window.uploadedImages.forEach((imageUrl, index) => {
        const col = document.createElement('div');
        col.className = 'col-md-4';
        col.innerHTML = `
            <div class="card h-100">
                <div class="position-relative">
                    <img src="${imageUrl}" 
                         class="card-img-top" 
                         alt="上传的图片"
                         style="height: 200px; object-fit: cover;">
                    <button class="btn btn-sm btn-danger position-absolute top-0 end-0 m-2" 
                            onclick="removeImage(${index})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
        row.appendChild(col);
    });
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

        const formData = new FormData();
        
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

        // 打印所有表单数据
        console.log('表单数据:');
        for (let pair of formData.entries()) {
            console.log(pair[0] + ': ' + pair[1]);
        }

        // 发送请求
        const response = await fetch('/api/assets/create', {
            method: 'POST',
            headers: {
                'X-Eth-Address': window.ethereum?.selectedAddress || ''
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '创建资产失败');
        }

        const result = await response.json();
        console.log('创建资产成功:', result);  // 添加日志
        showToast('资产创建成功');
        
        // 清除草稿
        localStorage.removeItem('assetDraft');
        
        // 跳转到资产列表页
        setTimeout(() => {
            window.location.href = '/assets';
        }, 1500);
        
    } catch (error) {
        console.error('提交表单失败:', error);
        showError(error.message);
    }
}

// 事件监听器
document.addEventListener('DOMContentLoaded', async function() {
    // 检查钱包连接状态
    if (!window.ethereum || !window.ethereum.selectedAddress) {
        // 显示连接钱包提示
        const formContent = document.getElementById('assetForm');
        if (formContent) {
            formContent.style.display = 'none';
            
            const walletPrompt = document.createElement('div');
            walletPrompt.className = 'wallet-prompt container text-center py-5';
            walletPrompt.innerHTML = `
                <div class="card shadow-sm">
                    <div class="card-body py-5">
                        <i class="fas fa-wallet fa-3x text-muted mb-3"></i>
                        <h3 class="mb-3">请先连接钱包</h3>
                        <p class="text-muted mb-4">您需要连接MetaMask钱包才能创建资产</p>
                        <button class="btn btn-primary" onclick="connectWallet(event)">
                            <i class="fas fa-plug me-2"></i>连接钱包
                        </button>
                    </div>
                </div>
            `;
            
            formContent.parentNode.insertBefore(walletPrompt, formContent);
        }
    } else {
        // 如果已连接钱包，显示表单并初始化
        const formContent = document.getElementById('assetForm');
        if (formContent) {
            formContent.style.display = 'block';
        }
        const walletPrompt = document.querySelector('.wallet-prompt');
        if (walletPrompt) {
            walletPrompt.style.display = 'none';
        }
        initializeFormElements();
    }

    // 监听钱包状态变化
    window.ethereum.on('accountsChanged', function(accounts) {
        if (accounts.length > 0) {
            const formContent = document.getElementById('assetForm');
            const walletPrompt = document.querySelector('.wallet-prompt');
            if (formContent) {
                formContent.style.display = 'block';
            }
            if (walletPrompt) {
                walletPrompt.style.display = 'none';
            }
            initializeFormElements();
        } else {
            const formContent = document.getElementById('assetForm');
            if (formContent) {
                formContent.style.display = 'none';
            }
            const walletPrompt = document.querySelector('.wallet-prompt');
            if (walletPrompt) {
                walletPrompt.style.display = 'block';
            }
        }
    });
});

// 添加新的钱包连接函数
async function connectWallet(event) {
    event.preventDefault(); // 阻止默认行为
    if (window.ethereum) {
        try {
            await window.ethereum.request({ method: 'eth_requestAccounts' });
            location.reload(); // 连接成功后刷新页面
        } catch (error) {
            console.error('连接钱包失败:', error);
            showError('连接钱包失败，请重试');
        }
    } else {
        showError('请安装MetaMask钱包');
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
            images: window.uploadedImages || [],  // 使用全局变量中的图片数组
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
            assetData.totalValue = formData.get('total_value');
            assetData.tokenPrice = document.getElementById('calculatedTokenPriceSimilar').textContent;
            assetData.annualRevenue = formData.get('annual_revenue');
        }

        console.log('预览数据:', assetData); // 添加日志

        // 创建预览内容
        const previewContent = `
            <div class="container-fluid">
                <!-- 图片轮播 -->
                ${assetData.images && assetData.images.length > 0 ? `
                    <div id="previewCarousel" class="carousel slide mb-4" data-bs-ride="carousel">
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
                ` : '<div class="text-center p-4 bg-light mb-4"><i class="fas fa-image fa-3x text-muted"></i><p class="mt-2">暂无图片</p></div>'}

                <!-- 资产信息 -->
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title mb-4">${assetData.name}</h5>
                                
                                <div class="row g-3">
                                    <!-- 基本信息 -->
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">资产类型</small>
                                            <h6 class="mb-0">${assetData.type === '10' ? '不动产' : '类不动产'}</h6>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">位置</small>
                                            <h6 class="mb-0">${assetData.location}</h6>
                                        </div>
                                    </div>

                                    <!-- 资产特定信息 -->
                                    ${assetData.type === '10' ? `
                                        <div class="col-md-6">
                                            <div class="bg-light rounded p-3">
                                                <small class="text-muted d-block mb-1">面积</small>
                                                <h6 class="mb-0">${assetData.area} ㎡</h6>
                                            </div>
                                        </div>
                                    ` : `
                                        <div class="col-md-6">
                                            <div class="bg-light rounded p-3">
                                                <small class="text-muted d-block mb-1">总价值</small>
                                                <h6 class="mb-0">${assetData.totalValue} USDC</h6>
                                            </div>
                                        </div>
                                    `}
                                    
                                    <!-- 代币信息 -->
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">代币代码</small>
                                            <h6 class="mb-0">${assetData.tokenSymbol}</h6>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">代币数量</small>
                                            <h6 class="mb-0">${assetData.tokenSupply}</h6>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">代币价格</small>
                                            <h6 class="mb-0">${assetData.tokenPrice} USDC</h6>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="bg-light rounded p-3">
                                            <small class="text-muted d-block mb-1">预期年收益</small>
                                            <h6 class="mb-0">${assetData.annualRevenue} USDC</h6>
                                        </div>
                                    </div>
                                </div>

                                <!-- 资产描述 -->
                                <div class="mt-4">
                                    <h6 class="text-muted mb-2">资产描述</h6>
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
                        <h5 class="modal-title">资产预览</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        ${previewContent}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        <button type="button" class="btn btn-primary" onclick="submitPreview(event)">提交</button>
                    </div>
                </div>
            </div>
        `;

        // 添加到页面
        document.body.appendChild(previewModal);
        new bootstrap.Modal(previewModal).show();
    } catch (error) {
        console.error('预览资产失败:', error);
        showError('预览资产失败，请稍后重试');
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