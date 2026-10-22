# 苏州园林数字资产安全分发与溯源系统

## 项目概述

从"版权裸奔"到"链上确权"：基于数字水印和AI推理的苏州园林数字资产安全分发与溯源系统

本项目是一个完整的数字资产管理系统，集成了数字水印、区块链存证、智能授权审批、AI分析等核心功能，为苏州园林数字资产提供全生命周期保护。

## 技术架构

### 后端 (Flask + SQLAlchemy)

```
backend/
├── app/
│   ├── __init__.py              # Flask应用工厂
│   ├── config.py                # 配置文件
│   ├── extensions.py            # Flask扩展(db, migrate, jwt)
│   ├── models/                  # 数据模型 (8个)
│   │   ├── user.py              # 用户模型 (User, UserToken)
│   │   ├── garden.py            # 园林模型 (Garden)
│   │   ├── asset.py             # 资产模型 (Asset, AssetTag, AssetFeature)
│   │   ├── license.py           # 授权模型 (License, LicenseApplication, LicenseContract)
│   │   ├── blockchain.py        # 区块链模型 (BlockchainTransaction, Certificate)
│   │   ├── log.py               # 日志模型 (OperationLog)
│   │   └── extra.py             # 扩展模型 (Favorite, DownloadRecord, SystemConfig)
│   ├── resources/               # API资源 (8个模块)
│   │   ├── auth.py              # 认证API (7个端点)
│   │   ├── asset.py             # 资产API
│   │   ├── garden.py            # 园林API
│   │   ├── watermark.py         # 水印API (5个端点)
│   │   ├── blockchain.py        # 区块链API (5个端点)
│   │   ├── license.py           # 授权API (5个端点)
│   │   └── ai.py                # AI功能API (4个端点)
│   ├── services/                # 业务服务 (3个)
│   │   ├── watermark_service.py # 水印服务
│   │   ├── blockchain_service.py# 区块链服务
│   │   └── ai_service.py        # AI服务
│   ├── utils/                   # 工具函数 (7个模块)
│   │   ├── response.py          # 统一响应格式
│   │   ├── file_utils.py        # 文件处理工具
│   │   ├── datetime_utils.py    # 日期时间工具
│   │   ├── auth.py              # JWT权限装饰器
│   │   ├── cache.py             # Redis缓存工具
│   │   ├── errors.py            # 错误处理器
│   │   └── commands.py          # Flask CLI命令
│   └── tasks.py                 # 旧任务入口（转发到 services/task_service.py 持久化队列）
├── algorithm/                   # 水印算法
│   ├── vector/                  # 矢量水印
│   │   ├── embed.py             # 坐标扰动嵌入
│   │   └── extract.py           # 水印提取
│   ├── raster/                  # 栅格水印
│   │   ├── embed.py             # DCT+QIM 嵌入
│   │   └── extract.py           # 水印提取
│   └── utils/                   # 算法工具
│       ├── get_coor.py          # 坐标提取
│       ├── to_geodataframe.py   # GeoDataFrame转换
│       └── nc.py                # NC值计算
├── contracts/                   # 智能合约
│   ├── AssetRegistry.sol        # FISCO BCOS合约
│   └── abi.py                   # 合约ABI定义
├── scripts/                     # 脚本文件
│   ├── init_db.py               # 数据库初始化
│   ├── create_test_data.py      # 测试数据生成
│   └── create_watermark.py      # 默认水印生成
├── migrations/                  # 数据库迁移
├── uploads/                     # 上传文件目录
├── data/                        # 数据文件目录
├── run.py                       # 启动入口
├── requirements.txt             # Python依赖
└── .env.example                 # 环境变量示例
```

### 前端 (Vue 3 + Vite + Element Plus)

