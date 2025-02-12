// 表单验证和提交处理
document.addEventListener('DOMContentLoaded', async function() {
    // 检查钱包连接状态
    if (!window.walletState || !window.walletState.isConnected || !window.walletState.currentAccount) {
        showError('Please connect your wallet first');
        return;
    }

    // 获取必要的 DOM 元素
    const form = document.getElementById('assetForm');
    const typeSelect = document.getElementById('type');
    const areaGroup = document.querySelector('.asset-area-group');
    const tokenAmountGroup = document.querySelector('.token-amount-group');
    const imageUpload = document.getElementById('imageUpload');
    const documentUpload = document.getElementById('documentUpload');
    const imagePreview = document.getElementById('imagePreview');
    const documentPreview = document.getElementById('documentPreview');
    const saveDraftBtn = document.getElementById('saveDraft');
    const submitBtn = document.querySelector('button[type="submit"]');
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    const errorMessage = document.getElementById('errorMessage');
    const calculationInfo = document.getElementById('calculationInfo');

    // 获取价值相关的输入元素
    const areaInput = document.getElementById('area');
    const totalValueInput = document.getElementById('totalValue');
    const tokenAmountInput = document.getElementById('tokenAmount');
    const tokenPriceInput = document.getElementById('tokenPrice');
    const annualRevenueInput = document.getElementById('annualRevenue');
    
    // Constants
    const FILE_SIZE_LIMIT = 6 * 1024 * 1024; // 6MB
    const IMAGE_COUNT_LIMIT = 10;
    const DOC_COUNT_LIMIT = 5;
    
    // Field validation rules
    const validateField = (field, value) => {
        switch(field) {
            case 'name':
                return value.length >= 2 && value.length <= 100;
            case 'location':
                return value.length >= 5 && value.length <= 200;
            case 'description':
                return value.length >= 10 && value.length <= 1000;
            case 'totalValue':
                return value > 0 && value <= 1000000000000;
            case 'tokenPrice':
                return value > 0 && value <= 1000000000;
            case 'annualRevenue':
                const totalValue = parseFloat(totalValueInput.value) || 0;
                return value > 0 && value <= totalValue;
            case 'area':
                return value > 0 && value <= 1000000;
            case 'tokenAmount':
                return value > 0;
            default:
                return true;
        }
    };
    
    // Add field validation
    ['name', 'location', 'description', 'totalValue', 'tokenPrice', 'annualRevenue', 'area', 'tokenAmount'].forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            element.addEventListener('input', () => {
                const value = element.value.trim();
                if (!validateField(field, value)) {
                    let errorMessage = `Invalid ${field.replace(/([A-Z])/g, ' $1').toLowerCase()}`;
                    switch(field) {
                        case 'name':
                            errorMessage = 'Name must be between 2 and 100 characters';
                            break;
                        case 'location':
                            errorMessage = 'Location must be between 5 and 200 characters';
                            break;
                        case 'description':
                            errorMessage = 'Description must be between 10 and 1000 characters';
                            break;
                        case 'totalValue':
                            errorMessage = 'Total value must be greater than 0 and not exceed 1 trillion';
                            break;
                        case 'annualRevenue':
                            errorMessage = 'Annual revenue must be greater than 0 and not exceed total value';
                            break;
                        case 'area':
                            errorMessage = 'Area must be greater than 0 and not exceed 1,000,000';
                            break;
                        case 'tokenAmount':
                            errorMessage = 'Token amount must be greater than 0';
                            break;
                    }
                    element.setCustomValidity(errorMessage);
                } else {
                    element.setCustomValidity('');
                }
                element.reportValidity();
                
                // 如果是影响计算的字段，更新计算结果
                if (['area', 'totalValue', 'tokenAmount'].includes(field)) {
                    updateTokenCalculation();
                }
            });
        }
    });

    // 资产类型切换处理
    typeSelect.addEventListener('change', function() {
        // 清空所有计算相关的输入值
        areaInput.value = '';
        tokenAmountInput.value = '';
        tokenPriceInput.value = '';
        calculationInfo.style.display = 'none';
        calculationInfo.innerHTML = '';

        // 重置验证状态
        [areaInput, tokenAmountInput, tokenPriceInput].forEach(input => {
            input.setCustomValidity('');
            input.classList.remove('is-invalid', 'is-valid');
        });

        if (this.value === '10') { // 不动产
            // 显示面积输入，隐藏代币数量输入
            areaGroup.style.display = 'block';
            tokenAmountGroup.style.display = 'none';
            areaInput.required = true;
            tokenAmountInput.required = false;
            
            // 显示不动产相关文档要求
            document.querySelector('.real-estate-docs').style.display = 'block';
            document.querySelector('.similar-assets-docs').style.display = 'none';
            
            // 更新帮助文本
            document.querySelector('#tokenPrice').nextElementSibling.textContent = 
                'Automatically calculated based on area (10,000 tokens per square meter)';
        } else if (this.value === '20') { // 类不动产
            // 显示代币数量输入，隐藏面积输入
            areaGroup.style.display = 'none';
            tokenAmountGroup.style.display = 'block';
            areaInput.required = false;
            tokenAmountInput.required = true;
            
            // 显示类不动产相关文档要求
            document.querySelector('.real-estate-docs').style.display = 'none';
            document.querySelector('.similar-assets-docs').style.display = 'block';
            
            // 更新帮助文本
            document.querySelector('#tokenPrice').nextElementSibling.textContent = 
                'Automatically calculated based on total value and token amount';
        }
        
        // 触发表单验证
        form.classList.add('was-validated');
    });

    // 代币数量计算和显示
    function updateTokenCalculation() {
        const assetType = typeSelect.value;
        const totalValue = parseFloat(totalValueInput.value) || 0;
        let tokenAmount = 0;
        let calculatedTokenPrice = 0;
        
        if (assetType === '10') { // 不动产
            const area = parseFloat(areaInput.value) || 0;
            if (area > 0 && totalValue > 0) {
                tokenAmount = area * 10000; // 每平米10000个代币
                calculatedTokenPrice = totalValue / tokenAmount;
                
                calculationInfo.innerHTML = `
                    <div class="mb-2">
                        <div>Total Tokens: <span class="value">${tokenAmount.toLocaleString()}</span></div>
                        <div>Tokens per Square Meter: <span class="value">10,000</span></div>
                        <div>Token Price: <span class="value">${calculatedTokenPrice.toFixed(6)} U</span></div>
                        <div>Total Value: <span class="value">${totalValue.toLocaleString()} U</span></div>
                    </div>
                `;
                calculationInfo.style.display = 'block';
            }
        } else if (assetType === '20') { // 类不动产
            tokenAmount = parseFloat(tokenAmountInput.value) || 0;
            if (tokenAmount > 0 && totalValue > 0) {
                calculatedTokenPrice = totalValue / tokenAmount;
                
                calculationInfo.innerHTML = `
                    <div class="mb-2">
                        <div>Total Tokens: <span class="value">${tokenAmount.toLocaleString()}</span></div>
                        <div>Token Price: <span class="value">${calculatedTokenPrice.toFixed(6)} U</span></div>
                        <div>Total Value: <span class="value">${totalValue.toLocaleString()} U</span></div>
                    </div>
                `;
                calculationInfo.style.display = 'block';
            }
        }
        
        // 更新代币价格输入框
        if (calculatedTokenPrice > 0) {
            tokenPriceInput.value = calculatedTokenPrice.toFixed(6);
        } else {
            tokenPriceInput.value = '';
            calculationInfo.style.display = 'none';
        }
    }

    // 图片上传处理
    setupFileUpload(imageUpload, imagePreview, ['image/jpeg', 'image/png', 'image/gif'], true);
    
    // 文档上传处理
    setupFileUpload(documentUpload, documentPreview, ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'], false);

    // 保存草稿
    saveDraftBtn.addEventListener('click', async function() {
        try {
            const formData = collectFormData();
            formData.append('is_draft', 'true');
            
            updateSubmitStatus(true, saveDraftBtn);
            const response = await submitData(formData);
            if (response.ok) {
                const result = await response.json();
                showSuccess('Draft saved successfully');
                setTimeout(() => {
                    window.location.href = `/assets/${result.id}`;
                }, 1500);
            }
        } catch (error) {
            showError(error.message);
        } finally {
            updateSubmitStatus(false, saveDraftBtn);
        }
    });

    // 表单提交处理
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        try {
            // 基础表单验证
            if (!form.checkValidity()) {
                e.stopPropagation();
                form.classList.add('was-validated');
                return;
            }

            // 更新提交状态
            updateSubmitStatus(true, submitBtn);

            // 自定义验证
            await validateForm();

            // 收集并提交数据
            const formData = collectFormData();
            const response = await submitData(formData);
            const result = await response.json();

            // 显示成功消息
            showSuccess('Asset created successfully');
            
            // 延迟跳转以显示成功消息
            setTimeout(() => {
                window.location.href = `/assets/${result.id}`;
            }, 1500);
        } catch (error) {
            showError(error.message);
        } finally {
            updateSubmitStatus(false, submitBtn);
        }
    });

    // 更新提交状态
    function updateSubmitStatus(isSubmitting, button) {
        if (isSubmitting) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        } else {
            button.disabled = false;
            button.innerHTML = button.id === 'saveDraft' ? 
                '<i class="fas fa-save me-1"></i>Save Draft' : 
                '<i class="fas fa-check me-1"></i>Create Asset';
        }
    }

    // 显示成功消息
    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'alert alert-success alert-dismissible fade show fixed-top m-3';
        successDiv.innerHTML = `
            <i class="fas fa-check-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(successDiv);
        
        // 3秒后自动关闭
        setTimeout(() => {
            successDiv.remove();
        }, 3000);
    }

    // 显示错误信息
    function showError(message) {
        if (errorModal && errorMessage) {
            errorMessage.innerHTML = `<i class="fas fa-exclamation-circle text-danger me-2"></i>${message}`;
            errorModal.show();
        } else {
            alert(message);
        }
    }

    // 收集表单数据
    function collectFormData() {
        const formData = new FormData();
        
        // 添加基本字段
        formData.append('name', document.getElementById('name').value.trim());
        formData.append('asset_type', typeSelect.value);
        formData.append('location', document.getElementById('location').value.trim());
        formData.append('description', document.getElementById('description').value.trim());
        formData.append('total_value', totalValueInput.value);
        formData.append('token_price', tokenPriceInput.value);
        formData.append('annual_revenue', annualRevenueInput.value);
        
        // 根据资产类型添加特定字段
        if (typeSelect.value === '10') {
            formData.append('area', areaInput.value);
            formData.append('token_amount', parseFloat(areaInput.value) * 10000);
        } else {
            formData.append('token_amount', tokenAmountInput.value);
        }
        
        // 添加图片文件（必须）
        const imageFiles = Array.from(imagePreview.querySelectorAll('img')).map(img => {
            return dataURLtoFile(img.src, `image_${Date.now()}.jpg`);
        });
        if (imageFiles.length === 0) {
            throw new Error('Please upload at least one asset image');
        }
        imageFiles.forEach(file => formData.append('images[]', file));
        
        // 添加文档文件（可选）
        const documentFiles = Array.from(documentPreview.querySelectorAll('.document-item')).map(item => {
            return item.file;
        });
        documentFiles.forEach(file => formData.append('documents[]', file));

        return formData;
    }

    // 提交数据到服务器
    async function submitData(formData) {
        if (!window.walletState || !window.walletState.isConnected || !window.walletState.currentAccount) {
            throw new Error('Please connect your wallet first');
        }

        const response = await fetch('/api/assets', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Eth-Address': window.walletState.currentAccount
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create asset');
        }

        return response;
    }

    // 表单提交验证
    async function validateForm() {
        // 验证图片上传
        const imageCount = imagePreview.querySelectorAll('img').length;
        if (imageCount === 0) {
            throw new Error('Please upload at least one asset image');
        }
        
        // 验证不动产类型特定字段
        if (typeSelect.value === '10') {
            const area = parseFloat(areaInput.value) || 0;
            const totalValue = parseFloat(totalValueInput.value) || 0;
            if (area <= 0) {
                throw new Error('Please enter valid building area');
            }
            if (totalValue <= 0) {
                throw new Error('Please enter valid total value');
            }
        }
        
        // 验证类不动产类型特定字段
        if (typeSelect.value === '20') {
            const tokenAmount = parseFloat(tokenAmountInput.value) || 0;
            const totalValue = parseFloat(totalValueInput.value) || 0;
            if (tokenAmount <= 0) {
                throw new Error('Please enter valid token amount');
            }
            if (totalValue <= 0) {
                throw new Error('Please enter valid total value');
            }
        }
        
        // 验证年收入
        const annualRevenue = parseFloat(annualRevenueInput.value) || 0;
        const totalValue = parseFloat(totalValueInput.value) || 0;
        if (annualRevenue <= 0) {
            throw new Error('Annual revenue must be greater than 0');
        }
        if (annualRevenue > totalValue) {
            throw new Error('Annual revenue cannot exceed total value');
        }
    }
});

// 将 Data URL 转换为 File 对象
function dataURLtoFile(dataurl, filename) {
    const arr = dataurl.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while(n--) {
        u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, {type: mime});
}

// 文件上传处理
function setupFileUpload(dropZone, previewZone, allowedTypes, isImage) {
    function validateFile(file) {
        if (file.size > FILE_SIZE_LIMIT) {
            throw new Error(`File size exceeds ${FILE_SIZE_LIMIT / 1024 / 1024}MB limit`);
        }
        
        if (isImage) {
            const imageCount = previewZone.querySelectorAll('img').length;
            if (imageCount >= IMAGE_COUNT_LIMIT) {
                throw new Error(`Maximum ${IMAGE_COUNT_LIMIT} images allowed`);
            }
        } else {
            const docCount = previewZone.querySelectorAll('.document-item').length;
            if (docCount >= DOC_COUNT_LIMIT) {
                throw new Error(`Maximum ${DOC_COUNT_LIMIT} documents allowed`);
            }
        }
        
        if (!allowedTypes.includes(file.type)) {
            throw new Error(`Unsupported file type: ${file.type}`);
        }
    }

    function handleFiles(files) {
        Array.from(files).forEach(file => {
            try {
                validateFile(file);
                processFile(file);
            } catch (error) {
                showError(error.message);
            }
        });
    }

    function processFile(file) {
        if (isImage) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const wrapper = document.createElement('div');
                wrapper.className = 'col-4 position-relative';
                
                const img = document.createElement('img');
                img.src = e.target.result;
                img.className = 'img-thumbnail';
                img.style.objectFit = 'cover';
                img.style.height = '200px';
                
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn btn-danger btn-sm position-absolute top-0 end-0 m-2';
                deleteBtn.innerHTML = '<i class="fas fa-times"></i>';
                deleteBtn.onclick = () => wrapper.remove();
                
                wrapper.appendChild(img);
                wrapper.appendChild(deleteBtn);
                previewZone.appendChild(wrapper);
            };
            reader.readAsDataURL(file);
        } else {
            const div = document.createElement('div');
            div.className = 'document-item mb-2 d-flex align-items-center justify-content-between';
            div.innerHTML = `
                <div>
                    <i class="fas fa-file me-2"></i>
                    <span>${file.name}</span>
                </div>
                <button type="button" class="btn btn-danger btn-sm">
                    <i class="fas fa-times"></i>
                </button>
            `;
            div.querySelector('button').onclick = () => div.remove();
            div.file = file;
            previewZone.appendChild(div);
        }
    }

    // 拖拽上传处理
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    // 点击上传处理
    dropZone.addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = allowedTypes.join(',');
        input.onchange = (e) => handleFiles(e.target.files);
        input.click();
    });
}