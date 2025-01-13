// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./openzeppelin/token/ERC20/ERC20.sol";
import "./openzeppelin/access/Ownable.sol";

contract AssetToken is ERC20, Ownable {
    constructor(
        string memory name,
        string memory symbol,
        uint256 totalSupply,
        address owner
    ) ERC20(name, symbol) {
        _mint(owner, totalSupply);
        _transferOwnership(owner);
    }
}