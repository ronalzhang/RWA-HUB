// Solana Web3.js 库 - 服务器API中继版本
// 此版本修改了Connection对象的实现，使其通过服务器API中继连接，避免直接连接RPC节点

// 保存原始脚本的引用
const originalScript = document.createElement('script');
originalScript.src = '/static/js/contracts/solana-web3.iife.min.js';
originalScript.async = true;

// 在原始脚本加载后修改Connection对象
originalScript.onload = function() {
    console.log('原始Solana库已加载，开始修改Connection对象');
    
    // 确保全局变量正确设置
    if (window.solanaWeb3js) {
        window.solanaWeb3 = window.solanaWeb3js;
    } else if (window.solana && window.solana.web3) {
        window.solanaWeb3 = window.solana.web3;
    }
    
    if (!window.solanaWeb3) {
        console.error('无法找到solanaWeb3对象');
        return;
    }
    
    // 保存原始Connection类
    const OriginalConnection = window.solanaWeb3.Connection;
    
    // 创建代理Connection类
    window.solanaWeb3.Connection = function(endpoint, commitmentOrConfig) {
        console.log('创建代理Connection，使用服务器API中继');
        
        // 强制使用服务器API中继
        const serverEndpoint = '/api/solana';
        
        // 调用原始构造函数
        const connection = new OriginalConnection(serverEndpoint, commitmentOrConfig);
        
        // 标记为代理连接
        connection._isProxy = true;
        connection._originalEndpoint = endpoint;
        
        // 重写getBalance方法
        const originalGetBalance = connection.getBalance;
        connection.getBalance = async function(publicKey, commitmentOrConfig) {
            try {
                console.log('使用服务器API获取余额');
                const address = publicKey.toString();
                const response = await fetch(`/api/solana/get_balance?address=${address}`);
                if (!response.ok) {
                    throw new Error('获取余额API调用失败');
                }
                const data = await response.json();
                if (data.success) {
                    return data.lamports;
                } else {
                    throw new Error(data.error || '获取余额失败');
                }
            } catch (error) {
                console.error('获取余额出错，尝试原始方法:', error);
                // 出错时尝试使用原始方法（可能在非受限地区仍然可用）
                return originalGetBalance.call(this, publicKey, commitmentOrConfig);
            }
        };
        
        // 重写getLatestBlockhash方法
        const originalGetLatestBlockhash = connection.getLatestBlockhash;
        connection.getLatestBlockhash = async function(commitmentOrConfig) {
            try {
                console.log('使用服务器API获取最新区块哈希');
                const response = await fetch('/api/solana/get_latest_blockhash');
                if (!response.ok) {
                    throw new Error('获取区块哈希API调用失败');
                }
                const data = await response.json();
                if (data.success) {
                    return {
                        blockhash: data.blockhash,
                        lastValidBlockHeight: data.lastValidBlockHeight
                    };
                } else {
                    throw new Error(data.error || '获取区块哈希失败');
                }
            } catch (error) {
                console.error('获取区块哈希出错，尝试原始方法:', error);
                return originalGetLatestBlockhash.call(this, commitmentOrConfig);
            }
        };
        
        // 重写getAccountInfo方法
        const originalGetAccountInfo = connection.getAccountInfo;
        connection.getAccountInfo = async function(publicKey, commitmentOrConfig) {
            try {
                console.log('使用服务器API获取账户信息');
                const address = publicKey.toString();
                const response = await fetch(`/api/solana/check_account?address=${address}`);
                if (!response.ok) {
                    throw new Error('获取账户信息API调用失败');
                }
                const data = await response.json();
                if (data.success) {
                    return data.account_info;
                } else {
                    throw new Error(data.error || '获取账户信息失败');
                }
            } catch (error) {
                console.error('获取账户信息出错，尝试原始方法:', error);
                return originalGetAccountInfo.call(this, publicKey, commitmentOrConfig);
            }
        };
        
        // 重写sendTransaction方法
        const originalSendTransaction = connection.sendTransaction;
        connection.sendTransaction = async function(transaction, signersOrOptions, options) {
            try {
                console.log('使用服务器API发送交易');
                // 将交易序列化为base64
                const serializedTransaction = Buffer.from(transaction.serialize()).toString('base64');
                
                const response = await fetch('/api/solana/submit_transaction', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        serialized_transaction: serializedTransaction,
                        skip_preflight: options?.skipPreflight || false
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(`发送交易失败: ${errorData.error || response.statusText}`);
                }
                
                const result = await response.json();
                if (!result.success) {
                    throw new Error(`交易提交失败: ${result.error}`);
                }
                
                return result.signature;
            } catch (error) {
                console.error('发送交易出错，尝试原始方法:', error);
                return originalSendTransaction.call(this, transaction, signersOrOptions, options);
            }
        };
        
        // 重写confirmTransaction方法
        const originalConfirmTransaction = connection.confirmTransaction;
        connection.confirmTransaction = async function(signatureOrBlockhash, commitment) {
            try {
                console.log('使用服务器API确认交易');
                let signature;
                
                // 兼容不同的函数签名
                if (typeof signatureOrBlockhash === 'string') {
                    signature = signatureOrBlockhash;
                } else if (signatureOrBlockhash.signature) {
                    signature = signatureOrBlockhash.signature;
                } else {
                    throw new Error('无效的交易签名参数');
                }
                
                const response = await fetch(`/api/solana/check_transaction?signature=${signature}`);
                if (!response.ok) {
                    throw new Error('确认交易API调用失败');
                }
                
                const data = await response.json();
                
                return {
                    value: {
                        confirmations: data.confirmed ? 1 : 0,
                        confirmationStatus: data.confirmed ? 'confirmed' : 'processed'
                    }
                };
            } catch (error) {
                console.error('确认交易出错，尝试原始方法:', error);
                return originalConfirmTransaction.call(this, signatureOrBlockhash, commitment);
            }
        };
        
        return connection;
    };
    
    console.log('Connection对象已成功修改为使用服务器API中继');
};

// 添加错误处理
originalScript.onerror = function(error) {
    console.error('加载原始Solana库失败:', error);
};

// 将原始脚本添加到文档
document.head.appendChild(originalScript); 