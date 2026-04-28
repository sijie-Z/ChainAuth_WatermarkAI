"""
智能合约 - 资产存证合约
用于FISCO BCOS联盟链
"""

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title GardenAssetRegistry
 * @dev 苏州园林数字资产存证合约
 */
contract GardenAssetRegistry {

    // 存证记录结构
    struct AssetRecord {
        string assetCode;           // 资产编码
        string watermarkId;         // 水印ID
        string fileHash;            // 文件哈希(SHA256)
        string featureHash;         // 特征向量哈希
        address creator;            // 创建者地址
        uint256 timestamp;          // 存证时间戳
        uint8 status;               // 状态：0-已存证 1-已授权 2-已归档
    }

    // 授权记录结构
    struct LicenseRecord {
        string assetCode;           // 资产编码
        address licensor;           // 授权方
        address licensee;           // 被授权方
        uint8 licenseType;          // 授权类型
        uint256 startTime;          // 授权开始时间
        uint256 endTime;            // 授权结束时间
        string usageScope;          // 使用范围
        uint256 timestamp;          // 记录时间
    }

    // 存证记录映射
    mapping(string => AssetRecord) public assetRecords;
    mapping(string => LicenseRecord[]) public licenseHistory;

    // 所有资产编码列表
    string[] public assetCodes;

    // 管理员地址
    address public admin;

    // 事件定义
    event AssetRegistered(string indexed assetCode, string watermarkId, address creator, uint256 timestamp);
    event LicenseGranted(string indexed assetCode, address licensee, uint8 licenseType, uint256 startTime, uint256 endTime);
    event AssetUpdated(string indexed assetCode, uint8 newStatus);

    // 修饰器
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only admin can call this function");
        _;
    }

    modifier assetExists(string memory _assetCode) {
        require(bytes(assetRecords[_assetCode].assetCode).length > 0, "Asset not registered");
        _;
    }

    modifier assetNotExists(string memory _assetCode) {
        require(bytes(assetRecords[_assetCode].assetCode).length == 0, "Asset already registered");
        _;
    }

    /**
     * @dev 构造函数
     */
    constructor() {
        admin = msg.sender;
    }

    /**
     * @dev 资产存证
     * @param _assetCode 资产编码
     * @param _watermarkId 水印ID
     * @param _fileHash 文件哈希
     * @param _featureHash 特征哈希
     */
    function registerAsset(
        string memory _assetCode,
        string memory _watermarkId,
        string memory _fileHash,
        string memory _featureHash
    ) public assetNotExists(_assetCode) returns (bool) {

        assetRecords[_assetCode] = AssetRecord({
            assetCode: _assetCode,
            watermarkId: _watermarkId,
            fileHash: _fileHash,
            featureHash: _featureHash,
            creator: msg.sender,
            timestamp: block.timestamp,
            status: 0
        });

        assetCodes.push(_assetCode);

        emit AssetRegistered(_assetCode, _watermarkId, msg.sender, block.timestamp);
        return true;
    }

    /**
     * @dev 授权记录
     * @param _assetCode 资产编码
     * @param _licensee 被授权方地址
     * @param _licenseType 授权类型
     * @param _startTime 开始时间
     * @param _endTime 结束时间
     * @param _usageScope 使用范围
     */
    function grantLicense(
        string memory _assetCode,
        address _licensee,
        uint8 _licenseType,
        uint256 _startTime,
        uint256 _endTime,
        string memory _usageScope
    ) public assetExists(_assetCode) returns (bool) {

        // 检查是否是创建者或管理员
        require(
            assetRecords[_assetCode].creator == msg.sender || msg.sender == admin,
            "Not authorized to grant license"
        );

        licenseHistory[_assetCode].push(LicenseRecord({
            assetCode: _assetCode,
            licensor: msg.sender,
            licensee: _licensee,
            licenseType: _licenseType,
            startTime: _startTime,
            endTime: _endTime,
            usageScope: _usageScope,
            timestamp: block.timestamp
        }));

        emit LicenseGranted(_assetCode, _licensee, _licenseType, _startTime, _endTime);
        return true;
    }

    /**
     * @dev 查询资产存证
     * @param _assetCode 资产编码
     */
    function getAssetRecord(string memory _assetCode)
        public view assetExists(_assetCode)
        returns (AssetRecord memory) {
        return assetRecords[_assetCode];
    }

    /**
     * @dev 验证水印ID
     * @param _assetCode 资产编码
     * @param _watermarkId 水印ID
     */
    function verifyWatermark(string memory _assetCode, string memory _watermarkId)
        public view assetExists(_assetCode)
        returns (bool) {
        return keccak256(bytes(assetRecords[_assetCode].watermarkId)) == keccak256(bytes(_watermarkId));
    }

    /**
     * @dev 验证文件哈希
     * @param _assetCode 资产编码
     * @param _fileHash 文件哈希
     */
    function verifyFileHash(string memory _assetCode, string memory _fileHash)
        public view assetExists(_assetCode)
        returns (bool) {
        return keccak256(bytes(assetRecords[_assetCode].fileHash)) == keccak256(bytes(_fileHash));
    }

    /**
     * @dev 更新资产状态
     * @param _assetCode 资产编码
     * @param _newStatus 新状态
     */
    function updateAssetStatus(string memory _assetCode, uint8 _newStatus)
        public onlyAdmin assetExists(_assetCode)
        returns (bool) {
        assetRecords[_assetCode].status = _newStatus;
        emit AssetUpdated(_assetCode, _newStatus);
        return true;
    }

    /**
     * @dev 获取授权历史
     * @param _assetCode 资产编码
     */
    function getLicenseHistory(string memory _assetCode)
        public view assetExists(_assetCode)
        returns (LicenseRecord[] memory) {
        return licenseHistory[_assetCode];
    }

    /**
     * @dev 获取资产数量
     */
    function getAssetCount() public view returns (uint256) {
        return assetCodes.length;
    }

    /**
     * @dev 获取所有资产编码
     */
    function getAllAssetCodes() public view returns (string[] memory) {
        return assetCodes;
    }

    /**
     * @dev 转移管理员权限
     * @param _newAdmin 新管理员地址
     */
    function transferAdmin(address _newAdmin) public onlyAdmin returns (bool) {
        require(_newAdmin != address(0), "Invalid address");
        admin = _newAdmin;
        return true;
    }
}