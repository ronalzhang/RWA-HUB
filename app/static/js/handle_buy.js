/**
 * 简化版购买处理脚本
 * 版本：1.0.0
 */

// 全局变量，用于存储timeout ID
let buyTimeoutId = null;

/**
 * 处理购买资产的函数
 * @param {string} assetId - 资产ID
 * @param {HTMLElement} amountInput - 数量输入框元素
 * @param {HTMLElement} buyButton - 购买按钮元素
 */
function handleBuy(assetId, amountInput, buyButton) {
  // 如果已有计时器运行，清除它
  if (buyTimeoutId) {
    clearTimeout(buyTimeoutId);
  }
  
  // 防止重复点击
  if (buyButton && buyButton.disabled) {
    console.log('购买处理中，请稍候...');
    return;
  }
  
  // 设置按钮加载状态
  if (buyButton) {
    buyButton.disabled = true;
    buyButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 处理中...';
  }
  
  // 检查资产ID
  if (!assetId) {
    console.error('资产ID未提供');
    resetButton(buyButton, 'Buy');
    return;
  }
  
  // 规范化资产ID格式
  if (/^\d+$/.test(assetId)) {
    assetId = `RH-${assetId}`;
  }
  
  // 检查购买数量
  let amount = 0;
  if (amountInput) {
    amount = parseInt(amountInput.value);
  }
  
  if (!amount || amount <= 0) {
    alert('请输入有效的购买数量');
    resetButton(buyButton, 'Buy');
    return;
  }
  
  // 检查钱包连接状态
  const walletAddress = localStorage.getItem('walletAddress');
  if (!walletAddress) {
    alert('请先连接您的钱包');
    resetButton(buyButton, 'Buy');
    return;
  }
  
  // 准备购买数据
  const purchaseData = {
    asset_id: assetId,
    amount: amount,
    wallet_address: walletAddress
  };
  
  // 显示加载状态
  if (typeof showLoadingState === 'function') {
    showLoadingState('正在准备购买...');
  }
  
  // 发送准备购买请求
  fetch('/api/trades/prepare_purchase', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(purchaseData)
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.error) {
      throw new Error(data.error);
    }
    
    // 处理响应
    console.log('准备购买成功', data);
    
    // 如果需要进行钱包签名
    if (data.requires_signature && typeof signAndConfirmTransaction === 'function') {
      // 更新加载状态
      if (typeof showLoadingState === 'function') {
        showLoadingState('请在钱包中确认交易...');
      }
      
      // 调用钱包签名函数
      signAndConfirmTransaction(data.transaction_data)
        .then(signatureData => {
          // 确认购买
          confirmPurchase(data.purchase_id, signatureData.signature);
        })
        .catch(error => {
          console.error('钱包签名失败', error);
          alert('交易签名失败，请重试');
          resetButton(buyButton, 'Buy');
          if (typeof hideLoadingState === 'function') {
            hideLoadingState();
          }
        });
    } else {
      // 无需签名，直接确认购买
      confirmPurchase(data.purchase_id);
    }
  })
  .catch(error => {
    console.error('准备购买失败', error);
    alert(`购买失败: ${error.message}`);
    resetButton(buyButton, 'Buy');
    if (typeof hideLoadingState === 'function') {
      hideLoadingState();
    }
  });
  
  /**
   * 确认购买函数
   * @param {string} purchaseId - 购买ID
   * @param {string} signature - 可选的签名数据
   */
  function confirmPurchase(purchaseId, signature = null) {
    // 确认购买数据
    const confirmData = { purchase_id: purchaseId };
    if (signature) {
      confirmData.signature = signature;
    }
    
    // 更新加载状态
    if (typeof showLoadingState === 'function') {
      showLoadingState('正在确认购买...');
    }
    
    // 发送确认购买请求
    fetch('/api/trades/confirm_purchase', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(confirmData)
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.error) {
        throw new Error(data.error);
      }
      
      // 购买成功
      console.log('购买成功', data);
      alert('购买成功！');
      
      // 重置按钮状态
      resetButton(buyButton, 'Buy');
      
      // 隐藏加载状态
      if (typeof hideLoadingState === 'function') {
        hideLoadingState();
      }
      
      // 延迟刷新页面以显示最新状态
      buyTimeoutId = setTimeout(() => {
        window.location.reload();
      }, 2000);
    })
    .catch(error => {
      console.error('确认购买失败', error);
      alert(`购买失败: ${error.message}`);
      resetButton(buyButton, 'Buy');
      if (typeof hideLoadingState === 'function') {
        hideLoadingState();
      }
    });
  }
}

/**
 * 重置按钮状态
 * @param {HTMLElement} button - 按钮元素
 * @param {string} text - 按钮文本
 */
function resetButton(button, text = 'Buy') {
  if (button) {
    button.disabled = false;
    button.innerHTML = text;
  }
}

// 处理按钮点击的简化函数
function handleBuyButtonClick(event) {
  // 阻止默认行为
  event.preventDefault();
  
  try {
    // 获取按钮和相关数据
    const button = event.currentTarget;
    
    // 获取资产ID
    let assetId = button.getAttribute('data-asset-id');
    if (!assetId) {
      const assetElement = document.querySelector('[data-asset-id]');
      if (assetElement) {
        assetId = assetElement.getAttribute('data-asset-id');
      }
    }
    
    if (!assetId) {
      alert('无法确定资产ID');
      return false;
    }
    
    // 获取购买数量
    const amountInput = document.querySelector('#purchase-amount, #amount-input, input[name="amount"]');
    if (!amountInput) {
      alert('无法确定购买数量');
      return false;
    }
    
    // 调用全局购买函数
    window.handleBuy(assetId, amountInput, button);
  } catch (error) {
    console.error('点击处理失败:', error);
    alert(error.message || '处理失败');
  }
  
  return false;
}

// 设置购买按钮事件
function setupBuyButton() {
  // 查找所有购买按钮
  const buyButtons = document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"], #buyButton, .btn-buy, #buy-button');
  
  buyButtons.forEach(button => {
    // 移除旧的事件监听器并附加新的
    const newButton = button.cloneNode(true);
    if (button.parentNode) {
      button.parentNode.replaceChild(newButton, button);
    }
    
    // 确保按钮文字为"Buy"
    if (newButton.textContent !== 'Buy') {
      newButton.textContent = 'Buy';
    }
    
    newButton.addEventListener('click', handleBuyButtonClick);
  });
}

// 初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupBuyButton);
} else {
  setupBuyButton();
} 