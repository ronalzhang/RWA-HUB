/**
 * 统一的购买处理器
 * 版本: 2.0.0 - 完全重构，统一所有购买逻辑
 */

class PurchaseHandler {
    constructor() {
        this.isProcessing = false;
        this.currentModal = null;
        this.init();
    }

    init() {
        console.log('Initializing unified purchase handler...');
        this.bindEvents();
        this.updateButtonStates();
    }

    bindEvents() {
        // 绑定购买按钮点击事件
        document.addEventListener('click', (event) => {
            const button = event.target.closest('#buy-button, .buy-button, [data-action="buy"]');
            if (button && !button.disabled) {
                event.preventDefault();
                this.handleBuyClick(button);
            }
        });

        // 监听钱包状态变化
        document.addEventListener('walletStateChanged', () => {
            this.updateButtonStates();
        });

        document.addEventListener('walletConnected', () => {
            this.updateButtonStates();
        });

        document.addEventListener('walletDisconnected', () => {
            this.updateButtonStates();
        });
    }

    async handleBuyClick(button) {
        if (this.isProcessing) {
            console.log('Purchase already in progress, ignoring click');
            return;
        }

        try {
            this.isProcessing = true;
            this.setButtonState(button, 'Processing...', true);

            // 获取购买参数
            const assetId = button.getAttribute('data-asset-id');
            const amountInput = document.getElementById('purchase-amount');
            const amount = amountInput ? parseInt(amountInput.value) : 1;

            if (!assetId) {
                throw new Error('Asset ID not found');
            }

            if (!amount || amount <= 0) {
                throw new Error('Please enter a valid purchase amount');
            }

            // 检查钱包连接
            if (!this.isWalletConnected()) {
                throw new Error('Please connect your wallet first');
            }

            // 准备购买
            const prepareData = await this.preparePurchase(assetId, amount);
            
            // 显示确认模态框
            this.showPurchaseModal(prepareData);

        } catch (error) {
            console.error('Purchase preparation failed:', error);
            this.showError(error.message);
            this.setButtonState(button, 'Buy', false);
        } finally {
            this.isProcessing = false;
        }
    }

