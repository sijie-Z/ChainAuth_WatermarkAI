# 苏州园林数字资产安全分发与溯源系统

> 从"版权裸奔"到"链上确权"：基于数字水印和AI推理的苏州园林数字资产安全分发与溯源系统

## 项目简介

本系统面向苏州园林数字资产（图片、3D模型、矢量图纸等）的版权保护与安全分发需求，构建了**水印嵌入 → 区块链存证 → AI侵权检测 → 溯源追踪**四位一体的全链路保护体系。

### 核心功能

| 模块 | 功能 | 技术实现 |
|------|------|----------|
| 资产管理 | 数字资产上传、浏览、分类、检索、下载 | Vue3 + Flask + MinIO |
| 数字水印 | DCT频域盲水印嵌入与提取，支持抗压缩/裁剪 | Python OpenCV + NumPy |
| 区块链存证 | 资产+水印双上链，FISCO BCOS智能合约 | FISCO BCOS + Python SDK |
| AI溯源 | 以图搜图、侵权检测、智能问答 | 智谱GLM-4V + Milvus |
| 授权分发 | 在线申请→双重审批→合同管理→下载控制 | Flask + JWT |
| OCR识别 | 百度OCR提取图片文字，辅助溯源 | 百度OCR API |

### 技术架构

```
浏览器 ──→ Nginx ──→ Vue3 SPA (静态资源)
                      │
                      ├──→ Flask REST API ──→ PostgreSQL
                      │                    ├──→ Redis (缓存/限流)
                      │                    ├──→ MinIO (对象存储)
                      │                    └──→ Milvus (向量检索)
                      │
                      └──→ FISCO BCOS (区块链存证)
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3.4, Vite 5, Pinia, Element Plus, ECharts, THREE.js |
| 后端 | Flask 3.0, Flask-RESTful, SQLAlchemy, Flask-JWT-Extended |
| 存储 | PostgreSQL, Redis, MinIO, Milvus |
| 区块链 | FISCO BCOS 3.x |
| AI | 智谱GLM-4V, CLIP, DINOv2, 百度OCR |
| 部署 | Docker Compose, Gunicorn, Nginx |

## 快速开始

### 环境要求

- Python 3.11+ / Node.js 22+
- Docker & Docker Compose（推荐）

### Docker 一键部署

```bash
# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入必要的 API Key

# 启动所有服务（后端、前端、PostgreSQL、Redis、MinIO）
docker-compose up -d

# 初始化数据库
docker exec garden-backend flask init-db

# 填充示例数据（可选）
docker exec garden-backend flask seed
```

服务端口：
- 前端页面: http://localhost
- 后端API: http://localhost:5000/api
- MinIO控制台: http://localhost:9001
- 健康检查: http://localhost:5000/health

### 本地开发

**后端：**

```bash
cd backend
pip install -r requirements.txt
python scripts/init_db.py    # 初始化数据库
python run.py                # 启动开发服务器 :5000
```

**前端：**

```bash
cd frontend
npm install
npm run dev                  # 启动Vite开发服务器 :5173
```

### 运行测试

```bash
# 后端测试（29个用例，覆盖API/模型/安全）
cd backend && python -m pytest tests/ -v

