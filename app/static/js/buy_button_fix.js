/**
 * buy_button_fix.js - 购买按钮语言修复脚本
 * 版本: 1.0.3
 * 作用: 确保购买按钮始终显示为英文"Buy"，避免显示为中文"购买"
 * 更新: 改进与wallet_api_fix.js的兼容性，优化详情页按钮处理
 */

(function() {
  // 避免重复加载
  if (window.buyButtonFixInitialized) return;
  window.buyButtonFixInitialized = true;
  
  // 配置
  const CONFIG = {
    debug: false, // 关闭调试减少日志
    buttonText: 'Buy',
    checkInterval: 2500,  // 减少检查频率，避免过度干预
    selectorPatterns: [
      // 通用选择器 - 移除了不支持的选择器
      '.buy-btn',
      '.buy-button',
      '[data-action="buy"]',
      '#buyButton',
      '.btn-buy',
      '.purchase-button',
      '[class*="buy"]',
      '.buy'
    ],
    excludeSelectors: [
      // 排除详情页的主购买按钮
      '#buy-button',
      '.detail-buy-button',
      '[data-asset-action="buy"]'
    ]
  };
  
  // 日志函数
  function log(message, data) {
    if (!CONFIG.debug) return;
    console.log(`[购买按钮修复] ${message}`, data || '');
  }
  
  // 检查是否在资产详情页
  function isAssetDetailPage() {
    return (
      window.location.pathname.includes('/assets/') || 
      document.querySelector('.asset-detail-page') ||
      document.getElementById('asset-detail-container') ||
      document.getElementById('buy-button')
    );
  }
  
  // 是否应该跳过处理该按钮
  function shouldSkipButton(btn) {
    // 1. 跳过详情页的特定按钮
    if (isAssetDetailPage() && 
        (btn.id === 'buy-button' || 
         btn.classList.contains('detail-buy-button') ||
         btn.hasAttribute('data-asset-id'))) {
      log(`跳过详情页特定按钮: ${btn.id || btn.className}`);
      return true;
    }
    
    // 2. 检查排除选择器
    for (const selector of CONFIG.excludeSelectors) {
      if (btn.matches(selector)) {
        log(`按钮匹配排除选择器 ${selector}，跳过处理`);
        return true;
      }
    }
    
    // 3. 跳过数字文本内容
    const btnText = btn.textContent.trim();
    if (/^\s*\d+(\.\d+)?\s*$/.test(btnText)) {
      log(`按钮文本为数字 "${btnText}"，跳过处理`);
      return true;
    }
    
    // 4. 检查是否有资产ID或代币价格数据属性
    if (btn.hasAttribute('data-asset-id') || 
        btn.hasAttribute('data-token-price')) {
      log(`按钮具有资产数据属性，跳过处理`);
      return true;
    }

    return false;
  }
  
  // 主函数：强制按钮显示为英文 - 使用全局钱包API提供的函数
  function forceEnglishButtons() {
    try {
      // 如果在资产详情页，减少干预
      if (isAssetDetailPage()) {
        log('检测到资产详情页，将减少干预以避免影响特殊按钮');
        return 0;
      }
      
      // 使用全局函数更新所有按钮(如果可用)
      if (typeof window.updateBuyButtonState === 'function') {
        log('使用全局updateBuyButtonState函数更新按钮');
        window.updateBuyButtonState(null, 'Buy');
        return 1;
      }
      
      // 否则使用自己的实现
      log('全局更新函数不可用，使用自己的实现');
      
      // 合并所有选择器
      const selector = CONFIG.selectorPatterns.join(', ');
      
      // 查找所有可能的购买按钮
      const buttons = document.querySelectorAll(selector);
      log(`找到 ${buttons.length} 个潜在购买按钮`);
      
      // 处理每个按钮
      let modifiedCount = 0;
      buttons.forEach((btn, idx) => {
        // 检查是否应该跳过此按钮
        if (shouldSkipButton(btn)) {
          return;
        }
        
        // 检查按钮内容
        const btnText = btn.textContent.trim();
        
        // 仅当文本是中文"购买"时才替换为英文"Buy"
        if (btnText === '购买' || btnText.includes('购买')) {
          const originalText = btnText;
          
          // 防止覆盖带有图标和其他内容的按钮
          if (btn.innerHTML.includes('<i class="') || btn.innerHTML.includes('<span')) {
            // 保留HTML结构，仅替换文本节点
            replaceTextNodesOnly(btn, '购买', 'Buy');
          } else {
            btn.textContent = CONFIG.buttonText;
          }
          
          log(`已将按钮 #${idx} 从"${originalText}"更新为"${CONFIG.buttonText}"`);
          modifiedCount++;
        }
      });
      
      log(`共修改了 ${modifiedCount} 个按钮的文本`);
      return modifiedCount;
    } catch (e) {
      console.error('购买按钮修复错误:', e);
      return 0;
    }
  }
  
  // 替换所有文本节点，保留HTML结构
  function replaceTextNodesOnly(element, searchText, replaceText) {
    if (!element) return;
    
    // 如果是文本节点
    if (element.nodeType === Node.TEXT_NODE) {
      if (element.textContent.includes(searchText)) {
        element.textContent = element.textContent.replace(searchText, replaceText);
      }
      return;
    }
    
    // 递归处理所有子节点
    element.childNodes.forEach(child => {
      replaceTextNodesOnly(child, searchText, replaceText);
    });
  }
  
  // 重写全局函数，使之与wallet_api_fix.js兼容
  function overrideGlobalUpdateFunctions() {
    // 如果原始函数不存在，先创建兼容函数
    if (typeof window.updateBuyButtonState !== 'function') {
      log('创建全局updateBuyButtonState兼容函数');
      window.updateBuyButtonState = function(button, text) {
        if (button) {
          // 跳过详情页的特定按钮
          if (isAssetDetailPage() && shouldSkipButton(button)) {
            return;
          }
          
          if (button.innerHTML.indexOf('fa-') === -1) {
            button.innerHTML = `<i class="fas fa-shopping-cart me-2"></i>${text || 'Buy'}`;
          } else {
            // 只替换文本
            replaceTextNodesOnly(button, '购买', text || 'Buy');
          }
        } else {
          // 调用我们自己的函数来更新所有按钮
          forceEnglishButtons();
        }
      };
    } else {
      log('全局updateBuyButtonState函数已存在，不进行覆盖');
    }
  }
  
  // 初始化函数
  function init() {
    log('初始化购买按钮修复脚本 v1.0.3');
    
    // 等待DOM加载完成
    function onReady() {
      try {
        // 确保全局更新函数存在
        overrideGlobalUpdateFunctions();
        
        // 立即执行一次按钮修复
        setTimeout(() => {
          forceEnglishButtons();
        }, 500);
        
        // 减少定期检查频率，避免干扰详情页
        if (!isAssetDetailPage()) {
          // 减少间隔时间
          setInterval(forceEnglishButtons, CONFIG.checkInterval);
        } else {
          log('在资产详情页上，禁用定期检查');
        }
        
        // 监听DOM变化
        if (typeof MutationObserver !== 'undefined' && !isAssetDetailPage()) {
          const observer = new MutationObserver(mutations => {
            let shouldUpdate = false;
            
            mutations.forEach(mutation => {
              if (mutation.type === 'childList' || mutation.type === 'attributes') {
                shouldUpdate = true;
              }
            });
            
            if (shouldUpdate) {
              forceEnglishButtons();
            }
          });
          
          // 观察整个document，但减少回调调用频率
          observer.observe(document.body, { 
            childList: true, 
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: ['class', 'style', 'disabled'] 
          });
          
          log('已注册DOM变化监听器');
        }
        
        log('初始化完成');
      } catch (e) {
        console.error('购买按钮修复初始化失败:', e);
      }
    }
    
    // 检查DOM状态并初始化
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      onReady();
    } else {
      document.addEventListener('DOMContentLoaded', onReady);
    }
  }
  
  // 启动初始化
  init();
})(); 