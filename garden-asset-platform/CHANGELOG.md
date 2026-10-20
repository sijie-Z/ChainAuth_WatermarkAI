# CHANGELOG

## [1.5.0] - 2026-10-19

### Added
- **严格 Git Flow**：`main` / `develop` / `feature/*` / `release/*` / `hotfix/*`，配套本地钩子、分支校验工作流与 `scripts/gitflow.sh`
- **GitHub Actions 体系**：后端 pytest + ruff + 覆盖率棘轮、前端 ESLint + Vitest + 构建、CodeQL、Dependency Review、gitleaks、OpenSSF Scorecard、Docker 构建、actionlint
- **机器人**：Dependabot（目标 `develop`，patch/minor 自动合并）、CodeRabbit、labeler、stale、welcome、Release Drafter、`main → develop` 回合并提醒
- **视觉体系 v2「青绿山水 · 档案册」**：黛青/宣纸/墨/印章朱砂令牌，宋体标题 + 等宽数据字体；重做首页、登录、注册、后台壳、仪表盘、资产目录、证书、溯源与错误页
- **前端测试基座**：Vitest + @vue/test-utils + jsdom，覆盖工具函数、状态组件与用户 store，并接入 CI
- **后端安全回归**：新增限流 429、安全响应头、健康检查用例（后端共 87 个用例）
- **鲁棒性测试**：JPEG q50、噪声、50%–150% 缩放、非 8 倍数尺寸的回归覆盖
- **前端 E2E**：Playwright 5 个点击流用例，覆盖首页、移动端导航、溯源页、管理员登录、普通用户浏览资产，并接入 `e2e.yml`
- **矢量水印**：新增 SHP/ZIP 上传、嵌入、提取的算法与 API 回归，包含无 vr 的溯源场景
- **端到端验证**：`scripts/e2e_flow.py` 覆盖注册 → 上传 → 发布审核 → 水印 → 上链 → 证书 → 双审批 → 下载 → 溯源，全部跑通
- **工程文档**：`docs/GIT-FLOW.md`、`docs/CI-CHARTER.md`、`docs/UI-DESIGN.md`、`docs/REFERENCE-NOTES.md`

### Security
- **生产配置**：gunicorn 以 `create_app('production')` 启动，修复 Docker 实际运行在 DEBUG 模式（HSTS 缺失、调度器不启动、CSP 放宽）
- **密钥一致性**：未配置 `SECRET_KEY` / `JWT_SECRET_KEY` 时生成一次并持久化到 instance 目录，多 worker / 重启后 Token 不再随机失效
- **账号状态**：登出撤销 access token（jti 黑名单），禁用/封禁用户的旧 Token 立即失效
- **访问控制**：资产列表/详情的草稿可见性、标签与 AI 分析的对象级权限、授权审批的角色与 action 校验、已审批列表仅审批角色可读
- **公开溯源防护**：限流 10 次/分钟、20MB 文件上限、ZIP 解压体积/数量上限，临时目录用完即删

