// 表单验证和提交处理
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // 检查钱包连接状态
        await checkConnection();
        
        // 监听钱包状态变化
        if (window.ethereum) {
            window.ethereum.on('accountsChanged', async (accounts) => {
                if (accounts.length === 0) {
                    await clearWalletState();
                } else {
                    await checkConnection();
                }
            });

            window.ethereum.on('chainChanged', async () => {
                await checkConnection();
            });
        }

        // 初始化表单事件监听
        initFormEvents();
    } catch (error) {
        console.error('页面初始化失败:', error);
    }
});

// 检查钱包连接状态
async function checkConnection() {
    try {
        if (!window.ethereum) {
            throw new Error('未检测到 MetaMask');
        }

        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
        if (accounts.length > 0) {
            window.walletState.currentAccount = accounts[0];
            window.walletState.isConnected = true;
            updateUI(true);
        } else {
            await clearWalletState();
        }
    } catch (error) {
        console.error('检查钱包连接失败:', error);
        await clearWalletState();
    }
}

// 清除钱包状态
async function clearWalletState() {
    window.walletState.currentAccount = null;
    window.walletState.isConnected = false;
    window.walletState.isAdmin = false;
    window.walletState.permissions = [];
    
    // 清除事件监听器
    if (walletEventListeners && walletEventListeners.length) {
        walletEventListeners.forEach(listener => {
            if (window.ethereum) {
                window.ethereum.removeListener(listener.event, listener.callback);
            }
        });
        walletEventListeners = [];
    }
    
    updateUI(false);
}

// 更新 UI 显示
function updateUI(isConnected) {
    const connectBtn = document.getElementById('connect-wallet');
    const accountDisplay = document.getElementById('account-display');
    const createForm = document.getElementById('create-asset-form');
    
    if (isConnected && window.walletState.currentAccount) {
        connectBtn.style.display = 'none';
        accountDisplay.textContent = `${window.walletState.currentAccount.substring(0, 6)}...${window.walletState.currentAccount.substring(38)}`;
        accountDisplay.style.display = 'block';
        if (createForm) {
            createForm.style.display = 'block';
        }
    } else {
        connectBtn.style.display = 'block';
        accountDisplay.style.display = 'none';
        if (createForm) {
            createForm.style.display = 'none';
        }
    }
}

// 初始化表单事件
function initFormEvents() {
    const form = document.getElementById('create-asset-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!window.walletState.isConnected) {
            alert('请先连接钱包');
            return;
        }
        
        try {
            // 获取表单数据
            const formData = new FormData(form);
            const assetData = {};
            for (let [key, value] of formData.entries()) {
                assetData[key] = value;
            }
            
            // 发送创建请求
            const response = await fetch('/api/assets/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(assetData)
            });
            
            if (!response.ok) {
                throw new Error('创建资产失败');
            }
            
            const result = await response.json();
            alert('资产创建成功!');
            window.location.href = '/assets';
        } catch (error) {
            console.error('创建资产失败:', error);
            alert('创建资产失败: ' + error.message);
        }
    });
}

