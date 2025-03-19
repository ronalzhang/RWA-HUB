// 示例：初始化分红弹窗
function initDividendModal() {
    // 获取必要元素
    const dividendAmountInput = document.getElementById('dividendAmount');
    const estimatedFeeElement = document.getElementById('estimatedFee');
    const platformFeeElement = document.getElementById('platformFee');
    const perTokenAmountElement = document.getElementById('perTokenAmount');
    const startDividendBtn = document.getElementById('startDividendBtn');
    
    if (!dividendAmountInput || !estimatedFeeElement || !platformFeeElement || !perTokenAmountElement || !startDividendBtn) {
        console.error('無法找到分紅彈窗的必要元素');
        return;
    }
    
    // 添加金额输入事件
    dividendAmountInput.addEventListener('input', calculateDividend);
    
    function calculateDividend() {
        let amount = parseFloat(dividendAmountInput.value) || 0;
        const totalSupply = parseFloat(document.getElementById('totalSupply').textContent.split('/')[0].trim()) || 1;
        
        // 验证最小金额
        if (amount < 10000) {
            startDividendBtn.disabled = true;
            startDividendBtn.textContent = window._('Minimum 10,000 USDC required');
            startDividendBtn.classList.add('btn-secondary');
            startDividendBtn.classList.remove('btn-primary');
        } else {
            startDividendBtn.disabled = false;
            startDividendBtn.textContent = window._('Start Dividend');
            startDividendBtn.classList.add('btn-primary');
            startDividendBtn.classList.remove('btn-secondary');
        }
        
        // 计算各项费用
        const estimatedFee = 0.055 * amount; // 示例：估算Gas费用
        const platformFee = 0.015 * amount; // 1.5%平台手续费
        const netDividend = amount - platformFee;
        const perTokenAmount = totalSupply > 0 ? netDividend / totalSupply : 0;
        
        // 更新显示
        estimatedFeeElement.textContent = estimatedFee.toFixed(3) + ' USDC';
        platformFeeElement.textContent = platformFee.toFixed(3) + ' USDC';
        perTokenAmountElement.textContent = perTokenAmount.toFixed(6) + ' USDC';
    }
    
    // 初始化计算
    calculateDividend();
    
    // 添加分红按钮点击事件
    startDividendBtn.addEventListener('click', async function() {
        if (this.disabled) return;
        
        const amount = parseFloat(dividendAmountInput.value);
        if (amount < 10000) {
            showErrorMessage(window._('Minimum dividend amount is 10,000 USDC'));
            return;
        }
        
        try {
            this.disabled = true;
            this.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${window._('Processing...')}`;
            
            // TODO: 这里添加实际的分红处理逻辑
            await new Promise(resolve => setTimeout(resolve, 2000)); // 模拟处理时间
            
            // 成功处理后
            showSuccessMessage(window._('Dividend initiated successfully'));
            const modal = bootstrap.Modal.getInstance(document.getElementById('dividendModal'));
            if (modal) modal.hide();
            
            // 重新加载分红历史
            loadDividendHistory();
        } catch (error) {
            console.error('分紅啟動失敗:', error);
            showErrorMessage(window._('Failed to initiate dividend') + ': ' + error.message);
        } finally {
            this.disabled = false;
            this.textContent = window._('Start Dividend');
        }
    });
}

// 显示成功消息
function showSuccessMessage(message) {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="${window._('Close')}"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // 5秒后自动关闭
    setTimeout(() => {
        if (alert && alert.parentNode === alertContainer) {
            alertContainer.removeChild(alert);
        }
    }, 5000);
}

// 显示错误消息
function showErrorMessage(message) {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="${window._('Close')}"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // 5秒后自动关闭
    setTimeout(() => {
        if (alert && alert.parentNode === alertContainer) {
            alertContainer.removeChild(alert);
        }
    }, 5000);
} 