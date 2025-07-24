/**
 * 简化版购买处理脚本
 * 版本：1.2.0 - 重构支付流程，增强稳定性
 */

// 全局变量，用于存储timeout ID (使用window对象避免重复声明)
window.buyTimeoutId = null;

// 使用模板中已定义的平台费率，避免重复声明
// const PLATFORM_FEE_RATE = 0.035; // 删除这行，改用window.PLATFORM_FEE_RATE

/**
 * 计算平台费用
 * @param {number} amount - 金额
 * @returns {number} - 平台费用
 */
function calculatePlatformFee(amount) {
  // 使用window对象上的PLATFORM_FEE_RATE，避免重复声明错误
  return amount * (window.PLATFORM_FEE_RATE || 0.035);
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
  console.log('购买函数被调用:', { assetId });
  
  // 如果已有计时器运行，清除它
  if (window.buyTimeoutId) {
    clearTimeout(window.buyTimeoutId);
    window.buyTimeoutId = null;
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
    showError('资产ID未提供，无法完成交易');
    return;
  }
  
  // 确保资产ID是数字格式（API期望整数）
  if (/^\d+$/.test(assetId)) {
    assetId = parseInt(assetId);
  } else {
    // 尝试解析为整数
    const parsed = parseInt(assetId);
    if (!isNaN(parsed)) {
      assetId = parsed;
    } else {
      console.error('无效的资产ID格式:', assetId);
      showError('无效的资产ID格式，无法完成交易');
      resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
      return;
    }
  }
  
  // 检查购买数量
  let amount = 0;
  if (amountInput) {
    amount = parseInt(amountInput.value);
  }
  
  if (!amount || amount <= 0) {
    showError('请输入有效的购买数量');
    resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
    return;
  }
  
  // 检查钱包连接状态
  const walletConnected = isWalletConnected();
  if (!walletConnected) {
    showError('Please connect your wallet first');
    resetButton(buyButton, '<i class="fas fa-wallet me-2"></i>Please Connect Wallet');
    buyButton.disabled = true;
    return;
  }
  
  // 获取钱包信息
  const walletAddress = getWalletAddress();
  const walletType = getWalletType();
  
  console.log('钱包信息:', { walletAddress, walletType });
  
  // 验证钱包地址格式
  if (!walletAddress || walletAddress.length < 32) {
    showError('钱包地址无效，请重新连接钱包');
    resetButton(buyButton, '<i class="fas fa-wallet me-2"></i>Please Connect Wallet');
    return;
  }
  
  // 准备购买数据
  const purchaseData = {
    asset_id: assetId,
    buyer_address: walletAddress,
    amount: amount,
    wallet_address: walletAddress,
    wallet_type: walletType
  };
  
  // 显示加载状态
  showLoadingState('正在准备购买...');
  
  // 发送智能合约购买准备请求
  console.log('发送智能合约购买准备请求:', purchaseData);
  fetch('/api/blockchain/prepare_purchase', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Wallet-Address': walletAddress,
      'X-Wallet-Type': walletType || 'unknown'
    },
    body: JSON.stringify(purchaseData)
  })
  .then(response => {
    console.log('API响应状态:', response.status, response.statusText);
    if (!response.ok) {
      return response.text().then(text => {
        console.error('API错误响应:', text);
        throw new Error(`服务器错误 ${response.status}: ${response.statusText}`);
      });
    }
    return response.json();
  })
  .then(data => {
    console.log('智能合约购买准备响应:', data);
    
    if (!data.success) {
      throw new Error(data.error || '准备智能合约交易失败');
    }
    
    // 获取智能合约交易数据
    const transactionData = data.transaction_data;
    const totalPrice = data.total_price;
    
    if (!transactionData) {
      throw new Error('服务器返回的智能合约交易数据不完整');
    }
    
    // 更新加载状态
    showLoadingState('请在钱包中确认智能合约交易...');
    
    // 检查Solana钱包API是否可用
    if (!window.solana || !window.solana.signAndSendTransaction) {
      throw new Error('Solana钱包API不可用，无法完成智能合约交易');
    }
    
    // 检查Solana Web3库是否可用
    console.log('调试：检查Solana Web3库状态...');
    console.log('window.solanaWeb3:', window.solanaWeb3);
    console.log('typeof solanaWeb3:', typeof solanaWeb3);
    console.log('window.solana:', window.solana);
    
    // 尝试多种可能的全局变量
    let solanaLib = null;
    if (window.solanaWeb3 && window.solanaWeb3.Transaction) {
      solanaLib = window.solanaWeb3;
      console.log('✅ 使用 window.solanaWeb3');
    } else if (typeof solanaWeb3 !== 'undefined' && solanaWeb3.Transaction) {
      solanaLib = solanaWeb3;
      window.solanaWeb3 = solanaWeb3; // 设置到window对象
      console.log('✅ 使用 solanaWeb3 并设置到 window');
    } else if (window.solana && window.solana.web3 && window.solana.web3.Transaction) {
      solanaLib = window.solana.web3;
      window.solanaWeb3 = window.solana.web3;
      console.log('✅ 使用 window.solana.web3');
    }
    
    if (!solanaLib || !solanaLib.Transaction) {
      console.log('⚠️ 未找到Solana库，创建简化版本...');
      // 创建简化的solanaWeb3对象
      solanaLib = {
        Transaction: {
          from: function(buffer) {
            // 简化的Transaction对象，只需要能被钱包处理
            return {
              serialize: function() {
                return buffer;
              },
              _buffer: buffer
            };
          }
        }
      };
      window.solanaWeb3 = solanaLib;
      console.log('✅ 创建了简化的Solana Web3库');
    }
    
    // 准备智能合约交易
    console.log(`执行智能合约资产购买: ${amount}个代币，总价: ${totalPrice} USDC`);
    
    // 解码交易数据
    const transactionBuffer = Uint8Array.from(atob(transactionData), c => c.charCodeAt(0));
    
    // 尝试使用signTransaction方法，这样更容易调试
    console.log('调用钱包签名，交易数据长度:', transactionBuffer.length);
    
    // 创建一个更完整的交易对象
    const transactionObj = {
      serialize: () => transactionBuffer,
      serializeMessage: () => transactionBuffer,
      signatures: [],
      feePayer: null
    };
    
    console.log('尝试使用signTransaction方法...');
    return window.solana.signTransaction(transactionObj)
      .then(signedTransaction => {
        console.log('交易签名成功，现在发送到网络...');
        // 这里我们可以使用自己的方法发送交易，或者让钱包发送
        return window.solana.sendTransaction(signedTransaction);
      })
      .then(paymentResult => {
        if (!paymentResult.signature) {
          throw new Error('智能合约交易失败：无签名返回');
        }
        
        console.log('智能合约交易成功，签名:', paymentResult.signature);
        
        // 确认智能合约购买
        return confirmSmartContractPurchase(
          assetId,
          walletAddress,
          amount,
          paymentResult.signature
        );
      });
  })
  .then(result => {
    console.log('智能合约购买完成:', result);
    
    // 显示成功消息
    showSuccessMessage('智能合约购买成功！', `您已成功通过智能合约购买 ${amount} 个代币，USDC支付和代币转移已同步完成。交易哈希: ${result.transaction_signature}`);
    
    // 重置按钮状态
    resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
    
    // 隐藏加载状态
    hideLoadingState();
    
    // 延迟刷新页面以显示最新状态
    window.buyTimeoutId = setTimeout(() => {
      window.location.reload();
    }, 3000);
  })
  .catch(error => {
    console.error('购买处理失败:', error);
    
    // 显示错误消息
    showError(error.message || '购买失败，请稍后重试');
    
    // 重置按钮状态
    resetButton(buyButton, '<i class="fas fa-shopping-cart me-2"></i>Buy');
    
    // 隐藏加载状态
    hideLoadingState();
  });
}

