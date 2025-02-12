// 配置常量
const CONFIG = {
    IMAGE: {
        MAX_FILES: 5,
        MAX_SIZE: 5 * 1024 * 1024, // 5MB
        ALLOWED_TYPES: ['image/jpeg', 'image/png'],
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

// 表单元素
const form = document.getElementById('assetForm');
const nameInput = document.getElementById('name');
const typeInput = document.getElementById('type');
const locationInput = document.getElementById('location');
const descriptionInput = document.getElementById('description');
const areaInput = document.getElementById('area');
const totalValueInput = document.getElementById('totalValue');
const tokenCountInput = document.getElementById('tokenCount');
const expectedAnnualRevenueInput = document.getElementById('expectedAnnualRevenue');
const imageDropzone = document.getElementById('imageDropzone');
const documentDropzone = document.getElementById('documentDropzone');

// 计算结果元素
const calculatedElements = {
    realEstate: {
        tokenCount: document.getElementById('calculatedTokenCount'),
        tokenPrice: document.getElementById('calculatedTokenPrice')
    },
    similarAssets: {
        tokenPrice: document.getElementById('calculatedTokenPriceSimilar')
    }
};

// 错误提示模态框
const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
const errorMessageElement = document.getElementById('errorMessage');

// 文件上传相关变量
let uploadedImages = [];
let uploadedDocuments = [];

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

// 切换资产类型显示
function toggleAssetTypeFields(type) {
    const elements = {
        realEstate: document.querySelectorAll('.asset-type-field.real-estate'),
        similarAssets: document.querySelectorAll('.asset-type-field.similar-assets'),
        realEstateDocs: document.querySelectorAll('.real-estate-docs'),
        similarAssetsDocs: document.querySelectorAll('.similar-assets-docs'),
        realEstateInfo: document.querySelector('.real-estate-info')
    };

    // 安全地切换元素类
    function toggleElementClasses(elementList, shouldShow) {
        elementList.forEach(element => {
            if (element) {
                if (shouldShow) {
                    element.classList.remove('hidden');
                } else {
                    element.classList.add('hidden');
                }
            }
        });
    }

    if (type === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        // 显示不动产相关元素
        toggleElementClasses(elements.realEstate, true);
        toggleElementClasses(elements.similarAssets, false);
        toggleElementClasses(elements.realEstateDocs, true);
        toggleElementClasses(elements.similarAssetsDocs, false);
        
        // 设置必填字段
        elements.realEstate.forEach(field => {
            if (field) {
                field.querySelectorAll('input, select, textarea').forEach(input => {
                    input.required = true;
                });
            }
        });

        // 清空类不动产字段
        elements.similarAssets.forEach(field => {
            if (field) {
                field.querySelectorAll('input, select, textarea').forEach(input => {
                    input.required = false;
                    input.value = '';
                });
            }
        });

        if (elements.realEstateInfo) {
            elements.realEstateInfo.classList.remove('hidden');
        }
        calculateRealEstateTokens();
    } else if (type === CONFIG.ASSET_TYPE.SIMILAR_ASSETS) {
        // 显示类不动产相关元素
        toggleElementClasses(elements.realEstate, false);
        toggleElementClasses(elements.similarAssets, true);
        toggleElementClasses(elements.realEstateDocs, false);
        toggleElementClasses(elements.similarAssetsDocs, true);

        // 设置必填字段
        elements.similarAssets.forEach(field => {
            if (field) {
                field.querySelectorAll('input, select, textarea').forEach(input => {
                    input.required = true;
                });
            }
        });

        // 清空不动产字段
        elements.realEstate.forEach(field => {
            if (field) {
                field.querySelectorAll('input, select, textarea').forEach(input => {
                    input.required = false;
                    input.value = '';
                });
            }
        });

        if (elements.realEstateInfo) {
            elements.realEstateInfo.classList.add('hidden');
        }
    }

    // 重置计算结果
    resetCalculations();
    
    // 更新文档要求显示
    updateDocumentRequirements(type);
}

// 重置计算结果
function resetCalculations() {
    calculatedElements.realEstate.tokenCount.textContent = '0';
    calculatedElements.realEstate.tokenPrice.textContent = '0.000000';
    calculatedElements.similarAssets.tokenPrice.textContent = '0.000000';
}

// 计算代币数量（不动产）
function calculateRealEstateTokens() {
    const area = parseFloat(areaInput.value) || 0;
    if (area > 0) {
        const tokenCount = Math.floor(area * CONFIG.CALCULATION.TOKENS_PER_SQUARE_METER);
        calculatedElements.realEstate.tokenCount.textContent = formatNumber(tokenCount);
        return tokenCount;
    }
    calculatedElements.realEstate.tokenCount.textContent = '0';
    return 0;
}

// 计算代币价格
function calculateTokenPrice() {
    const totalValue = parseFloat(totalValueInput.value) || 0;
    let tokenCount = 0;
    
    if (typeInput.value === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        tokenCount = calculateRealEstateTokens();
        if (totalValue > 0 && tokenCount > 0) {
            const tokenPrice = totalValue / tokenCount;
            const formattedPrice = formatNumber(tokenPrice, CONFIG.CALCULATION.PRICE_DECIMALS);
            calculatedElements.realEstate.tokenPrice.textContent = formattedPrice;
            calculatedElements.realEstate.tokenCount.textContent = formatNumber(tokenCount);
        } else {
            calculatedElements.realEstate.tokenPrice.textContent = '0.000000';
            calculatedElements.realEstate.tokenCount.textContent = '0';
        }
    } else {
        tokenCount = parseInt(tokenCountInput.value) || 0;
        if (totalValue > 0 && tokenCount > 0) {
            const tokenPrice = totalValue / tokenCount;
            const formattedPrice = formatNumber(tokenPrice, CONFIG.CALCULATION.PRICE_DECIMALS);
            calculatedElements.similarAssets.tokenPrice.textContent = formattedPrice;
        } else {
            calculatedElements.similarAssets.tokenPrice.textContent = '0.000000';
        }
    }
}

// 图片压缩函数
async function compressImage(file) {
    try {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
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
                            
                            // 转换为jpeg格式，使用更优的压缩质量
                            const dataURL = canvas.toDataURL('image/jpeg', CONFIG.IMAGE.COMPRESS.QUALITY);
                            resolve(dataURL);
                            
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
        return ['文件验证失败'];
    }
    
    const config = CONFIG[type.toUpperCase()];
    const errors = [];
    
    // 检查文件数量
    if (files.length > config.MAX_FILES) {
        errors.push(`最多只能上传${config.MAX_FILES}个文件`);
        return errors;
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
    
    return errors;
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

// 处理文件函数
async function handleFiles(files, type) {
    const fileType = type.toUpperCase();
    
    try {
        if (!files || files.length === 0) {
            console.error('没有选择文件');
            return;
        }
        
        // 验证文件
        const errors = validateFiles(files, fileType);
        if (errors.length > 0) {
            showError(errors.join('\n'));
            return;
        }
        
        // 检查已上传文件数量
        const currentFiles = fileType === 'IMAGE' ? uploadedImages : uploadedDocuments;
        const maxFiles = CONFIG[fileType].MAX_FILES;
        
        if (currentFiles.length + files.length > maxFiles) {
            showError(`最多只能上传${maxFiles}个文件`);
            return;
        }
        
        // 显示进度条
        const totalSize = Array.from(files).reduce((sum, file) => sum + file.size, 0);
        let loadedSize = 0;
        showProgress(fileType, 0, totalSize);
        
        // 使用Promise.all并行处理文件
        const filePromises = Array.from(files).map(async (file) => {
            try {
                const fileData = {
                    name: file.name,
                    type: file.type,
                    size: file.size,
                    lastModified: file.lastModified
                };
                
                if (fileType === 'IMAGE') {
                    fileData.data = await compressImage(file);
                } else {
                    fileData.data = await new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onload = e => resolve(e.target.result);
                        reader.onerror = () => reject(new Error('读取文件失败'));
                        reader.readAsDataURL(file);
                    });
                }
                
                loadedSize += file.size;
                showProgress(fileType, loadedSize, totalSize);
                
                return fileData;
            } catch (error) {
                console.error(`处理文件失败: ${file.name}`, error);
                throw new Error(`处理文件 ${file.name} 失败: ${error.message || '未知错误'}`);
            }
        });
        
        const processedFiles = await Promise.all(filePromises);
        
        // 更新文件列表
        if (fileType === 'IMAGE') {
            uploadedImages.push(...processedFiles);
            updateImagePreview();
        } else {
            uploadedDocuments.push(...processedFiles);
            updateDocumentList();
        }
        
    } catch (error) {
        console.error('文件处理失败:', error);
        showError(error.message || '文件处理失败');
    }
}

// 更新图片预览
function updateImagePreview() {
    const previewContainer = document.getElementById('imagePreview');
    if (!previewContainer) return;
    
    previewContainer.innerHTML = '';
    
    if (uploadedImages.length === 0) {
        previewContainer.innerHTML = '<div class="text-center text-muted">暂无图片</div>';
        return;
    }
    
    uploadedImages.forEach((image, index) => {
        try {
            const div = document.createElement('div');
            div.className = 'col-md-4 mb-3';
            div.innerHTML = `
                <div class="position-relative">
                    <div class="image-container" style="height: 200px; overflow: hidden;">
                        <img src="${image.data}" 
                             class="img-thumbnail w-100 h-100" 
                             alt="${image.name}"
                             style="object-fit: cover;">
                    </div>
                    <div class="position-absolute top-0 end-0 m-1">
                        <button type="button" class="btn btn-danger btn-sm" 
                                onclick="removeImage(${index})">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="mt-1 small text-muted text-truncate">
                        ${image.name}
                    </div>
                </div>
            `;
            previewContainer.appendChild(div);
        } catch (error) {
            console.error(`预览图片失败: ${image.name}`, error);
            showError(`预览图片 ${image.name} 失败`);
        }
    });
}

// 更新文档列表
function updateDocumentList() {
    const listContainer = document.getElementById('documentList');
    if (!listContainer) return;
    
    listContainer.innerHTML = '';
    
    if (uploadedDocuments.length === 0) {
        listContainer.innerHTML = '<div class="text-center text-muted">暂无文档</div>';
        return;
    }
    
    uploadedDocuments.forEach((doc, index) => {
        const div = document.createElement('div');
        div.className = 'mb-2 p-2 border rounded';
        div.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-file-alt me-2"></i>
                <div class="flex-grow-1">
                    <div class="text-truncate">${doc.name}</div>
                    <small class="text-muted">${formatFileSize(doc.size)}</small>
                </div>
                <button type="button" class="btn btn-danger btn-sm ms-2" 
                        onclick="removeDocument(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        listContainer.appendChild(div);
    });
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function removeImage(index) {
    uploadedImages.splice(index, 1);
    updateImagePreview();
}

function removeDocument(index) {
    uploadedDocuments.splice(index, 1);
    updateDocumentList();
}

function showError(message) {
    errorMessageElement.textContent = message;
    errorModal.show();
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
            if (input) input.value = value;
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
    const errors = [];
    const type = typeInput.value;
    
    // 基本字段验证
    if (!form.checkValidity()) {
        errors.push('请填写所有必填字段');
    }
    
    // 不动产特有验证
    if (type === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        const area = parseFloat(areaInput.value) || 0;
        if (area <= 0) {
            errors.push('面积必须大于0');
        }
    }
    
    // 类不动产特有验证
    if (type === CONFIG.ASSET_TYPE.SIMILAR_ASSETS) {
        const tokenCount = parseInt(tokenCountInput.value) || 0;
        if (tokenCount <= 0) {
            errors.push('代币数量必须大于0');
        }
        if (tokenCount % 1 !== 0) {
            errors.push('代币数量必须是整数');
        }
    }
    
    // 通用验证
    const totalValue = parseFloat(totalValueInput.value) || 0;
    if (totalValue <= 0) {
        errors.push('总价值必须大于0');
    }
    
    return errors;
}

// 事件监听器
document.addEventListener('DOMContentLoaded', async function() {
    // 检查钱包连接状态
    if (!window.ethereum) {
        window.location.href = '/?error=' + encodeURIComponent('请先安装MetaMask钱包');
        return;
    }
    
    try {
        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
        if (!accounts || accounts.length === 0) {
            window.location.href = '/?error=' + encodeURIComponent('请先连接钱包');
            return;
        }
    } catch (error) {
        console.error('检查钱包连接失败:', error);
        window.location.href = '/?error=' + encodeURIComponent('钱包连接检查失败');
        return;
    }

    // 初始化表单元素
    initializeFormElements();
});

// 初始化表单元素
function initializeFormElements() {
    const formElements = {
        form: document.getElementById('assetForm'),
        nameInput: document.getElementById('name'),
        typeInput: document.getElementById('type'),
        locationInput: document.getElementById('location'),
        descriptionInput: document.getElementById('description'),
        areaInput: document.getElementById('area'),
        totalValueInput: document.getElementById('totalValue'),
        tokenCountInput: document.getElementById('tokenCount'),
        expectedAnnualRevenueInput: document.getElementById('expectedAnnualRevenue'),
        imageDropzone: document.getElementById('imageDropzone'),
        documentDropzone: document.getElementById('documentDropzone')
    };

    // 验证必要的表单元素是否存在
    const missingElements = Object.entries(formElements)
        .filter(([key, element]) => !element)
        .map(([key]) => key);

    if (missingElements.length > 0) {
        console.error('缺少必要的表单元素:', missingElements);
        showError('页面加载错误，请刷新重试');
        return;
    }

    // 初始化事件监听
    initializeEventListeners(formElements);
}

// 初始化事件监听
function initializeEventListeners(elements) {
    // 拖放区域事件
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        elements.imageDropzone.addEventListener(eventName, preventDefaults);
        elements.documentDropzone.addEventListener(eventName, preventDefaults);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // 高亮拖放区域
    ['dragenter', 'dragover'].forEach(eventName => {
        elements.imageDropzone.addEventListener(eventName, highlight);
        elements.documentDropzone.addEventListener(eventName, highlight);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        elements.imageDropzone.addEventListener(eventName, unhighlight);
        elements.documentDropzone.addEventListener(eventName, unhighlight);
    });
    
    function highlight(e) {
        e.target.classList.add('border-primary');
    }
    
    function unhighlight(e) {
        e.target.classList.remove('border-primary');
    }
    
    // 处理文件拖放
    elements.imageDropzone.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files, 'image');
    });
    
    elements.documentDropzone.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files, 'document');
    });
    
    // 处理文件选择
    document.getElementById('imageInput').addEventListener('change', e => {
        if (e.target.files && e.target.files.length > 0) {
            handleFiles(e.target.files, 'image');
            e.target.value = ''; // 清空input，允许重复选择相同文件
        }
    });
    
    document.getElementById('documentInput').addEventListener('change', e => {
        if (e.target.files && e.target.files.length > 0) {
            handleFiles(e.target.files, 'document');
            e.target.value = ''; // 清空input，允许重复选择相同文件
        }
    });
    
    // 点击拖放区域触发文件选择
    elements.imageDropzone.addEventListener('click', () => {
        document.getElementById('imageInput').click();
    });
    
    elements.documentDropzone.addEventListener('click', () => {
        document.getElementById('documentInput').click();
    });
    
    // 资产类型切换
    elements.typeInput.addEventListener('change', function() {
        const type = this.value;
        if (type) {
            toggleAssetTypeFields(type);
            calculateTokenPrice();
        }
    });
    
    // 不动产计算触发器
    elements.areaInput.addEventListener('input', function() {
        if (elements.typeInput.value === CONFIG.ASSET_TYPE.REAL_ESTATE) {
            calculateTokenPrice();
        }
    });
    
    // 类不动产计算触发器
    document.getElementById('totalValueSimilar').addEventListener('input', function() {
        calculateTokenPrice();
    });
    
    document.getElementById('tokenCount').addEventListener('input', function() {
        calculateTokenPrice();
    });
    
    // 总价值变化触发器
    elements.totalValueInput.addEventListener('input', function() {
        calculateTokenPrice();
    });
    
    // 注释掉草稿相关的事件监听
    // let autoSaveTimer = setInterval(saveDraft, CONFIG.DRAFT.AUTO_SAVE_INTERVAL);
    
    // 检查草稿
    // checkDraft();
    
    // 草稿按钮事件
    /*
    loadDraftBtn.addEventListener('click', loadDraft);
    discardDraftBtn.addEventListener('click', () => {
        localStorage.removeItem(CONFIG.DRAFT.KEY);
        draftInfo.style.display = 'none';
    });
    saveDraftBtn.addEventListener('click', () => {
        saveDraft();
        showToast('草稿已保存');
    });
    */
    
    // 表单提交增强
    elements.form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const errors = validateForm();
        if (errors.length > 0) {
            showError(errors.join('\n'));
            return;
        }
        
        const formData = new FormData();
        formData.append('name', elements.nameInput.value);
        formData.append('type', elements.typeInput.value);
        formData.append('location', elements.locationInput.value);
        formData.append('description', elements.descriptionInput.value);
        
        // 根据资产类型处理不同字段
        if (elements.typeInput.value === CONFIG.ASSET_TYPE.REAL_ESTATE) {
            formData.append('area', elements.areaInput.value);
            formData.append('totalValue', elements.totalValueInput.value);
            formData.append('tokenCount', calculatedElements.realEstate.tokenCount.textContent.replace(/,/g, ''));
            formData.append('tokenPrice', calculatedElements.realEstate.tokenPrice.textContent.replace(/,/g, ''));
            formData.append('expectedAnnualRevenue', elements.expectedAnnualRevenueInput.value);
        } else {
            formData.append('tokenCount', elements.tokenCountInput.value);
            formData.append('totalValue', document.getElementById('totalValueSimilar').value);
            formData.append('tokenPrice', calculatedElements.similarAssets.tokenPrice.textContent.replace(/,/g, ''));
            formData.append('expectedAnnualRevenue', document.getElementById('expectedAnnualRevenueSimilar').value);
        }
        
        try {
            // 添加图片
            if (uploadedImages.length > 0) {
                for (let i = 0; i < uploadedImages.length; i++) {
                    const image = uploadedImages[i];
                    try {
                        const blob = await dataURLtoBlob(image.data);
                        formData.append('images[]', blob, image.name);
                    } catch (error) {
                        console.error(`处理图片失败: ${image.name}`, error);
                        showError(`处理图片 ${image.name} 失败，请重新上传`);
                        return;
                    }
                }
            }
            
            // 添加文档
            if (uploadedDocuments.length > 0) {
                for (let i = 0; i < uploadedDocuments.length; i++) {
                    const doc = uploadedDocuments[i];
                    try {
                        const blob = await dataURLtoBlob(doc.data);
                        formData.append('documents[]', blob, doc.name);
                    } catch (error) {
                        console.error(`处理文档失败: ${doc.name}`, error);
                        showError(`处理文档 ${doc.name} 失败，请重新上传`);
                        return;
                    }
                }
            }
            
            // 发送请求
            const response = await fetch('/api/assets/create', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || '提交失败');
            }
            
            const result = await response.json();
            localStorage.removeItem(CONFIG.DRAFT.KEY);
            window.location.href = `/assets/${result.assetId}`;
            
        } catch (error) {
            console.error('提交表单失败:', error);
            showError(error.message || '提交失败，请稍后重试');
        }
    });
    
    // 更新资产类型显示
    toggleAssetTypeFields(elements.typeInput.value);

    // 在initializeEventListeners函数中添加预览按钮事件监听
    document.getElementById('previewForm').addEventListener('click', function(e) {
        e.preventDefault();
        const errors = validateForm();
        if (errors.length > 0) {
            showError(errors.join('\n'));
            return;
        }
        previewAsset();
    });
}

