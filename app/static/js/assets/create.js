// 表单元素
const form = document.getElementById('assetForm');
const nameInput = document.getElementById('name');
const typeInput = document.getElementById('type');
const locationInput = document.getElementById('location');
const descriptionInput = document.getElementById('description');
const areaInput = document.getElementById('area');
const totalValueInput = document.getElementById('totalValue');
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
const maxFileSize = 5 * 1024 * 1024; // 5MB
const allowedImageTypes = ['image/jpeg', 'image/png', 'image/gif'];
const allowedDocumentTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

// 实时计算
function calculateTokens() {
    const totalValue = parseFloat(totalValueInput.value) || 0;
    const tokenPrice = parseFloat(tokenPriceInput.value) || 0;
    
    if (totalValue > 0 && tokenPrice > 0) {
        const tokenCount = Math.floor(totalValue / tokenPrice);
        document.getElementById('tokenCount').textContent = tokenCount.toLocaleString();
    } else {
        document.getElementById('tokenCount').textContent = '0';
    }
}

function calculateAnnualizedReturn() {
    const expectedAnnualRevenue = parseFloat(expectedAnnualRevenueInput.value) || 0;
    const totalValue = parseFloat(totalValueInput.value) || 0;
    
    if (totalValue > 0) {
        const annualizedReturn = (expectedAnnualRevenue / totalValue) * 100;
        document.getElementById('annualizedReturn').textContent = annualizedReturn.toFixed(2) + '%';
    } else {
        document.getElementById('annualizedReturn').textContent = '0%';
    }
}

// 文件处理函数
function handleFiles(files, type) {
    for (const file of files) {
        if (file.size > maxFileSize) {
            showError(`文件 ${file.name} 超过5MB限制`);
            continue;
        }
        
        const allowedTypes = type === 'image' ? allowedImageTypes : allowedDocumentTypes;
        if (!allowedTypes.includes(file.type)) {
            showError(`文件 ${file.name} 类型不支持`);
            continue;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            if (type === 'image') {
                uploadedImages.push({
                    name: file.name,
                    type: file.type,
                    data: e.target.result
                });
                updateImagePreview();
            } else {
                uploadedDocuments.push({
                    name: file.name,
                    type: file.type,
                    data: e.target.result
                });
                updateDocumentList();
            }
        };
        reader.readAsDataURL(file);
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
    
    // 实时计算监听器
    totalValueInput.addEventListener('input', () => {
        calculateTokens();
        calculateAnnualizedReturn();
    });
    
    tokenPriceInput.addEventListener('input', calculateTokens);
    expectedAnnualRevenueInput.addEventListener('input', calculateAnnualizedReturn);
    
    // 表单提交
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!form.checkValidity()) {
            e.stopPropagation();
            form.classList.add('was-validated');
            return;
        }
        
        const formData = new FormData();
        formData.append('name', nameInput.value);
        formData.append('type', typeInput.value);
        formData.append('location', locationInput.value);
        formData.append('description', descriptionInput.value);
        formData.append('area', areaInput.value);
        formData.append('totalValue', totalValueInput.value);
        formData.append('tokenPrice', tokenPriceInput.value);
        formData.append('expectedAnnualRevenue', expectedAnnualRevenueInput.value);
        
        // 添加图片和文档
        uploadedImages.forEach((image, index) => {
            formData.append(`images[${index}]`, dataURLtoBlob(image.data), image.name);
        });
        
        uploadedDocuments.forEach((doc, index) => {
            formData.append(`documents[${index}]`, dataURLtoBlob(doc.data), doc.name);
        });
        
        try {
            const response = await fetch('/api/assets/create', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('提交失败');
            }
            
            const result = await response.json();
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