// 获取必要的 DOM 元素
    // 检查钱包连接状态
    if (!window.walletState || !window.walletState.isConnected || !window.walletState.currentAccount) {
        showError('请先连接钱包');
        // 禁用表单
        const form = document.getElementById('assetForm');
        Array.from(form.elements).forEach(element => {
            element.disabled = true;
        });
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
    const fields = ['name', 'location', 'description', 'totalValue', 'tokenPrice', 'annualRevenue', 'area', 'tokenAmount'];
    fields.forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            element.addEventListener('input', () => {
                validateAndUpdateField(element, field);
            });

            // 添加失去焦点时的验证
            element.addEventListener('blur', () => {
                validateAndUpdateField(element, field);
            });
        }
    });

    function validateAndUpdateField(element, field) {
        const value = element.value.trim();
        let errorMessage = '';

        if (!validateField(field, value)) {
            switch(field) {
                case 'name':
                    errorMessage = '名称必须在2-100个字符之间';
                    break;
                case 'location':
                    errorMessage = '位置必须在5-200个字符之间';
                    break;
                case 'description':
                    errorMessage = '描述必须在10-1000个字符之间';
                    break;
                case 'totalValue':
                    errorMessage = '总价值必须大于0且不超过1万亿';
                    break;
                case 'annualRevenue':
                    errorMessage = '年收益必须大于0且不超过总价值';
                    break;
                case 'area':
                    errorMessage = '面积必须大于0且不超过1,000,000';
                    break;
                case 'tokenAmount':
                    errorMessage = '代币数量必须大于0';
                    break;
            }
        }

        element.setCustomValidity(errorMessage);
        
        // 更新验证状态样式
        if (errorMessage) {
            element.classList.add('is-invalid');
            element.classList.remove('is-valid');
        } else {
            element.classList.remove('is-invalid');
            element.classList.add('is-valid');
        }

        // 如果是影响计算的字段，更新计算结果
        if (['area', 'totalValue', 'tokenAmount'].includes(field)) {
            updateTokenCalculation();
        }
    }

    // 资产类型切换处理
    typeSelect.addEventListener('change', function() {
        handleAssetTypeChange(this.value);
    });

    function handleAssetTypeChange(type) {
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

        if (type === '10') { // 不动产
            setupRealEstateFields();
        } else if (type === '20') { // 类不动产
            setupSimilarAssetFields();
        }
        
        // 触发表单验证
        form.classList.add('was-validated');
    }

    function setupRealEstateFields() {
        areaGroup.style.display = 'block';
        tokenAmountGroup.style.display = 'none';
        areaInput.required = true;
        tokenAmountInput.required = false;
        
        document.querySelector('.real-estate-docs').style.display = 'block';
        document.querySelector('.similar-assets-docs').style.display = 'none';
        
        document.querySelector('#tokenPrice').nextElementSibling.textContent = 
            '根据面积自动计算（每平方米10,000个代币）';
    }

    function setupSimilarAssetFields() {
        areaGroup.style.display = 'none';
        tokenAmountGroup.style.display = 'block';
        areaInput.required = false;
        tokenAmountInput.required = true;
        
        document.querySelector('.real-estate-docs').style.display = 'none';
        document.querySelector('.similar-assets-docs').style.display = 'block';
        
        document.querySelector('#tokenPrice').nextElementSibling.textContent = 
            '根据总价值和代币数量自动计算';
    }

    // 代币数量计算和显示
    function updateTokenCalculation() {
        const assetType = typeSelect.value;
        const totalValue = parseFloat(totalValueInput.value) || 0;
        let tokenAmount = 0;
        let calculatedTokenPrice = 0;
        
        try {
            if (assetType === '10') { // 不动产
                const area = parseFloat(areaInput.value) || 0;
                if (area > 0 && totalValue > 0) {
                    tokenAmount = area * 10000; // 每平米10000个代币
                    calculatedTokenPrice = totalValue / tokenAmount;
                    updateCalculationInfo(tokenAmount, calculatedTokenPrice, totalValue, area);
                }
            } else if (assetType === '20') { // 类不动产
                tokenAmount = parseFloat(tokenAmountInput.value) || 0;
                if (tokenAmount > 0 && totalValue > 0) {
                    calculatedTokenPrice = totalValue / tokenAmount;
                    updateCalculationInfo(tokenAmount, calculatedTokenPrice, totalValue);
                }
            }
            
            // 更新代币价格输入框
            if (calculatedTokenPrice > 0) {
                tokenPriceInput.value = calculatedTokenPrice.toFixed(6);
                tokenPriceInput.classList.add('is-valid');
                tokenPriceInput.classList.remove('is-invalid');
            } else {
                tokenPriceInput.value = '';
                calculationInfo.style.display = 'none';
            }
        } catch (error) {
            console.error('计算错误:', error);
            showError('计算代币价格时出错');
        }
    }

    function updateCalculationInfo(tokenAmount, tokenPrice, totalValue, area = null) {
        let html = `
            <div class="mb-2">
                <div>总代币数量: <span class="value">${tokenAmount.toLocaleString()}</span></div>
                <div>代币价格: <span class="value">${tokenPrice.toFixed(6)} U</span></div>
                <div>总价值: <span class="value">${totalValue.toLocaleString()} U</span></div>
        `;
        
        if (area !== null) {
            html += `<div>每平方米代币数: <span class="value">10,000</span></div>`;
        }
        
        html += `</div>`;
        calculationInfo.innerHTML = html;
        calculationInfo.style.display = 'block';
    }

    // 文件上传处理
    setupFileUpload(imageUpload, imagePreview, ['image/jpeg', 'image/png', 'image/gif'], true);
    setupFileUpload(documentUpload, documentPreview, ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'], false);

    // 保存草稿
    saveDraftBtn.addEventListener('click', async function() {
        try {
            if (!validateForm()) {
                return;
            }

            const formData = collectFormData();
            formData.append('is_draft', 'true');
            
            updateSubmitStatus(true, saveDraftBtn);
            const response = await submitData(formData);
            
            if (response.ok) {
                const result = await response.json();
                showSuccess('草稿保存成功');
                setTimeout(() => {
                    window.location.href = `/assets/${result.id}`;
                }, 1500);
            } else {
                const error = await response.json();
                throw new Error(error.message || '保存草稿失败');
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
            if (!validateForm()) {
                return;
            }

            updateSubmitStatus(true, submitBtn);
            const formData = collectFormData();
            const response = await submitData(formData);
            
            if (response.ok) {
                const result = await response.json();
                showSuccess('资产创建成功');
                setTimeout(() => {
                    window.location.href = `/assets/${result.id}`;
                }, 1500);
            } else {
                const error = await response.json();
                throw new Error(error.message || '创建资产失败');
            }
        } catch (error) {
            showError(error.message);
        } finally {
            updateSubmitStatus(false, submitBtn);
        }
    });

    // 辅助函数
    function validateForm() {
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return false;
        }

        // 检查必要的文件上传
        const assetType = typeSelect.value;
        const images = imagePreview.querySelectorAll('.preview-item').length;
        
        if (images === 0) {
            showError('请至少上传一张资产图片');
            return false;
        }

        if (assetType === '10' || assetType === '20') {
            const documents = documentPreview.querySelectorAll('.preview-item').length;
            if (documents === 0) {
                showError('请上传必要的资产文件');
                return false;
            }
        }

        return true;
    }

    function updateSubmitStatus(isSubmitting, button) {
        const originalText = button.innerHTML;
        if (isSubmitting) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>提交中...';
        } else {
            button.disabled = false;
            button.innerHTML = originalText;
        }
    }

    function showSuccess(message) {
        const toast = new bootstrap.Toast(document.createElement('div'));
        toast._element.classList.add('toast', 'bg-success', 'text-white');
        toast._element.innerHTML = `
            <div class="toast-body">
                <i class="fas fa-check-circle me-2"></i>${message}
            </div>
        `;
        document.body.appendChild(toast._element);
        toast.show();
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorModal.show();
    }

    function collectFormData() {
        const formData = new FormData();
        
        // 基本信息
        formData.append('name', document.getElementById('name').value.trim());
        formData.append('type', typeSelect.value);
        formData.append('location', document.getElementById('location').value.trim());
        formData.append('description', document.getElementById('description').value.trim());
        
        // 价值信息
        formData.append('total_value', totalValueInput.value);
        formData.append('token_price', tokenPriceInput.value);
        formData.append('annual_revenue', annualRevenueInput.value);
        
        if (typeSelect.value === '10') {
            formData.append('area', areaInput.value);
            formData.append('token_amount', (parseFloat(areaInput.value) * 10000).toString());
        } else {
            formData.append('token_amount', tokenAmountInput.value);
        }
        
        // 文件
        const images = imagePreview.querySelectorAll('.preview-item img');
        images.forEach((img, index) => {
            const file = dataURLtoFile(img.src, `image_${index}.jpg`);
            formData.append('images', file);
        });
        
        const documents = documentPreview.querySelectorAll('.preview-item');
        documents.forEach((doc, index) => {
            const file = doc.file;
            if (file) {
                formData.append('documents', file);
            }
        });
        
        return formData;
    }

    async function submitData(formData) {
        const response = await fetch('/api/assets/create', {
            method: 'POST',
            headers: {
                'X-Eth-Address': window.walletState.currentAccount
            },
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || '提交失败');
        }
        
        return response;
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
    let fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true;
    fileInput.accept = allowedTypes.join(',');
    fileInput.style.display = 'none';
    dropZone.parentNode.appendChild(fileInput);
    
    // 点击上传区域触发文件选择
    dropZone.addEventListener('click', () => fileInput.click());
    
    // 拖放处理
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
    
    fileInput.addEventListener('change', () => {
        handleFiles(fileInput.files);
        fileInput.value = ''; // 清空选择，允许重复选择相同文件
    });
    
    function handleFiles(files) {
        const validFiles = Array.from(files).filter(file => {
            if (!validateFile(file)) {
                return false;
            }
            
            const currentCount = previewZone.querySelectorAll('.preview-item').length;
            const limit = isImage ? IMAGE_COUNT_LIMIT : DOC_COUNT_LIMIT;
            
            if (currentCount >= limit) {
                showError(`最多只能上传${limit}个${isImage ? '图片' : '文档'}`);
                return false;
            }
            
            return true;
        });
        
        validFiles.forEach(processFile);
    }
    
    function validateFile(file) {
        if (!allowedTypes.includes(file.type)) {
            showError(`不支持的文件类型: ${file.type}`);
            return false;
        }
        
        if (file.size > FILE_SIZE_LIMIT) {
            showError(`文件大小超过限制: ${(file.size / 1024 / 1024).toFixed(2)}MB > 6MB`);
            return false;
        }
        
        return true;
    }
    
    function processFile(file) {
        const reader = new FileReader();
        const previewItem = document.createElement('div');
        previewItem.className = 'preview-item col-md-3 mb-3';
        previewItem.file = file;
        
        if (isImage) {
            reader.onload = (e) => {
                previewItem.innerHTML = `
                    <div class="position-relative">
                        <img src="${e.target.result}" class="img-fluid rounded" alt="Preview">
                        <button type="button" class="btn btn-danger btn-sm position-absolute top-0 end-0 m-1">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
            };
            reader.readAsDataURL(file);
        } else {
            previewItem.innerHTML = `
                <div class="document-item">
                    <i class="fas fa-file me-2"></i>${file.name}
                    <button type="button" class="btn btn-danger btn-sm float-end">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }
        
        previewZone.appendChild(previewItem);
        
        // 添加删除按钮事件
        const deleteBtn = previewItem.querySelector('.btn-danger');
        deleteBtn.addEventListener('click', () => {
            previewItem.remove();
        });
    }
}