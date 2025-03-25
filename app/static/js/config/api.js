// API端点配置
const API_ENDPOINTS = {
    CREATE_TRADE: '/api/trades',
    UPDATE_TRADE: (id) => `/api/trades/${id}/update`,
    GET_TRADE_HISTORY: (assetId, page, perPage) => `/api/trades?asset_id=${assetId}&page=${page}&per_page=${perPage}`,
    GET_ASSET: (id) => `/api/assets/${id}`,
    GET_ASSET_HOLDERS: (assetId) => `/api/assets/${assetId}/holders`,
    GET_ASSET_DIVIDEND: (assetId) => `/api/assets/${assetId}/dividend`
};

// 合约配置
const CONTRACT_CONFIG = {
    // 交易合约地址
    TRADE_CONTRACT_ADDRESS: '0x8B3f5393Bca6164D605E74381b61D0c283f6fe6C',
    
    // USDC代币合约地址（Solana Devnet）
    USDC_CONTRACT_ADDRESS: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    
    // 平台钱包地址
    PLATFORM_WALLET: 'EeYfRdpGtdTM9pLDrXFq39C2SKYD9SQkijw7keUKJtLR',
    
    // 网络配置
    NETWORK: {
        SOLANA_ENDPOINT: 'https://api.devnet.solana.com',
        SOLANA_CLUSTER: 'devnet'
    },
    
    // 费用配置
    FEES: {
        PLATFORM_FEE_PERCENT: 3.5,  // 平台手续费比例
        DIVIDEND_FEE_PERCENT: 1.0   // 分红手续费比例
    }
};

// API基础配置
const API_CONFIG = {
    BASE_URL: 'https://rwa-hub.com',
    API_VERSION: 'v1',
    TIMEOUT: 30000,  // 30秒超时
    RETRY_COUNT: 3,  // 重试3次
    RETRY_DELAY: 1000  // 重试间隔1秒
};

// API验证配置
const API_VALIDATION = {
    // 是否启用API验证
    ENABLED: true,
    
    // 验证间隔(毫秒)
    INTERVAL: 24 * 60 * 60 * 1000,  // 每24小时
    
    // 验证超时时间(毫秒)
    TIMEOUT: 10000,  // 10秒
    
    // 验证失败重试次数
    RETRY_COUNT: 3,
    
    // 验证失败重试间隔(毫秒)
    RETRY_DELAY: 1000,  // 1秒
    
    // 验证日志级别
    LOG_LEVEL: 'info',  // debug, info, warn, error
    
    // 验证结果回调
    CALLBACK: null
};

// API响应格式
const API_RESPONSE_FORMAT = {
    // 成功响应
    SUCCESS: {
        code: 200,
        message: 'success',
        data: null
    },
    
    // 错误响应
    ERROR: {
        code: 500,
        message: 'error',
        error: null
    }
};

// 交易合约ABI
const TradeContractABI = [
    // 创建交易
    {
        "inputs": [
            {"name": "_tradeId", "type": "uint256"},
            {"name": "_seller", "type": "address"},
            {"name": "_amount", "type": "uint256"},
            {"name": "_price", "type": "uint256"}
        ],
        "name": "createTrade",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    // 执行交易
    {
        "inputs": [{"name": "_tradeId", "type": "uint256"}],
        "name": "executeTrade",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    // 查询交易信息
    {
        "inputs": [{"name": "", "type": "uint256"}],
        "name": "trades",
        "outputs": [
            {"name": "id", "type": "uint256"},
            {"name": "buyer", "type": "address"},
            {"name": "seller", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "price", "type": "uint256"},
            {"name": "completed", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
];

// USDC代币合约ABI（简化版）
const USDC_ABI = [
    // 查询余额
    {
        "constant": true,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    // 授权
    {
        "constant": false,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    // 转账
    {
        "constant": false,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
];

// 导出配置
export {
    API_ENDPOINTS,
    CONTRACT_CONFIG,
    API_CONFIG,
    API_VALIDATION,
    API_RESPONSE_FORMAT,
    TradeContractABI,
    USDC_ABI
}; 