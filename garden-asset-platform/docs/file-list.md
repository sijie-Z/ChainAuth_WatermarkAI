# 项目完整文件清单

## 后端文件 (85 个 Python 文件)

### 核心模块
```
backend/
├── app/
│   ├── __init__.py              # Flask应用工厂
│   ├── config.py                # 配置文件
│   ├── config_all.py            # 完整配置项
│   ├── config_features.py       # 功能开关
│   ├── config_test.py           # 测试配置
│   ├── extensions.py            # Flask扩展
│   ├── tasks.py                 # 持久化任务队列兼容入口（非 Celery）
│   │
│   ├── models/                  # 数据模型 (31 张表)
│   │   ├── __init__.py
│   │   ├── user.py              # 用户模型
│   │   ├── garden.py            # 园林模型
│   │   ├── asset.py             # 资产模型
│   │   ├── license.py           # 授权模型
│   │   ├── blockchain.py        # 区块链模型
│   │   ├── log.py               # 日志模型
│   │   └── extra.py             # 扩展模型
│   │
│   ├── resources/               # API资源 (21 个模块)
│   │   ├── __init__.py
│   │   ├── auth.py              # 认证API (7个端点)
│   │   ├── asset.py             # 资产API
│   │   ├── garden.py            # 园林API
│   │   ├── watermark.py         # 水印API (5个端点)
│   │   ├── blockchain.py        # 区块链API (5个端点)
│   │   ├── license.py           # 授权API (5个端点)
│   │   └── ai.py                # AI API (4个端点)
│   │
│   ├── services/                # 业务服务 (17 个)
│   │   ├── __init__.py
│   │   ├── watermark_service.py
│   │   ├── blockchain_service.py
│   │   └── ai_service.py
│   │
│   └── utils/                   # 工具模块 (26 个)
│       ├── __init__.py
│       ├── response.py          # 响应工具
│       ├── file_utils.py        # 文件工具
│       ├── datetime_utils.py    # 日期工具
│       ├── auth.py              # 认证装饰器
│       ├── cache.py             # 缓存工具
│       ├── errors.py            # 错误处理
│       ├── commands.py          # CLI命令
│       ├── validators.py        # 验证器
│       ├── exceptions.py        # 异常类
│       ├── middleware.py        # 中间件
│       ├── logger.py            # 日志配置
│       ├── jwt_callbacks.py     # JWT回调
│       ├── signals.py           # 信号处理
│       ├── geometry.py          # 几何工具
│       ├── enums.py             # 枚举定义
│       └── permissions.py       # 权限配置
│
├── algorithm/                   # 水印算法
│   ├── __init__.py
│   ├── vector/
│   │   ├── __init__.py
│   │   ├── embed.py
│   │   └── extract.py
│   ├── raster/
│   │   ├── __init__.py
│   │   ├── embed.py
│   │   └── extract.py
│   └── utils/
│       ├── __init__.py
│       ├── get_coor.py
│       ├── to_geodataframe.py
│       └── nc.py
│
├── contracts/                   # 智能合约
│   ├── AssetRegistry.sol
│   └── abi.py
│
├── scripts/                     # 脚本文件
│   ├── init_db.py
│   ├── create_test_data.py
│   └── create_watermark.py
│
├── tests/                       # 测试文件
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_asset.py
│   └── test_watermark.py
│
├── migrations/                  # 数据库迁移
│   └── env.py
│
├── uploads/                     # 上传目录
├── data/                        # 数据目录
├── run.py                       # 启动入口
├── requirements.txt             # Python依赖
├── pytest.ini                   # pytest配置
├── Dockerfile                   # Docker配置
├── README.md
└── PACKAGE.md
```

## 前端文件 (40+ Vue/JS文件)

### 核心模块
```
frontend/
├── src/
│   ├── main.js                  # 入口文件
│   ├── App.vue                  # 根组件
│   │
│   ├── router/                  # 路由配置
│   │   ├── index.js
│   │   └── guards.js
│   │
│   ├── stores/                  # 状态管理
│   │   └── user.js
│   │
│   ├── api/                     # API封装
│   │   ├── index.js
│   │   └── modules.js
│   │
│   ├── utils/                   # 工具函数
│   │   ├── index.js
│   │   ├── request.js
│   │   ├── charts.js
│   │   └── notify.js
│   │
│   ├── hooks/                   # Vue Hooks
│   │   └── index.js
│   │
│   ├── constants/               # 常量定义
│   │   └── index.js
│   │
│   ├── types/                   # 类型定义
│   │   └── index.ts
│   │
│   ├── styles/                  # 样式文件
│   │   └── global.scss
│   │
│   ├── components/              # 公共组件 (4个)
│   │   ├── index.js
│   │   └── common/
│   │       ├── EmptyState.vue
│   │       ├── LoadingWrapper.vue
│   │       ├── StatCard.vue
│   │       └── StatusTag.vue
│   │
│   └── views/                   # 页面组件 (19个)
│       ├── home/
│       │   ├── index.vue
│       │   ├── login.vue
│       │   └── register.vue
│       ├── asset/
│       │   ├── list.vue
│       │   ├── detail.vue
│       │   └── upload.vue
│       ├── trace/
│       │   └── index.vue
│       ├── license/
│       │   ├── apply.vue
│       │   └── my.vue
│       ├── certificate/
│       │   └── index.vue
│       └── admin/
│           ├── layout.vue
│           ├── dashboard.vue
│           ├── assets.vue
│           ├── watermark.vue
│           ├── license-pending.vue
│           ├── license-approved.vue
│           ├── blockchain.vue
│           └── users.vue
│
├── public/
│   └── favicon.svg
├── index.html
├── vite.config.js
├── package.json
├── nginx.conf
├── Dockerfile
├── README.md
└── PACKAGE.md
```

## 配置文件 (15个)

```
garden-asset-platform/
├── .gitignore                   # Git忽略配置
├── Makefile                     # Make命令
├── docker-compose.yml           # Docker编排
├── manage.py                    # 管理脚本
├── README.md                    # 项目说明
├── DEVELOPMENT.md               # 开发文档
│
├── backend/
│   ├── .env.example             # 环境变量示例
│   ├── requirements.txt         # Python依赖
│   ├── pytest.ini               # 测试配置
│   └── Dockerfile
│
├── frontend/
│   ├── package.json             # NPM依赖
│   ├── vite.config.js           # Vite配置
│   ├── .env.development         # 开发环境
│   ├── .env.production          # 生产环境
│   ├── nginx.conf               # Nginx配置
│   └── Dockerfile
│
├── docs/
│   ├── api.yaml                 # OpenAPI规范
│   ├── deployment.md            # 部署文档
│   └── summary.md               # 项目统计
│
└── .github/
    └── workflows/
        └── ci.yml               # CI/CD配置
```

## 统计汇总

| 类别 | 数量 |
|-----|------|
| Python文件 | 50+ |
| Vue组件 | 23 |
| JavaScript文件 | 10+ |
| 配置文件 | 15 |
| 文档文件 | 8 |
| **总文件数** | **100+** |

## 代码行数估计

| 模块 | 行数 |
|-----|------|
| 后端核心 | ~5000 |
| 水印算法 | ~2000 |
| 前端页面 | ~4000 |
| 前端工具 | ~1000 |
| 配置文档 | ~1000 |
| **总计** | **~13000** |