
// 优化的资产创建页面初始化代码
(function() {
    'use strict';
    
    // 防止重复初始化
    if (window.assetCreatePageOptimized) {
        return;
    }
    window.assetCreatePageOptimized = true;
    
    // 优化的代币符号生成函数
    async function generateTokenSymbolOptimized(type) {
        try {
            console.log('生成代币符号，类型:', type);
            
            const response = await fetch('/api/assets/generate-token-symbol', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ type: type || '10' })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.token_symbol) {
                console.log('生成代币符号成功:', data.token_symbol);
                return data.token_symbol;
            } else {
                throw new Error(data.error || '生成失败');
            }
        } catch (error) {
            console.error('生成代币符号失败:', error);
            
            // 本地备用生成
            const timestamp = Date.now().toString().slice(-6);
            const symbol = `RH-${timestamp}`;
            console.log('使用本地生成的符号:', symbol);
            return symbol;
        }
    }
    
    // 优化的页面初始化
    function initOptimized() {
        console.log('开始优化初始化...');
        
        // 立即检查钱包状态
        if (window.walletState && window.walletState.connected) {
            document.getElementById('walletCheck').style.display = 'none';
            document.getElementById('formContent').style.display = 'block';
        }
        
        // 资产类型变化时生成代币符号
        const typeSelect = document.getElementById('type');
        if (typeSelect) {
            typeSelect.addEventListener('change', async function() {
                const symbol = await generateTokenSymbolOptimized(this.value);
                const symbolInput = document.getElementById('tokensymbol');
                if (symbolInput) {
                    symbolInput.value = symbol;
                }
            });
        }
        
        console.log('优化初始化完成');
    }
    
    // DOM加载完成后立即初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initOptimized);
    } else {
        initOptimized();
    }
    
})();
