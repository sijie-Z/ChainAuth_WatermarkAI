# 园林资产平台后端服务

基于Flask的数字资产管理系统后端服务

## 环境要求

- Python 3.11+
- PostgreSQL 14+ (或SQLite用于开发)
- Redis 6+ (可选，用于限流/缓存；异步任务队列使用数据库)

## 安装步骤

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制环境配置
cp .env.example .env

# 初始化数据库
python scripts/init_db.py

# 启动服务
python run.py
```

## 项目结构

```
backend/
├── app/
│   ├── __init__.py      # 应用工厂
│   ├── config.py        # 配置文件
│   ├── extensions.py    # Flask扩展
│   ├── models/          # 数据模型
│   ├── resources/       # API资源
│   ├── services/        # 业务服务
│   ├── utils/           # 工具函数
│   └── tasks.py         # 异步任务
├── algorithm/           # 水印算法
├── scripts/             # 脚本文件
├── data/                # 数据文件
├── uploads/             # 上传文件
└── run.py              # 启动入口
```

## API文档

### 认证接口

- POST /api/register - 用户注册
- POST /api/login - 用户登录
- POST /api/logout - 用户登出

### 资产接口

- GET /api/assets - 资产列表
- GET /api/assets/:id - 资产详情
- POST /api/assets/upload - 上传资产

### 水印接口

- POST /api/watermark/embed - 嵌入水印
- POST /api/watermark/extract - 提取水印
- POST /api/watermark/trace - 溯源查询

### 区块链接口

- POST /api/blockchain/register - 上链存证
- GET /api/blockchain/verify/:id - 存证验证
- GET /api/blockchain/certificate/:id - 证书详情

## 开发说明

```bash
# 运行测试
pytest

# 代码格式化
black app/

# 代码检查
flake8 app/
```