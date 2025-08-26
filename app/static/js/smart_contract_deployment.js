/**
 * 智能合约部署和完整购买流程
 */

// 智能合约部署流程
class SmartContractDeployment {
    constructor() {
        this.isDeploying = false;
        this.deploymentStatus = null;
    }

    // 部署智能合约
    async deployContract(assetId) {
        if (this.isDeploying) {
            console.log('合约部署正在进行中...');
            return;
        }

        try {
            this.isDeploying = true;
            
            // 显示部署进度模态框
            this.showDeploymentModal();
            
            console.log(`开始部署智能合约，资产ID: ${assetId}`);
            
            // 调用部署API
            const response = await fetch('/api/deploy-contract', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    asset_id: assetId,
                    blockchain: 'solana'
                })
            });

            const result = await response.json();
            console.log('合约部署API响应:', result);

            if (result.success) {
                this.deploymentStatus = 'success';
                this.showDeploymentSuccess(result);
            } else {
                throw new Error(result.message || '部署失败');
            }

        } catch (error) {
            console.error('智能合约部署失败:', error);
            this.deploymentStatus = 'failed';
            this.showDeploymentError(error.message);
        } finally {
            this.isDeploying = false;
        }
    }

    // 显示部署进度模态框
    showDeploymentModal() {
        const modal = document.createElement('div');
        modal.id = 'deploymentModal';
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-rocket me-2"></i>智能合约部署中
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <h6>正在部署智能合约到Solana区块链...</h6>
                        <p class="text-muted">这可能需要几分钟时间，请耐心等待</p>
                        <div class="progress mt-3">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                 role="progressbar" style="width: 75%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden';
    }

    // 显示部署成功
    showDeploymentSuccess(result) {
        const modal = document.getElementById('deploymentModal');
        if (modal) {
            modal.querySelector('.modal-content').innerHTML = `
                <div class="modal-header bg-success text-white">
                    <h5 class="modal-title">
                        <i class="fas fa-check-circle me-2"></i>部署成功！
                    </h5>
                </div>
                <div class="modal-body text-center">
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                        <h5>智能合约部署成功！</h5>
                        <p>您的资产已成功部署到Solana区块链</p>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label fw-bold">合约地址:</label>
                        <div class="input-group">
                            <input type="text" class="form-control" readonly 
                                   value="${result.contract_address}" id="contractAddress">
                            <button class="btn btn-outline-secondary" onclick="copyContractAddress()">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="d-grid gap-2">
                        <button class="btn btn-primary" onclick="closeDeploymentModal()">
                            <i class="fas fa-shopping-cart me-2"></i>开始交易
                        </button>
                        <button class="btn btn-outline-secondary" onclick="viewOnExplorer('${result.contract_address}')">
                            <i class="fas fa-external-link-alt me-2"></i>在区块链浏览器中查看
                        </button>
                    </div>
                </div>
            `;
        }
    }

    // 显示部署错误
    showDeploymentError(errorMessage) {
        const modal = document.getElementById('deploymentModal');
        if (modal) {
            modal.querySelector('.modal-content').innerHTML = `
                <div class="modal-header bg-danger text-white">
                    <h5 class="modal-title">
                        <i class="fas fa-exclamation-triangle me-2"></i>部署失败
                    </h5>
                </div>
                <div class="modal-body text-center">
                    <div class="alert alert-danger">
                        <i class="fas fa-times-circle fa-3x text-danger mb-3"></i>
                        <h5>智能合约部署失败</h5>
                        <p>${errorMessage}</p>
                    </div>
                    
                    <div class="d-grid gap-2">
                        <button class="btn btn-primary" onclick="retryDeployment()">
                            <i class="fas fa-redo me-2"></i>重试部署
                        </button>
                        <button class="btn btn-outline-secondary" onclick="closeDeploymentModal()">
                            <i class="fas fa-times me-2"></i>关闭
                        </button>
                    </div>
                </div>
            `;
        }
    }
}

// 完整购买流程
class CompletePurchaseFlow {
    constructor() {
        this.isPurchasing = false;
        this.currentTransaction = null;
    }

