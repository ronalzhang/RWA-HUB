// 配置常量
const CONFIG = {
    IMAGE: {
        MAX_FILES: 10,
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
const totalValueInput = document.getElementById('total_value');
const tokenCountInput = document.getElementById('token_count');
const tokenSymbolInput = document.getElementById('token_symbol');
const annualRevenueInput = document.getElementById('annual_revenue');
const imageDropzone = document.getElementById('imageDropzone');
const documentDropzone = document.getElementById('documentDropzone');

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
    if (calculatedElements.realEstate.tokenCount) {
        calculatedElements.realEstate.tokenCount.textContent = '0';
    }
    if (calculatedElements.realEstate.tokenPrice) {
        calculatedElements.realEstate.tokenPrice.textContent = '0.000000';
    }
    if (calculatedElements.similarAssets.tokenPrice) {
        calculatedElements.similarAssets.tokenPrice.textContent = '0.000000';
    }
}

// 面积变化时计算代币数量
function calculateRealEstateTokens() {
    const areaInput = document.getElementById('area');
    const tokenCountElement = document.getElementById('token_count');
    
    if (!areaInput || !tokenCountElement) return;
    
    const area = parseFloat(areaInput.value) || 0;
    const tokenCount = area * CONFIG.CALCULATION.TOKENS_PER_SQUARE_METER;
    tokenCountElement.textContent = formatNumber(tokenCount);
    
    // 同时更新代币价格
    calculateTokenPrice();
}

// 总价值或面积变化时计算代币价格
function calculateTokenPrice() {
    const totalValueInput = document.getElementById('total_value');
    const areaInput = document.getElementById('area');
    const tokenPriceElement = document.getElementById('token_price');
    
    if (!totalValueInput || !areaInput || !tokenPriceElement) return;
    
    const total_value = parseFloat(totalValueInput.value) || 0;
    const area = parseFloat(areaInput.value) || 0;
    const token_supply = area * CONFIG.CALCULATION.TOKENS_PER_SQUARE_METER;
    
    if (total_value > 0 && token_supply > 0) {
        const price = total_value / token_supply;
        tokenPriceElement.textContent = formatNumber(price, CONFIG.CALCULATION.PRICE_DECIMALS);
    } else {
        tokenPriceElement.textContent = '0.000000';
    }
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
        // 基本验证
        if (!files || files.length === 0) {
            showError('请选择要上传的文件');
            return;
        }

        // 验证文件类型和数量
        const fileType = type || 'IMAGE';
        const config = CONFIG[fileType];
        if (!config) {
            showError('无效的文件类型');
            return;
        }

        if (files.length > config.MAX_FILES) {
            showError(`最多只能上传 ${config.MAX_FILES} 个文件`);
            return;
        }

        // 显示上传进度条
        const progressElement = fileType === 'IMAGE' ? imageUploadProgress : documentUploadProgress;
        progressElement.style.display = 'block';
        progressElement.querySelector('.progress-bar').style.width = '0%';

        // 准备上传
        const uploadPromises = [];
        const uploadResults = [];

        // 处理每个文件
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (!validateFile(file, fileType)) {
                continue;
            }

            const formData = new FormData();
            formData.append('file', file);

            // 创建上传Promise
            const uploadPromise = fetch('/api/upload', {
                method: 'POST',
                body: formData
            }).then(async response => {
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || '上传失败');
                }
                return response.json();
            }).then(result => {
                if (result.url) {
                    // 确保使用 HTTP 协议
                    let url = result.url;
                    if (url.startsWith('https://')) {
                        url = 'http://' + url.substring(8);
                    }
                    uploadResults.push({
                        url: url,
                        name: result.name || file.name
                    });
                    
                    // 更新进度
                    const progress = ((i + 1) / files.length) * 100;
                    progressElement.querySelector('.progress-bar').style.width = `${progress}%`;
                }
            });

            uploadPromises.push(uploadPromise);
        }

        // 等待所有文件上传完成
        await Promise.all(uploadPromises);

        // 更新UI
        if (fileType === 'IMAGE') {
            uploadedImages = [...uploadedImages, ...uploadResults];
            updateImagePreview();
        } else {
            uploadedDocuments = [...uploadedDocuments, ...uploadResults];
            updateDocumentList();
        }

        // 隐藏进度条
        setTimeout(() => {
            progressElement.style.display = 'none';
        }, 1000);

        // 显示上传结果
        const successCount = uploadResults.length;
        const failureCount = files.length - successCount;
        
        if (successCount > 0) {
            showToast(`成功上传 ${successCount} 个文件${failureCount > 0 ? `，${failureCount} 个文件失败` : ''}`);
        } else if (failureCount > 0) {
            showToast(`${failureCount} 个文件上传失败`);
        }

    } catch (error) {
        console.error('处理文件失败:', error);
        showError(error.message || '文件上传失败');
    }
}

