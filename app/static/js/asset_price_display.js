/**
 * 资产价格显示管理脚本
 * 版本: 1.0.1 - 修复购买按钮显示问题，仅显示Buy而非价格
 */

(function() {
  // 避免重复加载
  if (window.assetPriceDisplayInitialized) {
    console.debug('[价格显示] 脚本已初始化，跳过重复执行');
    return;
  }
  window.assetPriceDisplayInitialized = true;
  
  console.log('[价格显示] 初始化价格显示脚本 v1.0.1');
  
  // 配置
  const CONFIG = {
    debug: false,
    apiTimeoutMs: 5000,       // API请求超时时间
    defaultPrice: null,       // 不设置默认价格，避免显示错误信息
    cacheExpiry: 60000,       // 缓存过期时间：60秒
    apiEndpoints: [
      '/api/assets/{id}/price',
      '/api/v1/assets/{id}/price',
      '/api/price/{id}'
    ],
    sellApiEndpoints: [
      '/api/assets/{id}/sell_price',
      '/api/v1/assets/{id}/sell_price'
    ]
  };
  
  // 价格缓存
  const priceCache = new Map();
  
  // 安全执行函数，带超时
  function safeExecute(func, onTimeout, timeoutMs = 3000) {
    return new Promise((resolve) => {
      let resolved = false;
      let timeoutId;
      
      // 设置超时
      if (timeoutMs > 0) {
        timeoutId = setTimeout(() => {
          if (!resolved) {
            resolved = true;
            if (onTimeout) {
              resolve(onTimeout());
            } else {
              resolve(null);
            }
          }
        }, timeoutMs);
      }
      
      // 执行函数
      try {
        const result = func();
        
        // 如果是Promise，等待其完成
        if (result instanceof Promise) {
          result
            .then(value => {
              if (!resolved) {
                resolved = true;
                clearTimeout(timeoutId);
                resolve(value);
              }
            })
            .catch(error => {
              if (!resolved) {
                resolved = true;
                clearTimeout(timeoutId);
                console.error('[价格显示] safeExecute Promise错误:', error);
                resolve(null);
              }
            });
        } else {
          // 如果不是Promise，直接返回结果
          if (!resolved) {
            resolved = true;
            clearTimeout(timeoutId);
            resolve(result);
          }
        }
      } catch (error) {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeoutId);
          console.error('[价格显示] safeExecute 执行错误:', error);
          resolve(null);
        }
      }
    });
  }
  
  // 日志函数
  function log(message, data) {
    const prefix = '[价格显示]';
    if (data !== undefined) {
      console.debug(prefix, message, data);
    } else {
      console.debug(prefix, message);
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
  
  // 从缓存获取数据
  function getFromCache(key) {
    const cached = priceCache.get(key);
    if (!cached) return null;
    
    // 检查是否过期
    if (Date.now() - cached.timestamp > CONFIG.cacheExpiry) {
      priceCache.delete(key);
      return null;
    }
    
    log(`使用缓存价格数据: ${key}`);
    return cached.data;
  }
  
  // 添加数据到缓存
  function addToCache(key, data) {
    priceCache.set(key, {
      data: data,
      timestamp: Date.now()
    });
    
    log(`价格数据已缓存: ${key}`);
  }
  
  // 格式化价格
  function formatPrice(price) {
    if (price === null || price === undefined || isNaN(price)) {
      return '$0.00';
    }
    
    // 转换为数字
    const numPrice = parseFloat(price);
    
    // 格式化为货币形式
    return '$' + numPrice.toFixed(2);
  }
  
  // 获取资产价格
  async function fetchAssetPrice(assetId, forceRefresh = false) {
    return safeExecute(async () => {
      // 标准化资产ID
      const normalizedId = normalizeAssetId(assetId);
      if (!normalizedId) {
        throw new Error('无效的资产ID');
      }
      
      // 移除RH-前缀，仅使用数字部分作为API参数
      const idForApi = normalizedId.replace('RH-', '');
      
      // 缓存键
      const cacheKey = `price_${normalizedId}`;
      
      // 如果不是强制刷新，检查缓存
      if (!forceRefresh) {
        const cachedPrice = getFromCache(cacheKey);
        if (cachedPrice !== null) {
          return cachedPrice;
        }
      }
      
      // 尝试所有API端点
      for (const endpointTemplate of CONFIG.apiEndpoints) {
        const endpoint = endpointTemplate.replace('{id}', idForApi);
        
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), CONFIG.apiTimeoutMs);
          
          const response = await fetch(endpoint, {
            method: 'GET',
            headers: {
              'Accept': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (!response.ok) {
            continue; // 尝试下一个端点
          }
          
          const data = await response.json();
          
          // 处理不同的API响应格式
          let price = null;
          
          if (data.price !== undefined) {
            price = data.price;
          } else if (data.unit_price !== undefined) {
            price = data.unit_price;
          } else if (data.current_price !== undefined) {
            price = data.current_price;
          } else if (data.data && data.data.price !== undefined) {
            price = data.data.price;
          }
          
          if (price !== null) {
            // 缓存结果
            addToCache(cacheKey, price);
            return price;
          }
        } catch (error) {
          console.debug(`[价格显示] API端点 ${endpoint} 获取价格失败:`, error);
          // 继续尝试下一个端点
        }
      }
      
      // 所有端点都失败，尝试从页面获取价格
      const priceFromDOM = extractPriceFromDOM(assetId);
      if (priceFromDOM !== null) {
        addToCache(cacheKey, priceFromDOM);
        return priceFromDOM;
      }
      
      // 最终都失败，返回null
      return null;
    }, () => {
      console.debug('[价格显示] 获取资产价格超时');
      return null;
    }, CONFIG.apiTimeoutMs + 2000);
  }
  
  // 从DOM中提取价格信息
  function extractPriceFromDOM(assetId) {
    try {
      // 尝试从价格元素中获取
      const priceElements = document.querySelectorAll('.asset-price, .price-value, [data-asset-price]');
      for (const el of priceElements) {
        // 检查是否属于正确的资产
        const elAssetId = el.getAttribute('data-asset-id');
        if (elAssetId && elAssetId !== assetId && elAssetId !== assetId.replace('RH-', '')) {
          continue;
        }
        
        // 尝试从data属性获取价格
        if (el.hasAttribute('data-price')) {
          const dataPrice = parseFloat(el.getAttribute('data-price'));
          if (!isNaN(dataPrice)) {
            return dataPrice;
          }
        }
        
        // 尝试从内容中提取价格
        const text = el.textContent.trim();
        if (text) {
          // 移除货币符号和逗号，解析数字
          const priceMatch = text.replace(/[$,]/g, '').match(/(\d+(\.\d+)?)/);
          if (priceMatch && priceMatch[1]) {
            const price = parseFloat(priceMatch[1]);
            if (!isNaN(price)) {
              return price;
            }
          }
        }
      }
      
      // 尝试从meta标签获取
      const metaPriceElement = document.querySelector('meta[name="asset-price"], meta[property="og:price:amount"]');
      if (metaPriceElement) {
        const metaPrice = parseFloat(metaPriceElement.getAttribute('content'));
        if (!isNaN(metaPrice)) {
          return metaPrice;
        }
      }
      
      // 从全局变量中获取
      if (window.ASSET_CONFIG && window.ASSET_CONFIG.price) {
        return parseFloat(window.ASSET_CONFIG.price);
      }
      
      return null;
    } catch (error) {
      console.debug('[价格显示] 从DOM提取价格失败:', error);
      return null;
    }
  }
  
  // 更新页面上的价格显示
  async function updatePriceDisplay(assetId) {
    try {
      if (!assetId) {
        // 尝试从URL中获取
        const urlMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
        if (urlMatch && urlMatch[1]) {
          assetId = urlMatch[1];
        }
      }
      
      if (!assetId) {
        // 尝试从页面元素获取
        const assetIdElement = document.querySelector('[data-asset-id]');
        if (assetIdElement) {
          assetId = assetIdElement.getAttribute('data-asset-id');
        }
      }
      
      if (!assetId) {
        // 尝试从全局ASSET_CONFIG获取
        if (window.ASSET_CONFIG && window.ASSET_CONFIG.id) {
          assetId = window.ASSET_CONFIG.id;
        }
      }
      
      if (!assetId) {
        console.debug('[价格显示] 无法确定当前资产ID');
        return;
      }
      
      // 获取资产价格
      const price = await fetchAssetPrice(assetId);
      
      if (price === null) {
        console.debug('[价格显示] 无法获取资产价格，跳过更新显示');
        return;
      }
      
      // 使用requestAnimationFrame更新DOM
      requestAnimationFrame(() => {
        // 更新价格显示元素
        const priceElements = document.querySelectorAll('.asset-price, .price-value, [data-asset-price]');
        priceElements.forEach(el => {
          el.textContent = formatPrice(price);
          el.setAttribute('data-price', price);
        });
        
        // 更新购买按钮数据属性（不更改按钮文本）
        updateBuyButtonPrice(assetId, price);
      });
      
      return price;
    } catch (error) {
      console.debug('[价格显示] 更新价格显示失败:', error);
      return null;
    }
  }
  
  // 更新购买按钮价格数据属性（但不更改按钮文本）
  function updateBuyButtonPrice(assetId, price) {
    try {
      const buyButtons = document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"], #buyButton, .btn-buy, #buy-button');
      
      buyButtons.forEach(button => {
        // 检查是否是正确资产的按钮
        const buttonAssetId = button.getAttribute('data-asset-id');
        if (buttonAssetId && buttonAssetId !== assetId && buttonAssetId !== assetId.replace('RH-', '')) {
          return;
        }
        
        // 注意：不再修改按钮文本，只更新数据属性
        
        // 重要：保存原始数值价格到data属性
        if (price !== null && !isNaN(parseFloat(price))) {
          const numericPrice = parseFloat(price);
          // 保存价格到data属性 - 两个属性都设置确保兼容性
          button.setAttribute('data-price', numericPrice);
          button.setAttribute('data-token-price', numericPrice);
          
          // 添加日志以便调试
          log(`已更新按钮价格属性: data-price=${numericPrice}, data-token-price=${numericPrice}`);
        }
      });
    } catch (error) {
      console.debug('[价格显示] 更新购买按钮数据属性失败:', error);
    }
  }
  
  // 初始化
  function init() {
    return safeExecute(() => {
      log('正在初始化价格显示脚本...');
      
      // 立即触发一次更新
      setTimeout(() => {
        updatePriceDisplay();
      }, 500);
      
      // 定期更新价格（每5分钟）
      setInterval(() => {
        updatePriceDisplay();
      }, 300000);
      
      // 添加页面变化监听器，处理动态添加的元素
      const observer = new MutationObserver((mutations) => {
        // 检查是否有新的价格元素或购买按钮
        const hasPriceElements = document.querySelector('.asset-price, .price-value, [data-asset-price], .buy-btn, .buy-button, [data-action="buy"], #buyButton, .btn-buy');
        if (hasPriceElements) {
          setTimeout(() => {
            updatePriceDisplay();
          }, 200);
        }
      });
      
      // 配置并启动观察器
      observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: false,
        characterData: false
      });
      
      // 监听URL变化（单页应用）
      let lastUrl = location.href;
      const urlObserver = new MutationObserver(() => {
        const currentUrl = location.href;
        if (currentUrl !== lastUrl) {
          lastUrl = currentUrl;
          // URL变化后更新价格
          setTimeout(() => {
            updatePriceDisplay();
          }, 500);
        }
      });
      
      urlObserver.observe(document, { subtree: true, childList: true });
      
      log('价格显示脚本初始化完成 (不修改按钮文本)');
      
      // 发布初始化完成事件
      document.dispatchEvent(new CustomEvent('assetPriceDisplayReady'));
    }, () => {
      console.error('[价格显示] 初始化超时');
    }, 5000);
  }
  
  // 暴露全局方法
  window.updateAssetPrice = updatePriceDisplay;
  
  // 启动初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 200);
  }
})(); 