    // 初始化购买流程
    async initiatePurchase(assetId, amount) {
        console.log('[DEBUG] initiatePurchase called');
        if (this.isPurchasing) {
            console.log('购买流程正在进行中...');
            return;
        }

        try {
            this.isPurchasing = true;
            
            console.log(`开始购买流程，资产ID: ${assetId}, 数量: ${amount}`);
            
            // 1. 检查钱包连接
            await this.checkWalletConnection();
            
            // 2. 验证购买参数
            await this.validatePurchaseParams(assetId, amount);
            
            // 3. 创建购买交易
            const transaction = await this.createPurchaseTransaction(assetId, amount);
            
            // 4. 签名交易
            const signedTransaction = await this.signTransaction(transaction);
            
            // 5. 提交到区块链
            const result = await this.submitTransaction(signedTransaction, assetId, amount);
            
            // 6. 显示成功结果
            this.showPurchaseSuccess(result);
            
        } catch (error) {
            console.error('购买流程失败:', error);
            this.showPurchaseError(error.message);
        } finally {
            this.isPurchasing = false;
        }
    }

    // 检查钱包连接
    async checkWalletConnection() {
        if (!window.solana || !window.solana.isPhantom) {
            throw new Error('请先安装Phantom钱包');
        }

        if (!window.solana.isConnected) {
            console.log('钱包未连接，尝试连接...');
            await window.solana.connect();
        }

        if (!window.solana.publicKey) {
            throw new Error('钱包连接失败，请重试');
        }

        console.log('钱包连接成功:', window.solana.publicKey.toString());
    }

    // 验证购买参数
    async validatePurchaseParams(assetId, amount) {
        if (!assetId || amount <= 0) {
            throw new Error('无效的购买参数');
        }

        // 检查资产是否已部署
        const assetResponse = await fetch(`/api/assets/${assetId}/status`);
        const assetData = await assetResponse.json();
        
        if (!assetData.success || !assetData.asset.is_deployed) {
            throw new Error('资产尚未部署智能合约，无法购买');
        }

        // 检查剩余供应量
        if (amount > assetData.asset.remaining_supply) {
            throw new Error(`购买数量超过剩余供应量 (${assetData.asset.remaining_supply})`);
        }

        console.log('购买参数验证通过');
    }

