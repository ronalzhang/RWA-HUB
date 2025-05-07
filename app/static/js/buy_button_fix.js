/**
 * buy_button_fix.js - 购买按钮语言修复脚本
 * 版本: 1.0.1
 * 作用: 确保购买按钮始终显示为英文"Buy"，避免显示为中文"购买"
 * 更新: 增强检测资产详情页面功能，不再干扰特殊按钮
 */

(function() {
  // 避免重复加载
  if (window.buyButtonFixInitialized) return;
  window.buyButtonFixInitialized = true;
  
  // 配置
  const CONFIG = {
    debug: true, // 开启调试减少日志
    buttonText: 'Buy',
    checkInterval: 2000,  // 更频繁检查以捕获快速变化
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
      
      // 重要：移除了 '#buy-button' 和其他资产详情页特定选择器
      // 详情页按钮将被排除在外
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
  
  // 主函数：强制按钮显示为英文
  function forceEnglishButtons() {
    try {
      // 如果在资产详情页，不处理按钮
      if (isAssetDetailPage()) {
        log('检测到资产详情页，大部分功能将被禁用');
      }
      
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
  
  // 拦截按钮文本变化（仅用于非详情页按钮）
  function interceptButtonTextChanges(button) {
    // 检查是否应该跳过此按钮
    if (shouldSkipButton(button)) {
      return;
    }
    
    // 只处理尚未拦截过的按钮
    if (button._textChangeIntercepted) return;
    
    // 标记该按钮已被拦截
    button._textChangeIntercepted = true;
    
    // 为按钮设置特殊属性描述符
    try {
      // 拦截innerHTML属性
      const originalInnerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
      Object.defineProperty(button, 'innerHTML', {
        get: function() {
          return originalInnerHTML.get.call(this);
        },
        set: function(value) {
          // 执行原始的innerHTML设置
          originalInnerHTML.set.call(this, value);
          
          // 如果设置的内容包含"购买"，则替换为"Buy"
          // 但跳过包含数字的内容
          if (value.includes('购买') && !/^\s*\d+(\.\d+)?\s*$/.test(value)) {
            setTimeout(() => {
              replaceTextNodesOnly(this, '购买', 'Buy');
            }, 0);
          }
          
          return value;
        },
        configurable: true
      });
      
      // 拦截textContent属性
      const originalTextContent = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
      Object.defineProperty(button, 'textContent', {
        get: function() {
          return originalTextContent.get.call(this);
        },
        set: function(value) {
          // 如果是详情页的按钮，不拦截
          if (isAssetDetailPage() && shouldSkipButton(this)) {
            return originalTextContent.set.call(this, value);
          }
          
          // 如果尝试设置"购买"，则改为设置"Buy"
          // 但保护数字内容
          if (value === '购买') {
            value = 'Buy';
          } else if (/^\s*\d+(\.\d+)?\s*$/.test(value)) {
            // 如果是纯数字，不做处理
            log('保护数字内容:', value);
          }
          return originalTextContent.set.call(this, value);
        },
        configurable: true
      });
    } catch (e) {
      log('拦截按钮文本变化失败', e);
    }
  }
  
  // 监听DOM变化，捕获动态添加的按钮（排除详情页）
  function observeDOM() {
    log('开始监听DOM变化');
    
    // 创建MutationObserver实例
    const observer = new MutationObserver(mutations => {
      // 检查是否有新按钮添加或现有按钮内容变化
      let shouldForceEnglish = false;
      
      // 如果在资产详情页，降低观察敏感度
      if (isAssetDetailPage()) {
        // 仍然观察DOM变化，但不会对详情页的按钮进行更改
        return;
      }
      
      mutations.forEach(mutation => {
        // 如果有节点添加
        if (mutation.addedNodes.length > 0) {
          shouldForceEnglish = true;
        }
        
        // 如果属性或内容变化
        if (mutation.type === 'attributes' || mutation.type === 'childList') {
          const target = mutation.target;
          
          // 检查是否是购买按钮，但排除详情页特定按钮
          if (target.nodeType === Node.ELEMENT_NODE && 
             (target.classList.contains('buy-btn') || 
              target.getAttribute('data-action') === 'buy') && 
             !shouldSkipButton(target)) {
            shouldForceEnglish = true;
          }
        }
      });
      
      // 如果需要强制英文，执行修复
      if (shouldForceEnglish) {
        forceEnglishButtons();
      }
    });
    
    // 配置观察选项
    const config = { 
      childList: true,       // 观察子节点的添加或删除
      subtree: true,         // 观察所有后代节点
      attributes: true,      // 观察属性变化
      characterData: true    // 观察节点内容或文本
    };
    
    // 开始观察
    observer.observe(document.body, config);
    
    return observer;
  }
  
  // 覆盖全局更新函数，确保它们使用英文（仅非详情页）
  function overrideGlobalUpdateFunctions() {
    log('覆盖全局按钮更新函数');
    
    // 排除资产详情页
    if (isAssetDetailPage()) {
      log('在资产详情页上禁用全局函数覆盖');
      return;
    }
    
    // 备份原始函数
    if (window.updateBuyButtonState && !window._originalUpdateBuyButtonState) {
      window._originalUpdateBuyButtonState = window.updateBuyButtonState;
      
      // 覆盖全局函数
      window.updateBuyButtonState = function() {
        // 调用原始函数
        const result = window._originalUpdateBuyButtonState.apply(this, arguments);
        
        // 然后强制英文
        setTimeout(forceEnglishButtons, 10);
        
        return result;
      };
      
      log('成功覆盖 updateBuyButtonState 函数');
    }
    
    // 覆盖window.updateAllBuyButtons
    if (window.updateAllBuyButtons && !window._originalUpdateAllBuyButtons) {
      window._originalUpdateAllBuyButtons = window.updateAllBuyButtons;
      
      // 覆盖全局函数
      window.updateAllBuyButtons = function() {
        // 调用原始函数
        const result = window._originalUpdateAllBuyButtons.apply(this, arguments);
        
        // 在非详情页上强制英文
        if (!isAssetDetailPage()) {
          setTimeout(forceEnglishButtons, 10);
        }
        
        return result;
      };
      
      log('成功覆盖 updateAllBuyButtons 函数');
    }
  }
  
  // 初始化函数
  function init() {
    log('初始化购买按钮修复模块');
    
    // 等待DOM加载完成
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', onReady);
    } else {
      onReady();
    }
    
    function onReady() {
      // 检查是否在资产详情页
      const onDetailPage = isAssetDetailPage();
      if (onDetailPage) {
        log('检测到资产详情页，将减少干预以避免影响特殊按钮');
      }
      
      // 立即执行一次
      forceEnglishButtons();
      
      // 开始观察DOM变化
      const observer = observeDOM();
      
      // 覆盖全局函数（仅非详情页）
      if (!onDetailPage) {
        overrideGlobalUpdateFunctions();
      }
      
      // 定时强制更新，在详情页上使用更长的间隔
      CONFIG.checkInterval = onDetailPage ? 5000 : 2000; // 详情页5秒，其他页面2秒
      
      // 在详情页上完全禁用定时器
      let intervalId = null;
      if (!onDetailPage) {
        intervalId = setInterval(forceEnglishButtons, CONFIG.checkInterval);
        log('已启动定时更新，间隔：' + CONFIG.checkInterval + 'ms');
      } else {
        log('在资产详情页上禁用了定时更新');
      }
      
      // 保存清理函数
      window.cleanupBuyButtonFix = function() {
        if (intervalId) clearInterval(intervalId);
        observer.disconnect();
        log('已清理购买按钮修复模块');
      };
      
      log('购买按钮修复模块初始化完成');
    }
  }
  
  // 执行初始化
  init();
})(); 