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
                                // Execute purchase using the consolidated flow
                                const assetId = document.querySelector('meta[name="asset-id"]')?.content || window.ASSET_CONFIG?.id;
                                if (window.completePurchaseFlow && typeof window.completePurchaseFlow.initiatePurchase === 'function') {
                                    console.log('调用完整购买流程');
                                    window.completePurchaseFlow.initiatePurchase(parseInt(assetId), amount);
                                } else {
                                    console.error('completePurchaseFlow 不可用');
                                    Swal.fire({
                                        title: '系统错误',
                                        text: '购买功能暂时不可用，请刷新页面重试',
                                        icon: 'error',
                                        confirmButtonText: '确定'
                                    });
                                }
                            }
                        });
                    } else {
                        // 如果没有SweetAlert，使用原生确认对话框
                        const confirmed = confirm(`您确定要购买 ${amount} 个代币吗？`);
                        if (confirmed) {
                            const assetId = document.querySelector('meta[name="asset-id"]')?.content || window.ASSET_CONFIG?.id;
                            if (window.completePurchaseFlow && typeof window.completePurchaseFlow.initiatePurchase === 'function') {
                                console.log('调用完整购买流程');
                                window.completePurchaseFlow.initiatePurchase(parseInt(assetId), amount);
                            } else {
                                console.error('completePurchaseFlow 不可用');
                                alert('购买功能暂时不可用，请刷新页面重试');
                            }
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



