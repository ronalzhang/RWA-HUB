// 表单验证和提交处理
document.addEventListener('DOMContentLoaded', function() {
    // 获取必要的 DOM 元素
    const form = document.getElementById('assetForm');
    const typeSelect = document.getElementById('type');
    const areaGroup = document.querySelector('.asset-area-group');
    const imageUpload = document.getElementById('imageUpload');
    const documentUpload = document.getElementById('documentUpload');
    const imagePreview = document.getElementById('imagePreview');
    const documentPreview = document.getElementById('documentPreview');
    const saveDraftBtn = document.getElementById('saveDraft');
    const submitBtn = document.querySelector('button[type="submit"]');
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    const errorMessage = document.getElementById('errorMessage');

    // 获取价值相关的输入元素
    const areaInput = document.getElementById('area');
    const totalValueInput = document.getElementById('totalValue');
    const tokenPriceInput = document.getElementById('tokenPrice');
    const annualRevenueInput = document.getElementById('annualRevenue');
    
    // 添加计算提示元素
    const calculationInfo = document.createElement('div');
    calculationInfo.className = 'calculation-info mt-2 text-muted small';
    document.querySelector('.asset-area-group').appendChild(calculationInfo);
    
    // 初始化时隐藏面积输入框
    areaGroup.style.display = 'none';

    // Constants
    const FILE_SIZE_LIMIT = 10 * 1024 * 1024; // 10MB
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
                return value > 0 && value <= 100;
            case 'area':
                return value > 0 && value <= 1000000;
            default:
                return true;
        }
    };
    
    // Add field validation
    ['name', 'location', 'description', 'totalValue', 'tokenPrice', 'annualRevenue', 'area'].forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            element.addEventListener('input', () => {
                if (!validateField(field, element.value)) {
                    element.setCustomValidity(`Invalid ${field.replace(/([A-Z])/g, ' $1').toLowerCase()}`);
                } else {
                    element.setCustomValidity('');
                }
                element.reportValidity();
            });
        }
    });

    // 资产类型切换处理
    typeSelect.addEventListener('change', function() {
        if (this.value === '10') { // 不动产
            areaGroup.style.display = 'block';
            areaGroup.querySelector('input').required = true;
            // 显示不动产相关文档要求
            document.querySelector('.real-estate-docs').style.display = 'block';
            document.querySelector('.similar-assets-docs').style.display = 'none';
        } else if (this.value === '20') { // 类不动产
            areaGroup.style.display = 'none';
            areaGroup.querySelector('input').required = false;
            areaGroup.querySelector('input').value = '';
            // 显示类不动产相关文档要求
            document.querySelector('.real-estate-docs').style.display = 'none';
            document.querySelector('.similar-assets-docs').style.display = 'block';
        } else {
            areaGroup.style.display = 'none';
            areaGroup.querySelector('input').required = false;
            // 隐藏所有文档要求
            document.querySelector('.real-estate-docs').style.display = 'none';
            document.querySelector('.similar-assets-docs').style.display = 'none';
        }
        updateTokenCalculation();
    });

    // 图片上传处理
    setupFileUpload(imageUpload, imagePreview, ['image/jpeg', 'image/png', 'image/gif'], true);
    
    // 文档上传处理
    setupFileUpload(documentUpload, documentPreview, ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'], false);

    // 保存草稿
    saveDraftBtn.addEventListener('click', async function() {
        try {
            const formData = collectFormData();
            formData.append('is_draft', 'true');
            
            const response = await submitData(formData);
            if (response.ok) {
                const result = await response.json();
                alert('Draft saved successfully');
                window.location.href = `/assets/${result.id}`;
            }
        } catch (error) {
            showError(error.message);
        }
    });

    // 表单提交处理
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!form.checkValidity()) {
            e.stopPropagation();
            form.classList.add('was-validated');
            return;
        }

        try {
            updateSubmitStatus(true);
            await validateForm();
            const formData = collectFormData();
            const response = await submitData(formData);
            const result = await response.json();
            window.location.href = `/assets/${result.id}`;
        } catch (error) {
            showError(error.message);
        } finally {
            updateSubmitStatus(false);
        }
    });

    // 收集表单数据
    function collectFormData() {
        const formData = new FormData();
        
        // 添加基本字段
        formData.append('name', document.getElementById('name').value);
        formData.append('asset_type', document.getElementById('type').value);
        formData.append('location', document.getElementById('location').value);
        formData.append('description', document.getElementById('description').value);
        formData.append('total_value', document.getElementById('totalValue').value);
        formData.append('token_price', document.getElementById('tokenPrice').value);
        formData.append('annual_revenue', document.getElementById('annualRevenue').value);
        
        // 根据资产类型添加面积
        if (document.getElementById('type').value === '10') {
            formData.append('area', document.getElementById('area').value);
        }
        
        // 添加图片文件
        const imageFiles = Array.from(imagePreview.querySelectorAll('img')).map(img => {
            return dataURLtoFile(img.src, `image_${Date.now()}.jpg`);
        });
        imageFiles.forEach(file => formData.append('images[]', file));
        
        // 添加文档文件
        const documentFiles = Array.from(documentPreview.querySelectorAll('.document-item')).map(item => {
            return item.file;
        });
        documentFiles.forEach(file => formData.append('documents[]', file));

        return formData;
    }

    // 提交数据到服务器
    async function submitData(formData) {
        return await fetch('/api/assets', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Eth-Address': localStorage.getItem('userAddress')
            }
        });
    }

    // 显示错误信息
    function showError(message) {
        if (errorModal && errorMessage) {
            errorMessage.textContent = message;
            errorModal.show();
        } else {
            alert(message);
        }
    }

    // 代币数量计算和显示
    function updateTokenCalculation() {
        const area = parseFloat(areaInput.value) || 0;
        const assetType = typeSelect.value;
        const totalValue = parseFloat(totalValueInput.value) || 0;
        const tokenPrice = parseFloat(tokenPriceInput.value) || 0;
        
        if (assetType === '10' && area > 0) {
            const tokenAmount = area * 10000;
            const calculatedTotalValue = tokenAmount * tokenPrice;
            
            calculationInfo.innerHTML = `
                <div class="mb-2">
                    <div>Total Tokens: ${tokenAmount.toLocaleString()}</div>
                    <div>Tokens per Square Meter: 10,000</div>
                    ${tokenPrice > 0 ? `
                        <div>Token Price: ${tokenPrice.toLocaleString()} CNY</div>
                        <div>Calculated Total Value: ${calculatedTotalValue.toLocaleString()} CNY</div>
                        ${totalValue > 0 ? `
                            <div class="mt-2 ${Math.abs(calculatedTotalValue - totalValue) <= 0.01 ? 'text-success' : 'text-danger'}">
                                ${Math.abs(calculatedTotalValue - totalValue) <= 0.01 ? 
                                    '✓ Values match' : 
                                    '⚠ Values do not match'}
                            </div>
                        ` : ''}
                    ` : ''}
                </div>
            `;
            
            validatePrices(tokenAmount);
        } else if (assetType === '20') {
            if (totalValue > 0 && tokenPrice > 0) {
                const tokenAmount = Math.floor(totalValue / tokenPrice);
                calculationInfo.innerHTML = `
                    <div class="mb-2">
                        <div>Estimated Token Amount: ${tokenAmount.toLocaleString()}</div>
                        <div>Token Price: ${tokenPrice.toLocaleString()} CNY</div>
                        <div>Total Value: ${totalValue.toLocaleString()} CNY</div>
                    </div>
                `;
            } else {
                calculationInfo.innerHTML = '';
            }
        } else {
            calculationInfo.innerHTML = '';
        }
    }
    
    // 价格验证和实时计算
    function validatePrices(tokenAmount) {
        const totalValue = parseFloat(totalValueInput.value) || 0;
        const tokenPrice = parseFloat(tokenPriceInput.value) || 0;
        
        if (tokenAmount && tokenPrice) {
            const calculatedTotalValue = tokenAmount * tokenPrice;
            
            if (totalValue && Math.abs(calculatedTotalValue - totalValue) > 0.01) {
                totalValueInput.setCustomValidity('Total value does not match calculation from token amount and price');
                showCalculationError(`Current Settings:
                    <br>- Total Tokens: ${tokenAmount.toLocaleString()}
                    <br>- Token Price: ${tokenPrice.toLocaleString()} CNY
                    <br>- Calculated Total: ${calculatedTotalValue.toLocaleString()} CNY
                    <br>- Input Total: ${totalValue.toLocaleString()} CNY`);
            } else {
                totalValueInput.setCustomValidity('');
                hideCalculationError();
            }
        }
        
        const annualRevenue = parseFloat(annualRevenueInput.value) || 0;
        if (annualRevenue > 100) {
            annualRevenueInput.setCustomValidity('Annual revenue rate cannot exceed 100%');
        } else {
            annualRevenueInput.setCustomValidity('');
        }
        
        totalValueInput.reportValidity();
        annualRevenueInput.reportValidity();
    }
    
    // 显示计算错误
    function showCalculationError(message) {
        const errorDiv = document.getElementById('calculationError') || document.createElement('div');
        errorDiv.id = 'calculationError';
        errorDiv.className = 'alert alert-warning mt-2';
        errorDiv.innerHTML = message;
        totalValueInput.parentElement.appendChild(errorDiv);
    }
    
    // 隐藏计算错误
    function hideCalculationError() {
        const errorDiv = document.getElementById('calculationError');
        if (errorDiv) {
            errorDiv.remove();
        }
    }
    
    // 添加输入事件监听
    areaInput.addEventListener('input', updateTokenCalculation);
    totalValueInput.addEventListener('input', () => {
        if (typeSelect.value === '10') {
            updateTokenCalculation();
        }
    });
    tokenPriceInput.addEventListener('input', () => {
        if (typeSelect.value === '10') {
            updateTokenCalculation();
        }
    });
    annualRevenueInput.addEventListener('input', () => {
        const value = parseFloat(annualRevenueInput.value) || 0;
        if (value > 100) {
            annualRevenueInput.setCustomValidity('Annual revenue rate cannot exceed 100%');
        } else {
            annualRevenueInput.setCustomValidity('');
        }
        annualRevenueInput.reportValidity();
    });

    // Update file upload handling
    function setupFileUpload(dropZone, previewZone, allowedTypes, isImage) {
        function validateFile(file) {
            if (file.size > FILE_SIZE_LIMIT) {
                throw new Error(`File size exceeds ${FILE_SIZE_LIMIT / 1024 / 1024}MB limit`);
            }
            
            if (isImage) {
                const imageCount = imagePreview.querySelectorAll('img').length;
                if (imageCount >= IMAGE_COUNT_LIMIT) {
                    throw new Error(`Maximum ${IMAGE_COUNT_LIMIT} images allowed`);
                }
            } else {
                const docCount = documentPreview.querySelectorAll('.document-item').length;
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

    // Add global error handling
    window.addEventListener('unhandledrejection', function(event) {
        showError('An unexpected error occurred: ' + event.reason);
    });
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