    // 创建购买交易
    async createPurchaseTransaction(assetId, amount) {
        this.showProgressModal('创建购买交易...');
        
        const response = await fetch('/api/v2/trades/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': window.solana.publicKey.toString()
            },
            body: JSON.stringify({
                asset_id: assetId,
                amount: amount
            })
        });

        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || '创建交易失败');
        }

        console.log('V2 购买交易创建成功');
        // 返回整个结果，因为它包含了 trade_id 和 transaction_to_sign
        return result;
    }

    // 签名交易
    async signTransaction(transactionData) {
        this.updateProgressModal('请在钱包中确认交易...');
        
        const { transaction_to_sign } = transactionData;

        return new Promise((resolve, reject) => {
            const checkSolanaWeb3 = () => {
                if (typeof window.solanaWeb3 !== 'undefined') {
                    console.log('solanaWeb3 is loaded, proceeding with signing.');
                    try {
                        // 将交易数据转换为Transaction对象
                        const transactionObj = window.solanaWeb3.Transaction.from(
                            Buffer.from(transaction_to_sign.serialized_transaction, 'base64')
                        );
                        
                        window.solana.signTransaction(transactionObj).then(signedTransaction => {
                            console.log('交易签名成功');
                            // 返回签名后的交易哈希和原始的trade_id
                            resolve({ 
                                signature: signedTransaction.signature.toString('base64'),
                                trade_id: transactionData.trade_id
                            });
                        }).catch(error => {
                            if (error.message.includes('User rejected')) {
                                reject(new Error('用户取消了交易签名'));
                            }
                            reject(new Error('交易签名失败: ' + error.message));
                        });
                    } catch (error) {
                        reject(new Error('创建交易对象失败: ' + error.message));
                    }
                } else {
                    console.log('Waiting for solanaWeb3 to load...');
                    setTimeout(checkSolanaWeb3, 100);
                }
            };
            checkSolanaWeb3();
        });
    }

    // 提交交易到区块链
    async submitTransaction(signedData) {
        this.updateProgressModal('提交交易到区块链...');
        
        const { signature, trade_id } = signedData;

        const response = await fetch('/api/v2/trades/confirm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': window.solana.publicKey.toString()
            },
            body: JSON.stringify({
                trade_id: trade_id,
                tx_hash: signature
            })
        });

        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || '交易提交失败');
        }

        console.log('V2 交易提交成功:', result);
        // 添加 tx_hash 到结果中以便显示
        result.transaction_hash = signature;
        return result;
    }

    // 显示进度模态框
    showProgressModal(message) {
        let modal = document.getElementById('purchaseProgressModal');
        
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'purchaseProgressModal';
            modal.className = 'modal fade show';
            modal.style.display = 'block';
            modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
            document.body.appendChild(modal);
        }
        
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            <i class="fas fa-shopping-cart me-2"></i>处理购买请求
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <h6 id="progressMessage">${message}</h6>
                        <p class="text-muted">请不要关闭此页面</p>
                    </div>
                </div>
            </div>
        `;
        
        document.body.style.overflow = 'hidden';
    }

    // 更新进度消息
    updateProgressModal(message) {
        const messageElement = document.getElementById('progressMessage');
        if (messageElement) {
            messageElement.textContent = message;
        }
    }

    // 显示购买成功
    showPurchaseSuccess(result) {
        const modal = document.getElementById('purchaseProgressModal');
        if (modal) {
            modal.querySelector('.modal-content').innerHTML = `
                <div class="modal-header bg-success text-white">
                    <h5 class="modal-title">
                        <i class="fas fa-check-circle me-2"></i>购买成功！
                    </h5>
                </div>
                <div class="modal-body text-center">
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                        <h5>购买交易已完成！</h5>
                        <p>您的代币将在区块链确认后到账</p>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label fw-bold">交易哈希:</label>
                        <div class="input-group">
                            <input type="text" class="form-control" readonly 
                                   value="${result.transaction_hash}" id="transactionHash">
                            <button class="btn btn-outline-secondary" onclick="copyTransactionHash()">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="d-grid gap-2">
                        <button class="btn btn-primary" onclick="closePurchaseModal()">
                            <i class="fas fa-check me-2"></i>完成
                        </button>
                        <button class="btn btn-outline-secondary" onclick="viewTransactionOnExplorer('${result.transaction_hash}')">
                            <i class="fas fa-external-link-alt me-2"></i>在区块链浏览器中查看
                        </button>
                    </div>
                </div>
            `;
        }
    }

    // 显示购买错误
    showPurchaseError(errorMessage) {
        const modal = document.getElementById('purchaseProgressModal');
        if (modal) {
            modal.querySelector('.modal-content').innerHTML = `
                <div class="modal-header bg-danger text-white">
                    <h5 class="modal-title">
                        <i class="fas fa-exclamation-triangle me-2"></i>购买失败
                    </h5>
                </div>
                <div class="modal-body text-center">
                    <div class="alert alert-danger">
                        <i class="fas fa-times-circle fa-3x text-danger mb-3"></i>
                        <h5>购买交易失败</h5>
                        <p>${errorMessage}</p>
                    </div>
                    
                    <div class="d-grid gap-2">
                        <button class="btn btn-primary" onclick="retryPurchase()">
                            <i class="fas fa-redo me-2"></i>重试购买
                        </button>
                        <button class="btn btn-outline-secondary" onclick="closePurchaseModal()">
                            <i class="fas fa-times me-2"></i>关闭
                        </button>
                    </div>
                </div>
            `;
        }
    }
}

// 全局实例
window.smartContractDeployment = new SmartContractDeployment();
window.completePurchaseFlow = new CompletePurchaseFlow();

// 全局函数
window.deploySmartContract = function(assetId) {
    window.smartContractDeployment.deployContract(assetId);
};

window.initiatePurchase = function(assetId, amount) {
    window.completePurchaseFlow.initiatePurchase(assetId, amount);
};

// 辅助函数
window.copyContractAddress = function() {
    const input = document.getElementById('contractAddress');
    if (input) {
        input.select();
        document.execCommand('copy');
        showToast('合约地址已复制到剪贴板');
    }
};

window.copyTransactionHash = function() {
    const input = document.getElementById('transactionHash');
    if (input) {
        input.select();
        document.execCommand('copy');
        showToast('交易哈希已复制到剪贴板');
    }
};

window.viewOnExplorer = function(address) {
    window.open(`https://solscan.io/account/${address}`, '_blank');
};

