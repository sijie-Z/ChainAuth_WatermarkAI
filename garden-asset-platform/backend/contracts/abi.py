# AssetRegistry智能合约ABI
# 用于FISCO BCOS区块链存证

CONTRACT_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "assetId", "type": "string"},
            {"name": "watermarkId", "type": "string"},
            {"name": "fileHash", "type": "string"},
            {"name": "metadata", "type": "string"}
        ],
        "name": "registerAsset",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "licenseId", "type": "string"},
            {"name": "assetId", "type": "string"},
            {"name": "licensee", "type": "string"},
            {"name": "licenseType", "type": "string"},
            {"name": "validUntil", "type": "uint256"}
        ],
        "name": "grantLicense",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "assetId", "type": "string"}],
        "name": "verifyAsset",
        "outputs": [
            {"name": "exists", "type": "bool"},
            {"name": "watermarkId", "type": "string"},
            {"name": "fileHash", "type": "string"},
            {"name": "registeredAt", "type": "uint256"}
        ],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "watermarkId", "type": "string"}],
        "name": "verifyByWatermark",
        "outputs": [
            {"name": "exists", "type": "bool"},
            {"name": "assetId", "type": "string"}
        ],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "licenseId", "type": "string"}],
        "name": "verifyLicense",
        "outputs": [
            {"name": "valid", "type": "bool"},
            {"name": "assetId", "type": "string"},
            {"name": "licensee", "type": "string"}
        ],
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "assetId", "type": "string"},
            {"indexed": False, "name": "watermarkId", "type": "string"},
            {"indexed": False, "name": "registeredAt", "type": "uint256"}
        ],
        "name": "AssetRegistered",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "licenseId", "type": "string"},
            {"indexed": False, "name": "assetId", "type": "string"},
            {"indexed": False, "name": "licensee", "type": "string"}
        ],
        "name": "LicenseGranted",
        "type": "event"
    }
]

CONTRACT_BYTECODE = "0x..."  # 编译后的合约字节码