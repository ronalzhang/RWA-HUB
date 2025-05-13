/**
 * 简化版购买处理脚本
 * 版本：1.0.1
 */

// 全局变量，用于存储timeout ID (使用window对象避免重复声明)
window.buyTimeoutId = null;

// 平台费率配置
const PLATFORM_FEE_RATE = 0.035; // 3.5%平台费率

/**
 * 计算平台费用
 * @param {number} amount - 金额
 * @returns {number} - 平台费用
 */
function calculatePlatformFee(amount) {
  return amount * PLATFORM_FEE_RATE;
}

/**
 * 更新价格显示
 * 替代已删除的asset_price_display.js功能
 */
function updatePriceDisplay() {
  try {
    // 获取必要元素
    const amountInput = document.getElementById('purchase-amount');
    const totalPriceDisplay = document.getElementById('totalPrice');
    const buyButton = document.getElementById('buy-button');
    
    if (!amountInput || !totalPriceDisplay || !buyButton) {
      console.log('价格更新：找不到必要元素');
      return;
    }
    
    // 获取价格和数量
    const pricePerToken = parseFloat(buyButton.getAttribute('data-token-price')) || 0;
    const amount = parseInt(amountInput.value) || 0;
    
    // 计算总价
    const totalPrice = (amount * pricePerToken).toFixed(2);
    totalPriceDisplay.value = totalPrice;
    
    console.log(`价格更新：${amount} × ${pricePerToken} = ${totalPrice}`);
  } catch (error) {
    console.error('更新价格显示失败:', error);
  }
}

// 页面加载时更新价格
document.addEventListener('DOMContentLoaded', function() {
  // 初始化价格显示
  updatePriceDisplay();
  
  // 监听输入变化
  const amountInput = document.getElementById('purchase-amount');
  if (amountInput) {
    amountInput.addEventListener('input', updatePriceDisplay);
  }
  
  // 初始化按钮状态
  updateBuyButtonState();
});

/**
 * 处理购买资产的函数
 * @param {string} assetId - 资产ID
 * @param {HTMLElement} amountInput - 数量输入框元素
 * @param {HTMLElement} buyButton - 购买按钮元素
 */
function handleBuy(assetId, amountInput, buyButton) {
  // 如果已有计时器运行，清除它
  if (window.buyTimeoutId) {
    clearTimeout(window.buyTimeoutId);
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
    resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
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
    resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
    return;
  }
  
  // 检查钱包连接状态
  const walletAddress = localStorage.getItem('walletAddress');
  if (!walletAddress) {
    alert('请先连接您的钱包');
    resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
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
      'X-Wallet-Address': walletAddress
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
          resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
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
    resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
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
        'X-Wallet-Address': walletAddress
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
      resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
      
      // 隐藏加载状态
      if (typeof hideLoadingState === 'function') {
        hideLoadingState();
      }
      
      // 延迟刷新页面以显示最新状态
      window.buyTimeoutId = setTimeout(() => {
        window.location.reload();
      }, 2000);
    })
    .catch(error => {
      console.error('确认购买失败', error);
      alert(`购买失败: ${error.message}`);
      resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
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
function resetButton(button, text = '<i class="fas fa-shopping-cart me-2"></i>Buy') {
  if (button) {
    button.disabled = false;
    button.innerHTML = text;
  }
}

/**
 * 更新购买按钮状态
 * 检查钱包连接状态并更新按钮
 */
function updateBuyButtonState() {
  console.log('更新购买按钮状态');
  
  // 获取购买按钮
  const buyButton = document.getElementById('buy-button');
  if (!buyButton) {
    console.warn('找不到购买按钮元素');
    return;
  }
  
  // 检查钱包状态
  let isConnected = false;
  
  // 方法1: 检查walletState对象
  if (window.walletState) {
    if (window.walletState.connected || window.walletState.isConnected) {
      isConnected = true;
    }
  }
  
  // 方法2: 检查localStorage中的钱包地址
  if (!isConnected) {
    const walletAddress = localStorage.getItem('walletAddress');
    isConnected = !!walletAddress;
  }
  
  // 更新按钮状态
  if (isConnected) {
    console.log('钱包已连接，启用购买按钮');
    buyButton.disabled = false;
    buyButton.innerHTML = '<i class="fas fa-shopping-cart me-2"></i>Buy';
    buyButton.removeAttribute('title');
  } else {
    console.log('钱包未连接，禁用购买按钮');
    buyButton.disabled = true;
    buyButton.innerHTML = '<i class="fas fa-wallet me-2"></i>请先连接钱包';
    buyButton.title = '请先连接钱包';
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
    newButton.innerHTML = '<i class="fas fa-shopping-cart me-2"></i>Buy';
    
    newButton.addEventListener('click', handleBuyButtonClick);
  });
  
  // 更新按钮状态
  updateBuyButtonState();
}

// 添加钱包状态变化监听器
document.addEventListener('walletStateChanged', function(event) {
  console.log('钱包状态变化，更新购买按钮状态:', event.detail);
  updateBuyButtonState();
});

// 监听钱包连接事件
document.addEventListener('walletConnected', function(event) {
  console.log('钱包已连接，更新购买按钮状态:', event.detail);
  updateBuyButtonState();
});

// 监听钱包断开连接事件
document.addEventListener('walletDisconnected', function() {
  console.log('钱包已断开连接，更新购买按钮状态');
  updateBuyButtonState();
});

// 初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    setupBuyButton();
    
    // 如果walletState可用，调用其更新方法
    if (window.walletState && typeof window.walletState.updateDetailPageButtonState === 'function') {
      try {
        window.walletState.updateDetailPageButtonState();
      } catch (error) {
        console.error('调用walletState.updateDetailPageButtonState失败:', error);
        // 使用备用方法
        updateBuyButtonState();
      }
    } else {
      // 使用自己的方法
      updateBuyButtonState();
    }
  });
} else {
  setupBuyButton();
  
  // 如果walletState可用，调用其更新方法
  if (window.walletState && typeof window.walletState.updateDetailPageButtonState === 'function') {
    try {
      window.walletState.updateDetailPageButtonState();
    } catch (error) {
      console.error('调用walletState.updateDetailPageButtonState失败:', error);
      // 使用备用方法
      updateBuyButtonState();
    }
  } else {
    // 使用自己的方法
    updateBuyButtonState();
  }
} 