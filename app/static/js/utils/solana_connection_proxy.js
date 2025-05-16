/**
 * Solana连接代理
 * 拦截所有对Solana节点的直接连接请求，改为通过服务器API
 * 版本: 1.0.0
 */

// 定义SolanaConnectionProxy类
class SolanaConnectionProxy {
  constructor() {
    this.originalConnection = null;
    this.initialized = false;
    this.apiPrefix = '/api/solana';
  }

  /**
   * 初始化代理
   */
  init() {
    if (this.initialized) return;
    this.initialized = true;

    // 检测Solana Web3.js库是否已加载
    if (this._checkLibraryLoaded()) {
      this._setupProxy();
    } else {
      // 设置MutationObserver以检测库何时加载
      this._setupObserver();
    }

    console.log('[Solana代理] 初始化完成，等待Solana库加载');
  }

  /**
   * 检查Solana Web3.js库是否已加载
   * @private
   */
  _checkLibraryLoaded() {
    return (
      typeof window.solanaWeb3 !== 'undefined' ||
      typeof window.solanaWeb3js !== 'undefined' ||
      (typeof window.solana !== 'undefined' && typeof window.solana.web3 !== 'undefined')
    );
  }

  /**
   * 设置观察器以检测库加载
   * @private
   */
  _setupObserver() {
    // 检查<script>标签加载
    const scriptObserver = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'childList' && mutation.addedNodes.length) {
          for (const node of mutation.addedNodes) {
            if (node.tagName === 'SCRIPT' && 
                (node.src.includes('solana-web3') || node.src.includes('@solana/web3'))) {
              // 脚本已添加，等待加载
              node.addEventListener('load', () => {
                setTimeout(() => {
                  if (this._checkLibraryLoaded()) {
                    this._setupProxy();
                    scriptObserver.disconnect();
                  }
                }, 100);
              });
            }
          }
        }
      }

      // 定期检查全局对象是否已可用
      if (this._checkLibraryLoaded()) {
        this._setupProxy();
        scriptObserver.disconnect();
      }
    });

    scriptObserver.observe(document.documentElement, {
      childList: true,
      subtree: true
    });

    // 备用方案：定期检查
    const checkInterval = setInterval(() => {
      if (this._checkLibraryLoaded()) {
        this._setupProxy();
        clearInterval(checkInterval);
      }
    }, 500);

    // 最多等待10秒
    setTimeout(() => {
      clearInterval(checkInterval);
      scriptObserver.disconnect();
    }, 10000);
  }

  /**
   * 设置代理
   * @private
   */
  _setupProxy() {
    console.log('[Solana代理] 检测到Solana库已加载，设置代理');

    // 确定Solana Web3.js库的位置
    let solanaWeb3 = window.solanaWeb3;
    if (!solanaWeb3) {
      if (window.solanaWeb3js) {
        solanaWeb3 = window.solanaWeb3js;
      } else if (window.solana && window.solana.web3) {
        solanaWeb3 = window.solana.web3;
      } else {
        console.error('[Solana代理] 无法找到Solana Web3.js库');
        return;
      }
    }

    // 存储原始Connection类
    this.originalConnection = solanaWeb3.Connection;

    // 创建代理Connection类
    const self = this;
    solanaWeb3.Connection = function(...args) {
      console.log('[Solana代理] 拦截Connection创建:', args);
      
      // 创建原始Connection实例
      const originalInstance = new self.originalConnection(...args);
      
      // 代理方法
      return self._createConnectionProxy(originalInstance);
    };

    console.log('[Solana代理] 代理设置完成');
  }

  /**
   * 创建Connection实例的代理
   * @private
   */
  _createConnectionProxy(originalInstance) {
    const self = this;
    const proxy = {};

    // 代理所有方法和属性
    for (const prop in originalInstance) {
      if (typeof originalInstance[prop] === 'function') {
        // 代理方法
        proxy[prop] = function(...args) {
          return self._handleMethodCall(originalInstance, prop, args);
        };
      } else {
        // 复制属性
        Object.defineProperty(proxy, prop, {
          get: function() { return originalInstance[prop]; },
          set: function(value) { originalInstance[prop] = value; }
        });
      }
    }

    return proxy;
  }

  /**
   * 处理方法调用
   * @private
   */
  async _handleMethodCall(instance, method, args) {
    console.log(`[Solana代理] 方法调用: ${method}`, args);

    // 特殊处理某些方法
    switch (method) {
      case 'getAccountInfo':
        return this._handleGetAccountInfo(args);
      case 'getSignatureStatus':
      case 'getSignatureStatuses':
        return this._handleGetSignatureStatus(args);
      case 'getLatestBlockhash':
        return this._handleGetLatestBlockhash(args);
      case 'getBalance':
        return this._handleGetBalance(args);
      case 'getTokenAccountBalance':
        return this._handleGetTokenBalance(args);
      case 'getTokenAccountsByOwner':
        return this._handleGetTokenAccounts(args);
      default:
        // 对于其他方法，调用原始方法
        console.log(`[Solana代理] 未拦截的方法: ${method}，使用原始实现`);
        return instance[method].apply(instance, args);
    }
  }

  /**
   * 处理getAccountInfo方法
   * @private
   */
  async _handleGetAccountInfo(args) {
    try {
      const address = args[0].toString();
      console.log(`[Solana代理] 通过API检查账户: ${address}`);

      const response = await fetch(`${this.apiPrefix}/check_account?address=${address}`);
      if (!response.ok) {
        throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || '未知错误');
      }

      // 模拟Solana Connection返回格式
      return {
        context: { slot: 0 },
        value: result.account_info
      };
    } catch (error) {
      console.error('[Solana代理] 获取账户信息失败:', error);
      throw new Error(`failed to get info about account: ${error.message}`);
    }
  }

  /**
   * 处理getSignatureStatus方法
   * @private
   */
  async _handleGetSignatureStatus(args) {
    try {
      const signatures = Array.isArray(args[0]) ? args[0] : [args[0]];
      const options = args[1] || {};
      
      // 使用check_transaction API
      const promises = signatures.map(async (signature) => {
        const response = await fetch(`${this.apiPrefix}/check_transaction?signature=${signature}`);
        if (!response.ok) {
          throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
        }
        
        const result = await response.json();
        if (!result.success) {
          return { context: { slot: 0 }, value: null };
        }
        
        return {
          context: { slot: result.slot || 0 },
          value: {
            confirmationStatus: result.status,
            confirmations: result.confirmations,
            err: result.error,
            slot: result.slot || 0
          }
        };
      });
      
      const results = await Promise.all(promises);
      
      // 如果是getSignatureStatus，返回第一个结果，否则返回数组
      return method === 'getSignatureStatus' ? results[0] : { context: { slot: 0 }, value: results.map(r => r.value) };
    } catch (error) {
      console.error('[Solana代理] 获取交易状态失败:', error);
      throw new Error(`failed to get signature status: ${error.message}`);
    }
  }

  /**
   * 处理getLatestBlockhash方法
   * @private
   */
  async _handleGetLatestBlockhash(args) {
    try {
      const response = await fetch(`${this.apiPrefix}/get_latest_blockhash`);
      if (!response.ok) {
        throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || '未知错误');
      }
      
      return {
        context: { slot: 0 },
        value: {
          blockhash: result.blockhash,
          lastValidBlockHeight: result.lastValidBlockHeight
        }
      };
    } catch (error) {
      console.error('[Solana代理] 获取区块哈希失败:', error);
      throw new Error(`failed to get latest blockhash: ${error.message}`);
    }
  }

  /**
   * 处理getBalance方法
   * @private
   */
  async _handleGetBalance(args) {
    try {
      const address = args[0].toString();
      const response = await fetch(`${this.apiPrefix}/get_balance?address=${address}`);
      if (!response.ok) {
        throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || '未知错误');
      }
      
      return {
        context: { slot: 0 },
        value: result.balance || 0
      };
    } catch (error) {
      console.error('[Solana代理] 获取余额失败:', error);
      throw new Error(`failed to get balance: ${error.message}`);
    }
  }

  /**
   * 处理getTokenBalance方法
   * @private
   */
  async _handleGetTokenBalance(args) {
    try {
      const address = args[0].toString();
      const response = await fetch(`${this.apiPrefix}/get_token_balance?address=${address}`);
      if (!response.ok) {
        throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || '未知错误');
      }
      
      return {
        context: { slot: 0 },
        value: result.balance
      };
    } catch (error) {
      console.error('[Solana代理] 获取代币余额失败:', error);
      throw new Error(`failed to get token balance: ${error.message}`);
    }
  }

  /**
   * 处理getTokenAccounts方法
   * @private
   */
  async _handleGetTokenAccounts(args) {
    try {
      const owner = args[0].toString();
      const mint = args[1]?.mint?.toString();
      
      let url = `${this.apiPrefix}/get_token_accounts?owner=${owner}`;
      if (mint) {
        url += `&mint=${mint}`;
      }
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || '未知错误');
      }
      
      return {
        context: { slot: 0 },
        value: result.accounts.map(acc => ({
          pubkey: acc.address,
          account: {
            data: {
              parsed: {
                info: {
                  mint: acc.mint,
                  owner: acc.owner,
                  tokenAmount: acc.tokenAmount
                }
              }
            }
          }
        }))
      };
    } catch (error) {
      console.error('[Solana代理] 获取代币账户失败:', error);
      throw new Error(`failed to get token accounts: ${error.message}`);
    }
  }
}

// 创建并初始化代理
window.solanaConnectionProxy = new SolanaConnectionProxy();
window.solanaConnectionProxy.init();

console.log('[Solana代理] 脚本已加载'); 