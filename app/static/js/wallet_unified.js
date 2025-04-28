/**
 * wallet_unified.js - 统一钱包和购买按钮处理
 * 版本: 1.0.0
 * 作用: 统一管理钱包状态和购买按钮显示，确保英文"Buy"按钮
 */

(function() {
  // 避免重复初始化
  if (window.walletUnifiedInitialized) return;
  window.walletUnifiedInitialized = true;
  
  console.log('加载钱包统一处理模块 v1.0.0');
  
  // 配置
  const CONFIG = {
    debug: true,
    updateInterval: 1000,
    buttonTexts: {
      buy: 'Buy',
      buyDisabled: 'Buy',
      connect: 'Connect Wallet',
      loading: 'Loading...',
      insufficientBalance: 'Insufficient Balance'
    }
  };
  
  // 日志函数
  function log(message, data) {
    if (!CONFIG.debug) return;
    console.log(`[钱包统一] ${message}`, data || '');
  }
  
  // 全局钱包状态对象
  let walletState = {
    connected: false,
    address: null,
    walletType: null,
    balance: null,
    isAdmin: false
  };
  
  // 初始化全局更新函数
  window.updateBuyButtonState = function(buyButtons, forceText) {
    log('更新购买按钮状态');
    
    // 如果没有传入按钮，查找所有可能的购买按钮
    if (!buyButtons) {
      buyButtons = document.querySelectorAll(
        '.buy-btn, .buy-button, [data-action="buy"], #buyButton, button:contains("Buy"), ' +
        'a:contains("Buy"), .btn-buy, .purchase-button, [class*="buy"], .buy'
      );
    } else if (!Array.isArray(buyButtons) && !buyButtons.forEach) {
      // 如果传入单个按钮，转换为数组
      buyButtons = [buyButtons];
    }
    
    log(`处理 ${buyButtons.length} 个购买按钮`);
    
    // 获取钱包状态
    let connected = false;
    
    // 优先使用全局walletState
    if (window.walletState) {
      connected = window.walletState.isConnected || window.walletState.connected;
    } else {
      // 回退到localStorage检查
      const address = localStorage.getItem('walletAddress');
      connected = !!address;
    }
    
    // 处理每个按钮
    Array.from(buyButtons).forEach((btn, idx) => {
      if (!btn || typeof btn.textContent === 'undefined') return;
      
      // 如果强制指定文本，直接设置
      if (forceText) {
        btn.textContent = forceText;
        return;
      }
      
      // 获取当前文本
      const currentText = btn.textContent.trim();
      
      // 检查状态并更新相应文本
      if (!connected) {
        // 未连接钱包
        if (currentText !== CONFIG.buttonTexts.connect && 
            currentText !== '连接钱包' && 
            currentText !== 'Connect Wallet') {
          btn.textContent = CONFIG.buttonTexts.connect;
        }
      } else {
        // 已连接钱包，确保显示"Buy"
        if (currentText === '购买' || currentText === '买入' || currentText === 'purchase' || 
            (currentText !== CONFIG.buttonTexts.buy && btn.getAttribute('data-wallet-status') === 'ready')) {
          btn.textContent = CONFIG.buttonTexts.buy;
          log(`将按钮 #${idx} 从"${currentText}"更新为"${CONFIG.buttonTexts.buy}"`);
        }
      }
    });
    
    // 特别处理资产详情页的主购买按钮
    if (window.location.pathname.includes('/assets/')) {
      const detailBuyBtn = document.querySelector('#buyButton, .detail-buy-button, [data-asset-action="buy"]');
      if (detailBuyBtn && detailBuyBtn.textContent.trim() === '购买') {
        detailBuyBtn.textContent = CONFIG.buttonTexts.buy;
        log('已更新详情页主购买按钮为"Buy"');
      }
    }
  };
  
  // 监听钱包状态变化
  function setupWalletListeners() {
    // 监听现有的钱包事件
    document.addEventListener('walletConnected', function(e) {
      log('检测到钱包连接事件', e.detail);
      updateWalletState(true, e.detail.address, e.detail.walletType);
    });
    
    document.addEventListener('walletDisconnected', function() {
      log('检测到钱包断开事件');
      updateWalletState(false, null, null);
    });
    
    // 定期检查
    setInterval(function() {
      syncWalletState();
      window.updateBuyButtonState();
    }, CONFIG.updateInterval);
    
    // 页面加载完成后立即检查一次
    window.addEventListener('load', function() {
      syncWalletState();
      window.updateBuyButtonState();
      
      log('页面加载完成，已执行初始状态同步');
    });
  }
  
  // 同步钱包状态
  function syncWalletState() {
    let newState = {
      connected: false,
      address: null,
      walletType: null,
      balance: null,
      isAdmin: false
    };
    
    // 从全局对象获取
    if (window.walletState) {
      newState.connected = window.walletState.isConnected || window.walletState.connected;
      newState.address = window.walletState.address;
      newState.walletType = window.walletState.walletType;
      newState.balance = window.walletState.balance;
      newState.isAdmin = window.walletState.isAdmin;
    }
    
    // 如果没有连接信息，尝试从localStorage获取
    if (!newState.connected) {
      const address = localStorage.getItem('walletAddress');
      const walletType = localStorage.getItem('walletType');
      
      if (address) {
        newState.connected = true;
        newState.address = address;
        newState.walletType = walletType;
      }
    }
    
    // 检查是否有变化
    if (JSON.stringify(walletState) !== JSON.stringify(newState)) {
      log('钱包状态已更新', {
        before: walletState, 
        after: newState
      });
      
      // 更新状态
      walletState = newState;
      
      // 触发更新按钮
      window.updateBuyButtonState();
    }
  }
  
  // 更新钱包状态
  function updateWalletState(connected, address, walletType, balance, isAdmin) {
    walletState = {
      connected: connected,
      address: address,
      walletType: walletType,
      balance: balance,
      isAdmin: isAdmin
    };
    
    log('手动更新钱包状态', walletState);
    
    // 触发更新按钮
    window.updateBuyButtonState();
  }
  
  // 初始化
  function init() {
    log('初始化统一钱包模块');
    
    // 设置事件监听
    setupWalletListeners();
    
    // 第一次同步状态
    syncWalletState();
    
    // 在首次载入时执行按钮更新
    setTimeout(function() {
      window.updateBuyButtonState();
      log('初始按钮状态已更新');
    }, 500);
    
    log('统一钱包模块初始化完成');
  }
  
  // 启动
  init();
})(); 