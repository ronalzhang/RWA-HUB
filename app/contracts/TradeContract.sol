// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract TradeContract is Ownable, ReentrancyGuard {
    // USDC代币合约地址
    IERC20 public usdcToken;
    
    // 平台费率：3.5%
    uint256 public constant PLATFORM_FEE_RATE = 35; // 3.5% = 35/1000
    
    // 平台收款地址
    address public platformWallet;
    
    // 交易记录结构
    struct Trade {
        uint256 id;
        address buyer;
        address seller;
        uint256 amount;
        uint256 price;
        bool completed;
    }
    
    // 交易记录映射
    mapping(uint256 => Trade) public trades;
    
    // 事件
    event TradeCreated(uint256 indexed tradeId, address indexed buyer, address indexed seller, uint256 amount, uint256 price);
    event TradeCompleted(uint256 indexed tradeId);
    
    constructor(address _usdcToken, address _platformWallet) {
        usdcToken = IERC20(_usdcToken);
        platformWallet = _platformWallet;
    }
    
    // 创建交易
    function createTrade(
        uint256 _tradeId,
        address _seller,
        uint256 _amount,
        uint256 _price
    ) external {
        require(_amount > 0, "Amount must be greater than 0");
        require(_price > 0, "Price must be greater than 0");
        require(_seller != address(0), "Invalid seller address");
        
        trades[_tradeId] = Trade({
            id: _tradeId,
            buyer: msg.sender,
            seller: _seller,
            amount: _amount,
            price: _price,
            completed: false
        });
        
        emit TradeCreated(_tradeId, msg.sender, _seller, _amount, _price);
    }
    
    // 执行交易
    function executeTrade(uint256 _tradeId) external nonReentrant {
        Trade storage trade = trades[_tradeId];
        require(!trade.completed, "Trade already completed");
        require(msg.sender == trade.buyer, "Not trade buyer");
        
        uint256 totalAmount = trade.amount * trade.price;
        uint256 platformFee = (totalAmount * PLATFORM_FEE_RATE) / 1000;
        uint256 sellerAmount = totalAmount - platformFee;
        
        // 转账USDC
        require(usdcToken.transferFrom(msg.sender, platformWallet, platformFee), "Platform fee transfer failed");
        require(usdcToken.transferFrom(msg.sender, trade.seller, sellerAmount), "Seller payment transfer failed");
        
        trade.completed = true;
        emit TradeCompleted(_tradeId);
    }
    
    // 更新平台钱包地址
    function updatePlatformWallet(address _newWallet) external onlyOwner {
        require(_newWallet != address(0), "Invalid wallet address");
        platformWallet = _newWallet;
    }
} 