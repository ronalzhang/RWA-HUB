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
const tokenPriceInput = document.getElementById('tokenPrice');
const expectedAnnualRevenueInput = document.getElementById('expectedAnnualRevenue');
const imageDropzone = document.getElementById('imageDropzone');
const documentDropzone = document.getElementById('documentDropzone');

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
const draftTime = document.getElementById('draftTime');
const loadDraftBtn = document.getElementById('loadDraft');
const discardDraftBtn = document.getElementById('discardDraft');
const saveDraftBtn = document.getElementById('saveDraft');

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
    if (type === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        // 显示不动产字段
        document.querySelectorAll('.asset-type-field.real-estate').forEach(field => {
            field.classList.remove('hidden');
            field.querySelectorAll('input, select, textarea').forEach(input => {
                input.required = true;
            });
        });
        document.querySelectorAll('.real-estate-docs').forEach(el => el.classList.remove('hidden'));
        document.querySelectorAll('.similar-assets-docs').forEach(el => el.classList.add('hidden'));
        
        // 隐藏类不动产字段
        document.querySelectorAll('.asset-type-field.similar-assets').forEach(field => {
            field.classList.add('hidden');
            field.querySelectorAll('input, select, textarea').forEach(input => {
                input.required = false;
                input.value = '';
            });
        });
        
        // 更新计算显示
        document.querySelector('.real-estate-info').classList.remove('hidden');
        calculateRealEstateTokens();
    } else if (type === CONFIG.ASSET_TYPE.SIMILAR_ASSETS) {
        // 显示类不动产字段
        document.querySelectorAll('.asset-type-field.similar-assets').forEach(field => {
            field.classList.remove('hidden');
            field.querySelectorAll('input, select, textarea').forEach(input => {
                input.required = true;
            });
        });
        document.querySelectorAll('.similar-assets-docs').forEach(el => el.classList.remove('hidden'));
        document.querySelectorAll('.real-estate-docs').forEach(el => el.classList.add('hidden'));
        
        // 隐藏不动产字段
        document.querySelectorAll('.asset-type-field.real-estate').forEach(field => {
            field.classList.add('hidden');
            field.querySelectorAll('input, select, textarea').forEach(input => {
                input.required = false;
                input.value = '';
            });
        });
        
        // 更新计算显示
        document.querySelector('.real-estate-info').classList.add('hidden');
    }
    
    // 重置计算结果
    resetCalculations();
    
    // 更新文档要求显示
    updateDocumentRequirements(type);
}

// 重置计算结果
function resetCalculations() {
    calculatedTokenCount.textContent = '0';
    calculatedTokenPrice.textContent = '0.000000';
    tokenPriceInput.value = '';
}

// 计算代币数量（不动产）
function calculateRealEstateTokens() {
    const area = parseFloat(areaInput.value) || 0;
    if (area > 0) {
        const tokenCount = Math.floor(area * CONFIG.CALCULATION.TOKENS_PER_SQUARE_METER);
        calculatedTokenCount.textContent = formatNumber(tokenCount);
        return tokenCount;
    }
    calculatedTokenCount.textContent = '0';
    return 0;
}

// 计算代币价格
function calculateTokenPrice() {
    const totalValue = parseFloat(totalValueInput.value) || 0;
    let tokenCount = 0;
    
    if (typeInput.value === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        tokenCount = calculateRealEstateTokens();
    } else {
        tokenCount = parseInt(tokenCountInput.value) || 0;
    }
    
    if (totalValue > 0 && tokenCount > 0) {
        const tokenPrice = totalValue / tokenCount;
        const formattedPrice = formatNumber(tokenPrice, CONFIG.CALCULATION.PRICE_DECIMALS);
        calculatedTokenPrice.textContent = formattedPrice;
        tokenPriceInput.value = tokenPrice.toFixed(CONFIG.CALCULATION.PRICE_DECIMALS);
        
        // 更新显示
        if (typeInput.value === CONFIG.ASSET_TYPE.REAL_ESTATE) {
            calculatedTokenCount.textContent = formatNumber(tokenCount);
        }
    } else {
        calculatedTokenPrice.textContent = '0.000000';
        tokenPriceInput.value = '';
        calculatedTokenCount.textContent = '0';
    }
}

