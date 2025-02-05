const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("RealEstateToken", function () {
    let RealEstateToken;
    let realEstateToken;
    let owner;
    let addr1;
    let addr2;

    // 测试数据
    const tokenName = "Real Estate Token";
    const tokenSymbol = "RET";
    const propertyId = "PROPERTY-001";
    const propertyArea = 10000n; // 100平方米 = 10000平方厘米

    beforeEach(async function () {
        // 获取合约工厂和测试账户
        [owner, addr1, addr2] = await ethers.getSigners();
        RealEstateToken = await ethers.getContractFactory("RealEstateToken");
        
        // 部署合约
        realEstateToken = await RealEstateToken.deploy(
            tokenName,
            tokenSymbol,
            propertyId,
            propertyArea
        );
    });

    describe("Deployment", function () {
        it("Should set the right owner", async function () {
            expect(await realEstateToken.owner()).to.equal(owner.address);
        });

        it("Should set the correct token name and symbol", async function () {
            expect(await realEstateToken.name()).to.equal(tokenName);
            expect(await realEstateToken.symbol()).to.equal(tokenSymbol);
        });

        it("Should set the correct property information", async function () {
            const propertyInfo = await realEstateToken.getPropertyInfo();
            expect(propertyInfo._propertyId).to.equal(propertyId);
            expect(propertyInfo._propertyArea).to.equal(propertyArea);
            expect(propertyInfo._isMinted).to.equal(false);
        });

        it("Should set decimals to 0", async function () {
            expect(await realEstateToken.decimals()).to.equal(0);
        });
    });

    describe("Minting", function () {
        it("Should mint tokens equal to property area", async function () {
            await realEstateToken.mint();
            expect(await realEstateToken.totalSupply()).to.equal(propertyArea);
            expect(await realEstateToken.balanceOf(owner.address)).to.equal(propertyArea);
        });

        it("Should not allow minting twice", async function () {
            await realEstateToken.mint();
            await expect(realEstateToken.mint()).to.be.revertedWith("Tokens already minted");
        });

        it("Should only allow owner to mint", async function () {
            await expect(realEstateToken.connect(addr1).mint()).to.be.reverted;
        });
    });

    describe("Token Operations", function () {
        beforeEach(async function () {
            await realEstateToken.mint();
        });

        it("Should transfer tokens between accounts", async function () {
            const transferAmount = 100n;
            await realEstateToken.transfer(addr1.address, transferAmount);
            expect(await realEstateToken.balanceOf(addr1.address)).to.equal(transferAmount);
        });

        it("Should burn tokens", async function () {
            const burnAmount = 100n;
            const initialSupply = await realEstateToken.totalSupply();
            await realEstateToken.burn(burnAmount);
            expect(await realEstateToken.totalSupply()).to.equal(initialSupply - burnAmount);
        });

        it("Should emit TokensBurned event when burning tokens", async function () {
            const burnAmount = 100n;
            await expect(realEstateToken.burn(burnAmount))
                .to.emit(realEstateToken, "TokensBurned")
                .withArgs(owner.address, burnAmount);
        });
    });
}); 