# 苏州园林数字资产安全分发与溯源系统

> 从"版权裸奔"到"链上确权"：基于数字水印和AI推理的苏州园林数字资产安全分发与溯源系统

## 项目简介

本系统面向苏州园林数字资产（图片、3D模型、矢量图纸等）的版权保护与安全分发需求，构建了**水印嵌入 → 存证记录 → 可选 AI 辅助 → 溯源追踪**的保护链路。默认使用本地模拟链与关闭 AI；正式接入 FISCO BCOS、模型与 OCR 需按部署文档额外配置。

> 哪些能力已真实可用、哪些仍是演示，以及下一阶段的重构计划，见 [能力完整性审计](docs/COMPLETENESS-AUDIT.md)。

### 核心功能

| 模块 | 功能 | 技术实现 |
|------|------|----------|
| 资产管理 | 数字资产上传、浏览、分类、检索、下载 | Vue3 + Flask + MinIO |
| 数字水印 | DCT + QIM 盲水印嵌入与提取，抗 JPEG 压缩、噪声与 50%–150% 缩放 | Python OpenCV + NumPy |
| 区块链存证 | 文件哈希与水印编号生成存证记录与证书；默认本地模拟，可配置接入 FISCO BCOS | FISCO BCOS + Python SDK（可选） |
| AI 辅助（可选） | 以图搜图、侵权辅助检测、智能问答；默认关闭，需安装模型与 API Key | CLIP + Milvus + 智谱 GLM（可选） |
| 授权分发 | 在线申请→双重审批→合同管理→下载控制 | Flask + JWT |
| 协作与版本 | 评论/回复、影像区域标注、版本上传/恢复 | Vue3 + Flask |

### 技术架构

```
浏览器 ──→ Nginx ──→ Vue3 SPA (静态资源)
                      │
                      ├──→ Flask REST API ──→ PostgreSQL
                      │                    ├──→ Redis (缓存/限流)
                      │                    ├──→ MinIO (可选对象存储，当前默认本地磁盘)
                      │                    └──→ Milvus (向量检索)
                      │
                      └──→ FISCO BCOS (区块链存证)
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3.4, Vite 5, Pinia, Element Plus, ECharts |
| 后端 | Flask 3.0, Flask-RESTful, SQLAlchemy, Flask-JWT-Extended |
| 存储 | PostgreSQL, Redis, Milvus；MinIO 为可选服务（当前默认本地磁盘） |
| 区块链 | FISCO BCOS 3.x（可选，默认本地模拟存证） |
| AI | CLIP / 智谱 GLM（可选，需自行安装与配置） |
| 部署 | Docker Compose, Gunicorn, Nginx |

## 快速开始

> 第一次使用建议先读 [使用指南](docs/USER-GUIDE.md)，或启动后访问 `/guide` 查看站内引导。

### 环境要求

- Python 3.11+ / Node.js 22+
- Docker & Docker Compose（推荐）

### Docker 一键部署

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env，填入数据库密码等 Docker Compose 变量

# 启动所有服务（后端、前端、PostgreSQL、Redis、MinIO）
docker-compose up -d

# 初始化数据库
docker exec garden-backend python scripts/init_db.py

# 填充示例数据（可选）
docker exec garden-backend python scripts/create_test_data.py
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
# 后端测试（249个用例，覆盖API/模型/安全）
cd backend && python -m pytest tests/ -v

# 前端生产构建
cd frontend && npm run build
```

### 默认账号

管理员 `admin / admin123` · 审批员 `adm1, adm2 / 123456` · 用户 `user1, user2 / 123456`

