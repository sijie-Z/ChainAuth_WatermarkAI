# 挑战杯项目 - 苏州园林数字资产安全分发与溯源系统

从"版权裸奔"到"链上确权"：基于数字水印和AI推理的苏州园林数字资产安全分发与溯源系统

## 项目简介

本项目是一个完整的数字资产管理系统，集成了数字水印、区块链存证、智能授权审批等核心功能，为苏州园林数字资产提供全生命周期保护。

## 核心技术

- **数字水印**: 自研矢量水印(坐标扰动) + 栅格水印(DCT/LSB)
- **区块链存证**: FISCO BCOS联盟链
- **AI能力**: GLM-4-Flash智能问答 + CLIP/DINOv2特征提取
- **向量检索**: Milvus相似度搜索

## 项目结构

```
garden-asset-platform/
├── backend/                 # Flask后端服务
│   ├── app/
│   │   ├── models/         # 数据模型
│   │   ├── resources/      # API资源
│   │   ├── services/       # 业务服务
│   │   └── utils/          # 工具函数
│   ├── algorithm/          # 水印算法
│   ├── contracts/          # 智能合约
│   └── scripts/            # 脚本文件
├── frontend/               # Vue3前端应用
│   └── src/
│       ├── views/          # 页面组件(19个)
│       ├── api/            # API封装
│       ├── router/         # 路由配置
│       └── stores/         # 状态管理
└── docs/                    # 文档
```

## 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python scripts/init_db.py    # 初始化数据库
python run.py                # 启动服务
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 默认账号

- 管理员: admin / admin123
- 审批员: adm1, adm2 / 123456
- 用户: user1, user2 / 123456

## 主要功能

| 模块 | 功能 | 状态 |
|-----|------|------|
| 用户认证 | 注册/登录/JWT | ✅ |
| 资产管理 | 上传/列表/详情 | ✅ |
| 水印处理 | 嵌入/提取/溯源 | ✅ |
| 区块链 | 存证/验证/证书 | ✅ |
| 授权审批 | 申请/双重审批 | ✅ |
| AI分析 | 特征提取/搜索 | ✅ |

## 技术栈

**后端:** Flask 3.0, SQLAlchemy, Flask-JWT-Extended, Flask-RESTful

**前端:** Vue 3.4, Vite 5, Element Plus, Pinia, Vue Router

**数据库:** PostgreSQL / SQLite

**区块链:** FISCO BCOS

**AI:** GLM-4-Flash, CLIP, DINOv2, Milvus

## 更新日志

### 2026-04-26
- 完成前后端核心功能开发
- 19个Vue页面 + 8个API模块
- 数据库初始化脚本
- 水印算法迁移
- 授权审批流程

## 许可证

MIT License

## 作者

挑战杯项目团队
