# 项目结构说明

## 文件统计

- **总文件数**: 145+
- **Python文件**: 78个
- **Vue文件**: 23个
- **JavaScript文件**: 14个
- **配置文件**: 15+
- **文档文件**: 15+

## 目录结构

```
garden-asset-platform/
│
├── backend/                          # 后端服务
│   ├── app/                          # 应用核心
│   │   ├── __init__.py               # 应用工厂
│   │   ├── config.py                 # 配置管理
│   │   ├── extensions.py             # 扩展初始化
│   │   │
│   │   ├── models/                   # 数据模型 (8个)
│   │   │   ├── __init__.py
│   │   │   ├── user.py               # 用户模型
│   │   │   ├── garden.py             # 园林模型
│   │   │   ├── asset.py              # 资产模型
│   │   │   ├── license.py            # 授权模型
│   │   │   ├── blockchain.py         # 区块链模型
│   │   │   ├── log.py                # 日志模型
│   │   │   └── extra.py              # 扩展模型
│   │   │
│   │   ├── resources/                # API资源 (8个)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # 认证API
│   │   │   ├── asset.py              # 资产API
│   │   │   ├── garden.py             # 园林API
│   │   │   ├── watermark.py          # 水印API
│   │   │   ├── blockchain.py         # 区块链API
│   │   │   ├── license.py            # 授权API
│   │   │   └── ai.py                 # AI服务API
│   │   │
│   │   ├── services/                 # 业务服务 (4个)
│   │   │   ├── __init__.py
│   │   │   ├── watermark_service.py  # 水印服务
│   │   │   ├── blockchain_service.py # 区块链服务
│   │   │   └── ai_service.py         # AI服务
│   │   │
│   │   └── utils/                    # 工具函数 (17个)
│   │       ├── response.py           # 响应格式化
│   │       ├── file_utils.py         # 文件工具
│   │       ├── datetime_utils.py     # 时间工具
│   │       ├── auth.py               # 认证装饰器
│   │       ├── cache.py              # 缓存工具
│   │       ├── errors.py             # 错误处理
│   │       ├── commands.py           # CLI命令
│   │       ├── validators.py         # 数据验证
│   │       ├── exceptions.py         # 异常类
│   │       ├── middleware.py         # 中间件
│   │       ├── logger.py             # 日志配置
│   │       ├── jwt_callbacks.py      # JWT回调
│   │       ├── signals.py            # 信号处理
│   │       ├── geometry.py           # 几何计算
│   │       ├── enums.py              # 枚举定义
│   │       ├── permissions.py        # 权限管理
│   │       └── versioning.py         # 版本控制
│   │
│   ├── algorithm/                    # 水印算法模块
│   │   ├── __init__.py
│   │   ├── vector/                   # 矢量水印
│   │   │   ├── embed.py              # 嵌入算法
│   │   │   └── extract.py            # 提取算法
│   │   ├── raster/                   # 栅格水印
│   │   │   ├── embed.py              # DCT嵌入
│   │   │   └── extract.py            # 水印提取
│   │   └── utils/                    # 算法工具
│   │       ├── nc.py                 # NC值计算
│   │       └── psnr.py               # PSNR计算
│   │
│   ├── scripts/                      # 脚本文件
│   │   ├── init_db.py                # 数据库初始化
│   │   ├── create_test_data.py       # 测试数据生成
│   │   ├── create_watermark.py       # 水印图片生成
│   │   ├── health_check.py           # 健康检查
│   │   ├── blockchain_demo.py        # 区块链演示
│   │   ├── watermark_demo.py         # 水印演示
│   │   └── ai_demo.py                # AI功能演示
│   │
│   ├── tests/                        # 测试文件
│   │   ├── conftest.py               # 测试配置
│   │   ├── test_models.py            # 模型测试
│   │   ├── test_api.py               # API测试
│   │   └── test_watermark.py         # 算法测试
│   │
│   ├── run.py                        # 启动入口
│   ├── manage.py                     # 管理脚本
│   ├── requirements.txt              # Python依赖
│   ├── pytest.ini                    # 测试配置
│   └── .env.example                  # 环境变量示例
│
├── frontend/                         # 前端应用
│   ├── src/
│   │   ├── main.js                   # 入口文件
│   │   ├── App.vue                   # 根组件
│   │   │
│   │   ├── views/                    # 页面组件 (19个)
│   │   │   ├── home/
│   │   │   │   ├── index.vue         # 首页
│   │   │   │   ├── login.vue         # 登录
│   │   │   │   └── register.vue      # 注册
│   │   │   ├── asset/
│   │   │   │   ├── list.vue          # 资产列表
│   │   │   │   ├── detail.vue        # 资产详情
│   │   │   │   └── upload.vue        # 上传资产
│   │   │   ├── trace/
│   │   │   │   └── index.vue         # 溯源查询
│   │   │   ├── license/
│   │   │   │   ├── apply.vue         # 申请授权
│   │   │   │   └── my.vue            # 我的授权
│   │   │   ├── certificate/
│   │   │   │   └── index.vue         # 存证证书
│   │   │   └── admin/
│   │   │       ├── layout.vue        # 后台布局
│   │   │       ├── dashboard.vue     # 仪表盘
│   │   │       ├── assets.vue        # 资产管理
│   │   │       ├── watermark.vue     # 水印管理
│   │   │       ├── license-pending.vue # 待审批
│   │   │       ├── license-approved.vue # 已审批
│   │   │       ├── blockchain.vue    # 存证管理
│   │   │       └── users.vue         # 用户管理
│   │   │
│   │   ├── components/               # 通用组件 (4个)
│   │   │   └── common/
│   │   │       ├── EmptyState.vue    # 空状态
│   │   │       ├── LoadingWrapper.vue # 加载包装
│   │   │       ├── StatCard.vue      # 统计卡片
│   │   │       └── StatusTag.vue     # 状态标签
│   │   │
│   │   ├── api/                      # API模块
│   │   │   ├── index.js              # Axios实例
│   │   │   └── modules.js            # API模块导出
│   │   │
│   │   ├── stores/                   # 状态管理
│   │   │   └── user.js               # 用户状态
│   │   │
│   │   ├── router/                   # 路由配置
│   │   │   └── index.js              # 路由定义
│   │   │
│   │   └── assets/                   # 静态资源
│   │       └── styles/
│   │           ├── main.scss         # 主样式
│   │           └── variables.scss    # 变量定义
│   │
│   ├── index.html                    # HTML模板
│   ├── vite.config.js                # Vite配置
│   ├── package.json                  # Node依赖
│   ├── .eslintrc.cjs                 # ESLint配置
│   └── .prettierrc                   # Prettier配置
│
├── docs/                             # 文档目录
│   ├── QUICKSTART.md                 # 快速启动指南
│   ├── DEVELOPMENT.md                # 开发文档
│   ├── deployment.md                 # 部署文档
│   ├── api.yaml                      # API文档
│   ├── summary.md                    # 项目摘要
│   └── file-list.md                  # 文件列表
│
├── docker-compose.yml                # Docker编排
├── Dockerfile                        # 后端镜像
├── Dockerfile.frontend               # 前端镜像
├── nginx.conf                        # Nginx配置
├── Makefile                          # 管理命令
├── start.py                          # 一键启动脚本
├── start.sh                          # Linux启动脚本
├── start.bat                         # Windows启动脚本
├── install.sh                        # Linux安装脚本
├── install.bat                       # Windows安装脚本
├── README.md                         # 项目说明
├── CHANGELOG.md                      # 更新日志
└── .gitignore                        # Git忽略配置
```

