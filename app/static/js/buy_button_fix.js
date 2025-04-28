/**
 * buy_button_fix.js - 购买按钮语言修复脚本
 * 版本: 1.0.0
 * 作用: 确保购买按钮始终显示为英文"Buy"，避免显示为中文"购买"
 */

(function() {
  // 避免重复加载
  if (window.buyButtonFixInitialized) return;
  window.buyButtonFixInitialized = true;
  
  // 配置
  const CONFIG = {
    debug: false, // 关闭调试减少日志
    buttonText: 'Buy',
    checkInterval: 200,  // 更频繁检查以捕获快速变化
    selectorPatterns: [
      // 通用选择器 - 移除了不支持的选择器
      '.buy-btn',
      '.buy-button',
      '[data-action="buy"]',
      '#buyButton',
      '.btn-buy',
      '.purchase-button',
      '[class*="buy"]',
      '.buy',
      
      // 特定页面选择器
      '#buy-button',
      '.detail-buy-button',
      '[data-asset-action="buy"]',
      '.asset-buy-button'
    ]
  };
  
  // 日志函数
  function log(message, data) {
    if (!CONFIG.debug) return;
    console.log(`[购买按钮修复] ${message}`, data || '');
  }
  
  // 主函数：强制按钮显示为英文
  function forceEnglishButtons() {
    try {
      // 合并所有选择器
      const selector = CONFIG.selectorPatterns.join(', ');
      
      // 查找所有可能的购买按钮
      const buttons = document.querySelectorAll(selector);
      log(`找到 ${buttons.length} 个潜在购买按钮`);
      
      // 处理每个按钮
      let modifiedCount = 0;
      buttons.forEach((btn, idx) => {
        // 检查按钮内容
        const btnText = btn.textContent.trim();
        
        // 如果文本包含"购买"，替换为"Buy"
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
          
          // 标记按钮，防止其他脚本改回来
          btn.setAttribute('data-text-locked', 'true');
          
          // 覆盖内部函数：拦截任何setText类似的操作
          interceptButtonTextChanges(btn);
        }
        
        // 如果按钮已通过data-wallet-status标记为就绪状态，也确保显示"Buy"
        if (btn.getAttribute('data-wallet-status') === 'ready') {
          btn.textContent = CONFIG.buttonText;
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
  
  // 拦截按钮文本变化
  function interceptButtonTextChanges(button) {
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
          if (value.includes('购买')) {
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
          // 如果尝试设置"购买"，则改为设置"Buy"
          if (value === '购买') {
            value = 'Buy';
          }
          return originalTextContent.set.call(this, value);
        },
        configurable: true
      });
    } catch (e) {
      log('拦截按钮文本变化失败', e);
    }
  }
  
  // 监听DOM变化，捕获动态添加的按钮
  function observeDOM() {
    log('开始监听DOM变化');
    
    // 创建MutationObserver实例
    const observer = new MutationObserver(mutations => {
      // 检查是否有新按钮添加或现有按钮内容变化
      let shouldForceEnglish = false;
      
      mutations.forEach(mutation => {
        // 如果有节点添加
        if (mutation.addedNodes.length > 0) {
          shouldForceEnglish = true;
        }
        
        // 如果属性或内容变化
        if (mutation.type === 'attributes' || mutation.type === 'childList') {
          const target = mutation.target;
          
          // 检查是否是购买按钮
          if (target.nodeType === Node.ELEMENT_NODE && 
             (target.classList.contains('buy-btn') || 
              target.id === 'buy-button' || 
              target.getAttribute('data-action') === 'buy')) {
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
  
  // 覆盖全局更新函数，确保它们使用英文
  function overrideGlobalUpdateFunctions() {
    log('覆盖全局按钮更新函数');
    
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
        
        // 然后强制英文
        setTimeout(forceEnglishButtons, 10);
        
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
      // 立即执行一次
      forceEnglishButtons();
      
      // 开始观察DOM变化
      const observer = observeDOM();
      
      // 覆盖全局函数
      overrideGlobalUpdateFunctions();
      
      // 定时强制更新
      const intervalId = setInterval(forceEnglishButtons, CONFIG.checkInterval);
      
      // 保存清理函数
      window.cleanupBuyButtonFix = function() {
        clearInterval(intervalId);
        observer.disconnect();
        log('已清理购买按钮修复模块');
      };
      
      log('购买按钮修复模块初始化完成');
    }
  }
  
  // 执行初始化
  init();
})(); 