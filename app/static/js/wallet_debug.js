/**
 * wallet_debug.js - 钱包调试脚本
 * 版本: 1.0.0
 * 作用: 监控并记录钱包状态变化和页面交互，辅助排查问题
 */

(function() {
  // 避免重复加载
  if (window.walletDebugInitialized) return;
  window.walletDebugInitialized = true;
  
  // 调试开关
  const DEBUG = true;
  
  // 日志级别
  const LOG_LEVELS = {
    INFO: { label: 'INFO', color: '#0066cc' },
    WARN: { label: 'WARN', color: '#cc9900' },
    ERROR: { label: 'ERROR', color: '#cc0000' },
    DEBUG: { label: 'DEBUG', color: '#666666' }
  };
  
  // 全局变量保存
  let walletStateHistory = [];
  let buyButtonStateHistory = [];
  let errorLog = [];
  
  // 日志函数
  function log(level, message, data) {
    if (!DEBUG) return;
    
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp: timestamp,
      level: level.label,
      message: message,
      data: data || null
    };
    
    console.log(
      `%c[钱包调试] ${level.label} ${timestamp}:%c ${message}`, 
      `color: ${level.color}; font-weight: bold;`, 
      'color: inherit;', 
      data || ''
    );
    
    // 特定日志处理
    if (level === LOG_LEVELS.ERROR) {
      errorLog.push(logEntry);
    }
    
    return logEntry;
  }
  
  // 导出日志工具到全局
  window.walletDebug = {
    log: (message, data) => log(LOG_LEVELS.INFO, message, data),
    warn: (message, data) => log(LOG_LEVELS.WARN, message, data),
    error: (message, data) => log(LOG_LEVELS.ERROR, message, data),
    debug: (message, data) => log(LOG_LEVELS.DEBUG, message, data),
    getErrorLog: () => [...errorLog],
    getWalletStateHistory: () => [...walletStateHistory],
    getBuyButtonStateHistory: () => [...buyButtonStateHistory],
    clearLogs: () => {
      walletStateHistory = [];
      buyButtonStateHistory = [];
      errorLog = [];
      log(LOG_LEVELS.INFO, '日志已清除');
    }
  };
  
  // 初始化时记录当前页面URL和钱包状态
  walletDebug.log('调试脚本已加载', { 
    url: window.location.href,
    pathname: window.location.pathname,
    referrer: document.referrer,
    userAgent: navigator.userAgent
  });
  
  // 监控walletState变化
  function monitorWalletState() {
    let lastWalletState = null;
    
    // 检查初始钱包状态
    if (window.walletState) {
      const initialState = { 
        isConnected: window.walletState.isConnected,
        address: window.walletState.address,
        walletType: window.walletState.walletType,
        timestamp: new Date().toISOString(),
        source: '初始状态'
      };
      walletStateHistory.push(initialState);
      walletDebug.log('初始钱包状态', initialState);
      lastWalletState = initialState;
    } else {
      walletDebug.warn('window.walletState未初始化');
    }
    
    // 创建代理以监控walletState变化
    const monitorObject = window.walletState || {};
    
    if (!window.walletState) {
      window.walletState = {};
      walletDebug.warn('创建了临时walletState对象');
    }
    
    // 监听localStorage变化
    window.addEventListener('storage', function(e) {
      if (e.key === 'walletState') {
        try {
          const newState = JSON.parse(e.newValue);
          walletDebug.log('localStorage中的walletState已更新', newState);
          checkWalletStateChange(newState, 'localStorage事件');
        } catch (err) {
          walletDebug.error('解析localStorage中的walletState失败', err);
        }
      }
    });
    
    // 定期检查钱包状态
    setInterval(function() {
      if (window.walletState) {
        const currentState = { 
          isConnected: window.walletState.isConnected,
          address: window.walletState.address,
          walletType: window.walletState.walletType,
          timestamp: new Date().toISOString(),
          source: '定时检查'
        };
        
        // 检查是否有变化
        if (lastWalletState && 
            (lastWalletState.isConnected !== currentState.isConnected || 
             lastWalletState.address !== currentState.address ||
             lastWalletState.walletType !== currentState.walletType)) {
          walletStateHistory.push(currentState);
          walletDebug.log('钱包状态已变化', {
            from: lastWalletState,
            to: currentState
          });
          lastWalletState = currentState;
        }
      }
    }, 3000);
    
    // 辅助函数：检查钱包状态变化
    function checkWalletStateChange(newState, source) {
      if (!newState) return;
      
      const currentState = { 
        isConnected: newState.isConnected,
        address: newState.address,
        walletType: newState.walletType,
        timestamp: new Date().toISOString(),
        source: source
      };
      
      if (lastWalletState && 
          (lastWalletState.isConnected !== currentState.isConnected || 
           lastWalletState.address !== currentState.address ||
           lastWalletState.walletType !== currentState.walletType)) {
        walletStateHistory.push(currentState);
        walletDebug.log('钱包状态已变化', {
          from: lastWalletState,
          to: currentState
        });
        lastWalletState = currentState;
      }
    }
  }
  
  // 监控购买按钮状态
  function monitorBuyButton() {
    // 在DOM加载完成后执行
    function checkBuyButtons() {
      // 扩展选择器，确保能找到所有可能的购买按钮
      const buyButtons = document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"], #buyButton, button:contains("Buy"), a:contains("Buy"), .btn-buy, .purchase-button');
      
      if (buyButtons.length > 0) {
        walletDebug.log(`找到${buyButtons.length}个购买按钮`);
        
        buyButtons.forEach((btn, index) => {
          const buttonState = {
            index: index,
            id: btn.id || '无ID',
            text: btn.textContent.trim(),
            isDisabled: btn.disabled,
            classes: Array.from(btn.classList),
            timestamp: new Date().toISOString()
          };
          
          buyButtonStateHistory.push(buttonState);
          walletDebug.debug(`购买按钮 #${index} 状态`, buttonState);
          
          // 监视按钮变化
          const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
              if (mutation.type === 'attributes' || mutation.type === 'childList') {
                const newState = {
                  index: index,
                  id: btn.id || '无ID',
                  text: btn.textContent.trim(),
                  isDisabled: btn.disabled,
                  classes: Array.from(btn.classList),
                  mutation: mutation.type,
                  timestamp: new Date().toISOString()
                };
                
                buyButtonStateHistory.push(newState);
                walletDebug.debug(`购买按钮 #${index} 状态变化`, newState);
              }
            });
          });
          
          observer.observe(btn, { 
            attributes: true, 
            childList: true, 
            subtree: true 
          });
        });
      } else {
        walletDebug.warn('未找到购买按钮');
      }
    }
    
    // 初始检查
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', checkBuyButtons);
    } else {
      checkBuyButtons();
    }
    
    // 定期重新检查
    setInterval(checkBuyButtons, 5000);
  }
  
  // 捕获全局错误
  function monitorErrors() {
    // 捕获未处理的Promise错误
    window.addEventListener('unhandledrejection', function(event) {
      walletDebug.error('未处理的Promise错误', {
        reason: event.reason,
        stack: event.reason.stack
      });
    });
    
    // 捕获全局错误
    window.addEventListener('error', function(event) {
      walletDebug.error('全局JS错误', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error
      });
    });
    
    // 捕获控制台错误
    const originalConsoleError = console.error;
    console.error = function() {
      walletDebug.error('控制台错误', Array.from(arguments));
      originalConsoleError.apply(console, arguments);
    };
  }
  
  // 监控API请求
  function monitorApiRequests() {
    // 拦截XMLHttpRequest
    const originalXhrOpen = XMLHttpRequest.prototype.open;
    const originalXhrSend = XMLHttpRequest.prototype.send;
    
    XMLHttpRequest.prototype.open = function(method, url) {
      this._walletDebugData = {
        method: method,
        url: url,
        startTime: new Date().getTime()
      };
      return originalXhrOpen.apply(this, arguments);
    };
    
    XMLHttpRequest.prototype.send = function(data) {
      if (this._walletDebugData) {
        this._walletDebugData.requestData = data;
        
        this.addEventListener('load', function() {
          const duration = new Date().getTime() - this._walletDebugData.startTime;
          const status = this.status;
          let responseData = null;
          
          try {
            responseData = JSON.parse(this.responseText);
          } catch (e) {
            responseData = this.responseText;
          }
          
          // 只记录API请求
          if (this._walletDebugData.url.includes('/api/')) {
            walletDebug.log('API请求完成', {
              ...this._walletDebugData,
              status: status,
              duration: duration + 'ms',
              response: responseData
            });
            
            // 记录错误响应
            if (status >= 400) {
              walletDebug.error('API请求失败', {
                ...this._walletDebugData,
                status: status,
                duration: duration + 'ms',
                response: responseData
              });
            }
          }
        });
        
        this.addEventListener('error', function() {
          const duration = new Date().getTime() - this._walletDebugData.startTime;
          
          walletDebug.error('API请求网络错误', {
            ...this._walletDebugData,
            duration: duration + 'ms'
          });
        });
        
        this.addEventListener('timeout', function() {
          const duration = new Date().getTime() - this._walletDebugData.startTime;
          
          walletDebug.error('API请求超时', {
            ...this._walletDebugData,
            duration: duration + 'ms'
          });
        });
      }
      
      return originalXhrSend.apply(this, arguments);
    };
    
    // 拦截Fetch API
    const originalFetch = window.fetch;
    window.fetch = function(input, init) {
      const startTime = new Date().getTime();
      const url = (typeof input === 'string') ? input : input.url;
      const method = (init && init.method) ? init.method : (input.method || 'GET');
      const requestData = (init && init.body) ? init.body : null;
      
      // 记录API请求
      if (url.includes('/api/')) {
        walletDebug.debug('开始Fetch API请求', {
          url: url,
          method: method,
          requestData: requestData
        });
      }
      
      return originalFetch.apply(this, arguments)
        .then(response => {
          const duration = new Date().getTime() - startTime;
          const status = response.status;
          
          // 只记录API请求
          if (url.includes('/api/')) {
            // 克隆响应以不影响原始处理
            const clonedResponse = response.clone();
            
            clonedResponse.text().then(text => {
              let responseData = text;
              try {
                if (text) {
                  responseData = JSON.parse(text);
                }
              } catch (e) {
                // 如果解析失败，保持原始文本
              }
              
              walletDebug.log('Fetch API请求完成', {
                url: url,
                method: method,
                status: status,
                duration: duration + 'ms',
                response: responseData
              });
              
              // 记录错误响应
              if (status >= 400) {
                walletDebug.error('Fetch API请求失败', {
                  url: url,
                  method: method,
                  status: status,
                  duration: duration + 'ms',
                  response: responseData
                });
              }
            });
          }
          
          return response;
        })
        .catch(error => {
          const duration = new Date().getTime() - startTime;
          
          // 只记录API请求
          if (url.includes('/api/')) {
            walletDebug.error('Fetch API请求错误', {
              url: url,
              method: method,
              duration: duration + 'ms',
              error: error.toString()
            });
          }
          
          throw error;
        });
    };
  }
  
  // 在控制台添加调试命令
  function addConsoleCommands() {
    window.showWalletDebug = function() {
      console.log('%c===== 钱包调试信息 =====', 'font-weight: bold; font-size: 14px;');
      console.log('钱包状态历史:', walletStateHistory);
      console.log('购买按钮状态历史:', buyButtonStateHistory);
      console.log('错误日志:', errorLog);
      
      if (window.walletState) {
        console.log('当前钱包状态:', {
          isConnected: window.walletState.isConnected,
          address: window.walletState.address,
          walletType: window.walletState.walletType
        });
      } else {
        console.log('当前钱包状态: 未初始化');
      }
      
      return '调试信息已在控制台显示';
    };
  }
  
  // 初始化所有监控
  function init() {
    walletDebug.log('初始化钱包调试模块');
    monitorWalletState();
    monitorBuyButton();
    monitorErrors();
    monitorApiRequests();
    addConsoleCommands();
    walletDebug.log('钱包调试模块初始化完成');
  }
  
  // 启动调试
  init();
})(); 