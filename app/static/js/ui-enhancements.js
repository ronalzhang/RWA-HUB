/**
 * UI增强和用户体验优化
 * UI Enhancements and User Experience Optimizations
 */

class UIEnhancer {
    constructor() {
        this.isLoading = false;
        this.toastContainer = null;
        this.progressBar = null;
        this.walletStatus = 'disconnected';
        
        this.init();
    }
    
    init() {
        this.createToastContainer();
        this.createProgressBar();
        this.setupMobileNavigation();
        this.setupLoadingStates();
        this.setupWalletStatus();
        this.setupAccessibility();
        this.setupPerformanceMonitoring();
        
        console.log('🚀 UI Enhancer initialized');
    }
    
    // 创建通知容器
    createToastContainer() {
        if (!document.getElementById('toast-container')) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'toast-container';
            this.toastContainer.style.cssText = `
                position: fixed;
                top: 100px;
                right: 20px;
                z-index: 9999;
                pointer-events: none;
            `;
            document.body.appendChild(this.toastContainer);
        } else {
            this.toastContainer = document.getElementById('toast-container');
        }
    }
    
    // 创建进度条
    createProgressBar() {
        if (!document.getElementById('progress-indicator')) {
            this.progressBar = document.createElement('div');
            this.progressBar.id = 'progress-indicator';
            this.progressBar.className = 'progress-indicator';
            this.progressBar.innerHTML = '<div class="progress-bar"></div>';
            this.progressBar.style.display = 'none';
            document.body.appendChild(this.progressBar);
        } else {
            this.progressBar = document.getElementById('progress-indicator');
        }
    }
    
    // 设置移动端导航
    setupMobileNavigation() {
        // 创建移动端导航切换按钮
        const navbar = document.querySelector('.cyberpunk-nav .container');
        if (navbar && !document.querySelector('.mobile-nav-toggle')) {
            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'mobile-nav-toggle';
            toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
            toggleBtn.setAttribute('aria-label', 'Toggle navigation menu');
            
            // 创建移动端菜单
            const mobileMenu = document.createElement('div');
            mobileMenu.className = 'mobile-nav-menu';
            mobileMenu.innerHTML = `
                <a href="#assets" class="nav-link">资产市场</a>
                <a href="#features" class="nav-link">系统特性</a>
                <a href="#about" class="nav-link">关于我们</a>
                <a href="#contact" class="nav-link">联系我们</a>
            `;
            
            // 添加到导航栏
            const navContent = navbar.querySelector('.d-flex');
            if (navContent) {
                navContent.appendChild(toggleBtn);
            }
            document.body.appendChild(mobileMenu);
            
            // 切换菜单显示
            toggleBtn.addEventListener('click', () => {
                mobileMenu.classList.toggle('active');
                toggleBtn.innerHTML = mobileMenu.classList.contains('active') 
                    ? '<i class="fas fa-times"></i>' 
                    : '<i class="fas fa-bars"></i>';
            });
            
            // 点击菜单项关闭菜单
            mobileMenu.addEventListener('click', (e) => {
                if (e.target.classList.contains('nav-link')) {
                    mobileMenu.classList.remove('active');
                    toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
                }
            });
            
            // 点击外部关闭菜单
            document.addEventListener('click', (e) => {
                if (!navbar.contains(e.target) && !mobileMenu.contains(e.target)) {
                    mobileMenu.classList.remove('active');
                    toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
                }
            });
        }
    }
    
    // 设置加载状态
    setupLoadingStates() {
        // 为所有按钮添加加载状态
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-cyber-primary, .btn-cyber-secondary')) {
                this.showButtonLoading(e.target);
            }
        });
        
        // 页面加载时显示骨架屏
        if (document.readyState === 'loading') {
            this.showSkeletonScreen();
        }
    }
    
    // 显示按钮加载状态
    showButtonLoading(button) {
        if (button.classList.contains('loading')) return;
        
        const originalText = button.innerHTML;
        button.classList.add('loading');
        button.disabled = true;
        button.innerHTML = '<div class="cyber-loading" style="width: 20px; height: 20px; margin-right: 8px;"></div>处理中...';
        
        // 模拟加载完成
        setTimeout(() => {
            button.classList.remove('loading');
            button.disabled = false;
            button.innerHTML = originalText;
        }, 2000);
    }
    
    // 显示骨架屏
    showSkeletonScreen() {
        const assetGrid = document.querySelector('.cyber-asset-grid');
        if (assetGrid && assetGrid.children.length === 0) {
            for (let i = 0; i < 6; i++) {
                const skeleton = document.createElement('div');
                skeleton.className = 'cyber-asset-card-enhanced loading-skeleton';
                skeleton.innerHTML = `
                    <div class="skeleton-image loading-skeleton"></div>
                    <div style="padding: 1.5rem;">
                        <div class="skeleton-text large loading-skeleton"></div>
                        <div class="skeleton-text loading-skeleton"></div>
                        <div class="skeleton-text small loading-skeleton"></div>
                        <div style="margin-top: 1rem;">
                            <div class="skeleton-button loading-skeleton"></div>
                        </div>
                    </div>
                `;
                assetGrid.appendChild(skeleton);
            }
            
            // 移除骨架屏
            setTimeout(() => {
                const skeletons = document.querySelectorAll('.loading-skeleton');
                skeletons.forEach(skeleton => skeleton.remove());
            }, 3000);
        }
    }
    
    // 设置钱包状态
    setupWalletStatus() {
        const connectBtn = document.getElementById('connectWalletBtn');
        if (connectBtn) {
            // 创建状态指示器
            const statusIndicator = document.createElement('div');
            statusIndicator.className = 'wallet-status disconnected';
            statusIndicator.innerHTML = `
                <div class="wallet-status-dot"></div>
                <span>未连接</span>
            `;
            
            // 插入到按钮前面
            connectBtn.parentNode.insertBefore(statusIndicator, connectBtn);
            
            // 监听钱包连接事件
            connectBtn.addEventListener('click', () => {
                this.updateWalletStatus('connecting');
                
                // 模拟连接过程
                setTimeout(() => {
                    this.updateWalletStatus('connected');
                    this.showToast('钱包连接成功！', 'success');
                }, 2000);
            });
        }
    }
    
    // 更新钱包状态
    updateWalletStatus(status) {
        this.walletStatus = status;
        const statusIndicator = document.querySelector('.wallet-status');
        if (statusIndicator) {
            statusIndicator.className = `wallet-status ${status}`;
            
            const statusText = {
                'disconnected': '未连接',
                'connecting': '连接中...',
                'connected': '已连接'
            };
            
            statusIndicator.querySelector('span').textContent = statusText[status];
        }
    }
    
    // 设置无障碍功能
    setupAccessibility() {
        // 键盘导航支持
        document.addEventListener('keydown', (e) => {
            // Tab键导航增强
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
            
            // ESC键关闭模态框和菜单
            if (e.key === 'Escape') {
                const mobileMenu = document.querySelector('.mobile-nav-menu.active');
                if (mobileMenu) {
                    mobileMenu.classList.remove('active');
                    document.querySelector('.mobile-nav-toggle').innerHTML = '<i class="fas fa-bars"></i>';
                }
            }
        });
        
        // 鼠标点击时移除键盘导航样式
        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
        
        // 为交互元素添加焦点样式
        const interactiveElements = document.querySelectorAll('button, a, input, select, textarea');
        interactiveElements.forEach(element => {
            element.addEventListener('focus', () => {
                if (document.body.classList.contains('keyboard-navigation')) {
                    element.classList.add('focus-visible');
                }
            });
            
            element.addEventListener('blur', () => {
                element.classList.remove('focus-visible');
            });
        });
    }
    
    // 性能监控
    setupPerformanceMonitoring() {
        // 监控页面加载性能
        window.addEventListener('load', () => {
            if ('performance' in window) {
                const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
                console.log(`📊 Page load time: ${loadTime}ms`);
                
                // 如果加载时间过长，显示提示
                if (loadTime > 3000) {
                    this.showToast('页面加载较慢，正在优化中...', 'warning');
                }
            }
        });
        
        // 监控内存使用
        if ('memory' in performance) {
            setInterval(() => {
                const memory = performance.memory;
                const usedMB = Math.round(memory.usedJSHeapSize / 1048576);
                const limitMB = Math.round(memory.jsHeapSizeLimit / 1048576);
                
                if (usedMB > limitMB * 0.8) {
                    console.warn(`⚠️ High memory usage: ${usedMB}MB / ${limitMB}MB`);
                }
            }, 30000);
        }
    }
    
    // 显示通知
    showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `status-toast ${type}`;
        toast.style.pointerEvents = 'auto';
        
        const icons = {
            'success': 'fas fa-check-circle',
            'error': 'fas fa-exclamation-circle',
            'warning': 'fas fa-exclamation-triangle',
            'info': 'fas fa-info-circle'
        };
        
        toast.innerHTML = `
            <i class="${icons[type]} toast-icon"></i>
            <span>${message}</span>
            <button class="toast-close" aria-label="关闭通知">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // 显示动画
        setTimeout(() => toast.classList.add('show'), 100);
        
        // 关闭按钮事件
        toast.querySelector('.toast-close').addEventListener('click', () => {
            this.hideToast(toast);
        });
        
        // 自动关闭
        if (duration > 0) {
            setTimeout(() => this.hideToast(toast), duration);
        }
        
        return toast;
    }
    
    // 隐藏通知
    hideToast(toast) {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }
    
    // 显示进度条
    showProgress(progress = 0) {
        if (this.progressBar) {
            this.progressBar.style.display = 'block';
            const bar = this.progressBar.querySelector('.progress-bar');
            bar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }
    }
    
    // 隐藏进度条
    hideProgress() {
        if (this.progressBar) {
            setTimeout(() => {
                this.progressBar.style.display = 'none';
            }, 500);
        }
    }
    
    // 添加交互反馈
    addInteractiveFeedback(element) {
        element.classList.add('interactive-element');
        
        element.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const ripple = document.createElement('div');
            ripple.style.cssText = `
                position: absolute;
                left: ${x}px;
                top: ${y}px;
                width: 0;
                height: 0;
                background: rgba(0, 255, 255, 0.3);
                border-radius: 50%;
                transform: translate(-50%, -50%);
                animation: ripple-effect 0.6s ease-out;
                pointer-events: none;
                z-index: 1000;
            `;
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                if (ripple.parentNode) {
                    ripple.parentNode.removeChild(ripple);
                }
            }, 600);
        });
    }
    
    // 懒加载图片
    setupLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            images.forEach(img => imageObserver.observe(img));
        } else {
            // 降级处理
            images.forEach(img => {
                img.src = img.dataset.src;
            });
        }
    }
    
    // 平滑滚动
    setupSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
    
    // 检测设备类型
    detectDevice() {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isTablet = /iPad|Android(?!.*Mobile)/i.test(navigator.userAgent);
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        
        document.body.classList.toggle('mobile-device', isMobile);
        document.body.classList.toggle('tablet-device', isTablet);
        document.body.classList.toggle('touch-device', isTouchDevice);
        
        return { isMobile, isTablet, isTouchDevice };
    }
    
    // 网络状态监控
    setupNetworkMonitoring() {
        if ('navigator' in window && 'onLine' in navigator) {
            const updateOnlineStatus = () => {
                if (navigator.onLine) {
                    this.showToast('网络连接已恢复', 'success', 3000);
                } else {
                    this.showToast('网络连接已断开', 'error', 0);
                }
            };
            
            window.addEventListener('online', updateOnlineStatus);
            window.addEventListener('offline', updateOnlineStatus);
        }
    }
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple-effect {
        to {
            width: 300px;
            height: 300px;
            opacity: 0;
        }
    }
    
    .keyboard-navigation *:focus {
        outline: 2px solid var(--cyber-primary) !important;
        outline-offset: 2px !important;
    }
    
    .lazy {
        opacity: 0;
        transition: opacity 0.3s;
    }
    
    .lazy.loaded {
        opacity: 1;
    }
`;
document.head.appendChild(style);

// 初始化UI增强器
document.addEventListener('DOMContentLoaded', () => {
    window.uiEnhancer = new UIEnhancer();
    
    // 设置设备检测
    const device = window.uiEnhancer.detectDevice();
    console.log('📱 Device detected:', device);
    
    // 设置懒加载
    window.uiEnhancer.setupLazyLoading();
    
    // 设置平滑滚动
    window.uiEnhancer.setupSmoothScrolling();
    
    // 设置网络监控
    window.uiEnhancer.setupNetworkMonitoring();
    
    // 为所有按钮添加交互反馈
    document.querySelectorAll('.btn-cyber-primary, .btn-cyber-secondary, .cyber-asset-card-enhanced').forEach(element => {
        window.uiEnhancer.addInteractiveFeedback(element);
    });
});

// 导出给全局使用
window.UIEnhancer = UIEnhancer;