# CHANGELOG

## [1.1.0] - 2026-05-08

### Fixed
- CSP `script-src` 指令在 DEBUG 模式下产生重复项，现在统一为单条指令
- nginx.conf 缺少 `client_max_body_size`（默认 1MB 导致上传失败），设置为 500m
- docker-compose 中数据库凭证硬编码，改为环境变量引用
- docker-compose 中 `depends_on` 缺少健康检查条件，backend 可能在 DB 就绪前启动
- 移除 middleware.py 中未使用的 `cors_headers` 死代码

### Added
- 登录接口限流（5次/分钟）和注册接口限流（3次/小时）
- 资产上传接口限流（10次/分钟）
- config.py 中新增限流配置项（RATELIMIT_LOGIN/REGISTER/API）
- nginx.conf 安全响应头（X-Content-Type-Options, X-Frame-Options, CSP 等）
- docker-compose 中 PostgreSQL/Redis/MinIO 健康检查
- backend/.dockerignore 和 frontend/.dockerignore
- 项目根目录 .env.example（Docker Compose 环境变量模板）
- 测试用例：园林模块（7个）、授权模块（9个）、区块链模块（8个）
- 共享测试 fixtures：admin_header, sample_garden, sample_asset
- 前端骨架屏：资产列表页统计卡片+网格、我的授权页表格、管理后台资产表格

### Changed
- conftest.py 扩展测试 fixtures 体系

## [1.0.0] - 2026-04-26

### Added
- 完整的Flask后端架构
- Vue 3前端框架
- 数字水印算法 (矢量+栅格)
- 区块链存证功能
- 授权审批工作流
- AI智能分析集成
- Docker容器化支持
- CI/CD流水线

### 后端功能

#### 数据模型 (8个)
- User - 用户模型
- Garden - 园林模型
- Asset - 资产模型
- License - 授权模型
- Certificate - 证书模型
- OperationLog - 操作日志
- Favorite - 用户收藏
- DownloadRecord - 下载记录

#### API资源 (8个模块, 30+端点)
- auth - 认证模块 (注册/登录/登出/刷新Token)
- asset - 资产管理
- garden - 园林信息
- watermark - 水印处理 (嵌入/提取/溯源)
- blockchain - 区块链存证
- license - 授权管理
- ai - AI智能分析

#### 业务服务 (3个)
- WatermarkService - 水印处理服务
- BlockchainService - 区块链服务
- AIService - AI服务

#### 工具模块 (14个)
- response - 统一响应格式
- file_utils - 文件处理
- datetime_utils - 日期时间
- auth - JWT认证装饰器
- cache - Redis缓存
- errors - 错误处理
- commands - Flask CLI
- validators - 数据验证
- exceptions - 自定义异常
- middleware - 中间件
- logger - 日志配置
- jwt_callbacks - JWT回调
- signals - 信号处理
- geometry - 几何工具
- enums - 枚举定义
- permissions - 权限配置

### 前端功能

#### 页面组件 (19个)
- 首页模块: index, login, register
- 资产模块: list, detail, upload
- 溯源模块: trace
- 授权模块: apply, my
- 证书模块: certificate
- 管理后台: layout, dashboard, assets, watermark, license-pending, license-approved, blockchain, users

#### 公共组件 (4个)
- EmptyState - 空状态
- LoadingWrapper - 加载包装
- StatCard - 统计卡片
- StatusTag - 状态标签

#### 工具模块
- utils - 工具函数
- request - HTTP请求
- charts - 图表配置
- notify - 通知提示
- hooks - Vue Hooks
- constants - 常量定义
- types - 类型定义

### 基础设施
- Docker & Docker Compose
- Nginx反向代理
- Makefile管理命令
- GitHub Actions CI/CD
- OpenAPI文档

### 文档
- README.md - 项目说明
- DEVELOPMENT.md - 开发文档
- deployment.md - 部署文档
- api.yaml - API规范
- file-list.md - 文件清单

## 技术栈

### 后端
- Flask 3.0
- SQLAlchemy 2.0
- Flask-JWT-Extended
- Flask-RESTful
- Pillow / GeoPandas
- Celery / Redis

### 前端
- Vue 3.4
- Vite 5
- Element Plus
- Pinia
- Vue Router
- ECharts

### 数据库
- PostgreSQL
- Redis
- Milvus

### 区块链
- FISCO BCOS
- Web3.py

### AI
- GLM-4-Flash
- CLIP / DINOv2
- sentence-transformers