```
frontend/
├── public/
│   └── favicon.svg              # 网站图标
├── src/
│   ├── main.js                  # 入口文件
│   ├── App.vue                  # 根组件
│   ├── router/
│   │   └── index.js             # 路由配置 (20+路由)
│   ├── stores/
│   │   └── user.js              # Pinia用户状态
│   ├── api/
│   │   ├── index.js             # Axios实例配置
│   │   └── modules.js           # API模块 (7个)
│   ├── components/              # 公共组件
│   │   ├── common/
│   │   │   ├── EmptyState.vue   # 空状态组件
│   │   │   ├── LoadingWrapper.vue# 加载包装器
│   │   │   ├── StatCard.vue     # 统计卡片
│   │   │   └── StatusTag.vue    # 状态标签
│   │   └── index.js
│   ├── constants/
│   │   └── index.js             # 常量定义
│   ├── utils/
│   │   └── index.js             # 工具函数
│   └── views/                   # 页面组件 (19个)
│       ├── home/
│       │   ├── index.vue        # 首页
│       │   ├── login.vue        # 登录
│       │   └── register.vue     # 注册
│       ├── asset/
│       │   ├── list.vue         # 资产列表
│       │   ├── detail.vue       # 资产详情
│       │   └── upload.vue       # 上传资产
│       ├── trace/
│       │   └── index.vue        # 溯源查询
│       ├── license/
│       │   ├── apply.vue        # 申请授权
│       │   └── my.vue           # 我的授权
│       ├── certificate/
│       │   └── index.vue        # 存证证书
│       └── admin/               # 管理后台
│           ├── layout.vue       # 后台布局
│           ├── dashboard.vue    # 仪表盘
│           ├── assets.vue       # 资产管理
│           ├── watermark.vue    # 水印管理
│           ├── license-pending.vue   # 待审批
│           ├── license-approved.vue  # 已审批
│           ├── blockchain.vue   # 存证管理
│           └── users.vue        # 用户管理
├── index.html                   # HTML模板
├── vite.config.js               # Vite配置
├── package.json                 # NPM依赖
├── .env.development             # 开发环境变量
└── .env.production              # 生产环境变量
```

## 核心功能模块

### 1. 用户认证系统
- 用户注册/登录 (JWT认证)
- 角色权限管理 (user, asset_admin, license_admin, adm1, adm2, admin)
- Token刷新机制
- 操作日志记录

### 2. 数字水印系统
- **矢量水印**: 基于坐标扰动算法，适用于SHP地理数据
- **栅格水印**: DCT + QIM 低频量化（LSB 仅作可选简单回退），适用于影像数据
- **水印ID生成**: ZY-{园林编码}-{类型编码}-{时间戳}-{随机码}
- 支持批量处理
- NC值验证水印完整性

### 3. 区块链存证系统
- 支持FISCO BCOS联盟链
- 资产上链存证
- 存证验证与查询
- 电子证书生成
- 支持模拟模式(无真实链也可运行)

### 4. 授权审批流程
- 双重审批机制 (adm1一级审批 + adm2二级审批)
- 多种授权类型 (个人、学术、商业、展览、衍生创作)
- 授权合同生成
- 区块链授权记录

### 5. AI智能功能
- CLIP/DINOv2图像特征提取
- Milvus向量相似度检索
- 场景智能分类
- 相似资产搜索
- 潜在侵权检测
- GLM-4-Flash智能问答

### 6. 溯源查询系统
- 上传图片溯源
- 水印ID溯源
- 区块链存证验证
- 溯源报告生成

## API端点总览

### 认证模块 `/api`
| 方法 | 端点 | 说明 | 认证 |
|-----|------|-----|------|
| POST | /register | 用户注册 | 否 |
| POST | /login | 用户登录 | 否 |
| POST | /logout | 用户登出 | 是 |
| POST | /refresh | 刷新Token | 是(Refresh) |
| GET | /user/current | 当前用户信息 | 是 |
| GET | /users | 用户列表 | 管理员 |
| PUT | /users/:id | 更新用户 | 是 |

### 资产模块 `/api/assets`
| 方法 | 端点 | 说明 | 认证 |
|-----|------|-----|------|
| GET | / | 资产列表(分页) | 是 |
| GET | /:id | 资产详情 | 是 |
| POST | /upload | 上传资产 | 是 |
| PUT | /:id | 更新资产 | 是 |
| DELETE | /:id | 删除资产 | 管理员 |

### 水印模块 `/api/watermark`
| 方法 | 端点 | 说明 | 认证 |
|-----|------|-----|------|
| POST | /embed | 嵌入水印 | 是 |
| POST | /extract | 提取水印 | 是 |
| POST | /verify | 验证水印ID | 否 |
| POST | /trace | 上传图片溯源 | 否 |
| GET | /logs | 操作日志 | 管理员 |

### 区块链模块 `/api/blockchain`
| 方法 | 端点 | 说明 | 认证 |
|-----|------|-----|------|
| POST | /register | 上链存证 | 是 |
| GET | /verify/:id | 存证验证 | 否 |
| POST | /verify | 水印ID验证 | 否 |
| GET | /certificate/:id | 证书详情 | 否 |
| GET | /history | 存证历史 | 否 |
| GET | /status | 链状态 | 否 |

### 授权模块 `/api/license`
| 方法 | 端点 | 说明 | 认证 |
|-----|------|-----|------|
| POST | /apply | 申请授权 | 是 |
| GET | /pending | 待审批列表 | adm1/adm2 |
| POST | /approve/:id | 审批操作 | adm1/adm2 |
| GET | /approved | 已审批列表 | 是 |
| GET | /my | 我的授权 | 是 |

