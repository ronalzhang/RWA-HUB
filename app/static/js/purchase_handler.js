// Main entry point for purchase logic on the asset detail page.
// 防止重复初始化
if (window.purchaseHandlerInitialized) {
    console.warn('Purchase handler already initialized, skipping...');
} else {
    window.purchaseHandlerInitialized = true;
    
    document.addEventListener('DOMContentLoaded', function() {
        // 延迟初始化，确保其他脚本已加载
        setTimeout(function() {
            const buyButton = document.getElementById('buy-button');
            if (buyButton) {
                console.log('设置购买按钮事件监听器');
                
                // 清除可能存在的旧事件监听器
                const newButton = buyButton.cloneNode(true);
                buyButton.parentNode.replaceChild(newButton, buyButton);
                
                newButton.addEventListener('click', function(event) {
                    event.preventDefault();
                    event.stopPropagation();
                    
                    console.log('购买按钮被点击');
                    
                    // Check wallet connection
                    if (!window.walletState || !window.walletState.address) {
                        // 尝试从其他地方获取钱包地址
                        const walletAddress = localStorage.getItem('walletAddress') || 
                                            (window.solana && window.solana.publicKey ? window.solana.publicKey.toString() : null);
                        
                        if (!walletAddress) {
                            if (typeof Swal !== 'undefined') {
                                Swal.fire({
                                    title: '钱包未连接',
                                    text: '请先连接您的钱包再进行购买',
                                    icon: 'warning',
                                    confirmButtonText: '确定'
                                });
                            } else {
                                alert('请先连接您的钱包再进行购买。');
                            }
                            return;
                        }
                    }

                    // Get purchase amount
                    const amountInput = document.getElementById('purchase-amount');
                    const amount = parseInt(amountInput?.value || 0);
                    if (!amount || amount <= 0) {
                        if (typeof Swal !== 'undefined') {
                            Swal.fire({
                                title: '输入错误',
                                text: '请输入有效的购买数量',
                                icon: 'error',
                                confirmButtonText: '确定'
                            });
                        } else {
                            alert('请输入有效的购买数量。');
                        }
                        amountInput?.focus();
                        return;
                    }

                    // 执行购买逻辑
                    const executePurchase = () => {
                        const assetId = document.querySelector('meta[name="asset-id"]')?.content || 
                                       document.querySelector('[data-asset-id]')?.getAttribute('data-asset-id') ||
                                       window.ASSET_CONFIG?.id;
                        
                        // 检查是否有完整的购买流程
                        if (window.completePurchaseFlow && typeof window.completePurchaseFlow.initiatePurchase === 'function') {
                            console.log('调用完整购买流程');
                            window.completePurchaseFlow.initiatePurchase(parseInt(assetId), amount);
                        } else {
                            console.warn('completePurchaseFlow 不可用，使用简化购买流程');
                            // 简化的购买流程
                            simplePurchaseFlow(parseInt(assetId), amount);
                        }
                    };

                    // Show confirmation dialog
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({
                            title: '确认购买',
                            text: `您确定要购买 ${amount} 个代币吗？`,
                            icon: 'question',
                            showCancelButton: true,
                            confirmButtonText: '确认',
                            cancelButtonText: '取消'
                        }).then((result) => {
                            if (result.isConfirmed) {
                                executePurchase();
                            }
                        });
                    } else {
                        // 如果没有SweetAlert，使用原生确认对话框
                        const confirmed = confirm(`您确定要购买 ${amount} 个代币吗？`);
                        if (confirmed) {
                            executePurchase();
                        }
                    }
                });
                
                console.log('购买按钮事件监听器设置完成');
            } else {
                console.warn('购买按钮不存在');
            }
        }, 200); // 给其他脚本200ms的加载时间
    });
    
    console.log('购买处理器模块已加载');
}

// 简化的购买流程（当完整流程不可用时使用）
function simplePurchaseFlow(assetId, amount) {
    console.log(`开始简化购买流程: 资产ID=${assetId}, 数量=${amount}`);
    
    // 获取钱包地址
    const walletAddress = window.walletState?.address || 
                         localStorage.getItem('walletAddress') || 
                         (window.solana && window.solana.publicKey ? window.solana.publicKey.toString() : null);
    
    if (!walletAddress) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: '钱包未连接',
                text: '请先连接您的钱包',
                icon: 'warning',
                confirmButtonText: '确定'
            });
        } else {
            alert('请先连接您的钱包');
        }
        return;
    }
    
    // 显示处理中状态
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: '处理中...',
            text: '正在创建购买交易',
            icon: 'info',
            allowOutsideClick: false,
            showConfirmButton: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });
    }
    
    // 调用V2交易API创建购买
    fetch('/api/v2/trades/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_address: walletAddress,
            asset_id: assetId,
            amount: amount
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('购买API响应:', data);
        
        if (data.success) {
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: '交易创建成功',
                    text: `交易ID: ${data.trade_id}`,
                    icon: 'success',
                    confirmButtonText: '确定'
                }).then(() => {
                    // 刷新页面显示最新状态
                    window.location.reload();
                });
            } else {
                alert(`交易创建成功！交易ID: ${data.trade_id}`);
                window.location.reload();
            }
        } else {
            throw new Error(data.message || '创建交易失败');
        }
    })
    .catch(error => {
        console.error('购买失败:', error);
        
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: '购买失败',
                text: error.message || '请稍后重试',
                icon: 'error',
                confirmButtonText: '确定'
            });
        } else {
            alert(`购买失败: ${error.message || '请稍后重试'}`);
        }
    });
}