window.viewTransactionOnExplorer = function(txHash) {
    window.open(`https://solscan.io/tx/${txHash}`, '_blank');
};

window.closeDeploymentModal = function() {
    const modal = document.getElementById('deploymentModal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
        // 刷新页面以显示最新状态
        window.location.reload();
    }
};

window.closePurchaseModal = function() {
    const modal = document.getElementById('purchaseProgressModal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
        // 刷新页面以显示最新状态
        window.location.reload();
    }
};

window.retryDeployment = function() {
    const assetId = window.ASSET_CONFIG?.id;
    if (assetId) {
        window.smartContractDeployment.deployContract(assetId);
    }
};

window.retryPurchase = function() {
    const assetId = window.ASSET_CONFIG?.id;
    const amount = document.getElementById('purchase-amount')?.value;
    if (assetId && amount) {
        window.completePurchaseFlow.initiatePurchase(assetId, parseInt(amount));
    }
};

// 显示提示消息
function showToast(message) {
    // 创建简单的toast提示
    const toast = document.createElement('div');
    toast.className = 'alert alert-success position-fixed';
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// 购买按钮点击处理 - 全局可访问
window.handlePurchaseClick = function() {
    console.log('[DEBUG] handlePurchaseClick called');
    
    // 检查钱包连接
    const walletAddress = getWalletAddress();
    if (!walletAddress) {
        showToast('请先连接您的钱包');
        return;
    }
    
    const assetId = window.ASSET_CONFIG?.id;
    const amountInput = document.getElementById('purchase-amount');
    const amount = parseInt(amountInput?.value || 0);
    console.log(`[DEBUG] assetId: ${assetId}, amount: ${amount}`);
    
    if (!assetId) {
        showToast('资产信息错误');
        return;
    }
    
    if (!amount || amount <= 0) {
        showToast('请输入有效的购买数量');
        amountInput?.focus();
        return;
    }
    
    if (amount > window.ASSET_CONFIG?.remainingSupply) {
        showToast(`购买数量不能超过剩余供应量 (${window.ASSET_CONFIG.remainingSupply})`);
        amountInput?.focus();
        return;
    }
    
    // 启动完整购买流程
    window.completePurchaseFlow.initiatePurchase(assetId, amount);
};

// 获取钱包地址的辅助函数
function getWalletAddress() {
    if (window.walletState && window.walletState.address) {
        return window.walletState.address;
    }
    
    if (localStorage.getItem('walletAddress')) {
        return localStorage.getItem('walletAddress');
    }
    
    if (window.solana && window.solana.publicKey) {
        return window.solana.publicKey.toString();
    }
    
    if (window.ethereum && window.ethereum.selectedAddress) {
        return window.ethereum.selectedAddress;
    }
    
    return null;
}

// 调试：检查购买按钮状态
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        const buyButton = document.getElementById('buy-button');
        if (buyButton) {
            console.log('✅ 购买按钮存在');
            console.log('✅ 购买按钮事件监听器数量:', getEventListeners ? getEventListeners(buyButton) : '无法检测');
            
            // 添加调试点击事件
            buyButton.addEventListener('click', function(e) {
                console.log('🔍 购买按钮被点击 - 调试信息:');
                console.log('- 事件对象:', e);
                console.log('- 钱包状态:', window.walletState);
                console.log('- 资产配置:', window.ASSET_CONFIG);
                console.log('- completePurchaseFlow 可用:', !!window.completePurchaseFlow);
            }, true); // 使用捕获阶段，确保最先执行
        } else {
            console.warn('⚠️ 购买按钮不存在');
        }
    }, 500);
});

console.log('✅ 智能合约部署和购买流程模块已加载');