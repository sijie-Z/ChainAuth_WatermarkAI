# ChainAuth_WatermarkAI

> 从“版权裸奔”到“链上确权”：基于数字水印与 AI 推理的苏州园林数字资产安全分发与溯源系统

[![CI](https://github.com/sijie-Z/ChainAuth_WatermarkAI/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/sijie-Z/ChainAuth_WatermarkAI/actions/workflows/ci.yml)
[![CodeQL](https://github.com/sijie-Z/ChainAuth_WatermarkAI/actions/workflows/codeql.yml/badge.svg?branch=develop)](https://github.com/sijie-Z/ChainAuth_WatermarkAI/actions/workflows/codeql.yml)
[![Secret Scan](https://github.com/sijie-Z/ChainAuth_WatermarkAI/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/sijie-Z/ChainAuth_WatermarkAI/actions/workflows/secret-scan.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](garden-asset-platform/README.md)

本仓库包含苏州园林数字资产安全分发与溯源系统的完整实现：

**水印嵌入 → 区块链存证 → AI 侵权检测 → 授权分发 → 溯源追踪**

## 仓库结构

```
ChainAuth_WatermarkAI/
├── garden-asset-platform/        # 主项目（Vue3 + Flask + FISCO BCOS）
│   ├── backend/                  # Flask REST API、水印算法、智能合约
│   ├── frontend/                 # Vue 3 + Vite + Element Plus
│   ├── docs/                     # 项目文档
│   ├── docker-compose.yml        # 一键部署（PostgreSQL/Redis/MinIO）
│   └── CHANGELOG.md
├── 项目文档/                     # 技术架构设计文档、开发日志
├── docs/                         # 工程化文档（Git Flow、参考吸收记录）
├── .github/                      # CI/CD、机器人配置、Issue/PR 模板
├── .githooks/                    # 本地 Git 钩子（提交规范、敏感文件拦截）
└── scripts/                      # Git Flow 助手、GitHub 初始化脚本
```

## 快速开始

```bash
# Docker 一键部署
cd garden-asset-platform
cp .env.example .env                   # Docker Compose 环境变量模板
docker compose up -d
docker exec garden-backend python scripts/init_db.py
docker exec garden-backend python scripts/create_test_data.py
```

- 前端：http://localhost
- 后端 API：http://localhost:5000/api
- 健康检查：http://localhost:5000/health

本地开发与测试：

```bash
# 后端
cd garden-asset-platform/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
python scripts/init_db.py
python run.py                     # :5000
python -m pytest                  # 90 个用例（内存 SQLite）

# 前端
cd garden-asset-platform/frontend
npm ci
npm run dev                       # :5173
npm run lint:check && npm run build
```

## 工程化

| 能力 | 实现 |
|------|------|
| 分支模型 | 严格 Git Flow：`main` / `develop` / `feature/*` / `release/*` / `hotfix/*` |
| 提交规范 | Conventional Commits（本地 commit-msg 钩子 + CI commitlint + PR 标题校验） |
| CI | 后端 pytest + ruff、前端 ESLint + Vite 构建、Docker 构建校验、actionlint |
| 安全 | CodeQL、Dependency Review、gitleaks、OpenSSF Scorecard、Dependabot |
| 机器人 | Dependabot 自动合并（patch/minor）、CodeRabbit AI 审查、labeler、stale、welcome、Release Drafter |
| 发布 | 发布分支 → `main` → 标签 `vX.Y.Z` → GitHub Release + GHCR 镜像 |
| 自动回合并 | `main` 更新后自动创建同步提醒 issue，本地执行 `scripts/gitflow.sh sync` 走正常 PR 流程 |
| 视觉体系 | 青绿山水 · 档案册（黛青/宣纸/宋体/朱砂），详见 [docs/UI-DESIGN.md](docs/UI-DESIGN.md) |
| 端到端验证 | `garden-asset-platform/backend/scripts/e2e_flow.py`：完整 API 流程；Playwright 5 个前端点击流用例（`npm run test:e2e`） |

- 贡献流程：[CONTRIBUTING.md](CONTRIBUTING.md)
- Git Flow 详解：[docs/GIT-FLOW.md](docs/GIT-FLOW.md)
- 参考实践吸收记录：[docs/REFERENCE-NOTES.md](docs/REFERENCE-NOTES.md)
- 安全政策：[SECURITY.md](SECURITY.md)

### 本地启用钩子

```bash
bash scripts/setup-git-hooks.sh
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3.4、Vite 5、Pinia、Element Plus、ECharts |
| 后端 | Flask 3.0、Flask-RESTful、SQLAlchemy 2、JWT；Celery 预留（定时任务由 APScheduler 承担） |
| 存储 | PostgreSQL、Redis、Milvus；MinIO 为 docker-compose 可选服务（当前文件默认存本地磁盘） |
| 区块链 | FISCO BCOS 3.x |
| AI | 智谱 GLM-4V、CLIP、DINOv2、百度 OCR |
| 部署 | Docker Compose、Gunicorn、Nginx、GitHub Actions |

## 许可证

MIT License，详见 [garden-asset-platform/README.md](garden-asset-platform/README.md)。
