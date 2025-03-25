import { API_ENDPOINTS, API_CONFIG, API_VALIDATION, API_RESPONSE_FORMAT } from '../config/api.js';

// API请求参数验证工具
class ApiValidator {
    constructor() {
        this.config = API_CONFIG;
        this.validation = API_VALIDATION;
        this.responseFormat = API_RESPONSE_FORMAT;
        this.endpoints = API_ENDPOINTS;
        
        // 初始化日志
        this.logger = {
            debug: (...args) => this.validation.LOG_LEVEL === 'debug' && console.debug(...args),
            info: (...args) => ['debug', 'info'].includes(this.validation.LOG_LEVEL) && console.info(...args),
            warn: (...args) => ['debug', 'info', 'warn'].includes(this.validation.LOG_LEVEL) && console.warn(...args),
            error: (...args) => console.error(...args)
        };
    }
    
    // 验证请求参数
    validateParams(params, schema) {
        const errors = [];
        
        // 检查必填字段
        for (const [field, rule] of Object.entries(schema)) {
            // 字段是否存在
            if (!(field in params)) {
                if (rule.required !== false) {
                    errors.push(`缺少必填字段: ${field}`);
                }
                continue;
            }
            
            const value = params[field];
            
            // 类型检查
            if (rule.type) {
                const actualType = Array.isArray(value) ? 'array' : typeof value;
                if (actualType !== rule.type) {
                    errors.push(`${field} 必须是 ${rule.type} 类型`);
                    continue;
                }
            }
            
            // 格式检查
            if (rule.format) {
                if (!this.validateFormat(value, rule.format)) {
                    errors.push(`${field} 格式不正确`);
                    continue;
                }
            }
            
            // 枚举值检查
            if (rule.enum && !rule.enum.includes(value)) {
                errors.push(`${field} 必须是以下值之一: ${rule.enum.join(', ')}`);
                continue;
            }
            
            // 范围检查
            if (rule.min !== undefined && value < rule.min) {
                errors.push(`${field} 不能小于 ${rule.min}`);
            }
            if (rule.max !== undefined && value > rule.max) {
                errors.push(`${field} 不能大于 ${rule.max}`);
            }
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }
    
    // 验证响应格式
    validateResponse(response, schema) {
        const errors = [];
        
        // 检查响应状态
        if (response.code !== this.responseFormat.SUCCESS.code) {
            errors.push(`响应状态码错误: ${response.code}`);
            return { isValid: false, errors };
        }
        
        // 检查响应数据
        if (schema) {
            const result = this.validateParams(response.data, schema);
            if (!result.isValid) {
                errors.push(...result.errors);
            }
        }
        
        return {
            isValid: errors.length === 0,
            errors
        };
    }
    
    // 格式验证
    validateFormat(value, format) {
        switch (format) {
            case 'email':
                return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
            case 'url':
                try {
                    new URL(value);
                    return true;
                } catch {
                    return false;
                }
            case 'date':
                return !isNaN(Date.parse(value));
            case 'address':
                return /^(0x)?[0-9a-fA-F]{40}$/.test(value);
            case 'hash':
                return /^0x[0-9a-fA-F]{64}$/.test(value);
            case 'numeric':
                return !isNaN(value) && value.toString().trim() !== '';
            case 'decimal':
                return /^\d*\.?\d*$/.test(value);
            default:
                return true;
        }
    }
    
    // 执行API验证
    async validate() {
        if (!this.validation.ENABLED) {
            this.logger.info('API验证已禁用');
            return { success: true };
        }
        
        const errors = [];
        let retryCount = 0;
        
        while (retryCount < this.validation.RETRY_COUNT) {
            try {
                this.logger.info(`开始第${retryCount + 1}次API验证...`);
                
                // 1. 验证创建交易API
                const createTradeResult = await this.validateCreateTrade();
                if (!createTradeResult.success) {
                    errors.push(...createTradeResult.errors);
                }
                
                // 2. 验证交易历史API
                const tradeHistoryResult = await this.validateTradeHistory();
                if (!tradeHistoryResult.success) {
                    errors.push(...tradeHistoryResult.errors);
                }
                
                // 3. 验证更新交易状态API
                const updateTradeResult = await this.validateUpdateTrade();
                if (!updateTradeResult.success) {
                    errors.push(...updateTradeResult.errors);
                }
                
                // 如果没有错误,验证成功
                if (errors.length === 0) {
                    this.logger.info('API验证通过');
                    return { success: true };
                }
                
                // 如果有错误,重试
                this.logger.warn(`API验证失败,错误:`, errors);
                this.logger.info(`等待${this.validation.RETRY_DELAY}ms后重试...`);
                await new Promise(resolve => setTimeout(resolve, this.validation.RETRY_DELAY));
                retryCount++;
                
            } catch (error) {
                this.logger.error('API验证出错:', error);
                errors.push(error.message);
                retryCount++;
            }
        }
        
        // 所有重试都失败
        this.logger.error('API验证最终失败:', errors);
        return {
            success: false,
            errors
        };
    }
    
    // 验证创建交易API
    async validateCreateTrade() {
        const testData = {
            asset_id: 1,
            amount: "100",
            price: "10.5",
            type: "buy",
            trader_address: "0x1234567890123456789012345678901234567890"
        };
        
        try {
            // 验证请求参数
            const paramSchema = {
                asset_id: { type: 'number', required: true },
                amount: { type: 'string', required: true, format: 'numeric' },
                price: { type: 'string', required: true, format: 'decimal' },
                type: { type: 'string', required: true, enum: ['buy', 'sell'] },
                trader_address: { type: 'string', required: true, format: 'address' }
            };
            
            const paramValidation = this.validateParams(testData, paramSchema);
            if (!paramValidation.isValid) {
                return {
                    success: false,
                    errors: paramValidation.errors
                };
            }
            
            // 发送请求
            const response = await this.sendRequest(
                this.endpoints.CREATE_TRADE,
                'POST',
                testData
            );
            
            // 验证响应
            const responseSchema = {
                id: { type: 'number', required: true },
                status: { type: 'string', required: true, enum: ['pending', 'completed', 'failed'] }
            };
            
            const responseValidation = this.validateResponse(response, responseSchema);
            if (!responseValidation.isValid) {
                return {
                    success: false,
                    errors: responseValidation.errors
                };
            }
            
            return { success: true };
            
        } catch (error) {
            return {
                success: false,
                errors: [`创建交易API验证失败: ${error.message}`]
            };
        }
    }
    
    // 验证交易历史API
    async validateTradeHistory() {
        const params = {
            asset_id: 1,
            page: 1,
            per_page: 5
        };
        
        try {
            // 验证请求参数
            const paramSchema = {
                asset_id: { type: 'number', required: true },
                page: { type: 'number', required: true, min: 1 },
                per_page: { type: 'number', required: true, min: 1, max: 100 }
            };
            
            const paramValidation = this.validateParams(params, paramSchema);
            if (!paramValidation.isValid) {
                return {
                    success: false,
                    errors: paramValidation.errors
                };
            }
            
            // 发送请求
            const response = await this.sendRequest(
                `${this.endpoints.GET_TRADE_HISTORY(params.asset_id, params.page, params.per_page)}`,
                'GET'
            );
            
            // 验证响应
            const responseSchema = {
                trades: { type: 'array', required: true },
                pagination: { type: 'object', required: true }
            };
            
            const responseValidation = this.validateResponse(response, responseSchema);
            if (!responseValidation.isValid) {
                return {
                    success: false,
                    errors: responseValidation.errors
                };
            }
            
            // 验证每条交易记录
            if (Array.isArray(response.data.trades)) {
                const tradeSchema = {
                    id: { type: 'number', required: true },
                    created_at: { type: 'string', required: true, format: 'date' },
                    type: { type: 'string', required: true, enum: ['buy', 'sell'] },
                    amount: { type: 'string', required: true, format: 'numeric' },
                    price: { type: 'string', required: true, format: 'decimal' },
                    status: { type: 'string', required: true }
                };
                
                const errors = [];
                response.data.trades.forEach((trade, index) => {
                    const validation = this.validateParams(trade, tradeSchema);
                    if (!validation.isValid) {
                        errors.push(`第${index + 1}条交易记录验证失败: ${validation.errors.join(', ')}`);
                    }
                });
                
                if (errors.length > 0) {
                    return {
                        success: false,
                        errors
                    };
                }
            }
            
            return { success: true };
            
        } catch (error) {
            return {
                success: false,
                errors: [`交易历史API验证失败: ${error.message}`]
            };
        }
    }
    
    // 验证更新交易状态API
    async validateUpdateTrade() {
        const testData = {
            status: 'completed',
            tx_hash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
            wallet_address: '0x1234567890123456789012345678901234567890'
        };
        
        try {
            // 验证请求参数
            const paramSchema = {
                status: { type: 'string', required: true, enum: ['completed', 'failed'] },
                tx_hash: { type: 'string', required: true, format: 'hash' },
                wallet_address: { type: 'string', required: true, format: 'address' }
            };
            
            const paramValidation = this.validateParams(testData, paramSchema);
            if (!paramValidation.isValid) {
                return {
                    success: false,
                    errors: paramValidation.errors
                };
            }
            
            // 发送请求
            const response = await this.sendRequest(
                this.endpoints.UPDATE_TRADE(1),
                'POST',
                testData
            );
            
            // 验证响应
            const responseSchema = {
                success: { type: 'boolean', required: true }
            };
            
            const responseValidation = this.validateResponse(response, responseSchema);
            if (!responseValidation.isValid) {
                return {
                    success: false,
                    errors: responseValidation.errors
                };
            }
            
            return { success: true };
            
        } catch (error) {
            return {
                success: false,
                errors: [`更新交易状态API验证失败: ${error.message}`]
            };
        }
    }
    
    // 发送API请求
    async sendRequest(endpoint, method, data = null) {
        const url = `${this.config.BASE_URL}${endpoint}`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.config.TIMEOUT);
        
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Api-Version': this.config.API_VERSION
                },
                signal: controller.signal
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            const response = await fetch(url, options);
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            return result;
            
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }
}

