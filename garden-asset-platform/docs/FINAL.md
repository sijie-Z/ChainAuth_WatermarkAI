# 项目最终文档

## 一、项目概述

### 项目名称
从"版权裸奔"到"链上确权"：基于数字水印和AI推理的苏州园林数字资产安全分发与溯源系统

### 项目目标
为苏州园林数字资产提供全生命周期保护，包括：
- 数字水印嵌入与溯源
- 区块链存证确权
- 智能授权审批
- AI智能分析与检索

### 技术栈

**后端**
- Flask 3.0 + SQLAlchemy 2.0
- Flask-JWT-Extended (认证)
- Flask-RESTful (API)
- Pillow / GeoPandas (图像处理)
- Celery + Redis (异步任务)

**前端**
- Vue 3.4 + Vite 5
- Element Plus (UI)
- Pinia (状态管理)
- Vue Router (路由)
- ECharts (图表)

**基础设施**
- PostgreSQL (数据库)
- Redis (缓存/队列)
- FISCO BCOS (区块链)
- Milvus (向量检索)
- Docker (容器化)

## 二、功能模块

### 1. 用户认证模块
- 用户注册/登录
- JWT Token认证
- 角色权限管理
- 操作日志记录

### 2. 资产管理模块
- 资产上传/下载
- 文件去重
- 资产分类管理
- 收藏/下载记录

### 3. 数字水印模块
- **矢量水印**: 坐标扰动算法
- **栅格水印**: DCT域 + LSB
- 水印嵌入/提取/验证
- 图片溯源查询

### 4. 区块链存证模块
- FISCO BCOS联盟链
- 资产上链存证
- 存证验证
- 电子证书生成

### 5. 授权审批模块
- 双重审批机制
- 多种授权类型
- 授权合同生成
- 区块链授权记录

### 6. AI智能模块
- GLM-4-Flash智能问答
- CLIP特征提取
- DINOv2场景分类
- Milvus相似度检索

## 三、项目结构

```
garden-asset-platform/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── models/             # 数据模型 (8个)
│   │   ├── resources/          # API资源 (8个模块)
│   │   ├── services/           # 业务服务 (3个)
│   │   └── utils/              # 工具模块 (17个)
│   ├── algorithm/              # 水印算法
│   ├── contracts/              # 智能合约
│   ├── scripts/                # 脚本文件
│   ├── tests/                  # 测试文件
│   └── migrations/             # 数据库迁移
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── views/              # 页面组件 (19个)
│   │   ├── components/         # 公共组件 (4个)
│   │   ├── api/                # API封装 (7个模块)
│   │   ├── utils/              # 工具函数
│   │   ├── hooks/              # Vue Hooks
│   │   └── stores/             # 状态管理
│   └── public/                 # 静态资源
│
├── docs/                       # 文档
├── .github/workflows/          # CI/CD
├── docker-compose.yml          # Docker编排
├── Makefile                    # Make命令
├── start.py                    # 启动脚本
└── install.sh/bat              # 安装脚本
```

## 四、快速启动

### 方式一: Docker (推荐)

```bash
# 克隆项目
git clone <repository_url>
cd garden-asset-platform

# 配置环境变量
cp backend/.env.example backend/.env

# 启动服务
docker-compose up -d

# 初始化数据库
docker-compose exec backend flask init-gardens
```

### 方式二: 手动安装

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

**Windows:**
```cmd
install.bat
```

### 方式三: Python脚本

```bash
python start.py all        # 完整安装
python start.py backend    # 启动后端
python start.py frontend   # 启动前端
```

## 五、API文档

### 认证接口
| 方法 | 端点 | 说明 |
|-----|------|------|
| POST | /api/register | 用户注册 |
| POST | /api/login | 用户登录 |
| POST | /api/logout | 用户登出 |
| POST | /api/refresh | 刷新Token |

### 资产接口
| 方法 | 端点 | 说明 |
|-----|------|------|
| GET | /api/assets | 资产列表 |
| GET | /api/assets/:id | 资产详情 |
| POST | /api/assets/upload | 上传资产 |

### 水印接口
| 方法 | 端点 | 说明 |
|-----|------|------|
| POST | /api/watermark/embed | 嵌入水印 |
| POST | /api/watermark/extract | 提取水印 |
| POST | /api/watermark/trace | 溯源查询 |

### 区块链接口
| 方法 | 端点 | 说明 |
|-----|------|------|
| POST | /api/blockchain/register | 上链存证 |
| GET | /api/blockchain/certificate/:id | 证书详情 |

### 授权接口
| 方法 | 端点 | 说明 |
|-----|------|------|
| POST | /api/license/apply | 申请授权 |
| POST | /api/license/approve/:id | 审批操作 |

## 六、配置说明

### 环境变量

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/garden_asset

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# 区块链
BLOCKCHAIN_ENABLED=false
BLOCKCHAIN_RPC_URL=http://localhost:20200

# AI
ZHIPU_API_KEY=your-api-key
```

### 功能开关

```python
WATERMARK_ENABLED = True      # 水印功能
BLOCKCHAIN_ENABLED = False    # 区块链功能
AI_ENABLED = True             # AI功能
CELERY_ENABLED = False        # 异步任务
```

## 七、部署指南

### 生产环境要求
- Ubuntu 20.04+ / CentOS 7+
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- Nginx 1.20+

### 部署步骤

1. **安装依赖**
```bash
pip install -r requirements.txt
npm install
```

2. **配置环境**
```bash
cp .env.example .env
# 编辑.env配置生产环境参数
```

3. **初始化数据库**
```bash
python scripts/init_db.py
```

4. **构建前端**
```bash
npm run build
```

5. **启动服务**
```bash
# 使用Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"

# 或使用Docker
docker-compose up -d
```

## 八、项目统计

| 项目 | 数量 |
|-----|------|
| Python文件 | 55+ |
| Vue组件 | 23 |
| JavaScript文件 | 15+ |
| 配置文件 | 20 |
| 文档文件 | 12 |
| **总代码行数** | **~15000** |
| **总文件数** | **130+** |

## 九、技术亮点

1. **自研水印算法**: 矢量坐标扰动 + DCT/LSB栅格水印
2. **双重审批机制**: 完整的授权工作流
3. **区块链存证**: FISCO BCOS联盟链集成
4. **AI智能分析**: GLM-4 + CLIP多模态能力
5. **向量检索**: Milvus高效相似度搜索
6. **微服务架构**: Docker容器化部署
7. **完整测试**: pytest单元测试覆盖
8. **CI/CD**: GitHub Actions自动化

## 十、默认账号

| 用户名 | 密码 | 角色 | 说明 |
|-------|------|------|------|
| admin | admin123 | 超级管理员 | 通过 `flask create-admin` 创建 |
| adm1 | adm1123 | 一级审批员 | 需通过CLI创建 |
| adm2 | adm2123 | 二级审批员 | 需通过CLI创建 |
| user1 | 123456 | 普通用户 | 需通过CLI创建 |

> 注意：默认账号需通过 `flask create-admin` 命令创建，注册接口仅允许创建普通用户。

## 十一、许可证

MIT License

## 十二、联系方式

挑战杯项目团队 - 2026

---

*本文档最后更新: 2026-04-26*