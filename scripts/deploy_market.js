const hre = require("hardhat");

async function main() {
    const [deployer] = await ethers.getSigners();
    console.log("Deploying contracts with the account:", deployer.address);
    console.log("Account balance:", (await deployer.provider.getBalance(deployer.address)).toString());

    // Sepolia测试网上的USDC合约地址
    const USDC_ADDRESS = "0xda9d4f9b69ac6C22e444eD9aF0CfC043b7a7f53f";
    const PLATFORM_FEE_PERCENT = 250; // 2.5%

    // 部署市场合约
    const RealEstateMarket = await hre.ethers.getContractFactory("RealEstateMarket");
    console.log("Deploying RealEstateMarket...");
    
    const realEstateMarket = await RealEstateMarket.deploy(
        USDC_ADDRESS,
        PLATFORM_FEE_PERCENT
    );

    await realEstateMarket.waitForDeployment();
    const marketAddress = await realEstateMarket.getAddress();

    console.log("RealEstateMarket deployed to:", marketAddress);
    console.log("USDC Token:", await realEstateMarket.usdcToken());
    console.log("Platform Fee:", (await realEstateMarket.platformFeePercent()).toString(), "basis points");

    // 添加我们的资产代币到支持列表
    const ASSET_TOKEN_ADDRESS = "0x8e2cbB9C52f0404e4fe50C04c1999434de1cB281";
    console.log("\nAdding asset token to supported list...");
    await realEstateMarket.addSupportedToken(ASSET_TOKEN_ADDRESS);
    console.log("Asset token added successfully");

    // 验证合约
    if (process.env.ETHERSCAN_API_KEY) {
        console.log("\nVerifying contract on Etherscan...");
        try {
            await hre.run("verify:verify", {
                address: marketAddress,
                constructorArguments: [
                    USDC_ADDRESS,
                    PLATFORM_FEE_PERCENT
                ],
            });
            console.log("Contract verified successfully");
        } catch (error) {
            console.log("Error verifying contract:", error.message);
        }
    }
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    }); 