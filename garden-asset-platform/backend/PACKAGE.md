# @garden-asset-platform/backend

## 安装依赖

```bash
pip install -r requirements.txt
```

## 数据库初始化

```bash
# 初始化数据库
python scripts/init_db.py

# 创建测试数据
python scripts/create_test_data.py

# 创建水印图片
python scripts/create_watermark.py
```

## 启动服务

```bash
python run.py
```

## Flask命令

```bash
# 创建管理员
flask create-admin --username admin --password admin123

# 初始化园林
flask init-gardens

# 重置密码
flask reset-password user1 newpassword
```

## API端点

| 模块 | 端点 | 说明 |
|-----|------|-----|
| 认证 | POST /api/login | 登录 |
| 认证 | POST /api/register | 注册 |
| 资产 | GET /api/assets | 资产列表 |
| 资产 | POST /api/assets/upload | 上传资产 |
| 水印 | POST /api/watermark/embed | 嵌入水印 |
| 水印 | POST /api/watermark/trace | 溯源查询 |
| 区块链 | POST /api/blockchain/register | 上链存证 |
| 授权 | POST /api/license/apply | 申请授权 |