// 文件验证
function validateFile(file, type) {
    const config = CONFIG[type.toUpperCase()];
    if (!config) {
        showToast(`无效的文件类型: ${type}`);
        return false;
    }

    // 检查文件大小
    if (file.size > config.MAX_SIZE) {
        const maxSize = config.MAX_SIZE / (1024 * 1024);
        showToast(`文件 ${file.name} 超过大小限制 (${maxSize}MB)`);
        return false;
    }

    // 检查文件类型
    const fileExt = file.name.split('.').pop().toLowerCase();
    const allowedExts = config.ALLOWED_TYPES.map(type => type.split('/')[1]);
    if (!allowedExts.includes(fileExt)) {
        showToast(`文件 ${file.name} 类型不支持 (支持的格式: ${allowedExts.join(', ')})`);
        return false;
    }

    return true;
}

// 更新图片预览
function updateImagePreview() {
    const container = document.getElementById('imagePreview');
    if (!container) return;

    container.innerHTML = '';
    
    if (!uploadedImages || uploadedImages.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">暂无图片</div>';
        return;
    }

    uploadedImages.forEach((image, index) => {
        // 确保使用 HTTP 协议
        let imageUrl = image.url;
        if (imageUrl.startsWith('https://')) {
            imageUrl = 'http://' + imageUrl.substring(8);
        }
        
        const div = document.createElement('div');
        div.className = 'col-md-4 mb-3';
        div.innerHTML = `
            <div class="card h-100">
                <img src="${imageUrl}" 
                     class="card-img-top" 
                     alt="${image.name}"
                     style="height: 200px; object-fit: cover;">
                <div class="card-body">
                    <p class="card-text">${image.name}</p>
                    <button class="btn btn-sm btn-danger" 
                            onclick="removeImage(${index})">
                        删除
                    </button>
                </div>
            </div>
        `;
        container.appendChild(div);
    });
}

