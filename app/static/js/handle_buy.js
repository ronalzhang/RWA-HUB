/**
 * 简化版购买处理脚本
 * 版本：1.3.0 - 彻底简化，修复timeoutId未定义问题
 */

(function() {
  // 避免重复加载
  if (window.buyHandlerInitialized) {
    return;
  }
  window.buyHandlerInitialized = true;
  
  console.log('加载简化版购买处理脚本 v1.3.0');
  
  // 简化的全局购买处理函数
  window.handleBuy = function(assetId, amountInput, buyButton) {
    // 标准化资产ID
    function normalizeAssetId(id) {
      if (!id) return '';
      if (/^\d+$/.test(id)) return `RH-${id}`;
      if (id.startsWith('RH-')) return id;
      return id;
    }
    
    try {
      // 获取购买数量
      const amount = parseInt(amountInput?.value) || 0;
      
      if (isNaN(amount) || amount <= 0) {
        alert('请输入有效的购买数量');
        return;
      }
      
      // 获取钱包地址
      const walletAddress = localStorage.getItem('walletAddress') || '';
      if (!walletAddress) {
        alert('请先连接钱包');
        return;
      }
      
      // 标准化资产ID
      const normalizedId = normalizeAssetId(assetId);
      
      // 构建请求参数
      const params = {
        asset_id: normalizedId.replace('RH-', ''),
        amount: amount,
        wallet_address: walletAddress
      };
      
      console.log('准备购买请求:', params);
      
      // 显示按钮加载状态
      if (buyButton) {
        buyButton.disabled = true;
        buyButton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 处理中...`;
      }
      
      // 使用明确声明的timeoutId变量
      let timeoutId = setTimeout(() => {
        if (buyButton) {
          buyButton.disabled = false;
          buyButton.innerHTML = 'Buy';
        }
        alert('请求超时，请重试');
      }, 15000);
      
      // 发送API请求
      fetch('/api/trades/prepare_purchase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(params)
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP错误 ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (!data.success) {
          throw new Error(data.message || '准备购买请求失败');
        }
        
        // 确认购买
        return fetch('/api/trades/confirm_purchase', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({
            trade_id: data.trade_id,
            wallet_address: walletAddress
          })
        });
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP错误 ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // 清除超时
        clearTimeout(timeoutId);
        
        if (!data.success) {
          throw new Error(data.message || '确认购买失败');
        }
        
        // 显示成功消息
        alert('购买成功！');
        console.log('购买成功:', data);
        
        // 恢复按钮状态
        if (buyButton) {
          buyButton.disabled = false;
          buyButton.innerHTML = 'Buy';
        }
      })
      .catch(error => {
        // 清除超时
        clearTimeout(timeoutId);
        
        console.error('购买处理失败:', error);
        alert(error.message || '购买失败，请重试');
        
        // 恢复按钮状态
        if (buyButton) {
          buyButton.disabled = false;
          buyButton.innerHTML = 'Buy';
        }
      });
    } catch (error) {
      console.error('购买函数执行错误:', error);
      alert(error.message || '购买处理失败');
      
      // 恢复按钮状态
      if (buyButton) {
        buyButton.disabled = false;
        buyButton.innerHTML = 'Buy';
      }
    }
  };
  
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
})(); 