/**
 * 确认智能合约购买函数
 * @param {string} assetId - 资产ID
 * @param {string} walletAddress - 钱包地址
 * @param {number} amount - 购买数量
 * @param {string} signature - 交易签名
 */
function confirmSmartContractPurchase(assetId, walletAddress, amount, signature) {
  // 更新加载状态
  showLoadingState('正在确认智能合约购买...');
  
  // 确认购买数据
  const confirmData = { 
    asset_id: assetId,
    buyer_address: walletAddress,
    amount: amount,
    signed_transaction: signature
  };
  
  console.log('发送智能合约购买确认请求:', confirmData);
  
  // 发送确认购买请求
  return fetch('/api/blockchain/execute_purchase', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Wallet-Address': walletAddress
    },
    body: JSON.stringify(confirmData)
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`智能合约购买确认失败: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (!data.success) {
      throw new Error(data.error || '智能合约购买确认失败');
    }
    
    console.log('智能合约购买确认成功:', data);
    return {
      success: true,
      transaction_signature: data.transaction_signature,
      trade_id: data.trade_id,
      message: '智能合约购买已确认，代币转移和USDC支付同步完成'
    };
  });
}

/**
 * 确认购买函数（旧版本，保留向后兼容）
 * @param {string} purchaseId - 购买ID
 * @param {string} signature - 交易签名
 * @param {string} assetId - 资产ID
 * @param {string} walletAddress - 钱包地址
 * @param {number} amount - 购买数量
 */
function confirmPurchase(purchaseId, signature, assetId, walletAddress, amount) {
  // 更新加载状态
  showLoadingState('正在确认购买...');
  
  // 确认购买数据
  const confirmData = { 
    purchase_id: purchaseId,
    signature: signature,
    asset_id: assetId,
    wallet_address: walletAddress,
    amount: amount
  };
  
  console.log('发送确认购买请求:', confirmData);
  
  // 发送确认购买请求
  return fetch('/api/trades/confirm_purchase', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Wallet-Address': walletAddress
    },
    body: JSON.stringify(confirmData)
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`确认请求失败: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.error) {
      throw new Error(data.error);
    }
    
    console.log('确认购买成功:', data);
    return {
      success: true,
      transaction_hash: signature,
      purchase_id: purchaseId,
      message: '购买已确认，交易将在链上完成后到账'
    };
  });
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
  // 增强防抖机制 - 防止短时间内多次调用
  const now = Date.now();
  if (window._lastBuyButtonUpdate && (now - window._lastBuyButtonUpdate) < 1200) {
    // console.log('购买按钮状态更新太频繁，跳过此次更新');
    return;
  }
  window._lastBuyButtonUpdate = now;
  
  // 获取所有购买按钮
  const buyButtons = document.querySelectorAll('.buy-button, #buy-button');
  if (buyButtons.length === 0) {
    // console.log('找不到购买按钮元素，可能在其他页面');
    return;
  }
  
  // 检查钱包连接状态
  const walletConnected = isWalletConnected();
  
  // 只有状态真正需要改变时才记录日志和更新
  const shouldLog = !window._lastWalletConnectedState || window._lastWalletConnectedState !== walletConnected;
  if (shouldLog) {
  console.log('Wallet status check:', { connected: walletConnected });
    window._lastWalletConnectedState = walletConnected;
  }
  
  // 更新所有按钮状态
  buyButtons.forEach(buyButton => {
    const currentDisabled = buyButton.disabled;
    const shouldBeDisabled = !walletConnected;
    
    // 只有状态需要改变时才更新
    if (currentDisabled !== shouldBeDisabled) {
    if (walletConnected) {
        if (shouldLog) console.log('Wallet connected, enabling buy button');
      buyButton.disabled = false;
      buyButton.innerHTML = '<i class="fas fa-shopping-cart me-2"></i>Buy';
      buyButton.removeAttribute('title');
    } else {
        if (shouldLog) console.log('Wallet not connected, disabling buy button');
      buyButton.disabled = true;
      buyButton.innerHTML = '<i class="fas fa-wallet me-2"></i>Please Connect Wallet';
      buyButton.title = 'Please Connect Wallet';
      }
    }
  });
}

