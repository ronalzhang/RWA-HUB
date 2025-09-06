/**
 * 钱包连接功能测试脚本
 * 用于验证新的钱包管理系统是否正常工作
 */

(function() {
    'use strict';

    console.log('🧪 钱包连接测试脚本已加载');

    // 测试配置
    const TEST_CONFIG = {
        timeout: 10000, // 10秒超时
        retryCount: 3,
        debug: true
    };

    // 测试结果收集器
    const testResults = {
        passed: 0,
        failed: 0,
        tests: []
    };

    // 日志函数
    function log(message, type = 'info') {
        const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
        console.log(`${prefix} [钱包测试] ${message}`);
    }

    // 测试函数
    async function runTest(testName, testFunction) {
        log(`开始测试: ${testName}`);
        
        try {
            const result = await Promise.race([
                testFunction(),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('测试超时')), TEST_CONFIG.timeout)
                )
            ]);
            
            testResults.passed++;
            testResults.tests.push({ name: testName, status: 'passed', result });
            log(`测试通过: ${testName}`, 'success');
            return result;
            
        } catch (error) {
            testResults.failed++;
            testResults.tests.push({ name: testName, status: 'failed', error: error.message });
            log(`测试失败: ${testName} - ${error.message}`, 'error');
            return null;
        }
    }

    // 测试1: 检查钱包管理器是否加载
    async function testWalletManagerLoaded() {
        if (!window.walletManager) {
            throw new Error('walletManager 未加载');
        }
        
        if (typeof window.walletManager.init !== 'function') {
            throw new Error('walletManager.init 方法不存在');
        }
        
        return 'walletManager 已正确加载';
    }

    // 测试2: 检查兼容性接口
    async function testCompatibilityInterface() {
        if (!window.walletState) {
            throw new Error('walletState 兼容性接口未加载');
        }
        
        const requiredMethods = ['connect', 'disconnect', 'openWalletSelector'];
        for (const method of requiredMethods) {
            if (typeof window.walletState[method] !== 'function') {
                throw new Error(`walletState.${method} 方法不存在`);
            }
        }
        
        return '兼容性接口正常';
    }

    // 测试3: 检查移动端增强器（仅移动端）
    async function testMobileEnhancer() {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        if (!isMobile) {
            return '非移动端设备，跳过移动端增强器测试';
        }
        
        if (!window.mobileWalletEnhancer) {
            throw new Error('移动端钱包增强器未加载');
        }
        
        return '移动端增强器已加载';
    }

    // 测试4: 钱包管理器初始化
    async function testWalletManagerInit() {
        const result = await window.walletManager.init();
        
        if (!result) {
            throw new Error('钱包管理器初始化失败');
        }
        
        if (!window.walletManager.state.initialized) {
            throw new Error('钱包管理器状态未正确设置');
        }
        
        return '钱包管理器初始化成功';
    }

    // 测试5: 钱包选择器创建
    async function testWalletSelector() {
        // 测试打开钱包选择器
        const selector = window.walletManager.openWalletSelector();
        
        if (!selector) {
            throw new Error('钱包选择器创建失败');
        }
        
        // 检查选择器是否在DOM中
        const selectorInDOM = document.getElementById('walletSelector');
        if (!selectorInDOM) {
            throw new Error('钱包选择器未添加到DOM');
        }
        
        // 关闭选择器
        const closed = window.walletManager.closeWalletSelector();
        if (!closed) {
            throw new Error('钱包选择器关闭失败');
        }
        
        return '钱包选择器功能正常';
    }

    // 测试6: 钱包检测
    async function testWalletDetection() {
        const detectedWallets = [];
        
        // 检测Phantom
        if (window.solana && window.solana.isPhantom) {
            detectedWallets.push('Phantom');
        }
        
        // 检测MetaMask
        if (window.ethereum && window.ethereum.isMetaMask) {
            detectedWallets.push('MetaMask');
        }
        
        // 检测其他以太坊钱包
        if (window.ethereum && !window.ethereum.isMetaMask) {
            detectedWallets.push('其他以太坊钱包');
        }
        
        return `检测到钱包: ${detectedWallets.length > 0 ? detectedWallets.join(', ') : '无'}`;
    }

    // 测试7: 状态管理
    async function testStateManagement() {
        const initialState = window.walletManager.getState();
        
        if (!initialState) {
            throw new Error('无法获取钱包状态');
        }
        
        // 检查必要的状态属性
        const requiredProps = ['address', 'walletType', 'connected', 'connecting'];
        for (const prop of requiredProps) {
            if (!(prop in initialState)) {
                throw new Error(`状态缺少必要属性: ${prop}`);
            }
        }
        
        return '状态管理正常';
    }

    // 测试8: 事件系统
    async function testEventSystem() {
        let eventReceived = false;
        
        // 添加状态变化监听器
        const testCallback = (state) => {
            eventReceived = true;
        };
        
        window.walletManager.onStateChange(testCallback);
        
        // 触发状态变化（模拟）
        window.walletManager.notifyStateChange();
        
        // 等待事件
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // 移除监听器
        window.walletManager.offStateChange(testCallback);
        
        if (!eventReceived) {
            throw new Error('状态变化事件未触发');
        }
        
        return '事件系统正常';
    }

    // 测试9: 地址格式化
    async function testAddressFormatting() {
        const testAddress = '1234567890abcdef1234567890abcdef12345678';
        const formatted = window.walletManager.formatAddress(testAddress);
        
        if (!formatted || formatted === testAddress) {
            throw new Error('地址格式化失败');
        }
        
        if (!formatted.includes('...')) {
            throw new Error('地址格式化格式不正确');
        }
        
        return `地址格式化正常: ${formatted}`;
    }

    // 测试10: 移动端深度链接构建（仅移动端）
    async function testMobileDeepLinks() {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        if (!isMobile) {
            return '非移动端设备，跳过深度链接测试';
        }
        
        if (!window.mobileWalletEnhancer) {
            throw new Error('移动端增强器未加载');
        }
        
        // 测试深度链接构建（不实际跳转）
        const phantomParams = window.mobileWalletEnhancer.buildConnectionParams('phantom');
        const phantomDeepLink = window.mobileWalletEnhancer.buildDeepLinkUrl('phantom', phantomParams);
        
        if (!phantomDeepLink || !phantomDeepLink.startsWith('phantom://')) {
            throw new Error('Phantom深度链接构建失败');
        }
        
        return `深度链接构建正常: ${phantomDeepLink.substring(0, 50)}...`;
    }

    // 运行所有测试
    async function runAllTests() {
        log('🚀 开始钱包连接功能测试');
        log('=' * 50);
        
        const tests = [
            ['钱包管理器加载检查', testWalletManagerLoaded],
            ['兼容性接口检查', testCompatibilityInterface],
            ['移动端增强器检查', testMobileEnhancer],
            ['钱包管理器初始化', testWalletManagerInit],
            ['钱包选择器功能', testWalletSelector],
            ['钱包检测功能', testWalletDetection],
            ['状态管理功能', testStateManagement],
            ['事件系统功能', testEventSystem],
            ['地址格式化功能', testAddressFormatting],
            ['移动端深度链接', testMobileDeepLinks]
        ];
        
        for (const [testName, testFunction] of tests) {
            await runTest(testName, testFunction);
            // 测试间隔
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        // 输出测试结果
        log('=' * 50);
        log(`测试完成! 通过: ${testResults.passed}, 失败: ${testResults.failed}`);
        
        if (testResults.failed > 0) {
            log('失败的测试:', 'error');
            testResults.tests
                .filter(test => test.status === 'failed')
                .forEach(test => log(`  - ${test.name}: ${test.error}`, 'error'));
        }
        
        // 返回测试结果
        return testResults;
    }

    // 创建测试按钮（开发环境）
    function createTestButton() {
        if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            return; // 只在开发环境显示
        }
        
        const button = document.createElement('button');
        button.textContent = '🧪 测试钱包功能';
        button.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 10000;
            padding: 10px 15px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        `;
        
        button.onclick = async () => {
            button.disabled = true;
            button.textContent = '测试中...';
            
            try {
                await runAllTests();
            } finally {
                button.disabled = false;
                button.textContent = '🧪 测试钱包功能';
            }
        };
        
        document.body.appendChild(button);
    }

    // 自动运行测试（开发环境）
    function autoRunTests() {
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            setTimeout(() => {
                log('自动运行钱包功能测试...');
                runAllTests();
            }, 2000);
        }
    }

    // 暴露测试函数到全局
    window.walletTest = {
        runAllTests,
        runTest,
        testResults
    };

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            createTestButton();
            autoRunTests();
        });
    } else {
        createTestButton();
        autoRunTests();
    }

    log('钱包测试脚本初始化完成');

})();