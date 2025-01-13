// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./AssetToken.sol";

contract AssetFactory {
    event TokenCreated(address tokenAddress, string name, string symbol, uint256 totalSupply, address owner);
    
    function createAssetToken(
        string memory name,
        string memory symbol,
        uint256 totalSupply,
        address owner
    ) public returns (address) {
        AssetToken token = new AssetToken(name, symbol, totalSupply, owner);
        emit TokenCreated(address(token), name, symbol, totalSupply, owner);
        return address(token);
    }
}