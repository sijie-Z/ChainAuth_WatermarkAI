# CHANGELOG

## [Unreleased]

### Added
- 批量侵权巡检：管理员一次上传最多 20 个疑似副本，异步提取水印并匹配已发布资产，匹配项自动生成待处理线索；未匹配文件自动清理
- 本地内存安全测试入口 `scripts/run_tests.py`：每个测试文件单独子进程运行，限制 OpenBLAS/OpenMP/NumExpr 线程数，显示单文件峰值内存；Windows 上全量 300 个用例实测通过，单文件峰值 256MB
- 水印算法改为按需导入：API 启动和大多数测试不再加载 OpenCV/GeoPandas/Pandas，测试进程基线内存从数百 MB 降到约 95MB
- 侵权线索：公开溯源页可提交疑似盗用文件/链接/说明，服务端尝试水印匹配资产；后台新增“侵权线索”页，支持受理、确认、驳回、文件预览/下载，确认或驳回通知举报人与权利人
- 授权版本绑定：审批时记录文件版本，资产更新后旧授权不能直接下载新版本；证书/合同/授权详情显示对应版本，历史授权保持兼容
- 通知渠道：站内 SSE 实时推送（Authorization 头鉴权、断线补发、心跳保活）+ 服务端邮件偏好（按资产/授权/任务/侵权线索分组）；`notification_deliveries` 记录投递状态，SMTP 失败自动退避重试；账号设置页可保存偏好并发送测试邮件
- 授权范围执行：申请与授权新增使用目的、使用渠道、可下载格式、授权地域、下载次数上限；下载时校验申报用途/地域/格式/剩余次数，超范围返回 403 并写入下载台账；历史授权保持不限制
- 下载台账区分成功与超范围拒绝，新增拒绝原因、申报用途、地域和结果筛选；后台仪表盘增加通知渠道与邮件投递计数
- 异步任务队列：水印/存证任务写入 `async_tasks` 表，由进程内 worker 或 `flask tasks run` 执行；支持入队去重、进度查询、失败自动重试与退避、手动重试/取消、超时对账；资产详情、批量上传均改为异步提交并轮询结果，不再占用请求线程
- 版本级存证证书：证书新增 `version_id`/`version_no`，同一资产不同版本各自持证；上传新版本会重置当前水印与存证状态，旧证书保留并在版本列表/证书页标注“历史版本”；公开验证会拒绝用旧证书冒充当前版本
- `docker compose` 新增独立 `worker` 服务；后台仪表盘“系统能力”增加异步任务排队/处理中/失败数量，新增 `/admin/tasks` 任务队列页（筛选、自动刷新、重试、取消）
- 公开分享核验：资产详情可生成免登录分享链接，支持有效期、访问码、下载开关与下载次数上限，可随时撤销；公开页展示资产信息与完整证据链（`/share/:token`）
- 证据链 `GET /api/assets/:id/evidence`：按上传、水印、链上存证、证书、审核发布、授权、下载的顺序汇总，区分不可篡改存证与业务台账；资产详情新增时间线，公开分享页复用
- 下载记录 `/downloads` 与后台下载台账 `/admin/downloads`：支持按资产、用户、日期、关键词筛选，管理员可看汇总；`GET /api/downloads/my`、`GET /api/downloads`
- 待办已读状态：`notification_reads` 表与 `POST /api/notifications/read`，顶栏和后台铃铛支持未读计数、全部已读
- 园林档案维护 `/admin/gardens`：新建、编辑、删除园林（有资产时拒绝删除），补齐历史、坐标、文保年份字段
- 全局命令面板（Ctrl/⌘+K）：搜索资产与园林、跳转页面与后台入口，支持键盘上下选择
- 我的合集 `/collections`：用户可按主题组织资产，支持公开/私有、批量加入、移出与编辑；资产详情新增“加入合集”
- 后台资产表支持多选与批量嵌水印/上链，逐项统计成功与失败；单条水印/上链增加不可逆操作确认
- 后台仪表盘补真实周/月资产类型分布与 30 天水印趋势；后台铃铛改为待办下拉，可直接跳转
- 上传支持多文件队列：一次选择最多 50 个文件，逐件编辑标题、显示上传/水印/存证进度与失败原因；单个文件失败不影响其余文件，成功后可在队列内直接提交发布
- 资产版本历史：上传新版本、下载历史版本、恢复旧版本（生成新版本而非删除历史）；资产主表始终指向当前版本，文件变更后水印状态重置，证据链会标注历史存证对应当前文件已变更
- 资产讨论：评论、一级回复、编辑与软删除，支持分页、角色标签与权限控制
- 图纸/影像标注：在当前版本图上拖拽框选，支持备注/问题/建议类型、待处理/已解决状态、编辑与删除；标注绑定版本，历史版本标注只在列表展示、不叠加到新图
- 资产详情下方改为“证据链 / 标注 / 版本 / 讨论”标签页，降低长页面滚动负担
- 引入 Flask-Migrate/Alembic：baseline 覆盖全部表结构，`scripts/init_db.py` 改为执行迁移；旧库自动 stamp 基线，新增迁移测试验证空库可建全表
- 分享下载写入独立 `share_downloads` 台账；后台下载台账合并授权下载与匿名分享下载，新增渠道筛选、渠道列与分享下载汇总
- 授权履约：授权管理员/授权方/资产所有者可撤销或续期授权；撤销后下载立即失效，续期同步合同到期时间；状态按到期时间实时显示为“已过期”
- 独家授权互斥：已有生效授权时不能再批独家授权，已有独家授权时也不能再批普通授权，冲突返回 409
- 事件型通知：资产提交发布通知资产管理员、审核结果通知上传者、授权审批/撤销/续期通知申请人；与实时待办合并到同一铃铛并支持已读
- 检索分面：资产列表支持标签、文件格式、上传日期范围、上传者筛选；新增 `/api/tags` 返回标签及计数
- 站内使用指南补充批量上传、版本历史，并更新测试数量
- 上传支持 500MB 内大文件不设总超时、上传前扩展名/大小校验；园林列表加载失败时禁用筛选并可重试
- 溯源结果增加水印/证书/链上记录逐项核验、哈希复制与内容核验说明；报告下载对用户可控字段做 HTML 转义
- 同周期还包括：站内使用指南 `/guide`、统一站点顶栏、资产缩略图与真实园林照片、我的资产/收藏、授权合同与撤回、操作日志、上传进度与标签落库等