// 创建验证器实例
const validator = new ApiValidator();

// 导出验证相关函数
export const validateCreateTradeParams = (params) => validator.validateParams(params, {
    asset_id: { type: 'number', required: true },
    amount: { type: 'string', required: true, format: 'numeric' },
    price: { type: 'string', required: true, format: 'decimal' },
    type: { type: 'string', required: true, enum: ['buy', 'sell'] },
    trader_address: { type: 'string', required: true, format: 'address' }
});

export const validateUpdateTradeParams = (params) => validator.validateParams(params, {
    status: { type: 'string', required: true, enum: ['completed', 'failed'] },
    tx_hash: { type: 'string', required: true, format: 'hash' },
    wallet_address: { type: 'string', required: true, format: 'address' }
});

export const validateTradeHistoryParams = (params) => validator.validateParams(params, {
    asset_id: { type: 'number', required: true },
    page: { type: 'number', required: true, min: 1 },
    per_page: { type: 'number', required: true, min: 1, max: 100 }
});

export const validateTradeRecord = (trade) => validator.validateParams(trade, {
    id: { type: 'number', required: true },
    created_at: { type: 'string', required: true, format: 'date' },
    type: { type: 'string', required: true, enum: ['buy', 'sell'] },
    amount: { type: 'string', required: true, format: 'numeric' },
    price: { type: 'string', required: true, format: 'decimal' },
    status: { type: 'string', required: true }
});