> 正式部署前请通过 `ADMIN_INITIAL_PASSWORD` 指定初始管理员密码，或登录后立即修改；演示账号可用 `python -m flask reset-password` 重置。

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
│   ├── algorithm/                 # 水印算法库（DCT+QIM/矢量）
│   ├── contracts/                 # Solidity智能合约
│   ├── scripts/                   # 初始化与种子数据脚本
│   ├── tests/                     # pytest测试（249个用例）
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
| GET | `/api/assets/:id/thumbnail` | 资产缩略图（`?size=card` 返回列表卡片图） |
| GET | `/api/assets/:id/related` | 同园林相关资产 |
| GET | `/api/assets/:id/evidence` | 资产证据链（上传/水印/存证/证书/发布/授权/下载） |
| GET/POST | `/api/assets/:id/versions` | 版本历史 / 上传新版本（文件替换并重置水印） |
| GET | `/api/assets/:id/versions/:version_id/download` | 下载指定历史版本 |
| POST | `/api/assets/:id/versions/:version_id/restore` | 恢复历史版本（生成新版本，不删除历史） |
| GET/POST | `/api/assets/:id/comments` | 评论列表 / 发表评论或回复 |
| PUT/DELETE | `/api/assets/:id/comments/:comment_id` | 编辑 / 删除评论 |
| GET/POST | `/api/assets/:id/annotations` | 区域标注列表 / 新增标注 |
| PUT/DELETE | `/api/assets/:id/annotations/:annotation_id` | 更新状态或内容 / 删除标注 |
| GET/POST | `/api/assets/:id/shares` | 查询/创建公开分享链接（有效期、访问码、下载权限） |
| GET | `/api/shares/:token` | 公开分享页数据（免登录，返回资产与证据链） |
| GET | `/api/shares/:token/download` | 通过分享链接下载（受分享设置限制） |
| DELETE | `/api/shares/:id` | 撤销分享链接 |
| GET/POST/DELETE | `/api/assets/:id/favorite` | 查询/添加/取消收藏 |
| GET | `/api/favorites` | 我的收藏列表 |
| GET | `/api/downloads/my` | 我的下载记录 |
| GET | `/api/downloads` | 全平台下载台账（管理员，支持筛选与汇总） |
| GET | `/api/assets/:id/downloads` | 单件资产下载摘要（所有者/管理员） |
| GET/POST | `/api/collections` | 我的合集列表 / 新建合集 |
| GET/PUT/DELETE | `/api/collections/:id` | 合集详情 / 编辑 / 删除 |
| POST | `/api/collections/:id/assets` | 批量加入资产 |
| DELETE | `/api/collections/:id/assets/:asset_id` | 从合集移除资产 |
| GET/POST | `/api/gardens` | 园林列表 / 新建园林档案（管理员） |
| PUT/DELETE | `/api/gardens/:id` | 编辑 / 删除园林档案（管理员，仍有资产时拒绝删除） |

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

### 待办与审计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/notifications` | 当前用户的待办提醒（审批、申请状态、到期），含未读数与已读状态 |
| POST | `/api/notifications/read` | 标记单条或全部待办为已读 |
| GET | `/api/logs` | 操作日志（管理员，支持模块/结果/日期/关键词筛选） |
| GET | `/api/system/status` | 系统能力状态（管理员：AI/链/Redis/调度器真实启用情况） |

### 授权管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/license/apply` | 申请使用授权 |
| GET | `/api/license/pending` | 待审批列表（审批员） |
| POST | `/api/license/approve/:id` | 审批（通过/拒绝） |
| GET | `/api/license/approved` | 已审批列表 |
| GET | `/api/license/my` | 我的授权 |
| GET | `/api/license/my-applications` | 我的申请 |
| POST | `/api/license/applications/:id/cancel` | 撤回申请 |
| GET | `/api/license/:id/contract` | 查看授权合同 |

## 安全特性

- JWT双Token认证（Access 24h + Refresh 30d）；登出同时撤销 refresh token，改密/重置密码后旧 token 立即失效
- 请求频率限制（Redis计数器，可配置阈值；Redis异常不影响业务执行）
- 文件上传魔数字节校验（17种文件类型）
- 文件大小限制（继承Flask MAX_CONTENT_LENGTH）
- Content-Security-Policy响应头（生产模式）
- X-Content-Type-Options / X-Frame-Options / X-XSS-Protection
- SQL注入防护（SQLAlchemy参数化查询）
- 生产环境堆栈信息不泄露
- 角色权限控制（admin / asset_admin / license_admin / adm1 / adm2 / user）

## 环境变量

Docker 部署见 `garden-asset-platform/.env.example`；本地开发见 `backend/.env.example`。关键配置项：

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
| `ADMIN_INITIAL_PASSWORD` | 初始化脚本创建 admin 时使用的密码 | `admin123`（仅演示） |
| `TRUST_PROXY_HEADERS` | 是否信任反向代理的 `X-Forwarded-For`（仅在后端不直接暴露时开启） | `false` |

> 多 worker 部署（4 个 gunicorn worker）默认关闭任务调度器，避免备份/授权过期任务重复执行。如需启用，设置 `SCHEDULER_ENABLED=true`，并确保只运行一个调度进程（或改用外部 cron）。

> 文件默认保存在 `backend/uploads/`（Docker 中为挂载卷）。`docker-compose.yml` 中的 MinIO 服务为可选组件，当前版本尚未接入对象存储后端。

> AI 对话 SDK `zhipuai` 的元数据要求 `pyjwt<2.9`，与安全版 PyJWT（≥2.11）冲突，因此不在核心依赖中。需要 GLM 对话时执行：`pip install --no-deps zhipuai==2.0.1 httpx pydantic cachetools`。

## 许可证

MIT License
