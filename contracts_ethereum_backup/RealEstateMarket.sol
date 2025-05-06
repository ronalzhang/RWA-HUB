// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract RealEstateMarket is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // 状态变量
    IERC20 public usdcToken;  // USDC代币合约
    uint256 public platformFeePercent;  // 平台手续费百分比
    mapping(address => uint256) public tokenPrices;  // 资产代币价格映射
    mapping(address => bool) public supportedTokens;  // 支持的资产代币列表
    
    // 分销佣金百分比 (以万分之一为单位)
    uint256 public level1CommissionRate = 3000;  // 30%
    uint256 public level2CommissionRate = 1500;  // 15%
    uint256 public level3CommissionRate = 500;   // 5%

    // 事件
    event TokenListed(address indexed token, uint256 price);
    event TokenPurchased(
        address indexed token,
        address indexed buyer,
        address indexed seller,
        uint256 amount,
        uint256 price,
        uint256 platformFee
    );
    event TokenPurchasedWithDistribution(
        address indexed token,
        address indexed buyer,
        address indexed seller,
        uint256 amount,
        uint256 totalPrice,
        uint256 platformFee,
        address[] distributors,
        uint256[] commissions
    );
    event PlatformFeeUpdated(uint256 newFeePercent);
    event CommissionRatesUpdated(uint256 level1Rate, uint256 level2Rate, uint256 level3Rate);

    constructor(
        address _usdcToken,
        uint256 _platformFeePercent
    ) Ownable(msg.sender) {
        require(_usdcToken != address(0), "Invalid USDC address");
        require(_platformFeePercent <= 1000, "Fee too high"); // 最高10%

        usdcToken = IERC20(_usdcToken);
        platformFeePercent = _platformFeePercent;
    }

    // 添加支持的资产代币
    function addSupportedToken(address tokenAddress) external onlyOwner {
        require(tokenAddress != address(0), "Invalid token address");
        supportedTokens[tokenAddress] = true;
    }

    // 设置资产代币价格
    function setTokenPrice(address tokenAddress, uint256 price) external {
        require(supportedTokens[tokenAddress], "Token not supported");
        require(IERC20(tokenAddress).balanceOf(msg.sender) > 0, "Not token holder");
        tokenPrices[tokenAddress] = price;
        emit TokenListed(tokenAddress, price);
    }

    // 更新分销佣金比例
    function updateCommissionRates(
        uint256 _level1Rate,
        uint256 _level2Rate,
        uint256 _level3Rate
    ) external onlyOwner {
        // 确保总和不超过10000 (100%)
        require(_level1Rate + _level2Rate + _level3Rate <= 10000, "Total rate too high");
        
        level1CommissionRate = _level1Rate;
        level2CommissionRate = _level2Rate;
        level3CommissionRate = _level3Rate;
        
        emit CommissionRatesUpdated(_level1Rate, _level2Rate, _level3Rate);
    }

    // 原有购买函数 (保留向后兼容)
    function purchaseTokens(
        address tokenAddress,
        address seller,
        uint256 amount
    ) external nonReentrant {
        require(supportedTokens[tokenAddress], "Token not supported");
        require(amount > 0, "Invalid amount");
        
        uint256 price = tokenPrices[tokenAddress];
        require(price > 0, "Token not listed for sale");

        // 计算总价和平台费用
        uint256 totalPrice = price * amount;
        uint256 platformFee = (totalPrice * platformFeePercent) / 10000;
        uint256 sellerAmount = totalPrice - platformFee;

        // 转移USDC
        usdcToken.safeTransferFrom(msg.sender, address(this), totalPrice);
        usdcToken.safeTransfer(seller, sellerAmount);
        usdcToken.safeTransfer(owner(), platformFee);

        // 转移资产代币
        IERC20(tokenAddress).safeTransferFrom(seller, msg.sender, amount);

        emit TokenPurchased(
            tokenAddress,
            msg.sender,
            seller,
            amount,
            totalPrice,
            platformFee
        );
    }
    
    // 新增带分销功能的购买函数
    function purchaseTokensWithDistribution(
        address tokenAddress,   // 资产代币地址
        address seller,         // 卖家地址
        uint256 amount,         // 购买数量
        address[] memory distributors,  // 分销商地址数组 [一级,二级,三级]
        uint8[] memory levels           // 对应分销级别 [1,2,3]
    ) external nonReentrant {
        // 基本验证
        require(supportedTokens[tokenAddress], "Token not supported");
        require(amount > 0, "Invalid amount");
        require(distributors.length == levels.length, "Arrays length mismatch");
        require(distributors.length <= 3, "Too many distributors");
        
        uint256 price = tokenPrices[tokenAddress];
        require(price > 0, "Token not listed for sale");

        // 1. 计算所有金额
        uint256 totalPrice = price * amount;
        uint256 platformFee = (totalPrice * platformFeePercent) / 10000;
        
        // 计算分销佣金
        uint256[] memory commissions = new uint256[](distributors.length);
        uint256 totalCommission = 0;
        
        for(uint i=0; i<distributors.length; i++) {
            if(levels[i] == 1) {
                commissions[i] = (platformFee * level1CommissionRate) / 10000;
            } else if(levels[i] == 2) {
                commissions[i] = (platformFee * level2CommissionRate) / 10000;
            } else if(levels[i] == 3) {
                commissions[i] = (platformFee * level3CommissionRate) / 10000;
            }
            totalCommission += commissions[i];
        }
        
        // 实际平台收入
        uint256 platformIncome = platformFee - totalCommission;
        
        // 卖家收入
        uint256 sellerAmount = totalPrice - platformFee;
        
        // 2. 执行转账
        // 从买家收取总价
        usdcToken.safeTransferFrom(msg.sender, address(this), totalPrice);
        
        // 首先转给卖家 - 确保卖家优先获得资金
        usdcToken.safeTransfer(seller, sellerAmount);
        
        // 然后分发佣金
        for(uint i=0; i<distributors.length; i++) {
            if(commissions[i] > 0 && distributors[i] != address(0)) {
                usdcToken.safeTransfer(distributors[i], commissions[i]);
            }
        }
        
        // 最后平台收取剩余部分
        if(platformIncome > 0) {
            usdcToken.safeTransfer(owner(), platformIncome);
        }
        
        // 3. 最后转移资产代币
        IERC20(tokenAddress).safeTransferFrom(seller, msg.sender, amount);
        
        // 4. 发出事件
        emit TokenPurchasedWithDistribution(
            tokenAddress, 
            msg.sender, 
            seller, 
            amount, 
            totalPrice, 
            platformFee, 
            distributors, 
            commissions
        );
    }

    // 更新平台手续费
    function updatePlatformFee(uint256 newFeePercent) external onlyOwner {
        require(newFeePercent <= 1000, "Fee too high"); // 最高10%
        platformFeePercent = newFeePercent;
        emit PlatformFeeUpdated(newFeePercent);
    }

    // 紧急取回代币（仅限平台费用）
    function emergencyWithdraw(address token) external onlyOwner {
        uint256 balance = IERC20(token).balanceOf(address(this));
        if (balance > 0) {
            IERC20(token).safeTransfer(owner(), balance);
        }
    }
} 