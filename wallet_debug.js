/**
 * 钱包调试和状态修复脚本
 * 用于解决钱包连接后按钮状态未正确更新的问题
 */

(function() {
    console.log('钱包调试脚本已加载 - v1.0.1');

    /**
     * 修复购买按钮状态的主函数
     */
    function fixBuyButtonState() {
        console.log('执行购买按钮状态修复');
        
        // 获取页面上的购买按钮
        const buyButtons = document.querySelectorAll('.buy-button, #buy-button, [data-role="buy-button"]');
        if (buyButtons.length === 0) {
            console.log('未找到购买按钮，无需修复');
            return;
        }
        
        console.log(`找到 ${buyButtons.length} 个购买按钮`);
        
        // 检查钱包连接状态
        const isWalletConnected = checkWalletConnection();
        console.log('钱包连接状态:', isWalletConnected);
        
        // 更新所有按钮
        buyButtons.forEach(button => {
            updateButtonState(button, isWalletConnected);
        });
    }
    
    /**
     * 全面检查钱包连接状态
     */
    function checkWalletConnection() {
        // 检查多种可能的钱包状态存储位置
        
        // 1. 检查walletState对象
        if (window.walletState && (
            window.walletState.isConnected || 
            window.walletState.connected || 
            window.walletState.address
        )) {
            console.log('通过walletState检测到钱包已连接');
            return true;
        }
        
        // 2. 检查wallet对象
        if (window.wallet && (
            window.wallet.connected ||
            (window.wallet.getAddress && window.wallet.getAddress()) ||
            (window.wallet.getConnectionStatus && window.wallet.getConnectionStatus())
        )) {
            console.log('通过wallet对象检测到钱包已连接');
            return true;
        }
        
        // 3. 检查全局变量
        if (window.connectedWalletAddress || window.ethereumAddress || window.solanaAddress) {
            console.log('通过全局地址变量检测到钱包已连接');
            return true;
        }
        
        // 4. 检查localStorage
        const storedAddress = localStorage.getItem('walletAddress');
        const storedType = localStorage.getItem('walletType');
        if (storedAddress && storedType) {
            console.log('通过localStorage检测到钱包已连接:', storedAddress, storedType);
            
            // 同步钱包状态
            if (window.walletState) {
                window.walletState.connected = true;
                window.walletState.address = storedAddress;
                window.walletState.type = storedType;
            }
            
            return true;
        }
        
        console.log('未检测到已连接的钱包');
        return false;
    }
    
    /**
     * 更新按钮状态
     */
    function updateButtonState(button, isConnected) {
        if (!button) return;
        
        const originalText = button.getAttribute('data-original-text') || button.innerHTML;
        
        // 首次调用时保存原始文本
        if (!button.hasAttribute('data-original-text')) {
            button.setAttribute('data-original-text', originalText);
        }
        
        if (isConnected) {
            button.disabled = false;
            
            // 如果当前显示的是连接钱包的文本，则恢复原始文本
            if (button.innerHTML.includes('Connect Wallet') || button.innerHTML.includes('连接钱包')) {
                button.innerHTML = originalText;
            }
            
            button.removeAttribute('title');
        } else {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-wallet me-2"></i>Connect Wallet';
            button.title = 'Please connect your wallet first';
        }
    }
    
    /**
     * 监听钱包连接事件
     */
    function setupWalletEventListeners() {
        const walletEvents = [
            'walletConnected', 
            'walletDisconnected', 
            'walletStateChanged', 
            'balanceUpdated',
            'addressChanged'
        ];
        
        walletEvents.forEach(eventName => {
            window.addEventListener(eventName, () => {
                console.log(`检测到钱包事件: ${eventName}`);
                // 延迟执行，确保其他钱包脚本已更新状态
                setTimeout(fixBuyButtonState, 300);
            });
        });
        
        console.log('已设置钱包事件监听');
    }
    
    /**
     * 初始化钱包调试修复
     */
    function initWalletDebugFix() {
        console.log('初始化钱包调试修复');
        
        // 设置全局函数，允许其他脚本手动触发修复
        window.fixBuyButtonState = fixBuyButtonState;
        
        // 设置事件监听
        setupWalletEventListeners();
        
        // 初次执行修复
        setTimeout(fixBuyButtonState, 1000);
        
        // 每5秒自动检查一次状态
        setInterval(fixBuyButtonState, 5000);
    }
    
    // 监听DOM加载完成事件
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWalletDebugFix);
    } else {
        // 如果DOM已加载，立即执行
        initWalletDebugFix();
    }
    
    // 监听页面完全加载事件
    window.addEventListener('load', () => {
        console.log('页面完全加载，再次执行修复');
        fixBuyButtonState();
    });
})(); 