### Fixed
- 水印 ID 重复份数改为按图像容量自适应（20/12/8/5/3/1）：修复部分高光/截断区域导致 ID 位错误、批量巡检无法匹配的问题；提取端兼容历史 5/8/12 份编码
- 同内容新版本不再按文件哈希继承旧证书：版本列表只把无 `version_id` 的旧证书按指纹回填，新版本必须重新存证
- 移除从未部署的 Celery 任务入口，避免与持久化队列并存；`app/tasks.py` 改为新队列的兼容入口，依赖清单移除 `celery`
- 登出时同时撤销 refresh token；改密/管理员重置密码后旧 access/refresh token 立即失效
- 修复限流装饰器在视图抛异常时重复执行视图的问题；新增可选的 `TRUST_PROXY_HEADERS` 反代真实 IP 支持
- 同哈希上传只向有权限查看该资产的人返回已存在资产 ID，避免探测他人草稿
- 存证验证重新计算当前文件 SHA-256，并校验证书状态与有效期；水印编号验证明确标注“仅登记匹配，未校验图片内容”
- 审批通过只生成一份合同（同一申请的合同唯一），并同步累加资产授权次数
- 修复公开分享接口的 401 触发登录刷新/跳转的问题；访问码错误时停留在分享页并提示
- 修复操作日志结束日期漏掉当天、资产列表快速筛选旧响应覆盖新结果、详情页授权状态失败仍可重复申请等问题
- 修复后端全量测试因高内存占用偶发 MemoryError（单进程分文件运行稳定）
- 修复演示用户资产的文件指纹与实际文件不一致，版本回填现在读取真实文件哈希
- 修复水印后存证校验必然失败：证书指纹按原始文件计算，校验同时接受原始/水印派生文件
- 已发布/待审资产上传新版本会退回草稿，必须重新水印、提交发布并审核后才能继续对外分发
- 下载文件名跟随实际文件扩展名，避免水印副本为 PNG 却按 JPG 命名
- 证书页明确标注“本地模拟存证”，首页与 README 将 AI/OCR/联盟链改为可选能力，不再宣称默认可用
- 前端构建产物目录改为 `static`，修复 Nginx 下 `/assets/:id` 直达被静态目录拦截；compose 补 `TRUST_PROXY_HEADERS`、持久化 watermarks/extracted/instance，并将数据库/Redis/MinIO/后端端口限制在本机
- 公开溯源只命中已发布资产，避免通过水印编号探测草稿
- 后台下载台账不再漏掉匿名分享下载，证据链“累计下载”与台账可通过渠道汇总对账
- 同周期还包括：路由白屏/卡顿与 Google Fonts 外链、列表骨架塌陷、详情页布局溢出、后台切换重建、水印 `verified` 误判、证书页硬编码、登录回跳与 400ms 定时器等问题

### Tests
- 后端 300 个用例：使用 `backend/scripts/run_tests.py` 逐文件隔离完整跑通（300 passed，单文件峰值 256MB）；新增侵权线索、批量巡检与授权版本绑定用例
- 前端 47 个 Vitest（`--maxWorkers=1` 降低内存占用）；Playwright 16 个点击流（新增命令面板、下载记录、公开分享核验、合集、批量上传、版本恢复、评论/标注与授权续期/撤销入口）