    async preparePurchase(assetId, amount) {
        const walletAddress = this.getWalletAddress();
        
        // 首先尝试智能合约准备，如果失败则回退到传统方式
        try {
            const response = await fetch('/api/blockchain/prepare_purchase', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': walletAddress,
                    'X-Wallet-Type': this.getWalletType() || 'unknown'
                },
                body: JSON.stringify({
                    asset_id: assetId,
                    buyer_address: walletAddress,
                    amount: amount
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // 转换为统一格式
                    return {
                        success: true,
                        asset_id: assetId,
                        amount: amount,
                        price: data.asset_info.token_price,
                        name: data.asset_info.name,
                        total_price: data.total_price,
                        platform_fee: data.platform_fee,
                        creator_amount: data.creator_amount,
                        platform_address: 'Smart Contract', // 智能合约自动分账
                        purchase_type: 'smart_contract',
                        contract_data: data
                    };
                }
            }
        } catch (error) {
            console.log('Smart contract preparation failed, trying traditional method:', error.message);
        }

        // 回退到传统准备方式
        const response = await fetch('/api/trades/prepare_purchase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': walletAddress
            },
            body: JSON.stringify({
                asset_id: assetId,
                amount: amount,
                wallet_address: walletAddress
            })
        });

        if (!response.ok) {
            throw new Error(`Preparation failed: ${response.status}`);
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.message || 'Purchase preparation failed');
        }

        // 添加购买类型标识
        data.purchase_type = 'traditional';
        return data;
    }

    showPurchaseModal(prepareData) {
        // 移除现有模态框
        const existingModal = document.getElementById('buyModal');
        if (existingModal) {
            existingModal.remove();
        }

        // 创建新的模态框
        const modalHtml = `
            <div class="modal fade" id="buyModal" tabindex="-1" aria-labelledby="buyModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="buyModalLabel">Confirm Purchase</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div id="buyModalError" class="alert alert-danger" style="display: none;"></div>
                            <div class="mb-3">
                                <strong>Asset:</strong> ${prepareData.name}
                            </div>
                            <div class="mb-3">
                                <strong>Amount:</strong> ${prepareData.amount} tokens
                            </div>
                            <div class="mb-3">
                                <strong>Price per token:</strong> ${prepareData.price} USDC
                            </div>
                            <div class="mb-3">
                                <strong>Total:</strong> ${(prepareData.total_price || prepareData.amount * prepareData.price).toFixed(2)} USDC
                            </div>
                            ${prepareData.purchase_type === 'smart_contract' ? `
                            <div class="mb-3">
                                <div class="alert alert-info">
                                    <strong>Smart Contract Purchase</strong><br>
                                    <small>Automatic fee distribution:</small><br>
                                    <small>• Platform fee: ${prepareData.platform_fee.toFixed(2)} USDC (3.5%)</small><br>
                                    <small>• Creator amount: ${prepareData.creator_amount.toFixed(2)} USDC</small>
                                </div>
                            </div>
                            ` : `
                            <div class="mb-3">
                                <strong>Platform:</strong> ${prepareData.platform_address}
                            </div>
                            `}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="confirmPurchaseBtn">
                                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true" style="display: none;"></span>
                                Confirm Purchase
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('buyModal'));
        const confirmBtn = document.getElementById('confirmPurchaseBtn');
        
        // 绑定确认按钮事件
        confirmBtn.addEventListener('click', () => {
            this.executePurchase(prepareData, modal, confirmBtn);
        });

        modal.show();
        this.currentModal = modal;
    }

    async executePurchase(prepareData, modal, confirmBtn) {
        try {
            this.setButtonState(confirmBtn, 'Processing...', true);
            this.hideModalError();

            const walletAddress = this.getWalletAddress();

            // 根据购买类型选择不同的执行方式
            if (prepareData.purchase_type === 'smart_contract') {
                return await this.executeSmartContractPurchase(prepareData, modal, confirmBtn, walletAddress);
            } else {
                return await this.executeTraditionalPurchase(prepareData, modal, confirmBtn, walletAddress);
            }

        } catch (error) {
            console.error('Error during purchase execution:', error);
            this.showModalError(error.message);
            this.setButtonState(confirmBtn, 'Confirm Purchase', false);
            throw error;
        }
    }

    async executeSmartContractPurchase(prepareData, modal, confirmBtn, walletAddress) {
        console.log('Executing smart contract purchase for asset:', prepareData.asset_id);

        // 使用预准备的智能合约数据
        const contractData = prepareData.contract_data;
        
        // 请求用户在钱包中签名智能合约交易
        this.setButtonState(confirmBtn, 'Please confirm in wallet...', true);

        const transactionData = contractData.transaction_data;
        const totalPrice = contractData.total_price;

        console.log(`Executing smart contract purchase: ${prepareData.amount} tokens, total: ${totalPrice} USDC`);
        console.log('Platform fee:', contractData.platform_fee, 'Creator amount:', contractData.creator_amount);

            // 检查Solana钱包API
            if (!window.solana || !window.solana.signAndSendTransaction) {
                throw new Error('Solana wallet API not available');
            }

            // 解码交易数据
            let transactionBuffer;
            try {
                const binaryString = atob(transactionData);
                transactionBuffer = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                    transactionBuffer[i] = binaryString.charCodeAt(i);
                }
                console.log('Transaction data decoded successfully, length:', transactionBuffer.length);
            } catch (error) {
                throw new Error(`Transaction data decode failed: ${error.message}`);
            }

            // 创建兼容的Transaction对象
            const compatibleTransaction = {
                serialize: function() {
                    console.log('Transaction.serialize() called');
                    return transactionBuffer;
                },
                serializeMessage: function() {
                    console.log('Transaction.serializeMessage() called');
                    return transactionBuffer;
                },
                signatures: [],
                feePayer: null,
                recentBlockhash: null,
                instructions: [],
                _message: transactionBuffer,
                _serialized: transactionBuffer
            };

        // 执行智能合约交易
        console.log('Sending transaction to wallet for signing...');
        
        const walletResult = await window.solana.signAndSendTransaction(compatibleTransaction);
        console.log('Wallet transaction result:', walletResult);

        // 处理钱包返回结果
        let signature;
        if (walletResult && walletResult.signature) {
            signature = walletResult.signature;
        } else if (typeof walletResult === 'string') {
            signature = walletResult;
        } else {
            throw new Error('Invalid wallet response format');
        }

        if (!signature) {
            throw new Error('No transaction signature returned from wallet');
        }

        console.log('Smart contract transaction successful, signature:', signature);

        // 确认智能合约购买
        this.setButtonState(confirmBtn, 'Confirming purchase...', true);

        const executeResult = await fetch('/api/blockchain/execute_purchase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': walletAddress
            },
            body: JSON.stringify({
                asset_id: prepareData.asset_id,
                buyer_address: walletAddress,
                amount: prepareData.amount,
                signed_transaction: signature
            })
        });

        if (!executeResult.ok) {
            throw new Error(`Smart contract execution failed: ${executeResult.status}`);
        }

        const executeData = await executeResult.json();
        console.log('Smart contract execution result:', executeData);

        if (!executeData.success) {
            throw new Error(executeData.error || 'Smart contract execution failed');
        }

        console.log('Smart contract purchase completed successfully');

        // 显示成功消息
        this.showSuccess(`Smart Contract Purchase Successful! You have purchased ${prepareData.amount} tokens. USDC payment and token transfer completed with automatic fee distribution. Transaction: ${signature.slice(0, 8)}...`);

        // 关闭模态框
        modal.hide();

        // 刷新资产信息
        this.refreshAssetInfo(prepareData.asset_id);

        return {
            success: true,
            transaction_signature: signature,
            trade_id: executeData.trade_id,
            message: 'Smart contract purchase confirmed with automatic fee distribution'
        };
    }

    async executeTraditionalPurchase(prepareData, modal, confirmBtn, walletAddress) {
        console.log('Executing traditional purchase for asset:', prepareData.asset_id);

        // 1. 执行转账
        console.log(`Preparing to transfer ${prepareData.amount * prepareData.price} USDC to ${prepareData.platform_address}`);
        
        const transferResult = await fetch('/api/execute_transfer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': walletAddress
            },
            body: JSON.stringify({
                token_symbol: 'USDC',
                amount: parseFloat(prepareData.amount * prepareData.price),
                to_address: prepareData.platform_address,
                from_address: walletAddress
            })
        });

        if (!transferResult.ok) {
            throw new Error(`Transfer failed: ${transferResult.status}`);
        }

        const transferData = await transferResult.json();
        console.log('Transfer result:', transferData);

        if (!transferData.success) {
            throw new Error(transferData.message || 'Transfer failed');
        }

        // 2. 确认购买
        console.log('Transfer successful, now confirming purchase');

        const confirmResult = await fetch('/api/trades/confirm_purchase', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': walletAddress
            },
            body: JSON.stringify({
                purchase_id: prepareData.purchase_id,
                signature: transferData.signature,
                asset_id: prepareData.asset_id,
                wallet_address: walletAddress,
                amount: prepareData.amount
            })
        });

        if (!confirmResult.ok) {
            const errorData = await confirmResult.json();
            throw new Error(errorData.error || 'Purchase confirmation failed');
        }

        const confirmData = await confirmResult.json();
        console.log('Purchase confirmation result:', confirmData);

        if (!confirmData.success) {
            throw new Error(confirmData.error || 'Purchase confirmation processing failed');
        }

        console.log('Traditional purchase flow completed');

        // 显示成功消息
        this.showSuccess('Purchase successful! Transaction submitted');

        // 关闭模态框
        modal.hide();

        // 刷新资产信息
        this.refreshAssetInfo(prepareData.asset_id);

        return confirmData;
    }

    async refreshAssetInfo(assetId) {
        console.log('Refreshing asset info for asset ID:', assetId);
        
        try {
            // 尝试多个API端点
            const endpoints = [
                `/api/assets/${assetId}`,
                `/api/assets/symbol/${assetId}`,
                `/api/assets/RH-${assetId}`
            ];

            let assetData = null;
            for (const endpoint of endpoints) {
                try {
                    console.log(`Trying API endpoint: ${endpoint}`);
                    const response = await fetch(endpoint);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.success && data.asset) {
                            assetData = data.asset;
                            break;
                        }
                    }
                } catch (error) {
                    console.log(`Endpoint ${endpoint} failed:`, error.message);
                }
            }

            if (assetData) {
                console.log('Updating asset info display:', assetData);
                this.updateAssetDisplay(assetData);
            } else {
                console.log('Could not refresh asset info from any endpoint');
            }

        } catch (error) {
            console.error('Failed to refresh asset info:', error);
        }
    }

    updateAssetDisplay(assetData) {
        // 更新剩余供应量
        const remainingSupplyElement = document.querySelector('[data-field="remaining_supply"]');
        if (remainingSupplyElement && assetData.remaining_supply !== undefined) {
            remainingSupplyElement.textContent = assetData.remaining_supply.toLocaleString();
        }

        // 更新价格
        const priceElements = document.querySelectorAll('.asset-price, .price-value, [data-asset-price]');
        priceElements.forEach(element => {
            if (assetData.token_price !== undefined) {
                element.textContent = `${assetData.token_price} USDC`;
            }
        });

        // 触发余额更新事件
        if (typeof window.triggerBalanceUpdatedEvent === 'function') {
            window.triggerBalanceUpdatedEvent('USDC', 0);
        }
    }

    // 工具方法
    isWalletConnected() {
        if (window.walletState && (window.walletState.connected || window.walletState.isConnected)) {
            return true;
        }
        return !!localStorage.getItem('walletAddress');
    }

    getWalletAddress() {
        if (window.walletState && window.walletState.address) {
            return window.walletState.address;
        }
        return localStorage.getItem('walletAddress');
    }

    getWalletType() {
        if (window.walletState && window.walletState.walletType) {
            return window.walletState.walletType;
        }
        return localStorage.getItem('walletType') || 'phantom';
    }

    updateButtonStates() {
        const buyButtons = document.querySelectorAll('#buy-button, .buy-button, [data-action="buy"]');
        const isConnected = this.isWalletConnected();

        buyButtons.forEach(button => {
            if (isConnected) {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-shopping-cart me-2"></i>Buy';
            } else {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-wallet me-2"></i>Please Connect Wallet';
            }
        });
    }

    setButtonState(button, text, disabled) {
        if (button) {
            button.disabled = disabled;
            if (disabled && text.includes('Processing')) {
                button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${text}`;
            } else {
                button.innerHTML = text.includes('Buy') ? `<i class="fas fa-shopping-cart me-2"></i>${text}` : text;
            }
        }
    }

    showError(message) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Error',
                text: message,
                icon: 'error',
                confirmButtonText: 'OK'
            });
        } else {
            alert(message);
        }
    }

    showSuccess(message) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Success',
                text: message,
                icon: 'success',
                confirmButtonText: 'OK'
            });
        } else {
            alert(message);
        }
    }

    showModalError(message) {
        const errorDiv = document.getElementById('buyModalError');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }
    }

    hideModalError() {
        const errorDiv = document.getElementById('buyModalError');
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
    }
}

// 初始化购买处理器
document.addEventListener('DOMContentLoaded', () => {
    window.purchaseHandler = new PurchaseHandler();
});

// 导出给其他脚本使用
window.PurchaseHandler = PurchaseHandler;