export const validateApiResponse = (response, endpoint) => {
    const schema = {
        CREATE_TRADE: {
            id: { type: 'number', required: true },
            status: { type: 'string', required: true, enum: ['pending', 'completed', 'failed'] }
        },
        UPDATE_TRADE: {
            success: { type: 'boolean', required: true }
        },
        GET_TRADE_HISTORY: {
            trades: { type: 'array', required: true },
            pagination: { type: 'object', required: true }
        }
    }[endpoint];
    
    if (!schema) {
        return {
            isValid: false,
            errors: [`未知的API端点: ${endpoint}`]
        };
    }
    
    return validator.validateParams(response, schema);
};

// 导出验证器实例
export const runApiValidation = () => validator.validate();

// 导出定期验证任务设置函数
export const setupApiValidationSchedule = () => {
    if (API_VALIDATION.ENABLED) {
        // 开发环境：每次代码提交前运行
        if (process.env.NODE_ENV === 'development') {
            document.addEventListener('beforeunload', async () => {
                const result = await validator.validate();
                if (!result.success) {
                    console.error('API验证失败,请修复后再提交');
                }
            });
        }
        
        // 测试环境：每日自动运行
        if (process.env.NODE_ENV === 'test') {
            const now = new Date();
            const nextRun = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 2, 0, 0, 0);
            const timeToNextRun = nextRun - now;
            
            setTimeout(async () => {
                await validator.validate();
                setInterval(() => validator.validate(), API_VALIDATION.INTERVAL);
            }, timeToNextRun);
        }
        
        // 生产环境：每次部署前运行
        if (process.env.NODE_ENV === 'production') {
            window.preDeployValidation = () => validator.validate();
        }
    }
}; 