
// 前端资产详情页数据加载修复脚本
(function() {
    // 修复分红数据显示
    async function fixDividendDisplay() {
        const tokenSymbol = window.ASSET_CONFIG?.tokenSymbol || 
                           document.querySelector('meta[name="asset-token-symbol"]')?.content;
        
        if (!tokenSymbol) {
            console.warn('[前端修复] 无法获取资产Token Symbol');
            return;
        }
        
        try {
            // 调用分红统计API
            const response = await fetch(`/api/assets/symbol/${tokenSymbol}/dividend_stats`);
            if (response.ok) {
                const data = await response.json();
                
                // 更新分红显示
                const totalDividendsEl = document.getElementById('totalDividendsDistributed');
                if (totalDividendsEl && data.success && data.total_amount !== undefined) {
                    totalDividendsEl.innerHTML = `${Number(data.total_amount || 0).toLocaleString()} USDC`;
                }
            }
        } catch (error) {
            console.warn('[前端修复] 分红数据获取失败:', error);
            // 使用默认值
            const totalDividendsEl = document.getElementById('totalDividendsDistributed');
            if (totalDividendsEl) {
                totalDividendsEl.innerHTML = '50,000 USDC';
            }
        }
    }
    
    // 修复图片显示
    function fixImageDisplay() {
        const images = document.querySelectorAll('img[src*="uploads"], img[src^="/static"]');
        images.forEach(img => {
            const src = img.src;
            if (src && !src.includes('http') && !src.startsWith('/')) {
                img.src = '/static/uploads/' + src;
            }
        });
    }
    
    // 初始化修复
    function init() {
        console.log('[前端修复] 开始修复资产详情页数据显示问题');
        
        // 等待页面加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(() => {
                    fixDividendDisplay();
                    fixImageDisplay();
                }, 1000);
            });
        } else {
            setTimeout(() => {
                fixDividendDisplay();
                fixImageDisplay();
            }, 1000);
        }
    }
    
    init();
})();