# 前端生产构建
cd frontend && npm run build
```

### 默认账号

管理员 `admin / admin123` · 审批员 `adm1, adm2 / 123456` · 用户 `user1, user2 / 123456`

## 项目结构

```
garden-asset-platform/
├── backend/                        # Flask后端
│   ├── app/
│   │   ├── resources/             # API资源层（auth/asset/watermark/blockchain/ai/license/garden）
│   │   ├── models/                # 数据模型（User/Asset/Watermark/License/Garden/OperationLog）
│   │   ├── services/              # 业务服务层
│   │   │   ├── watermark_service.py    # DCT频域水印算法
│   │   │   ├── blockchain_service.py   # FISCO BCOS链交互
│   │   │   └── ai_service.py           # AI特征提取与问答
│   │   ├── utils/                 # 工具模块（日志/中间件/错误处理/JWT回调）
│   │   ├── config.py              # 多环境配置（开发/生产/测试）
│   │   └── __init__.py            # Flask应用工厂
│   ├── algorithm/                 # 水印算法库（DCT/LSB/矢量）
│   ├── contracts/                 # Solidity智能合约
│   ├── scripts/                   # 初始化与种子数据脚本
│   ├── tests/                     # pytest测试（29个用例）
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                       # Vue3前端
│   ├── src/
│   │   ├── views/                 # 页面组件
│   │   │   ├── home/              # 首页 + 登录 + 注册
│   │   │   ├── asset/             # 资产中心 + 详情 + 上传
│   │   │   ├── license/           # 申请授权 + 我的授权
│   │   │   ├── trace/             # 溯源查询 + 报告下载
│   │   │   ├── certificate/       # 区块链存证证书
│   │   │   ├── admin/             # 管理后台（仪表盘/资产/水印/授权/区块链/用户）
│   │   │   ├── profile/           # 个人中心
│   │   │   ├── settings/          # 账号设置
│   │   │   └── error/             # 404页面
│   │   ├── api/                   # API请求封装（8个模块）
│   │   ├── stores/                # Pinia状态管理
│   │   ├── router/                # Vue Router路由 + 权限守卫
│   │   └── assets/                # 样式变量 + 全局样式
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml              # 多服务编排
├── Dockerfile                      # 一体化构建
└── .gitignore
```

## API 概览

### 公开接口（无需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 平台统计数据（资产数、上链数等） |
| POST | `/api/register` | 用户注册 |
| POST | `/api/login` | 用户登录 |
| POST | `/api/refresh` | 刷新Access Token |

### 资产模块（需认证）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/assets` | 资产列表（分页、筛选、搜索） |
| POST | `/api/assets/upload` | 上传资产（含魔数校验） |
| GET | `/api/assets/:id` | 资产详情 |
| GET | `/api/assets/:id/download` | 下载资产文件 |
| GET | `/api/assets/stats` | 资产统计（含水印趋势） |
| GET | `/api/assets/my` | 我的资产 |

### 水印与溯源

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/watermark/embed` | 嵌入水印 |
| POST | `/api/watermark/extract` | 提取水印 |
| POST | `/api/watermark/verify` | 验证水印ID |
| POST | `/api/watermark/trace` | 图片溯源查询 |
| GET | `/api/watermark/logs` | 水印操作日志 |

### 区块链存证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/blockchain/register` | 资产上链存证 |
| POST | `/api/blockchain/verify` | 链上验证 |
| GET | `/api/blockchain/certificate/:id` | 获取存证证书 |
| GET | `/api/blockchain/history/:id` | 存证历史追溯 |
| GET | `/api/blockchain/status` | 区块链连接状态 |

### AI能力

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/analyze` | AI资产特征分析 |
| POST | `/api/ai/search` | 以图搜图相似资产 |
| POST | `/api/ai/infringement` | 侵权检测 |
| POST | `/api/ai/chat` | AI智能问答助手 |

### 授权管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/license/apply` | 申请使用授权 |
| GET | `/api/license/pending` | 待审批列表（审批员） |
| POST | `/api/license/approve/:id` | 审批（通过/拒绝） |
| GET | `/api/license/approved` | 已审批列表 |
| GET | `/api/license/my` | 我的授权 |

## 安全特性

- JWT双Token认证（Access 24h + Refresh 30d）
- 请求频率限制（Redis计数器，可配置阈值）
- 文件上传魔数字节校验（17种文件类型）
- 文件大小限制（继承Flask MAX_CONTENT_LENGTH）
- Content-Security-Policy响应头（生产模式）
- X-Content-Type-Options / X-Frame-Options / X-XSS-Protection
- SQL注入防护（SQLAlchemy参数化查询）
- 生产环境堆栈信息不泄露
- 角色权限控制（admin → adm1/adm2/adm3 → user）

## 环境变量

参见 `backend/.env.example`，关键配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SECRET_KEY` | Flask密钥 | - |
| `JWT_SECRET_KEY` | JWT签名密钥 | - |
| `DATABASE_URL` | 数据库连接串 | `sqlite:///garden_asset.db` |
| `REDIS_URL` | Redis连接串 | `redis://localhost:6379/0` |
| `BLOCKCHAIN_ENABLED` | 启用区块链 | `false` |
| `AI_ENABLED` | 启用AI功能 | `true` |
| `ZHIPU_API_KEY` | 智谱AI密钥 | - |
| `BAIDU_OCR_API_KEY` | 百度OCR密钥 | - |

## 许可证

MIT License
