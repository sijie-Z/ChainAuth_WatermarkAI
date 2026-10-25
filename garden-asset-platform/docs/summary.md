# 项目文件统计

> 基于当前代码库实测统计（2026-10-25，v1.11.0）

## 后端

- Python 文件：85（`backend/app`）
- 数据模型：31 张表（`backend/app/models`）
- API 资源模块：21（`backend/app/resources`）
- 服务层：17（水印、存证、授权范围、任务队列、通知、证据包、存储巡检等）
- 工具模块：26（鉴权、路径安全、审计签名、备份、限流、迁移等）
- 测试文件：52（pytest，按文件子进程串行执行）

## 前端

- Vue 单文件组件：52（40 个页面 + 11 个公共组件 + 根组件）
- JavaScript 模块：22（API、路由、状态、下载/续传工具等）
- 单元测试：7 个 Vitest 文件；Playwright 11 个 E2E 文件

## 配置文件

- Docker：后端/前端 Dockerfile、docker-compose.yml（PostgreSQL/Redis/MinIO 可选服务）
- Nginx：`frontend/nginx.conf`
- CI/CD：`.github/workflows/`（CI、CodeQL、E2E、Docker、Release、Scorecard、密钥扫描等）
- 测试：`pytest.ini`、`vitest.config.js`、`playwright.config.js`

## 文档

- 根 README 与主项目 README
- `DEVELOPMENT.md`、`deployment.md`、`QUICKSTART.md`、`USER-GUIDE.md`
- `COMPLETENESS-AUDIT.md`（能力边界与路线图）、`DEMO-SCRIPT.md`、`assets/`（17 张截图与演示视频）
- `api.yaml`、`PROJECT-STRUCTURE.md`、`file-list.md`

## 核心功能

1. ✅ 用户认证：JWT 双 Token、登出/改密失效、找回密码、邮箱验证
2. ✅ 资产管理：多文件上传、8MB+ 分块断点续传（跨页面恢复）、版本、回收站、检索分面
3. ✅ 数字水印：DCT/QIM 盲水印、矢量坐标水印、鲁棒性实验室（8 项真实攻击）
4. ✅ 存证：按文件版本签发证书；默认本地模拟链，FISCO BCOS 可选接入
5. ✅ 授权分发：双重审批、合同、版本绑定、用途/渠道/格式/地域/次数执行、使用报表
6. ✅ 分发安全：短时下载/预览/分享票据、可见下载指纹、下载台账、审计日志 HMAC
7. ✅ 协作：评论/回复、影像区域标注（版本绑定）
8. ✅ 异步任务：持久化队列、worker 心跳、重试/取消/超时对账
9. ✅ 通知：站内 SSE、邮件、Webhook（签名、重试、SSRF 拦截）
10. ✅ 证据包：ZIP 导出与公开核验（结构、哈希、水印、证书、版本）
11. ⭕ AI 辅助（可选）：以图搜图、侵权辅助检测、智能问答；默认关闭，需模型与 API Key

## 数据库表（31）

- 账号与组织：`users`、`user_tokens`、`gardens`
- 资产：`assets`、`asset_tags`、`asset_features`、`asset_versions`、`asset_comments`、`asset_annotations`、`collections`、`collection_assets`
- 存证与授权：`certificates`、`blockchain_transactions`、`licenses`、`license_applications`、`license_contracts`
- 分发与台账：`download_records`、`download_fingerprints`、`asset_shares`、`share_downloads`
- 任务与运维：`async_tasks`、`worker_heartbeats`、`upload_sessions`、`system_configs`
- 互动与通知：`favorites`、`infringement_reports`、`notification_events`、`notification_reads`、`notification_preferences`、`notification_deliveries`、`operation_logs`

## 技术亮点

1. 自研 DCT/QIM 栅格水印与矢量坐标水印，含攻击基准与真实实验页
2. 双重审批与可执行授权范围（版本、用途、地域、格式、配额）
3. 版本级存证证书与公开证据包核验
4. 长时任务持久化队列与 worker 健康度
5. 短时票据流式下载/预览，避免大文件进入 JS 内存
6. 跨页面断点续传与会话生命周期治理
7. 完整测试覆盖：后端 52 个 pytest 文件、前端 Vitest、Playwright E2E