// 更新文档列表
function updateDocumentList() {
    const container = document.getElementById('documentList');
    if (!container) return;

    container.innerHTML = '';
    
    if (!uploadedDocuments || uploadedDocuments.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">暂无文档</div>';
        return;
    }

    uploadedDocuments.forEach((doc, index) => {
        const div = document.createElement('div');
        div.className = 'mb-2 p-2 border rounded';
        div.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-file me-2"></i>
                <span class="flex-grow-1">${doc.name}</span>
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
    if (index >= 0 && index < uploadedImages.length) {
        uploadedImages.splice(index, 1);
        console.log('移除后的图片数组:', uploadedImages);
        updateImagePreview();
    }
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
    const errors = [];
    const type = document.getElementById('type').value;
    
    // 基本字段验证
    if (!form.checkValidity()) {
        errors.push('请填写所有必填字段');
    }
    
    // 验证代币符号
    const tokenSymbol = document.getElementById('tokenSymbol').value;
    if (!tokenSymbol) {
        errors.push('代币符号不能为空');
    } else if (!/^RH-(10|20)\d{4}$/.test(tokenSymbol)) {
        errors.push('代币符号格式不正确，应为 RH-XXYYYY 格式');
    }
    
    // 不动产特有验证
    if (type === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        const area = parseFloat(document.getElementById('area').value) || 0;
        if (area <= 0) {
            errors.push('面积必须大于0');
        }
        
        const totalValue = parseFloat(document.getElementById('total_value').value) || 0;
        if (totalValue <= 0) {
            errors.push('总价值必须大于0');
        }
    }
    
    // 类不动产特有验证
    if (type === CONFIG.ASSET_TYPE.SIMILAR_ASSETS) {
        const tokenCount = parseInt(document.getElementById('tokenCount').value) || 0;
        if (tokenCount <= 0) {
            errors.push('代币数量必须大于0');
        }
        if (tokenCount % 1 !== 0) {
            errors.push('代币数量必须是整数');
        }
        
        const totalValue = parseFloat(document.getElementById('totalValueSimilar').value) || 0;
        if (totalValue <= 0) {
            errors.push('总价值必须大于0');
        }
    }
    
    return errors;
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

// 资产类型切换事件
document.getElementById('type').addEventListener('change', function(e) {
    const type = e.target.value;
    toggleAssetTypeFields(type);
    generateTokenSymbol(type);
});

// 面积和总价值变化事件
document.getElementById('area').addEventListener('input', async function() {
    if (document.getElementById('type').value === '10') {
        calculateRealEstateTokens();
    }
});

document.getElementById('total_value').addEventListener('input', function() {
    calculateTokenPrice();
});

// 类不动产代币数量和总价值变化事件
document.getElementById('tokenCount').addEventListener('input', function() {
    calculateSimilarAssetsTokenPrice();
});

document.getElementById('totalValueSimilar').addEventListener('input', function() {
    calculateSimilarAssetsTokenPrice();
});

// 生成代币代码
async function generateTokenSymbol(type) {
    try {
        const response = await fetch('/api/assets/generate-token-symbol', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ type })
        });
        
        if (!response.ok) {
            throw new Error('生成代币代码失败');
        }
        
        const data = await response.json();
        document.getElementById('tokenSymbol').value = data.token_symbol;
    } catch (error) {
        console.error('生成代币代码失败:', error);
        showError('生成代币代码失败: ' + error.message);
    }
}

// 计算类不动产代币价格
async function calculateSimilarAssetsTokenPrice() {
    const tokenCount = parseInt(document.getElementById('tokenCount').value) || 0;
    const totalValue = parseFloat(document.getElementById('totalValueSimilar').value) || 0;
    
    try {
        const response = await fetch('/api/assets/calculate-tokens', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: '20',
                token_count: tokenCount,
                total_value: totalValue
            })
        });
        
        if (!response.ok) {
            throw new Error('计算代币价格失败');
        }
        
        const data = await response.json();
        document.getElementById('calculatedTokenPriceSimilar').textContent = 
            formatNumber(data.token_price, CONFIG.CALCULATION.PRICE_DECIMALS);
    } catch (error) {
        console.error('计算代币价格失败:', error);
        showError('计算代币价格失败: ' + error.message);
    }
}

// 初始化表单元素
function initializeFormElements() {
    const elements = {
        form: document.getElementById('assetForm'),
        name: document.getElementById('name'),
        type: document.getElementById('type'),
        location: document.getElementById('location'),
        description: document.getElementById('description'),
        area: document.getElementById('area'),
        total_value: document.getElementById('total_value'),
        token_count: document.getElementById('token_count'),
        token_price: document.getElementById('token_price'),
        annual_revenue: document.getElementById('annual_revenue'),
        tokenCount: document.getElementById('tokenCount'),
        totalValueSimilar: document.getElementById('totalValueSimilar'),
        calculatedTokenPriceSimilar: document.getElementById('calculatedTokenPriceSimilar'),
        expectedAnnualRevenueSimilar: document.getElementById('expectedAnnualRevenueSimilar'),
        imageDropzone: document.getElementById('imageDropzone'),
        imageInput: document.getElementById('imageInput'),
        documentDropzone: document.getElementById('documentDropzone'),
        documentInput: document.getElementById('documentInput'),
        previewBtn: document.getElementById('previewForm'),
        saveDraftBtn: document.getElementById('saveDraft')
    };
    
    // 初始化事件监听器
    initializeEventListeners(elements);
    
    // 检查是否有草稿
    checkDraft();
    
    return elements;
}

