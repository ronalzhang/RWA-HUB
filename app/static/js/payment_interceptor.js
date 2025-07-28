/**
 * 支付流程拦截器脚本
 * 版本: 1.0.0 - 修复支付流程和智能合约调用
 */

(function() {
  // 避免重复加载
  if (window.paymentInterceptorInitialized) {
    console.debug('[支付流程] 脚本已初始化，跳过重复执行');
    return;
  }
  window.paymentInterceptorInitialized = true;
  
  console.log('[支付流程] 初始化支付拦截器 v1.0.0');
  
  // 配置
  const CONFIG = {
    debug: false,
    apiTimeoutMs: 15000,      // API请求超时时间
    paymentTimeoutMs: 60000,  // 支付超时时间
    retryCount: 2,            // 失败重试次数
    minPurchaseAmount: 0.01,  // 最小购买金额
    enableLogs: true,         // 启用支付日志
    defaultChain: 'ethereum', // 默认链
    supportedChains: ['ethereum', 'solana', 'polygon'],
    contractAddresses: {
      ethereum: '0x92E52a1A235d9A103D970901066CE910AAceFD37',
      solana: '8JFUpyf8rKJdMnLkpLCUz8zXUcyJUuvJmjXPUQsw61Kc',
      polygon: '0xA5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff'
    }
  };
  
  // 安全执行函数
  function safeExecute(fn, fallback, timeout = 15000) {
    let hasCompleted = false;
    let localTimeoutId = null;
    
    // 设置安全超时
    localTimeoutId = setTimeout(() => {
      if (!hasCompleted) {
        console.debug('[支付流程] 操作超时终止');
        hasCompleted = true;
        
        if (typeof fallback === 'function') {
          try {
            fallback();
          } catch (e) {
            console.debug('[支付流程] 降级处理失败:', e);
          }
        }
      }
    }, timeout);
    
    // 执行主函数
    try {
      const result = fn();
      
      // 处理Promise
      if (result && typeof result.then === 'function') {
        return Promise.race([
          result.then(value => {
            if (!hasCompleted) {
              clearTimeout(localTimeoutId);
              hasCompleted = true;
            }
            return value;
          }).catch(err => {
            if (!hasCompleted) {
              clearTimeout(localTimeoutId);
              hasCompleted = true;
            }
            throw err;
          }),
          new Promise((_, reject) => {
            // 此Promise会在timeoutId触发时被拒绝
          })
        ]);
      }
      
      // 同步结果
      clearTimeout(localTimeoutId);
      hasCompleted = true;
      return result;
    } catch (error) {
      if (!hasCompleted) {
        clearTimeout(localTimeoutId);
        hasCompleted = true;
        console.debug('[支付流程] 操作执行失败:', error);
        
        if (typeof fallback === 'function') {
          try {
            return fallback();
          } catch (e) {
            console.debug('[支付流程] 降级处理失败:', e);
          }
        }
      }
      throw error;
    }
  }
  
  // 日志函数
  function log(message, data) {
    if (CONFIG.debug) {
      if (data !== undefined) {
        console.log(`[支付流程] ${message}`, data);
      } else {
        console.log(`[支付流程] ${message}`);
      }
    }
  }
  
  // 标准化资产ID
  function normalizeAssetId(assetId) {
    if (!assetId) return null;
    
    // 如果是纯数字，添加RH-前缀
    if (/^\d+$/.test(assetId)) {
      return `RH-${assetId}`;
    }
    
    // 如果已经是RH-格式，保持不变
    if (assetId.startsWith('RH-')) {
      return assetId;
    }
    
    // 尝试提取数字部分
    const match = assetId.match(/(\d+)/);
    if (match && match[1]) {
      return `RH-${match[1]}`;
    }
    
    return assetId;
  }
  
  // 获取当前钱包信息
  function getWalletInfo() {
    const result = {
      connected: false,
      address: '',
      chain: 'solana',
      balance: 0
    };
    
    // 尝试从localStorage获取
    const storedAddress = localStorage.getItem('walletAddress') || localStorage.getItem('eth_address');
    const storedType = localStorage.getItem('walletType') || 'phantom';
    
    if (storedAddress) {
      result.connected = true;
      result.address = storedAddress;
      result.chain = storedType === 'metamask' ? 'ethereum' : 'solana';
    }
    
    // 尝试从window.walletState获取
    if (window.walletState) {
      result.connected = result.connected || 
        window.walletState.isConnected || 
        window.walletState.connected || 
        false;
      result.address = result.address || window.walletState.address || null;
      result.chain = result.chain || window.walletState.chain || window.walletState.chainId || 'solana';
      result.balance = result.balance || window.walletState.balance || 0;
    }
    
    return result;
  }
  
  // 检查钱包连接状态
  function isWalletConnected() {
    // 首选检查 - localStorage
    const storedAddress = localStorage.getItem('walletAddress') || localStorage.getItem('eth_address');
    if (storedAddress) {
      return true;
    }
    
    // 检查全局walletState
    if (window.walletState) {
      if (typeof window.walletState.isWalletConnected === 'function') {
        try {
          return window.walletState.isWalletConnected();
        } catch (error) {
          console.error('调用钱包连接检查函数失败:', error);
        }
      }
      
      // 检查walletState属性
      if (window.walletState.isConnected || window.walletState.connected) {
        return true;
      }
    }
    
    // 检查window.walletPublicKey
    if (window.walletPublicKey) {
      try {
        const pubkeyStr = typeof window.walletPublicKey === 'string' 
          ? window.walletPublicKey 
          : (typeof window.walletPublicKey.toString === 'function' 
            ? window.walletPublicKey.toString() 
            : '');
        
        if (pubkeyStr && pubkeyStr.length > 30) {
          return true;
        }
      } catch (error) {
        console.error('解析钱包公钥失败:', error);
      }
    }
    
    return false;
  }
  
  // 获取合约地址
  function getContractAddress(chain) {
    const activeChain = chain || getWalletInfo().chain || CONFIG.defaultChain;
    return CONFIG.contractAddresses[activeChain] || CONFIG.contractAddresses[CONFIG.defaultChain];
  }
  
  // 向服务器发送交易记录
  async function logTransaction(transactionData) {
    if (!CONFIG.enableLogs) return;
    
    try {
      const controller = new AbortController();
      const localTimeoutId = setTimeout(() => controller.abort(), 5000);
      
      await fetch('/api/transaction/log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(transactionData),
        signal: controller.signal
      });
      
      clearTimeout(localTimeoutId);
    } catch (error) {
      console.debug('[支付流程] 记录交易失败:', error);
    }
  }
  
  // 准备购买数据
  async function preparePurchase(assetId, amount) {
    return safeExecute(async () => {
      // 检查钱包连接
      if (!isWalletConnected()) {
        throw new Error('请先连接您的钱包');
      }
      
      // 标准化资产ID
      const normalizedId = normalizeAssetId(assetId);
      if (!normalizedId) {
        throw new Error('无效的资产ID');
      }
      
      // 移除RH-前缀，仅使用数字部分作为API参数
      const idForApi = normalizedId.replace('RH-', '');
      
      // 检查购买数量
      const purchaseAmount = parseFloat(amount);
      if (isNaN(purchaseAmount) || purchaseAmount < CONFIG.minPurchaseAmount) {
        throw new Error(`购买数量必须大于${CONFIG.minPurchaseAmount}`);
      }
      
      // 获取钱包信息
      const walletInfo = getWalletInfo();
      
      // 构建请求参数
      const params = {
        asset_id: idForApi,
        amount: purchaseAmount,
        wallet_address: walletInfo.address,
        chain: walletInfo.chain || CONFIG.defaultChain
      };
      
      log('准备购买请求:', params);
      
      // 尝试不同的API端点
      const endpoints = [
        '/api/trades/prepare_purchase',
        '/api/v1/trades/prepare_purchase'
      ];
      
      for (let i = 0; i < endpoints.length; i++) {
        try {
          // 创建AbortController用于超时控制
          const controller = new AbortController();
          const localTimeoutId = setTimeout(() => controller.abort(), CONFIG.apiTimeoutMs);
          
          const response = await fetch(endpoints[i], {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(params),
            signal: controller.signal
          });
          
          clearTimeout(localTimeoutId);
          
          if (!response.ok) {
            if (i === endpoints.length - 1) {
              throw new Error(`服务器错误: ${response.status}`);
            }
            continue; // 尝试下一个端点
          }
          
          const data = await response.json();
          
          // 验证响应
          if (!data || !data.success) {
            throw new Error(data.message || '准备购买请求失败');
          }
          
          // 添加一些额外信息，方便后续处理
          data.asset_id = normalizedId;
          data.amount = purchaseAmount;
          data.wallet_address = walletInfo.address;
          data.chain = walletInfo.chain || CONFIG.defaultChain;
          data.contract_address = getContractAddress(data.chain);
          
          return data;
        } catch (error) {
          if (i === endpoints.length - 1) {
            throw error;
          }
          // 否则尝试下一个端点
        }
      }
      
      throw new Error('所有API端点都失败');
    }, () => {
      console.debug('[支付流程] 准备购买请求超时');
      throw new Error('准备购买请求超时，请稍后重试');
    }, CONFIG.apiTimeoutMs + 2000);
  }
  
  // 调用智能合约执行支付
  async function executeContractPayment(purchaseData) {
    return safeExecute(async () => {
      log('执行合约支付:', purchaseData);
      
      // 检查购买数据
      if (!purchaseData || !purchaseData.success || !purchaseData.purchase_id) {
        throw new Error('无效的购买数据');
      }
      
      // 检查钱包连接
      if (!isWalletConnected()) {
        throw new Error('钱包已断开连接，请重新连接');
      }
      
      // 获取钱包和链信息
      const walletInfo = getWalletInfo();
      const chain = purchaseData.chain || walletInfo.chain || CONFIG.defaultChain;
      
      // 确定合约地址
      const contractAddress = purchaseData.contract_address || getContractAddress(chain);
      
      // 根据链选择不同的支付方法
      let paymentResult = null;
      
      if (chain === 'ethereum' || chain === 'polygon') {
        // 以太坊/Polygon支付
        if (typeof window.executeEthereumPayment === 'function') {
          paymentResult = await window.executeEthereumPayment(
            contractAddress,
            purchaseData.purchase_id,
            purchaseData.total_price || purchaseData.amount,
            walletInfo.address
          );
        } else {
          // 手动调用以太坊合约
          paymentResult = await executeEthereumPaymentManual(
            contractAddress,
            purchaseData.purchase_id,
            purchaseData.total_price || purchaseData.amount,
            walletInfo.address
          );
        }
      } else if (chain === 'solana') {
        // Solana支付
        if (typeof window.executeSolanaPayment === 'function') {
          paymentResult = await window.executeSolanaPayment(
            contractAddress,
            purchaseData.purchase_id,
            purchaseData.total_price || purchaseData.amount,
            walletInfo.address
          );
        } else {
          // 回退到API支付
          paymentResult = await executeApiPayment(purchaseData);
        }
      } else {
        // 不支持的链，使用API支付
        paymentResult = await executeApiPayment(purchaseData);
      }
      
      if (!paymentResult || !paymentResult.success) {
        throw new Error(paymentResult?.message || '支付执行失败');
      }
      
      // 记录交易
      await logTransaction({
        purchase_id: purchaseData.purchase_id,
        transaction_hash: paymentResult.transaction_hash,
        wallet_address: walletInfo.address,
        asset_id: purchaseData.asset_id,
        amount: purchaseData.amount,
        total_price: purchaseData.total_price,
        chain: chain,
        status: 'completed',
        timestamp: new Date().toISOString()
      });
      
      return {
        success: true,
        purchase_id: purchaseData.purchase_id,
        transaction_hash: paymentResult.transaction_hash,
        ...paymentResult
      };
    }, () => {
      console.debug('[支付流程] 执行合约支付超时');
      throw new Error('支付处理超时，请检查您的钱包是否已确认交易');
    }, CONFIG.paymentTimeoutMs);
  }
  
  // 手动执行以太坊合约支付
  async function executeEthereumPaymentManual(contractAddress, purchaseId, amount, walletAddress) {
    try {
      // 检查是否有以太坊提供者
      if (!window.ethereum) {
        throw new Error('未检测到以太坊钱包');
      }
      
      // 合约ABI (简化版，仅包含支付方法)
      const contractABI = [
        {
          "inputs": [
            {
              "internalType": "uint256",
              "name": "purchaseId",
              "type": "uint256"
            }
          ],
          "name": "payForAsset",
          "outputs": [],
          "stateMutability": "payable",
          "type": "function"
        }
      ];
      
      // 创建合约实例
      let contract;
      if (window.web3) {
        contract = new window.web3.eth.Contract(contractABI, contractAddress);
      } else if (window.ethers) {
        const provider = new window.ethers.providers.Web3Provider(window.ethereum);
        const signer = provider.getSigner();
        contract = new window.ethers.Contract(contractAddress, contractABI, signer);
      } else {
        throw new Error('未找到web3或ethers库');
      }
      
      // 准备交易参数
      const purchaseIdBN = window.web3 ? window.web3.utils.toBN(purchaseId) : purchaseId;
      const amountWei = window.web3 ? 
        window.web3.utils.toWei(amount.toString(), 'ether') : 
        window.ethers.utils.parseEther(amount.toString());
      
      // 执行交易
      let txHash;
      
      if (window.web3) {
        // 使用web3.js
        const result = await contract.methods.payForAsset(purchaseIdBN).send({
          from: walletAddress,
          value: amountWei,
          gas: 200000
        });
        txHash = result.transactionHash;
      } else {
        // 使用ethers.js
        const tx = await contract.payForAsset(purchaseIdBN, { value: amountWei });
        const receipt = await tx.wait();
        txHash = receipt.transactionHash;
      }
      
      if (!txHash) {
        throw new Error('交易失败，未返回交易哈希');
      }
      
      return {
        success: true,
        transaction_hash: txHash,
        message: '支付成功'
      };
    } catch (error) {
      console.error('[支付流程] 以太坊支付失败:', error);
      return {
        success: false,
        message: error.message || '支付失败'
      };
    }
  }
  
  // 通过API执行支付
  async function executeApiPayment(purchaseData) {
    try {
      // 构建请求参数
      const params = {
        purchase_id: purchaseData.purchase_id,
        wallet_address: purchaseData.wallet_address,
        amount: purchaseData.amount,
        asset_id: purchaseData.asset_id.replace('RH-', '')
      };
      
      // 发送确认请求
      const controller = new AbortController();
      const localTimeoutId = setTimeout(() => controller.abort(), CONFIG.apiTimeoutMs);
      
      const response = await fetch('/api/trades/confirm_purchase', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(params),
        signal: controller.signal
      });
      
      clearTimeout(localTimeoutId);
      
      if (!response.ok) {
        throw new Error(`服务器错误: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data || !data.success) {
        throw new Error(data.message || '确认购买失败');
      }
      
      return {
        success: true,
        transaction_hash: data.transaction_id || data.transaction_hash || `api-${Date.now()}`,
        message: '支付成功'
      };
    } catch (error) {
      console.error('[支付流程] API支付失败:', error);
      return {
        success: false,
        message: error.message || '支付失败'
      };
    }
  }
  
  // 显示支付结果通知
  function showPaymentNotification(isSuccess, message) {
    try {
      const container = document.querySelector('.alert-container, .message-container');
      
      if (!container) {
        // 使用alert作为备用
        if (isSuccess) {
          alert('支付成功：' + message);
        } else {
          alert('支付失败：' + message);
        }
        return;
      }
      
      // 创建通知元素
      const notification = document.createElement('div');
      notification.className = `alert alert-${isSuccess ? 'success' : 'danger'} alert-dismissible fade show`;
      notification.setAttribute('role', 'alert');
      
      notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      `;
      
      // 添加到容器
      container.appendChild(notification);
      
      // 自动关闭
      setTimeout(() => {
        if (notification.parentNode) {
          notification.classList.remove('show');
          setTimeout(() => {
            if (notification.parentNode) {
              notification.parentNode.removeChild(notification);
            }
          }, 500);
        }
      }, 8000);
    } catch (error) {
      console.debug('[支付流程] 显示通知失败:', error);
      // 使用alert作为备用
      if (isSuccess) {
        alert('支付成功：' + message);
      } else {
        alert('支付失败：' + message);
      }
    }
  }
  
  // 刷新资产列表
  function refreshAssetsList() {
    try {
      // 尝试调用全局刷新函数
      if (typeof window.refreshUserAssets === 'function') {
        window.refreshUserAssets();
      } else if (typeof window.updateUserAssets === 'function') {
        window.updateUserAssets();
      } else {
        // 尝试刷新页面
        const assetsList = document.querySelector('.assets-list, .user-assets');
        if (assetsList) {
          // 发送自定义事件
          assetsList.dispatchEvent(new CustomEvent('refresh'));
        }
      }
    } catch (error) {
      console.debug('[支付流程] 刷新资产列表失败:', error);
    }
  }
  
  // 主要的购买处理函数
  async function handlePurchase(assetId, amount, options = {}) {
    // 创建加载指示器
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay';
    loadingOverlay.innerHTML = `
      <div class="loading-spinner">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-2">处理中，请稍候...</p>
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
    
    try {
      // 检查钱包连接
      if (!isWalletConnected()) {
        throw new Error('请先连接您的钱包');
      }
      
      // 显示加载指示器
      document.body.appendChild(loadingOverlay);
      
      // 1. 准备购买数据
      const purchaseData = await preparePurchase(assetId, amount);
      
      // 2. 执行合约支付
      const paymentResult = await executeContractPayment(purchaseData);
      
      // 3. 处理成功结果
      if (paymentResult.success) {
        // 显示成功通知
        showPaymentNotification(true, `购买成功！交易哈希: ${paymentResult.transaction_hash.slice(0, 8)}...`);
        
        // 刷新资产列表
        setTimeout(refreshAssetsList, 2000);
        
        // 调用成功回调
        if (typeof options.onSuccess === 'function') {
          options.onSuccess(paymentResult);
        }
        
        return paymentResult;
      } else {
        throw new Error(paymentResult.message || '支付失败');
      }
    } catch (error) {
      console.error('[支付流程] 购买处理失败:', error);
      
      // 显示错误通知
      showPaymentNotification(false, error.message || '购买处理失败');
      
      // 调用错误回调
      if (typeof options.onError === 'function') {
        options.onError(error);
      }
      
      return {
        success: false,
        message: error.message || '购买处理失败'
      };
    } finally {
      // 移除加载指示器
      if (loadingOverlay.parentNode) {
        loadingOverlay.parentNode.removeChild(loadingOverlay);
      }
    }
  }
  
  // 拦截原始的购买处理函数
  function interceptOriginalHandlers() {
    try {
      // 保存原始处理函数
      if (typeof window.handleBuyButtonClick === 'function') {
        window._originalHandleBuyButtonClick = window.handleBuyButtonClick;
      }
      
      if (typeof window.processPurchase === 'function') {
        window._originalProcessPurchase = window.processPurchase;
      }
      
      // 替换为我们的处理函数
      window.handleBuyButtonClick = async function(event) {
        try {
          // 阻止默认行为
          if (event) {
            event.preventDefault();
            event.stopPropagation();
          }
          
          // 获取按钮和相关数据
          const button = event.currentTarget;
          if (!button) return false;
          
          // 更新按钮状态
          if (typeof window.updateBuyButtonState === 'function') {
            window.updateBuyButtonState(button, '处理中...', true);
          } else {
            button.disabled = true;
            button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 处理中...`;
          }
          
          // 获取资产ID
          let assetId = button.getAttribute('data-asset-id');
          if (!assetId) {
            const assetElement = document.querySelector('[data-asset-id]');
            if (assetElement) {
              assetId = assetElement.getAttribute('data-asset-id');
            }
          }
          
          if (!assetId) {
            // 尝试从URL获取
            const urlMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
            if (urlMatch && urlMatch[1]) {
              assetId = urlMatch[1];
            }
          }
          
          // 获取购买数量
          let amount = 1; // 默认为1个
          
          // 首先尝试从按钮属性获取
          if (button.hasAttribute('data-amount')) {
            amount = parseFloat(button.getAttribute('data-amount')) || 1;
          } else {
            // 尝试从输入框获取
            const amountInput = document.querySelector('#amount-input, #purchase-amount, input[name="amount"]');
            if (amountInput) {
              amount = parseFloat(amountInput.value) || 1;
            }
          }
          
          // 执行购买
          const result = await handlePurchase(assetId, amount, {
            onSuccess: () => {
              // 更新按钮状态
              if (typeof window.updateBuyButtonState === 'function') {
                window.updateBuyButtonState(button, button.dataset.originalText || '购买', false);
              } else {
                button.disabled = false;
                button.innerHTML = button.dataset.originalText || '购买';
              }
            },
            onError: () => {
              // 更新按钮状态
              if (typeof window.updateBuyButtonState === 'function') {
                window.updateBuyButtonState(button, button.dataset.originalText || '购买', false);
              } else {
                button.disabled = false;
                button.innerHTML = button.dataset.originalText || '购买';
              }
            }
          });
          
          return false;
        } catch (error) {
          console.error('[支付流程] 处理购买按钮点击失败:', error);
          
          // 尝试恢复按钮状态
          try {
            if (typeof window.updateBuyButtonState === 'function') {
              window.updateBuyButtonState(event.currentTarget, '购买', false);
            } else if (event && event.currentTarget) {
              event.currentTarget.disabled = false;
              event.currentTarget.innerHTML = event.currentTarget.dataset.originalText || '购买';
            }
          } catch (e) {}
          
          return false;
        }
      };
      
      // 替换processPurchase函数
      window.processPurchase = async function(assetId, amount) {
        return handlePurchase(assetId, amount);
      };
      
      log('已拦截原始购买处理函数');
    } catch (error) {
      console.error('[支付流程] 拦截原始处理函数失败:', error);
    }
  }
  
  // 绑定购买按钮事件 - 已禁用，使用wallet.js中的处理逻辑
  function bindBuyButtons() {
    // 禁用此函数，避免与wallet.js冲突
    console.log('bindBuyButtons disabled - using wallet.js logic instead');
    return;
      
      buyButtons.forEach(button => {
        // 跳过无效按钮和已绑定的按钮
        if (!button || button.getAttribute('data-payment-handler-bound') === 'true') {
          return;
        }
        
        // 移除现有的事件监听器
        const newButton = button.cloneNode(true);
        if (button.parentNode) {
          button.parentNode.replaceChild(newButton, button);
        }
        
        // 保存原始文本
        if (!newButton.dataset.originalText) {
          newButton.dataset.originalText = newButton.textContent.trim();
        }
        
        // 绑定新的事件处理器
        newButton.addEventListener('click', window.handleBuyButtonClick);
        newButton.setAttribute('data-payment-handler-bound', 'true');
      });
      
      log(`已绑定 ${buyButtons.length} 个购买按钮`);
    } catch (error) {
      console.error('[支付流程] 绑定购买按钮失败:', error);
    }
  }
  
  // 初始化
  function init() {
    return safeExecute(() => {
      log('正在初始化支付拦截器...');
      
      // 替换原始处理函数
      interceptOriginalHandlers();
      
      // 绑定购买按钮
      setTimeout(bindBuyButtons, 1000);
      
      // 设置MutationObserver监控新添加的按钮
      const observer = new MutationObserver((mutations) => {
        let needsRebind = false;
        
        mutations.forEach(mutation => {
          if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            for (let i = 0; i < mutation.addedNodes.length; i++) {
              const node = mutation.addedNodes[i];
              if (node.nodeType === 1) { // 元素节点
                if (node.matches && (
                  node.matches('.buy-btn, .buy-button, [data-action="buy"], #buyButton, .btn-buy, #buy-button') ||
                  node.querySelector('.buy-btn, .buy-button, [data-action="buy"], #buyButton, .btn-buy, #buy-button')
                )) {
                  needsRebind = true;
                  break;
                }
              }
            }
          }
        });
        
        if (needsRebind) {
          setTimeout(bindBuyButtons, 200);
        }
      });
      
      // 配置观察器
      observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: false
      });
      
      // 监听URL变化
      let lastUrl = location.href;
      const urlObserver = new MutationObserver(() => {
        const currentUrl = location.href;
        if (currentUrl !== lastUrl) {
          lastUrl = currentUrl;
          setTimeout(bindBuyButtons, 1000);
        }
      });
      
      urlObserver.observe(document, { subtree: true, childList: true });
      
      log('支付拦截器初始化完成');
      
      // 发布初始化完成事件
      document.dispatchEvent(new CustomEvent('paymentInterceptorReady'));
      
      // 导出全局API
      window.paymentAPI = {
        handlePurchase,
        isWalletConnected,
        getWalletInfo,
        refreshAssetsList
      };
    }, () => {
      console.error('[支付流程] 初始化超时');
    }, 10000);
  }
  
  // 启动初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 500);
  }
})();

