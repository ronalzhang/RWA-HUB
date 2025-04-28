/**
 * dividend_fix.js - 分红显示修复脚本
 * 版本: 1.0.1
 */

(function() {
  // 避免重复加载
  if (window.dividendFixInitialized) return;
  window.dividendFixInitialized = true;
  
  // 配置
  const CONFIG = {
    debug: false,
    apiRetryInterval: 3000,
    apiMaxRetries: 2
  };
  
  // 日志函数
  function log(message, data) {
    if (!CONFIG.debug) return;
    console.log(`[分红修复] ${message}`, data || '');
  }

  // 日志错误函数
  function logError(message, data) {
    if (!CONFIG.debug) return;
    console.error(`[分红修复] ${message}`, data || '');
  }
  
  // 处理API错误的函数
  function handleApiError(error, endpoint) {
    // 降级为调试级别日志，不要输出为错误
    console.debug(`[分红API] 调用${endpoint}失败, 使用默认值`, error);
    return {success: false};
  }
  
  // 尝试多个API端点，直到一个成功
  async function tryApiSequentially(apis, transformFn) {
    let result = null;
    let errors = [];
    
    for (let i = 0; i < apis.length; i++) {
      try {
        const endpoint = apis[i];
        log(`尝试API端点 (${i+1}/${apis.length}): ${endpoint}`);
        
        // 使用带超时的fetch
        const timeoutPromise = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('请求超时')), 5000)
        );
        
        const response = await Promise.race([
          fetch(endpoint),
          timeoutPromise
        ]);
        
        if (!response.ok) {
          throw new Error(`HTTP错误 ${response.status}`);
        }
        
        const data = await response.json();
        
        // 如果有数据转换函数，则应用它
        result = transformFn ? transformFn(data) : data;
        
        // 成功获取数据后结束
        log(`API调用成功: ${endpoint}`);
        return result;
      } catch (error) {
        // 收集错误信息，但继续尝试下一个API
        errors.push({api: apis[i], error: error.message});
        
        // 不要输出为错误，而是降级为调试日志
        console.debug(`[分红API] 尝试API失败: ${apis[i]}`, error);
      }
    }
    
    // 所有API都失败后，尝试几次后不再重试
    if (errors.length > 0 && CONFIG.apiMaxRetries > 0) {
      log(`所有API尝试失败，${CONFIG.apiMaxRetries}秒后重试..`, errors);
      
      // 减少重试计数
      CONFIG.apiMaxRetries--;
      
      return new Promise(resolve => {
        setTimeout(() => {
          resolve(tryApiSequentially(apis, transformFn));
        }, CONFIG.apiRetryInterval);
      });
    }
    
    // 所有尝试都失败，返回默认结果
    return {success: false, errors};
  }
  
  // 加载分红数据
  async function loadDividendData(assetId) {
    if (!assetId) {
      console.debug('[分红修复] 缺少资产ID，无法加载分红数据');
      return null;
    }
    
    try {
      // 构建多个可能的API端点路径
      const apis = [
        `/api/assets/${assetId}/dividend_stats`,
        `/api/dividend/total/${assetId}`
      ];
      
      // 尝试顺序调用API，直到成功
      const data = await tryApiSequentially(apis, response => {
        // 任何返回数据都视为有效，将处理结果规范化
        return {
          success: true,
          total_dividends: response.total_dividends || response.total || 0,
          last_dividend: response.last_dividend || response.latest || null,
          next_dividend: response.next_dividend || response.upcoming || null
        };
      }).catch(error => {
        // 仅输出调试日志，不要显示为错误
        console.debug("[分红API] 数据加载失败", error);
        return {success: false};
      });
      
      return data;
    } catch (error) {
      console.debug("[分红API] 未能加载分红数据", error);
      return {success: false};
    }
  }
  
  // 更新页面上的分红显示
  function updateDividendDisplay(assetId, data) {
    if (!data || !data.success) {
      // 如果没有数据，使用默认显示
      const dividendElements = document.querySelectorAll('.dividend-amount, .dividend-info');
      dividendElements.forEach(el => {
        // 隐藏分红信息而不是显示错误
        el.style.display = 'none';
      });
      return;
    }
    
    // 更新总分红金额
    const totalDividendElements = document.querySelectorAll('.total-dividend, .total-dividends');
    totalDividendElements.forEach(el => {
      el.textContent = formatCurrency(data.total_dividends || 0);
      el.setAttribute('data-amount', data.total_dividends || 0);
    });
    
    // 更新最近分红信息
    if (data.last_dividend) {
      const lastDividendElements = document.querySelectorAll('.last-dividend, .latest-dividend');
      lastDividendElements.forEach(el => {
        const amount = data.last_dividend.amount || 0;
        const date = data.last_dividend.date || '';
        
        el.textContent = `${formatCurrency(amount)} (${formatDate(date)})`;
        el.setAttribute('data-amount', amount);
        el.setAttribute('data-date', date);
      });
    }
    
    // 更新下次分红信息
    if (data.next_dividend) {
      const nextDividendElements = document.querySelectorAll('.next-dividend, .upcoming-dividend');
      nextDividendElements.forEach(el => {
        const amount = data.next_dividend.amount || 0;
        const date = data.next_dividend.date || '';
        
        el.textContent = `${formatCurrency(amount)} (${formatDate(date)})`;
        el.setAttribute('data-amount', amount);
        el.setAttribute('data-date', date);
      });
    }
    
    // 显示所有分红相关元素
    document.querySelectorAll('.dividend-section, .dividend-info, .dividend-container').forEach(el => {
      el.style.display = '';
    });
  }
  
  // 格式化货币
  function formatCurrency(value) {
    if (!value) return '$0.00';
    
    const num = parseFloat(value);
    if (isNaN(num)) return '$0.00';
    
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num);
  }
  
  // 格式化日期
  function formatDate(dateStr) {
    if (!dateStr) return '';
    
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return '';
      
      return date.toLocaleDateString();
    } catch (e) {
      return '';
    }
  }
  
  // 主函数：修复分红显示
  function fixDividendDisplay() {
    // 获取当前资产ID
    let assetId = null;
    
    // 尝试从URL中获取
    const urlMatch = window.location.pathname.match(/\/assets\/([^\/]+)/);
    if (urlMatch && urlMatch[1]) {
      assetId = urlMatch[1];
    }
    
    // 尝试从页面元素获取
    if (!assetId) {
      const assetIdElement = document.querySelector('[data-asset-id]');
      if (assetIdElement) {
        assetId = assetIdElement.getAttribute('data-asset-id');
      }
    }
    
    // 如果找不到资产ID，返回
    if (!assetId) {
      return;
    }
    
    // 加载分红数据并更新显示
    loadDividendData(assetId).then(data => {
      updateDividendDisplay(assetId, data);
    }).catch(error => {
      // 不要作为错误输出
      console.debug('[分红修复] 处理分红数据时出错', error);
    });
  }
  
  // 在DOM加载完成后执行
  function onDomReady(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback);
    } else {
      callback();
    }
  }
  
  // 初始化
  onDomReady(fixDividendDisplay);
  
  // 暴露公共API
  window.dividendFix = {
    refreshDividendInfo: fixDividendDisplay
  };
})(); 