/**
 * 检查钱包是否已连接
 * @returns {boolean} - 钱包是否已连接
 */
function isWalletConnected() {
  // 方法1: 检查walletState对象
  if (window.walletState) {
    if (window.walletState.connected || window.walletState.isConnected) {
      return true;
    }
  }
  
  // 方法2: 检查localStorage中的钱包地址
  const walletAddress = localStorage.getItem('walletAddress');
  return !!walletAddress;
}

/**
 * 获取钱包地址
 * @returns {string|null} - 钱包地址
 */
function getWalletAddress() {
  // 方法1: 从walletState获取
  if (window.walletState && window.walletState.address) {
    return window.walletState.address;
  }
  
  // 方法2: 从localStorage获取
  return localStorage.getItem('walletAddress');
}

/**
 * 获取钱包类型
 * @returns {string} - 钱包类型
 */
function getWalletType() {
  // 方法1: 从walletState获取
        if (window.walletState && window.walletState.walletType) {
    return window.walletState.walletType;
  }
  
  // 方法2: 从localStorage获取
  return localStorage.getItem('walletType') || 'unknown';
}

/**
 * 显示错误消息
 * @param {string} message - 错误消息
 */
function showError(message) {
  if (typeof Swal !== 'undefined') {
    Swal.fire({
      title: '错误',
      text: message,
      icon: 'error',
      confirmButtonText: '确定'
    });
  } else {
    alert(message);
  }
}

