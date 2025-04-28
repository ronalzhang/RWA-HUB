/**
 * wallet_fix.js - 钱包连接修复脚本
 * 版本: 1.1.1
 * 作用: 修复钱包连接状态同步和UI更新问题
 */

(function() {
  // 避免重复加载
  if (window.walletFixInitialized) return;
  window.walletFixInitialized = true;
  
  // 配置和常量
  const CONFIG = {
    debug: true,
    buttonCheckInterval: 1000,
    walletCheckInterval: 2000,
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
  
  // 日志函数
  function log(message, data) {
    if (!CONFIG.debug) return;
    console.log(`[钱包修复] ${message}`, data || '');
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
                        const fullResponse = await window.solana.connect();
                        
                        if (fullResponse && fullResponse.publicKey) {
                          log('成功连接到Phantom钱包', fullResponse.publicKey.toString());
                          
                          if (window.wallet && typeof window.wallet.afterSuccessfulConnection === 'function') {
                            window.wallet.afterSuccessfulConnection(
                              fullResponse.publicKey.toString(), 
                              'phantom', 
                              window.solana
                            );
                          }
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
          // 构建更可靠的Universal Link
          const currentUrl = encodeURIComponent(window.location.href);
          // 使用最新的Phantom深度链接格式
          const deepLink = `https://phantom.app/ul/browse/${currentUrl}`;
          
          // 保存连接尝试状态
          localStorage.setItem('pendingWalletType', walletType);
          localStorage.setItem('pendingWalletConnection', 'true');
          localStorage.setItem('pendingWalletTimestamp', Date.now().toString());
          localStorage.setItem('lastConnectionAttemptUrl', window.location.href);
          
          log('跳转到Phantom钱包APP', deepLink);
          window.location.href = deepLink;
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
  
  // 更新按钮状态
  function updateBuyButton(button) {
    if (!button) return;
    
    const walletState = window.walletState;
    const i18n = CONFIG.i18n[currentLang] || CONFIG.i18n.en;
    
    if (!walletState || !walletState.isWalletConnected()) {
      // 未连接钱包
      button.textContent = i18n.connect_wallet;
      button.disabled = false;
      button.setAttribute('data-wallet-status', 'disconnected');
    } else if (walletState.balance === null) {
      // 连接了钱包但余额未知
      button.textContent = i18n.loading;
      button.disabled = true;
      button.setAttribute('data-wallet-status', 'loading');
    } else if (typeof button.getAttribute('data-min-balance') === 'string') {
      // 检查最小余额要求
      const minBalance = parseFloat(button.getAttribute('data-min-balance'));
      const currentBalance = parseFloat(walletState.balance);
      
      if (!isNaN(minBalance) && !isNaN(currentBalance) && currentBalance < minBalance) {
        button.textContent = i18n.insufficient_balance;
        button.disabled = true;
        button.setAttribute('data-wallet-status', 'insufficient');
      } else {
        // 始终使用英文"Buy"，确保统一
        button.textContent = 'Buy';
        button.disabled = false;
        button.setAttribute('data-wallet-status', 'ready');
      }
    } else {
      // 默认状态 - 钱包已连接
      // 始终使用英文"Buy"，确保统一
      button.textContent = 'Buy';
      button.disabled = false;
      button.setAttribute('data-wallet-status', 'ready');
    }
  }
  
  // 监控钱包状态
  function monitorWalletState() {
    let lastWalletStatus = null;
    
    setInterval(function() {
      // 确保钱包状态对象存在
      const walletState = ensureWalletState();
      
      // 获取当前状态
      const currentStatus = {
        isConnected: walletState.isConnected,
        address: walletState.address,
        walletType: walletState.walletType
      };
      
      // 检查是否有变化
      const hasChanged = !lastWalletStatus || 
        lastWalletStatus.isConnected !== currentStatus.isConnected ||
        lastWalletStatus.address !== currentStatus.address ||
        lastWalletStatus.walletType !== currentStatus.walletType;
      
      if (hasChanged) {
        log('钱包状态已变化', {
          before: lastWalletStatus,
          after: currentStatus
        });
        
        // 更新所有购买按钮
        document.querySelectorAll('.buy-btn, .buy-button, [data-action="buy"]').forEach(updateBuyButton);
        
        // 触发自定义事件
        const eventName = currentStatus.isConnected ? 'walletConnected' : 'walletDisconnected';
        const event = new CustomEvent(eventName, {
          detail: {
            address: currentStatus.address,
            walletType: currentStatus.walletType
          },
          bubbles: true
        });
        document.dispatchEvent(event);
        
        // 更新上次状态
        lastWalletStatus = {...currentStatus};
      }
    }, CONFIG.walletCheckInterval);
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
      }
      
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
    
    // 确保钱包状态
    ensureWalletState();
    
    // 定义全局函数来统一更新所有购买按钮
    window.updateAllBuyButtons = function() {
      console.log('[钱包修复] 全局更新所有购买按钮为英文"Buy"');
      try {
        // 使用标准有效的选择器
        const validSelectors = [
          '.buy-btn', 
          '.buy-button', 
          '[data-action="buy"]', 
          '#buyButton', 
          '.btn-buy', 
          '.purchase-button', 
          '[class*="buy"]', 
          '.buy',
          '#buy-button',
          '.detail-buy-button',
          '[data-asset-action="buy"]',
          '.asset-buy-button'
        ];
        
        // 分段查询确保安全
        let allButtons = [];
        validSelectors.forEach(selector => {
          try {
            const buttons = document.querySelectorAll(selector);
            buttons.forEach(btn => allButtons.push(btn));
          } catch (err) {
            // 忽略单个选择器错误
          }
        });
        
        // 去重
        allButtons = [...new Set(allButtons)];
        
        // 修改文本
        allButtons.forEach(btn => {
          if (btn.textContent.trim() === '购买') {
            btn.textContent = 'Buy';
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
    
    // 修复API请求
    fixApiRequests();
    
    // 修复移动端钱包连接问题
    fixMobileWalletConnection();
    
    log('钱包修复模块初始化完成');
  }
  
  // 启动修复
  init();
})(); 