/**
 * RWA-HUB 钱包API修复脚本
 * 解决API 404错误和资产ID不一致问题
 * 版本: 1.6.0 - 修复浏览器卡死问题，优化性能
 */

// 防止重复初始化
if (window.walletApiFixInitialized) {
  console.debug('[钱包API] 脚本已初始化，跳过重复执行');
} else {
  // 设置初始化标志
  window.walletApiFixInitialized = true;
  console.log('[钱包API] 初始化修复脚本 v1.6.0');

  // 安全执行函数 - 防止任何操作导致页面卡死
  function safeExecute(fn, fallback, timeout = 5000) {
    let hasCompleted = false;
    let timeoutId = null;
    
    // 设置安全超时
    timeoutId = setTimeout(() => {
      if (!hasCompleted) {
        console.debug('[钱包API] 操作超时终止');
        hasCompleted = true;
        
        if (typeof fallback === 'function') {
          try {
            fallback();
          } catch (e) {
            console.debug('[钱包API] 降级处理失败:', e);
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
              clearTimeout(timeoutId);
              hasCompleted = true;
            }
            return value;
          }).catch(err => {
            if (!hasCompleted) {
              clearTimeout(timeoutId);
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
      clearTimeout(timeoutId);
      hasCompleted = true;
      return result;
    } catch (error) {
      if (!hasCompleted) {
        clearTimeout(timeoutId);
        hasCompleted = true;
        console.debug('[钱包API] 操作执行失败:', error);
        
        if (typeof fallback === 'function') {
          try {
            return fallback();
          } catch (e) {
            console.debug('[钱包API] 降级处理失败:', e);
          }
        }
      }
      throw error;
    }
  }

  // 为全局window对象添加购买按钮更新函数
  window.updateBuyButtonStateGlobal = function(button, text, forceUpdate = false) {
    return safeExecute(() => {
      // 日志函数
      const log = function(message, data) {
        if (typeof console !== 'undefined' && console.debug) {
          if (data !== undefined) {
            console.debug(`[钱包API] ${message}`, data);
          } else {
            console.debug(`[钱包API] ${message}`);
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
        
      } catch (error) {
        console.error('[钱包API] 更新购买按钮状态时出错:', error);
      }
    }, null, 2000);
  };

  // 将全局函数设置为标准函数名称，以确保兼容性
  window.updateBuyButtonState = window.updateBuyButtonState || window.updateBuyButtonStateGlobal;
  
  // 修复API URL的函数
  function fixApiUrl(originalUrl) {
    try {
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
    } catch (e) {
      console.debug('[钱包API] 修复URL时出错:', e);
      return originalUrl;
    }
  }
  
  // 获取钱包地址的函数
  function getWalletAddress() {
    try {
      // 尝试从页面状态获取钱包地址
      if (window.walletState && window.walletState.address) {
        return window.walletState.address;
      }
      
      if (window.ethereum && window.ethereum.selectedAddress) {
        return window.ethereum.selectedAddress;
      }
      
      if (window.solana && window.solana.publicKey) {
        return window.solana.publicKey.toString();
      }
      
      // 尝试从cookie中获取钱包地址
      const cookies = document.cookie.split(';');
      for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'wallet_address' || name === 'eth_address' || name === 'phantom_address') {
          return value;
        }
      }
      
      // 尝试从localStorage获取
      return localStorage.getItem('walletAddress') || null;
    } catch (e) {
      console.debug('[钱包API] 获取钱包地址时出错:', e);
      return null;
    }
  }
  
  // 增强版fetch，支持多次重试和错误处理
  window.fetchWithRetry = async function(url, options = {}, retries = 2, backoff = 300) {
    return safeExecute(async () => {
      const originalFetch = window.fetch;
      const requestStartTime = Date.now();
      
      // 修复URL
      const fixedUrl = fixApiUrl(url);
      
      // 添加身份验证令牌（如果有）
      const finalOptions = { ...options };
      
      // 确保headers存在
      finalOptions.headers = finalOptions.headers || {};
      
      // 如果是API请求，添加钱包地址到header
      if (fixedUrl.includes('/api/') && !finalOptions.headers['X-Wallet-Address']) {
        const walletAddress = getWalletAddress();
        if (walletAddress) {
          finalOptions.headers['X-Wallet-Address'] = walletAddress;
        }
      }
      
      // 执行fetch请求，支持重试
      let lastError;
      let attempt = 0;
      const maxAttempts = retries + 1;
      
      while (attempt < maxAttempts) {
        attempt++;
        try {
          // 设置超时
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时
          
          if (!finalOptions.signal) {
            finalOptions.signal = controller.signal;
          }
          
          // 执行fetch
          const response = await originalFetch(fixedUrl, finalOptions);
          clearTimeout(timeoutId);
          
          // 如果响应成功，直接返回
          if (response.ok) {
            return response;
          }
          
          // 对于404错误尝试替代URL
          if (response.status === 404 && fixedUrl.includes('/api/')) {
            // 尝试替代路径（仅尝试一次API v1路径）
            const alternativeUrl = fixedUrl.replace('/api/', '/api/v1/');
            
            if (alternativeUrl !== fixedUrl) {
              try {
                const altController = new AbortController();
                const altTimeoutId = setTimeout(() => altController.abort(), 5000);
                
                const altOptions = { ...finalOptions };
                if (!altOptions.signal) {
                  altOptions.signal = altController.signal;
                }
                
                const altResponse = await originalFetch(alternativeUrl, altOptions);
                clearTimeout(altTimeoutId);
                
                if (altResponse.ok) {
                  console.debug(`[钱包API] 成功使用替代API路径: ${alternativeUrl}`);
                  return altResponse;
                }
              } catch (altError) {
                // 忽略替代路径的错误
                console.debug('[钱包API] 替代API路径失败:', alternativeUrl);
              }
            }
          }
          
          // 保存错误
          lastError = new Error(`请求失败: ${response.status} ${response.statusText}`);
          lastError.response = response;
          
          // 如果请求时间超过10秒，不再重试
          if (Date.now() - requestStartTime > 10000) {
            console.debug('[钱包API] 请求时间过长，停止重试:', fixedUrl);
            break;
          }
          
        } catch (error) {
          clearTimeout(timeoutId);
          lastError = error;
          
          // 如果是中止的请求，不再重试
          if (error.name === 'AbortError') {
            console.debug('[钱包API] 请求被中止:', fixedUrl);
            break;
          }
        }
        
        // 如果还有重试次数，等待后重试
        if (attempt < maxAttempts) {
          // 指数回退
          const delay = backoff * Math.pow(2, attempt - 1);
          console.debug(`[钱包API] 重试请求 (${attempt}/${maxAttempts})，延迟 ${delay}ms: ${fixedUrl}`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
      
      // 所有重试都失败
      throw lastError || new Error('请求失败，已达到最大重试次数');
    }, async () => {
      // 如果safeExecute超时，返回一个已拒绝的Promise
      console.debug('[钱包API] fetchWithRetry超时:', url);
      throw new Error('请求超时');
    }, 15000);
  };

  // 初始化钱包API修复
  const initWalletApiFix = function() {
    return safeExecute(() => {
      console.debug('[钱包API] 开始初始化修复功能');
      
      // 将fetchWithRetry添加为全局fetch的备选项
      window.fetchWithFallback = async function(url, options = {}) {
        try {
          return await window.fetch(url, options);
        } catch (error) {
          console.debug('[钱包API] 原始fetch失败，尝试使用fetchWithRetry:', error);
          return window.fetchWithRetry(url, options);
        }
      };
      
      // 保存原始函数，用于回退
      const originalFetch = window.fetch;
      
      // 将window.fetch替换为增强版本
      window.fetch = async function(url, options = {}) {
        // 只处理特定API请求，其他请求使用原始fetch
        if (typeof url === 'string' && (url.includes('/api/') || options?.headers?.['X-RWA-API'])) {
          return window.fetchWithRetry(url, options, 1);
        } else {
          return originalFetch(url, options);
        }
      };
      
      // 触发初始化完成事件
      document.dispatchEvent(new CustomEvent('walletApiFixReady'));
      
      console.log('[钱包API] 修复脚本初始化完成');
    }, () => {
      console.error('[钱包API] 初始化超时');
    }, 3000);
  };

  // 执行初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWalletApiFix);
  } else {
    // 使用setTimeout确保脚本在页面其他部分初始化后执行
    setTimeout(initWalletApiFix, 200);
  }
} 