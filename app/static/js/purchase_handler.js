'''
// Manually integrated SPL-Token functions to avoid CDN/bundler issues.
// Version: @solana/spl-token@0.4.13

const TOKEN_PROGRAM_ID = new solanaWeb3.PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
const ASSOCIATED_TOKEN_PROGRAM_ID = new solanaWeb3.PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL');

// Errors
class TokenError extends Error {
    constructor(message) {
        super(message);
        this.name = 'TokenError';
    }
}
class TokenAccountNotFoundError extends TokenError { constructor() { super('Token account not found'); this.name = 'TokenAccountNotFoundError'; } }
class TokenInvalidAccountOwnerError extends TokenError { constructor() { super('Token invalid account owner'); this.name = 'TokenInvalidAccountOwnerError'; } }
class TokenInvalidAccountSizeError extends TokenError { constructor() { super('Token invalid account size'); this.name = 'TokenInvalidAccountSizeError'; } }
class TokenInvalidMintError extends TokenError { constructor() { super('Token invalid mint'); this.name = 'TokenInvalidMintError'; } }
class TokenInvalidOwnerError extends TokenError { constructor() { super('Token invalid owner'); this.name = 'TokenInvalidOwnerError'; } }
class TokenOwnerOffCurveError extends TokenError { constructor() { super('Token owner off curve'); this.name = 'TokenOwnerOffCurveError'; } }


// state/mint.js
function getAssociatedTokenAddressSync(
    mint,
    owner,
    allowOwnerOffCurve = false,
    programId = TOKEN_PROGRAM_ID,
    associatedTokenProgramId = ASSOCIATED_TOKEN_PROGRAM_ID
) {
    if (!allowOwnerOffCurve && !solanaWeb3.PublicKey.isOnCurve(owner.toBuffer())) {
        throw new TokenOwnerOffCurveError();
    }

    const [address] = solanaWeb3.PublicKey.findProgramAddressSync(
        [owner.toBuffer(), programId.toBuffer(), mint.toBuffer()],
        associatedTokenProgramId
    );
    return address;
}

// state/account.js
const AccountLayout = solana.bufferLayout.struct([
    solana.bufferLayout.blob(32, 'mint'),
    solana.bufferLayout.blob(32, 'owner'),
    solana.bufferLayout.u64('amount'),
    solana.bufferLayout.u32('delegateOption'),
    solana.bufferLayout.blob(32, 'delegate'),
    solana.bufferLayout.u8('state'),
    solana.bufferLayout.u32('isNativeOption'),
    solana.bufferLayout.u64('isNative'),
    solana.bufferLayout.u64('delegatedAmount'),
    solana.bufferLayout.u32('closeAuthorityOption'),
    solana.bufferLayout.blob(32, 'closeAuthority'),
]);

const ACCOUNT_SIZE = AccountLayout.span;

function unpackAccount(address, info, programId = TOKEN_PROGRAM_ID) {
    if (!info) throw new TokenAccountNotFoundError();
    if (!info.owner.equals(programId)) throw new TokenInvalidAccountOwnerError();
    if (info.data.length < ACCOUNT_SIZE) throw new TokenInvalidAccountSizeError();

    const rawAccount = AccountLayout.decode(info.data.slice(0, ACCOUNT_SIZE));

    return {
        address,
        mint: new solanaWeb3.PublicKey(rawAccount.mint),
        owner: new solanaWeb3.PublicKey(rawAccount.owner),
        amount: rawAccount.amount,
        delegate: rawAccount.delegateOption ? new solanaWeb3.PublicKey(rawAccount.delegate) : null,
        delegatedAmount: rawAccount.delegatedAmount,
        isInitialized: rawAccount.state !== 0,
        isFrozen: rawAccount.state === 2,
        isNative: !!rawAccount.isNativeOption,
        rentExemptReserve: rawAccount.isNativeOption ? rawAccount.isNative : null,
        closeAuthority: rawAccount.closeAuthorityOption ? new solanaWeb3.PublicKey(rawAccount.closeAuthority) : null,
    };
}

async function getAccount(connection, address, commitment, programId = TOKEN_PROGRAM_ID) {
    const info = await connection.getAccountInfo(address, commitment);
    return unpackAccount(address, info, programId);
}


// instructions/associatedTokenAccount.js
function createAssociatedTokenAccountInstruction(
    payer,
    associatedToken,
    owner,
    mint,
    programId = TOKEN_PROGRAM_ID,
    associatedTokenProgramId = ASSOCIATED_TOKEN_PROGRAM_ID
) {
    const keys = [
        { pubkey: payer, isSigner: true, isWritable: true },
        { pubkey: associatedToken, isSigner: false, isWritable: true },
        { pubkey: owner, isSigner: false, isWritable: false },
        { pubkey: mint, isSigner: false, isWritable: false },
        { pubkey: solanaWeb3.SystemProgram.programId, isSigner: false, isWritable: false },
        { pubkey: programId, isSigner: false, isWritable: false },
    ];

    return new solanaWeb3.TransactionInstruction({
        keys,
        programId: associatedTokenProgramId,
        data: Buffer.alloc(0),
    });
}

// instructions/transfer.js
const transferInstructionData = solana.bufferLayout.struct([solana.bufferLayout.u8('instruction'), solana.bufferLayout.u64('amount')]);

function createTransferInstruction(
    source,
    destination,
    owner,
    amount,
    multiSigners = [],
    programId = TOKEN_PROGRAM_ID
) {
    const keys = [
        { pubkey: source, isSigner: false, isWritable: true },
        { pubkey: destination, isSigner: false, isWritable: true },
    ];

    if (multiSigners.length > 0) {
        keys.push({ pubkey: owner, isSigner: false, isWritable: false });
        for (const signer of multiSigners) {
            keys.push({ pubkey: signer.publicKey, isSigner: true, isWritable: false });
        }
    } else {
        keys.push({ pubkey: owner, isSigner: true, isWritable: false });
    }

    const data = Buffer.alloc(transferInstructionData.span);
    transferInstructionData.encode(
        {
            instruction: 3, // Transfer instruction
            amount: BigInt(amount),
        },
        data
    );

    return new solanaWeb3.TransactionInstruction({ keys, programId, data });
}


/**
 * 统一的购买处理器
 * 版本: 2.1.0 - 集成SPL-Token功能，移除外部依赖
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
        const buyButtons = document.querySelectorAll('#buy-button, .buy-button, [data-action="buy"]');
        buyButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                if (!button.disabled) {
                    event.preventDefault();
                    this.handleBuyClick(button);
                }
            });
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
        console.log('Using session-based purchase preparation method.');

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
            const errorData = await response.json().catch(() => ({ "error": "An unknown error occurred" }));
            throw new Error(errorData.error || `Preparation failed: ${response.status}`);
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Purchase preparation failed');
        }
        
        console.log("Purchase prepared successfully:", data);
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
                                <strong>Total:</strong> ${(prepareData.total_amount).toFixed(2)} USDC
                            </div>
                             <div class="mb-3">
                                <div class="alert alert-info">
                                    <strong>Pay to:</strong><br>
                                    <small>${prepareData.recipient_address}</small>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="confirmPurchaseBtn">
                                <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true" style="display: none;"></span>
                                Confirm & Pay
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
            this.setButtonState(confirmBtn, 'Processing Payment...', true);
            this.hideModalError();

            const walletAddress = this.getWalletAddress();

            // Step 1: Execute payment via wallet
            this.setButtonState(confirmBtn, 'Please confirm in wallet...', true);
            const signature = await this.executeWalletPayment(prepareData);
            
            if (!signature) {
                throw new Error("Payment was cancelled or failed in the wallet.");
            }

            console.log('Payment transaction successful, signature:', signature);
            this.setButtonState(confirmBtn, 'Finalizing purchase...', true);

            // Step 2: Confirm purchase with the backend
            const confirmResult = await fetch('/api/trades/confirm_purchase', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Wallet-Address': walletAddress
                },
                body: JSON.stringify({
                    purchase_id: prepareData.purchase_id,
                    signature: signature,
                    asset_id: prepareData.asset_id,
                    wallet_address: walletAddress,
                    amount: prepareData.amount
                })
            });

            if (!confirmResult.ok) {
                const errorData = await confirmResult.json().catch(() => ({}));
                throw new Error(errorData.error || `Purchase confirmation failed: ${confirmResult.status}`);
            }

            const confirmData = await confirmResult.json();
            if (!confirmData.success) {
                throw new Error(confirmData.error || 'Purchase confirmation failed on backend.');
            }

            console.log('Purchase completed successfully');
            this.showSuccess('Purchase successful! Your transaction has been submitted.');
            modal.hide();
            this.refreshAssetInfo(prepareData.asset_id);

            return {
                success: true,
                transaction_signature: signature,
                trade_id: confirmData.trade_id,
                message: 'Purchase confirmed.'
            };

        } catch (error) {
            console.error('Error during purchase execution:', error);
            this.showModalError(error.message);
            this.setButtonState(confirmBtn, 'Confirm & Pay', false);
            throw error;
        }
    }
    
    async executeWalletPayment(prepareData) {
        // This function creates and sends a real Solana transaction
        if (!window.solana || !window.solana.isPhantom) {
            throw new Error("Solana wallet (Phantom) not found.");
        }
        if (!window.solana.isConnected) {
            await window.solana.connect();
        }
        if (!window.solanaWeb3) {
            throw new Error("solanaWeb3 is not available. Please ensure the Solana Web3 library is loaded.");
        }

        const connection = new solanaWeb3.Connection(solanaWeb3.clusterApiUrl('mainnet-beta'));
        const fromPubkey = new solanaWeb3.PublicKey(this.getWalletAddress());
        const toPubkey = new solanaWeb3.PublicKey(prepareData.recipient_address);
        const usdcMint = new solanaWeb3.PublicKey('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v');

        const fromTokenAccountAddress = getAssociatedTokenAddressSync(usdcMint, fromPubkey);
        const toTokenAccountAddress = getAssociatedTokenAddressSync(usdcMint, toPubkey);

        const transaction = new solanaWeb3.Transaction();
        
        // Check if the receiver's token account exists, if not, create it.
        try {
            await getAccount(connection, toTokenAccountAddress);
        } catch (error) {
            if (error instanceof TokenAccountNotFoundError || error instanceof TokenInvalidAccountOwnerError) {
                transaction.add(
                    createAssociatedTokenAccountInstruction(
                        fromPubkey,
                        toTokenAccountAddress,
                        toPubkey,
                        usdcMint
                    )
                );
            } else {
                throw error;
            }
        }

        transaction.add(
            createTransferInstruction(
                fromTokenAccountAddress,
                toTokenAccountAddress,
                fromPubkey,
                prepareData.total_amount * 1000000 // USDC has 6 decimals
            )
        );

        transaction.feePayer = fromPubkey;
        transaction.recentBlockhash = (await connection.getLatestBlockhash()).blockhash;

        const { signature } = await window.solana.signAndSendTransaction(transaction);
        await connection.confirmTransaction(signature);

        return signature;
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

// 导出给其他脚本使用
window.PurchaseHandler = PurchaseHandler;
