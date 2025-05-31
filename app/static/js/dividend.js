/**
 * 资产分红管理脚本
 * 版本：1.0.0
 */

(function() {
  // 配置
  const CONFIG = {
    apiBaseUrl: '/api',
    minDividendAmount: 10000, // 最小分红金额：10,000 USDC
    platformFeeRate: 0.015,   // 平台费率：1.5%
    apiTimeoutMs: 10000,      // API超时时间：10秒
    debug: false              // 调试模式
  };
  
  // ============================
  // 辅助函数
  // ============================
  
  // 日志函数
  function log(message, data) {
    if (CONFIG.debug) {
      if (data) {
        console.log('[分红] ' + message, data);
      } else {
        console.log('[分红] ' + message);
      }
    }
  }
  
  // 获取钱包地址
  function getWalletAddress() {
    // 优先使用 walletState
    if (window.walletState && window.walletState.address) {
      return window.walletState.address;
    }
    
    // 备用方案，从localStorage获取
    return localStorage.getItem('walletAddress');
  }
  
  // 检查钱包连接状态
  function isWalletConnected() {
    // 方法1: 使用 walletState
    if (window.walletState) {
      if (window.walletState.connected || window.walletState.isConnected) {
        return true;
      }
    }
    
    // 方法2: 检查localStorage中的钱包地址
    const walletAddress = localStorage.getItem('walletAddress');
    return !!walletAddress;
  }
  
  // 显示消息
  function showMessage(message, type = 'info', title = null) {
    if (typeof Swal !== 'undefined') {
      const swalConfig = {
        title: title || (type === 'error' ? '错误' : (type === 'success' ? '成功' : '提示')),
        text: message,
        icon: type,
        confirmButtonText: '确定',
        confirmButtonColor: '#007bff',
        customClass: {
          popup: 'swal2-popup-custom',
          title: 'swal2-title-custom',
          content: 'swal2-content-custom'
        }
      };
      
      // 错误消息显示更长时间
      if (type === 'error') {
        swalConfig.timer = 8000;
        swalConfig.timerProgressBar = true;
        swalConfig.confirmButtonColor = '#dc3545';
      } else if (type === 'success') {
        swalConfig.timer = 3000;
        swalConfig.timerProgressBar = true;
        swalConfig.confirmButtonColor = '#28a745';
      }
      
      Swal.fire(swalConfig);
    } else {
      // 降级为原生alert，但格式化消息
      const prefix = type === 'error' ? '❌ 错误: ' : (type === 'success' ? '✅ 成功: ' : 'ℹ️ 提示: ');
      alert(prefix + message);
    }
  }
  
  // 显示加载状态
  function showLoading(message = '处理中...') {
    if (typeof Swal !== 'undefined') {
      Swal.fire({
        title: '请稍候',
        text: message,
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        customClass: {
          popup: 'swal2-popup-loading',
          title: 'swal2-title-loading'
        },
        didOpen: () => {
          Swal.showLoading();
        }
      });
    } else {
      // 创建自定义加载界面
      let loadingEl = document.getElementById('dividendLoadingOverlay');
      if (!loadingEl) {
        loadingEl = document.createElement('div');
        loadingEl.id = 'dividendLoadingOverlay';
        loadingEl.style.cssText = `
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
        `;
        
        const spinnerContainer = document.createElement('div');
        spinnerContainer.style.cssText = `
          background-color: white;
          padding: 30px;
          border-radius: 10px;
          text-align: center;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        `;
        
        const spinner = document.createElement('div');
        spinner.className = 'spinner-border text-primary';
        spinner.setAttribute('role', 'status');
        spinner.style.cssText = 'width: 3rem; height: 3rem;';
        
        const messageEl = document.createElement('p');
        messageEl.className = 'dividend-loading-message mt-3 mb-0';
        messageEl.style.cssText = 'margin: 0; font-size: 16px; color: #333;';
        messageEl.textContent = message;
        
        spinnerContainer.appendChild(spinner);
        spinnerContainer.appendChild(messageEl);
        loadingEl.appendChild(spinnerContainer);
        document.body.appendChild(loadingEl);
      } else {
        const messageEl = loadingEl.querySelector('.dividend-loading-message');
        if (messageEl) {
          messageEl.textContent = message;
        }
        loadingEl.style.display = 'flex';
      }
    }
  }
  
  // 隐藏加载状态
  function hideLoading() {
    if (typeof Swal !== 'undefined') {
      Swal.close();
    } else {
      const loadingEl = document.getElementById('dividendLoadingOverlay');
      if (loadingEl) {
        loadingEl.style.display = 'none';
      }
    }
  }
  
  // 格式化货币
  function formatCurrency(amount, currency = 'USDC', decimals = 2) {
    if (isNaN(amount)) return '0 ' + currency;
    return parseFloat(amount).toFixed(decimals) + ' ' + currency;
  }
  
  // ============================
  // 主要功能
  // ============================
  
  // 初始化分红表单
  function initDividendForm() {
    const form = document.getElementById('dividendForm');
    if (!form) return;
    
    log('初始化分红表单');
    
    // 获取表单元素
    const amountInput = document.getElementById('amount');
    const intervalInput = document.getElementById('interval');
    const platformFeeEl = document.getElementById('platformFee');
    const actualAmountEl = document.getElementById('actualAmount');
    const submitBtn = document.getElementById('submitBtn');
    
    // 检查必要元素
    if (!amountInput || !platformFeeEl || !actualAmountEl || !submitBtn) {
      log('分红表单缺少必要元素');
      return;
    }
    
    // 添加金额输入事件
    amountInput.addEventListener('input', function() {
      updateDividendCalculation(amountInput, platformFeeEl, actualAmountEl, submitBtn);
    });
    
    // 添加表单提交事件
    form.addEventListener('submit', function(event) {
      event.preventDefault();
      
      // 获取表单数据
      const amount = parseFloat(amountInput.value);
      const interval = parseInt(intervalInput.value || 24); // 默认24小时
      
      // 验证金额
      if (isNaN(amount) || amount < CONFIG.minDividendAmount) {
        showMessage(`最小分红金额为 ${CONFIG.minDividendAmount} USDC`, 'error');
        return;
      }
      
      // 验证钱包连接
      if (!isWalletConnected()) {
        showMessage('请先连接钱包', 'error');
        return;
      }
      
      // 调用分红函数
      startDividend(amount, interval);
    });
    
    // 初始化计算
    updateDividendCalculation(amountInput, platformFeeEl, actualAmountEl, submitBtn);
  }
  
  // 更新分红计算
  function updateDividendCalculation(amountInput, platformFeeEl, actualAmountEl, submitBtn) {
    const amount = parseFloat(amountInput.value) || 0;
    
    // 计算平台费用
    const platformFee = amount * CONFIG.platformFeeRate;
    const actualAmount = amount - platformFee;
    
    // 更新显示
    platformFeeEl.textContent = formatCurrency(platformFee);
    actualAmountEl.textContent = formatCurrency(actualAmount);
    
    // 更新按钮状态
    if (amount < CONFIG.minDividendAmount) {
      submitBtn.disabled = true;
      submitBtn.textContent = `最小金额 ${CONFIG.minDividendAmount} USDC`;
    } else {
      submitBtn.disabled = false;
      submitBtn.textContent = '发起分红';
    }
  }
  
  // 启动分红
  async function startDividend(amount, interval) {
    // 获取资产ID
    const assetId = getAssetId();
    if (!assetId) {
      showMessage('无法确定资产ID', 'error');
      return;
    }
    
    // 获取钱包地址
    const walletAddress = getWalletAddress();
    if (!walletAddress) {
      showMessage('请先连接钱包', 'error');
      return;
    }
    
    // 显示加载状态
    showLoading('正在准备分红交易...');
    
    try {
      log('开始分红流程', { assetId, amount, interval, walletAddress });
      
      // 步骤1: 调用API准备分红
      const prepareResponse = await fetch(`${CONFIG.apiBaseUrl}/dividends/prepare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Wallet-Address': walletAddress
        },
        body: JSON.stringify({
          asset_id: assetId,
          amount: amount,
          interval: interval * 3600 // 转换小时为秒
        })
      });
      
      if (!prepareResponse.ok) {
        const errorData = await prepareResponse.json();
        throw new Error(errorData.error || `准备分红失败: ${prepareResponse.status}`);
      }
      
      const prepareData = await prepareResponse.json();
      log('准备分红响应', prepareData);
      
      // 获取接收地址和金额
      const platformAddress = prepareData.platform_address;
      const dividendId = prepareData.dividend_id;
      
      if (!platformAddress || !dividendId) {
        throw new Error('服务器返回的分红信息不完整');
      }
      
      // 步骤2: 使用钱包API转账USDC
      showLoading('请在钱包中确认交易...');
      
      // 检查钱包API是否可用
      if (!window.walletState || typeof window.walletState.transferToken !== 'function') {
        throw new Error('钱包API不可用，无法完成分红支付');
      }
      
      const transferResult = await window.walletState.transferToken('USDC', platformAddress, amount);
      
      if (!transferResult.success) {
        throw new Error(transferResult.error || '钱包转账失败');
      }
      
      log('分红支付成功，交易哈希:', transferResult.txHash);
      
      // 步骤3: 确认分红
      showLoading('正在确认分红交易...');
      
      const confirmResponse = await fetch(`${CONFIG.apiBaseUrl}/dividends/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Wallet-Address': walletAddress
        },
        body: JSON.stringify({
          dividend_id: dividendId,
          transaction_hash: transferResult.txHash
        })
      });
      
      if (!confirmResponse.ok) {
        const errorData = await confirmResponse.json();
        throw new Error(errorData.error || `确认分红失败: ${confirmResponse.status}`);
      }
      
      const confirmData = await confirmResponse.json();
      log('确认分红响应', confirmData);
      
      // 隐藏加载状态
      hideLoading();
      
      // 显示成功消息
      showMessage('分红发起成功！分红将在链上确认后分配给所有持有者。', 'success');
      
      // 刷新分红历史
      if (typeof refreshDividendHistory === 'function') {
        setTimeout(refreshDividendHistory, 1000);
      } else {
        // 延迟刷新页面
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      }
      
    } catch (error) {
      log('分红流程失败', error);
      hideLoading();
      showMessage(error.message || '分红流程失败', 'error');
    }
  }
  
  // 领取分红
  window.claimDividend = function(recordId) {
    if (!recordId) {
      console.error('领取分红: 记录ID未提供');
      showMessage('记录ID未提供', 'error');
      return Promise.reject(new Error('记录ID未提供'));
    }
    
    const walletAddress = getWalletAddress();
    if (!walletAddress) {
      console.warn('领取分红: 钱包未连接');
      showMessage('请先连接钱包领取分红', 'warning');
      return Promise.reject(new Error('钱包未连接'));
    }
    
    // 显示加载状态
    showLoading('正在准备领取分红...');
    
    const claimData = {
      record_id: recordId,
      wallet_address: walletAddress
    };
    
    return fetch(`${CONFIG.apiBaseUrl}/dividends/claim`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Wallet-Address': walletAddress
      },
      body: JSON.stringify(claimData)
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(data => {
          throw new Error(data.error || `HTTP error ${response.status}`);
        });
      }
      return response.json();
    })
    .then(data => {
      if (data.error) {
        throw new Error(data.error);
      }
      
      log('领取分红响应', data);
      
      // 获取接收地址和金额
      const recipient = data.recipient_address || walletAddress;
      const amount = data.amount || 0;
      
      if (isNaN(amount) || amount <= 0) {
        throw new Error('分红金额无效');
      }
      
      // 使用钱包API转账USDC
      showLoading('请在钱包中确认交易...');
      
      // 执行领取操作
      return confirmClaimDividend(data.claim_id);
    })
    .then(result => {
      hideLoading();
      showMessage('分红领取成功！', 'success');
      
      // 刷新页面
      setTimeout(() => {
        window.location.reload();
      }, 2000);
      
      return result;
    })
    .catch(error => {
      console.error('领取分红失败:', error);
      hideLoading();
      showMessage(error.message || '领取分红失败', 'error');
      throw error;
    });
  };
  
  // 确认领取分红
  function confirmClaimDividend(claimId) {
    const walletAddress = getWalletAddress();
    if (!walletAddress) {
      return Promise.reject(new Error('钱包未连接'));
    }
    
    const confirmData = { 
      claim_id: claimId,
      wallet_address: walletAddress
    };
    
    return fetch(`${CONFIG.apiBaseUrl}/dividends/confirm_claim`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Wallet-Address': walletAddress
      },
      body: JSON.stringify(confirmData)
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(data => {
          throw new Error(data.error || `HTTP error ${response.status}`);
        });
      }
      return response.json();
    })
    .then(data => {
      if (data.error) {
        throw new Error(data.error);
      }
      return data;
    });
  }
  
  // 获取分红历史
  function getMyDividendHistory() {
    const walletAddress = getWalletAddress();
    if (!walletAddress) {
      return Promise.reject(new Error('钱包未连接'));
    }
    
    return fetch(`${CONFIG.apiBaseUrl}/dividends/my-history?address=${walletAddress}`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        log('获取分红历史成功', data);
        return data;
      })
      .catch(error => {
        console.error('获取分红历史失败:', error);
        throw error;
      });
  }
  
  // 渲染分红表格
  function renderDividendTable(records) {
    const tableContainer = document.getElementById('dividendHistoryTable');
    if (!tableContainer) {
      console.warn('找不到分红历史表格容器');
      return;
    }
    
    if (!records || records.length === 0) {
      tableContainer.innerHTML = `
        <div class="text-center py-4">
          <p class="text-gray-500">暂无分红记录</p>
        </div>
      `;
      return;
    }
    
    // 构建表格HTML
    let tableHtml = `
      <table class="w-full">
        <thead>
          <tr>
            <th class="py-2 text-left">资产</th>
            <th class="py-2 text-right">金额</th>
            <th class="py-2 text-center">状态</th>
            <th class="py-2 text-right">时间</th>
            <th class="py-2 text-center">操作</th>
          </tr>
        </thead>
        <tbody>
    `;
    
    // 添加记录行
    records.forEach(record => {
      const date = new Date(record.created_at);
      const formattedDate = `${date.getFullYear()}-${(date.getMonth()+1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
      
      tableHtml += `
        <tr class="border-t">
          <td class="py-3">${record.asset_symbol || record.asset_id}</td>
          <td class="py-3 text-right">${formatCurrency(record.amount)}</td>
          <td class="py-3 text-center">
            <span class="px-2 py-1 rounded-full text-xs ${getStatusClass(record.status)}">
              ${getStatusText(record.status)}
            </span>
          </td>
          <td class="py-3 text-right">${formattedDate}</td>
          <td class="py-3 text-center">
            ${getActionButton(record)}
          </td>
        </tr>
      `;
    });
    
    tableHtml += `
        </tbody>
      </table>
    `;
    
    // 更新表格容器
    tableContainer.innerHTML = tableHtml;
    
    // 添加事件监听器
    const claimButtons = tableContainer.querySelectorAll('.claim-btn');
    claimButtons.forEach(button => {
      button.addEventListener('click', function() {
        const recordId = this.getAttribute('data-record-id');
        if (recordId) {
          window.claimDividend(recordId);
        }
      });
    });
  }
  
  // 获取状态样式类
  function getStatusClass(status) {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'claimed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'expired':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  }
  
  // 获取状态文本
  function getStatusText(status) {
    switch (status) {
      case 'pending':
        return '待领取';
      case 'claimed':
        return '已领取';
      case 'failed':
        return '失败';
      case 'expired':
        return '已过期';
      default:
        return status;
    }
  }
  
  // 获取操作按钮
  function getActionButton(record) {
    if (record.status === 'pending') {
      return `<button class="claim-btn px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm" data-record-id="${record.id}">领取</button>`;
    }
    
    if (record.status === 'claimed' && record.transaction_hash) {
      return `<a href="https://solscan.io/tx/${record.transaction_hash}" target="_blank" class="text-blue-600 hover:underline text-sm">查看交易</a>`;
    }
    
    return '';
  }
  
  // 获取资产ID
  function getAssetId() {
    // 方法1: 从URL获取
    const matches = window.location.pathname.match(/\/assets\/([^\/]+)/);
    if (matches && matches[1]) {
      return matches[1];
    }
    
    // 方法2: 从页面元素获取
    const assetIdElement = document.querySelector('[data-asset-id]');
    if (assetIdElement) {
      return assetIdElement.getAttribute('data-asset-id');
    }
    
    // 方法3: 从全局变量获取
    if (window.ASSET_ID) {
      return window.ASSET_ID;
    }
    
    if (window.assetId) {
      return window.assetId;
    }
    
    // 方法4: 从ASSET_CONFIG获取
    if (window.ASSET_CONFIG && window.ASSET_CONFIG.id) {
      return window.ASSET_CONFIG.id;
    }
    
    return null;
  }
  
  // 刷新分红历史
  window.refreshDividendHistory = function() {
    getMyDividendHistory()
      .then(data => {
        renderDividendTable(data.records || []);
      })
      .catch(error => {
        console.error('刷新分红历史失败:', error);
      });
  };
  
  // 初始化分红表格
  window.initDividendTable = function() {
    const tableContainer = document.getElementById('dividendHistoryTable');
    if (!tableContainer) {
      return;
    }
    
    // 获取并显示分红历史
    getMyDividendHistory()
      .then(data => {
        renderDividendTable(data.records || []);
      })
      .catch(error => {
        console.error('获取分红历史失败:', error);
        showMessage(`获取分红历史失败: ${error.message}`, 'error');
        
        // 显示空表格
        renderDividendTable([]);
      });
  };
  
  // 全局初始化
  function init() {
    log('初始化分红脚本');
    
    // 初始化分红表单
    initDividendForm();
    
    // 初始化分红表格
    if (document.getElementById('dividendHistoryTable')) {
      window.initDividendTable();
    }
  }
  
  // 当DOM加载完成后初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
})(); 