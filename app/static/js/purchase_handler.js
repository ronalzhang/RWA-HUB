// Main entry point for purchase logic on the asset detail page.
document.addEventListener('DOMContentLoaded', function() {
    const buyButton = document.getElementById('buy-button');
    if (buyButton) {
        buyButton.addEventListener('click', function() {
            // Check wallet connection
            if (!window.walletState || !window.walletState.address) {
                showError('请先连接您的钱包再进行购买。');
                return;
            }

            // Get purchase amount
            const amount = document.getElementById('purchase-amount').value;
            if (!amount || amount <= 0) {
                showError('请输入有效的购买数量。');
                return;
            }

            // Show confirmation dialog
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
                    const assetId = document.querySelector('meta[name="asset-id"]').content;
                    window.completePurchaseFlow.initiatePurchase(assetId, amount);
                }
            });
        });
    }
});