// 导出全局函数
window.handlePurchase = handlePurchase;
window.confirmPurchase = confirmPurchase;
window.updateBuyButtonPrice = updateBuyButtonPrice;
window.updateBuyButtonState = updateBuyButtonState;

// 添加全局handleBuy函数，供detail.html使用
window.handleBuy = function(assetId, amountInput, buyButton, tokenPrice, walletInfo = {}) {
  log('handleBuy全局函数被调用:', { assetId, tokenPrice, walletInfo });
  
  try {
    // 获取购买数量
    const amount = parseInt(amountInput?.value) || 0;
    
    if (isNaN(amount) || amount <= 0) {
      showError('请输入有效的购买数量');
      return;
    }
    
    // 如果tokenPrice提供了但为0，尝试从按钮获取
    let price = tokenPrice;
    if (!price && buyButton) {
      price = parseFloat(buyButton.getAttribute('data-token-price') || '0');
    }
    
    // 使用handlePurchase函数处理购买
    return handlePurchase(assetId, amount, {
      price: price,
      walletAddress: walletInfo.walletAddress,
      walletType: walletInfo.walletType,
      isConnected: walletInfo.walletConnected,
      button: buyButton
    });
  } catch (error) {
    console.error('handleBuy全局函数执行失败:', error);
    showError(error.message || '购买处理失败');
    return { success: false, error: error.message };
  }
};

