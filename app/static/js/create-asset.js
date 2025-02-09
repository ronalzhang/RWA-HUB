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
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                },
                credentials: 'same-origin'
            });
            return response;
        } catch (error) {
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
        dropArea.addEventListener('click', () => input.click());
        dropArea.addEventListener('dragover', handleDragOver);
        dropArea.addEventListener('dragleave', handleDragLeave);
        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.classList.remove('dragover');
            handler(e.dataTransfer.files);
        });
        
        input.addEventListener('change', function() {
            handler(this.files);
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
    
    // 处理表单提交
    async function handleSubmit(e) {
        e.preventDefault();
        
        if (!form.checkValidity()) {
            e.stopPropagation();
            form.classList.add('was-validated');
            return;
        }
        
        if (!validateRequiredFiles()) {
            return;
        }
        
        try {
            submitBtn.disabled = true;
            submitBtn.querySelector('.spinner-border').classList.remove('d-none');
            
            const formData = new FormData(form);
            // 添加文件数据
            uploadedFiles.images.forEach((file, name) => {
                formData.append('images[]', file);
            });
            uploadedFiles.documents.forEach((file, name) => {
                formData.append('documents[]', file);
            });
            
            const response = await submitWithRetry(formData);
            const result = await response.json();
            
            if (response.ok) {
                localStorage.removeItem('assetDraft');
                window.location.href = result.redirect || '/assets';
            } else {
                showError(result.error || _('Failed to create asset'));
            }
        } catch (error) {
            showError(_('Network error occurred'));
        } finally {
            submitBtn.disabled = false;
            submitBtn.querySelector('.spinner-border').classList.add('d-none');
        }
    }
    
    // 文件处理函数
    function handleImageFiles(files) {
        const validFiles = validateFiles(files, {
            types: ['image/jpeg', 'image/png', 'image/webp'],
            maxSize: 5 * 1024 * 1024,
            maxCount: 10,
            errorMessages: {
                type: _('只支持 JPG、PNG、WEBP 格式的图片'),
                size: _('图片大小不能超过 5MB'),
                count: _('最多只能上传 10 张图片')
            }
        });
        
        if (validFiles.length === 0) return;
        
        // 检查总数限制
        const currentCount = imagePreview.children.length;
        if (currentCount + validFiles.length > 10) {
            showError(_('图片总数不能超过 10 张'));
            return;
        }
        
        const progressBar = document.querySelector('#imageUploadProgress .progress-bar');
        const progressContainer = document.getElementById('imageUploadProgress');
        showProgress(progressContainer, progressBar, validFiles.length);
        
        let processed = 0;
        validFiles.forEach(file => {
            const reader = new FileReader();
            reader.onload = function(e) {
                createImagePreview(file, e.target.result);
                updateProgress(progressContainer, progressBar, ++processed, validFiles.length);
            };
            reader.readAsDataURL(file);
        });
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
            showError(options.errorMessages.count);
            return [];
        }
        
        Array.from(files).forEach(file => {
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
            
            validFiles.push(file);
        });
        
        // 显示所有错误
        if (errors.length > 0) {
            showError(errors.join('\n'));
        }
        
        return validFiles;
    }
    
    function createImagePreview(file, dataUrl) {
        const div = document.createElement('div');
        div.className = 'col-md-4 col-lg-3';
        div.innerHTML = `
            <div class="card h-100">
                <div class="card-img-wrapper">
                    <img src="${dataUrl}" class="card-img-top" alt="${_('预览')}" loading="lazy">
                    <div class="card-img-overlay d-flex justify-content-end">
                        <button type="button" class="btn btn-danger btn-sm remove-file" aria-label="${_('删除文件')}">
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
        
        uploadedFiles.images.set(file.name, file);
        
        div.querySelector('.remove-file').addEventListener('click', function() {
            if (confirm(_('确定要删除这张图片吗？'))) {
                uploadedFiles.images.delete(file.name);
                div.remove();
            }
        });
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
    
    function validateRequiredFiles() {
        const selectedType = assetTypeSelect.value;
        const hasImages = imagePreview.children.length > 0;
        const hasDocuments = documentPreview.children.length > 0;
        
        if (!hasImages) {
            showError(_('Please upload at least one image'));
            return false;
        }
        
        const requiredDocCount = selectedType === '10' ? 3 : 3;
        if (!hasDocuments || documentPreview.children.length < requiredDocCount) {
            showError(_(`Please upload all required documents (${requiredDocCount} documents needed)`));
            return false;
        }
        
        return true;
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
        document.getElementById('errorMessage').textContent = message;
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
}); 