// 图片压缩函数
async function compressImage(file) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.src = URL.createObjectURL(file);
        
        img.onload = () => {
            const canvas = document.createElement('canvas');
            let width = img.width;
            let height = img.height;
            
            // 计算缩放比例
            if (width > CONFIG.IMAGE.COMPRESS.MAX_WIDTH) {
                height = (CONFIG.IMAGE.COMPRESS.MAX_WIDTH * height) / width;
                width = CONFIG.IMAGE.COMPRESS.MAX_WIDTH;
            }
            if (height > CONFIG.IMAGE.COMPRESS.MAX_HEIGHT) {
                width = (CONFIG.IMAGE.COMPRESS.MAX_HEIGHT * width) / height;
                height = CONFIG.IMAGE.COMPRESS.MAX_HEIGHT;
            }
            
            canvas.width = width;
            canvas.height = height;
            
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            
            canvas.toBlob((blob) => {
                resolve(new File([blob], file.name, {
                    type: 'image/jpeg',
                    lastModified: Date.now()
                }));
            }, 'image/jpeg', CONFIG.IMAGE.COMPRESS.QUALITY);
        };
        
        img.onerror = reject;
    });
}

// 文件验证函数
function validateFiles(files, type) {
    const config = CONFIG[type];
    const errors = [];
    
    if (files.length > config.MAX_FILES) {
        errors.push(`最多只能上传${config.MAX_FILES}个文件`);
    }
    
    for (const file of files) {
        if (file.size > config.MAX_SIZE) {
            errors.push(`文件 ${file.name} 超过大小限制`);
        }
        
        if (!config.ALLOWED_TYPES.includes(file.type)) {
            errors.push(`文件 ${file.name} 类型不支持`);
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
    const errors = validateFiles(files, type);
    if (errors.length > 0) {
        showError(errors.join('\n'));
        return;
    }
    
    const processedFiles = [];
    let totalSize = 0;
    let loadedSize = 0;
    
    for (const file of files) {
        totalSize += file.size;
        try {
            let processedFile = file;
            if (type === 'IMAGE') {
                processedFile = await compressImage(file);
            }
            
            const reader = new FileReader();
            reader.onload = function(e) {
                loadedSize += processedFile.size;
                showProgress(type, loadedSize, totalSize);
                
                if (type === 'IMAGE') {
                    uploadedImages.push({
                        name: processedFile.name,
                        type: processedFile.type,
                        data: e.target.result,
                        size: processedFile.size
                    });
                    updateImagePreview();
                } else {
                    uploadedDocuments.push({
                        name: processedFile.name,
                        type: processedFile.type,
                        data: e.target.result,
                        size: processedFile.size
                    });
                    updateDocumentList();
                }
            };
            reader.readAsDataURL(processedFile);
            processedFiles.push(processedFile);
        } catch (error) {
            showError(`处理文件 ${file.name} 失败: ${error.message}`);
        }
    }
}

function updateImagePreview() {
    const previewContainer = document.getElementById('imagePreview');
    previewContainer.innerHTML = '';
    
    uploadedImages.forEach((image, index) => {
        const div = document.createElement('div');
        div.className = 'col-md-4 mb-3';
        div.innerHTML = `
            <div class="position-relative">
                <img src="${image.data}" class="img-thumbnail" alt="${image.name}">
                <button type="button" class="btn btn-danger btn-sm position-absolute top-0 end-0 m-1" 
                        onclick="removeImage(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        previewContainer.appendChild(div);
    });
}

function updateDocumentList() {
    const listContainer = document.getElementById('documentList');
    listContainer.innerHTML = '';
    
    uploadedDocuments.forEach((doc, index) => {
        const div = document.createElement('div');
        div.className = 'mb-2';
        div.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-file-alt me-2"></i>
                <span class="me-auto">${doc.name}</span>
                <button type="button" class="btn btn-danger btn-sm" 
                        onclick="removeDocument(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        listContainer.appendChild(div);
    });
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
    const draft = JSON.parse(localStorage.getItem(CONFIG.DRAFT.KEY));
    if (!draft) return;
    
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
}

function checkDraft() {
    const draft = JSON.parse(localStorage.getItem(CONFIG.DRAFT.KEY));
    if (draft) {
        draftInfo.style.display = 'block';
        draftTime.textContent = new Date(draft.timestamp).toLocaleString();
    }
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
document.addEventListener('DOMContentLoaded', function() {
    // 拖放区域事件
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        imageDropzone.addEventListener(eventName, preventDefaults);
        documentDropzone.addEventListener(eventName, preventDefaults);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // 高亮拖放区域
    ['dragenter', 'dragover'].forEach(eventName => {
        imageDropzone.addEventListener(eventName, highlight);
        documentDropzone.addEventListener(eventName, highlight);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        imageDropzone.addEventListener(eventName, unhighlight);
        documentDropzone.addEventListener(eventName, unhighlight);
    });
    
    function highlight(e) {
        e.target.classList.add('border-primary');
    }
    
    function unhighlight(e) {
        e.target.classList.remove('border-primary');
    }
    
    // 处理文件拖放
    imageDropzone.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files, 'image');
    });
    
    documentDropzone.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files, 'document');
    });
    
    // 处理文件选择
    document.getElementById('imageInput').addEventListener('change', e => {
        handleFiles(e.target.files, 'image');
    });
    
    document.getElementById('documentInput').addEventListener('change', e => {
        handleFiles(e.target.files, 'document');
    });
    
    // 资产类型切换
    typeInput.addEventListener('change', function() {
        toggleAssetTypeFields(this.value);
    });
    
    // 不动产计算触发器
    areaInput.addEventListener('input', function() {
        if (typeInput.value === CONFIG.ASSET_TYPE.REAL_ESTATE) {
            calculateTokenPrice();
        }
    });
    
    // 类不动产计算触发器
    tokenCountInput.addEventListener('input', function() {
        if (typeInput.value === CONFIG.ASSET_TYPE.SIMILAR_ASSETS) {
            calculateTokenPrice();
        }
    });
    
    // 总价值变化触发器
    totalValueInput.addEventListener('input', calculateTokenPrice);
    
    // 自动保存
    let autoSaveTimer = setInterval(saveDraft, CONFIG.DRAFT.AUTO_SAVE_INTERVAL);
    
    // 检查草稿
    checkDraft();
    
    // 草稿按钮事件
    loadDraftBtn.addEventListener('click', loadDraft);
    discardDraftBtn.addEventListener('click', () => {
        localStorage.removeItem(CONFIG.DRAFT.KEY);
        draftInfo.style.display = 'none';
    });
    saveDraftBtn.addEventListener('click', () => {
        saveDraft();
        showToast('草稿已保存');
    });
    
    // 表单提交增强
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const errors = validateForm();
        if (errors.length > 0) {
            showError(errors.join('\n'));
            return;
        }
        
        const formData = new FormData();
        formData.append('name', nameInput.value);
        formData.append('type', typeInput.value);
        formData.append('location', locationInput.value);
        formData.append('description', descriptionInput.value);
        formData.append('area', areaInput.value);
        formData.append('totalValue', totalValueInput.value);
        formData.append('expectedAnnualRevenue', expectedAnnualRevenueInput.value);
        
        // 添加图片和文档
        uploadedImages.forEach((image, index) => {
            formData.append(`images[${index}]`, dataURLtoBlob(image.data), image.name);
        });
        
        uploadedDocuments.forEach((doc, index) => {
            formData.append(`documents[${index}]`, dataURLtoBlob(doc.data), doc.name);
        });
        
        // 添加计算结果
        if (typeInput.value === CONFIG.ASSET_TYPE.REAL_ESTATE) {
            formData.append('tokenCount', calculatedTokenCount.textContent.replace(/,/g, ''));
        }
        formData.append('tokenPrice', tokenPriceInput.value);
        
        try {
            const response = await fetch('/api/assets/create', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || '提交失败');
            }
            
            const result = await response.json();
            // 清除草稿
            localStorage.removeItem(CONFIG.DRAFT.KEY);
            clearInterval(autoSaveTimer);
            
            window.location.href = `/assets/${result.assetId}`;
        } catch (error) {
            showError(error.message);
        }
    });
});

// 辅助函数
function dataURLtoBlob(dataURL) {
    const arr = dataURL.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    
    while (n--) {
        u8arr[n] = bstr.charCodeAt(n);
    }
    
    return new Blob([u8arr], { type: mime });
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
    const realEstateInfo = document.querySelector('.real-estate-info');
    
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
        realEstateInfo.classList.remove('hidden');
        calculateRealEstateTokens();
    } else {
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
        realEstateInfo.classList.add('hidden');
        calculatedTokenCount.textContent = '0';
    }
    
    calculateTokenPrice();
} 