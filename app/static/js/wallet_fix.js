/**
 * wallet_fix.js - 钱包连接修复脚本
 * 版本: 1.1.3
 * 作用: 修复钱包连接状态同步和UI更新问题
 */

(function() {
  // 避免重复加载
  if (window.walletFixInitialized) return;
  window.walletFixInitialized = true;
  
  // 配置和常量
  const CONFIG = {
    debug: false, // 关闭调试日志
    buttonCheckInterval: 1000,
    walletCheckInterval: 2000,
    edgeWalletCheckInterval: 5000, // Edge浏览器使用更长的间隔
    i18n: {
      'en': {
        'buy': 'Buy',
        'connect_wallet': 'Connect Wallet',
        'insufficient_balance': 'Insufficient Balance',
        'loading': 'Loading...'
      },
      'zh': {
        'buy': 'Buy',
        'connect_wallet': '连接钱包',
        'insufficient_balance': '余额不足',
        'loading': '加载中...'
      }
    }
  };
  
  // 当前语言环境
  const currentLang = document.documentElement.lang || 'en';
  
  // 检测是否为Edge浏览器
  const isEdgeBrowser = () => {
    return navigator.userAgent.indexOf("Edg/") > -1 || 
           navigator.userAgent.indexOf("Edge/") > -1;
  };
  
  // 日志函数
  function log(message, data) {
    if (CONFIG.debug) {
      console.log(`[钱包修复] ${message}`, data || '');
    }
  }
  
  // 完全禁用页面自动刷新行为（仅限Edge浏览器）
  function disableEdgePageRefresh() {
    if (!isEdgeBrowser()) return; // 仅适用于Edge浏览器
    
    try {
      // 1. 保存原始的history方法
      const originalPushState = history.pushState;
      const originalReplaceState = history.replaceState;
      
      // 重写history方法，防止页面调用history.go/back等方法
      history.pushState = function() {
        log('Edge浏览器: 拦截history.pushState调用');
        const url = arguments[2];
        if (url && url !== window.location.href) {
          log('Edge浏览器: 允许正常跳转', url);
          return originalPushState.apply(this, arguments);
        }
        // 拦截可能导致刷新的调用
        return undefined;
      };
      
      history.replaceState = function() {
        log('Edge浏览器: 拦截history.replaceState调用');
        const url = arguments[2];
        if (url && url !== window.location.href) {
          log('Edge浏览器: 允许正常跳转', url);
          return originalReplaceState.apply(this, arguments);
        }
        // 拦截可能导致刷新的调用
        return undefined;
      };
      
      // 2. 阻止页面刷新尝试
      window.onbeforeunload = function(e) {
        const target = e.target.activeElement;
        // 仅阻止非用户意图的刷新
        if (!target || !['A', 'BUTTON', 'INPUT'].includes(target.tagName)) {
          log('Edge浏览器: 阻止非用户意图的页面刷新');
          e.preventDefault();
          e.stopPropagation();
          return false;
        }
      };
      
      // 3. 阻止location.reload()调用
      const originalWindowReload = window.location.reload;
      window.location.reload = function() {
        log('Edge浏览器: 拦截location.reload()调用');
        // 完全阻止自动刷新
        return undefined;
      };
      
      log('Edge浏览器: 页面自动刷新保护已启用');
    } catch (err) {
      console.error('启用Edge刷新保护失败:', err);
    }
  }
  
  // 为Edge浏览器彻底禁用visibilitychange事件
  function disableEdgeVisibilityChange() {
    if (!isEdgeBrowser()) return; // 仅适用于Edge浏览器
    
    try {
      log('Edge浏览器: 正在禁用visibilitychange事件');
      
      // 1. 保存原始的addEventListener和removeEventListener方法
      const originalAddEventListener = document.addEventListener;
      const originalRemoveEventListener = document.removeEventListener;
      
      // 2. 重写addEventListener方法，彻底阻止visibilitychange事件注册
      document.addEventListener = function(type, listener, options) {
        if (type === 'visibilitychange') {
          log('Edge浏览器: 阻止添加visibilitychange事件监听器');
          // 完全阻止注册，不保留监听器引用
          return undefined;
        }
        
        // 其他事件正常添加
        return originalAddEventListener.call(this, type, listener, options);
      };
      
      // 3. 重写removeEventListener方法
      document.removeEventListener = function(type, listener, options) {
        if (type === 'visibilitychange') {
          log('Edge浏览器: 移除visibilitychange事件监听器(已禁用)');
          return undefined;
        }
        
        // 其他事件正常移除
        return originalRemoveEventListener.call(this, type, listener, options);
      };
      
      // 4. 尝试定义一个不可修改的visibilityState属性
      try {
        // 首先删除现有属性
        delete document.visibilityState;
        
        // 然后定义一个新的不可修改的属性
        Object.defineProperty(document, 'visibilityState', {
          configurable: false,
          enumerable: true,
          get: function() {
            return 'visible'; // 始终返回可见状态，避免触发页面刷新
          }
        });
        
        // 劫持document.hidden属性
        Object.defineProperty(document, 'hidden', {
          configurable: false,
          enumerable: true,
          get: function() {
            return false; // 始终返回非隐藏状态
          }
        });
      } catch (propErr) {
        log('Edge浏览器: 无法重新定义visibilityState属性，尝试使用替代方法', propErr);
        
        // 替代方法: 拦截Document.prototype.visibilityState的getter
        const originalVisibilityStateGetter = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState');
        if (originalVisibilityStateGetter && originalVisibilityStateGetter.get) {
          Object.defineProperty(Document.prototype, 'visibilityState', {
            get: function() {
              return 'visible'; // 始终返回可见状态
            }
          });
        }
      }
      
      // 5. 劫持document对象的dispatchEvent方法，防止手动触发visibilitychange事件
      const originalDispatchEvent = document.dispatchEvent;
      document.dispatchEvent = function(event) {
        if (event.type === 'visibilitychange') {
          log('Edge浏览器: 阻止手动触发visibilitychange事件');
          return true; // 假装事件已成功触发
        }
        return originalDispatchEvent.call(this, event);
      };
      
      log('Edge浏览器: visibilitychange事件已完全禁用');
    } catch (err) {
      console.error('禁用Edge浏览器visibilitychange事件失败:', err);
    }
  }
  
  // 强力修复Edge浏览器问题
  function applyEdgeBrowserFixes() {
    if (!isEdgeBrowser()) return;
    
    log('检测到Edge浏览器，应用全面修复方案');
    
    // 1. 禁用visibilitychange事件
    disableEdgeVisibilityChange();
    
    // 2. 禁用页面自动刷新行为
    disableEdgePageRefresh();
    
    // 3. 修复wallet.js中的问题代码
    if (window.walletState) {
      // 覆盖checkWalletConnection方法
      if (typeof window.walletState.checkWalletConnection === 'function') {
        const originalCheckWalletConnection = window.walletState.checkWalletConnection;
        let lastCheck = 0;
        
        window.walletState.checkWalletConnection = function() {
          const now = Date.now();
          // 限制检查频率，至少10秒一次
          if (now - lastCheck < 10000) {
            log('Edge浏览器: 忽略频繁的钱包检查请求');
            return Promise.resolve(false);
          }
          
          lastCheck = now;
          return originalCheckWalletConnection.apply(this, arguments)
            .catch(err => {
              log('Edge浏览器: 静默处理钱包检查错误', err);
              return false;
            });
        };
        
        log('Edge浏览器: 已增强钱包状态检查方法');
      }
      
      // 禁用可能导致页面刷新的方法
      const methodsToDisable = ['handleStorageChange', 'checkWalletConsistency'];
      
      methodsToDisable.forEach(methodName => {
        if (typeof window.walletState[methodName] === 'function') {
          const originalMethod = window.walletState[methodName];
          window.walletState[methodName] = function() {
            log(`Edge浏览器: 禁用可能导致刷新的方法 ${methodName}`);
            return false; // 返回假值防止进一步处理
          };
          log(`Edge浏览器: 已禁用 ${methodName} 方法`);
        }
      });
    }
    
    log('Edge浏览器: 全面修复方案已应用');
  }
  
  // 检查并修复钱包状态
  function ensureWalletState() {
    if (!window.walletState) {
      log('创建缺失的walletState对象');
      window.walletState = {
        isConnected: false,
        address: null,
        walletType: null,
        balance: null,
        
        // 基本方法实现
        connect: async function(walletType) {
          log(`尝试连接钱包类型: ${walletType}`);
          try {
            if (walletType === 'metamask' && window.ethereum) {
              const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
              if (accounts && accounts.length > 0) {
                this.isConnected = true;
                this.address = accounts[0];
                this.walletType = walletType;
                this.saveState();
                this.dispatchEvent('connected');
                return true;
              }
            } else if (walletType === 'solana' && window.solana) {
              try {
                const response = await window.solana.connect();
                if (response.publicKey) {
                  this.isConnected = true;
                  this.address = response.publicKey.toString();
                  this.walletType = walletType;
                  this.saveState();
                  this.dispatchEvent('connected');
                  return true;
                }
              } catch (err) {
                log('Solana钱包连接错误', err);
              }
            }
            return false;
          } catch (err) {
            log('钱包连接错误', err);
            return false;
          }
        },
        
        disconnect: function() {
          this.isConnected = false;
          this.address = null;
          this.walletType = null;
          this.balance = null;
          this.saveState();
          this.dispatchEvent('disconnected');
        },
        
        saveState: function() {
          try {
            localStorage.setItem('walletAddress', this.address || '');
            localStorage.setItem('walletType', this.walletType || '');
            
            // 兼容新旧存储方式
            const stateToSave = {
              isConnected: this.isConnected,
              address: this.address,
              walletType: this.walletType
            };
            localStorage.setItem('walletState', JSON.stringify(stateToSave));
          } catch (e) {
            log('保存钱包状态失败', e);
          }
        },
        
        loadState: function() {
          try {
            // 尝试从localStorage加载状态
            const address = localStorage.getItem('walletAddress');
            const walletType = localStorage.getItem('walletType');
            
            // 检查新版本存储
            const savedState = localStorage.getItem('walletState');
            if (savedState) {
              try {
                const parsedState = JSON.parse(savedState);
                if (parsedState && typeof parsedState === 'object') {
                  this.isConnected = !!parsedState.isConnected;
                  this.address = parsedState.address || null;
                  this.walletType = parsedState.walletType || null;
                  return;
                }
              } catch (e) {
                log('解析walletState失败', e);
              }
            }
            
            // 回退到旧版本存储
            if (address && walletType) {
              this.address = address;
              this.walletType = walletType;
              this.isConnected = true;
            } else {
              this.isConnected = false;
              this.address = null;
              this.walletType = null;
            }
          } catch (e) {
            log('加载钱包状态失败', e);
            this.isConnected = false;
            this.address = null;
            this.walletType = null;
          }
        },
        
        dispatchEvent: function(eventName, detail) {
          const event = new CustomEvent('wallet' + eventName.charAt(0).toUpperCase() + eventName.slice(1), {
            detail: detail || {
              address: this.address,
              walletType: this.walletType
            },
            bubbles: true
          });
          document.dispatchEvent(event);
        },
        
        getAddress: function() {
          return this.address;
        },
        
        getWalletType: function() {
          return this.walletType;
        },
        
        isWalletConnected: function() {
          return this.isConnected && !!this.address;
        }
      };
      
      // 初始载入状态
      window.walletState.loadState();
      
      // 添加以太坊事件监听
      if (window.ethereum) {
        window.ethereum.on('accountsChanged', function(accounts) {
          if (accounts.length === 0) {
            window.walletState.disconnect();
          } else if (window.walletState.walletType === 'metamask') {
            window.walletState.address = accounts[0];
            window.walletState.isConnected = true;
            window.walletState.saveState();
            window.walletState.dispatchEvent('changed');
          }
        });
      }
      
      // 添加Solana事件监听
      if (window.solana) {
        window.solana.on('disconnect', function() {
          if (window.walletState.walletType === 'solana') {
            window.walletState.disconnect();
          }
        });
      }
    } else {
      // 确保所有必要的方法存在
      const requiredMethods = ['connect', 'disconnect', 'getAddress', 'isWalletConnected'];
      
      requiredMethods.forEach(method => {
        if (typeof window.walletState[method] !== 'function') {
          log(`为缺失的方法创建空实现: ${method}`);
          
          // 创建空方法
          window.walletState[method] = function() {
            log(`调用了未实现的方法: ${method}`);
            return method === 'isWalletConnected' ? false : null;
          };
        }
      });
      
      // 确保保存和加载方法存在
      if (typeof window.walletState.saveState !== 'function') {
        window.walletState.saveState = function() {
          try {
            localStorage.setItem('walletAddress', this.address || '');
            localStorage.setItem('walletType', this.walletType || '');
            
            const stateToSave = {
              isConnected: this.isConnected,
              address: this.address,
              walletType: this.walletType
            };
            localStorage.setItem('walletState', JSON.stringify(stateToSave));
          } catch (e) {
            log('保存钱包状态失败', e);
          }
        };
      }
      
      if (typeof window.walletState.loadState !== 'function') {
        window.walletState.loadState = function() {
          try {
            const address = localStorage.getItem('walletAddress');
            const walletType = localStorage.getItem('walletType');
            
            const savedState = localStorage.getItem('walletState');
            if (savedState) {
              try {
                const parsedState = JSON.parse(savedState);
                if (parsedState && typeof parsedState === 'object') {
                  this.isConnected = !!parsedState.isConnected;
                  this.address = parsedState.address || null;
                  this.walletType = parsedState.walletType || null;
                  return;
                }
              } catch (e) {
                log('解析walletState失败', e);
              }
            }
            
            if (address && walletType) {
              this.address = address;
              this.walletType = walletType;
              this.isConnected = true;
            } else {
              this.isConnected = false;
              this.address = null;
              this.walletType = null;
            }
          } catch (e) {
            log('加载钱包状态失败', e);
          }
        };
        
        // 立即加载状态
        window.walletState.loadState();
      }
    }
    
    return window.walletState;
  }
  
  // 修复移动端钱包连接问题
  function fixMobileWalletConnection() {
    if (!window.wallet || typeof window.wallet.isMobile !== 'function' || !window.wallet.isMobile()) {
      return; // 不是移动设备，不需要修复
    }

    log('初始化移动端钱包连接修复');

    // 增强从钱包APP返回后的连接处理
    window.addEventListener('visibilitychange', async function() {
      if (document.visibilityState === 'visible') {
        log('页面变为可见，检查是否从钱包APP返回');
        
        // 检查是否有待处理的钱包连接
        const pendingWalletType = localStorage.getItem('pendingWalletType');
        const pendingWalletConnection = localStorage.getItem('pendingWalletConnection');
        const pendingWalletTimestamp = localStorage.getItem('pendingWalletTimestamp');
        
        if (pendingWalletType && pendingWalletConnection === 'true') {
          const timestamp = parseInt(pendingWalletTimestamp, 10);
          const now = Date.now();
          const timeDiff = now - timestamp;
          
          if (timeDiff <= 5 * 60 * 1000) { // 5分钟内有效
            log(`检测到从${pendingWalletType}钱包APP返回，尝试主动连接`);
            
            // 延迟一点时间执行，确保钱包APP有足够时间初始化
            setTimeout(async () => {
              try {
                // 检查特定钱包类型
                if (pendingWalletType.toLowerCase() === 'phantom') {
                  // 检查Phantom钱包是否已在页面初始化
                  if (window.solana && window.solana.isPhantom) {
                    log('Phantom钱包已初始化，尝试连接');
                    
                    try {
                      // 尝试连接已授权的钱包（更轻量级的调用）
                      const response = await window.solana.connect({ onlyIfTrusted: true }).catch(() => null);
                      
                      if (response && response.publicKey) {
                        log('成功连接到已授权的Phantom钱包', response.publicKey.toString());
                        
                        // 如果wallet对象存在，更新钱包状态
                        if (window.wallet && typeof window.wallet.afterSuccessfulConnection === 'function') {
                          window.wallet.afterSuccessfulConnection(
                            response.publicKey.toString(), 
                            'phantom', 
                            window.solana
                          );
                        }
                      } else {
                        // 如果onlyIfTrusted失败，尝试常规连接
                        log('尝试标准Phantom连接');
                        const fullResponse = await window.solana.connect().catch(e => {
                          log('标准连接出错', e);
                          return null;
                        });
                        
                        if (fullResponse && fullResponse.publicKey) {
                          log('成功连接到Phantom钱包', fullResponse.publicKey.toString());
                          
                          if (window.wallet && typeof window.wallet.afterSuccessfulConnection === 'function') {
                            window.wallet.afterSuccessfulConnection(
                              fullResponse.publicKey.toString(), 
                              'phantom', 
                              window.solana
                            );
                          }
                        } else {
                          // 可能是Phantom App还没完全初始化，再等一会重试
                          setTimeout(() => {
                            log('再次尝试连接Phantom钱包');
                            window.solana.connect().then(lastTry => {
                              if (lastTry && lastTry.publicKey) {
                                log('最后尝试成功连接到Phantom', lastTry.publicKey.toString());
                                if (window.wallet && typeof window.wallet.afterSuccessfulConnection === 'function') {
                                  window.wallet.afterSuccessfulConnection(
                                    lastTry.publicKey.toString(), 
                                    'phantom', 
                                    window.solana
                                  );
                                }
                              }
                            }).catch(finalError => {
                              log('最终连接尝试失败', finalError);
                            });
                          }, 1500);
                        }
                      }
                    } catch (error) {
                      log('从APP返回后连接Phantom钱包失败', error);
                    }
                  } else {
                    log('Phantom钱包对象未找到，无法完成连接');
                  }
                }
                // 可以添加其他钱包类型的处理...
              } finally {
                // 清除钱包连接尝试状态
                localStorage.removeItem('pendingWalletType');
                localStorage.removeItem('pendingWalletConnection');
                localStorage.removeItem('pendingWalletTimestamp');
              }
            }, 1000);
          } else {
            // 时间戳过期，清除状态
            localStorage.removeItem('pendingWalletType');
            localStorage.removeItem('pendingWalletConnection');
            localStorage.removeItem('pendingWalletTimestamp');
          }
        }
      }
    });
    
    // 拦截和增强原始钱包连接方法
    if (window.wallet && typeof window.wallet.connect === 'function') {
      const originalConnect = window.wallet.connect;
      
      window.wallet.connect = async function(walletType) {
        // 如果不是移动设备或者已经在钱包浏览器中，使用原始方法
        if (!window.wallet.isMobile() || 
            (walletType === 'phantom' && window.solana) || 
            ((walletType === 'metamask' || walletType === 'ethereum') && window.ethereum)) {
          return originalConnect.apply(this, arguments);
        }
        
        log(`增强的移动端钱包连接: ${walletType}`);
        
        // 对Phantom钱包的特殊处理
        if (walletType.toLowerCase() === 'phantom') {
          // 检测iOS设备
          const isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
          
          // 构建更可靠的Universal Link或Deep Link
          const currentUrl = encodeURIComponent(window.location.href);
          let deepLink;
          
          if (isIOS) {
            // iOS设备使用Universal Link
            deepLink = `https://phantom.app/ul/browse/${currentUrl}`;
            log('使用iOS的Universal Link:', deepLink);
          } else {
            // Android设备使用特定的协议链接
            deepLink = `phantom://browse/${currentUrl}`;
            // 备用链接，如果上面的不工作
            const backupLink = `https://phantom.app/ul/browse/${currentUrl}`;
            log('使用Android的Deep Link:', deepLink);
            log('备用链接:', backupLink);
          }
          
          // 保存连接尝试状态
          localStorage.setItem('pendingWalletType', walletType);
          localStorage.setItem('pendingWalletConnection', 'true');
          localStorage.setItem('pendingWalletTimestamp', Date.now().toString());
          localStorage.setItem('lastConnectionAttemptUrl', window.location.href);
          
          log('跳转到Phantom钱包APP', deepLink);
          
          // 对于iOS，需要一个小延迟来确保localStorage写入完成
          if (isIOS) {
            setTimeout(() => {
              window.location.href = deepLink;
            }, 100);
          } else {
            window.location.href = deepLink;
          }
          return true;
        }
        
        // 其他钱包类型使用原始方法
        return originalConnect.apply(this, arguments);
      };
      
      log('已增强原始钱包连接方法');
    }
  }
  
  // 修复购买按钮状态
  function fixBuyButtons() {
    const buyButtons = document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"]');
    if (!buyButtons || buyButtons.length === 0) return;
    
    log(`发现${buyButtons.length}个购买按钮`);
    
    buyButtons.forEach((button, index) => {
      if (button._fixApplied) return;
      button._fixApplied = true;
      
      log(`正在修复购买按钮 #${index}: ${button.textContent.trim() || '(空文本)'}`);
      
      // 保存原始状态
      button._originalText = button.textContent.trim();
      button._originalDisabled = button.disabled;
      
      // 更新按钮状态
      updateBuyButton(button);
      
      // 监听点击事件
      button.addEventListener('click', function(e) {
        if (!window.walletState || !window.walletState.isWalletConnected()) {
          e.preventDefault();
          e.stopPropagation();
          
          log('未连接钱包，显示连接钱包对话框');
          if (typeof window.openWalletSelector === 'function') {
            window.openWalletSelector();
          } else if (typeof window.walletState.connect === 'function') {
            // 默认尝试连接Metamask
            window.walletState.connect('metamask');
          }
          return false;
        }
      });
    });
  }
  
  // 监控钱包状态
  function monitorWalletState() {
    let lastWalletStatus = null;
    let isFirstCheck = true;  // 添加首次检查标记
    let lastUpdateTime = 0;   // 添加上次更新时间戳
    const isEdge = isEdgeBrowser();
    
    // 根据浏览器类型选择检查间隔
    const checkInterval = isEdge ? CONFIG.edgeWalletCheckInterval : CONFIG.walletCheckInterval;
    
    if (isEdge) {
      log('检测到Edge浏览器，使用更长的钱包状态检查间隔');
    }
    
    // 初始化时立即记录当前状态，但不触发事件
    const initialWalletState = ensureWalletState();
    lastWalletStatus = {
      isConnected: initialWalletState.isConnected,
      address: initialWalletState.address,
      walletType: initialWalletState.walletType
    };
    log('初始钱包状态已记录', lastWalletStatus);
    
    const intervalId = setInterval(function() {
      // 对于Edge浏览器，添加更严格的时间限制
      const now = Date.now();
      if (isEdge && now - lastUpdateTime < 5000) {
        // Edge浏览器中，如果距离上次更新少于5秒，则跳过此次检查
        return;
      }
      
      // 确保钱包状态对象存在
      const walletState = ensureWalletState();
      
      // 获取当前状态
      const currentStatus = {
        isConnected: walletState.isConnected,
        address: walletState.address,
        walletType: walletState.walletType
      };
      
      // 首次检查只存储状态，不触发事件
      if (isFirstCheck) {
        lastWalletStatus = {...currentStatus};
        isFirstCheck = false;
        log('首次钱包状态检查完成，不触发事件', currentStatus);
        return;
      }
      
      // 添加深度比较，防止对象引用变化但内容相同导致的假状态变化
      function deepEqual(obj1, obj2) {
        // 处理简单类型
        if (obj1 === obj2) return true;
        
        // 处理null或undefined
        if (obj1 == null || obj2 == null) return obj1 === obj2;
        
        // 处理不同类型
        if (typeof obj1 !== typeof obj2) return false;
        
        // 处理对象类型
        if (typeof obj1 === 'object') {
          const keys1 = Object.keys(obj1);
          const keys2 = Object.keys(obj2);
          
          if (keys1.length !== keys2.length) return false;
          
          return keys1.every(key => deepEqual(obj1[key], obj2[key]));
        }
        
        // 其他情况（基本类型）
        return obj1 === obj2;
      }
      
      // 在Edge浏览器中使用更严格的比较
      let hasChanged = false;
      
      if (isEdge) {
        // Edge浏览器中，只有当状态真正发生重大变化时才更新
        hasChanged = (
          (lastWalletStatus.isConnected !== currentStatus.isConnected) || // 连接状态改变
          (lastWalletStatus.address !== currentStatus.address && 
           currentStatus.address !== null && 
           currentStatus.address !== "") || // 地址改变且有效
          (lastWalletStatus.walletType !== currentStatus.walletType && 
           currentStatus.walletType !== null && 
           currentStatus.walletType !== "") // 钱包类型有效且发生改变
        );
      } else {
        // 其他浏览器使用标准比较，但避免无意义的null -> null或空字符串变化
        hasChanged = (
          lastWalletStatus.isConnected !== currentStatus.isConnected ||
          (lastWalletStatus.address !== currentStatus.address && 
           (currentStatus.address !== null && currentStatus.address !== "")) ||
          (lastWalletStatus.walletType !== currentStatus.walletType && 
           (currentStatus.walletType !== null && currentStatus.walletType !== ""))
        );
      }
      
      // 如果钱包已连接但地址相同，不触发不必要的更新
      if (hasChanged && lastWalletStatus.isConnected && currentStatus.isConnected &&
          lastWalletStatus.address === currentStatus.address) {
        // 如果只是walletType变化但两者都有效，则不触发完整更新
        if (lastWalletStatus.walletType && currentStatus.walletType && 
            lastWalletStatus.walletType !== currentStatus.walletType) {
          log('钱包类型变化但地址相同，跳过完整更新', {
            oldType: lastWalletStatus.walletType,
            newType: currentStatus.walletType
          });
          // 更新类型但不触发完整更新流程
          lastWalletStatus.walletType = currentStatus.walletType;
          hasChanged = false;
        }
      }
      
      if (hasChanged) {
        log('钱包状态已变化', {
          before: lastWalletStatus,
          after: currentStatus
        });
        
        // 记录更新时间
        lastUpdateTime = now;
        
        // 更新所有购买按钮
        document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"], #buy-button').forEach(updateBuyButton);
        
        // 避免不必要的断连再连接循环
        if (lastWalletStatus.isConnected === false && currentStatus.isConnected === true) {
          // 仅在钱包从断开到连接时触发walletConnected事件
          const event = new CustomEvent('walletConnected', {
            detail: {
              address: currentStatus.address,
              walletType: currentStatus.walletType
            },
            bubbles: true
          });
          document.dispatchEvent(event);
          log('已触发钱包连接事件', currentStatus);
        } else if (lastWalletStatus.isConnected === true && currentStatus.isConnected === false) {
          // 仅在钱包从连接到断开时触发walletDisconnected事件
          const event = new CustomEvent('walletDisconnected', {
            detail: {
              previousAddress: lastWalletStatus.address,
              previousWalletType: lastWalletStatus.walletType
            },
            bubbles: true
          });
          document.dispatchEvent(event);
          log('已触发钱包断开事件', {previousState: lastWalletStatus});
        }
        
        // 触发通用的钱包状态变化事件
        const stateChangeEvent = new CustomEvent('walletStateChanged', {
          detail: {
            isConnected: currentStatus.isConnected,
            address: currentStatus.address,
            walletType: currentStatus.walletType,
            previousState: {...lastWalletStatus}
          },
          bubbles: true
        });
        document.dispatchEvent(stateChangeEvent);
        
        // 更新上次状态
        lastWalletStatus = {...currentStatus};
      }
    }, checkInterval);
    
    // 特别处理Edge浏览器的visibilitychange事件
    if (isEdge) {
      // 完全禁用visibilitychange事件，防止Edge浏览器的异常行为
      disableEdgeVisibilityChange();
      
      // 为Edge浏览器注册一个更安全的仅一次性visibilitychange处理
      const safeVisibilityHandler = function() {
        log('Edge浏览器: 安全的visibilitychange事件处理');
        // 移除自身，确保只执行一次
        document.removeEventListener('visibilitychange', safeVisibilityHandler);
        
        // 只在页面变为可见时尝试恢复会话
        if (document.visibilityState === 'visible') {
          setTimeout(function() {
            log('Edge浏览器: 页面变为可见，安全地检查钱包状态');
            // 安全地触发一次钱包状态检查
            const walletState = ensureWalletState();
            if (walletState && typeof walletState.checkWalletConnection === 'function') {
              try {
                walletState.checkWalletConnection().catch(() => {});
              } catch (e) {
                // 忽略所有错误
              }
            }
          }, 1000);
        }
      };
      
      // 尝试添加这个安全的处理器
      try {
        document.addEventListener('visibilitychange', safeVisibilityHandler, { once: true });
      } catch (e) {
        log('Edge浏览器: 无法添加安全的visibilitychange处理器', e);
      }
    }
    
    // 返回间隔ID，便于需要时清除
    return intervalId;
  }
  
  // 更新按钮状态
  function updateBuyButton(button) {
    if (!button) return;

    // 检查是否为资产详情页的特定购买按钮
    const isAssetDetailPage = window.location.pathname.includes('/assets/') || 
                              document.querySelector('.asset-detail-page');
    
    // 更精确地检测detail.html页面中的购买按钮
    const isDetailPageBuyButton = (
      (button.id === 'buy-button' && isAssetDetailPage) || // ID匹配且在资产页面
      (button.hasAttribute('data-asset-id') && button.hasAttribute('data-token-price')) || // 具有特定数据属性
      (isAssetDetailPage && button.closest('.trade-card')) // 在资产页内的交易卡片中
    );

    if (isDetailPageBuyButton) {
      // 在资产详情页，由detail.html自己处理按钮文本
      log('检测到资产详情页购买按钮，由页面自身处理');
      return;
    }
    
    // 非资产详情页的按钮，由wallet_fix.js处理
    try {
      const walletState = window.walletState;
      const isConnected = walletState && (
        (typeof walletState.isWalletConnected === 'function' && walletState.isWalletConnected()) ||
        walletState.isConnected || 
        walletState.connected
      );
      
      if (!isConnected) {
        // 钱包未连接状态
        button.disabled = false; // 允许点击，触发钱包连接流程
        
        // 支持多语言
        const lang = document.documentElement.lang || navigator.language || 'en';
        const connectText = (lang.startsWith('zh') ? 
                           CONFIG.i18n.zh.connect_wallet : 
                           CONFIG.i18n.en.connect_wallet);
        
        // 保留按钮原始内容
        if (!button._originalText) {
          button._originalText = button.textContent.trim();
        }
        
        // 设置连接钱包文本
        button.textContent = connectText;
        button.innerHTML = `<i class="fas fa-wallet me-2"></i>${connectText}`;
      } else {
        // 钱包已连接
        button.disabled = false;
        
        // 恢复原始文本
        if (button._originalText) {
          button.textContent = button._originalText;
        } else {
          // 如果没有原始文本记录，使用默认文本
          const lang = document.documentElement.lang || navigator.language || 'en';
          const buyText = (lang.startsWith('zh') ? 
                         CONFIG.i18n.zh.buy : 
                         CONFIG.i18n.en.buy);
          button.textContent = buyText;
          button.innerHTML = `<i class="fas fa-shopping-cart me-2"></i>${buyText}`;
        }
      }
    } catch (error) {
      log('更新按钮状态时出错', error);
    }
  }
  
  // 修复网络请求错误
  function fixApiRequests() {
    const originalFetch = window.fetch;
    
    window.fetch = function(input, init) {
      const url = typeof input === 'string' ? input : input.url;
      
      // 检查并修复API请求
      if (url.includes('/api/')) {
        // 确保请求头包含内容类型
        if (!init) init = {};
        if (!init.headers) init.headers = {};
        
        // 如果是JSON请求，确保设置正确的内容类型
        if (init.body && typeof init.body === 'string' && init.body.startsWith('{')) {
          init.headers['Content-Type'] = 'application/json';
        }
        
        // 检查GET请求的查询参数
        if (url.includes('/api/get_user_assets') && !url.includes('?address=')) {
          const walletState = window.walletState;
          if (walletState && walletState.address) {
            const separator = url.includes('?') ? '&' : '?';
            const newUrl = `${url}${separator}address=${walletState.address}${walletState.walletType ? '&wallet_type=' + walletState.walletType : ''}`;
            log(`修复API请求URL: ${url} -> ${newUrl}`);
            input = newUrl;
          }
        }
        
        // 完全静默处理某些特定API错误，避免在控制台显示404
        const isDividendApi = (
          url.includes('/api/assets/') && url.includes('/dividend_stats') || 
          url.includes('/api/dividend/total/')
        );
        
        // 创建请求拦截处理函数
        return originalFetch.call(this, input, init)
          .then(response => {
            // 即使成功，也尝试改进分红数据，防止loading状态
            if (isDividendApi && response.status === 404) {
              // 返回一个合法的空分红数据结构，而不是404错误
              return new Response(JSON.stringify({
                success: true,
                total_dividends: 0,
                last_dividend: null,
                next_dividend: null,
                message: "暂无分红数据"
              }), {
                status: 200,
                headers: {'Content-Type': 'application/json'}
              });
            }
            return response;
          })
          .catch(error => {
            // 完全静默某些API错误，返回有效的默认响应
            if (isDividendApi) {
              // 对于分红相关的API调用错误，返回空分红数据而不是抛出错误
              return new Response(JSON.stringify({
                success: true,
                total_dividends: 0,
                last_dividend: null,
                next_dividend: null,
                message: "暂无分红数据"
              }), {
                status: 200,
                headers: {'Content-Type': 'application/json'}
              });
            }
            
            // 资产信息API错误处理
            if (url.includes('/api/assets/') && !url.includes('/dividend')) {
              console.debug(`资产API调用失败: ${url}`);
              return new Response(JSON.stringify({success: false, error: "资产信息不存在"}), {
                status: 200,
                headers: {'Content-Type': 'application/json'}
              });
            }
            
            // 其他错误继续抛出
            throw error;
          });
      }
      
      // 对于其他API调用，使用原始fetch
      return originalFetch.call(this, input, init);
    };
  }
  
  // DOM准备好以后再修复按钮
  function onDomReady(callback) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', callback);
    } else {
      callback();
    }
  }
  
  // 主初始化
  function init() {
    log('初始化钱包修复模块');
    
    // 首先应用Edge浏览器修复
    if (isEdgeBrowser()) {
      applyEdgeBrowserFixes();
    }
    
    // 确保钱包状态
    ensureWalletState();
    
    // 定义全局函数来统一更新所有购买按钮
    window.updateAllBuyButtons = function() {
      if (CONFIG.debug) {
        console.log('[钱包修复] 全局更新所有购买按钮');
      }
      try {
        const isAssetDetailPage = window.location.pathname.includes('/assets/') || 
                                 document.querySelector('.asset-detail-page') ||
                                 document.getElementById('asset-detail-container') ||
                                 document.getElementById('buy-button');

        const validSelectors = [
          '.buy-btn', '.buy-button', '[data-action="buy"]',
          '#buyButton', '.btn-buy', '.purchase-button',
          '[class*="buy"]', '.buy',
          '.detail-buy-button', '[data-asset-action="buy"]', '.asset-buy-button'
        ];
        
        let allButtons = [];
        validSelectors.forEach(selector => {
          try {
            const buttons = document.querySelectorAll(selector);
            buttons.forEach(btn => {
              // 如果是详情页的特定购买按钮 (id='buy-button')，则不添加到这里进行文本修改
              if (isAssetDetailPage && btn.id === 'buy-button') {
                return; 
              }
              allButtons.push(btn);
            });
          } catch (err) {}
        });
        
        allButtons = [...new Set(allButtons)];
        
        allButtons.forEach(btn => {
          // 对于非详情页主购买按钮，如果文本是'购买'，则改为'Buy'
          if (btn.textContent.trim() === '购买') {
            btn.textContent = 'Buy';
          }
          // 同时调用 updateBuyButton 来正确设置其状态（如果它不是详情页主按钮）
          if (!isAssetDetailPage || btn.id !== 'buy-button') {
             updateBuyButton(btn);
          }
        });
        return true;
      } catch (e) {
        console.error('更新购买按钮出错:', e);
        return false;
      }
    };
    
    // 初始修复
    onDomReady(function() {
      // 修复购买按钮
      fixBuyButtons();
      
      // 立即运行全局更新函数
      if (window.updateAllBuyButtons) {
        window.updateAllBuyButtons();
      }
      
      // 定期检查购买按钮（可能有动态加载的）
      setInterval(function() {
        fixBuyButtons();
        
        // 每次检查时也运行全局更新
        if (window.updateAllBuyButtons) {
          window.updateAllBuyButtons();
        }
      }, CONFIG.buttonCheckInterval);
    });
    
    // 监控钱包状态
    monitorWalletState();
    
    // 减少控制台错误和警告
    window.addEventListener('error', function(event) {
      // 忽略资源加载错误和部分API请求错误
      if (event.filename && (
          event.filename.includes('/api/assets/') || 
          event.filename.includes('/api/dividend/'))) {
        event.preventDefault();
        return false;
      }
    }, true);
    
    // 修复API请求
    fixApiRequests();
    
    // 修复移动端钱包连接问题
    fixMobileWalletConnection();
    
    log('钱包修复模块初始化完成');
  }
})(); 