### AI模块 `/api/ai`
| 方法 | 端点 | 说明 | 认证 |
|-----|------|-----|------|
| POST | /analyze | 资产分析 | 是 |
| POST | /search | 相似搜索 | 是 |
| POST | /infringement | 侵权检测 | 是 |
| POST | /chat | 智能问答 | 是 |

### 园林模块 `/api/gardens`
| 方法 | 端点 | 说明 | 认证 |
|-----|------|-----|------|
| GET | / | 园林列表 | 否 |
| GET | /:id | 园林详情 | 否 |

## 数据库设计

### 核心表结构

| 表名 | 说明 | 主要字段 |
|-----|------|---------|
| users | 用户表 | id, username, email, role, status |
| gardens | 园林表 | id, name, code, location, unesco_heritage |
| assets | 资产表 | id, asset_code, title, asset_type, watermark_status, chain_status |
| asset_tags | 资产标签 | id, asset_id, tag_name |
| asset_features | 资产特征 | id, asset_id, feature_vector |
| licenses | 授权记录 | id, license_code, license_type, status |
| license_applications | 授权申请 | id, application_code, adm1_status, adm2_status |
| certificates | 存证证书 | id, certificate_id, tx_hash, block_number |
| operation_logs | 操作日志 | id, user_id, action, module |

## 开发进度

### ✅ 已完成

#### 后端
- [x] Flask应用工厂架构
- [x] 8个数据模型设计
- [x] 8个API资源模块 (30+端点)
- [x] 3个业务服务层
- [x] 水印算法迁移 (矢量+栅格)
- [x] 7个工具模块
- [x] 异步任务队列（async_tasks + worker + flask tasks run）
- [x] 数据库初始化脚本
- [x] Flask CLI命令
- [x] 错误处理中间件
- [x] JWT认证装饰器

#### 前端
- [x] Vue 3项目初始化
- [x] 19个页面组件
- [x] 4个公共组件
- [x] 路由配置与权限守卫
- [x] Pinia状态管理
- [x] Axios API封装 (7模块)
- [x] 工具函数库
- [x] 常量定义
- [x] 环境配置

#### 文档
- [x] README.md
- [x] DEVELOPMENT.md
- [x] backend/README.md
- [x] frontend/README.md

### 🚧 进行中

- [x] 前端单元测试 (Vitest，46 个用例)
- [ ] API文档 (Swagger UI)

### 📋 待完成

- [ ] HTTPS证书配置
- [ ] 性能优化 (懒加载、缓存策略)
- [ ] 数据库迁移脚本

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 22+
- PostgreSQL 14+ (或SQLite用于开发)
- Redis 6+ (可选，用于限流/缓存；异步任务队列使用数据库，不依赖 Redis)

### 后端启动

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

# 复制环境配置
cp .env.example .env

# 初始化数据库
python scripts/init_db.py

# 创建测试数据 (可选)
python scripts/create_test_data.py

# 创建水印图片
python scripts/create_watermark.py

# 启动服务
python run.py
```

### 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 开发模式运行
npm run dev

# 生产构建
npm run build
```

### 默认账号

| 用户名 | 密码 | 角色 |
|-------|------|------|
| admin | admin123 | 超级管理员 |
| adm1 | 123456 | 一级审批员 |
| adm2 | 123456 | 二级审批员 |
| asset_mgr | 123456 | 资产管理员 |
| license_mgr | 123456 | 授权管理员 |
| user1 | 123456 | 普通用户 |

### Flask CLI命令

```bash
# 创建管理员
flask create-admin --username admin --password admin123

# 初始化园林数据
flask init-gardens

# 重置用户密码
flask reset-password user1 newpassword
```

## 技术栈详情

### 后端技术
| 技术 | 版本 | 用途 |
|-----|------|------|
| Flask | 3.0 | Web框架 |
| Flask-RESTful | 0.3.10 | RESTful API |
| SQLAlchemy | 2.0.23 | ORM |
| Flask-Migrate | 4.0.5 | 数据库迁移 |
| Flask-JWT-Extended | 4.6.0 | JWT认证 |
| Flask-CORS | 4.0.0 | 跨域支持 |
| 异步任务 | 数据库队列 | 水印/存证任务入队、重试与超时对账（`flask tasks run`） |
| Pillow | 10.1.0 | 图像处理 |
| GeoPandas | 0.14.1 | 空间数据处理 |
| zhipuai | 2.0.1 | GLM API |

### 前端技术
| 技术 | 版本 | 用途 |
|-----|------|------|
| Vue | 3.4 | 前端框架 |
| Vite | 5.x | 构建工具 |
| Element Plus | 2.x | UI组件库 |
| Pinia | 2.x | 状态管理 |
| Vue Router | 4.x | 路由管理 |
| Axios | 1.x | HTTP客户端 |

