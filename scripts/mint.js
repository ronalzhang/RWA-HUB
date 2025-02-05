const hre = require("hardhat");

async function main() {
    // 获取部署的合约
    const contractAddress = "0x8e2cbB9C52f0404e4fe50C04c1999434de1cB281";
    const RealEstateToken = await hre.ethers.getContractFactory("RealEstateToken");
    const realEstateToken = await RealEstateToken.attach(contractAddress);

    console.log("开始铸造代币...");
    
    // 调用mint函数
    const tx = await realEstateToken.mint();
    await tx.wait();

    // 获取铸造后的信息
    const propertyInfo = await realEstateToken.getPropertyInfo();
    console.log("\n铸造完成！");
    console.log("总供应量:", propertyInfo._totalSupply.toString(), "tokens");
    console.log("是否已铸造:", propertyInfo._isMinted);

    // 获取部署者的余额
    const [deployer] = await ethers.getSigners();
    const balance = await realEstateToken.balanceOf(deployer.address);
    console.log("部署者余额:", balance.toString(), "tokens");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    }); 