### Fixed
- **矢量水印**：默认 RGBA 水印按二维读取崩溃、水印未二值化、45×45 尺寸不匹配、`np.nditer` 对象数组报错、ZIP 资产无法读取；现已支持 SHP/ZIP 上传与提取，水印 ID 写入 `wm_id` 属性列，矢量溯源可命中资产
- **矢量几何**：多部件（MultiPoint / MultiLineString / MultiPolygon）按部件嵌入，空几何用占位保持要素下标，修复写回错位与 MultiPoint 被写成 None
- **AI 降级**：未安装模型/未配置 Key 时，AI 分析、问答、检索、侵权检测统一返回 503 与明确提示，不再 500
- **依赖兼容**：锁定 `fiona==1.9.6`、`pandas==2.2.3`，修复 geopandas 0.14 在新版 fiona/pandas 下无法读写 SHP
- **非图片资产**：文档/视频/模型不支持水印时返回 400 而非 500；前端自动禁用不支持的自动水印选项
- **栅格水印算法**：水印 ID 从未真正嵌入；原 DCT 符号判定在压缩后大量误码；彩色图被转灰度。现改为 ID + 水印图联合嵌入、QIM 低频量化、ID 五重重复编码、缩放自动恢复，彩色图保留颜色。实测 **JPEG q50、噪声、50%–150% 缩放均可还原 ID，NC≈1.0，PSNR≈35 dB**；裁剪仍是已知边界（需结合链上存证核验）
- **授权审批**：上传资产未写 `uploader_id` 导致创建授权时 500；adm1 看不到未分配申请、adm2 看不到一级已通过的申请
- **资产下载**：`send_file` 以 app.root_path 解析相对路径导致 500；现统一使用绝对路径
- **下载权限**：所有者与管理员可下载未发布资产（草稿）；已删除资产仅管理员可见
- **角色枚举**：资产统计、区块链上链与管理员装饰器统一为六种角色，移除不存在的 `adm3` / `super_admin`
- **调度器**：APScheduler 延迟导入，未安装时应用仍可正常启动
- **溯源接口**：引用不存在的 `Certificate.confirmed_at` 导致 500
- 限流器在 Flask-RESTful 资源中返回元组导致 500（应为 429）
- 测试环境缺少 JWT 密钥导致登录用例 500；测试间共享限流状态造成连锁失败
- `OperationLog` 使用 BIGINT 主键在 SQLite 下不自增
- 前端 ESLint 配置语法错误与 `ecmaVersion` 拼写错误
- 后端缺少 pytest/geopandas/shapely，生产镜像启动会失败；后端 Dockerfile 缺少健康检查所需的 curl
- 仪表盘图表初始化时机错误（loading 结束后容器才渲染）
- API 错误提示重复刷屏，5xx/网络错误改为友好提示并去重
- **中文文件名**：`secure_filename` 剥掉扩展名导致上传 500，改用原始扩展名 + UUID 存储名
- **水印格式**：16 位 / CMYK / 调色板图像统一归一化读取，RGBA 保留 alpha；彩色图改为逐通道提取后多数表决，噪声图 NC 从 0.87 提升到 0.998
- **区块链**：配置合约地址时真实调用 `AssetRegistry.registerAsset`；交易失败不再签发证书或标记已存证
- **授权**：申请编码加入微秒与随机后缀避免唯一键冲突；新增 `/api/license/my-applications`；“审批中”筛选同时覆盖待一级审批与一级已通过；分页参数非法时不再 500
- **备份/调度**：SQLite 备份按 Flask-SQLAlchemy 的 instance 路径解析；调度器默认关闭，避免多 worker 重复执行
- **AI**：Milvus 初始化不再依赖应用上下文；临时文件在 Windows 上可正常删除
- **前端**：上传读取 `asset_id`、证书按嵌套结构解析、溯源读取顶层 `verified`、刷新失败清空 Pinia 登录态、角色枚举统一、后台上传路由、筛选参数、合同鉴权下载、假控件替换
- **移动端布局**：修复园林卡片被桌面规则覆盖导致的 2px 挤压与大片空白、页脚品牌竖排；后台资产表格重排，编码不再换行、操作列不再遮挡状态
- **状态文案**：水印/存证状态与节点状态统一为中文并覆盖 none/pending/verified 等全部取值；修正登录页演示账号密码
- **网页上传**：请求实例默认 `application/json` 导致 FormData 丢失文件字段（后端报“未上传文件”）；拦截器对 FormData 删除 Content-Type，由浏览器生成 multipart 边界
- **状态标签**：`StatusTag` 按 watermark/chain 输出“未嵌入/未存证”，资产详情与授权申请页不再统一显示“未处理”
- **上传草稿**：水印与上链完成前不再显示“提交发布”，避免未完成处理就发布
- **授权列表**：重排列宽，固定操作列不再遮挡申请时间
- **CI**：`main → develop` 改为提醒 issue（GITHUB_TOKEN 建的 PR 不会触发必需检查）、Dependabot scope 前缀、GHCR 镜像名小写、Docker 构建补充依赖文件触发路径

### Changed
- 运行时升级：Node.js 22、Python 3.11、当前 GitHub Actions 主版本（node24 运行时）
- 移除 THREE.js 粒子背景、emoji 图标、玻璃拟态与渐变按钮；Element Plus 改为通过 CSS 变量主题化
- 参考项目目录移出仓库并从发布历史中剔除，仓库体积从约 813 MB 降至约 0.5 MB
- 前端开发环境统一走 Vite proxy（`VITE_API_BASE_URL=/api`），不再硬编码 `http://localhost:5000/api`
- 移除未使用的 `minio` / `scipy` / `passlib` 依赖；文档明确 MinIO 为可选组件，文件当前默认存本地磁盘

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