### 基础设施
| 技术 | 用途 |
|-----|------|
| PostgreSQL | 主数据库 |
| Redis | 缓存/消息队列 |
| FISCO BCOS | 区块链 |
| Milvus | 向量数据库 |
| MinIO | 对象存储（可选，当前默认本地磁盘） |

## 项目亮点

1. **自研水印算法**: 矢量坐标扰动 + DCT/QIM栅格水印，兼顾鲁棒性与不可见性
2. **双重审批机制**: 完善的授权工作流，确保资产安全分发
3. **区块链存证**: 基于FISCO BCOS联盟链，提供可信存证
4. **AI智能分析**: 集成GLM-4、CLIP等模型，提供智能分析与检索
5. **全栈自主研发**: 从算法到应用层完全自主开发

## 更新日志

### 2026-05-08 (v1.2.0)
- ✅ 修复注册接口角色注入漏洞（硬编码role='user'）
- ✅ 修复JWT Token配置类型错误（timedelta）
- ✅ 修复CORS允许所有来源（改为配置白名单）
- ✅ 生产环境安全加固（Secure Cookie、HTTPS）
- ✅ AI/区块链服务初始化修复
- ✅ 输入XSS防护（HTML标签检测）
- ✅ 区块链模拟数据增强（FISCO BCOS风格哈希）
- ✅ 后端测试修复与扩展（admin fixture、授权流程、密码修改）
- ✅ 前端设计系统统一（SCSS变量替换硬编码颜色）
- ✅ 共享组件注册与集成（StatCard、StatusTag、EmptyState）
- ✅ 资产详情页骨架屏与错误状态

### 2026-05-08 (v1.1.0)
- ✅ CSP安全头修复
- ✅ 登录/注册/上传接口限流
- ✅ Docker Compose健康检查
- ✅ 园林/授权/区块链模块测试
- ✅ 前端骨架屏加载状态

### 2026-04-26 (v1.0.0)
- ✅ Flask后端架构（8模型、8资源模块、30+端点）
- ✅ Vue 3前端（19页面、4组件、Pinia状态管理）
- ✅ 数字水印算法（矢量+栅格）
- ✅ 区块链存证（FISCO BCOS）
- ✅ AI智能分析（GLM-4、CLIP）
- ✅ Docker容器化部署
- ✅ GitHub Actions CI/CD
- ✅ 项目文档体系

---

## 最终统计

**项目总文件数: 245个**（2026-10-20 统计，git 跟踪文件）

| 类别 | 数量 | 说明 |
|-----|------|------|
| Python文件 | 89 | 后端、算法、测试与脚本 |
| Vue组件 | 28 | 页面 + 公共组件 |
| JavaScript/CJS | 25 | 前端工具、配置与 API |
| Markdown文档 | 24 | 项目与工程文档 |
| 其他 | 79 | Docker、YAML、JSON、样式与静态资源 |

**代码行数（Python + Vue + JS）: ~25,600 行**

### 核心功能完成度

| 模块 | 状态 | 完成度 | 说明 |
|-----|------|-------|------|
| 用户认证 | ✅ | 95% | JWT双Token、角色权限、密码修改 |
| 资产管理 | ✅ | 95% | 上传/下载/分类/去重/收藏 |
| 水印处理 | ✅ | 90% | 矢量+栅格算法、嵌入/提取/溯源 |
| 区块链存证 | ✅ | 85% | 模拟模式完整、真实链需配置FISCO BCOS |
| 授权审批 | ✅ | 95% | 双重审批、合同生成、5种授权类型 |
| AI分析 | ✅ | 80% | GLM-4/CLIP集成，需配置API Key |
| 前端界面 | ✅ | 90% | 19页面+骨架屏+设计系统 |
| 单元测试 | ✅ | 95% | 后端 296 个用例 + 前端 46 个用例 + 16 个 Playwright 用例，CI 全量执行 |
| Docker部署 | ✅ | 90% | 多服务编排、健康检查、HTTPS待配置 |
| CI/CD | ✅ | 100% | Git Flow + 16 个工作流 + 机器人体系 |

### 技术亮点

1. **自研水印算法**: 矢量坐标扰动 + DCT/QIM栅格水印
2. **双重审批机制**: adm1+adm2完整工作流
3. **区块链存证**: FISCO BCOS联盟链集成
4. **AI智能分析**: GLM-4 + CLIP特征提取
5. **向量检索**: Milvus相似度搜索
6. **微服务架构**: Docker容器化部署
7. **完整测试**: pytest单元测试
8. **CI/CD**: GitHub Actions自动化

---

## 许可证

MIT License

## 联系方式

苏州园林数字资产平台团队 - 2026