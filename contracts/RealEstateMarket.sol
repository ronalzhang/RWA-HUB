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
    event PlatformFeeUpdated(uint256 newFeePercent);

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

    // 购买资产代币
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