// 兼容旧版handle_buy.js的代码
if (typeof window.handleBuyButtonClick !== 'function') {
  window.handleBuyButtonClick = async function(event) {
    event.preventDefault();
    
    try {
      // 获取按钮和资产ID
      const button = event.currentTarget;
      const assetId = button.getAttribute('data-asset-id');
      
      if (!assetId) {
        console.error('购买按钮缺少data-asset-id属性');
        showError('购买信息不完整，请刷新页面重试');
        return;
      }
      
      // 获取购买数量
      const amountInput = document.getElementById('purchase-amount');
      if (!amountInput) {
        console.error('找不到购买数量输入框');
        showError('购买组件缺失，请刷新页面重试');
        return;
      }
      
      const amount = parseInt(amountInput.value);
      if (isNaN(amount) || amount <= 0) {
        showError('请输入有效的购买数量');
        return;
      }
      
      // 获取价格
      const price = parseFloat(button.getAttribute('data-token-price') || '0');
      
      // 调用handlePurchase函数
      await handlePurchase(assetId, amount, {
        price: price,
        button: button
      });
    } catch (error) {
      console.error('处理购买点击失败:', error);
      showError(error.message || '购买处理失败');
    }
  };
}

// 显示错误消息
function showError(message, element = null) {
  console.error('[支付拦截器] 错误:', message);
  
  // 尝试使用已有的错误显示区域
  if (!element) {
    // 优先检查通用错误显示区域
    element = document.getElementById('buy-error') || 
              document.getElementById('error-message') || 
              document.querySelector('.error-message');
  }
  
  if (element) {
    element.textContent = message;
    element.style.display = 'block';
    
    // 自动隐藏
    setTimeout(() => {
      element.style.display = 'none';
    }, 5000);
    return;
  }
  
  // 如果没有找到错误显示区域，使用alert
  alert(message);
} 