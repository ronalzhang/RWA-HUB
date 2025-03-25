// 合约地址配置
const CONTRACT_CONFIG = {
    // 交易合约地址
    TRADE_CONTRACT_ADDRESS: '0x...',  // 部署后填入实际地址
    
    // USDC代币合约地址
    USDC_CONTRACT_ADDRESS: '0x...',   // 使用实际的USDC合约地址
    
    // 平台钱包地址
    PLATFORM_WALLET: '0x...',         // 平台收款地址
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