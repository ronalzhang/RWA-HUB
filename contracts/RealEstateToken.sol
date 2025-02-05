// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";

contract RealEstateToken is ERC20, Ownable, ERC20Burnable {
    // 资产信息
    string public propertyId;
    uint256 public propertyArea;  // 单位：平方厘米
    bool public isMinted;

    // 事件
    event PropertyMinted(string propertyId, uint256 totalSupply);
    event TokensBurned(address indexed burner, uint256 amount);

    constructor(
        string memory _name,
        string memory _symbol,
        string memory _propertyId,
        uint256 _propertyArea
    ) ERC20(_name, _symbol) Ownable(msg.sender) {
        propertyId = _propertyId;
        propertyArea = _propertyArea;
        isMinted = false;
    }

    // 铸造代币，每平方厘米对应1个代币
    function mint() external onlyOwner {
        require(!isMinted, "Tokens already minted");
        require(propertyArea > 0, "Invalid property area");
        
        uint256 totalSupply = propertyArea;  // 1:1 对应关系
        _mint(msg.sender, totalSupply);
        isMinted = true;
        
        emit PropertyMinted(propertyId, totalSupply);
    }

    // 重写decimals函数，确保代币不可分割
    function decimals() public view virtual override returns (uint8) {
        return 0;
    }

    // 销毁代币
    function burn(uint256 amount) public virtual override {
        super.burn(amount);
        emit TokensBurned(msg.sender, amount);
    }

    // 获取资产信息
    function getPropertyInfo() external view returns (
        string memory _propertyId,
        uint256 _propertyArea,
        uint256 _totalSupply,
        bool _isMinted
    ) {
        return (
            propertyId,
            propertyArea,
            totalSupply(),
            isMinted
        );
    }
} 