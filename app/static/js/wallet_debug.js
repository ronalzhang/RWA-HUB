/**
 * wallet_debug.js - 钱包调试脚本
 * 版本: 1.0.0
 * 作用: 监控并记录钱包状态变化和页面交互，辅助排查问题
 */

(function() {
  // 避免重复加载
  if (window.walletDebugInitialized) return;
  window.walletDebugInitialized = true;
  
  // 配置
  const config = {
    // 调试级别：0=关闭, 1=错误, 2=警告, 3=信息, 4=调试
    logLevel: 1, // 只保留错误日志
    
    // 是否记录钱包状态变化
    trackWalletState: true,
    
    // 是否记录购买按钮状态
    trackBuyButton: false, // 关闭购买按钮状态追踪
    
    // 是否拦截API请求
    interceptApiRequests: true,
    
    // 最大历史记录条数
    maxHistory: 50
  };
  
  // 历史记录
  const walletStateHistory = [];
  const buyButtonStateHistory = [];
  const apiRequestHistory = [];
  
  // 调试工具
  const walletDebug = {
    error: function(message, data) {
      log('ERROR', message, data);
    },
    
    warn: function(message, data) {
      log('WARN', message, data);
    },
    
    log: function(message, data) {
      log('INFO', message, data);
    },
    
    debug: function(message, data) {
      log('DEBUG', message, data);
    },
    
    getWalletStateHistory: function() {
      return walletStateHistory;
    },
    
    getBuyButtonStateHistory: function() {
      return buyButtonStateHistory;
    },
    
    getApiRequestHistory: function() {
      return apiRequestHistory;
    },
    
    clear: function() {
      walletStateHistory.length = 0;
      buyButtonStateHistory.length = 0;
      apiRequestHistory.length = 0;
      console.clear();
    }
  };
  
  // 记录日志
  function log(level, message, data) {
    // 检查日志级别
    const levelMap = { 'ERROR': 1, 'WARN': 2, 'INFO': 3, 'DEBUG': 4 };
    if (!levelMap[level] || levelMap[level] > config.logLevel) {
      return;
    }
    
    // 格式化消息
    const timestamp = new Date().toISOString();
    const formattedMessage = `[钱包调试] ${level} ${timestamp}: ${message}`;
    
    // 输出到控制台
    if (data) {
      console.log(formattedMessage, data);
    } else {
      console.log(formattedMessage);
    }
    
    // 限制历史记录长度
    if (walletStateHistory.length > config.maxHistory) {
      walletStateHistory.shift();
    }
    
    if (buyButtonStateHistory.length > config.maxHistory) {
      buyButtonStateHistory.shift();
    }
    
    if (apiRequestHistory.length > config.maxHistory) {
      apiRequestHistory.shift();
    }
  }
  
  // 监控钱包状态
  function monitorWalletState() {
    // 初始状态
    if (window.walletState) {
      const initialState = { ...window.walletState };
      walletStateHistory.push({
        timestamp: new Date().toISOString(),
        state: initialState,
        source: '初始状态'
      });
      
      walletDebug.log('初始钱包状态', initialState);
    }
    
    // 创建全局发布者
    let originalWalletState = window.walletState ? { ...window.walletState } : null;
    
    // 定义全局的setter函数
    function setupWalletStateProxy() {
      if (window.walletState) {
        if (!window._walletStateProxySet) {
          try {
            // 使用Proxy监控对象变化
            const walletStateHandler = {
              set(target, property, value) {
                target[property] = value;
                
                // 记录变化
                if (JSON.stringify(target) !== JSON.stringify(originalWalletState)) {
                  checkWalletStateChange(target, 'walletState属性变化:' + property);
                  originalWalletState = { ...target };
                }
                
                return true;
              }
            };
            
            // 应用Proxy
            window.walletState = new Proxy(window.walletState, walletStateHandler);
            window._walletStateProxySet = true;
            
            walletDebug.debug('已设置钱包状态代理');
          } catch (e) {
            walletDebug.error('设置钱包状态代理失败', e);
          }
        }
      } else {
        // 如果walletState不存在，创建一个空对象并监控
        window.walletState = new Proxy({
          isConnected: false,
          address: '',
          walletType: '',
          timestamp: new Date().toISOString(),
          source: '创建空walletState'
        }, {
          set(target, property, value) {
            target[property] = value;
            
            // 记录变化
            if (JSON.stringify(target) !== JSON.stringify(originalWalletState)) {
              checkWalletStateChange(target, 'walletState创建并变化:' + property);
              originalWalletState = { ...target };
            }
            
            return true;
          }
        });
        
        window._walletStateProxySet = true;
        walletDebug.log('为缺失的walletState创建了代理对象');
      }
    }
    
    // 检查钱包状态变化
    function checkWalletStateChange(newState, source) {
      if (!originalWalletState) {
        originalWalletState = newState;
        return;
      }
      
      // 避免记录重复状态
      if (JSON.stringify(newState) === JSON.stringify(originalWalletState)) {
        return;
      }
      
      // 记录状态变化
      walletStateHistory.push({
        timestamp: new Date().toISOString(),
        before: originalWalletState ? { ...originalWalletState } : null,
        after: newState ? { ...newState } : null,
        source: source || '未知来源'
      });
      
      walletDebug.debug('钱包状态已变化', {
        before: originalWalletState,
        after: newState,
        source: source
      });
      
      // 更新原始状态
      originalWalletState = { ...newState };
    }
    
    // 设置状态代理
    setupWalletStateProxy();
    
    // 定期检查钱包状态
    setInterval(() => {
      if (window.walletState && !window._walletStateProxySet) {
        setupWalletStateProxy();
      }
    }, 1000);
  }
  
  // 监控购买按钮状态
  function monitorBuyButton() {
    // 在DOM加载完成后执行
    function checkBuyButtons() {
      try {
        // 使用标准CSS选择器
        const buyButtons = document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"], #buyButton, .btn-buy, .purchase-button');
        
        if (buyButtons.length > 0) {
          walletDebug.debug(`找到${buyButtons.length}个购买按钮`);
          
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
          walletDebug.debug('未找到购买按钮');
        }
      } catch (e) {
        walletDebug.error('检查购买按钮时出错', e);
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
            walletDebug.debug('API请求完成', {
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
                responseData = JSON.parse(text);
              } catch (e) {
                // 保持文本格式
              }
              
              walletDebug.debug('Fetch API请求完成', {
                url: url,
                method: method,
                status: status,
                duration: duration + 'ms',
                response: responseData
              });
              
              // 记录到历史
              apiRequestHistory.push({
                timestamp: new Date().toISOString(),
                url: url,
                method: method,
                status: status,
                duration: duration,
                request: requestData,
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
          
          if (url.includes('/api/')) {
            walletDebug.error('Fetch API请求异常', {
              url: url,
              method: method,
              duration: duration + 'ms',
              error: error
            });
            
            // 记录到历史
            apiRequestHistory.push({
              timestamp: new Date().toISOString(),
              url: url,
              method: method,
              status: 'ERROR',
              duration: duration,
              request: requestData,
              error: error.message
            });
          }
          
          throw error;
        });
    };
  }
  
  // 添加控制台命令
  function addConsoleCommands() {
    window.walletDebug = walletDebug;
    
    // 添加控制台命令
    walletDebug.debug('已添加以下控制台命令:');
    walletDebug.debug('window.walletDebug.getWalletStateHistory() - 获取钱包状态历史');
    walletDebug.debug('window.walletDebug.getBuyButtonStateHistory() - 获取购买按钮状态历史');
    walletDebug.debug('window.walletDebug.getApiRequestHistory() - 获取API请求历史');
    walletDebug.debug('window.walletDebug.clear() - 清除历史记录和控制台');
  }
  
  // 初始化
  function init() {
    walletDebug.log('初始化钱包调试模块');
    
    // 监控钱包状态
    if (config.trackWalletState) {
      monitorWalletState();
    }
    
    // 监控购买按钮
    if (config.trackBuyButton) {
      monitorBuyButton();
    }
    
    // 监控错误
    monitorErrors();
    
    // 监控API请求
    if (config.interceptApiRequests) {
      monitorApiRequests();
    }
    
    // 添加控制台命令
    addConsoleCommands();
    
    walletDebug.log('钱包调试模块初始化完成');
  }
  
  // 执行初始化
  init();
})(); 