/**
 * 显示成功消息
 * @param {string} title - 标题
 * @param {string} message - 成功消息
 */
function showSuccessMessage(title, message) {
  if (typeof Swal !== 'undefined') {
    Swal.fire({
      title: title,
      text: message,
      icon: 'success',
      confirmButtonText: '确定'
    });
  } else {
    alert(`${title}: ${message}`);
  }
}

/**
 * 显示加载状态
 * @param {string} message - 加载消息
 */
function showLoadingState(message = '处理中...') {
  if (typeof window.showLoadingOverlay === 'function') {
    window.showLoadingOverlay(message);
  } else {
    // 创建加载遮罩层
    let loadingOverlay = document.getElementById('buyLoadingOverlay');
    
    if (!loadingOverlay) {
      loadingOverlay = document.createElement('div');
      loadingOverlay.id = 'buyLoadingOverlay';
      loadingOverlay.className = 'loading-overlay';
      loadingOverlay.innerHTML = `
        <div class="loading-spinner">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="mt-2 loading-message">${message}</p>
        </div>
      `;
      
      // 添加样式
      const style = document.createElement('style');
      style.textContent = `
        .loading-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background-color: rgba(0, 0, 0, 0.5);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 9999;
        }
        .loading-spinner {
          background-color: white;
          padding: 20px;
          border-radius: 5px;
          text-align: center;
        }
      `;
      document.head.appendChild(style);
      
      document.body.appendChild(loadingOverlay);
    } else {
      // 更新消息
      const messageElement = loadingOverlay.querySelector('.loading-message');
      if (messageElement) {
        messageElement.textContent = message;
      }
      loadingOverlay.style.display = 'flex';
    }
  }
}

/**
 * 隐藏加载状态
 */
function hideLoadingState() {
  if (typeof window.hideLoadingOverlay === 'function') {
    window.hideLoadingOverlay();
  } else {
    const loadingOverlay = document.getElementById('buyLoadingOverlay');
    if (loadingOverlay) {
      loadingOverlay.style.display = 'none';
    }
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
      showError('无法确定资产ID');
      return false;
            }
            
            // 获取购买数量
    const amountInput = document.querySelector('#purchase-amount, #amount-input, input[name="amount"]');
            if (!amountInput) {
      showError('无法确定购买数量');
      return false;
    }
    
    // 调用购买函数
    handleBuy(assetId, amountInput, button);
  } catch (error) {
    console.error('点击处理失败:', error);
    showError(error.message || '处理失败');
  }
  
  return false;
}