// 初始化事件监听
function initializeEventListeners(elements) {
    if (!elements) return;

    // 拖放区域事件
    const dropzones = [elements.imageDropzone, elements.documentDropzone].filter(Boolean);
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzones.forEach(dropzone => {
            dropzone.addEventListener(eventName, preventDefaults);
        });
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // 高亮拖放区域
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzones.forEach(dropzone => {
            dropzone.addEventListener(eventName, highlight);
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropzones.forEach(dropzone => {
            dropzone.addEventListener(eventName, unhighlight);
        });
    });
    
    function highlight(e) {
        e.target.classList.add('border-primary');
    }
    
    function unhighlight(e) {
        e.target.classList.remove('border-primary');
    }
    
    // 处理文件拖放和选择
    if (elements.imageDropzone && elements.imageInput) {
        // 拖放处理
        elements.imageDropzone.addEventListener('drop', e => {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        });
        
        // 文件选择处理
        elements.imageInput.addEventListener('change', e => {
            if (e.target.files && e.target.files.length > 0) {
                handleFiles(e.target.files);
                e.target.value = ''; // 清空input，允许选择相同文件
            }
        });
        
        // 点击上传区域 - 移除旧的点击事件，只保留这一个
        elements.imageDropzone.onclick = e => {
            // 确保只有点击dropzone本身或其直接子元素时才触发
            if (e.target === elements.imageDropzone || e.target.parentNode === elements.imageDropzone) {
                elements.imageInput.click();
            }
        };
    }
    
    if (elements.documentDropzone && elements.documentInput) {
        // 拖放处理
        elements.documentDropzone.addEventListener('drop', e => {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        });
        
        // 文件选择处理
        elements.documentInput.addEventListener('change', e => {
            if (e.target.files && e.target.files.length > 0) {
                handleFiles(e.target.files);
                e.target.value = ''; // 清空input，允许选择相同文件
            }
        });
        
        // 点击上传区域 - 移除旧的点击事件，只保留这一个
        elements.documentDropzone.onclick = e => {
            // 确保只有点击dropzone本身或其直接子元素时才触发
            if (e.target === elements.documentDropzone || e.target.parentNode === elements.documentDropzone) {
                elements.documentInput.click();
            }
        };
    }
    
    // 表单提交
    if (elements.form) {
        elements.form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!window.ethereum?.selectedAddress) {
                showError('请先连接钱包');
                return;
            }
            
            const errors = validateForm();
            if (errors.length > 0) {
                showError(errors.join('\n'));
                return;
            }
            
            await submitForm(e);
        });
    }
    
    // 预览按钮
    if (elements.previewBtn) {
        elements.previewBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const errors = validateForm();
            if (errors.length > 0) {
                showError(errors.join('\n'));
                return;
            }
            previewAsset();
        });
    }
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
    const formData = new FormData(form);
    const assetData = {
        name: formData.get('name'),
        type: formData.get('type'),
        location: formData.get('location'),
        description: formData.get('description'),
        token_symbol: formData.get('token_symbol'),
        images: uploadedImages.map(image => ({
            ...image,
            url: image.url.startsWith('https://') ? 'http://' + image.url.substring(8) : image.url
        })),
        documents: uploadedDocuments.map(doc => ({
            ...doc,
            url: doc.url.startsWith('https://') ? 'http://' + doc.url.substring(8) : doc.url
        }))
    };

    if (assetData.type === CONFIG.ASSET_TYPE.REAL_ESTATE) {
        const area = parseFloat(formData.get('area')) || 0;
        assetData.area = area;
        assetData.total_value = formData.get('total_value');
        assetData.token_supply = area * CONFIG.CALCULATION.TOKENS_PER_SQUARE_METER;
        assetData.token_price = assetData.token_supply > 0 ? 
            (parseFloat(assetData.total_value) / assetData.token_supply).toFixed(CONFIG.CALCULATION.PRICE_DECIMALS) : 
            '0.000000';
        assetData.annual_revenue = formData.get('annual_revenue');
    } else {
        assetData.token_supply = formData.get('token_supply');
        assetData.total_value = formData.get('total_value');
        assetData.token_price = calculatedElements.similarAssets.tokenPrice.textContent.replace(/,/g, '');
        assetData.annual_revenue = formData.get('annual_revenue');
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
                <div class="modal-body">
                    <div class="container-fluid">
                        ${assetData.images.length > 0 ? `
                            <div id="previewCarousel" class="carousel slide mb-4" data-bs-ride="carousel">
                                <div class="carousel-inner">
                                    ${assetData.images.map((image, index) => `
                                        <div class="carousel-item ${index === 0 ? 'active' : ''}">
                                            <img src="${image.url}" class="d-block w-100" alt="${image.name}" 
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
                        ` : ''}

                        <div class="row mb-4">
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

                        <div class="row mb-4">
                            <div class="col-md-4">
                                <div class="card h-100">
                                    <div class="card-body">
                                        <h6 class="text-muted mb-2">资产类型</h6>
                                        <p class="h5 mb-0">${assetData.type === CONFIG.ASSET_TYPE.REAL_ESTATE ? '不动产' : '类不动产'}</p>
                                    </div>
                                </div>
                            </div>
                            ${assetData.type === CONFIG.ASSET_TYPE.REAL_ESTATE ? `
                                <div class="col-md-4">
                                    <div class="card h-100">
                                        <div class="card-body">
                                            <h6 class="text-muted mb-2">资产面积</h6>
                                            <p class="h5 mb-0">${formatNumber(assetData.area, 2)} ㎡</p>
                                        </div>
                                    </div>
                                </div>
                            ` : ''}
                            <div class="col-md-4">
                                <div class="card h-100">
                                    <div class="card-body">
                                        <h6 class="text-muted mb-2">预期年收益</h6>
                                        <p class="h5 mb-0">${formatNumber(assetData.annual_revenue, 2)} USDC</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="card mb-4">
                            <div class="card-header">
                                <h5 class="card-title mb-0">代币信息</h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-3">
                                        <h6 class="text-muted mb-2">代币代码</h6>
                                        <p class="h5 mb-0">${assetData.token_symbol}</p>
                                    </div>
                                    <div class="col-md-3">
                                        <h6 class="text-muted mb-2">代币总量</h6>
                                        <p class="h5 mb-0">${formatNumber(assetData.token_supply)}</p>
                                    </div>
                                    <div class="col-md-3">
                                        <h6 class="text-muted mb-2">代币价格</h6>
                                        <p class="h5 mb-0">${assetData.token_price} USDC</p>
                                    </div>
                                    <div class="col-md-3">
                                        <h6 class="text-muted mb-2">总价值</h6>
                                        <p class="h5 mb-0">${formatNumber(assetData.total_value, 2)} USDC</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="card mb-4">
                            <div class="card-header">
                                <h5 class="card-title mb-0">资产描述</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">${assetData.description}</p>
                            </div>
                        </div>

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
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    <button type="button" class="btn btn-primary" onclick="submitForm()">提交审核</button>
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

// 表单提交处理
form.addEventListener('submit', async (event) => {
    event.preventDefault();
    
    try {
        const formData = new FormData(form);
        
        // 添加图片文件
        uploadedImages.forEach(async (image, index) => {
            try {
                const blob = await dataURLtoBlob(image.url);
                formData.append('files[]', blob, image.name);
            } catch (error) {
                console.error(`转换图片失败: ${image.name}`, error);
                throw error;
            }
        });
        
        // 发送请求
        const response = await fetch('/api/assets/create', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '创建资产失败');
        }
        
        const result = await response.json();
        alert('资产创建成功');
        window.location.href = `/assets/${result.assetId}`;
        
    } catch (error) {
        console.error('提交表单失败:', error);
        showError(error.message || '创建资产失败，请重试');
    }
});

// 修改页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', () => {
    // 不再调用 initializeDropzone()，因为相关功能已经在 initializeFormElements() 中处理
}); 