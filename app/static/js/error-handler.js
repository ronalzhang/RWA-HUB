/**
 * 前端统一错误处理工具
 * 提供统一的错误显示和处理功能
 */

class ErrorHandler {
    constructor() {
        this.errorCodes = {
            // 认证相关错误
            1001: '钱包未连接',
            1002: '无效的钱包地址',
            1003: '需要身份验证',
            1004: '管理员权限不足',
            1005: '令牌已过期',
            1006: '无效的令牌',
            
            // 验证相关错误
            1101: '数据验证失败',
            1102: '缺少必填字段',
            1103: '数据格式错误',
            1104: '请求必须是JSON格式',
            1105: '请求体不能为空',
            
            // 业务逻辑错误
            1201: '余额不足',
            1202: '资产不存在',
            1203: '交易记录不存在',
            1204: '用户不存在',
            1205: '资产不可用',
            1206: '可售数量不足',
            
            // 支付相关错误
            1301: '支付失败',
            1302: '支付超时',
            1303: '无效的支付金额',
            1304: '支付已处理',
            
            // 区块链相关错误
            1401: '区块链操作失败',
            1402: '交易失败',
            1403: '网络连接错误',
            1404: '智能合约错误',
            
            // 系统错误
            1501: '数据库操作失败',
            1502: '服务器内部错误',
            1503: '服务暂时不可用',
            1504: '请求频率超限',
            
            // 权限相关错误
            1601: '权限不足',
            1602: '资源访问被拒绝',
            1603: '操作不被允许'
        };
        
        this.init();
    }
    
    init() {
        // 绑定全局错误处理
        window.addEventListener('unhandledrejection', (event) => {
            this.handlePromiseRejection(event);
        });
        
        // 创建错误显示容器
        this.createErrorContainer();
    }
    
    createErrorContainer() {
        // 检查是否已存在错误容器
        if (document.getElementById('error-container')) {
            return;
        }
        
        const container = document.createElement('div');
        container.id = 'error-container';
        container.className = 'error-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            max-width: 400px;
        `;
        
        document.body.appendChild(container);
    }
    
    /**
     * 处理API响应错误
     * @param {Object} error - 错误对象
     * @param {Object} options - 选项
     */
    handleApiError(error, options = {}) {
        const {
            showToast = true,
            showModal = false,
            callback = null,
            context = null
        } = options;
        
        let errorInfo = this.parseError(error);
        
        // 记录错误日志
        console.error('API错误:', errorInfo);
        
        // 显示错误信息
        if (showToast) {
            this.showErrorToast(errorInfo);
        }
        
        if (showModal) {
            this.showErrorModal(errorInfo);
        }
        
        // 执行回调
        if (callback && typeof callback === 'function') {
            callback(errorInfo, context);
        }
        
        // 特殊错误处理
        this.handleSpecialErrors(errorInfo);
        
        return errorInfo;
    }
    
    /**
     * 解析错误对象
     * @param {Object} error - 错误对象
     */
    parseError(error) {
        let errorInfo = {
            code: 9999,
            type: 'UNKNOWN_ERROR',
            message: '未知错误',
            field: null,
            details: null,
            timestamp: new Date().toISOString()
        };
        
        // 处理不同类型的错误
        if (error.response) {
            // HTTP响应错误
            const data = error.response.data;
            if (data && data.error) {
                errorInfo = {
                    code: data.error.code || 9999,
                    type: data.error.type || 'HTTP_ERROR',
                    message: data.error.message || '请求失败',
                    field: data.error.field || null,
                    details: data.error.details || null,
                    timestamp: data.error.timestamp || new Date().toISOString(),
                    httpStatus: error.response.status
                };
            } else {
                errorInfo.message = `HTTP ${error.response.status}: ${error.response.statusText}`;
                errorInfo.httpStatus = error.response.status;
            }
        } else if (error.message) {
            // JavaScript错误
            errorInfo.message = error.message;
            errorInfo.type = 'JAVASCRIPT_ERROR';
        } else if (typeof error === 'string') {
            // 字符串错误
            errorInfo.message = error;
        }
        
        return errorInfo;
    }
    
    /**
     * 显示错误Toast
     * @param {Object} errorInfo - 错误信息
     */
    showErrorToast(errorInfo) {
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.style.cssText = `
            background: linear-gradient(135deg, #ff6b6b, #ee5a52);
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
            border-left: 4px solid #ff4757;
            animation: slideInRight 0.3s ease-out;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        `;
        
        // 添加动画样式
        if (!document.getElementById('error-toast-styles')) {
            const style = document.createElement('style');
            style.id = 'error-toast-styles';
            style.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                .error-toast:hover {
                    transform: translateX(-5px);
                    transition: transform 0.2s ease;
                }
            `;
            document.head.appendChild(style);
        }
        
        // 构建错误内容
        let content = `
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="flex: 1;">
                    <div style="font-weight: 600; margin-bottom: 4px;">
                        ${this.getErrorTitle(errorInfo)}
                    </div>
                    <div style="font-size: 14px; opacity: 0.9;">
                        ${errorInfo.message}
                    </div>
                </div>
                <div style="margin-left: 12px; cursor: pointer; font-size: 18px; opacity: 0.7; hover: opacity: 1;">
                    ×
                </div>
            </div>
        `;
        
        // 添加字段信息
        if (errorInfo.field) {
            content += `<div style="font-size: 12px; margin-top: 8px; opacity: 0.8;">字段: ${errorInfo.field}</div>`;
        }
        
        toast.innerHTML = content;
        
        // 添加关闭功能
        toast.addEventListener('click', () => {
            this.removeToast(toast);
        });
        
        // 自动关闭
        setTimeout(() => {
            if (toast.parentNode) {
                this.removeToast(toast);
            }
        }, 5000);
        
        // 添加到容器
        const container = document.getElementById('error-container');
        container.appendChild(toast);
    }
    
