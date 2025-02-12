// 表单验证和提交处理
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('assetForm');
    const typeSelect = document.getElementById('type');
    const areaGroup = document.querySelector('.asset-area-group');
    const imageUpload = document.getElementById('imageUpload');
    const documentUpload = document.getElementById('documentUpload');
    const imagePreview = document.getElementById('imagePreview');
    const documentPreview = document.getElementById('documentPreview');
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    const errorMessage = document.getElementById('errorMessage');

    // 资产类型切换处理
    typeSelect.addEventListener('change', function() {
        if (this.value === '10') { // 不动产
            areaGroup.style.display = 'block';
            areaGroup.querySelector('input').required = true;
        } else {
            areaGroup.style.display = 'none';
            areaGroup.querySelector('input').required = false;
        }
    });

    // 图片上传处理
    setupFileUpload(imageUpload, imagePreview, ['image/jpeg', 'image/png', 'image/gif'], true);
    
    // 文档上传处理
    setupFileUpload(documentUpload, documentPreview, ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'], false);

    // 表单提交处理
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!form.checkValidity()) {
            e.stopPropagation();
            form.classList.add('was-validated');
            return;
        }

        try {
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

            // 发送请求
            const response = await fetch('/api/assets', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Eth-Address': localStorage.getItem('userAddress')
                }
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || '创建资产失败');
            }

            const result = await response.json();
            window.location.href = `/assets/${result.id}`;
            
        } catch (error) {
            errorMessage.textContent = error.message;
            errorModal.show();
        }
    });
});

// 文件上传处理函数
function setupFileUpload(dropZone, previewZone, allowedTypes, isImage) {
    dropZone.addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = allowedTypes.join(',');
        input.onchange = (e) => handleFiles(e.target.files);
        input.click();
    });

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

    function handleFiles(files) {
        Array.from(files).forEach(file => {
            if (allowedTypes.includes(file.type)) {
                if (isImage) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.className = 'col-4 img-thumbnail';
                        img.style.objectFit = 'cover';
                        img.style.height = '200px';
                        previewZone.appendChild(img);
                    };
                    reader.readAsDataURL(file);
                } else {
                    const div = document.createElement('div');
                    div.className = 'document-item mb-2';
                    div.innerHTML = `
                        <i class="fas fa-file me-2"></i>
                        <span>${file.name}</span>
                    `;
                    div.file = file;
                    previewZone.appendChild(div);
                }
            }
        });
    }
}

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