## API端点列表

### 认证模块 (7个端点)
- POST /api/register - 用户注册
- POST /api/login - 用户登录
- POST /api/logout - 用户登出
- POST /api/refresh - 刷新Token
- GET /api/user/current - 获取当前用户
- GET /api/users - 用户列表
- PUT /api/users/:id - 更新用户

### 资产模块 (10个端点)
- GET /api/assets - 资产列表
- GET /api/assets/:id - 资产详情
- POST /api/assets/upload - 上传资产
- PUT /api/assets/:id - 更新资产
- DELETE /api/assets/:id - 删除资产
- GET /api/assets/:id/download - 下载资产
- POST /api/assets/:id/favorite - 收藏资产
- GET /api/assets/stats - 资产统计
- GET /api/assets/my - 我的资产
- POST /api/assets/:id/publish - 发布资产

### 水印模块 (5个端点)
- POST /api/watermark/embed - 嵌入水印
- POST /api/watermark/extract - 提取水印
- POST /api/watermark/verify - 验证水印
- POST /api/watermark/trace - 水印溯源
- GET /api/watermark/logs - 操作日志

### 区块链模块 (5个端点)
- POST /api/blockchain/register - 资产存证
- GET /api/blockchain/verify/:id - 验证存证
- GET /api/blockchain/certificate/:id - 获取证书
- GET /api/blockchain/history - 存证历史
- GET /api/blockchain/status - 链状态

### AI模块 (4个端点)
- POST /api/ai/analyze - AI分析
- POST /api/ai/search - 相似搜索
- POST /api/ai/infringement - 侵权检测
- POST /api/ai/chat - 智能对话

### 授权模块 (5个端点)
- POST /api/license/apply - 申请授权
- GET /api/license/pending - 待审批列表
- POST /api/license/approve/:id - 审批授权
- GET /api/license/approved - 已审批列表
- GET /api/license/my - 我的授权

## 技术栈

### 后端
- Flask 3.0 - Web框架
- Flask-RESTful - RESTful API
- SQLAlchemy - ORM
- Flask-JWT-Extended - JWT认证
- Pillow - 图像处理
- GeoPandas - 矢量数据处理
- PyTorch + Transformers - AI模型
- ZhipuAI - GLM-4 API
- Web3.py - 区块链交互

### 前端
- Vue 3 - 前端框架
- Vite - 构建工具
- Element Plus - UI组件库
- Pinia - 状态管理
- Vue Router - 路由管理
- Axios - HTTP客户端
- ECharts - 图表库

### 数据库与中间件
- PostgreSQL - 主数据库
- Redis - 缓存
- Milvus Lite - 向量数据库
- MinIO - 对象存储
- FISCO BCOS - 区块链

## 开发规范

### Git提交规范
```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试相关
chore: 构建/工具
```

### 分支管理
- main - 主分支
- develop - 开发分支
- feature/* - 功能分支
- hotfix/* - 修复分支

## 部署方式

1. **开发环境**: Python + Node.js 直接运行
2. **生产环境**: Docker + Docker Compose
3. **云部署**: 支持阿里云/腾讯云/AWS

---

*文档生成时间: 2026-04-26*