    /**
     * 移除Toast
     * @param {Element} toast - Toast元素
     */
    removeToast(toast) {
        toast.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }
    
    /**
     * 显示错误模态框
     * @param {Object} errorInfo - 错误信息
     */
    showErrorModal(errorInfo) {
        // 创建模态框
        const modal = document.createElement('div');
        modal.className = 'error-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10001;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: white;
            padding: 24px;
            border-radius: 12px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        `;
        
        modalContent.innerHTML = `
            <div style="display: flex; align-items: center; margin-bottom: 16px;">
                <div style="width: 40px; height: 40px; background: #ff6b6b; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                    <span style="color: white; font-size: 20px;">!</span>
                </div>
                <h3 style="margin: 0; color: #333;">${this.getErrorTitle(errorInfo)}</h3>
            </div>
            <div style="margin-bottom: 16px; color: #666; line-height: 1.5;">
                ${errorInfo.message}
            </div>
            ${errorInfo.field ? `<div style="margin-bottom: 16px; font-size: 14px; color: #888;">相关字段: ${errorInfo.field}</div>` : ''}
            ${errorInfo.details ? `<div style="margin-bottom: 16px; font-size: 14px; color: #888;">详细信息: ${JSON.stringify(errorInfo.details)}</div>` : ''}
            <div style="text-align: right;">
                <button id="error-modal-close" style="
                    background: #ff6b6b;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                ">确定</button>
            </div>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // 绑定关闭事件
        const closeBtn = modal.querySelector('#error-modal-close');
        const closeModal = () => {
            document.body.removeChild(modal);
        };
        
        closeBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
    
    /**
     * 获取错误标题
     * @param {Object} errorInfo - 错误信息
     */
    getErrorTitle(errorInfo) {
        const titles = {
            'VALIDATION_ERROR': '验证错误',
            'AUTH_REQUIRED': '需要登录',
            'ADMIN_ACCESS_DENIED': '权限不足',
            'ASSET_NOT_FOUND': '资产不存在',
            'PAYMENT_FAILED': '支付失败',
            'BLOCKCHAIN_ERROR': '区块链错误',
            'DATABASE_ERROR': '数据库错误',
            'INTERNAL_ERROR': '系统错误'
        };
        
        return titles[errorInfo.type] || '错误';
    }
    
    /**
     * 处理特殊错误
     * @param {Object} errorInfo - 错误信息
     */
    handleSpecialErrors(errorInfo) {
        switch (errorInfo.type) {
            case 'AUTH_REQUIRED':
                // 需要登录，跳转到登录页面或显示连接钱包提示
                if (typeof window.connectWallet === 'function') {
                    setTimeout(() => {
                        if (confirm('需要连接钱包才能继续操作，是否立即连接？')) {
                            window.connectWallet();
                        }
                    }, 1000);
                }
                break;
                
            case 'ADMIN_ACCESS_DENIED':
                // 管理员权限不足，可能需要跳转
                setTimeout(() => {
                    if (window.location.pathname.includes('/admin/')) {
                        window.location.href = '/';
                    }
                }, 2000);
                break;
                
            case 'RATE_LIMIT_EXCEEDED':
                // 请求频率超限，暂时禁用相关按钮
                this.disableButtons(5000);
                break;
        }
    }
    
    /**
     * 暂时禁用按钮
     * @param {number} duration - 禁用时长（毫秒）
     */
    disableButtons(duration) {
        const buttons = document.querySelectorAll('button[type="submit"], .btn-primary');
        buttons.forEach(btn => {
            btn.disabled = true;
            const originalText = btn.textContent;
            let countdown = Math.ceil(duration / 1000);
            
            const updateText = () => {
                btn.textContent = `请等待 ${countdown}s`;
                countdown--;
                
                if (countdown >= 0) {
                    setTimeout(updateText, 1000);
                } else {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            };
            
            updateText();
        });
    }
    
    /**
     * 处理Promise拒绝
     * @param {Event} event - 未处理的Promise拒绝事件
     */
    handlePromiseRejection(event) {
        console.error('未处理的Promise拒绝:', event.reason);
        
        // 如果是网络错误，显示友好提示
        if (event.reason && event.reason.message && event.reason.message.includes('fetch')) {
            this.showErrorToast({
                code: 1403,
                type: 'NETWORK_ERROR',
                message: '网络连接失败，请检查网络设置',
                timestamp: new Date().toISOString()
            });
        }
    }
    
    /**
     * 清除所有错误提示
     */
    clearAllErrors() {
        const container = document.getElementById('error-container');
        if (container) {
            container.innerHTML = '';
        }
        
        // 移除模态框
        const modals = document.querySelectorAll('.error-modal');
        modals.forEach(modal => {
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
        });
    }
}

// 创建全局错误处理器实例
window.errorHandler = new ErrorHandler();

// 便捷函数
window.showError = function(error, options = {}) {
    return window.errorHandler.handleApiError(error, options);
};

window.clearErrors = function() {
    window.errorHandler.clearAllErrors();
};

// 为axios添加响应拦截器（如果存在）
if (typeof axios !== 'undefined') {
    axios.interceptors.response.use(
        response => response,
        error => {
            window.errorHandler.handleApiError(error);
            return Promise.reject(error);
        }
    );
}

// 为fetch添加错误处理包装器
if (typeof window.fetch !== 'undefined') {
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        return originalFetch.apply(this, args)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        const error = new Error('HTTP Error');
                        error.response = { status: response.status, statusText: response.statusText, data };
                        throw error;
                    }).catch(() => {
                        const error = new Error('HTTP Error');
                        error.response = { status: response.status, statusText: response.statusText, data: {} };
                        throw error;
                    });
                }
                return response;
            })
            .catch(error => {
                if (error.response) {
                    window.errorHandler.handleApiError(error);
                }
                throw error;
            });
    };
}