// 初始化购买按钮
function setupBuyButton() {
  // 避免重复初始化
  if (window.buyButtonInitialized) {
    console.log('购买按钮已初始化，跳过重复初始化');
    return;
  }
  
  console.log('初始化购买按钮...');
  
  // 查找所有购买按钮
  const buyButtons = document.querySelectorAll('.buy-button, #buy-button');
  if (buyButtons.length === 0) {
    console.log('当前页面没有购买按钮');
    return;
  }
            
  console.log(`找到 ${buyButtons.length} 个购买按钮`);
  
  // 为每个按钮添加点击事件
  buyButtons.forEach(button => {
    // 检查是否已经绑定过事件
    if (button.dataset.buyEventBound) {
      console.log('按钮已绑定事件，跳过');
      return;
    }
    
    // 添加点击事件
    button.addEventListener('click', handleBuyButtonClick);
    button.dataset.buyEventBound = 'true'; // 标记已绑定
    console.log('已添加购买按钮点击事件');
  });
  
  // 初始更新按钮状态
  updateBuyButtonState();
  
  // 标记已初始化
  window.buyButtonInitialized = true;
}

// 用于跟踪最后一次状态更新的时间戳和正在进行的更新操作
// 使用window对象避免重复声明错误
window.lastStateUpdateTimestamp = window.lastStateUpdateTimestamp || 0;
window.pendingUpdateTimer = window.pendingUpdateTimer || null;

// 添加钱包状态变化监听器
document.addEventListener('walletStateChanged', function(event) {
  // 检查是否是新的状态变化
  const timestamp = event.detail?.timestamp || Date.now();
  if (timestamp <= window.lastStateUpdateTimestamp) {
    console.log('忽略重复的钱包状态变化事件');
    return;
  }
  
  // 使用延迟更新，避免短时间内多次触发
  if (window.pendingUpdateTimer) {
    clearTimeout(window.pendingUpdateTimer);
  }
  
  window.pendingUpdateTimer = setTimeout(() => {
    window.lastStateUpdateTimestamp = timestamp;
    console.log('钱包状态变化，更新购买按钮状态:', event.detail);
    updateBuyButtonState();
    window.pendingUpdateTimer = null;
  }, 2000); // 延迟2秒执行，减轻服务器负担
});

// 监听钱包连接事件，使用同样的延迟机制
document.addEventListener('walletConnected', function(event) {
  const timestamp = Date.now();
  if (timestamp <= window.lastStateUpdateTimestamp + 2000) {
    console.log('忽略短时间内的重复钱包连接事件');
    return;
  }
  
  if (window.pendingUpdateTimer) {
    clearTimeout(window.pendingUpdateTimer);
  }
  
  window.pendingUpdateTimer = setTimeout(() => {
    window.lastStateUpdateTimestamp = timestamp;
    console.log('钱包已连接，更新购买按钮状态:', event.detail);
    updateBuyButtonState();
    window.pendingUpdateTimer = null;
  }, 2000);
});

// 监听钱包断开连接事件
document.addEventListener('walletDisconnected', function() {
  const timestamp = Date.now();
  if (timestamp <= window.lastStateUpdateTimestamp + 2000) {
    console.log('短时间内已处理过状态变化，跳过');
    return;
  }
  
  if (window.pendingUpdateTimer) {
    clearTimeout(window.pendingUpdateTimer);
  }
  
  window.pendingUpdateTimer = setTimeout(() => {
    window.lastStateUpdateTimestamp = timestamp;
    console.log('钱包已断开连接，更新购买按钮状态');
    updateBuyButtonState();
    window.pendingUpdateTimer = null;
  }, 2000);
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