// 工具函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 重试机制
async function submitWithRetry(formData, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch('/api/assets', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content,
                },
                credentials: 'same-origin'
            });
            
            console.log('提交响应:', response);
            return response;
        } catch (error) {
            console.error('提交错误:', error);
            if (i === maxRetries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
        }
    }
}

// 全局文件存储
let uploadedFiles = {
    images: new Map(),
    documents: new Map()
};

// 表单验证和提交处理
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('assetForm');
    const submitBtn = document.getElementById('submitBtn');
    const saveDraftBtn = document.getElementById('saveDraft');
    const descriptionField = document.getElementById('description');
    const descriptionCount = document.getElementById('descriptionCount');
    const assetTypeSelect = document.getElementById('type');
    const areaField = document.getElementById('area');
    const imageUploadArea = document.getElementById('imageUpload');
    const documentUploadArea = document.getElementById('documentUpload');
    const imageInput = document.getElementById('imageInput');
    const documentInput = document.getElementById('documentInput');
    const imagePreview = document.getElementById('imagePreview');
    const documentPreview = document.getElementById('documentPreview').querySelector('.list-group');
    const draftSavedToast = new bootstrap.Toast(document.getElementById('draftSavedToast'));
    
    // 初始化所有功能
    initializeForm();
    setupTokenSupplyCalculation();
    
    // 字符计数器（带防抖）
    descriptionField.addEventListener('input', debounce(function() {
        const count = this.value.length;
        descriptionCount.textContent = count;
        if (count > 1000) {
            this.value = this.value.substring(0, 1000);
        }
    }, 300));
    
    // 资产类型联动
    assetTypeSelect.addEventListener('change', function() {
        const selectedType = this.value;
        handleAssetTypeChange(selectedType);
    });
    
    // 文件上传区域的键盘访问
    [imageUploadArea, documentUploadArea].forEach(area => {
        area.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });
    
    // 图片上传处理
    setupFileUpload(imageUploadArea, imageInput, handleImageFiles, 'images');
    
    // 文档上传处理
    setupFileUpload(documentUploadArea, documentInput, handleDocumentFiles, 'documents');
    
    // 保存草稿
    saveDraftBtn.addEventListener('click', saveDraft);
    
    // 表单提交
    form.addEventListener('submit', handleSubmit);
    
    // 初始化函数
    function initializeForm() {
        loadDraft();
        setupAccessibility();
    }
    
    // 加载草稿
    function loadDraft() {
        const savedDraft = localStorage.getItem('assetDraft');
        if (savedDraft) {
            const draftData = JSON.parse(savedDraft);
            // 恢复表单字段
            for (let key in draftData.formFields) {
                const input = form.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = draftData.formFields[key];
                    // 触发change事件以更新联动效果
                    if (input.id === 'type') {
                        input.dispatchEvent(new Event('change'));
                    }
                }
            }
            // 更新字符计数
            if (descriptionField.value) {
                descriptionCount.textContent = descriptionField.value.length;
            }
        }
    }
    
    // 设置可访问性
    function setupAccessibility() {
        [imageUploadArea, documentUploadArea].forEach(area => {
            area.setAttribute('role', 'button');
            area.setAttribute('tabindex', '0');
        });
    }
    
    // 处理资产类型变化
    function handleAssetTypeChange(selectedType) {
        // 处理面积字段
        if (selectedType === '10') { // 不动产
            areaField.setAttribute('required', 'required');
            areaField.closest('.asset-area-group').classList.remove('d-none');
        } else {
            areaField.removeAttribute('required');
            areaField.closest('.asset-area-group').classList.add('d-none');
        }
        
        // 显示对应的文档要求
        document.querySelectorAll('[data-asset-type]').forEach(el => {
            el.classList.toggle('d-none', el.dataset.assetType !== selectedType);
        });
    }
    
    // 设置文件上传
    function setupFileUpload(dropArea, input, handler, type) {
        // 点击上传
        dropArea.addEventListener('click', () => {
            input.value = ''; // 清除之前的选择
            input.click();
        });
        
        // 拖拽处理
        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.classList.add('dragover');
        });
        
        dropArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.classList.remove('dragover');
        });
        
        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            console.log('拖拽文件数量:', files.length);
            if (files.length > 0) {
                handler(files);
            }
        });
        
        // 文件选择处理
        input.addEventListener('change', function(e) {
            console.log('选择文件数量:', this.files.length);
            if (this.files.length > 0) {
                handler(this.files);
            }
        });
    }
    
    // 保存草稿
    function saveDraft() {
        const formData = new FormData(form);
        const draftData = {
            formFields: {},
            files: {
                images: Array.from(uploadedFiles.images.keys()),
                documents: Array.from(uploadedFiles.documents.keys())
            }
        };
        
        for (let [key, value] of formData.entries()) {
            if (!key.endsWith('[]')) {
                draftData.formFields[key] = value;
            }
        }
        
        localStorage.setItem('assetDraft', JSON.stringify(draftData));
        draftSavedToast.show();
    }
    
    // 验证必需的文件
    function validateRequiredFiles() {
        // 验证图片
        if (uploadedFiles.images.size === 0) {
            showError('请至少上传一张资产图片');
            return false;
        }
        
        // 验证文档
        const assetType = document.getElementById('type').value;
        const requiredDocs = {
            '10': ['房产证', '土地证', '评估报告'],
            '20': ['拍卖证书', '展览文件', '资产证明']
        }[assetType] || [];
        
        if (uploadedFiles.documents.size === 0) {
            showError(`请上传必需的资产文档：${requiredDocs.join('、')}`);
            return false;
        }
        
        return true;
    }
    
    // 处理表单提交
    async function handleSubmit(e) {
        e.preventDefault();
        
        try {
            // 基础表单验证
            if (!form.checkValidity()) {
                e.stopPropagation();
                form.classList.add('was-validated');
                showError('请填写所有必填字段');
                return;
            }
            
            // 验证文件
            if (!validateRequiredFiles()) {
                return;
            }
            
            // 验证数值
            const totalValue = parseFloat(document.getElementById('totalValue').value);
            const annualRevenue = parseFloat(document.getElementById('annualRevenue').value);
            
            if (annualRevenue > totalValue) {
                showError('预期年收益不能大于资产总价值');
                return;
            }
            
            // 禁用提交按钮并显示加载状态
            submitBtn.disabled = true;
            submitBtn.querySelector('.spinner-border').classList.remove('d-none');
            
            const formData = new FormData(form);
            
            // 添加资产类型
            formData.append('asset_type', assetTypeSelect.value);
            
            // 添加图片文件
            uploadedFiles.images.forEach((file, name) => {
                formData.append('images[]', file);
            });
            
            // 添加文档文件
            uploadedFiles.documents.forEach((file, name) => {
                formData.append('documents[]', file);
            });
            
            // 提交表单
            const response = await submitWithRetry(formData);
            
            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || '创建资产失败');
            }
            
            const result = await response.json();
            
            // 清除草稿
            localStorage.removeItem('assetDraft');
            
            // 显示成功提示
            const successToast = new bootstrap.Toast(document.getElementById('draftSavedToast'));
            document.querySelector('#draftSavedToast .toast-body').textContent = '资产创建成功，正在跳转...';
            successToast.show();
            
            // 延迟跳转
            setTimeout(() => {
                window.location.href = result.redirect || '/assets';
            }, 1500);
            
        } catch (error) {
            console.error('提交失败:', error);
            showError(error.message || '网络错误，请稍后重试');
        } finally {
            submitBtn.disabled = false;
            submitBtn.querySelector('.spinner-border').classList.add('d-none');
        }
    }
    
    // 图片处理函数
    function handleImageFiles(files) {
        console.log('开始处理图片文件:', files.length, '个文件');
        
        // 检查预览容器是否存在
        const imagePreview = document.getElementById('imagePreview');
        if (!imagePreview) {
            console.error('找不到图片预览容器');
            showError('系统错误：图片预览组件未找到');
            return;
        }
        
        // 隐藏之前的错误提示
        const errorDiv = document.getElementById('imageUploadError');
        if (errorDiv) {
            errorDiv.classList.add('d-none');
            errorDiv.textContent = '';
        }
        
        // 文件验证
        const validFiles = validateFiles(files, {
            types: ['image/jpeg', 'image/jpg', 'image/png'],
            maxSize: 6 * 1024 * 1024,  // 6MB
            maxCount: 10,
            maxDimension: 4096, // 最大尺寸4096px
            errorMessages: {
                type: '只支持 JPG、JPEG、PNG 格式的图片',
                size: '图片大小不能超过 6MB',
                count: '最多只能上传 10 张图片',
                dimension: '图片尺寸不能超过 4096x4096'
            }
        });
        
        console.log('验证通过的文件数量:', validFiles.length);
        if (validFiles.length === 0) return;
        
        // 检查总数限制
        const currentCount = uploadedFiles.images.size;
        console.log('当前已有图片数量:', currentCount);
        if (currentCount + validFiles.length > 10) {
            showImageError('图片总数不能超过 10 张');
            return;
        }
        
        // 显示进度条
        const progressContainer = document.getElementById('imageUploadProgress');
        const progressBar = progressContainer?.querySelector('.progress-bar');
        if (progressContainer && progressBar) {
            progressContainer.classList.remove('d-none');
            progressBar.style.width = '0%';
        }
        
        let processedCount = 0;
        validFiles.forEach((file, index) => {
            console.log(`处理第 ${index + 1} 张图片:`, file.name);
            
            // 创建临时的加载状态预览
            const tempPreview = createLoadingPreview(file.name);
            
            const reader = new FileReader();
            reader.onload = async function(e) {
                try {
                    console.log(`图片 ${file.name} 读取完成，开始处理`);
                    
                    // 压缩图片
                    const compressedImage = await compressImage(e.target.result, {
                        maxWidth: 2048,
                        maxHeight: 2048,
                        quality: 0.8
                    });
                    
                    console.log(`图片 ${file.name} 压缩完成`);
                    
                    // 移除加载状态预览
                    if (tempPreview) {
                        tempPreview.remove();
                    }
                    
                    // 创建实际预览
                    createImagePreview(file, compressedImage);
                    uploadedFiles.images.set(file.name, dataURLtoFile(compressedImage, file.name));
                    
                    // 更新进度
                    processedCount++;
                    const progress = (processedCount / validFiles.length) * 100;
                    updateImageProgress(progress);
                    
                    console.log(`图片 ${file.name} 处理完成，进度: ${progress}%`);
                    
                    // 所有文件处理完成
                    if (processedCount === validFiles.length) {
                        console.log('所有图片处理完成');
                        setTimeout(() => {
                            if (progressContainer && progressBar) {
                                progressContainer.classList.add('d-none');
                                progressBar.style.width = '0%';
                            }
                        }, 500);
                    }
                } catch (error) {
                    console.error(`处理图片 ${file.name} 失败:`, error);
                    showImageError(`处理图片 ${file.name} 失败: ${error.message}`);
                    if (tempPreview) {
                        tempPreview.remove();
                    }
                    processedCount++;
                }
            };
            
            reader.onerror = function(error) {
                console.error(`读取图片 ${file.name} 失败:`, error);
                showImageError(`读取图片 ${file.name} 失败`);
                if (tempPreview) {
                    tempPreview.remove();
                }
                processedCount++;
            };
            
            console.log(`开始读取图片 ${file.name}`);
            reader.readAsDataURL(file);
        });
    }
    
    // 创建加载状态预览
    function createLoadingPreview(filename) {
        const div = document.createElement('div');
        div.className = 'col-md-4 col-lg-3';
        div.innerHTML = `
            <div class="card h-100">
                <div class="card-img-wrapper d-flex align-items-center justify-content-center bg-light">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                </div>
                <div class="card-body">
                    <p class="card-text small text-truncate mb-0">${filename}</p>
                    <small class="text-muted">处理中...</small>
                </div>
            </div>
        `;
        
        document.getElementById('imagePreview').appendChild(div);
        return div;
    }
    
    // 压缩图片
    async function compressImage(dataURL, options = {}) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                let { width, height } = img;
                
                // 计算缩放比例
                if (width > options.maxWidth) {
                    height *= options.maxWidth / width;
                    width = options.maxWidth;
                }
                if (height > options.maxHeight) {
                    width *= options.maxHeight / height;
                    height = options.maxHeight;
                }
                
                canvas.width = width;
                canvas.height = height;
                
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                
                // 转换为 base64
                resolve(canvas.toDataURL('image/jpeg', options.quality || 0.8));
            };
            img.onerror = reject;
            img.src = dataURL;
        });
    }
    
    // 将 base64 转换为文件对象
    function dataURLtoFile(dataURL, filename) {
        const arr = dataURL.split(',');
        const mime = arr[0].match(/:(.*?);/)[1];
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        
        return new File([u8arr], filename, { type: mime });
    }
    
    function handleDocumentFiles(files) {
        const validFiles = validateFiles(files, {
            types: [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ],
            maxSize: 10 * 1024 * 1024,
            maxCount: 5,
            errorMessages: {
                type: _('只支持 PDF、DOC、DOCX 格式的文档'),
                size: _('文档大小不能超过 10MB'),
                count: _('最多只能上传 5 个文档')
            }
        });
        
        if (validFiles.length === 0) return;
        
        // 检查总数限制
        const currentCount = documentPreview.children.length;
        if (currentCount + validFiles.length > 5) {
            showError(_('文档总数不能超过 5 个'));
            return;
        }
        
        const progressBar = document.querySelector('#documentUploadProgress .progress-bar');
        const progressContainer = document.getElementById('documentUploadProgress');
        showProgress(progressContainer, progressBar, validFiles.length);
        
        validFiles.forEach(file => {
            createDocumentPreview(file);
        });
        
        setTimeout(() => {
            hideProgress(progressContainer, progressBar);
        }, 500);
    }
    
    // 验证文件
    function validateFiles(files, options) {
        const validFiles = [];
        const errors = [];
        
        // 检查文件数量
        if (files.length > options.maxCount) {
            showImageError(options.errorMessages.count);
            return [];
        }
        
        const checkImageDimensions = (file) => {
            return new Promise((resolve) => {
                const img = new Image();
                img.onload = function() {
                    if (img.width > options.maxDimension || img.height > options.maxDimension) {
                        errors.push(`${file.name}: ${options.errorMessages.dimension}`);
                        resolve(false);
                    } else {
                        resolve(true);
                    }
                };
                img.onerror = () => resolve(false);
                img.src = URL.createObjectURL(file);
            });
        };
        
        const validateFile = async (file) => {
            // 检查文件类型
            if (!options.types.includes(file.type)) {
                errors.push(`${file.name}: ${options.errorMessages.type}`);
                return;
            }
            
            // 检查文件大小
            if (file.size > options.maxSize) {
                errors.push(`${file.name}: ${options.errorMessages.size}`);
                return;
            }
            
            // 检查图片尺寸
            if (await checkImageDimensions(file)) {
                validFiles.push(file);
            }
        };
        
        // 等待所有文件验证完成
        Promise.all(Array.from(files).map(validateFile)).then(() => {
            if (errors.length > 0) {
                showImageError(errors.join('\n'));
            }
        });
        
        return validFiles;
    }
    
    function createImagePreview(file, dataUrl) {
        console.log('创建图片预览:', file.name);
        
        const imagePreview = document.getElementById('imagePreview');
        if (!imagePreview) {
            console.error('找不到图片预览容器');
            return;
        }
        
        const div = document.createElement('div');
        div.className = 'col-md-4 col-lg-3 mb-3';
        div.innerHTML = `
            <div class="card h-100">
                <div class="card-img-wrapper">
                    <img src="${dataUrl}" class="card-img-top" alt="${file.name}" loading="lazy" 
                        onerror="this.onerror=null; this.src='/static/images/image-error.png';">
                    <div class="card-img-overlay d-flex justify-content-end">
                        <button type="button" class="btn btn-danger btn-sm remove-file" aria-label="删除图片">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <p class="card-text small text-truncate mb-0">${file.name}</p>
                    <small class="text-muted">${formatFileSize(file.size)}</small>
                </div>
            </div>
        `;
        
        imagePreview.appendChild(div);
        
        // 删除按钮事件
        const removeButton = div.querySelector('.remove-file');
        if (removeButton) {
            removeButton.addEventListener('click', function() {
                if (confirm('确定要删除这张图片吗？')) {
                    uploadedFiles.images.delete(file.name);
                    div.remove();
                    console.log(`已删除图片: ${file.name}`);
                }
            });
        }
        
        console.log(`图片预览创建完成: ${file.name}`);
    }
    
    function createDocumentPreview(file) {
        const div = document.createElement('div');
        div.className = 'list-group-item d-flex justify-content-between align-items-center';
        div.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="far fa-file-${getFileIcon(file.type)} fa-2x me-3"></i>
                <div>
                    <div class="text-truncate" style="max-width: 200px;">${file.name}</div>
                    <small class="text-muted">${formatFileSize(file.size)}</small>
                </div>
            </div>
            <button type="button" class="btn btn-danger btn-sm remove-file" aria-label="${_('删除文件')}">
                <i class="fas fa-trash"></i>
            </button>
        `;
        documentPreview.appendChild(div);
        
        uploadedFiles.documents.set(file.name, file);
        
        div.querySelector('.remove-file').addEventListener('click', function() {
            if (confirm(_('确定要删除这个文档吗？'))) {
                uploadedFiles.documents.delete(file.name);
                div.remove();
            }
        });
    }
    
    function showProgress(container, bar, total) {
        container.classList.remove('d-none');
        bar.style.width = '0%';
        bar.setAttribute('aria-valuenow', 0);
    }
    
    function updateProgress(container, bar, current, total) {
        const progress = (current / total) * 100;
        bar.style.width = `${progress}%`;
        bar.setAttribute('aria-valuenow', progress);
        
        if (current === total) {
            setTimeout(() => hideProgress(container, bar), 500);
        }
    }
    
    function hideProgress(container, bar) {
        container.classList.add('d-none');
        bar.style.width = '0%';
        bar.setAttribute('aria-valuenow', 0);
    }
    
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.add('dragover');
    }
    
    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.classList.remove('dragover');
    }
    
    function getFileIcon(type) {
        switch (type) {
            case 'application/pdf':
                return 'pdf';
            case 'application/msword':
            case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                return 'word';
            default:
                return 'alt';
        }
    }
    
    function showError(message) {
        const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
        const errorMessage = document.getElementById('errorMessage');
        errorMessage.textContent = message;
        
        // 添加图标
        const icon = document.createElement('i');
        icon.className = 'fas fa-exclamation-circle me-2 text-danger';
        errorMessage.insertBefore(icon, errorMessage.firstChild);
        
        errorModal.show();
    }

    // Token数量计算和显示
    function setupTokenSupplyCalculation() {
        const assetTypeSelect = document.getElementById('type');
        const areaInput = document.getElementById('area');
        const tokenSupplyInput = document.getElementById('tokenSupply');
        const totalValueInput = document.getElementById('totalValue');
        const tokenPriceInput = document.getElementById('tokenPrice');
        const tokenSupplyGroup = document.querySelector('.token-supply-group');
        const tokenSupplyDisplay = document.createElement('div');
        tokenSupplyDisplay.className = 'form-text mt-1';
        tokenSupplyGroup.appendChild(tokenSupplyDisplay);

        // 监听资产类型变化
        assetTypeSelect.addEventListener('change', function() {
            const isRealEstate = this.value === '10';
            tokenSupplyInput.readOnly = isRealEstate;
            tokenSupplyInput.value = '';
            tokenSupplyDisplay.textContent = '';
            tokenPriceInput.value = '';
            
            if (isRealEstate) {
                // 如果是不动产，显示自动计算提示
                tokenSupplyDisplay.textContent = '代币数量将根据面积自动计算';
                // 如果已有面积，立即计算
                if (areaInput.value) {
                    calculateTokenSupply(parseFloat(areaInput.value));
                }
            } else {
                // 如果是类不动产，显示手动输入提示
                tokenSupplyDisplay.textContent = '请输入代币发行总量';
                tokenSupplyInput.removeAttribute('readonly');
            }
        });

        // 监听面积输入变化（不动产）
        areaInput.addEventListener('input', function() {
            if (assetTypeSelect.value === '10') {
                const area = parseFloat(this.value);
                if (!isNaN(area) && area > 0) {
                    calculateTokenSupply(area);
                } else {
                    tokenSupplyInput.value = '';
                    tokenPriceInput.value = '';
                    tokenSupplyDisplay.textContent = '请输入有效的面积';
                }
            }
        });

        // 监听代币数量输入（类不动产）
        tokenSupplyInput.addEventListener('input', function() {
            if (assetTypeSelect.value === '20') {
                const value = parseInt(this.value);
                if (!isNaN(value)) {
                    if (value <= 0) {
                        tokenSupplyDisplay.textContent = '代币发行量必须大于0';
                        tokenSupplyDisplay.classList.add('text-danger');
                        this.setCustomValidity('代币发行量必须大于0');
                    } else if (value > 100000000) {
                        tokenSupplyDisplay.textContent = '代币发行量不能超过1亿';
                        tokenSupplyDisplay.classList.add('text-danger');
                        this.setCustomValidity('代币发行量不能超过1亿');
                    } else {
                        tokenSupplyDisplay.textContent = `总发行量: ${value.toLocaleString()} 代币`;
                        tokenSupplyDisplay.classList.remove('text-danger');
                        this.setCustomValidity('');
                        calculateTokenPrice();
                    }
                }
            }
        });

        // 监听总价值变化
        totalValueInput.addEventListener('input', function() {
            const totalValue = parseFloat(this.value);
            if (!isNaN(totalValue) && totalValue > 0) {
                calculateTokenPrice();
            } else {
                tokenPriceInput.value = '';
            }
        });

        // 计算代币数量（不动产）
        function calculateTokenSupply(area) {
            if (!isNaN(area) && area > 0) {
                const tokenSupply = Math.floor(area * 10000); // 1平方米 = 10000代币
                tokenSupplyInput.value = tokenSupply;
                tokenSupplyDisplay.textContent = `总发行量: ${tokenSupply.toLocaleString()} 代币 (${area}㎡ × 10000)`;
                calculateTokenPrice();
            }
        }

        // 计算代币价格
        function calculateTokenPrice() {
            const totalValue = parseFloat(totalValueInput.value);
            const tokenSupply = parseInt(tokenSupplyInput.value);
            
            if (!isNaN(totalValue) && !isNaN(tokenSupply) && totalValue > 0 && tokenSupply > 0) {
                const tokenPrice = totalValue / tokenSupply;
                tokenPriceInput.value = tokenPrice.toFixed(6);
            } else {
                tokenPriceInput.value = '';
            }
        }

        // 初始化时如果已有值则计算
        if (assetTypeSelect.value === '10' && areaInput.value) {
            calculateTokenSupply(parseFloat(areaInput.value));
        } else if (assetTypeSelect.value === '20' && tokenSupplyInput.value) {
            const value = parseInt(tokenSupplyInput.value);
            if (!isNaN(value) && value > 0) {
                tokenSupplyDisplay.textContent = `总发行量: ${value.toLocaleString()} 代币`;
                calculateTokenPrice();
            }
        }
    }

    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 更新上传进度
    function updateImageProgress(progress) {
        const progressBar = document.querySelector('#imageUploadProgress .progress-bar');
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
    }

    // 显示图片错误
    function showImageError(message) {
        console.error('图片错误:', message);
        const errorDiv = document.getElementById('imageUploadError');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('d-none');
        } else {
            console.error('找不到错误提示容器');
            showError(message);
        }
    }
}); 