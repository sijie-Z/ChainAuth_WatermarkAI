# 快速启动指南

## 环境要求

- Python 3.11+
- Node.js 22+
- PostgreSQL 14+ (或使用SQLite开发模式)
- Redis 6+ (可选，用于缓存)

## 快速启动

### 方式一：一键启动 (推荐)

**Windows:**
```bash
# 双击运行或在命令行执行
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### 方式二：手动启动

#### 1. 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填入必要配置

# 初始化数据库
python scripts/init_db.py

# 启动后端服务
python run.py
```

后端服务运行在 http://localhost:5000

#### 2. 前端启动

```bash
# 新开终端，进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务运行在 http://localhost:5173

### 方式三：Docker部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 默认账号

系统初始化后创建以下账号：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 超级管理员 |
| adm1 | adm123 | 资产管理员 |
| adm2 | adm123 | 授权管理员 |
| user1 | user123 | 普通用户 |

**重要：首次登录后请立即修改密码！**

## 核心功能使用

### 1. 资产上传

1. 登录系统
2. 进入「资产中心」→「上传资产」
3. 填写资产信息，上传文件
4. 提交审核

### 2. 水印嵌入

1. 进入「管理后台」→「水印管理」
2. 选择待处理的资产
3. 点击「嵌入水印」
4. 系统自动嵌入数字水印

### 3. 区块链存证

1. 确保资产已嵌入水印
2. 进入「管理后台」→「存证管理」
3. 选择资产，点击「上链存证」
4. 系统生成存证证书

### 4. 溯源查询

1. 进入「溯源查询」页面
2. 上传待查询的图片或文件
3. 系统提取水印并匹配资产
4. 显示资产详情和存证信息

### 5. 授权申请

1. 进入资产详情页
2. 点击「申请授权」
3. 填写申请信息
4. 等待管理员审批

## 开发命令

```bash
# 运行测试
make test
# 或
cd backend && pytest

# 代码格式化
make format
# 或
black backend/app

# 创建测试数据
make create-data

# 健康检查
cd backend && python scripts/health_check.py
```

## 常见问题

### Q: 数据库连接失败？

检查 PostgreSQL 服务是否启动，数据库是否创建：
```bash
# 创建数据库
createdb garden_asset

# 或使用 psql
psql -U postgres -c "CREATE DATABASE garden_asset;"
```

### Q: 前端启动报错？

```bash
# 清除依赖缓存
rm -rf node_modules
npm install
```

### Q: AI功能不可用？

AI功能需要安装额外依赖：
```bash
pip install torch transformers pymilvus
```

如不使用AI功能，可在 `.env` 中设置：
```
AI_ENABLED=false
```

### Q: 区块链功能不可用？

区块链功能需要部署 FISCO BCOS 节点。如无节点，系统将使用模拟模式。

## 项目结构

```
garden-asset-platform/
├── backend/                 # 后端代码
│   ├── app/                 # 应用核心
│   │   ├── models/          # 数据模型
│   │   ├── resources/       # API资源
│   │   ├── services/        # 业务服务
│   │   ├── utils/           # 工具函数
│   │   └── __init__.py      # 应用工厂
│   ├── algorithm/           # 水印算法
│   ├── scripts/             # 脚本文件
│   ├── tests/               # 测试文件
│   └── requirements.txt     # Python依赖
├── frontend/                # 前端代码
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── api/             # API模块
│   │   ├── stores/          # 状态管理
│   │   ├── router/          # 路由配置
│   │   └── assets/          # 静态资源
│   └── package.json         # Node依赖
├── docs/                    # 文档
├── docker-compose.yml       # Docker配置
├── Makefile                 # 管理命令
└── README.md                # 项目说明
```

## 技术支持

如有问题，请查阅：
- [开发文档](./docs/DEVELOPMENT.md)
- [API文档](./docs/api.yaml)
- [部署文档](./docs/deployment.md)

## 许可证

MIT License
