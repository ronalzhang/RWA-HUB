const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("RealEstateMarket", function () {
    let RealEstateToken;
    let realEstateToken;
    let RealEstateMarket;
    let realEstateMarket;
    let MockUSDC;
    let mockUSDC;
    let owner;
    let seller;
    let buyer;
    let platformFeePercent;

    const initialUSDCAmount = ethers.parseUnits("10000", 6); // 10000 USDC
    const tokenAmount = 100n; // 100 tokens
    const tokenPrice = ethers.parseUnits("10", 6); // 10 USDC per token

    beforeEach(async function () {
        [owner, seller, buyer] = await ethers.getSigners();
        platformFeePercent = 500; // 5%

        // 部署模拟USDC
        MockUSDC = await ethers.getContractFactory("MockUSDC");
        mockUSDC = await MockUSDC.deploy();

        // 部署资产代币
        RealEstateToken = await ethers.getContractFactory("RealEstateToken");
        realEstateToken = await RealEstateToken.deploy(
            "Real Estate Token",
            "RET",
            "PROPERTY-001",
            1000n
        );

        // 部署市场合约
        RealEstateMarket = await ethers.getContractFactory("RealEstateMarket");
        realEstateMarket = await RealEstateMarket.deploy(
            await mockUSDC.getAddress(),
            platformFeePercent
        );

        // 铸造资产代币给卖家
        await realEstateToken.mint();
        await realEstateToken.transfer(seller.address, tokenAmount);

        // 铸造USDC给买家
        await mockUSDC.mint(buyer.address, initialUSDCAmount);
    });

    describe("Market Setup", function () {
        it("Should set the correct USDC token address", async function () {
            expect(await realEstateMarket.usdcToken()).to.equal(await mockUSDC.getAddress());
        });

        it("Should set the correct platform fee", async function () {
            expect(await realEstateMarket.platformFeePercent()).to.equal(platformFeePercent);
        });
    });

    describe("Token Management", function () {
        it("Should add supported token", async function () {
            await realEstateMarket.addSupportedToken(await realEstateToken.getAddress());
            expect(await realEstateMarket.supportedTokens(await realEstateToken.getAddress())).to.be.true;
        });

        it("Should set token price", async function () {
            await realEstateMarket.addSupportedToken(await realEstateToken.getAddress());
            await realEstateMarket.connect(seller).setTokenPrice(await realEstateToken.getAddress(), tokenPrice);
            expect(await realEstateMarket.tokenPrices(await realEstateToken.getAddress())).to.equal(tokenPrice);
        });
    });

    describe("Token Purchase", function () {
        beforeEach(async function () {
            await realEstateMarket.addSupportedToken(await realEstateToken.getAddress());
            await realEstateMarket.connect(seller).setTokenPrice(await realEstateToken.getAddress(), tokenPrice);
            await realEstateToken.connect(seller).approve(await realEstateMarket.getAddress(), tokenAmount);
            await mockUSDC.connect(buyer).approve(await realEstateMarket.getAddress(), initialUSDCAmount);
        });

        it("Should purchase tokens successfully", async function () {
            const purchaseAmount = 50n;
            const totalPrice = tokenPrice * purchaseAmount;
            const platformFee = (totalPrice * BigInt(platformFeePercent)) / 10000n;
            const sellerAmount = totalPrice - platformFee;

            await expect(
                realEstateMarket.connect(buyer).purchaseTokens(
                    await realEstateToken.getAddress(),
                    seller.address,
                    purchaseAmount
                )
            ).to.emit(realEstateMarket, "TokenPurchased")
             .withArgs(
                await realEstateToken.getAddress(),
                buyer.address,
                seller.address,
                purchaseAmount,
                totalPrice,
                platformFee
             );

            // 验证代币转移
            expect(await realEstateToken.balanceOf(buyer.address)).to.equal(purchaseAmount);
            expect(await mockUSDC.balanceOf(seller.address)).to.equal(sellerAmount);
            expect(await mockUSDC.balanceOf(owner.address)).to.equal(platformFee);
        });
    });

    describe("Admin Functions", function () {
        it("Should update platform fee", async function () {
            const newFee = 300; // 3%
            await realEstateMarket.updatePlatformFee(newFee);
            expect(await realEstateMarket.platformFeePercent()).to.equal(newFee);
        });

        it("Should not allow fee higher than 10%", async function () {
            await expect(realEstateMarket.updatePlatformFee(1100))
                .to.be.revertedWith("Fee too high");
        });
    });
}); 