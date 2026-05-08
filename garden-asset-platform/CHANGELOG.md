# CHANGELOG

## [1.4.0] - 2026-05-08

### Security
- **Redis限流初始化**：`extensions.py` 新增 Redis 客户端初始化，限流功能真正生效
- **内存限流降级**：Redis 不可用时自动降级到内存限流（单实例有效），不再静默跳过
- **HSTS安全头**：生产环境自动添加 `Strict-Transport-Security` 头
- **密钥缺失保护**：`SECRET_KEY`/`JWT_SECRET_KEY` 未配置时自动生成随机密钥并告警，不再使用硬编码默认值
- **健康检查增强**：`/health` 端点现在检查数据库连接，异常时返回 503

### Fixed
- **重复Axios实例**：移除死代码 `utils/request.js`，统一使用 `api/index.js`
- **Token刷新双倍错误**：修复刷新失败时显示两条错误消息的问题
- **Token刷新并发**：添加队列机制防止多个请求同时触发刷新
- **根Dockerfile**：从 `python run.py` 改为 `gunicorn`，修复健康检查路径 `/api/health` → `/health`
- **路由守卫403**：权限不足时跳转 `/403` 页面而非 `/home`

### Performance
- **THREE.js代码分割**：从主包分离为独立chunk（444KB），仅首页加载
- **Element Plus图标优化**：移除全局注册循环，依赖 unplugin 自动导入，减少 135KB
- **ECharts保持独立chunk**：1022KB独立加载

### Added
- **403错误页面**：专用权限不足页面
- **ErrorBoundary组件**：Vue错误边界，防止组件渲染错误导致白屏
- **移动端响应式**：5个用户页面添加 @media 查询（detail、upload、license/apply、license/my、trace）
- **SEO元标签**：Open Graph、robots、theme-color
- **任务调度器初始化**：生产环境自动启动备份/清理/授权过期检查

## [1.3.0] - 2026-05-08

### Security
- **XSS输入防护**：注册接口检测HTML标签，防止脚本注入
- **输入验证工具**：新增 `has_html_tags()` 和 `sanitize_text()` 函数

### Fixed
- **admin_header测试fixture**：注册后直接在数据库中提升角色，绕过注册接口的角色强制
- **test_watermark.py重复类**：移除重复的 `TestBlockchain` 类，补充水印嵌入/提取/溯源测试
- **文档自相矛盾**：DEVELOPMENT.md 同时将 Docker/CI/CD 列为"已完成"和"待完成"
- **虚假100%完成度**：修正核心模块完成度为实际值（80-95%）

### Added
- **区块链模拟数据增强**：生成FISCO BCOS风格的交易哈希、区块号、Gas消耗、合约地址
- **BlockchainTransaction.to_dict()**：返回 `gas_used`、`from_address`、`block_hash`、`confirmations`
- **Certificate.to_dict()**：返回 `file_hash`、`ownership_type`、`valid_from/until`
- **前端共享组件注册**：StatCard、StatusTag、EmptyState 全局注册并集成到视图
- **设计系统统一**：5个视图（detail、upload、license/apply、license/my、trace）从硬编码颜色迁移到SCSS变量
- **资产详情骨架屏**：加载时显示骨架屏，加载失败显示错误状态+重试按钮
- **授权流程测试**：双重审批完整流程测试、拒绝流程测试
- **密码修改测试**：成功、旧密码错误、新密码太短
- **注册角色注入测试**：验证 `role: "admin"` 被忽略
- **adm1/adm2测试fixtures**：资产管理员认证头

## [1.2.0] - 2026-05-08

### Security (CRITICAL)
- **注册接口角色注入漏洞**：用户可在注册时传入 `role: "admin"` 获取管理员权限，已强制硬编码为 `user` 角色
- **JWT Token 配置类型错误**：`JWT_ACCESS_TOKEN_EXPIRES` 为整数而非 `timedelta`，导致 Token 过期时间异常
- **CORS 允许所有来源**：`CORS(app)` 无限制，改为从 `CORS_ORIGINS` 环境变量读取白名单
- **生产环境安全加固**：新增 `ProductionConfig`，启用 `SESSION_COOKIE_SECURE`、`HTTPONLY`、`PREFERRED_URL_SCHEME=https`

### Fixed
- **AI/区块链服务未初始化**：`create_app()` 未调用 `ai_service.init_app()` 和 `blockchain_service.init_app()`
- **裸 except 捕获**：security.py、log.py、blockchain_service.py 中的 `except:` 改为具体异常类型
- **tasks.py 方法调用错误**：`AIService.analyze_asset(asset)` 修正为 `ai_service.process_asset(asset)`
- **限流静默失败**：Redis 不可用时 `except Exception: pass` 改为记录警告日志
- **资产预览 404**：detail.vue 引用不存在的 `/api/assets/{id}/preview`，改为使用 `thumbnail_path` 或 SVG 占位图
- **设置页面虚假 API**：使用 `setTimeout` 模拟，已接入 `userApi.updateProfile` 和 `userApi.changePassword`
- **路由守卫问题**：未登录访问受保护页面无反馈、已登录用户访问 /login 无重定向、子路由角色权限继承失效

### Added
- **修改密码端点**：`POST /api/user/change-password`，验证旧密码后更新
- **用户信息更新端点**：`PUT /api/user/current`，支持更新昵称、邮箱、手机号
- **前端 userApi 模块**：新增 `updateProfile` 和 `changePassword` API 方法
- **路由守卫增强**：`ElMessage.warning` 权限不足提示、已登录用户自动重定向到 /assets
- **requirements.txt 清理**：移除未使用的 pandas/pytz，新增 gunicorn、opencv-python-headless、scipy

### Changed
- `MAX_CONTENT_LENGTH` 配置支持环境变量覆盖（默认 500MB）

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