## [1.7.0] - 2026-10-21

### Changed
- ECharts 5.6 → 6.1（真实浏览器验证：仪表盘 2 个图表正常渲染，console/page error 为 0）
- unplugin-vue-components 0.26 → 32.1、unplugin-auto-import 0.17 → 21.1；npm audit high 从 6 降到 0
- pytest 8.3.4 → 9.0.3（CI 194 用例通过）
- 前端版本号 1.7.0

### Known
- npm audit 剩余 moderate 来自 eslint-plugin-vue 9 的传递依赖，修复需升级到 10.x（独立任务）

## [1.6.0] - 2026-10-21

### Changed
- 前端工具链：Vite 8.3（Rolldown）、@vitejs/plugin-vue 6、Vitest 5、@vitest/coverage-v8 5、jsdom 29、sass 1.99；分包配置改为函数形式
- 后端依赖：Flask 3.1.3、Flask-JWT-Extended 4.7.4、Flask-Cors 6.0.5、gunicorn 26.2、cryptography 50.0.2、Pillow 13、geopandas 1.1.2、fiona 1.10.1、pyogrio 0.13、requests 2.34.2、python-dotenv 1.2.4
- 安全：显式 pin PyJWT 2.15.1；`zhipuai` 因与安全版 PyJWT 的元数据冲突改为可选安装（需 GLM 对话时另行安装）
- 前端 npm audit 告警 17 → 9（0 critical）；后端 requirements 的 OSV 扫描无 high/critical

### Fixed
- 水印缩放恢复遇到容量不足的小尺寸候选图时不再抛 `IndexError`
- 注册日志写入失败不再把已创建用户判为注册失败
- 溯源接口正式支持 `.webp`
- 园林列表返回实时已发布资产数

### Tests
- 后端 194 个用例，覆盖率 57%（auth 98%、license 100%、watermark 100%）；CI 覆盖率门槛提升到 55%
- 前端 41 个 Vitest、5 个 Playwright 点击流

## [1.5.0] - 2026-10-19

### Added
- **严格 Git Flow**：`main` / `develop` / `feature/*` / `release/*` / `hotfix/*`，配套本地钩子、分支校验工作流与 `scripts/gitflow.sh`
- **GitHub Actions 体系**：后端 pytest + ruff + 覆盖率棘轮、前端 ESLint + Vitest + 构建、CodeQL、Dependency Review、gitleaks、OpenSSF Scorecard、Docker 构建、actionlint
- **机器人**：Dependabot（目标 `develop`，patch/minor 自动合并）、CodeRabbit、labeler、stale、welcome、Release Drafter、`main → develop` 回合并提醒
- **视觉体系 v2「青绿山水 · 档案册」**：黛青/宣纸/墨/印章朱砂令牌，宋体标题 + 等宽数据字体；重做首页、登录、注册、后台壳、仪表盘、资产目录、证书、溯源与错误页
- **前端测试基座**：Vitest + @vue/test-utils + jsdom，覆盖工具函数、状态组件与用户 store，并接入 CI
- **后端安全回归**：新增限流 429、安全响应头、健康检查用例（后端共 90 个用例）
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
- **依赖兼容与安全**：升级 `geopandas==1.1.2`、`fiona==1.10.1`、`pyogrio==0.13.0`、`pandas==2.2.3`，兼容 SHP 读写并修复 Fiona 内置 GDAL 的 CVE-2023-45853（critical）与 GeoPandas `to_postgis()` SQL 注入（high）
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
- **前端依赖安全**：升级 `vitest==3.2.6`，并通过 npm overrides 将 `tinypool` 固定到 2.1.2、将 `test-exclude` 的 `glob` 固定到 10.5.0，修复 GHSA-5xrq-8626-4rwp、GHSA-85c8-ppgw-ccpr、GHSA-5gmw-xhrv-c9v3、GHSA-5j98-mcp5-4vw2（critical/high）；41 个前端测试与构建保持通过
- **注册/溯源契约**：注册日志写入失败不再把已创建用户判为注册失败；溯源接口正式支持 `.webp` 并补回归测试
- **水印缩放恢复**：小尺寸候选图容量不足时安全跳过，不再抛 `IndexError`（issue #31）
- **园林统计**：`Garden.to_dict` 改为实时统计已发布资产数，首页园林卡片不再恒显示 0 件资产
- **CI 修复**：actionlint 的未使用循环变量、PR 标题检查补充 `statuses: write`、welcome action 输入改为下划线命名；CodeQL 路径检查改用临时目录登记表 + `commonpath` 校验；Scorecard 增加手动触发
- **Dependabot 策略**：安全更新固定指向默认分支 `main`，因此 main 接受 `dependabot/*` 并跳过其标题/commit 检查；自动合并按目标分支选择 merge commit 或 squash

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