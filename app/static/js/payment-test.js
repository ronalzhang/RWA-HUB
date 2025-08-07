
// 资产创建支付测试脚本
(function() {
    'use strict';
    
    // 测试支付配置获取
    async function testPaymentConfig() {
        try {
            console.log('测试支付配置获取...');
            
            const response = await fetch('/api/service/config/payment_settings');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const config = await response.json();
            console.log('支付配置:', config);
            
            if (config.asset_creation_fee_address && config.creation_fee) {
                console.log('✓ 支付配置正常');
                return true;
            } else {
                console.error('✗ 支付配置不完整');
                return false;
            }
        } catch (error) {
            console.error('✗ 支付配置获取失败:', error);
            return false;
        }
    }
    
    // 测试代币符号生成
    async function testTokenSymbolGeneration() {
        try {
            console.log('测试代币符号生成...');
            
            const response = await fetch('/api/assets/generate-token-symbol', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ type: '10' })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log('代币符号生成结果:', data);
            
            if (data.success && data.token_symbol) {
                console.log('✓ 代币符号生成正常');
                return true;
            } else {
                console.error('✗ 代币符号生成失败');
                return false;
            }
        } catch (error) {
            console.error('✗ 代币符号生成测试失败:', error);
            return false;
        }
    }
    
    // 运行所有测试
    async function runAllTests() {
        console.log('开始运行资产创建支付测试...');
        
        const configTest = await testPaymentConfig();
        const tokenTest = await testTokenSymbolGeneration();
        
        if (configTest && tokenTest) {
            console.log('🎉 所有测试通过！资产创建支付流程正常');
        } else {
            console.log('❌ 部分测试失败，请检查配置');
        }
    }
    
    // 导出测试函数到全局
    window.testAssetCreationPayment = runAllTests;
    
    // 如果在控制台中，自动运行测试
    if (typeof window !== 'undefined' && window.location.pathname.includes('/assets/create')) {
        console.log('检测到资产创建页面，可以运行 testAssetCreationPayment() 进行测试');
    }
    
})();
