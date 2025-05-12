/**
 * RWA-HUB 钱包API修复脚本
 * 解决API 404错误和资产ID不一致问题
 * 版本: 1.5.2 - 生产环境强化版，优化初始化逻辑，避免重复运行
 */

// 防止重复初始化
if (window.walletApiFixInitialized) {
  console.log('钱包API修复脚本已初始化，跳过重复执行');
} else {
  window.walletApiFixInitialized = true;

  // 为全局window对象添加购买按钮更新函数
  window.updateBuyButtonStateGlobal = function(button, text, forceUpdate = false) {
    // 日志函数
    const log = function(message, data) {
      if (typeof console !== 'undefined' && console.log) {
        if (data !== undefined) {
          console.log(`[钱包API] ${message}`, data);
        } else {
          console.log(`[钱包API] ${message}`);
        }
      }
    };
    
    // 检查当前页面是否为资产详情页
    const isAssetDetailPage = function() {
      return (
        window.location.pathname.includes('/assets/') || 
        document.querySelector('.asset-detail-page') ||
        document.getElementById('asset-detail-container') ||
        document.getElementById('buy-button')
      );
    };
    
    try {
      // 设置单个按钮的状态
      const setButtonState = function(btn, btnText, force = false) {
        // 跳过处理无效的按钮
        if (!btn || !btn.tagName || btn.tagName.toLowerCase() !== 'button') {
          return false;
        }
        
        // 如果是详情页上的主购买按钮且不是强制更新，使用特殊处理
        const isMainDetailButton = btn.id === 'buy-button' || btn.classList.contains('detail-buy-button');
        if (isMainDetailButton && !force && isAssetDetailPage()) {
          // 在详情页上，尊重按钮当前的状态，可能被detail.html页面处理
          return false;
        }
        
        // 如果按钮被禁用且没有强制更新标志，不进行更新
        if (btn.disabled && !force) {
          return false;
        }
        
        // 对于普通按钮，更新内容
        const hasSpinner = btn.querySelector('.spinner-border') !== null;
        const originalText = btn.dataset.originalText || btn.textContent.trim();
        const newText = btnText || originalText || 'Buy';
        
        // 保存原始文本，如果尚未保存
        if (!btn.dataset.originalText) {
          btn.dataset.originalText = originalText;
        }
        
        // 是否为加载中状态
        const isProcessing = newText.includes('Processing') || newText.includes('处理中');
        
        // 更新按钮内容
        if (isProcessing && !hasSpinner) {
          // 添加加载指示器
          btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${newText}`;
        } else if (!isProcessing && hasSpinner) {
          // 移除加载指示器
          btn.innerHTML = newText;
        } else if (btn.textContent.trim() !== newText) {
          // 仅更新文本
          btn.innerHTML = btn.innerHTML.replace(btn.textContent.trim(), newText);
        }
        
        return true;
      };
      
      // 如果传入了具体按钮，则只更新该按钮
      if (button) {
        setButtonState(button, text, forceUpdate);
        return;
      }
      
      // 否则，批量更新所有购买按钮
      let count = 0;
      const buttons = document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"], #buyButton, .btn-buy, #buy-button');
      buttons.forEach(btn => {
        if (setButtonState(btn, text, forceUpdate)) {
          count++;
        }
      });
      
      log(`更新购买按钮状态`, { text: text || 'Buy', count });
      log(`共更新了 ${count} 个购买按钮`);
      
    } catch (error) {
      console.error('[钱包API] 更新购买按钮状态时出错:', error);
    }
  };

  // 将全局函数设置为标准函数名称，以确保兼容性
  window.updateBuyButtonState = window.updateBuyButtonState || window.updateBuyButtonStateGlobal;
  
  // 为API请求添加重试和错误处理功能
  const originalFetch = window.fetch;
  
  // 增强版fetch，支持多次重试和错误处理
  window.fetchWithRetry = async function(url, options = {}, retries = 3, backoff = 300) {
    // 如果遇到API错误，尝试替换URL部分
    const fixApiUrl = function(originalUrl) {
      // 替换一些常见的URL模式
      let fixedUrl = originalUrl;
      
      // 修复API端点
      if (originalUrl.includes('/api/')) {
        // 处理资产API调用
        if (originalUrl.includes('/api/assets/')) {
          // 标准化ID格式：移除多余的RH-前缀
          fixedUrl = fixedUrl.replace(/\/api\/assets\/RH-(\d+)\//, '/api/assets/$1/');
          fixedUrl = fixedUrl.replace(/\/api\/assets\/RH-(\d+)$/, '/api/assets/$1');
          
          // 处理多余的斜杠
          fixedUrl = fixedUrl.replace(/([^:])\/\/+/g, '$1/');
        }
        
        // 处理用户资产API
        if (originalUrl.includes('/api/user/assets')) {
          // 确保包含必要的查询参数
          if (!originalUrl.includes('?')) {
            fixedUrl = `${fixedUrl}?limit=50&offset=0`;
          } else if (!originalUrl.includes('limit=')) {
            fixedUrl = `${fixedUrl}&limit=50`;
          }
          
          // 添加时间戳防止缓存
          if (!originalUrl.includes('_=')) {
            fixedUrl = `${fixedUrl}&_=${Date.now()}`;
          }
        }
        
        // 处理钱包API
        if (originalUrl.includes('/api/wallet/')) {
          // 添加时间戳防止缓存
          if (!originalUrl.includes('_=')) {
            fixedUrl = `${fixedUrl}${originalUrl.includes('?') ? '&' : '?'}_=${Date.now()}`;
          }
        }
      }
      
      return fixedUrl;
    };
    
    // 修复URL
    const fixedUrl = fixApiUrl(url);
    
    // 添加身份验证令牌（如果有）
    const finalOptions = { ...options };
    
    // 确保headers存在
    finalOptions.headers = finalOptions.headers || {};
    
    // 尝试从cookie中获取钱包地址
    const getWalletAddressFromCookie = function() {
      const cookies = document.cookie.split(';');
      for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'wallet_address' || name === 'eth_address' || name === 'phantom_address') {
          return value;
        }
      }
      return null;
    };
    
    // 尝试从页面状态获取钱包地址
    const getWalletAddressFromState = function() {
      if (window.walletState && window.walletState.address) {
        return window.walletState.address;
      }
      
      if (window.ethereum && window.ethereum.selectedAddress) {
        return window.ethereum.selectedAddress;
      }
      
      if (window.solana && window.solana.publicKey) {
        return window.solana.publicKey.toString();
      }
      
      return null;
    };
    
    // 如果是API请求，添加钱包地址到header
    if (fixedUrl.includes('/api/') && !finalOptions.headers['X-Wallet-Address']) {
      const walletAddress = getWalletAddressFromState() || getWalletAddressFromCookie();
      if (walletAddress) {
        finalOptions.headers['X-Wallet-Address'] = walletAddress;
      }
    }
    
    // 执行fetch请求，支持重试
    let lastError;
    
    for (let i = 0; i <= retries; i++) {
      try {
        const response = await originalFetch(fixedUrl, finalOptions);
        
        // 如果响应成功，直接返回
        if (response.ok) {
          return response;
        }
        
        // 对于404错误尝试替代URL
        if (response.status === 404 && fixedUrl.includes('/api/')) {
          // 尝试替代路径
          const pathComponents = fixedUrl.split('/');
          const apiIndex = pathComponents.indexOf('api');
          
          if (apiIndex > 0 && apiIndex < pathComponents.length - 1) {
            // 尝试API v1路径
            const alternativeUrl = fixedUrl.replace('/api/', '/api/v1/');
            
            try {
              const altResponse = await originalFetch(alternativeUrl, finalOptions);
              if (altResponse.ok) {
                console.log(`[钱包API] 成功使用替代API路径: ${alternativeUrl}`);
                return altResponse;
              }
            } catch (altError) {
              // 忽略替代路径的错误
            }
          }
        }
        
        // 保存错误
        lastError = new Error(`请求失败: ${response.status} ${response.statusText}`);
        lastError.response = response;
        
      } catch (error) {
        lastError = error;
      }
      
      // 如果还有重试次数，等待后重试
      if (i < retries) {
        // 指数回退
        const delay = backoff * Math.pow(2, i);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
    
    // 所有重试失败，抛出最后一个错误
    throw lastError;
  };
  
  // 重写fetch函数
  window.fetch = async function(url, options = {}) {
    // 跳过非API请求和静态资源
    if (!url.includes('/api/') || url.includes('/static/') || url.includes('/vendor/')) {
      return originalFetch(url, options);
    }
    
    try {
      // 使用增强版fetch
      return await window.fetchWithRetry(url, options, 2);
    } catch (error) {
      console.error(`[钱包API] 请求失败: ${url}`, error);
      throw error;
    }
  };
  
  // 初始化函数
  const initWalletApiFix = function() {
    try {
      // 应用购买按钮状态修复
      if (typeof window.updateBuyButtonState === 'function') {
        // 确保在DOM加载后更新购买按钮
        setTimeout(() => {
          window.updateBuyButtonState(null, 'Buy');
        }, 500);
      }
      
      // 添加查询资产API兼容性处理
      const originalGetUserAssets = window.walletState?.getUserAssets;
      if (typeof originalGetUserAssets === 'function') {
        window.walletState.getUserAssets = async function(address) {
          try {
            // 调用原始函数
            return await originalGetUserAssets.call(this, address);
          } catch (error) {
            console.error('原始获取用户资产失败，尝试替代方法:', error);
            
            // 使用替代API调用
            try {
              // 确保地址参数有效
              if (!address && this.address) {
                address = this.address;
              }
              
              if (!address) {
                throw new Error('未提供钱包地址');
              }
              
              // 构建API URL
              const timestamp = Date.now();
              const apiUrl = `/api/user/assets?address=${encodeURIComponent(address)}&limit=50&_=${timestamp}`;
              
              // 调用API
              const response = await window.fetch(apiUrl);
              if (!response.ok) {
                throw new Error(`API响应错误: ${response.status}`);
              }
              
              const data = await response.json();
              if (!data.success) {
                throw new Error(data.error || '获取资产失败');
              }
              
              // 处理资产数据
              const assets = data.assets || [];
              console.log(`[钱包API] 获取到 ${assets.length} 个用户资产`);
              
              // 将资产数据保存到钱包状态
              this.assets = assets;
              
              // 触发余额更新事件
              if (typeof this.triggerBalanceUpdatedEvent === 'function') {
                this.triggerBalanceUpdatedEvent();
              }
              
              return assets;
            } catch (fallbackError) {
              console.error('获取用户资产的替代方法也失败:', fallbackError);
              throw fallbackError;
            }
          }
        };
      }
      
      console.log('[钱包API] 修复脚本初始化完成');
    } catch (error) {
      console.error('[钱包API] 初始化钱包API修复脚本失败:', error);
    }
  };
  
  // 在DOM加载完成后初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWalletApiFix);
  } else {
    // 如果DOM已加载完成，立即初始化
    initWalletApiFix();
  }
} 