// 辅助函数
async function dataURLtoBlob(dataURL) {
    try {
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
    } catch (error) {
        console.error('转换dataURL到Blob失败:', error);
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
    const type = typeInput.value;
    const realEstateFields = document.querySelectorAll('.asset-type-field.real-estate');
    const similarAssetsFields = document.querySelectorAll('.asset-type-field.similar-assets');
    
    // 生成并显示代币代码
    const tokenSymbolInput = document.getElementById('tokenSymbol');
    if (type) {
        const randomNum = Math.floor(Math.random() * 9999) + 1000; // 生成1000-9999的随机数
        const assetCode = type === CONFIG.ASSET_TYPE.REAL_ESTATE ? '10' : '20';
        tokenSymbolInput.value = `${assetCode}${randomNum}`;
    } else {
        tokenSymbolInput.value = '';
    }

    if (type === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        realEstateFields.forEach(field => {
            field.classList.remove('hidden');
            field.querySelectorAll('input, select').forEach(input => input.required = true);
        });
        similarAssetsFields.forEach(field => {
            field.classList.add('hidden');
            field.querySelectorAll('input, select').forEach(input => {
                input.required = false;
                input.value = '';
            });
        });
        calculateRealEstateTokens();
    } else if (type === CONFIG.ASSET_TYPE.SIMILAR_ASSETS) {
        realEstateFields.forEach(field => {
            field.classList.add('hidden');
            field.querySelectorAll('input, select').forEach(input => {
                input.required = false;
                input.value = '';
            });
        });
        similarAssetsFields.forEach(field => {
            field.classList.remove('hidden');
            field.querySelectorAll('input, select').forEach(input => input.required = true);
        });
    }
    
    calculateTokenPrice();
    updateDocumentRequirements(type);
}

// 预览功能实现
function previewAsset() {
    // 获取表单数据
    const formData = new FormData(form);
    const assetData = {
        name: formData.get('name'),
        type: formData.get('type'),
        location: formData.get('location'),
        description: formData.get('description'),
        images: uploadedImages,
        documents: uploadedDocuments
    };

    // 根据资产类型获取特定字段
    if (assetData.type === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        assetData.area = formData.get('area');
        assetData.totalValue = formData.get('totalValue');
        assetData.tokenCount = calculatedElements.realEstate.tokenCount.textContent.replace(/,/g, '');
        assetData.tokenPrice = calculatedElements.realEstate.tokenPrice.textContent.replace(/,/g, '');
        assetData.expectedAnnualRevenue = formData.get('expectedAnnualRevenue');
        assetData.assetTypeName = '不动产';
    } else {
        assetData.tokenCount = formData.get('tokenCount');
        assetData.totalValue = document.getElementById('totalValueSimilar').value;
        assetData.tokenPrice = calculatedElements.similarAssets.tokenPrice.textContent.replace(/,/g, '');
        assetData.expectedAnnualRevenue = document.getElementById('expectedAnnualRevenueSimilar').value;
        assetData.assetTypeName = '类不动产';
    }

    // 创建预览模态框
    const previewModal = document.createElement('div');
    previewModal.className = 'modal fade';
    previewModal.id = 'previewModal';
    previewModal.innerHTML = `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">资产预览</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body p-0">
                    <div class="container-fluid p-0">
                        <!-- 图片轮播 -->
                        ${assetData.images.length > 0 ? `
                            <div class="asset-images mb-4">
                                <div id="previewCarousel" class="carousel slide" data-bs-ride="carousel">
                                    <div class="carousel-inner">
                                        ${assetData.images.map((image, index) => `
                                            <div class="carousel-item ${index === 0 ? 'active' : ''}">
                                                <img src="${image.data}" class="d-block w-100" alt="${image.name}" 
                                                     style="height: 400px; object-fit: cover;">
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
                            </div>
                        ` : ''}

                        <div class="container py-4">
                            <!-- 资产标题和状态 -->
                            <div class="row align-items-center mb-4">
                                <div class="col-md-8">
                                    <h2 class="mb-2">${assetData.name}</h2>
                                    <p class="text-muted mb-0">
                                        <i class="fas fa-map-marker-alt me-2"></i>${assetData.location}
                                    </p>
                                </div>
                                <div class="col-md-4 text-end">
                                    <span class="badge bg-secondary">预览模式</span>
                                </div>
                            </div>

                            <!-- 资产信息卡片 -->
                            <div class="row mb-4">
                                <div class="col-md-4 mb-3">
                                    <div class="card h-100">
                                        <div class="card-body">
                                            <h6 class="card-subtitle mb-2 text-muted">资产类型</h6>
                                            <p class="card-text h5">${assetData.assetTypeName}</p>
                                        </div>
                                    </div>
                                </div>
                                ${assetData.type === CONFIG.ASSET_TYPE.REAL_ESTATE ? `
                                    <div class="col-md-4 mb-3">
                                        <div class="card h-100">
                                            <div class="card-body">
                                                <h6 class="card-subtitle mb-2 text-muted">资产面积</h6>
                                                <p class="card-text h5">${formatNumber(assetData.area, 2)} ㎡</p>
                                            </div>
                                        </div>
                                    </div>
                                ` : ''}
                                <div class="col-md-4 mb-3">
                                    <div class="card h-100">
                                        <div class="card-body">
                                            <h6 class="card-subtitle mb-2 text-muted">预期年收益</h6>
                                            <p class="card-text h5">${formatNumber(assetData.expectedAnnualRevenue, 2)} USDC</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- 代币信息 -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">代币信息</h5>
                                </div>
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-3 mb-3">
                                            <h6 class="text-muted">代币总量</h6>
                                            <p class="h5">${formatNumber(assetData.tokenCount)}</p>
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <h6 class="text-muted">代币价格</h6>
                                            <p class="h5">${assetData.tokenPrice} USDC</p>
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <h6 class="text-muted">总价值</h6>
                                            <p class="h5">${formatNumber(assetData.totalValue, 2)} USDC</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- 资产描述 -->
                            <div class="card mb-4">
                                <div class="card-header">
                                    <h5 class="card-title mb-0">资产描述</h5>
                                </div>
                                <div class="card-body">
                                    <p class="card-text">${assetData.description}</p>
                                </div>
                            </div>

                            <!-- 相关文档 -->
                            ${assetData.documents.length > 0 ? `
                                <div class="card">
                                    <div class="card-header">
                                        <h5 class="card-title mb-0">相关文档</h5>
                                    </div>
                                    <div class="card-body">
                                        <div class="list-group list-group-flush">
                                            ${assetData.documents.map(doc => `
                                                <div class="list-group-item">
                                                    <i class="fas fa-file-alt me-2"></i>
                                                    ${doc.name}
                                                </div>
                                            `).join('')}
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    <button type="button" class="btn btn-primary" onclick="submitAsset()">提交审核</button>
                </div>
            </div>
        </div>
    `;

    // 移除旧的预览模态框（如果存在）
    const oldModal = document.getElementById('previewModal');
    if (oldModal) {
        oldModal.remove();
    }

    // 添加新的预览模态框到页面
    document.body.appendChild(previewModal);

    // 显示预览模态框
    const modal = new bootstrap.Modal(previewModal);
    modal.show();
}

// 添加提交资产函数
async function submitAsset() {
    try {
        const errors = validateForm();
        if (errors.length > 0) {
            showError(errors.join('\n'));
            return;
        }

        const formData = new FormData(form);
        
        // 根据资产类型处理不同字段
        if (typeInput.value === CONFIG.ASSET_TYPE.REAL_ESTATE) {
            formData.append('area', areaInput.value);
            formData.append('totalValue', totalValueInput.value);
            formData.append('tokenCount', calculatedElements.realEstate.tokenCount.textContent.replace(/,/g, ''));
            formData.append('tokenPrice', calculatedElements.realEstate.tokenPrice.textContent.replace(/,/g, ''));
            formData.append('expectedAnnualRevenue', expectedAnnualRevenueInput.value);
        } else {
            formData.append('tokenCount', tokenCountInput.value);
            formData.append('totalValue', document.getElementById('totalValueSimilar').value);
            formData.append('tokenPrice', calculatedElements.similarAssets.tokenPrice.textContent.replace(/,/g, ''));
            formData.append('expectedAnnualRevenue', document.getElementById('expectedAnnualRevenueSimilar').value);
        }

        // 添加图片
        if (uploadedImages.length > 0) {
            for (let i = 0; i < uploadedImages.length; i++) {
                const image = uploadedImages[i];
                try {
                    const blob = await dataURLtoBlob(image.data);
                    formData.append('images[]', blob, image.name);
                } catch (error) {
                    console.error(`处理图片失败: ${image.name}`, error);
                    showError(`处理图片 ${image.name} 失败，请重新上传`);
                    return;
                }
            }
        }

        // 添加文档
        if (uploadedDocuments.length > 0) {
            for (let i = 0; i < uploadedDocuments.length; i++) {
                const doc = uploadedDocuments[i];
                try {
                    const blob = await dataURLtoBlob(doc.data);
                    formData.append('documents[]', blob, doc.name);
                } catch (error) {
                    console.error(`处理文档失败: ${doc.name}`, error);
                    showError(`处理文档 ${doc.name} 失败，请重新上传`);
                    return;
                }
            }
        }

        // 显示加载状态
        const submitButton = document.querySelector('#previewModal .btn-primary');
        const originalText = submitButton.innerHTML;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 提交中...';

        // 发送请求
        const response = await fetch('/api/assets/create', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || error.error || '提交失败');
        }

        const result = await response.json();
        localStorage.removeItem(CONFIG.DRAFT.KEY);
        
        // 显示成功提示
        showToast('资产提交成功！');
        
        // 延迟跳转，让用户看到成功提示
        setTimeout(() => {
            window.location.href = `/assets/${result.assetId}`;
        }, 1500);

    } catch (error) {
        console.error('提交表单失败:', error);
        showError(error.message || '提交失败，请稍后重试');
        
        // 恢复按钮状态
        const submitButton = document.querySelector('#previewModal .btn-primary');
        submitButton.disabled = false;
        submitButton.innerHTML = '提交审核';
    }
} 