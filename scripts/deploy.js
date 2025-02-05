const hre = require("hardhat");

async function main() {
    const [deployer] = await ethers.getSigners();
    console.log("Deploying contracts with the account:", deployer.address);
    console.log("Account balance:", (await deployer.provider.getBalance(deployer.address)).toString());

    // 部署参数
    const tokenName = "Real Estate Token";
    const tokenSymbol = "RET";
    const propertyId = "PROPERTY-001";
    const propertyArea = 10000n; // 100平方米 = 10000平方厘米

    // 部署合约
    const RealEstateToken = await hre.ethers.getContractFactory("RealEstateToken");
    console.log("Deploying RealEstateToken...");
    
    const realEstateToken = await RealEstateToken.deploy(
        tokenName,
        tokenSymbol,
        propertyId,
        propertyArea
    );

    await realEstateToken.waitForDeployment();
    const contractAddress = await realEstateToken.getAddress();

    console.log("RealEstateToken deployed to:", contractAddress);
    console.log("Token Name:", await realEstateToken.name());
    console.log("Token Symbol:", await realEstateToken.symbol());
    
    // 获取资产信息
    const propertyInfo = await realEstateToken.getPropertyInfo();
    console.log("\nProperty Information:");
    console.log("Property ID:", propertyInfo._propertyId);
    console.log("Property Area:", propertyInfo._propertyArea.toString(), "square centimeters");
    console.log("Total Supply:", propertyInfo._totalSupply.toString(), "tokens");
    console.log("Is Minted:", propertyInfo._isMinted);

    // 验证合约
    if (process.env.ETHERSCAN_API_KEY) {
        console.log("\nVerifying contract on Etherscan...");
        try {
            await hre.run("verify:verify", {
                address: contractAddress,
                constructorArguments: [
                    tokenName,
                    tokenSymbol,
                    propertyId,
                    propertyArea
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