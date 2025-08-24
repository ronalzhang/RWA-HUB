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
        console.log('Using smart contract purchase preparation method.');

        const response = await fetch('/api/create-purchase-transaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Wallet-Address': walletAddress
            },
            body: JSON.stringify({
                asset_id: assetId,
                amount: amount,
                buyer_address: walletAddress
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Preparation failed: ${response.status}`);
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Purchase preparation failed');
        }

        // Add purchase type identifier for smart contract flow
        data.purchase_type = 'smart_contract';
        
        // Fetch asset details to show in the modal
        const assetResponse = await fetch(`/api/assets/${assetId}`);
        if (assetResponse.ok) {
            const assetData = await assetResponse.json();
            if (assetData.success) {
                data.name = assetData.asset.name;
                data.price = assetData.asset.token_price;
                data.total_price = data.amount * data.price;
                data.platform_address = 'Platform'; // Placeholder
            }
        }

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
                                    <small>This transaction will be processed on the blockchain.</small>
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
        this.setButtonState(confirmBtn, 'Please confirm in wallet...', true);

        try {
            const transactionData = prepareData.transaction;
            if (!transactionData) {
                throw new Error('Transaction data not found in preparation response.');
            }

            if (!window.solana || !window.solana.signAndSendTransaction) {
                throw new Error('Solana wallet API not available');
            }

            // Decode the base64 transaction data
            const transactionBuffer = Uint8Array.from(atob(transactionData), c => c.charCodeAt(0));

            // Create a transaction object that the wallet can understand
            const transaction = {
                serialize: () => transactionBuffer,
                serializeMessage: () => transactionBuffer,
                signatures: [],
                feePayer: null,
                recentBlockhash: null,
                instructions: [],
            };

            const { signature } = await window.solana.signAndSendTransaction(transaction);

            if (!signature) {
                throw new Error('Transaction was not signed or sent.');
            }

            console.log('Transaction successful, signature:', signature);

            this.setButtonState(confirmBtn, 'Finalizing purchase...', true);

            const executeResult = await fetch('/api/submit-transaction', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': walletAddress
                },
                body: JSON.stringify({
                    asset_id: prepareData.asset_id,
                    amount: prepareData.amount,
                    signed_transaction: signature,
                    trade_id: prepareData.trade_id // Pass the trade_id back
                })
            });

            if (!executeResult.ok) {
                const errorData = await executeResult.json().catch(() => ({}));
                throw new Error(errorData.error || `Purchase finalization failed: ${executeResult.status}`);
            }

            const executeData = await executeResult.json();
            if (!executeData.success) {
                throw new Error(executeData.error || 'Purchase finalization failed on backend.');
            }

            console.log('Smart contract purchase completed successfully');
            this.showSuccess('Purchase successful! Your transaction has been submitted.');
            modal.hide();
            this.refreshAssetInfo(prepareData.asset_id);

            return {
                success: true,
                transaction_signature: signature,
                trade_id: executeData.trade_id,
                message: 'Smart contract purchase confirmed.'
            };

        } catch (error) {
            console.error('Error during smart contract purchase execution:', error);
            this.showModalError(error.message);
            this.setButtonState(confirmBtn, 'Confirm Purchase', false);
            throw error;
        }
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